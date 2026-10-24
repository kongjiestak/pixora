import json
import os
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from pixora.local import prepare, pairing_page
from pixora.server import create_app
from pixora.devices import provision


def test_private_isolated_setup_and_revoked_pairing(tmp_path):
    directory = tmp_path/'local'
    first = prepare(directory)
    assert first == prepare(directory)
    assert first['read'] != first['write'] != first['screen']
    if os.name != 'nt':
        assert directory.stat().st_mode & 0o777 == 0o700
        assert (directory/'local.json').stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(directory/'pixora.sqlite') as conn:
        conn.execute('UPDATE devices SET revoked=1')
    second = prepare(directory)
    assert second['screen'] != first['screen']
    assert second['write'] == first['write']
    page = pairing_page(directory, 'http://127.0.0.1:8024', second['screen'])
    assert '<svg' in page.read_text()
    assert '#token=' in page.read_text()
    assert first['write'] not in page.read_text()
    assert page.stat().st_mode & 0o777 == 0o600 or os.name == 'nt'


def test_activity_default_disabled_and_read_only_scopes(tmp_path, monkeypatch):
    value = prepare(tmp_path)
    app = create_app(tmp_path/'pixora.sqlite', value['read'], value['write'], web_dir=tmp_path/'none')
    with TestClient(app) as client:
        auth = {'Authorization':'Bearer '+value['screen']}
        assert client.get('/api/v1/activity',headers=auth).status_code == 404
        monkeypatch.setenv('PIXORA_LOCAL_ACTIVITY','true')
        monkeypatch.setattr('pixora.activity.observe_activity',lambda:dict(source='codex-local-events',state='unknown',observed_at=100,expires_at=115))
        assert client.get('/api/v1/activity').status_code == 401
        assert client.get('/api/v1/activity',headers={'Authorization':'Bearer '+value['write']}).status_code == 401
        assert client.get('/api/v1/activity',headers=auth).json()['state'] == 'unknown'
        assert client.post('/api/v1/snapshots',headers=auth,json={}).status_code == 401
        with sqlite3.connect(tmp_path/'pixora.sqlite') as conn:
            limited=provision(conn,'system only',['system'],['real'])
            demo=provision(conn,'demo only',['codex'],['demo'])
        for device in [limited,demo]:
            assert client.get('/api/v1/activity',headers={'Authorization':'Bearer '+device['token']}).status_code == 403
        with sqlite3.connect(tmp_path/'pixora.sqlite') as conn:
            conn.execute('UPDATE devices SET revoked=1')
        assert client.get('/api/v1/activity',headers=auth).status_code == 401


def test_activity_adapter_matches_hardware_contract():
    root=Path(__file__).parents[1]
    assert (root/'pixora/activity.py').read_text() == (root/'clients/codex_activity.py').read_text()


def test_gui_codex_fallback_and_network_selection(monkeypatch):
    from pixora.local import codex_executable, discover_lan
    monkeypatch.delenv('PIXORA_CODEX_BIN', raising=False)
    monkeypatch.delenv('APM_CODEX_BIN', raising=False)
    monkeypatch.setattr('pixora.local.shutil.which',lambda _:None)
    monkeypatch.setattr('pixora.local.sys.platform','darwin')
    monkeypatch.setattr('pixora.local.Path.is_file',lambda _:True)
    monkeypatch.setattr('pixora.local.os.access',lambda *_:True)
    assert codex_executable().startswith('/Applications/ChatGPT.app/')
    monkeypatch.setenv('PIXORA_CODEX_BIN','explicit-codex')
    assert codex_executable() == 'explicit-codex'
    class Socket:
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def connect(self,*_):pass
        def getsockname(self):return ('172.20.10.2',12345)
    monkeypatch.setattr('pixora.local.socket.socket',lambda *_:Socket())
    assert discover_lan() == '172.20.10.2'


def test_weather_migration_is_limited_to_launcher_owned_screen(tmp_path):
    from pixora.device_profiles import read_profile
    value=prepare(tmp_path)
    with sqlite3.connect(tmp_path/'pixora.sqlite') as conn:
        other=provision(conn,'other screen',['codex'],['real'])
        conn.execute('UPDATE devices SET providers=? WHERE token_hash=?', (json.dumps(['codex']), __import__('pixora.devices',fromlist=['token_hash']).token_hash(value['screen'])))
    assert prepare(tmp_path)['screen']==value['screen']
    with sqlite3.connect(tmp_path/'pixora.sqlite') as conn:
        rows=conn.execute('SELECT id,providers FROM devices').fetchall()
        assert dict(rows)[other['id']]==json.dumps(['codex'])
        owned=[row for row in rows if row[0]!=other['id']][0]
        assert set(json.loads(owned[1]))=={'codex','weather'}
        assert read_profile(conn,owned[0])[0].weather_location==1796236
