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
