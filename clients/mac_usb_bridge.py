"""Bridge a scoped HTTPS Pixora feed to its matching, explicitly enabled USB screen.
Requires pyserial==3.5. No Wi-Fi or upstream account passwords are needed.
"""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import ssl
import time
import urllib.error
import urllib.request


def proof(token, message):
    return hmac.new(token.encode(), message, hashlib.sha256).hexdigest()


def hello_nonce(line, token):
    match = re.search(rb'PXUSB_HELLO ([0-9a-f]{32}) ([0-9a-f]{64})(?:\s|$)', line)
    if match and hmac.compare_digest(match[2].decode(), proof(token, b'hello ' + match[1])):
        return match[1].decode()
    return None


def make_frame(payload, token, nonce, epoch, sequence):
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    if len(body) > 16384 or not re.fullmatch('[0-9a-f]{32}', nonce):
        raise ValueError('Invalid frame')
    header = f'{nonce} {epoch} {sequence}'
    signature = proof(token, b'data ' + header.encode() + b'\n' + body)
    return b'PXUSB1 ' + header.encode() + b' ' + signature.encode() + b' ' + body + b'\n'


def fetch(config):
    request = urllib.request.Request(config['server'].rstrip('/') + '/api/v1/device',
                                     headers={'Authorization': 'Bearer ' + config['token'], 'Accept': 'application/json'})
    # Do not forward the bearer to redirect destinations, even HTTPS ones.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context()), NoRedirect())
    try:
        with opener.open(request, timeout=12) as response:
            raw = response.read(16385)
        if len(raw) > 16384:
            raise ValueError('Feed too large')
        value = json.loads(raw)
        if value.get('mode') != 'real' or value.get('device_id') != config['device_id']:
            raise ValueError('Device scope mismatch')
        # Same scoped token, same verified origin; never import unrelated observations.
        request = urllib.request.Request(config['server'].rstrip('/') + '/api/v2/observations',
            headers={'Authorization': 'Bearer ' + config['token'], 'Accept': 'application/json'})
        value["observations"] = [{"provider": "weather", "status": "error"}]
        try:
            with opener.open(request, timeout=12) as response:
                raw_weather = response.read(16385)
            if len(raw_weather) <= 16384:
                weather = json.loads(raw_weather)
                if weather.get('schema_version') == 2:
                    value['observations'] = [o for o in weather.get('observations', [])
                        if isinstance(o, dict) and o.get('provider') == 'weather'][:1]
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                return {'event': 'revoked'}
        except (OSError, ValueError, TypeError):
            pass  # A weather failure must not erase otherwise valid quota data.
        return value
    except urllib.error.HTTPError as error:
        return {'event': 'revoked' if error.code in (401, 403) else 'offline'}
    except (OSError, ValueError):
        return {'event': 'offline'}


def run(config, once=False):
    import serial
    from serial.tools import list_ports
    while True:
        try:
            with serial.Serial(port=None, baudrate=115200, timeout=0.2, write_timeout=5) as connection:
                port = config['port']
                if config.get('usb_serial'):
                    matches = [p.device for p in list_ports.comports() if p.serial_number == config['usb_serial'] and p.vid == 0x303A]
                    if len(matches) != 1:
                        raise OSError('Matching physical USB screen not present')
                    port = matches[0]
                connection.port = port; connection.dtr = False; connection.rts = False; connection.open()
                nonce = None; sequence = 0; due = 0; feed_due = 0; cached_feed = None; ack_deadline = None; deadline = time.monotonic() + 40
                print('Waiting for authenticated USB screen', flush=True)
                while True:
                    line = connection.read_until(b'\n', 2048)
                    metric = re.search(rb'pixora_ui: refresh samples=(\d+) mean_ms=(\d+) max_ms=(\d+)', line)
                    if metric:
                        print('Display refresh: samples=%s mean_ms=%s max_ms=%s' % tuple(x.decode() for x in metric.groups()), flush=True)
                    navigation = re.search(rb'pixora_ui: navigation (action=\d+ page=\d+|ready page=\d+ face=\d+ build_ms=\d+)', line)
                    if navigation:
                        print('Display navigation: ' + navigation[1].decode(), flush=True)
                    candidate = hello_nonce(line, config['token'])
                    if candidate and candidate != nonce:
                        nonce = candidate; sequence = int(time.time()); due = 0
                        print('Matching USB screen authenticated', flush=True)
                    if not nonce and time.monotonic() > deadline:

                        if once:
                            raise OSError('No matching enabled USB screen')
                        print('Enable Mac USB on the matching screen to start', flush=True)
                        deadline = time.monotonic() + 60
                    if nonce and time.monotonic() >= due:
                        sequence += 1
                        if cached_feed is None or time.monotonic() >= feed_due:
                            cached_feed = fetch(config); feed_due = time.monotonic() + 30
                        payload = dict(cached_feed)
                        if config.get('activity_enabled') and 'event' not in payload and any(isinstance(p, dict) and p.get('provider') == 'codex' for p in payload.get('providers', [])):
                            from codex_activity import observe_activity
                            payload['activity'] = observe_activity()
                        connection.write(make_frame(payload, config['token'], nonce, int(time.time()), sequence)); connection.flush()
                        due = time.monotonic() + (5 if config.get('activity_enabled') else 30)
                        ack_deadline = time.monotonic() + 15
                        print('Sent scoped feed' if 'event' not in payload else 'Sent ' + payload['event'] + ' status', flush=True)
                    if once and ack_deadline and time.monotonic() > ack_deadline:
                        raise OSError('No signed frame acknowledgement')
                    if nonce and re.search(rb'PXUSB_ACK ' + str(sequence).encode() + rb' (data|revoked|offline)\b', line):
                        print('Screen acknowledged signed frame', flush=True)
                        if once:
                            return
        except (OSError, serial.SerialException):
            print('USB unavailable; retrying in 5 seconds', flush=True)
            if once:
                raise SystemExit(1)
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if args.config.stat().st_mode & 0o077:
        parser.error('Configuration must be private (chmod 600)')
    config = json.loads(args.config.read_text())
    from urllib.parse import urlsplit
    url = urlsplit(config['server'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        parser.error('A plain HTTPS server origin is required')
    if not re.fullmatch('[A-Za-z0-9_-]{32,128}', config['token']) or not re.fullmatch('[0-9a-f]{24}', config['device_id']):
        parser.error('A scoped display device configuration is required')
    run(config, args.once)


if __name__ == '__main__':
    main()
