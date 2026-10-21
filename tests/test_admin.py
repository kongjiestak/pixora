import json
import sqlite3
from datetime import timedelta,datetime
import pytest
from fastapi.testclient import TestClient
from pixora.server import create_app
from pixora.models import now
from pixora.devices import provision
from pixora.device_profiles import read_profile,configure
from pixora.admin import issue_key,COOKIE,audit
from test_api import READ,WRITE,auth

ORIGIN={'Origin':'https://testserver'}

def setup(tmp_path):
    db=tmp_path/'admin.sqlite';app=create_app(db,READ,WRITE)
    c=TestClient(app,base_url='https://testserver')
    with sqlite3.connect(db) as conn:
        key=issue_key(conn,'owner');device=provision(conn,'existing phone',['codex','system'],['real'])
    return db,c,key,device

def login(c,key):return c.post('/api/admin/session',headers={**ORIGIN,**auth(key['token'])})
def new(c,name='new phone',providers=None):return c.post('/api/admin/devices',headers=ORIGIN,json=dict(name=name,providers=providers or ['codex','system'],days=30))
def target(c,identifier):
    return next(dict(id=d['id'],revision=d['revision']) for d in c.get('/api/admin/devices').json()['devices'] if d['id']==identifier)

def test_no_display_collector_or_legacy_credential_can_administer(tmp_path):
    db,c,key,d=setup(tmp_path)
    for token in [d['token'],READ,WRITE,'wrong']:
        assert login(c,dict(token=token)).status_code==401
        assert c.get('/api/admin/devices',headers=auth(token)).status_code==401
        assert c.post('/api/admin/devices',headers={**ORIGIN,**auth(token)},json=dict(name='no',providers=['codex'])).status_code==401
    assert c.post('/api/v1/session',headers={**ORIGIN,**auth(d['token'])}).status_code==200
    assert c.get('/api/admin/devices').status_code==401
    for url in ['/api/v1/device','/api/v2/device-config','/api/v2/observations']:
        fresh=TestClient(c.app,base_url='https://testserver')
        assert fresh.get(url,headers=auth(key['token'])).status_code==401
    assert login(c,key).status_code==200
    assert c.get('/api/v1/device').status_code==200  # independent existing display session


def test_cookie_digest_expiry_revocation_and_separate_logout(tmp_path):
    db,c,key,d=setup(tmp_path)
    c.post('/api/v1/session',headers={**ORIGIN,**auth(d['token'])})
    response=login(c,key);cookie=c.cookies.get(COOKIE)
    assert all(v in response.headers['set-cookie'] for v in ['HttpOnly','Secure','SameSite=strict','Path=/'])
    assert 'Domain=' not in response.headers['set-cookie']
    assert now()+timedelta(hours=7)<datetime.fromisoformat(response.json()['expires_at'])<=now()+timedelta(hours=8)
    with sqlite3.connect(db) as conn:
        raw=str(conn.execute('SELECT * FROM admin_keys').fetchall())+str(conn.execute('SELECT * FROM admin_sessions').fetchall())
        assert key['token'] not in raw and cookie not in raw
    assert c.delete('/api/admin/session',headers=ORIGIN).status_code==204
    assert c.get('/api/admin/session').status_code==401
    assert c.get('/api/v1/device').status_code==200
    assert login(c,key).status_code==200
    with sqlite3.connect(db) as conn:conn.execute('UPDATE admin_keys SET revoked=1 WHERE id=?',(key['id'],))
    assert c.get('/api/admin/devices').status_code==401


@pytest.mark.parametrize('change',['key_expiry','session_expiry'])
def test_expiry_is_checked_on_every_admin_read_and_write(tmp_path,change):
    db,c,key,d=setup(tmp_path);login(c,key)
    with sqlite3.connect(db) as conn:
        table='admin_keys' if change=='key_expiry' else 'admin_sessions'
        conn.execute('UPDATE '+table+' SET expires_at=?',((now()-timedelta(seconds=1)).isoformat(),))
    assert c.get('/api/admin/devices').status_code==401
    assert new(c).status_code==401


@pytest.mark.parametrize('origin',[None,'https://evil.example','http://testserver'])
def test_csrf_guards_all_admin_mutations(tmp_path,origin):
    db,c,key,d=setup(tmp_path);headers={} if origin is None else {'Origin':origin}
    assert c.post('/api/admin/session',headers={**headers,**auth(key['token'])}).status_code==403
    login(c,key)
    assert c.post('/api/admin/devices',headers=headers,json=dict(name='x',providers=['codex'])).status_code==403
    assert c.post('/api/admin/devices/'+d['id']+'/revoke',headers=headers).status_code==403
    assert c.post('/api/admin/devices/'+d['id']+'/configure',headers=headers,json=dict(revision=0,name='bad')).status_code==403
    assert c.post('/api/admin/profiles/publish',headers=headers,json=dict(targets=[target(c,d['id'])],profile={})).status_code==403
    assert c.delete('/api/admin/session',headers=headers).status_code==403
    assert c.get('/api/admin/session').status_code==200


