# Pixora roadmap

[English](ROADMAP.md) | [简体中文](ROADMAP.zh-CN.md)

Acceptance-driven, no promised dates. Current status: **Early Development**, package version `0.1.0.dev1` is development metadata, not an accepted release.

| Milestone | Scope | Gate / status |
|---|---|---|
| V0.1 | Real Codex → API → web; EN/ZH; widgets; PWA/Kiosk; trusted local privacy | Implemented foundation. Physical phone PWA, deployment/runtime and long-running recovery acceptance remain open. No new Pixora Release |
| V0.2 | Generic Observation v2, SQLite migration, PVE/host read-only connector, history | Planned; migration rollback + first real system widget |
| V0.3 | CI/GitHub and calendar/tasks/weather/RSS | Planned; real source timestamps, privacy and compatibility matrix |
| V0.4 | Layout editor, server device config, per-device scoped tokens and revocation | Planned; public devices must not retrieve private fields via API |
| V0.5 | Private mail summaries, life/bill reminders, travel, budgets, goals | Planned; minimal data retention, connector revocation and screen lock |
| V0.7 | Authorized automation and Home Assistant interaction | Planned; separate command permissions, audit, confirmation and idempotency |
| V0.9 | ESP32 multiple screens/e-paper, low-end optimization | Planned; hardware/protocol tests, recovery and update compatibility |
| V1.0 | Stable SDK/protocol, migrations, permission model, reproducible releases | Planned; platform matrix, recovery drills and security review |

NFC, MagSafe and custom PCB are separate future experiments. The legacy APM `v0.1.0` pre-release is retained as history and is not evidence of Pixora acceptance.
