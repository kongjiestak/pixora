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

The first container runtime attempt hit a connection reset during immediate startup health probing (after successful tests/build). The CI probe now retries transient startup errors with a 30-second bound and emits container diagnostics on failure; see the actual published run result.

## Actual PVE target, 2026-10-15

See [PVE_ACCEPTANCE.md](PVE_ACCEPTANCE.md) for actual deployment, real Mac roundtrip, container restart persistence and isolated backup/restore results on image commit `993ac50`. This supersedes the earlier PVE-not-deployed row, but physical-phone, secure phone ingress and Mac autostart/sleep gates remain open. The scoped-token increment passed 30 backend + 9 frontend tests and actual Docker CI runtime checks in [run 38753174124](https://github.com/kongjiestak/pixora/actions/runs/38753174124).

## V0.2 development increment, 2026-10-20

Code commit `21832ca`: 53 Python tests, 13 frontend tests and production UI build passed. [CI 39389999268](https://github.com/kongjiestak/pixora/actions/runs/39389999268) passed clean installs, tests, Docker build and runtime smoke. One existing Starlette TestClient deprecation warning remains.

An independent loopback-only VPS beta migrated a private online SQLite copy. Existing v1 snapshot rows, original device rows/scopes and session rows compared equal to the migration backup. An installed, non-editable Python 0.2.0.dev1 package collected two actual Linux host CPU/memory/root-disk observations and delivered them to v2. Latest, pagination and unauthorized requests returned expected results. Restoring the pre-v2 backup to a new path and running the prior v0.1 image read the original quotas successfully. Production health remained OK; production has not been upgraded to v2.

The beta browser rendered real system metrics and two history rows, with no horizontal document overflow at 956×500. This is desktop responsive verification, not iPhone V0.2 acceptance. Test observations are point-in-time samples; continuous collector operation and production promotion remain pending. No formal V0.2 Release is claimed. See [contract, retention and rollback](V0.2.md).

## V0.2 Taste-Skill UI redesign

Applied the upstream app-screen workflow using True-black flat, seed 1899116366, with retained Pixora data hue/system fonts. [Design provenance and critique](design/UI-DIRECTION.md) records the source commit and check substitution. Fifteen frontend tests and production build passed; upstream static lint returned 0 FAIL/0 WARN. CUA browser checks covered 1440/768/390px, EN/ZH, dark/light, real metrics, history, shared-mode clearing and 956×440 display layout. Device and token scope logic was preserved; no schema/backend change in this UI increment. Physical phone approval remains pending. Production is not automatically upgraded by this design preview.


## V0.4 dev3 administrator console (2026-10-21)

- 92 Python tests and 31 frontend tests passed, production Vite build passed; npm reported zero known dependency vulnerabilities at install time. Staged/full-history secret and commit-email audit passed. GitHub CI includes a clean container build/runtime check.
- VPS rollout: additive administrator tables; SQLite backup/current integrity checks passed and all nine original device rows were identical after migration. Existing read scopes were preserved.
- Live isolated QA: two temporary devices, dedicated administrator login, display Cookie, batch publication, stale-revision 409, policy narrowing, denied grant expansion, revocation 401 for Bearer and Cookie, token-free inventory/audit. Both temporary devices were revoked afterward.
- Browser console: actual HTTPS sign-in, filtering, source/form/layout controls and stored server profile loading checked. Narrow portrait overflow checked independently of physical phones. Administrator screen pairing scan on a real phone remains owner acceptance; it is not inferred from API/desktop tests.
- Existing owner confirmation covers themes and city switching; no stable Release is created.