def test_create_pair_scope_and_revoke_existing_cookie_immediately(tmp_path):
    db,c,key,d=setup(tmp_path);login(c,key)
    with sqlite3.connect(db) as conn:old=conn.execute('SELECT * FROM devices WHERE id=?',(d['id'],)).fetchone()
    result=new(c,providers=['system']);assert result.status_code==201
    added=result.json();token=added['token']
    display=TestClient(c.app,base_url='https://testserver')
    assert display.post('/api/v1/session',headers={**ORIGIN,**auth(token)}).status_code==200
    cfg=display.get('/api/v2/device-config').json();assert cfg['providers']==['system'] and cfg['revision']==1
    assert display.get('/api/v1/device?mode=demo').status_code==403
    assert c.post('/api/admin/devices/'+added['id']+'/revoke',headers=ORIGIN).status_code==200
    for headers in [{},auth(token)]:assert display.get('/api/v2/device-config',headers=headers).status_code==401
    for url in ['/api/admin/devices','/api/admin/audit']:
        r=c.get(url);assert token not in r.text and key['token'] not in r.text and 'token_hash' not in r.text
    with sqlite3.connect(db) as conn:assert conn.execute('SELECT * FROM devices WHERE id=?',(d['id'],)).fetchone()==old


def test_atomic_batch_publication_conflicts_and_policy_preservation(tmp_path):
    db,c,key,d=setup(tmp_path);login(c,key);b=new(c).json()
    with sqlite3.connect(db) as conn:configure(conn,d['id'],policy=dict(rules={'system':dict(metrics=['cpu.used'])}))
    targets=[target(c,d['id']),target(c,b['id'])]
    body=dict(targets=targets,profile=dict(theme='paper',accent='amber',weather_location=4699066))
    result=c.post('/api/admin/profiles/publish',headers=ORIGIN,json=body);assert result.status_code==200
    for value in result.json()['devices']:
        with sqlite3.connect(db) as conn:
            profile,policy,revision,_=read_profile(conn,value['id']);assert profile.theme=='paper' and revision==2
            if value['id']==d['id']:assert policy.rules['system'].metrics==['cpu.used']
    assert c.post('/api/admin/profiles/publish',headers=ORIGIN,json=body).status_code==409
    # A valid first target and stale second target must not partially publish.
    body['targets'][0]=target(c,d['id']);body['profile']['theme']='aurora'
    assert c.post('/api/admin/profiles/publish',headers=ORIGIN,json=body).status_code==409
    with sqlite3.connect(db) as conn:assert read_profile(conn,d['id'])[0].theme=='paper'
    body['targets']=[target(c,d['id'])]*2
    assert c.post('/api/admin/profiles/publish',headers=ORIGIN,json=body).status_code==422


def test_admin_edit_cannot_expand_grant_and_invalid_create_rolls_back(tmp_path):
    db,c,key,d=setup(tmp_path);login(c,key)
    url='/api/admin/devices/'+d['id']+'/configure'
    bad=c.post(url,headers=ORIGIN,json=dict(revision=0,name='changed',policy=dict(rules={'weather':{}})))
    assert bad.status_code==422
    good=c.post(url,headers=ORIGIN,json=dict(revision=0,name='desk',policy=dict(rules={'system':dict(metrics=['cpu.used'])})))
    assert good.status_code==200
    assert c.post(url,headers=ORIGIN,json=dict(revision=0,name='stale')).status_code==409
    with sqlite3.connect(db) as conn:count=conn.execute('SELECT COUNT(*) FROM devices').fetchone()[0]
    for body in [dict(name=' ',providers=['system']),dict(name='x',providers=['system'],policy=dict(rules={'codex':{}})),dict(name='x',providers=['system'],days=366),dict(name='x',providers=['system'],profile=dict(theme='bad')),dict(name='x',providers=['system'],modes=['demo'])]:
        assert c.post('/api/admin/devices',headers=ORIGIN,json=body).status_code==422
    with sqlite3.connect(db) as conn:assert conn.execute('SELECT COUNT(*) FROM devices').fetchone()[0]==count
    device=next(x for x in c.get('/api/admin/devices').json()['devices'] if x['id']==d['id']);assert device['name']=='desk'


def test_inventory_pagination_corrupt_configuration_and_audit_bounds(tmp_path):
    db,c,key,d=setup(tmp_path);login(c,key)
    new(c)
    first=c.get('/api/admin/devices?limit=1').json();assert first['next_before']
    second=c.get('/api/admin/devices?limit=1&before='+first['next_before']).json();assert first['devices'][0]['id']!=second['devices'][0]['id']
    with sqlite3.connect(db) as conn:
        configure(conn,d['id']);conn.execute("UPDATE device_profiles SET policy='bad' WHERE device_id=?",(d['id'],))
        for i in range(1005):audit(conn,key['id'],'revoke',d['id'])
        assert conn.execute('SELECT COUNT(*) FROM admin_audit').fetchone()[0]==1000
    assert next(x for x in c.get('/api/admin/devices').json()['devices'] if x['id']==d['id'])['configuration_error']
    assert len(c.get('/api/admin/audit').json()['events'])==100
    assert c.post('/api/admin/devices/'+d['id']+'/revoke',headers=ORIGIN).status_code==200


def test_login_rate_limit_and_session_cap(tmp_path):
    db,c,key,d=setup(tmp_path)
    for _ in range(7):c.cookies.clear();assert login(c,key).status_code==200
    with sqlite3.connect(db) as conn:assert conn.execute('SELECT COUNT(*) FROM admin_sessions').fetchone()[0]==5
    for _ in range(13):assert login(c,dict(token='wrong')).status_code==401
    assert login(c,key).status_code==429


def test_admin_cli_key_create_list_revoke(tmp_path,monkeypatch,capsys):
    from pixora.admin import main
    db,c,key,d=setup(tmp_path)
    def cli(*args):
        monkeypatch.setattr('sys.argv',['pixora-admin','--db',str(db),*args]);main();return json.loads(capsys.readouterr().out)
    created=cli('create','--name','backup','--days','1')
    assert created['token'] not in json.dumps(cli('list'))
    assert login(c,created).status_code==200
    cli('revoke',created['id']);assert c.get('/api/admin/session').status_code==401
