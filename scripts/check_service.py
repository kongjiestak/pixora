"""Check a running service after demo collection; no credentials printed."""
import os
import httpx
with httpx.Client(base_url=os.getenv('PIXORA_SERVER','http://127.0.0.1:8000'),trust_env=False,timeout=10) as c:
    read={'Authorization':'Bearer '+os.environ['PIXORA_READ_TOKEN']}
    write={'Authorization':'Bearer '+os.environ['PIXORA_WRITE_TOKEN']}
    assert c.get('/healthz').json()['status']=='ok'
    assert c.get('/api/v1/device').status_code==401
    assert c.get('/api/v1/device',headers=write).status_code==401
    assert c.get('/api/v1/device',headers=read).json()['providers'][1]['status']=='unavailable'
    demo=c.get('/api/v1/device?mode=demo',headers=read).json()
    assert all(p['source']=='demo' and p['mode']=='demo' and p['collected_at'] for p in demo['providers'])
    for path in ('/','/sw.js','/manifest.webmanifest','/icon-192.png','/icon-512.png'):assert c.get(path).status_code==200
    assert 'Pixora' in c.get('/').text
    print('PASS: live service, demo roundtrip, real/demo separation, token boundaries and PWA assets')

# Exercise scoped authorization against the actual running process/database.
import sqlite3
from pixora.devices import provision
with sqlite3.connect(os.getenv('PIXORA_DB', 'data/pixora.sqlite')) as conn:
    device = provision(conn, 'ci-demo-screen', ['codex'], ['demo'])
with httpx.Client(base_url=os.getenv('PIXORA_SERVER','http://127.0.0.1:8000'), trust_env=False, timeout=10) as c:
    scoped = {'Authorization': 'Bearer '+device['token']}
    r = c.get('/api/v1/device?mode=demo', headers=scoped)
    assert r.status_code == 200 and [p['provider'] for p in r.json()['providers']] == ['codex']
    assert c.get('/api/v1/device?mode=real', headers=scoped).status_code == 403
    assert c.post('/api/v1/snapshots', json={}, headers=scoped).status_code == 401
    with sqlite3.connect(os.getenv('PIXORA_DB', 'data/pixora.sqlite')) as conn:
        conn.execute('UPDATE devices SET revoked=1 WHERE id=?', (device['id'],))
    assert c.get('/api/v1/device?mode=demo', headers=scoped).status_code == 401
print('PASS: running service enforces provider/mode scope, read-only boundary and immediate revocation')
