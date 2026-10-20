import asyncio
import json
import sqlite3
import httpx
import pytest
from fastapi.testclient import TestClient
from pixora.information_connectors import GitHubCollector,RSSCollector,TasksCollector,parse_feed,public_url
from pixora.observations import Observation,Entry
from pixora.server import create_app
from pixora.devices import provision

READ='r'*40;WRITE='w'*40

def test_rss_atom_and_untrusted_xml():
 rss=b'<rss><channel><item><title>Example</title><link>https://example.com/post</link></item><item><title>Unsafe</title><link>javascript:alert(1)</link></item></channel></rss>'
 items=parse_feed(rss);assert items[0].url=='https://example.com/post' and items[1].url is None
 atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom</title><link href="https://example.com/atom"/></entry></feed>'
 assert parse_feed(atom)[0].title=='Atom'
 # Literal DOCTYPE inside article CDATA is inert content, not an XML DTD.
 assert parse_feed(b'<rss><channel><item><title>Code</title><description><![CDATA[<!DOCTYPE html>]]></description></item></channel></rss>')[0].title=='Code'
 for raw in [b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss/>',b'<html/>',b'\x00<rss/>',b'x'*(1024*1024+1)]:
  with pytest.raises(ValueError):parse_feed(raw)
 for url in ['javascript:alert(1)','http://example.com','https://user:pass@example.com','https://example.com/\n']:
  with pytest.raises(ValueError):Entry(title='bad',url=url)

def test_public_url_rejects_private_addresses_and_redirect_credentials():
 for url in ['http://example.com','https://127.0.0.1','https://[::1]','https://user:pass@example.com','https://example.com:444']:
  with pytest.raises(ValueError):asyncio.run(public_url(url))

def test_tasks_file_counts_and_failure(tmp_path,monkeypatch):
 p=tmp_path/'tasks.json';monkeypatch.setenv('PIXORA_TASKS_FILE',str(p))
 p.write_text(json.dumps([{'title':'Actual admin task','done':False},{'title':'Done','done':True}]))
 item=asyncio.run(TasksCollector().collect())[0]
 assert item.status=='ok' and [m.value for m in item.metrics]==[1,1]
 assert item.entries[0].title=='Actual admin task' and len(item.entries)==1
 p.write_text('[{"title":"bad","done":"false"}]')
 item=asyncio.run(TasksCollector().collect())[0];assert item.status=='error' and item.entries==[] and item.metrics==[]
 monkeypatch.delenv('PIXORA_TASKS_FILE');assert asyncio.run(TasksCollector().collect())[0].status=='unavailable'

def test_github_and_rss_http_contracts(monkeypatch):
 import pixora.information_connectors as mod
 requests=[]
 def handler(r):
  requests.append(r)
  assert 'authorization' not in r.headers
  if '/actions/runs' in str(r.url):return httpx.Response(200,json={'workflow_runs':[{'name':'tests','status':'completed','conclusion':'success','html_url':'https://github.com/owner/repo/actions/runs/1'}]})
  return httpx.Response(200,json={'stargazers_count':2,'open_issues_count':3})
 monkeypatch.setattr(mod,'client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(handler)))
 monkeypatch.setenv('PIXORA_GITHUB_REPOSITORY','owner/repo')
 item=asyncio.run(GitHubCollector().collect())[0];assert item.status=='ok' and len(item.entries)==2
 monkeypatch.setattr(mod,'client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(403))))
 item=asyncio.run(GitHubCollector().collect())[0];assert item.status=='error' and not item.metrics
 monkeypatch.setenv('PIXORA_GITHUB_REPOSITORY','../../bad');assert asyncio.run(GitHubCollector().collect())[0].status=='error'
 monkeypatch.setenv('PIXORA_RSS_URL','https://example.com/feed')
 async def validate(url):return url
 monkeypatch.setattr(mod,'public_url',validate)
 monkeypatch.setattr(mod,'client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(302,headers={'location':'https://127.0.0.1'}))))
 assert asyncio.run(RSSCollector().collect())[0].status=='error'

def test_new_scopes_history_and_live_revocation(tmp_path,monkeypatch):
 monkeypatch.setenv('PIXORA_TASKS_FILE',str(tmp_path/'tasks.json'));(tmp_path/'tasks.json').write_text('[]')
 item=asyncio.run(TasksCollector().collect())[0]
 db=tmp_path/'db';c=TestClient(create_app(db,READ,WRITE))
 with sqlite3.connect(db) as con:
  old=provision(con,'old',['codex','system'],['real']);new=provision(con,'personal',['tasks','rss'],['real'])
 headers=lambda token:{'Authorization':'Bearer '+token}
 assert c.post('/api/v2/observations',json=item.model_dump(mode='json'),headers=headers(WRITE)).status_code==200
 assert c.get('/api/v2/observations',headers=headers(old['token'])).json()['observations']==[]
 assert c.get('/api/v2/history?provider=tasks',headers=headers(old['token'])).status_code==403
 assert c.get('/api/v2/history?provider=tasks',headers=headers(new['token'])).status_code==200
 assert c.get('/api/v1/device',headers=headers(new['token'])).json()['providers']==[]
 with sqlite3.connect(db) as con:con.execute('update devices set revoked=1 where id=?',(new['id'],))
 assert c.get('/api/v2/observations',headers=headers(new['token'])).status_code==401
