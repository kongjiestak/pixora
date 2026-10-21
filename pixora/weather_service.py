"""Bounded, authenticated on-demand city weather; upstream hosts are fixed."""
import asyncio
from collections import OrderedDict,deque
import json,time
import httpx
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from pixora.information_connectors import client,read_url,WeatherCollector

class WeatherUnavailable(Exception):pass
class WeatherBusy(Exception):pass

def place(raw):
    identifier=raw['id'];lat=raw['latitude'];lon=raw['longitude'];zone=raw['timezone']
    if not isinstance(raw['name'],str) or not raw['name'].strip():raise ValueError('invalid place name')
    if type(identifier) is not int or not 1<=identifier<=2147483647:raise ValueError('invalid place id')
    if type(lat) not in (int,float) or type(lon) not in (int,float) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('invalid coordinates')
    ZoneInfo(zone)
    return dict(id=identifier,name=str(raw['name'])[:100],admin1=str(raw.get('admin1',''))[:100],country=str(raw.get('country',''))[:100],timezone=zone,latitude=lat,longitude=lon)

class WeatherService:
    def __init__(self):
        self.cache=OrderedDict();self.pending={};self.rates=OrderedDict()
    def rate(self,device,kind):
        key=(device,kind);stamp=time.monotonic();q=self.rates.pop(key,deque())
        while q and q[0]<stamp-60:q.popleft()
        self.rates[key]=q
        while len(self.rates)>512:self.rates.popitem(last=False)
        if len(q)>=(10 if kind=='search' else 6):raise WeatherBusy()
        q.append(stamp)
    async def cached(self,key,ttl,loader):
        cached=self.cache.pop(key,None)
        if cached and cached[0]>time.monotonic():
            self.cache[key]=cached;return cached[1]
        if key not in self.pending:
            if len(self.pending)>=4:raise WeatherBusy()
            async def produce():
                try:
                    value=await loader();self.cache[key]=(time.monotonic()+ttl,value)
                    while len(self.cache)>256:self.cache.popitem(last=False)
                    return value
                finally:self.pending.pop(key,None)
            self.pending[key]=asyncio.create_task(produce())
            self.pending[key].add_done_callback(lambda task:None if task.cancelled() else task.exception())
        return await asyncio.shield(self.pending[key])
    async def search(self,name,language):
        async def load():
            try:
                async with asyncio.timeout(20),client() as c:
                    raw=json.loads(await read_url(c,'https://geocoding-api.open-meteo.com/v1/search?'+urlencode(dict(name=name,count=8,language=language,format='json'))))
                return [place(p) for p in raw.get('results',[])[:8]]
            except (httpx.HTTPError,OSError,ValueError,KeyError,TypeError,TimeoutError,AttributeError) as e:raise WeatherUnavailable() from e
        return await self.cached(('search',name,language),600,load)
    async def location(self,identifier,language):
        async def load():
            try:
                async with asyncio.timeout(20),client() as c:
                    raw=json.loads(await read_url(c,'https://geocoding-api.open-meteo.com/v1/get?'+urlencode(dict(id=identifier,language=language))))
                result=place(raw)
                if result['id']!=identifier:raise ValueError('place id mismatch')
                return result
            except (httpx.HTTPError,OSError,ValueError,KeyError,TypeError,TimeoutError,AttributeError) as e:raise WeatherUnavailable() from e
        return await self.cached(('location',identifier,language),86400,load)
    async def weather(self,identifier,language,device=None):
        async def load():
            self.rate(device,'weather')
            location=await self.location(identifier,language)
            label=' · '.join(dict.fromkeys(x for x in [location['name'],location['admin1'],location['country']] if x))[:240]
            item=(await WeatherCollector(latitude=location['latitude'],longitude=location['longitude'],label=label,entity='place-'+str(identifier),timezone=location['timezone']).collect())[0]
            if item.status!='ok':raise WeatherUnavailable()
            return item.model_dump(mode='json')
        return await self.cached(('weather',identifier,language),600,load)
