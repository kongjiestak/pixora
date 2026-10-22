# Pixora first-screen prototype — V0.5 dev1

[English](README.md) | [简体中文](README.zh-CN.md)

**Prototype, not hardware-accepted firmware.** The first target is Waveshare ESP32-S3-Touch-AMOLED-2.16 (480×480, CO5300, 16 MiB Flash, 8 MiB PSRAM). A real unit was read-identified and its entire original flash was privately backed up and digest-verified before any write. Chip identification alone does not verify panel/touch compatibility. Do not flash another board using this layout.

This original client uses the Apache-2.0 Waveshare BSP, LVGL and ESP-IDF instead of forking the full VibePulse application. Its protocol requires synthetic placeholder totals when only quotas are available; the Pixora client can directly use the already authorized API without those mappings. No VibePulse code or assets are included.

## Implemented in source

- HTTPS GET `/api/v1/device`, scoped display Bearer token, 30-second polling; existing server policy/revocation applies. Certificate bundle and hostname verification remain enabled; redirects disabled. No write/control or upstream account credentials.
- Two Codex remaining-quota rings, reset countdown, collection age and stale/offline states. Unknown stays `--`, not zero. Weekly-only grants never appear in the short-window slot. Cached readings age locally; 401/403 clears displayed quotas. No Claude, task activity, weather, profile/theme sync, OTA, language selection or native watch support is claimed.
- Phone Wi-Fi setup: device displays a random WPA2 setup-network QR; join it and open `http://192.168.4.1`. This initial prototype requires manually opening that address, not a finished captive portal. The page is bilingual; the screen currently uses English built-in fonts.
- Service/token loaded from private NVS provisioning. Advanced setup can replace them but never returns saved credentials. Changing the server requires a new token. Network settings are stored in NVS; the prototype does not claim encrypted flash storage. Setup requests are accepted only through the AP local address, not the station/LAN interface, and form changes require the setup page's Origin.
- Missing initial configuration opens setup; saved networks retry automatically during outages. Touch Wi-Fi / Setup to correct an invalid saved network. Setup remains active until Save/restart, with no automatic expiry yet. Wrong Wi-Fi settings may be saved; the fallback permits retry. Initial setup/security/heap/rotation/24-hour behavior still needs physical acceptance.

## Build with pinned dependencies

Activate ESP-IDF **v5.5.5**, with CMake/Ninja and the esp32s3 tools installed. Dependencies are pinned by `main/idf_component.yml` plus `dependencies.lock` (keep the lockfile). No secrets in source/config defaults:

```sh
cd firmware/esp32
idf.py set-target esp32s3
idf.py build
CC=clang ./host-tests/run.sh
```

The host test uses the same C parser and IDF cJSON, with Address/UndefinedBehavior Sanitizers. It checks missing/zero, weekly scope, truncation, stale/future observations and timestamp offsets. This is not a substitute for Wi-Fi/TLS/display tests on the board.

## Private provisioning and recovery

An administrator creates a **separate real Codex display device**, not a legacy/admin/collector key. Keep its JSON outside the repository with permissions 600:

```json
{"server":"https://your-pixora.example","token":"SCOPED_DISPLAY_TOKEN_FROM_YOUR_ADMINISTRATOR"}
```

Generate private NVS under your protected deployment directory; do not publish it:

```sh
python tools/provision_nvs.py --config /private/config.json --output /private/pixora-nvs.private.bin
```

The tool requires a private config and refuses an output inside the source repository. Firmware binaries contain no user credentials. The NVS image goes at `0x9000`, size `0x6000`; app at `0x10000`. Use `build/flash_args` for exact bootloader/partition/app offsets, then provision private NVS. This replaces the old partition table and settings, so preserve a **full-flash backup before flashing**. A full backup may contain private Wi-Fi or application credentials; do not upload it. Never burn eFuses or disable security protections to make this prototype run.

Restore only the matching unit, with its original full dump and original flash parameters verified. Read/digest-verify the backup before writing, retain USB ROM-download recovery and check the board power requirements. The attached-unit backup/recovery instructions live outside this public source tree.

## Acceptance gate

Physical display/touch, phone setup, actual certificate validation, authenticated read, phone/hardware same-sample quota equality, revocation clearing, Wi-Fi loss/recovery, cold boot, server restart, Mac off with home collector on and 24-hour stability must each be recorded. Public CI/build success or chip identification does not satisfy that gate. No stable Release is created.

See [third-party notices](THIRD_PARTY.md) and [V0.5 scope](../../docs/V0.5.md).
