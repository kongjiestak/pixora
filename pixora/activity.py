"""Read only local Codex lifecycle metadata; never export prompts, paths or thread IDs.
This is an experimental local-rollout adapter, not a global account activity API.
"""
from datetime import datetime
import json
from pathlib import Path
import time


def _epoch(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError, AttributeError):
        return 0


def observe_activity(root=None, now=None):
    now = time.time() if now is None else now
    root = Path(root) if root is not None else Path.home() / '.codex' / 'sessions'
    result = {'source': 'codex-local-events', 'state': 'unknown',
              'observed_at': int(now), 'expires_at': int(now) + 15}
    try:
        files = sorted(root.rglob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)[:12]
        states = []
        for path in files:
            stat = path.stat()
            # A dead/stalled writer must not keep the robot working indefinitely.
            if stat.st_mtime > now + 60 or now - stat.st_mtime > 90:
                continue
            with path.open('rb') as stream:
                stream.seek(max(0, stat.st_size - 1048576))
                rows = stream.read(1048576).splitlines()
            lifecycle = None
            for row in rows:
                try:
                    event = json.loads(row)
                except (ValueError, UnicodeDecodeError):
                    continue
                if not isinstance(event, dict) or event.get('type') != 'event_msg':
                    continue
                payload = event.get('payload')
                if not isinstance(payload, dict):
                    continue
                kind = payload.get('type')
                stamp = _epoch(event.get('timestamp'))
                if kind in ('task_started', 'task_complete', 'turn_aborted', 'task_failed') and 0 < stamp <= now + 60:
                    lifecycle = kind
            if lifecycle:
                states.append('working' if lifecycle == 'task_started' else 'error' if lifecycle == 'task_failed' else 'idle')
        if states:
            result['state'] = 'working' if 'working' in states else 'error' if 'error' in states else 'idle'
        return result
    except OSError:
        return result
