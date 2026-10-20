# Pixora architecture

[English](ARCHITECTURE.md) | [简体中文](ARCHITECTURE.zh-CN.md)

Software-first monorepo. Browser/PWA is a first-class display; a future ESP32 reads the same versioned device API. Five modes are extensibility categories, not five completed applications.

```mermaid
flowchart LR
  CLI[Mac connector registry] -->|normalized quota / write token| API[FastAPI]
  API --> DB[(SQLite WAL)]
  DB --> API
  API -->|read token / source / timestamps / stale| UI[Vue 3 + Vue I18n]
  UI --> W[Widget registry + presets]
  W --> P[Browser / phone / tablet PWA]
  API -. future .-> ESP[ESP32]
```

## Implemented contracts

- `Collector.collect() -> list[Snapshot | Observation]`: allowlisted Codex, demo and Linux system collectors. No arbitrary remote plugin loading.
- Snapshot v1: `provider`, `source`, `mode`, `status`, `observed_at` (ingest alias `collected_at`), `windows`, optional `reason_code`. API returns both timestamp names plus receipt time, age and stale. Quota schema intentionally limits providers; it is not a universal metrics schema.
- Widget registry: `{titleKey, mode, sensitivity}`. Vue widget inputs `{data, clock, connected}`; display logic uses locale keys and raw structured fields. UTC storage, local-zone Intl presentation. `public` widgets can display without quota credentials; sharing clears token and pending requests.
- SQLite retains v1 latest provider/mode snapshots plus bounded v2 metric history (1,000 records/stream). Additive migration makes a private pre-v2 backup and backfills current snapshots. Transactions reject older replayed observations; connections close after each operation. Single trust domain and separate read/write token capabilities.
- Three layouts, light/dark themes and device configuration are browser-local. No server-managed device registry or drag/drop editor.
- PWA precaches public shell and built assets. No API/token/observation persistence. HTTPS scoped devices may restore a Secure HttpOnly session; manual localhost tokens remain in memory. HTTPS/localhost required. Screen wake and full-screen are browser-dependent.

## Future contracts and boundaries

Numeric Observation v2 now separates connector/entity ID, category, mode, metrics/units, collection/expiry, source and sensitivity, with migration and v1 compatibility. Latest and history APIs apply existing scopes. See [V0.2](V0.2.md). External plugin SDK/configuration is still planned.

AI / system / developer / personal / automation widgets may share one layout. PVE/NAS, CI, calendar/tasks/weather, private summaries and Home Assistant connectors are planned. Commands require a separate authorized, audited, idempotent channel; read tokens will never implicitly gain write/control capabilities.

Per-device provider/mode scopes, expiry and immediate revocation are implemented; field-level ACL/public projections remain planned. Local UI filtering is not this protection.

Run on a Mac alone, or keep the service in a PVE Linux VM while the Mac pushes outbound observations. Mac sleep makes data stale. A VPS is optional. ESP32 sizes, NFC, MagSafe and PCB work are future hardware exploration, not current compatibility claims.
