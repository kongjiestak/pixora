"""Read-only, administrator-configured public feeds and local task files.
No remote configuration endpoint, credential forwarding or HTML rendering.
"""
import asyncio
from datetime import timedelta
import ipaddress
import json
from pathlib import Path
import re
import socket
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import httpx
from pixora.observations import Observation,Metric,Entry
from pixora.models import now
from pixora.settings import setting

MAX_BYTES=1024*1024

def base(provider,category,source,entity='default'):
 t=now()
 return dict(provider=provider,connector_id=provider+'-readonly',entity_id=entity,category=category,source=source,mode='real',collected_at=t,expires_at=t+timedelta(minutes=30))

async def public_url(url):
 p=urlsplit(url)
 if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443) or p.fragment:
  raise ValueError('public HTTPS URL required')
 addresses=await asyncio.to_thread(socket.getaddrinfo,p.hostname,443,type=socket.SOCK_STREAM)
 if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('public host required')
 return url

async def read_url(client,url):
 async with client.stream('GET',url) as r:
  r.raise_for_status();chunks=[];size=0
  async for chunk in r.aiter_bytes():
   size+=len(chunk)
   if size>MAX_BYTES:raise ValueError('response too large')
   chunks.append(chunk)
  return b''.join(chunks)

def client():
 return httpx.AsyncClient(timeout=15,follow_redirects=False,trust_env=False,headers={'User-Agent':'Pixora/0.3','Accept':'application/json, application/atom+xml, application/rss+xml, application/xml'})

def parse_feed(raw):
 if len(raw)>MAX_BYTES or b'\x00' in raw:raise ValueError('unsafe XML')
 class NoDTD(ET.TreeBuilder):
  def doctype(self,name,pubid,system):raise ValueError('DTD not allowed')
 root=ET.fromstring(raw,parser=ET.XMLParser(target=NoDTD()))
 tag=lambda el:el.tag.rsplit('}',1)[-1]
 if tag(root) not in ('rss','feed','RDF'):raise ValueError('not RSS/Atom')
 result=[]
 for item in root.iter():
  if tag(item) not in ('item','entry'):continue
  fields={tag(c):c for c in item}
  title=' '.join(''.join(fields['title'].itertext()).split())[:240] if 'title' in fields else ''
  if not title:continue
  link=None
  for child in item:
   if tag(child)=='link' and child.get('rel','alternate')=='alternate':
    candidate=child.get('href') or child.text
    if candidate:
     try:link=Entry(title=title,url=candidate.strip()).url;break
     except ValueError:pass
  # Feed HTML is displayed as inert text, never injected into the DOM.
  result.append(Entry(title=title,url=link))
  if len(result)==10:break
 return result

class RSSCollector:
 async def collect(self):
  b=base('rss','personal','rss-https')
  url=setting('RSS_URL','')
  if not url:return [Observation(**b,status='unavailable')]
  try:
   await public_url(url)
   async with asyncio.timeout(30):
    async with client() as c:entries=parse_feed(await read_url(c,url))
   return [Observation(**b,status='ok',metrics=[Metric(key='feed.items',value=len(entries),unit='items')],entries=entries)]
  except (httpx.HTTPError,OSError,TimeoutError,ValueError,ET.ParseError):return [Observation(**b,status='error')]

class GitHubCollector:
 async def collect(self):
  b=base('github','developer','github-rest')
  repo=setting('GITHUB_REPOSITORY','')
  if not repo:return [Observation(**b,status='unavailable')]
  try:
   if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9_.-]{1,100}',repo):raise ValueError('invalid repo')
   async with asyncio.timeout(40),client() as c:
    data=json.loads(await read_url(c,'https://api.github.com/repos/'+repo))
    runs=json.loads(await read_url(c,'https://api.github.com/repos/'+repo+'/actions/runs?per_page=5'))
   metrics=[Metric(key='github.stars',value=data['stargazers_count'],unit='count'),Metric(key='github.open_items',value=data['open_issues_count'],unit='count')]
   entries=[Entry(title=repo,url='https://github.com/'+repo)]
   for run in runs['workflow_runs'][:5]:
    entries.append(Entry(title=str(run.get('name') or 'Workflow')[:240],detail=str(run.get('conclusion') or run['status'])[:240],url=run['html_url']))
   return [Observation(**b,status='ok',metrics=metrics,entries=entries)]
  except (httpx.HTTPError,OSError,TimeoutError,ValueError,KeyError,TypeError):return [Observation(**b,status='error')]

