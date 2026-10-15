# Pixora verification — 2026-10-15

Current state: **Early Development**, not accepted V0.1. Tests below were actually executed; generated support matrices are not evidence.

| Check | Observed result |
|---|---|
| Python install after package rename | Passed, `pixora-dashboard` 0.1.0.dev1 / namespace pixora |
| Backend tests | 21 passed on local Python 3.13, pytest 9.1.1; one upstream Starlette TestClient/httpx deprecation warning; includes 2 commit-email regression cases |
| Frontend tests | 9 passed, including actual Vue I18n switching/fallback, key parity, locale choice, disabled/corrupt storage, formatting, clock-based staleness and shared filtering |
| Production build | Passed on Node 24 (supported floor 22+); JS about 141 KB / gzip 52 KB |
| Real Codex query | Passed again: 2 windows, current CLI account/rateLimits/read; account values not published |
| Real data roundtrip | Passed: connector → authenticated local HTTP POST → SQLite → read-only API; ChatGPT stays unavailable |
| Demo / static smoke | Passed: collector demo upload, read/write boundaries, demo/real isolation, collection timestamp and PWA assets |
| Browser language/display | Passed in desktop in-app Chromium: EN/ZH switching, preference after reload, shared clears/hides private data, Kiosk entry and exit controls |
| Responsive | 375×812 and 812×375 browser viewports checked; no horizontal document overflow. These are viewport tests, not real-phone certification |
| Offline shell | Passed: temporarily offline network + reload still renders public UI; network restored. No API observation cache claimed |
| npm audit | 0 known vulnerabilities after installing locked dependencies |
| Python advisories | pip-audit pinned requirements: 0 known vulnerabilities after fixing pytest advisory |
| License inventory | Actual Python/npm metadata inspected; npm runtime notices retained; devtools license obtained from matching upstream tag |
| Secret/history scan | Basic staged and reachable-history scan passed; no tested sensitive patterns. Not a professional audit |
| Docker local | CLI exists; daemon unavailable. Compose is checked with generated random test tokens. Local container build/runtime cannot be claimed |
| New CI | Pipeline includes Python/Node clean install/tests/build, Docker build and container startup/demo/API smoke. Consult actual [Actions](https://github.com/kongjiestak/pixora/actions) result for the published commit |
| PVE / optional VPS | Not deployed or verified |
| Physical Android / iPhone / iPad | Installation, old-system compatibility, long-running wake/background/restore not verified |

Clean exported source verification passed independently: new venv, pinned dependency install, non-editable project installation, generated .env (0600), 19 backend tests, 9 frontend tests, production build, Compose config and a running server → CLI demo → SQLite/API smoke. Dependencies are pinned but do not yet include wheel hashes or a signed SBOM. Codex upstream behavior and working-brand legal clearance remain outside the guarantees of this build.

Privacy cleanup: original author/committer personal email was replaced in the publicly referenced branch/tag history with owner authorization. A fresh remote mirror downloaded 65 objects and none contained the original email. Legacy Release/assets were retained. Old GitHub objects may remain accessible by SHA until separately handled; no complete cache erasure is claimed. The original backup is private and not distributed.
