import asyncio
from datetime import timedelta,timezone
import json
import sqlite3
import importlib.util
from fastapi.testclient import TestClient
import pytest
from pixora.server import create_app
from pixora.models import now
from pixora.devices import provision
from pixora.observations import Observation
from pixora.system_connector import SystemCollector,cpu_sample,memory_percent

READ='r'*40;WRITE='w'*40
def auth(t):return {'Authorization':'Bearer '+t}
def observation(age=0,entity='local-host'):
 t=now()-timedelta(seconds=age)
 return dict(provider='system',connector_id='linux-host',entity_id=entity,category='system',source='linux-proc-statvfs',mode='real',status='ok',collected_at=t.isoformat(),expires_at=(t+timedelta(seconds=600)).isoformat(),metrics=[dict(key='cpu.used',value=25,unit='percent')])

def test_migration_backfill_and_restore(tmp_path):
 db=tmp_path/'db'
 body=dict(provider='codex',source='codex-app-server',mode='real',status='ok',observed_at=now().isoformat(),windows=[dict(name='codex/primary',used_percent=25)])
 with sqlite3.connect(db) as c:
  c.execute('create table snapshots(provider,mode,body,received_at,primary key(provider,mode))')
  c.execute('insert into snapshots values(?,?,?,?)',('codex','real',json.dumps(body),now().isoformat()))
 app=create_app(db,READ,WRITE)
 backup=list(tmp_path.glob('db.pre-v2-*'));assert len(backup)==1
 create_app(db,READ,WRITE);assert len(list(tmp_path.glob('db.pre-v2-*')))==1
 with sqlite3.connect(db) as c:
  assert c.execute('pragma user_version').fetchone()[0]==2
  assert c.execute('select count(*) from observations').fetchone()[0]==1
  assert json.loads(c.execute('select body from snapshots').fetchone()[0])==body
 spec=importlib.util.spec_from_file_location('restore','scripts/restore_database.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 restored=tmp_path/'rollback';mod.restore(backup[0],restored)
 with sqlite3.connect(restored) as c:
  assert c.execute('pragma user_version').fetchone()[0]==0
  assert c.execute('select count(*) from snapshots').fetchone()[0]==1
 with pytest.raises(FileExistsError):mod.restore(backup[0],restored)

def test_v2_history_scopes_replay_expiry_and_v1(tmp_path):
 db=tmp_path/'db';client=TestClient(create_app(db,READ,WRITE))
 with sqlite3.connect(db) as c:
  qa=provision(c,'system',['system'],['real']);old=provision(c,'old',['codex'],['real'])
 assert client.post('/api/v2/observations',json=observation(),headers=auth(qa['token'])).status_code==401
 for age in (800,700,650):assert client.post('/api/v2/observations',json=observation(age),headers=auth(WRITE)).status_code==200
 assert client.post('/api/v2/observations',json=observation(1000),headers=auth(WRITE)).status_code==409
 latest=client.get('/api/v2/observations',headers=auth(qa['token'])).json()['observations']
 assert len(latest)==1 and latest[0]['stale']
 assert client.get('/api/v2/observations',headers=auth(old['token'])).json()['observations']==[]
 assert client.get('/api/v2/history?provider=system',headers=auth(old['token'])).status_code==403
 assert client.get('/api/v2/history?provider=system&mode=demo',headers=auth(qa['token'])).status_code==403
 page=client.get('/api/v2/history?provider=system&limit=2',headers=auth(qa['token'])).json();assert len(page['items'])==2
 next_page=client.get('/api/v2/history?provider=system&limit=2&before='+str(page['next_before']),headers=auth(qa['token'])).json();assert len(next_page['items'])==1
 assert client.get('/api/v2/history?provider=system&limit=501',headers=auth(qa['token'])).status_code==422
 assert client.get('/api/v2/history?provider=system').status_code==401
 assert client.get('/api/v1/device',headers=auth(qa['token'])).json()['providers']==[]
 assert client.get('/api/v2/observations',headers=auth(WRITE)).status_code==401
 with sqlite3.connect(db) as c:c.execute('update devices set revoked=1 where id=?',(qa['id'],))
 assert client.get('/api/v2/observations',headers=auth(qa['token'])).status_code==401

def test_contract_unknown_and_timestamps():
 x=observation();x['metrics'][0]['value']=None
 with pytest.raises(ValueError):Observation(**x)
 x['metrics'][0]['value']=float('nan')
 with pytest.raises(ValueError):Observation(**x)
 x=observation();x['collected_at']=now().replace(tzinfo=None).isoformat()
 with pytest.raises(ValueError):Observation(**x)
 x=observation();x['collected_at']=now().astimezone(timezone(timedelta(hours=8))).isoformat()
 assert Observation(**x).collected_at.utcoffset()==timedelta(0)


def test_system_missing_source_and_parsing(monkeypatch):
 assert cpu_sample('cpu 10 0 20 40 5 0 0 0 10 0')==(75,45)
 assert memory_percent('MemTotal: 100 kB\nMemAvailable: 25 kB')==75
 import pixora.system_connector as module
 monkeypatch.setattr(module.sys,'platform','darwin')
 item=asyncio.run(SystemCollector().collect())[0]
 assert item.status=='unavailable' and item.metrics==[]

def test_retention_dedup_and_failed_migration(tmp_path):
 from pixora.database import append,migrate
 db=tmp_path/'bounded';create_app(db,READ,WRITE)
 with sqlite3.connect(db) as c:
  for age in range(1100,0,-1):append(c,Observation(**observation(age)),now().isoformat())
  assert c.execute('select count(*) from observations').fetchone()[0]==1000
  item=Observation(**observation());append(c,item,now().isoformat());append(c,item,now().isoformat())
  assert c.execute('select count(*) from observations').fetchone()[0]==1000
 broken=tmp_path/'broken'
 with sqlite3.connect(broken) as c:
  c.execute('create table snapshots(body,received_at)');c.execute("insert into snapshots values('invalid','invalid')")
 with pytest.raises(ValueError):migrate(broken)
 with sqlite3.connect(broken) as c:
  assert c.execute('pragma user_version').fetchone()[0]==0
  assert not c.execute("select name from sqlite_master where name='observations'").fetchall()
 assert len(list(tmp_path.glob('broken.pre-v2-*')))==1
