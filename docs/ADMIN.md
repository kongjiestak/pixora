# Device administration (V0.4 dev3)

[English](ADMIN.md) | [简体中文](ADMIN.zh-CN.md)

Open `/?admin=1`, or Settings → Device management (administrator). The console is a separate administrator capability. It does not accept a display token, collector write token or legacy read token. No default key or unauthenticated bootstrap endpoint exists.

## Bootstrap and recovery

Create a dedicated key **locally on the server**, using the same SQLite path as the running server:

```sh
pixora-admin --db /data/pixora.sqlite create --name owner --days 90
# Docker Compose (inherits PIXORA_DB):
docker compose exec monitor python -m pixora.admin create --name owner --days 90
```

The command returns a secret once. Store it privately, enter it into the HTTPS console and do not paste it into URLs, screenshots, logs or issues. Browser storage never saves the key. There is no reset-by-email or remote key creation. Lost keys can be replaced locally:

```sh
pixora-admin --db /data/pixora.sqlite list
pixora-admin --db /data/pixora.sqlite revoke KEY_ID
```

Only key/session digests are stored. The separate `__Host-pixora_admin` cookie is Secure, HttpOnly, host-only and SameSite Strict. Sessions last at most eight hours or until key expiry/revocation, whichever comes first; five active sessions per key. Every request rechecks key validity. Signing out of management leaves display sessions intact. HTTPS same-origin Origin is required for every browser mutation. Login is limited to 20 attempts/minute/process globally; this is a small self-hosted service, not distributed abuse protection. Reverse proxy hardening remains the operator's responsibility.

## Screens and pairing

The paginated list shows authorization status, expiry, original source grants, configuration revision and unexpired session count. **Active is authorization status, not proof of an online screen.** Use a separate pairing token per physical device; previously reused codes cannot distinguish individual phones. Existing devices, scopes and local customizations are preserved on upgrade.

Add device selects source scopes, name and 1–365-day expiry; real mode only in the console. Demo-only provisioning remains available via local CLI. A maximum of 200 unrevoked, unexpired devices may be created by this console. Unsupported upstream sources remain unavailable, never fabricated.

Creation returns a new display token once and generates its QR locally in the browser using bundled [node-qrcode (MIT)](https://github.com/soldair/node-qrcode). No external QR service receives it. The fragment pairing link is cleared by the display on arrival. The code is a reusable bearer credential **until device expiry or revocation**, not a single-use invitation. The console hides it on dismissal, backgrounding or after ten minutes, without revoking it. Never publicly share it. Revoke/recreate if it is lost; list endpoints cannot recover raw tokens.

Revocation has an explicit confirmation, invalidates the token and removes all its sessions immediately. It cannot erase already rendered/offline content on another screen. Naming and policy edits require a matching revision. Policies only narrow original grants; advanced JSON uses the existing [V0.4 contract](V0.4.md), with fail-closed validation. The initial UI has no visual field-policy builder.

## Multi-screen layout publication

Select up to 20 healthy active devices, edit a layout draft or import an exported display profile, then Publish. All targets and revisions are checked in one SQLite transaction: any stale, revoked, expired or corrupt target aborts the entire batch. Only profiles change; source grants and restrictive policies remain intact. The same layout can be assigned to multiple screens; load another device's layout to reuse it. This is a constrained profile editor, not free-form composition or drag/drop.

Display clients check server recommendations during the 30-second data refresh. **Browser-local layout overrides keep precedence.** Select Restore server recommendation on a customized phone to follow remote publications. This console deliberately does not force-delete another browser's local preferences. The import supports all validated profile fields, including arbitrary resolved weather place IDs; city quick choices cover the existing collector default, Shanghai and Houston.

The bounded audit table retains 1000 events and returns the latest 100; records actor key ID, time, action, device ID and revision/scope summary, not raw credentials, observation content or IPs. This is operational history, not a tamper-proof compliance log.

## Deployment and rollback

Dev3 adds `admin_keys`, `admin_sessions`, `admin_audit` tables without modifying existing device rows. Back up SQLite using its backup API before upgrading. Rolling back to dev2 removes web administration but preserves the existing profile-policy enforcement and revocation flags. Keep old profiles/policies compatible and never restore a pre-revocation database casually. The pre-V0.4 privacy-sensitive rollback restriction still applies. Key backups are sensitive; local server filesystem access remains full administrator authority.

Remaining: one-use invitation exchange, forced remote layout adoption, online presence, visual policy editor, arbitrary widget composition and stronger multi-user administrator roles. No stable release or hardware acceptance is claimed.
