> Current direction / 当前方向（2026-10-22）：V0.4 owner accepted; V0.5 first ESP32 + phone onboarding; V0.6 activity/minimal alerts + Watch 8 notification trial; V0.7 novice usability; V1.0 stable delivery. Old personal-information expansion is cancelled. See [V0.5](V0.5.md) / [中文](V0.5.zh-CN.md). Older milestone rows below are historical context, not the current plan.

# Pixora roadmap

[English](ROADMAP.md) | [简体中文](ROADMAP.zh-CN.md)

Acceptance-driven, no promised dates. Current status: **Early Development**, package version `0.4.0.dev1` is development metadata, not an accepted release.

| Milestone | Scope | Gate / status |
|---|---|---|
| V0.1 | Real Codex → API → web; EN/ZH; widgets; PWA/Kiosk; trusted local privacy | Implemented; VPS deployment, iPhone PWA and home collector recovery accepted. No stable Pixora Release |
| V0.2 | Generic Observation v2, SQLite migration, PVE/host read-only connector, history | Implemented on main; migration/rollback, real Linux host widget/history and iPhone + Android display accepted; dedicated PVE API deferred |
| V0.3 | CI/GitHub and calendar/tasks/weather/RSS | In development: public GitHub, RSS/Atom and local tasks implemented; local calendar/weather and quota-ring display implemented; account sync deferred, task editor paused per owner |
| V0.4 | Layout editor, server device config, per-device scoped tokens and revocation | In progress: constrained Orbit editor, administrator-published device profiles, entity/metric/window/entry policies; web device administration and remote publication pending |
| V0.5 | Private mail summaries, life/bill reminders, travel, budgets, goals | Planned; minimal data retention, connector revocation and screen lock |
| V0.7 | Authorized automation and Home Assistant interaction | Planned; separate command permissions, audit, confirmation and idempotency |
| V0.9 | ESP32 multiple screens/e-paper, low-end optimization | Planned; hardware/protocol tests, recovery and update compatibility |
| V1.0 | Stable SDK/protocol, migrations, permission model, reproducible releases | Planned; platform matrix, recovery drills and security review |

NFC, MagSafe and custom PCB are separate future experiments. The legacy APM `v0.1.0` pre-release is retained as history and is not evidence of Pixora acceptance.

## 2026-10-15 progress / 进度更新

Provider/mode scoped device tokens, digest-only storage, expiry and live revocation are implemented ahead of the V0.4 milestone. Local CLI administration only; pairing UI, field-level policies and server layout synchronization remain planned. Linux Docker runtime CI passed for the previous baseline; this increment is subject to its own CI. Physical-phone/PVE acceptance remains open.


## V0.2 development update / 开发进度

Observation v2, additive migration with private backup, v1 quota backfill, Linux CPU/memory/root-disk metrics, private system Widget and bounded paginated history are implemented on the V0.2 development branch. Dedicated PVE API integration is deferred; the first connector is Linux host read-only collection. Existing device scopes remain unchanged. See [contracts and rollback](V0.2.md). Deployment and phone acceptance are separate gates; no stable V0.2 Release is claimed.

V0.1 operations now include VPS HTTPS, independent home collection, verified recovery, certificate renewal and isolated SQLite restore. User iPhone installation/session/rotation/continued-display checks passed; Android 13 portrait/landscape display passed owner acceptance; Android installation remains untested. Earlier status rows above are historical baseline descriptions.

## V0.4 first increment / 首轮增量

See [device profiles, restrictive policies and rollback boundary](V0.4.md). V0.3 Orbit/settings were accepted on iPhone; V0.4 has its own acceptance gate. No stable Release is claimed.


## V0.4 dev3 update / 更新

Implemented: administrator-only web device inventory, per-device pairing/revocation, restrictive policy editing and atomic batch profile publication. Local overrides keep precedence; arbitrary widget composition, online presence and one-use invitations remain future work. See [administrator guide](ADMIN.md) / [管理员指南](ADMIN.zh-CN.md). Deployment and owner acceptance are separate from automated checks. Package version 0.4.0.dev3 remains Early Development.


## 2026-10-23 direction update / 最新方向

V0.6 quota reminders / Watch are paused by owner. V0.7 now prioritizes local computer startup, QR phone access and unified companion displays, followed by USB request-specific controls, then push-to-talk. This supersedes older ordering; implementation and remaining gates: [V0.7](V0.7.md) / [中文](V0.7.zh-CN.md).
