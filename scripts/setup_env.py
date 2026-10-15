"""Generate local tokens; never commit the output."""
from pathlib import Path
import secrets
import os
p = Path(".env")
fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
with os.fdopen(fd, "w") as f:
    f.write(f"APM_READ_TOKEN={secrets.token_urlsafe(32)}\nAPM_WRITE_TOKEN={secrets.token_urlsafe(32)}\n")
print("Created .env with distinct random tokens (0600)")
