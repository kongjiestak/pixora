"""Local supervisor: isolated credentials, read-only screen pairing, no cloud required."""
import argparse
import html
import io
import ipaddress
import json
import os
from pathlib import Path
import secrets
import signal
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import webbrowser

from pixora.database import migrate
from pixora.devices import initialize, provision, token_hash
from pixora.models import now


def prepare(directory):
    directory = Path(directory).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    config = directory / 'local.json'
    if config.is_symlink():
        raise ValueError('local.json must not be a symlink')
    if config.exists():
        os.chmod(config, 0o600)
        value = json.loads(config.read_text())
    else:
        value = dict(read=secrets.token_urlsafe(32), write=secrets.token_urlsafe(32))
    if any(not isinstance(value.get(k), str) or len(value[k]) < 32 for k in ('read', 'write')) or value['read'] == value['write']:
        raise ValueError('invalid local credentials; restore your private local.json')
    database = directory / 'pixora.sqlite'
    migrate(str(database))
    with sqlite3.connect(database) as conn:
        initialize(conn)
        row = conn.execute('SELECT id FROM devices WHERE token_hash=? AND revoked=0 AND expires_at>?',
                           (token_hash(value.get('screen', '')), now().isoformat())).fetchone()
        if row is None:
            device = provision(conn, 'Local screen / 本地屏幕', ['codex'], ['real'], days=30)
            value['screen'] = device['token']
    # Atomic private write, including on platforms without POSIX permission enforcement.
    temporary = directory / ('config-' + secrets.token_hex(8))
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)
    os.replace(temporary, config)
    os.chmod(database, 0o600)
    return value


def pairing_page(directory, base, token):
    import qrcode
    import qrcode.image.svg
    link = base + '/?kiosk#token=' + token
    buffer = io.BytesIO()
    qrcode.make(link, image_factory=qrcode.image.svg.SvgPathImage, border=4).save(buffer)
    svg = buffer.getvalue().decode().split('?>')[-1]
    page = Path(directory) / 'connect.html'
    if page.is_symlink():
        raise ValueError('connect.html must not be a symlink')
    content = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><title>Pixora · 本地屏幕 / Local screen</title>
