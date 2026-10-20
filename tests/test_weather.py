import asyncio
from datetime import datetime,timezone
import json,sqlite3
import httpx
from fastapi.testclient import TestClient
from pixora.information_connectors import WeatherCollector
from pixora.server import create_app
from pixora.devices import provision

def weather():
 epoch=int(datetime.now(timezone.utc).timestamp())
 return dict(current=dict(time=epoch,temperature_2m=21.5,apparent_temperature=20,weather_code=3),current_units={'temperature_2m':'°C'},hourly_units={'temperature_2m':'°C'},daily={'temperature_2m_max':[24],'temperature_2m_min':[18],'precipitation_probability_max':[30]},hourly={'time':[epoch+3600,epoch+7200,epoch+10800],'temperature_2m':[22,23,22],'weather_code':[3,3,61]})

def test_weather_data_failure_and_scope(monkeypatch,tmp_path):
 import pixora.information_connectors as module
 monkeypatch.setenv('PIXORA_WEATHER_LATITUDE','31.23');monkeypatch.setenv('PIXORA_WEATHER_LONGITUDE','121.47')
 def handler(request):
  assert request.url.host=='api.open-meteo.com' and 'authorization' not in request.headers
  assert request.url.params['timezone']=='Asia/Shanghai'
  return httpx.Response(200,json=weather())
 monkeypatch.setattr(module,'client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(handler)))
 item=asyncio.run(WeatherCollector().collect())[0];assert item.status=='ok' and len(item.metrics)==16
 assert item.metrics[0].value==21.5 and item.entries[0].url=='https://open-meteo.com/'
 db=tmp_path/'db';client=TestClient(create_app(db,'r'*40,'w'*40))
 with sqlite3.connect(db) as c:old=provision(c,'old',['codex','rss'],['real']);new=provision(c,'weather',['weather'],['real'])
 auth=lambda token:{'Authorization':'Bearer '+token}
 assert client.post('/api/v2/observations',json=item.model_dump(mode='json'),headers=auth('w'*40)).status_code==200
 assert client.get('/api/v2/observations',headers=auth(old['token'])).json()['observations']==[]
 assert client.get('/api/v2/history?provider=weather',headers=auth(old['token'])).status_code==403
 assert client.get('/api/v2/observations',headers=auth(new['token'])).json()['observations'][0]['provider']=='weather'
 bad=weather();bad['current']['time']-=86400
 monkeypatch.setattr(module,'client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=bad))))
 failed=asyncio.run(WeatherCollector().collect())[0];assert failed.status=='error' and failed.metrics==[]
 monkeypatch.setenv('PIXORA_WEATHER_LATITUDE','NaN');assert asyncio.run(WeatherCollector().collect())[0].status=='error'
 monkeypatch.delenv('PIXORA_WEATHER_LATITUDE');assert asyncio.run(WeatherCollector().collect())[0].status=='unavailable'
