"""Dedicated administrator credentials; display and collector tokens never grant administration."""
import argparse
import json
import secrets
import sqlite3
import time
from datetime import timedelta, datetime
from pathlib import Path
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from fastapi import Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials
from pixora.models import now
from pixora.devices import token_hash, provision
from pixora.device_profiles import Profile, Policy, read_profile, configure
from pixora.settings import setting

COOKIE='__Host-pixora_admin'
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
class NewDevice(Strict):
    name: Annotated[str,Field(min_length=1,max_length=80)]
    providers: Annotated[list[Literal['codex','chatgpt','system','github','rss','tasks','weather']],Field(min_length=1,max_length=7)]
    days: Annotated[int,Field(ge=1,le=365)]=30
    profile: Profile=Field(default_factory=Profile)
    policy: Policy=Field(default_factory=Policy)
class Target(Strict):
    id: Annotated[str,Field(pattern=r'^[a-f0-9]{24}$')]
    revision: Annotated[int,Field(ge=0)]
class Publication(Strict):
    targets: Annotated[list[Target],Field(min_length=1,max_length=20)]
    profile: Profile
class DeviceUpdate(Strict):
    revision: Annotated[int,Field(ge=0)]
    name: Annotated[str,Field(min_length=1,max_length=80)] | None=None
    policy: Policy | None=None