<style>body{font:18px system-ui;background:#091319;color:#e4f4ef;max-width:640px;margin:8vh auto;padding:24px;line-height:1.7}svg{width:260px;height:260px;background:white}a{color:#80e5c4}small{display:block;color:#adc1ba}</style>
<h1>Pixora</h1><p>Make Every Screen Useful.</p><h2>扫码连接 / Scan to connect</h2>''' + svg + '<p><a href="' + html.escape(link, quote=True) + '">在此电脑打开 / Open on this computer</a></p><p>' + html.escape(base) + '''</p>
<small>手机与电脑须在同一局域网，电脑保持运行。二维码包含只读凭据，请勿分享。<br>Use the same LAN; keep this computer running. This QR contains a read-only credential; keep it private.</small>
<p>HTTP 接入仅临时授权；重开需重新扫码。HTTPS 与手机安装需另行配置受信任证书。<br>HTTP pairing lasts for this page only. Re-scan after reopening. Trusted HTTPS is needed for persistent login and full PWA support.</p></html>'''
    fd = os.open(page, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(content)
    os.chmod(page, 0o600)
    return page


def discover_lan():
    # UDP connect selects the route without sending packets or requiring a reply.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(('192.0.2.1', 9))
        candidate = probe.getsockname()[0]
    address = ipaddress.IPv4Address(candidate)
    if not address.is_private or address.is_loopback or address.is_link_local or address.is_unspecified:
        raise ValueError('no private LAN route')
    return candidate


def codex_executable():
    explicit = os.environ.get('PIXORA_CODEX_BIN') or os.environ.get('APM_CODEX_BIN')
    if explicit:
        return explicit
    found = shutil.which('codex')
    if found:
        return found
    if sys.platform == 'darwin':
        for app in [Path('/Applications/ChatGPT.app'), Path.home()/'Applications/ChatGPT.app']:
            candidate = app/'Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    return 'codex'


def main():
    parser = argparse.ArgumentParser(description='Pixora local computer + optional trusted LAN screen')
    parser.add_argument('--data-dir', type=Path, default=Path.home()/'.pixora'/'local')
    parser.add_argument('--web-dir', type=Path, default=Path('web/dist'))
    parser.add_argument('--port', type=int, default=8024)
    parser.add_argument('--lan-address', help='Explicit private IPv4 on this computer; default is localhost only')
    parser.add_argument('--lan-auto', action='store_true', help='Use this computer’s current private LAN/hotspot address')
    parser.add_argument('--cert', type=Path)
    parser.add_argument('--key', type=Path)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be 1–65535')
    if bool(args.cert) != bool(args.key):
        parser.error('--cert and --key must be supplied together')
    if args.lan_auto and args.lan_address:
        parser.error('select --lan-auto or --lan-address, not both')
    if args.lan_auto:
        try:
            args.lan_address = discover_lan()
        except (OSError, ValueError):
            parser.error('No private network detected. Connect Wi-Fi/hotspot or omit --lan-auto for computer-only use.')
    host = '127.0.0.1'
    if args.lan_address:
        try:
            address = ipaddress.IPv4Address(args.lan_address)
            if not address.is_private or address.is_loopback or address.is_unspecified or address.is_link_local or address.is_multicast:
                raise ValueError()
            host = str(address)
        except ValueError:
            parser.error('select a private LAN IPv4 address assigned to this computer')
    if not (args.web_dir/'index.html').is_file():
        parser.error('Web build missing. Run npm --prefix web ci && npm --prefix web run build first.')
    if args.cert and (not args.cert.is_file() or not args.key.is_file()):
        parser.error('certificate/key file missing')
    # Fail before provisioning if another process owns the selected address/port.
    try:
        with socket.socket() as probe:
            probe.bind((host, args.port))
        values = prepare(args.data_dir)
    except (OSError, ValueError):
        parser.error('Cannot initialize local service: check port, private directory and local.json; details suppressed.')
    directory = args.data_dir.expanduser().resolve()
    scheme = 'https' if args.cert else 'http'
    base = f'{scheme}://{host}:{args.port}'
    env = dict(os.environ, PIXORA_DB=str(directory/'pixora.sqlite'), PIXORA_READ_TOKEN=values['read'],
               PIXORA_WRITE_TOKEN=values['write'], PIXORA_ALLOW_LEGACY_READ_TOKEN='false',
               PIXORA_WEB_DIR=str(args.web_dir.resolve()), PIXORA_LOCAL_ACTIVITY='true', PIXORA_CODEX_BIN=codex_executable())
    server = [sys.executable, '-m', 'uvicorn', 'pixora.server:create_app', '--factory', '--host', host,
              '--port', str(args.port), '--no-access-log', '--no-proxy-headers']
    if args.cert:
        server += ['--ssl-certfile', str(args.cert.resolve()), '--ssl-keyfile', str(args.key.resolve())]
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    processes = []
    old_umask = os.umask(0o077)
    try:
        # No credentials in process arguments, console output or HTTP query strings.
        processes.append(subprocess.Popen(server, env=env))
        import httpx
        ready = False
        for _ in range(100):
            if processes[0].poll() is not None:
                raise RuntimeError('server exited')
            try:
                with httpx.Client(trust_env=False, verify=str(args.cert.resolve()) if args.cert else True, timeout=.5) as client:
                    ready = client.get(base+'/healthz').status_code == 200
                if ready:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(.1)
        if not ready:
            raise RuntimeError('server startup/HTTPS verification failed')
        # HTTPS collection verifies the supplied certificate; LAN HTTP is explicit opt-in.
        if args.cert:
            env['SSL_CERT_FILE'] = str(args.cert.resolve())
        collector = [sys.executable, '-m', 'pixora.collector', '--server', base]
        if args.cert:
            collector += ['--ca-file', str(args.cert.resolve())]
        if args.lan_address and not args.cert:
            collector.append('--allow-private-http')
        processes.append(subprocess.Popen(collector, env=env))
        page = pairing_page(directory, base, values['screen'])
        print(f'Pixora ready / 已启动: {base}\nPrivate pairing page / 私有配对页: {page}\nCtrl+C stops server and collector / 停止服务与采集', flush=True)
        if host == '127.0.0.1':
            print('Localhost only / 仅此电脑。手机接入需显式指定 --lan-address。', flush=True)
        elif not args.cert:
            print('Trusted LAN HTTP only / 仅可信局域网临时显示；勿映射公网端口。', flush=True)
        if not args.no_browser:
            webbrowser.open(page.as_uri())
        while all(p.poll() is None for p in processes):
            time.sleep(.5)
        raise RuntimeError('a local service stopped')
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError, ValueError):
        print('Pixora stopped unexpectedly; check startup, certificate and Codex sign-in. / 启动异常，请检查证书和 Codex 登录。', file=sys.stderr)
        raise SystemExit(1)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
        os.umask(old_umask)


if __name__ == '__main__':
    main()
