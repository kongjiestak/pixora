from datetime import timedelta
from fastapi.testclient import TestClient
import pytest
from apm.server import create_app
from apm.models import now

READ = "r"*40
WRITE = "w"*40

def auth(token):
    return {"Authorization": "Bearer "+token}

def payload(mode="real", age=0):
    return dict(provider="codex", source="demo" if mode=="demo" else "codex-app-server", mode=mode, status="ok", observed_at=(now()-timedelta(seconds=age)).isoformat(), windows=[dict(name="codex/primary", used_percent=25, duration_minutes=300)])

@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path/'test.sqlite', READ, WRITE, 600, web_dir=tmp_path/'no-web'))

def test_fail_closed(tmp_path):
    with pytest.raises(RuntimeError):
        create_app(tmp_path/'x', 'short', WRITE)
    with pytest.raises(RuntimeError):
        create_app(tmp_path/'x', READ, READ)

def test_auth_scope(client):
    assert client.get('/healthz').status_code==200
    for token in ('', WRITE):
        assert client.get('/api/v1/device', headers=auth(token)).status_code==401
    assert client.post('/api/v1/snapshots', json=payload(), headers=auth(READ)).status_code==401
    assert client.post('/api/v1/device', headers=auth(READ)).status_code==405
    assert client.get('/api/v1/snapshots', headers=auth(WRITE)).status_code==405

def test_empty_never_fabricates(client):
    data=client.get('/api/v1/device',headers=auth(READ)).json()
    assert all(p['windows']==[] and p['status']=='unavailable' and p['stale'] for p in data['providers'])

def test_roundtrip_and_modes(client):
    assert client.post('/api/v1/snapshots',json=payload(),headers=auth(WRITE)).status_code==200
    p=client.get('/api/v1/device',headers=auth(READ)).json()['providers'][0]
    assert p['windows'][0]['remaining_percent']==75
    assert not p['stale'] and p['source']=='codex-app-server'
    assert client.post('/api/v1/snapshots',json=payload('demo'),headers=auth(WRITE)).status_code==200
    assert client.get('/api/v1/device?mode=demo',headers=auth(READ)).json()['providers'][0]['mode']=='demo'
    assert client.get('/api/v1/device',headers=auth(READ)).json()['providers'][0]['mode']=='real'
    assert client.get('/api/v1/device?mode=invalid',headers=auth(READ)).status_code==422

def test_stale_replay_and_future(client):
    assert client.post('/api/v1/snapshots',json=payload(age=1000),headers=auth(WRITE)).status_code==200
    assert client.get('/api/v1/device',headers=auth(READ)).json()['providers'][0]['stale']
    assert client.post('/api/v1/snapshots',json=payload(age=2000),headers=auth(WRITE)).status_code==409
    assert client.post('/api/v1/snapshots',json=payload(age=-1000),headers=auth(WRITE)).status_code==422

def test_bad_data(client):
    bad=payload();bad['windows'][0]['used_percent']=101
    assert client.post('/api/v1/snapshots',json=bad,headers=auth(WRITE)).status_code==422
    bad=payload();bad['provider']='chatgpt'
    assert client.post('/api/v1/snapshots',json=bad,headers=auth(WRITE)).status_code==422
    bad=payload();bad['mode']='demo'
    assert client.post('/api/v1/snapshots',json=bad,headers=auth(WRITE)).status_code==422
    bad=payload();bad['observed_at']='2026-01-01T00:00:00'
    assert client.post('/api/v1/snapshots',json=bad,headers=auth(WRITE)).status_code==422
    bad=payload();bad['access_token']='never store raw credentials'
    assert client.post('/api/v1/snapshots',json=bad,headers=auth(WRITE)).status_code==422

def test_body_limit(client):
    assert client.post('/api/v1/snapshots',content=b'x'*33000,headers=auth(WRITE)).status_code==413
    def chunks():
        yield b'x'*20000
        yield b'x'*20000
    assert client.post('/api/v1/snapshots',content=chunks(),headers=auth(WRITE)).status_code==413

def test_error_does_not_present_old_success(client):
    client.post('/api/v1/snapshots',json=payload(),headers=auth(WRITE))
    bad=payload();bad.update(status='error',windows=[],reason='offline')
    assert client.post('/api/v1/snapshots',json=bad,headers=auth(WRITE)).status_code==200
    p=client.get('/api/v1/device',headers=auth(READ)).json()['providers'][0]
    assert p['status']=='error' and p['windows']==[]

def test_persistence(tmp_path):
    path=tmp_path/'persist.sqlite'
    TestClient(create_app(path,READ,WRITE)).post('/api/v1/snapshots',json=payload(),headers=auth(WRITE))
    assert TestClient(create_app(path,READ,WRITE)).get('/api/v1/device',headers=auth(READ)).json()['providers'][0]['status']=='ok'

def test_expired_reset_and_headers(client):
    v=payload();v['windows'][0]['resets_at']=(now()-timedelta(seconds=1)).isoformat()
    client.post('/api/v1/snapshots',json=v,headers=auth(WRITE))
    r=client.get('/api/v1/device',headers=auth(READ))
    assert r.json()['providers'][0]['stale']
    assert r.headers['cache-control']=='no-store'
