import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from pixora.server import create_app
from pixora.devices import provision
from pixora.device_profiles import configure,read_profile
from test_v2 import observation,READ,WRITE,auth
from test_api import payload


def setup(tmp_path):
    db=tmp_path/'profiles.sqlite'
    client=TestClient(create_app(db,READ,WRITE),base_url='https://testserver')
    with sqlite3.connect(db) as conn:device=provision(conn,'desk',['codex','system','rss'],['real'])
    return db,client,device


def test_profile_read_only_revision_and_legacy_compatibility(tmp_path):
    db,c,d=setup(tmp_path)
    url='/api/v2/device-config'
    assert c.get(url).status_code==401
    assert c.get(url,headers=auth(READ)).status_code==403
    first=c.get(url,headers=auth(d['token'])).json()
    assert first['revision']==0 and first['profile']['show_clock']
    with sqlite3.connect(db) as conn:
        result=configure(conn,d['id'],{'show_clock':False,'focus_window':'weekly'})
        assert result['revision']==1
    result=c.get(url,headers=auth(d['token']))
    assert result.status_code==200 and result.headers['cache-control']=='no-store'
    assert result.json()['profile']['show_clock'] is False
    assert d['token'] not in result.text and 'policy' not in result.json()
    assert c.patch(url,headers=auth(d['token']),json={'profile':{}}).status_code==405
    assert c.post('/api/v2/observations',headers=auth(d['token']),json=observation()).status_code==401
    # Additive migration survives reopen and leaves original device row/token intact.
    other=TestClient(create_app(db,READ,WRITE))
    assert other.get(url,headers=auth(d['token'])).json()['revision']==1


def test_policy_filters_latest_history_and_live_cookie(tmp_path):
    db,c,d=setup(tmp_path)
    for entity in ['private-host','allowed-host','private-host','allowed-host']:
        item=observation(entity=entity)
        item['metrics'].append({'key':'memory.used','value':90,'unit':'percent'})
        item['entries']=[{'title':'allowed title','detail':'SECRET detail','url':'https://example.com/private'}]
        assert c.post('/api/v2/observations',headers=auth(WRITE),json=item).status_code==200
    assert c.post('/api/v1/session',headers={**auth(d['token']),'Origin':'https://testserver'}).status_code==200
    with sqlite3.connect(db) as conn:configure(conn,d['id'],policy={'rules':{'system':{'entities':['allowed-host'],'metrics':['cpu.used'],'entries':'titles'}}})
    for headers in [auth(d['token']),{}]:
        latest=c.get('/api/v2/observations',headers=headers).json()['observations']
        assert len(latest)==1 and latest[0]['entity_id']=='allowed-host'
        assert [m['key'] for m in latest[0]['metrics']]==['cpu.used']
        assert latest[0]['entries']==[{'title':'allowed title'}]
        page=c.get('/api/v2/history?provider=system&limit=1',headers=headers).json()
        assert len(page['items'])==1 and page['next_before']
        next_page=c.get('/api/v2/history?provider=system&limit=1&before='+str(page['next_before']),headers=headers).json()
        assert len(next_page['items'])==1
        assert page['items'][0]['id']!=next_page['items'][0]['id']
        for response in [c.get('/api/v2/observations',headers=headers),c.get('/api/v2/history?provider=system',headers=headers)]:
            assert all(secret not in response.text for secret in ['private-host','SECRET','example.com/private','memory.used'])
        assert c.get('/api/v2/history?provider=rss',headers=headers).status_code==403
        assert c.get('/api/v1/device',headers=headers).json()['providers']==[]
    with sqlite3.connect(db) as conn:conn.execute('UPDATE devices SET revoked=1 WHERE id=?',(d['id'],))
    assert c.get('/api/v2/device-config').status_code==401
    assert c.get('/api/v2/observations').status_code==401


