# Deployment and APM migration

## Local / PVE

Follow README on Python 3.11+ and Node 22+. `scripts/setup_env.py` creates random tokens with mode 0600, refusing to replace an existing `.env`. For a new clean checkout copy no real config from another machine. `.env.example` deliberately contains blank token placeholders; the service fails closed until generated tokens exist.

For Docker: run `python3 scripts/setup_env.py`, `docker compose config --quiet`, `docker compose up -d --build`. Default host bind is `127.0.0.1`, service port 8000, non-root runtime, named volume `pixora-data`, health check `/healthz`. `docker compose down` keeps the volume; `down -v` removes it. Container runtime and deployment acceptance are documented in VERIFICATION.md.

On PVE prefer a Debian/Ubuntu VM running Docker, not the hypervisor management host. The Mac collector pushes outbound over HTTPS or an explicitly trusted encrypted VPN. A sleeping Mac stops collection; snapshots become stale. Home uptime, VPN, CGNAT and firewall determine reachability. An actual PVE-hosted Debian Docker deployment has now passed the bounded checks in [PVE_ACCEPTANCE.md](PVE_ACCEPTANCE.md); no VPS is required or verified. Japan VPS optional, not required.

For a private LAN/VPN choose `PIXORA_BIND` deliberately and restrict access. PWA installation requires secure context (HTTPS or localhost); phone LAN HTTP does not provide full PWA behavior. Do not disable certificate checks or put tokens in URLs. A trusted TLS reverse proxy may expose the web app; this does not expose the local Codex process. Add proxy limits and exclude Authorization from logs.

## Existing APM checkout

Git history and the legacy APM release are retained. Import path is `pixora`, command `pixora-collect`, Python distribution `pixora-dashboard` (no PyPI publication implied). `apm-collect` is a CLI alias; `APM_*` variables are fallbacks. `PIXORA_*` wins, even if empty. Reinstall with `pip install --no-deps .` after updating.

Default local DB changes from `data/apm.sqlite` to `data/pixora.sqlite`. **Do not silently start with an empty DB or overwrite the old one**: set `PIXORA_DB` to the old file if retaining it, or use SQLite's backup API to make a stopped/consistent copy. v1 snapshot rows remain readable; observed_at is retained and collected_at added in the read response.

Docker changes the volume name from `apm-data` to `pixora-data`; keep the old volume. Stop the old service, back up SQLite including WAL safely, and explicitly attach the existing volume via a Compose override (use its actual Docker volume name), or restore a consistent backup into the new volume with UID 10001 write access. Never `down -v` during migration. Old LaunchAgent examples are replaced with `examples/org.pixora.collector.plist`; update absolute paths and private env file before loading. No LaunchAgent is automatically installed.

Browser settings migrate from `apm-device` when `pixora-device` is absent; tokens and observations were never persisted. Local locale preference is `pixora-locale`. The service worker removes only its own legacy shell cache.

## Backups and revocation

Use SQLite online backup or stop before copying the database; do not ignore WAL. Back up tokens separately. One service corresponds to one Codex account: account switching should use a new DB/instance to avoid mixed observations. Legacy global token rotation requires restart. Scoped-device tokens support immediate revocation and provider/mode restrictions; see [DEVICES.md](DEVICES.md). Backups include device token digests and scope policies; treat them as private.

## Trusted LAN HTTPS

See [HTTPS.md](HTTPS.md) for DNS-01, reverse-proxy, VPN hostname exceptions, scoped-token acceptance and explicit renewal requirements. Actual target TLS 1.3 and browser secure-context/service-worker checks passed on 2026-10-16; physical phones remain unverified.
