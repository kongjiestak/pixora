"""Validate and atomically deploy externally renewed certificates to a Caddy container."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import time
from datetime import datetime, timezone


def command(args, data=None):
    result = subprocess.run(args, input=data, capture_output=True)
    if result.returncode:
        raise RuntimeError('certificate validation or reload command failed')
    return result.stdout


def validate_pair(cert, key, domain):
    command(['openssl', 'x509', '-in', str(cert), '-checkend', '604800', '-noout'])
    command(['openssl', 'verify', '-purpose', 'sslserver', '-verify_hostname', domain,
             '-untrusted', str(cert), str(cert)])
    public = command(['openssl', 'x509', '-in', str(cert), '-pubkey', '-noout'])
    cert_key = command(['openssl', 'pkey', '-pubin', '-outform', 'DER'], public)
    private_key = command(['openssl', 'pkey', '-in', str(key), '-pubout', '-outform', 'DER'])
    if cert_key != private_key:
        raise RuntimeError('certificate and key do not match')
    der = command(['openssl', 'x509', '-in', str(cert), '-outform', 'DER'])
    expiry = command(['openssl', 'x509', '-in', str(cert), '-noout', '-enddate']).decode().strip()
    return hashlib.sha256(der).hexdigest(), expiry


def served_fingerprint(domain, port):
    with socket.create_connection(('127.0.0.1', port), timeout=10) as raw:
        with ssl.create_default_context().wrap_socket(raw, server_hostname=domain) as tls:
            fingerprint = hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest()
            tls.sendall(f'GET /healthz HTTP/1.1\r\nHost: {domain}:{port}\r\nConnection: close\r\n\r\n'.encode())
            if b' 200 ' not in tls.recv(1024).split(b'\r\n', 1)[0]:
                raise RuntimeError('HTTPS health check failed')
            return fingerprint


def atomic_write(path, content):
    temporary = path.with_name(path.name+'.next')
    temporary.write_bytes(content)
    temporary.chmod(0o600)
    temporary.replace(path)


def deploy(base, domain, port, container):
    incoming, live, config = base/'tls/incoming', base/'tls/live', base/'https-config'
    for path in (incoming, live, config):
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
    fingerprint, expiry = validate_pair(incoming/'fullchain.pem', incoming/'key.pem', domain)
    state_path = base/'tls-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    enabled = (base/'tls-managed.enabled').exists()
    if enabled and state.get('fingerprint') == fingerprint and served_fingerprint(domain, port) == fingerprint:
        state.update(checked_at=datetime.now(timezone.utc).isoformat(), status='ok')
        atomic_write(state_path, json.dumps(state, indent=2).encode())
        (base/'tls-last-error.json').unlink(missing_ok=True)
        print('TLS checked: trusted certificate, matching served fingerprint, HTTPS healthy')
        return
    generation = 'cert-'+fingerprint
    target = live/generation
    target.mkdir(mode=0o700, exist_ok=True)
    for name in ('fullchain.pem', 'key.pem'):
        shutil.copyfile(incoming/name, target/name)
        (target/name).chmod(0o600)
    # A new certificate generation changes the config path, avoiding stale file-cache reuse.
    text = (f'{{\n auto_https off\n admin unix//run/pixora-caddy-admin.sock\n}}\n'
            f'https://{domain}:{port} {{\n tls /certs/{generation}/fullchain.pem /certs/{generation}/key.pem\n'
            ' reverse_proxy monitor:8000\n}\n')
    candidate = config/'Caddyfile.candidate'
    candidate.write_text(text)
    candidate.chmod(0o600)
    if enabled:
        command(['docker', 'exec', container, 'caddy', 'validate', '--config', '/etc/caddy/Caddyfile.candidate', '--adapter', 'caddyfile'])
    current = config/'Caddyfile'
    previous = current.read_bytes() if current.exists() else None
    atomic_write(current, text.encode())
    reload_args = ['docker', 'exec', container, 'caddy', 'reload', '--config', '/etc/caddy/Caddyfile',
                   '--adapter', 'caddyfile', '--address', 'unix//run/pixora-caddy-admin.sock', '--force']
    if enabled:
        try:
            command(reload_args)
            for attempt in range(5):
                try:
                    if served_fingerprint(domain, port) == fingerprint:
                        break
                except (OSError, RuntimeError):
                    pass
                if attempt == 4:
                    raise RuntimeError('new certificate not served; rolling back')
                time.sleep(1)
        except Exception:
            if previous is not None:
                atomic_write(current, previous)
                command(reload_args)
            raise
    result = {'status': 'ok' if enabled else 'prepared', 'fingerprint': fingerprint,
              'not_after': expiry, 'checked_at': datetime.now(timezone.utc).isoformat()}
    atomic_write(state_path, json.dumps(result, indent=2).encode())
    (base/'tls-last-error.json').unlink(missing_ok=True)
    print('TLS deployment verified' if enabled else 'TLS deployment prepared; proxy activation pending')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--port', type=int, default=2053)
    parser.add_argument('--container', default='pixora-vps-https')
    args = parser.parse_args()
    # Settings are administrator-owned; reject characters that could become Caddy directives.
    if not args.domain or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789.-' for c in args.domain) or not 1 <= args.port <= 65535:
        parser.error('invalid domain or port')
    os.umask(0o077)
    with (args.base/'tls-deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            deploy(args.base, args.domain, args.port, args.container)
        except Exception:
            atomic_write(args.base/'tls-last-error.json', json.dumps({'status': 'failed', 'at': datetime.now(timezone.utc).isoformat()}).encode())
            raise SystemExit('TLS validation/deployment failed; current configuration retained or rollback attempted')


if __name__ == '__main__':
    main()