def test_window_filter_covers_v1_and_v2(tmp_path):
    db,c,d=setup(tmp_path)
    body=payload();body['windows'].append({'name':'secret-weekly','used_percent':85})
    assert c.post('/api/v1/snapshots',headers=auth(WRITE),json=body).status_code==200
    with sqlite3.connect(db) as conn:configure(conn,d['id'],policy={'rules':{'codex':{'windows':[body['windows'][0]['name']]}}})
    for url in ['/api/v1/device','/api/v2/observations','/api/v2/history?provider=codex']:
        response=c.get(url,headers=auth(d['token']))
        assert response.status_code==200 and 'secret-weekly' not in response.text
    with sqlite3.connect(db) as conn:configure(conn,d['id'],policy={'rules':{'codex':{'connectors':['not-quota-v1']}}})
    assert c.get('/api/v1/device',headers=auth(d['token'])).json()['providers']==[]
    assert c.get('/api/v2/observations',headers=auth(d['token'])).json()['observations']==[]


def test_public_only_and_empty_rules_are_server_boundaries(tmp_path):
    db,c,d=setup(tmp_path)
    for sensitivity,entity in [('public','public-host'),('private','secret-private-host')]:
        item=observation(entity=entity);item['sensitivity']=sensitivity
        assert c.post('/api/v2/observations',headers=auth(WRITE),json=item).status_code==200
    c.post('/api/v1/snapshots',headers=auth(WRITE),json=payload())
    with sqlite3.connect(db) as conn:configure(conn,d['id'],policy={'public_only':True})
    for url in ['/api/v2/observations','/api/v2/history?provider=system']:
        response=c.get(url,headers=auth(d['token']))
        assert 'public-host' in response.text and 'secret-private-host' not in response.text
    assert c.get('/api/v1/device',headers=auth(d['token'])).json()['providers']==[]
    with sqlite3.connect(db) as conn:configure(conn,d['id'],policy={'rules':{}})
    assert c.get('/api/v2/observations',headers=auth(d['token'])).json()['observations']==[]
    assert c.get('/api/v2/history?provider=system',headers=auth(d['token'])).status_code==403
    assert c.get('/api/v2/device-config',headers=auth(d['token'])).json()['providers']==[]


@pytest.mark.parametrize('profile,policy',[
    ({'show_clock':'false'},None),({'unknown':True},None),({'density':'huge'},None),
    (None,{'rules':{'weather':{}}}),(None,{'rules':{'system':{'metrics':'cpu.used'}}}),
    (None,{'rules':{'system':{'entries':'unsafe'}}}),(None,{'extra':True})])
def test_invalid_configuration_is_atomic(tmp_path,profile,policy):
    db,c,d=setup(tmp_path)
    with sqlite3.connect(db) as conn,pytest.raises(ValueError):configure(conn,d['id'],profile,policy)
    with sqlite3.connect(db) as conn:assert read_profile(conn,d['id'])[2]==0


def test_cli_configure_inspect_and_missing_device(tmp_path,monkeypatch,capsys):
    from pixora.devices import main
    db,c,d=setup(tmp_path);p=tmp_path/'profile.json';p.write_text('{"show_clock":false}')
    def cli(*args):
        monkeypatch.setattr('sys.argv',['pixora-device','--db',str(db),*args]);main()
        return json.loads(capsys.readouterr().out)
    assert cli('configure',d['id'],'--profile',str(p))['revision']==1
    result=cli('inspect',d['id']);assert result['profile']['show_clock'] is False
    assert d['token'] not in json.dumps(result)
    with pytest.raises(SystemExit):cli('configure','missing','--profile',str(p))


def test_empty_entity_filter_and_sql_literals_never_bypass_scope(tmp_path):
    db,c,d=setup(tmp_path)
    c.post('/api/v2/observations',headers=auth(WRITE),json=observation(entity='allowed'))
    for entities in [[],["allowed' OR 1=1 --"]]:
        with sqlite3.connect(db) as conn:configure(conn,d['id'],policy={'rules':{'system':{'entities':entities}}})
        assert c.get('/api/v2/observations',headers=auth(d['token'])).json()['observations']==[]
        assert c.get('/api/v2/history?provider=system',headers=auth(d['token'])).json()['items']==[]


def test_corrupt_policy_fails_closed_instead_of_reverting_to_full_grant(tmp_path):
    db,c,d=setup(tmp_path)
    with sqlite3.connect(db) as conn:
        configure(conn,d['id'],policy={'rules':{}})
        conn.execute("UPDATE device_profiles SET policy='broken'")
    for url in ['/api/v1/device','/api/v2/observations','/api/v2/history?provider=system','/api/v2/device-config']:
        response=c.get(url,headers=auth(d['token']))
        assert response.status_code==503 and 'configuration invalid' in response.text
