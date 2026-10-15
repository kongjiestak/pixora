import argparse
import asyncio
import json
import os
import random
from urllib.parse import urlparse
import httpx
from apm.plugins import PLUGINS

async def run(args):
    if args.interval < 30:
        raise SystemExit("interval must be >= 30 seconds")
    token = os.getenv("APM_WRITE_TOKEN", "")
    if not args.print_only:
        url = urlparse(args.server)
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise SystemExit("invalid server URL")
        if url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1", "::1") and not args.allow_private_http:
            raise SystemExit("Use HTTPS, or --allow-private-http only over a trusted private VPN")
        if len(token) < 32:
            raise SystemExit("APM_WRITE_TOKEN must contain 32+ characters")
    failures = 0
    while True:
        snapshots = await PLUGINS[args.plugin]().collect()
        if args.print_only:
            print(json.dumps([s.model_dump(mode="json") for s in snapshots], ensure_ascii=False))
            return
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
                for snapshot in snapshots:
                    response = await client.post(args.server.rstrip("/")+"/api/v1/snapshots", headers={"Authorization": "Bearer "+token}, json=snapshot.model_dump(mode="json"))
                    response.raise_for_status()
            failures = 0
            print("snapshot delivered", flush=True)
        except httpx.HTTPError:
            failures += 1
            print("delivery failed; check server, network and token (details suppressed)", flush=True)
            if args.once:
                raise SystemExit(1)
        if args.once:
            return
        await asyncio.sleep(min(3600, args.interval*2**min(failures, 4)) + random.uniform(0, 5))

def main():
    p = argparse.ArgumentParser(description="APM Mac outbound collector")
    p.add_argument("--plugin", choices=PLUGINS, default="codex")
    p.add_argument("--server", default=os.getenv("APM_SERVER", "http://127.0.0.1:8000"))
    p.add_argument("--interval", type=int, default=120)
    p.add_argument("--once", action="store_true")
    p.add_argument("--print-only", action="store_true")
    p.add_argument("--allow-private-http", action="store_true")
    asyncio.run(run(p.parse_args()))

if __name__ == "__main__":
    main()
