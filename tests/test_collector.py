import asyncio
from argparse import Namespace
import httpx
import pytest
from pixora import collector
from pixora.models import Snapshot, Window, now


def test_failed_requests_back_off_then_recover_without_restart(monkeypatch, capsys):
    attempts = []
    sleeps = []
    token = 'X'*48
    monkeypatch.setenv('PIXORA_WRITE_TOKEN', token)
    class Plugin:
        async def collect(self):
            return [Snapshot(provider='codex', mode='real', source='codex-app-server', status='ok', observed_at=now(), windows=[Window(name='primary', used_percent=10)])]
    monkeypatch.setitem(collector.PLUGINS, 'test', Plugin)
    def handler(request):
        assert request.headers['Authorization'] == 'Bearer '+token
        attempts.append(request)
        if len(attempts) == 1:
            raise httpx.ConnectError('private network details', request=request)
        return httpx.Response(503 if len(attempts) == 2 else 200)
    client = httpx.AsyncClient
    monkeypatch.setattr(collector.httpx, 'AsyncClient', lambda **kw: client(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(collector.random, 'uniform', lambda *_: 0)
    async def sleep(delay):
        sleeps.append(delay)
        if len(sleeps) == 3:
            raise asyncio.CancelledError()
    monkeypatch.setattr(collector.asyncio, 'sleep', sleep)
    args = Namespace(interval=120, max_retry_delay=300, print_only=False, server='https://monitor.test', allow_private_http=False, plugin='test', once=False)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(collector.run(args))
    assert sleeps == [240, 300, 120]
    output = capsys.readouterr().out
    assert output.count('delivery failed') == 2 and output.count('snapshot delivered') == 1
    assert token not in output and 'private network details' not in output


def test_long_outage_remains_bounded_and_success_resets_delay():
    assert collector.retry_delay(120, 1000) == 300
    assert collector.retry_delay(120, 0) == 120
    assert collector.retry_delay(120, 3, 60) == 60