def initialize(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS admin_keys(id TEXT PRIMARY KEY,name TEXT NOT NULL,token_hash TEXT UNIQUE NOT NULL,expires_at TEXT NOT NULL,revoked INTEGER NOT NULL DEFAULT 0)')
    conn.execute('CREATE TABLE IF NOT EXISTS admin_sessions(token_hash TEXT PRIMARY KEY,key_id TEXT NOT NULL,expires_at TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS admin_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,device_id TEXT,detail TEXT NOT NULL)')

def issue_key(conn,name,days=90):
    if not name.strip() or len(name)>80 or not 1<=days<=365:raise ValueError('invalid key name or expiry')
    secret=secrets.token_urlsafe(32);identifier=secrets.token_hex(12);expiry=(now()+timedelta(days=days)).isoformat()
    conn.execute('INSERT INTO admin_keys VALUES (?,?,?,?,0)',(identifier,name.strip(),token_hash(secret),expiry))
    return dict(id=identifier,token=secret,expires_at=expiry)

def audit(conn,actor,action,device_id=None,detail=None):
    conn.execute('INSERT INTO admin_audit(at,actor,action,device_id,detail) VALUES (?,?,?,?,?)',(now().isoformat(),actor,action,device_id,json.dumps(detail or {})))
    conn.execute('DELETE FROM admin_audit WHERE id NOT IN (SELECT id FROM admin_audit ORDER BY id DESC LIMIT 1000)')

def device_info(conn,row):
    identifier,name,providers,modes,expires,revoked=row
    try:
        profile,policy,revision,updated=read_profile(conn,identifier)
        config=dict(profile=profile.model_dump(),policy=policy.model_dump(),revision=revision,updated_at=updated,configuration_error=False)
    except ValueError:config=dict(profile=None,policy=None,revision=None,updated_at=None,configuration_error=True)
    sessions=conn.execute('SELECT COUNT(*) FROM device_sessions WHERE device_id=? AND expires_at>?',(identifier,now().isoformat())).fetchone()[0]
    return dict(id=identifier,name=name,providers=json.loads(providers),modes=json.loads(modes),expires_at=expires,
        status='revoked' if revoked else 'expired' if datetime.fromisoformat(expires)<=now() else 'active',sessions=sessions if not revoked else 0,**config)

class Conflict(ValueError):pass

def check_target(conn,identifier,revision):
    row=conn.execute('SELECT id,name,providers,modes,expires_at,revoked FROM devices WHERE id=?',(identifier,)).fetchone()
    if row is None or row[5] or datetime.fromisoformat(row[4])<=now():raise ValueError('unknown, expired or revoked device')
    if read_profile(conn,identifier)[2]!=revision:raise Conflict('configuration changed; reload before publishing')
    return row

def install_routes(app,db,same_origin,bearer):
    attempts=[]
    def admin_scope(request:Request):
        secret=request.cookies.get(COOKIE,'')
        with db() as conn:
            row=conn.execute('SELECT k.id,k.name,s.expires_at FROM admin_sessions s JOIN admin_keys k ON k.id=s.key_id WHERE s.token_hash=? AND s.expires_at>? AND k.expires_at>? AND k.revoked=0',
                (token_hash(secret),now().isoformat(),now().isoformat())).fetchone() if secret else None
        if row is None:raise HTTPException(401,'administrator sign-in required')
        return dict(id=row[0],name=row[1],expires_at=row[2])
    @app.post('/api/admin/session')
    def login(request:Request,credentials:HTTPAuthorizationCredentials | None=Depends(bearer)):
        same_origin(request)
        timestamp=time.monotonic();attempts[:]=[t for t in attempts if timestamp-t<60]
        if len(attempts)>=20:raise HTTPException(429,'administrator sign-in limit; retry later')
        attempts.append(timestamp)
        secret=credentials.credentials if credentials else ''
        with db() as conn:
            row=conn.execute('SELECT id,name,expires_at FROM admin_keys WHERE token_hash=? AND revoked=0 AND expires_at>?',(token_hash(secret),now().isoformat())).fetchone()
            if row is None:raise HTTPException(401,'invalid administrator key')
            expiry=min(now()+timedelta(hours=8),datetime.fromisoformat(row[2]));session=secrets.token_urlsafe(32)
            conn.execute('DELETE FROM admin_sessions WHERE expires_at<=? OR token_hash=?',(now().isoformat(),token_hash(request.cookies.get(COOKIE,''))))
            conn.execute('INSERT INTO admin_sessions VALUES (?,?,?)',(token_hash(session),row[0],expiry.isoformat()))
            conn.execute('DELETE FROM admin_sessions WHERE key_id=? AND token_hash NOT IN (SELECT token_hash FROM admin_sessions WHERE key_id=? ORDER BY expires_at DESC LIMIT 5)',(row[0],row[0]))
            audit(conn,row[0],'sign_in')
        response=JSONResponse(dict(name=row[1],expires_at=expiry.isoformat()))
        response.set_cookie(COOKIE,session,max_age=max(1,int((expiry-now()).total_seconds())),expires=expiry,path='/',secure=True,httponly=True,samesite='strict')
        return response
    @app.get('/api/admin/session')
    def session(scope=Depends(admin_scope)):return dict(name=scope['name'],expires_at=scope['expires_at'])
    @app.delete('/api/admin/session')
    def logout(request:Request):
        same_origin(request)
        with db() as conn:conn.execute('DELETE FROM admin_sessions WHERE token_hash=?',(token_hash(request.cookies.get(COOKIE,'')),))
        response=Response(status_code=204);response.delete_cookie(COOKIE,path='/',secure=True,httponly=True,samesite='strict');return response
    @app.get('/api/admin/devices')
    def inventory(limit:int=Query(default=100,ge=1,le=100),before:str=Query(default='',max_length=24),scope=Depends(admin_scope)):
        with db() as conn:
            rows=conn.execute("SELECT id,name,providers,modes,expires_at,revoked FROM devices WHERE (?='' OR id<?) ORDER BY id DESC LIMIT ?",(before,before,limit+1)).fetchall()
            items=[device_info(conn,row) for row in rows[:limit]]
        return dict(devices=items,next_before=rows[limit-1][0] if len(rows)>limit else None)
    @app.post('/api/admin/devices',status_code=201)
    def create(body:NewDevice,request:Request,scope=Depends(admin_scope)):
        same_origin(request)
        try:
            with db() as conn:
                conn.execute('BEGIN IMMEDIATE')
                if conn.execute('SELECT COUNT(*) FROM devices WHERE revoked=0 AND expires_at>?',(now().isoformat(),)).fetchone()[0]>=200:raise HTTPException(409,'active device limit reached')
                device=provision(conn,body.name,body.providers,['real'],body.days)
                configure(conn,device['id'],body.profile.model_dump(),body.policy.model_dump())
                audit(conn,scope['id'],'create',device['id'],dict(providers=sorted(set(body.providers)),days=body.days))
            return device
        except ValueError:raise HTTPException(422,'invalid device configuration or scope')
    @app.post('/api/admin/profiles/publish')
    def publish(body:Publication,request:Request,scope=Depends(admin_scope)):
        same_origin(request)
        if len({t.id for t in body.targets})!=len(body.targets):raise HTTPException(422,'duplicate target')
        try:
            with db() as conn:
                conn.execute('BEGIN IMMEDIATE')
                for t in body.targets:check_target(conn,t.id,t.revision)
                result=[]
                for t in body.targets:
                    value=configure(conn,t.id,profile=body.profile.model_dump());audit(conn,scope['id'],'publish_profile',t.id,dict(revision=value['revision']))
                    result.append(dict(id=t.id,revision=value['revision']))
            return dict(devices=result)
        except Conflict:raise HTTPException(409,'configuration changed; reload before publishing')
        except ValueError:raise HTTPException(422,'invalid device configuration or target')
    @app.post('/api/admin/devices/{identifier}/configure')
    def update(identifier:str,body:DeviceUpdate,request:Request,scope=Depends(admin_scope)):
        same_origin(request)
        if body.name is None and body.policy is None:raise HTTPException(422,'no changes supplied')
        if body.name is not None and not body.name.strip():raise HTTPException(422,'device name is empty')
        try:
            with db() as conn:
                conn.execute('BEGIN IMMEDIATE');check_target(conn,identifier,body.revision)
                value=configure(conn,identifier,policy=body.policy.model_dump() if body.policy else None)
                if body.name is not None:conn.execute('UPDATE devices SET name=? WHERE id=?',(body.name.strip(),identifier))
                audit(conn,scope['id'],'configure',identifier,dict(revision=value['revision'],policy_changed=body.policy is not None,name_changed=body.name is not None))
            return dict(id=identifier,revision=value['revision'])
        except Conflict:raise HTTPException(409,'configuration changed; reload before saving')
        except ValueError:raise HTTPException(422,'invalid device configuration or scope')
    @app.post('/api/admin/devices/{identifier}/revoke')
    def revoke(identifier:str,request:Request,scope=Depends(admin_scope)):
        same_origin(request)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('UPDATE devices SET revoked=1 WHERE id=?',(identifier,)).rowcount!=1:raise HTTPException(404,'unknown device')
            conn.execute('DELETE FROM device_sessions WHERE device_id=?',(identifier,));audit(conn,scope['id'],'revoke',identifier)
        return dict(id=identifier,revoked=True)
    @app.get('/api/admin/audit')
    def history(scope=Depends(admin_scope)):
        with db() as conn:rows=conn.execute('SELECT id,at,action,device_id,detail FROM admin_audit ORDER BY id DESC LIMIT 100').fetchall()
        return dict(events=[dict(id=r[0],at=r[1],action=r[2],device_id=r[3],detail=json.loads(r[4])) for r in rows])

def main():
    parser=argparse.ArgumentParser(description='Local administrator bootstrap; raw keys are shown only once')
    parser.add_argument('--db',default=setting('DB','data/pixora.sqlite'))
    commands=parser.add_subparsers(dest='command',required=True)
    create=commands.add_parser('create');create.add_argument('--name',required=True);create.add_argument('--days',type=int,default=90)
    commands.add_parser('list');revoke=commands.add_parser('revoke');revoke.add_argument('id')
    args=parser.parse_args();Path(args.db).parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(args.db,timeout=10) as conn:
        initialize(conn)
        if args.command=='create':
            try:print(json.dumps(issue_key(conn,args.name,args.days)))
            except ValueError as e:parser.error(str(e))
        elif args.command=='list':print(json.dumps([dict(zip(['id','name','expires_at','revoked'],r)) for r in conn.execute('SELECT id,name,expires_at,revoked FROM admin_keys')]))
        else:
            if conn.execute('UPDATE admin_keys SET revoked=1 WHERE id=?',(args.id,)).rowcount!=1:parser.error('unknown administrator key')
            conn.execute('DELETE FROM admin_sessions WHERE key_id=?',(args.id,));print(json.dumps(dict(id=args.id,revoked=True)))
if __name__=='__main__':main()