class TasksCollector:
 async def collect(self):
  b=base('tasks','personal','local-json')
  path=setting('TASKS_FILE','')
  if not path:return [Observation(**b,status='unavailable')]
  try:
   # The file path is trusted local admin config, never supplied by a web visitor.
   with Path(path).open('rb') as f:raw=f.read(MAX_BYTES+1)
   if len(raw)>MAX_BYTES:raise ValueError('file too large')
   data=json.loads(raw)
   if not isinstance(data,list) or len(data)>200:raise ValueError('max 200 tasks')
   for item in data:
    if not isinstance(item,dict) or set(item)-{'title','done'} or type(item.get('done')) is not bool:raise ValueError('invalid task')
    Entry(title=item['title'])
   pending=[i for i in data if not i['done']]
   entries=[Entry(title=i['title'],detail='pending') for i in pending[:10]]
   return [Observation(**b,status='ok',metrics=[Metric(key='tasks.pending',value=len(pending),unit='count'),Metric(key='tasks.completed',value=len(data)-len(pending),unit='count')],entries=entries)]
  except (OSError,ValueError,KeyError,TypeError):return [Observation(**b,status='error')]

class InformationCollector:
 async def collect(self):
  items=[]
  for plugin in [GitHubCollector,RSSCollector,WeatherCollector]:items.extend(await plugin().collect())
  return items

class WeatherCollector:
 async def collect(self):
  b=base('weather','personal','open-meteo',setting('WEATHER_ENTITY','city'))
  lat=setting('WEATHER_LATITUDE','');lon=setting('WEATHER_LONGITUDE','')
  if not lat or not lon:return [Observation(**b,status='unavailable')]
  try:
   latitude=float(lat);longitude=float(lon)
   if not -90<=latitude<=90 or not -180<=longitude<=180:raise ValueError('invalid coordinates')
   from datetime import datetime,timezone
   from urllib.parse import urlencode
   params=dict(latitude=latitude,longitude=longitude,current='temperature_2m,apparent_temperature,weather_code',daily='temperature_2m_max,temperature_2m_min,precipitation_probability_max',hourly='temperature_2m,weather_code',forecast_days=2,timezone='Asia/Shanghai',timeformat='unixtime')
   async with asyncio.timeout(30),client() as c:data=json.loads(await read_url(c,'https://api.open-meteo.com/v1/forecast?'+urlencode(params)))
   cur=data['current'];daily=data['daily'];hourly=data['hourly']
   if data['current_units']['temperature_2m']!='°C' or data['hourly_units']['temperature_2m']!='°C':raise ValueError('unexpected units')
   # Use upstream timestamps; a fresh HTTP fetch must not make an old model current.
   epoch=cur['time'];sample=datetime.fromtimestamp(epoch,timezone.utc)
   if sample>b['collected_at']+timedelta(minutes=5) or sample<b['collected_at']-timedelta(hours=2):raise ValueError('old or future model data')
   metrics=[Metric(key='weather.temperature',value=cur['temperature_2m'],unit='celsius'),Metric(key='weather.feels',value=cur['apparent_temperature'],unit='celsius'),Metric(key='weather.code',value=cur['weather_code'],unit='wmo-code'),Metric(key='weather.model_time',value=epoch,unit='unix-seconds'),Metric(key='weather.high',value=daily['temperature_2m_max'][0],unit='celsius'),Metric(key='weather.low',value=daily['temperature_2m_min'][0],unit='celsius'),Metric(key='weather.rain',value=daily['precipitation_probability_max'][0],unit='percent')]
   indices=[i for i,t in enumerate(hourly['time']) if t>epoch][:3]
   for j,i in enumerate(indices):
    metrics.extend([Metric(key=f'weather.hour.{j}.time',value=hourly['time'][i],unit='unix-seconds'),Metric(key=f'weather.hour.{j}.temperature',value=hourly['temperature_2m'][i],unit='celsius'),Metric(key=f'weather.hour.{j}.code',value=hourly['weather_code'][i],unit='wmo-code')])
   if cur['temperature_2m'] is None:raise ValueError('missing current temperature')
   return [Observation(**b,status='ok',metrics=metrics,entries=[Entry(title=setting('WEATHER_LABEL','City'),detail='Asia/Shanghai',url='https://open-meteo.com/')])]
  except (httpx.HTTPError,OSError,TimeoutError,ValueError,KeyError,IndexError,TypeError,OverflowError):return [Observation(**b,status='error')]
