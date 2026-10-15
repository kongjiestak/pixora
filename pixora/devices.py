"""Local-only device provisioning. Raw tokens are never stored in SQLite."""
import argparse
import hashlib
import json
import secrets
import sqlite3
from datetime import timedelta
from pathlib import Path
from pixora.models import now
from pixora.settings import setting


def initialize(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS devices(
        id TEXT PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT UNIQUE NOT NULL,
        providers TEXT NOT NULL, modes TEXT NOT NULL, expires_at TEXT NOT NULL,
        revoked INTEGER NOT NULL DEFAULT 0)''')


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def provision(conn, name, providers, modes, days=30):
    if not name.strip() or len(name) > 80:
        raise ValueError('name must contain 1–80 characters')
    if not providers or not set(providers) <= {'codex', 'chatgpt'}:
        raise ValueError('select codex and/or chatgpt')
    if not modes or not set(modes) <= {'real', 'demo'}:
        raise ValueError('select real and/or demo')
    if not 1 <= days <= 365:
        raise ValueError('expiry must be 1–365 days')
    identifier = secrets.token_hex(12)
    token = secrets.token_urlsafe(32)
    expires = (now() + timedelta(days=days)).isoformat()
    conn.execute('INSERT INTO devices VALUES (?,?,?,?,?,?,0)',
                 (identifier, name.strip(), token_hash(token), json.dumps(sorted(set(providers))),
                  json.dumps(sorted(set(modes))), expires))
    return {'id': identifier, 'token': token, 'expires_at': expires}


def main():
    parser = argparse.ArgumentParser(description='Local Pixora device administration; no network admin endpoint')
    parser.add_argument('--db', default=setting('DB', 'data/pixora.sqlite'))
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('create')
    create.add_argument('--name', required=True)
    create.add_argument('--provider', action='append', choices=['codex', 'chatgpt'], required=True)
    create.add_argument('--mode', action='append', choices=['demo', 'real'], default=None)
    create.add_argument('--days', type=int, default=30)
    commands.add_parser('list')
    revoke = commands.add_parser('revoke')
    revoke.add_argument('id')
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db, timeout=10)
    try:
        with conn:
            initialize(conn)
            if args.command == 'create':
                # Safe default: explicit extra authorization is needed for real observations.
                print(json.dumps(provision(conn, args.name, args.provider, args.mode or ['demo'], args.days)))
            elif args.command == 'list':
                rows = conn.execute('SELECT id,name,providers,modes,expires_at,revoked FROM devices').fetchall()
                print(json.dumps([dict(zip(['id','name','providers','modes','expires_at','revoked'], r)) for r in rows]))
            else:
                if conn.execute('UPDATE devices SET revoked=1 WHERE id=?', (args.id,)).rowcount != 1:
                    parser.error('unknown device')
                print(json.dumps({'revoked': True, 'id': args.id}))
    except ValueError as exc:
        parser.error(str(exc))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
