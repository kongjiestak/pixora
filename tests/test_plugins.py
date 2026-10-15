import asyncio
import pytest
from pixora.plugins import normalize, DemoCollector, CodexCollector

def test_multi_bucket_and_nullable():
    p=normalize({'rateLimitsByLimitId':{'codex':{'primary':{'usedPercent':0,'windowDurationMins':300,'resetsAt':1700000000},'secondary':None},'other':{'primary':{'usedPercent':100}}}})
    assert [w.used_percent for w in p.windows]==[0,100]
    assert p.windows[0].resets_at.tzinfo is not None

def test_legacy_and_unknown():
    assert normalize({'rateLimits':{'primary':{'usedPercent':42}}}).windows[0].used_percent==42
    assert normalize({'rateLimits':None}).status=='unavailable'
    assert normalize({'rateLimits':{'primary':{'usedPercent':None}}}).windows==[]

def test_invalid_percent_fails():
    with pytest.raises(ValueError):
        normalize({'rateLimits':{'primary':{'usedPercent':-1}}})

def test_demo_marked():
    assert all(s.mode=='demo' and s.source=='demo' for s in asyncio.run(DemoCollector().collect()))

def test_missing_cli_is_explicit_error(monkeypatch):
    monkeypatch.setenv('APM_CODEX_BIN','/does-not-exist/codex')
    result=asyncio.run(CodexCollector().collect())[0]
    assert result.status=='error' and result.windows==[]


def test_stdio_handshake_and_notification(tmp_path, monkeypatch):
    fake=tmp_path/'fake-codex'
    fake.write_text("#!/usr/bin/env python3\nimport sys,json\nassert sys.argv[1:]==['app-server','--stdio']\nfirst=json.loads(sys.stdin.readline())\nassert first['method']=='initialize'\nprint(json.dumps({'id':first['id'],'result':{}}),flush=True)\nassert json.loads(sys.stdin.readline())['method']=='initialized'\nrequest=json.loads(sys.stdin.readline())\nassert request['method']=='account/rateLimits/read'\nprint(json.dumps({'method':'notification','params':{}}),flush=True)\nprint(json.dumps({'id':request['id'],'result':{'rateLimitsByLimitId':{'codex':{'primary':{'usedPercent':17,'windowDurationMins':300}}}}}),flush=True)\nsys.stdin.read()\n")
    fake.chmod(0o700)
    monkeypatch.setenv('APM_CODEX_BIN',str(fake))
    result=asyncio.run(CodexCollector().collect())[0]
    assert result.status=='ok' and result.windows[0].used_percent==17


def test_errors_and_demos_use_reason_codes(monkeypatch):
    monkeypatch.setenv('PIXORA_CODEX_BIN','/does-not-exist/codex')
    result=asyncio.run(CodexCollector().collect())[0]
    assert result.reason_code=='codex_read_failed' and result.reason is None
    assert all(s.reason_code=='demo_fixed' for s in asyncio.run(DemoCollector().collect()))
