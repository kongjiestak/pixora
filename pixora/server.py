import os
import json
import sqlite3
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager, contextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pixora.models import Snapshot, now
from pixora.settings import setting
from pixora.devices import initialize, token_hash

bearer = HTTPBearer(auto_error=False)

def create_app(db_path=None, read_token=None, write_token=None, stale_seconds=None, web_dir=None):
    read_token = read_token or setting("READ_TOKEN", "")
    write_token = write_token or setting("WRITE_TOKEN", "")
    if min(len(read_token), len(write_token)) < 32 or read_token == write_token:
        raise RuntimeError("Set distinct PIXORA_READ_TOKEN and PIXORA_WRITE_TOKEN (32+ characters)")
    db_path = str(db_path or setting("DB", "data/pixora.sqlite"))
    stale = int(stale_seconds or setting("STALE_SECONDS", "600"))
    if stale < 1:
        raise RuntimeError("PIXORA_STALE_SECONDS must be positive")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    @contextmanager
    def db():
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            with conn:
                yield conn
        finally:
            conn.close()
    with db() as conn:
        initialize(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS device_sessions(token_hash TEXT PRIMARY KEY, device_id TEXT NOT NULL, expires_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS snapshots(provider TEXT, mode TEXT, body TEXT NOT NULL, received_at TEXT NOT NULL, PRIMARY KEY(provider,mode))")

    @asynccontextmanager
    async def lifespan(app):
        yield
    app = FastAPI(title="Pixora", version="0.1.0.dev1", lifespan=lifespan)

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

    cookie_name = "__Host-pixora_session"

    def invalid():
        raise HTTPException(401, "invalid token", headers={"WWW-Authenticate": "Bearer"})

    def device_scope(token):
        with db() as conn:
            row = conn.execute("SELECT id,providers,modes,expires_at FROM devices WHERE token_hash=? AND revoked=0 AND expires_at>?",
                               (token_hash(token), now().isoformat())).fetchone()
        if row is None:
            invalid()
        return {"id": row[0], "providers": json.loads(row[1]), "modes": json.loads(row[2]), "expires_at": row[3]}

    def session_scope(request):
        token = request.cookies.get(cookie_name, "")
        if not token:
            invalid()
        with db() as conn:
            row = conn.execute("SELECT d.id,d.providers,d.modes,s.expires_at,d.expires_at FROM device_sessions s JOIN devices d ON d.id=s.device_id WHERE s.token_hash=? AND s.expires_at>? AND d.expires_at>? AND d.revoked=0",
                               (token_hash(token), now().isoformat(), now().isoformat())).fetchone()
        if row is None:
            invalid()
        return {"id": row[0], "providers": json.loads(row[1]), "modes": json.loads(row[2]), "expires_at": min(row[3], row[4])}

    def read_scope(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None:
            return session_scope(request)
        token = credentials.credentials
        if secrets.compare_digest(token, read_token):
            if setting("ALLOW_LEGACY_READ_TOKEN", "true").lower() != "true":
                invalid()
            return {"providers": ["codex", "chatgpt"], "modes": ["real", "demo"], "id": None}
        return device_scope(token)

    def same_origin(request):
        # Browser mutations require an explicit, exact HTTPS Origin. Do not trust forwarded headers.
        if request.headers.get("origin") != "https://" + request.headers.get("host", ""):
            raise HTTPException(403, "same-origin HTTPS required")

    @app.post("/api/v1/session")
    def login(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        same_origin(request)
        if credentials is None:
            invalid()
        # Only scoped devices can create persistent sessions. Global read/write tokens cannot.
        scope = device_scope(credentials.credentials)
        expiry = min(now() + timedelta(days=30), datetime.fromisoformat(scope["expires_at"]))
        secret = secrets.token_urlsafe(32)
        with db() as conn:
            conn.execute("DELETE FROM device_sessions WHERE expires_at<=? OR token_hash=?", (now().isoformat(), token_hash(request.cookies.get(cookie_name, ""))))
            conn.execute("INSERT INTO device_sessions VALUES (?,?,?)", (token_hash(secret), scope["id"], expiry.isoformat()))
            # Bound sessions per device; oldest expiry is evicted first.
            conn.execute("DELETE FROM device_sessions WHERE device_id=? AND token_hash NOT IN (SELECT token_hash FROM device_sessions WHERE device_id=? ORDER BY expires_at DESC LIMIT 20)", (scope["id"], scope["id"]))
        response = JSONResponse({"authenticated": True, "expires_at": expiry.isoformat(), "modes": scope["modes"]})
        response.set_cookie(cookie_name, secret, max_age=max(1, int((expiry-now()).total_seconds())), expires=expiry, path="/", secure=True, httponly=True, samesite="strict")
        return response

    @app.get("/api/v1/session")
    def session(request: Request):
        scope = session_scope(request)
        return {"authenticated": True, "expires_at": scope["expires_at"], "modes": scope["modes"]}

    @app.delete("/api/v1/session")
    def logout(request: Request):
        same_origin(request)
        with db() as conn:
            conn.execute("DELETE FROM device_sessions WHERE token_hash=?", (token_hash(request.cookies.get(cookie_name, "")),))
        response = Response(status_code=204)
        response.delete_cookie(cookie_name, path="/", secure=True, httponly=True, samesite="strict")
        return response

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

    @app.get("/api/v1/device")
    def device(mode: str = "real", scope=Depends(read_scope)):
        if mode not in ("real", "demo"):
            raise HTTPException(422, "mode must be real or demo")
        if mode not in scope["modes"]:
            raise HTTPException(403, "device mode not permitted")
        with db() as conn:
            rows = dict((p, (body, received)) for p, body, received in conn.execute("SELECT provider, body, received_at FROM snapshots WHERE mode=?", (mode,)))
        items = []
        for provider in scope["providers"]:
            row = rows.get(provider)
            if row:
                snap = Snapshot.model_validate_json(row[0])
                item = json.loads(snap.model_dump_json())
                age = max(0, int((now() - snap.observed_at).total_seconds()))
                item.update(collected_at=item["observed_at"], received_at=row[1], age_seconds=age, stale=age > stale or any(w.resets_at and w.resets_at <= now() for w in snap.windows))
                for window in item["windows"]:
                    window["remaining_percent"] = max(0, min(100, 100-window["used_percent"]))
                items.append(item)
            else:
                items.append(dict(provider=provider, mode=mode, source="unavailable", status="unavailable", observed_at=None, collected_at=None, received_at=None, age_seconds=None, stale=True, windows=[], reason_code="chatgpt_unavailable" if provider == "chatgpt" else "awaiting_collector", reason=None))
        return {"schema_version": 1, "server_time": now(), "stale_after_seconds": stale, "mode": mode, "device_id": scope["id"], "providers": items}

    web = Path(web_dir or setting("WEB_DIR", "web/dist"))
    if web.is_dir():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app
