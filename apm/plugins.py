"""Allowlisted collectors. Never send Codex credentials or raw RPC responses."""
import asyncio
import json
import os
from typing import Protocol
from datetime import datetime, timezone, timedelta
from apm.models import Snapshot, Window, now

class Collector(Protocol):
    async def collect(self) -> list[Snapshot]: ...

class CollectionError(Exception):
    pass

def normalize(result: dict) -> Snapshot:
    buckets = result.get("rateLimitsByLimitId")
    if not buckets:
        legacy = result.get("rateLimits")
        buckets = {legacy.get("limitId") or "codex": legacy} if legacy else {}
    windows = []
    for bucket, data in buckets.items():
        if not isinstance(data, dict):
            continue
        for name in ("primary", "secondary"):
            raw = data.get(name)
            if not isinstance(raw, dict) or raw.get("usedPercent") is None:
                continue
            windows.append(Window(name=f"{bucket}/{name}", used_percent=raw["usedPercent"], duration_minutes=raw.get("windowDurationMins"), resets_at=datetime.fromtimestamp(raw["resetsAt"], timezone.utc) if raw.get("resetsAt") is not None else None))
    return Snapshot(provider="codex", source="codex-app-server", mode="real", status="ok" if windows else "unavailable", observed_at=now(), windows=windows, reason=None if windows else "接口未返回可用额度窗口")

class CodexCollector:
    async def collect(self):
        p = None
        try:
            p = await asyncio.create_subprocess_exec(os.getenv("APM_CODEX_BIN", "codex"), "app-server", "--stdio", stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=1024*1024)
            async def send(message):
                p.stdin.write((json.dumps(message)+"\n").encode())
                await p.stdin.drain()
            async def request(i, method, params):
                await send(dict(id=i, method=method, params=params))
                while True:
                    line = await p.stdout.readline()
                    if not line:
                        raise CollectionError()
                    message = json.loads(line)
                    if message.get("id") == i and "method" not in message:
                        if "error" in message:
                            raise CollectionError()
                        return message["result"]
                    if "id" in message and "method" in message:
                        await send({"id": message["id"], "error": {"code": -32601, "message": "unsupported"}})
            async with asyncio.timeout(30):
                await request(1, "initialize", {"clientInfo": {"name":"ai_pocket_monitor", "version":"0.1.0"}})
                await send({"method":"initialized"})
                result = await request(2, "account/rateLimits/read", {})
                return [normalize(result)]
        except (OSError, TimeoutError, CollectionError, ValueError, KeyError, TypeError):
            return [Snapshot(provider="codex", source="codex-app-server", mode="real", status="error", observed_at=now(), reason="Codex 读取失败：检查 CLI 版本、登录与网络；未上传底层错误或凭据")]
        finally:
            if p and p.returncode is None:
                p.terminate()
                try:
                    await asyncio.wait_for(p.wait(), 5)
                except TimeoutError:
                    p.kill()
                    await p.wait()

class DemoCollector:
    async def collect(self):
        return [Snapshot(provider=p, mode="demo", source="demo", status="ok", observed_at=now(), windows=[Window(name="示例/5h", used_percent=v, duration_minutes=300, resets_at=now()+timedelta(hours=2))], reason="固定模拟值，不代表账号真实额度") for p,v in (("codex", 36), ("chatgpt", 62))]

PLUGINS: dict[str, type[Collector]] = {"codex": CodexCollector, "demo": DemoCollector}
