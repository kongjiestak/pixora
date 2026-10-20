import sqlite3
from datetime import timedelta, datetime
import pytest
from fastapi.testclient import TestClient
from pixora.server import create_app
from pixora.devices import provision
from pixora.models import now
from test_api import READ, WRITE, auth, payload

ORIGIN = {'Origin': 'https://testserver'}
COOKIE = '__Host-pixora_session'

def setup(tmp_path, days=90):
    path = tmp_path/'sessions.sqlite'
    client = TestClient(create_app(path, READ, WRITE), base_url='https://testserver')
    with sqlite3.connect(path) as conn:
        device = provision(conn, 'phone', ['codex'], ['real'], days)
    return path, client, device

def login(client, device):
    return client.post('/api/v1/session', headers={**ORIGIN, **auth(device['token'])})

def test_cookie_restores_read_only_scope_across_clients(tmp_path):
    path, client, device = setup(tmp_path)
    response = login(client, device)
    assert response.status_code == 200
    cookie = response.headers['set-cookie']
    assert all(x in cookie for x in ['HttpOnly', 'Secure', 'SameSite=strict', 'Path=/'])
    assert 'Domain=' not in cookie and 'no-store' in response.headers['cache-control']
    assert device['token'] not in response.text
    restored = TestClient(client.app, base_url='https://testserver')
    restored.cookies.update(client.cookies)
    assert restored.get('/api/v1/session').status_code == 200
    response = restored.get('/api/v1/device')
    assert [p['provider'] for p in response.json()['providers']] == ['codex']
    assert restored.get('/api/v1/device?mode=demo').status_code == 403
    assert restored.post('/api/v1/snapshots', json=payload()).status_code == 401
    with sqlite3.connect(path) as conn:
        stored = str(conn.execute('SELECT * FROM device_sessions').fetchall())
    assert client.cookies.get(COOKIE) not in stored
    assert restored.get('/api/v1/device', headers=auth('wrong')).status_code == 401

@pytest.mark.parametrize('action', ['revoke', 'device_expiry', 'session_expiry', 'logout'])
def test_live_revocation_expiry_and_logout(tmp_path, action):
    path, client, device = setup(tmp_path)
    login(client, device)
    copied = client.cookies.get(COOKIE)
    with sqlite3.connect(path) as conn:
        expired = (now()-timedelta(seconds=1)).isoformat()
        if action == 'revoke': conn.execute('UPDATE devices SET revoked=1')
        if action == 'device_expiry': conn.execute('UPDATE devices SET expires_at=?', (expired,))
        if action == 'session_expiry': conn.execute('UPDATE device_sessions SET expires_at=?', (expired,))
    if action == 'logout':
        assert client.delete('/api/v1/session', headers=ORIGIN).status_code == 204
        client.cookies.set(COOKIE, copied)
    assert client.get('/api/v1/device').status_code == 401
    assert client.get('/api/v1/session').status_code == 401

@pytest.mark.parametrize('origin', [None, 'https://evil.example', 'http://testserver'])
def test_csrf_blocks_session_changes(tmp_path, origin):
    _, client, device = setup(tmp_path)
    headers = auth(device['token'])
    if origin: headers['Origin'] = origin
    assert client.post('/api/v1/session', headers=headers).status_code == 403
    login(client, device)
    assert client.delete('/api/v1/session', headers={'Origin': origin} if origin else {}).status_code == 403
    assert client.get('/api/v1/device').status_code == 200

@pytest.mark.parametrize('token', [READ, WRITE, 'invalid'])
def test_global_and_invalid_tokens_cannot_create_sessions(tmp_path, token):
    _, client, _ = setup(tmp_path)
    assert client.post('/api/v1/session', headers={**ORIGIN, **auth(token)}).status_code == 401

def test_expiry_cap_and_session_bound(tmp_path):
    path, client, device = setup(tmp_path, days=1)
    response = login(client, device)
    assert datetime.fromisoformat(response.json()['expires_at']) <= datetime.fromisoformat(device['expires_at'])
    for _ in range(22):
        client.cookies.clear()
        assert login(client, device).status_code == 200
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM device_sessions').fetchone()[0] == 20

def test_long_device_authorization_still_limits_session_to_30_days(tmp_path):
    _, client, device = setup(tmp_path, days=90)
    response = login(client, device)
    assert now()+timedelta(days=29) < datetime.fromisoformat(response.json()['expires_at']) <= now()+timedelta(days=30)
