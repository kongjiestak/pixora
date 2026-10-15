import json
import sqlite3
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from pixora.devices import provision, main, token_hash
from pixora.models import now
from pixora.server import create_app
from test_api import READ, WRITE, auth, payload


def setup(tmp_path, modes=('demo',), providers=('chatgpt',)):
    path = tmp_path/'devices.sqlite'
    client = TestClient(create_app(path, READ, WRITE))
    with sqlite3.connect(path) as conn:
        device = provision(conn, 'public screen', providers, modes)
    return path, client, device


def test_server_filters_before_returning(tmp_path):
    path, client, device = setup(tmp_path)
    client.post('/api/v1/snapshots', json=payload('demo'), headers=auth(WRITE))
    client.post('/api/v1/snapshots', json=payload(), headers=auth(WRITE))
    response = client.get('/api/v1/device?mode=demo', headers=auth(device['token']))
    assert response.status_code == 200
    assert response.json()['device_id'] == device['id']
    assert [p['provider'] for p in response.json()['providers']] == ['chatgpt']
    assert 'codex-app-server' not in response.text and 'codex/primary' not in response.text
    assert client.get('/api/v1/device?mode=real', headers=auth(device['token'])).status_code == 403
    assert client.post('/api/v1/snapshots', json=payload(), headers=auth(device['token'])).status_code == 401
    with sqlite3.connect(path) as conn:
        stored = str(conn.execute('SELECT * FROM devices').fetchall())
    assert device['token'] not in stored and token_hash(device['token']) in stored


@pytest.mark.parametrize('action', ['revoke', 'expire'])
def test_revocation_and_expiry_are_live(tmp_path, action):
    path, client, device = setup(tmp_path, ('real',), ('codex',))
    assert client.get('/api/v1/device', headers=auth(device['token'])).status_code == 200
    with sqlite3.connect(path) as conn:
        if action == 'revoke':
            conn.execute('UPDATE devices SET revoked=1 WHERE id=?', (device['id'],))
        else:
            conn.execute('UPDATE devices SET expires_at=? WHERE id=?', ((now()-timedelta(seconds=1)).isoformat(), device['id']))
    response = client.get('/api/v1/device', headers=auth(device['token']))
    assert response.status_code == 401 and response.headers['cache-control'] == 'no-store'
    assert client.get('/api/v1/device', headers=auth(READ)).status_code == 200


def test_legacy_can_be_disabled_without_blocking_devices(tmp_path, monkeypatch):
    _, client, device = setup(tmp_path, ('real',), ('codex',))
    monkeypatch.setenv('PIXORA_ALLOW_LEGACY_READ_TOKEN', 'false')
    assert client.get('/api/v1/device', headers=auth(READ)).status_code == 401
    assert client.get('/api/v1/device', headers=auth(device['token'])).status_code == 200
    assert client.post('/api/v1/snapshots', json=payload(), headers=auth(WRITE)).status_code == 200


def test_device_cli_lifecycle(tmp_path, monkeypatch, capsys):
    path = str(tmp_path/'cli.sqlite')
    def run(*args):
        monkeypatch.setattr('sys.argv', ['pixora-device', '--db', path, *args])
        main()
        return json.loads(capsys.readouterr().out)
    device = run('create', '--name', 'desk', '--provider', 'codex')
    rows = run('list')
    assert device['token'] not in json.dumps(rows)
    assert json.loads(rows[0]['modes']) == ['demo']
    run('revoke', device['id'])
    assert run('list')[0]['revoked'] == 1
    with pytest.raises(SystemExit):
        run('revoke', 'missing')


@pytest.mark.parametrize('providers,modes,days', [([],['demo'],30),(['other'],['demo'],30),(['codex'],[],30),(['codex'],['demo'],0)])
def test_invalid_policy_rejected(tmp_path, providers, modes, days):
    path, _, _ = setup(tmp_path)
    with sqlite3.connect(path) as conn, pytest.raises(ValueError):
        provision(conn, 'desk', providers, modes, days)
