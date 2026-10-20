# Implementation and acceptance tasks

The supplied publication kit was reviewed against the existing implementation; it was not used as evidence of completed features.

| Work | Implemented evidence | Acceptance remaining |
|---|---|---|
| Brand migration | Pixora UI, package, PWA, docs and examples; APM config aliases | Provisional brand legal clearance outside technical release |
| Data | Codex/demo registry, structured status/source/time/stale, SQLite | More upstream versions/accounts and recovery tests |
| I18N | Vue I18n EN/ZH, locale detection/switch/fallback/Intl | Physical-device language/layout review |
| Web | Reusable widgets, themes, presets, local device settings, display mode | Old Android/iOS matrix, long-running kiosk |
| Privacy | Read/write tokens, local shared filtering, secret scan | Server per-device ACL and revocation |
| Self-host | FastAPI, Compose, non-root Docker | PVE and physical end-to-end acceptance |
| Open source | MIT + notices, bilingual README, contribution and issue/PR templates | Community feedback |

Publication policy: preserve commits and historical tags/releases, no force push. Candidate organization must not be assumed owned or available. Prefer the authorized existing account. Publish repository as Early Development until acceptance is complete; no new formal Release for this migration.


V0.2 implementation and acceptance contract: [V0.2.md](V0.2.md). Latest status: numeric observation/history, reversible migration, Linux system connector and private system Widget implemented; deployment and device verification tracked explicitly. Existing device-scoped ACL/revocation, VPS/home deployments and iPhone installation have since passed their recorded checks; earlier table entries are historical baseline.
