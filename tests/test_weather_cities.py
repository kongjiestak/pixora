import asyncio,json,sqlite3
import httpx,pytest
from fastapi.testclient import TestClient
from pixora.server import create_app
from pixora.devices import provision
from pixora.device_profiles import configure
from pixora.weather_service import WeatherService,WeatherBusy
from test_weather import weather

HOUSTON={'id':4699066,'name':'Houston','latitude':29.76328,'longitude':-95.36327,'timezone':'America/Chicago','admin1':'Texas','country':'United States'}

def setup(tmp_path,monkeypatch):
    import pixora.weather_service as service
    import pixora.information_connectors as connectors
    calls=[]
    def handle(req):
        calls.append(req)
        assert 'authorization' not in req.headers and 'cookie' not in req.headers
        if req.url.host=='geocoding-api.open-meteo.com':
            return httpx.Response(200,json={'results':[HOUSTON]} if req.url.path.endswith('search') else {**HOUSTON,'id':int(req.url.params['id'])})
        assert req.url.host=='api.open-meteo.com' and req.url.params['timezone']=='America/Chicago'
        assert float(req.url.params['longitude'])<0
        return httpx.Response(200,json=weather())
    factory=lambda:httpx.AsyncClient(transport=httpx.MockTransport(handle),follow_redirects=False,trust_env=False)
    monkeypatch.setattr(service,'client',factory);monkeypatch.setattr(connectors,'client',factory)
    db=tmp_path/'cities';c=TestClient(create_app(db,'r'*40,'w'*40))
    with sqlite3.connect(db) as conn:
        d=provision(conn,'weather',['weather'],['real']);old=provision(conn,'old',['codex'],['real'])
    return db,c,d,old,calls


def test_city_search_weather_timezone_cache_and_projections(tmp_path,monkeypatch):
    db,c,d,old,calls=setup(tmp_path,monkeypatch);auth={'Authorization':'Bearer '+d['token']}
    assert c.get('/api/v2/weather/locations?name=Houston').status_code==401
    assert c.get('/api/v2/weather/locations?name=Houston',headers={'Authorization':'Bearer '+old['token']}).status_code==403
    locations=c.get('/api/v2/weather/locations?name=Houston&language=en',headers=auth).json()['locations']
    assert locations[0]['id']==4699066 and locations[0]['timezone']=='America/Chicago'
    url='/api/v2/weather/4699066';first=c.get(url,headers=auth)
    assert first.status_code==200
    item=first.json()['observation'];assert item['entries'][0]['detail']=='America/Chicago' and item['entity_id']=='place-4699066'
    n=len(calls);again=c.get(url,headers=auth);assert len(calls)==n
    assert again.json()['observation']['collected_at']==item['collected_at']
    with sqlite3.connect(db) as conn:
        configure(conn,d['id'],policy={'rules':{'weather':{'entities':['place-4699066'],'metrics':['weather.temperature'],'entries':'none'}}})
    response=c.get(url,headers=auth)
    assert [m['key'] for m in response.json()['observation']['metrics']]==['weather.temperature']
    assert response.json()['observation']['entries']==[] and 'Houston' not in response.text
    n=len(calls);assert c.get('/api/v2/weather/1796236',headers=auth).status_code==403;assert len(calls)==n
    assert c.patch('/api/v2/device-config',headers=auth,json={'weather_location':4699066}).status_code==405


def test_city_public_only_and_bad_parameters_do_not_fetch(tmp_path,monkeypatch):
    db,c,d,old,calls=setup(tmp_path,monkeypatch);auth={'Authorization':'Bearer '+d['token']}
    for path in ['/api/v2/weather/0','/api/v2/weather/2147483648','/api/v2/weather/locations?name=x','/api/v2/weather/locations?name=xx&language=unsafe']:
        assert c.get(path,headers=auth).status_code==422
    assert not calls
    with sqlite3.connect(db) as conn:configure(conn,d['id'],policy={'public_only':True})
    assert c.get('/api/v2/weather/4699066',headers=auth).status_code==403
    assert c.get('/api/v2/weather/locations?name=Houston',headers=auth).status_code==403
    assert not calls


def test_city_network_failure_and_rate_limit(tmp_path,monkeypatch):
    db,c,d,old,calls=setup(tmp_path,monkeypatch);auth={'Authorization':'Bearer '+d['token']}
    for _ in range(10):assert c.get('/api/v2/weather/4699066',headers=auth).status_code==200
    for identifier in range(4699067,4699072):assert c.get('/api/v2/weather/'+str(identifier),headers=auth).status_code==200
    assert c.get('/api/v2/weather/4699072',headers=auth).status_code==429
    import pixora.weather_service as service
    monkeypatch.setattr(service,'client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(503))))
    assert c.get('/api/v2/weather/locations?name=Other',headers=auth).status_code==502


def test_weather_cache_coalesces_and_bounds_state():
    async def check():
        s=WeatherService();gate=asyncio.Event();count=0
        async def loader():
            nonlocal count
            count+=1;await gate.wait();return 'ok'
        tasks=[asyncio.create_task(s.cached('same',600,loader)) for _ in range(8)]
        await asyncio.sleep(0);await asyncio.sleep(0);gate.set()
        assert await asyncio.gather(*tasks)==['ok']*8 and count==1
        async def value():return 'small'
        for i in range(300):await s.cached(i,600,value)
        assert len(s.cache)==256
    asyncio.run(check())
