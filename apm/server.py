import os
import json
import sqlite3
import secrets
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from apm.models import Snapshot, now

bearer = HTTPBearer(auto_error=False)

def create_app(db_path=None, read_token=None, write_token=None, stale_seconds=None, web_dir=None):
    read_token = read_token or os.getenv("APM_READ_TOKEN", "")
    write_token = write_token or os.getenv("APM_WRITE_TOKEN", "")
    if min(len(read_token), len(write_token)) < 32 or read_token == write_token:
        raise RuntimeError("Set distinct APM_READ_TOKEN and APM_WRITE_TOKEN (32+ characters)")
    db_path = str(db_path or os.getenv("APM_DB", "data/apm.sqlite"))
    stale = int(stale_seconds or os.getenv("APM_STALE_SECONDS", "600"))
    if stale < 1:
        raise RuntimeError("APM_STALE_SECONDS must be positive")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    def db():
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS snapshots(provider TEXT, mode TEXT, body TEXT NOT NULL, received_at TEXT NOT NULL, PRIMARY KEY(provider,mode))")

    @asynccontextmanager
    async def lifespan(app):
        yield
    app = FastAPI(title="AI Pocket Monitor", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method == "POST":
            # Bound streaming bodies, including requests without Content-Length.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 32768:
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"detail": "body too large"}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"
        return response

    def auth(expected):
        def check(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
            if credentials is None or not secrets.compare_digest(credentials.credentials, expected):
                raise HTTPException(401, "invalid token", headers={"WWW-Authenticate":"Bearer"})
        return check

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.post("/api/v1/snapshots", dependencies=[Depends(auth(write_token))])
    def ingest(snapshot: Snapshot):
        received = now().isoformat()
        body = snapshot.model_dump_json()
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT body FROM snapshots WHERE provider=? AND mode=?", (snapshot.provider, snapshot.mode)).fetchone()
            if existing and Snapshot.model_validate_json(existing[0]).observed_at > snapshot.observed_at:
                raise HTTPException(409, "older observation rejected")
            conn.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?)", (snapshot.provider, snapshot.mode, body, received))
        return {"accepted": True, "received_at": received}

    @app.get("/api/v1/device", dependencies=[Depends(auth(read_token))])
    def device(mode: str = "real"):
        if mode not in ("real", "demo"):
            raise HTTPException(422, "mode must be real or demo")
        with db() as conn:
            rows = dict((p, (body, received)) for p, body, received in conn.execute("SELECT provider, body, received_at FROM snapshots WHERE mode=?", (mode,)))
        items = []
        for provider in ("codex", "chatgpt"):
            row = rows.get(provider)
            if row:
                snap = Snapshot.model_validate_json(row[0])
                item = json.loads(snap.model_dump_json())
                age = max(0, int((now() - snap.observed_at).total_seconds()))
                item.update(received_at=row[1], age_seconds=age, stale=age > stale or any(w.resets_at and w.resets_at <= now() for w in snap.windows))
                for window in item["windows"]:
                    window["remaining_percent"] = max(0, min(100, 100-window["used_percent"]))
                items.append(item)
            else:
                items.append(dict(provider=provider, mode=mode, source="unavailable", status="unavailable", observed_at=None, received_at=None, age_seconds=None, stale=True, windows=[], reason="尚无数据；ChatGPT 真实额度未接入" if provider == "chatgpt" else "等待 Mac 采集客户端"))
        return {"schema_version": 1, "server_time": now(), "stale_after_seconds": stale, "mode": mode, "providers": items}

    web = Path(web_dir or os.getenv("APM_WEB_DIR", "web/dist"))
    if web.is_dir():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app
