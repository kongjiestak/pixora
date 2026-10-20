"""Additive v2 migration with an online SQLite backup; old v1 tables stay intact."""
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from pixora.models import Snapshot
from pixora.observations import from_snapshot

VERSION=2

def append(conn, observation, received_at):
    raw=observation.model_dump_json()
    conn.execute('INSERT OR IGNORE INTO observations(provider,connector_id,entity_id,mode,collected_at,expires_at,body,received_at) VALUES(?,?,?,?,?,?,?,?)',
        (observation.provider,observation.connector_id,observation.entity_id,observation.mode,
         observation.collected_at.isoformat(),observation.expires_at.isoformat(),raw,received_at))
    # Bound each stream; latest snapshot is retained even after expiry.
    conn.execute('DELETE FROM observations WHERE provider=? AND connector_id=? AND entity_id=? AND mode=? AND id NOT IN (SELECT id FROM observations WHERE provider=? AND connector_id=? AND entity_id=? AND mode=? ORDER BY collected_at DESC,id DESC LIMIT 1000)',
        (observation.provider,observation.connector_id,observation.entity_id,observation.mode)*2)

def migrate(path):
    path=Path(path)
    with sqlite3.connect(path,timeout=10) as conn:
        version=conn.execute('PRAGMA user_version').fetchone()[0]
        if version>VERSION:raise RuntimeError('database newer than this application')
        if version==VERSION:return
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables:
            stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup=path.with_name(path.name+'.pre-v2-'+stamp)
            with sqlite3.connect(backup) as destination:conn.backup(destination)
            backup.chmod(0o600)
        conn.execute('BEGIN IMMEDIATE')
        try:
            conn.execute('CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY,provider TEXT NOT NULL,connector_id TEXT NOT NULL,entity_id TEXT NOT NULL,mode TEXT NOT NULL,collected_at TEXT NOT NULL,expires_at TEXT NOT NULL,body TEXT NOT NULL,received_at TEXT NOT NULL,UNIQUE(provider,connector_id,entity_id,mode,collected_at))')
            conn.execute('CREATE INDEX IF NOT EXISTS observations_stream ON observations(provider,mode,collected_at DESC,id DESC)')
            if 'snapshots' in tables:
                for body,received in conn.execute('SELECT body,received_at FROM snapshots').fetchall():
                    append(conn,from_snapshot(Snapshot.model_validate_json(body)),received)
            conn.execute('PRAGMA user_version=2');conn.commit()
        except Exception:
            conn.rollback();raise
