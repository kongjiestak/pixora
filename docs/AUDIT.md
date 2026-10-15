# Pixora migration and publication audit — 2026-10-15

## Before changes

Existing repo: `kongjiestak/ai-pocket-monitor`, two historical commits, legacy APM v0.1.0 pre-release. Clean local worktree. Existing FastAPI/SQLite/Vue/PWA quota loop worked. UI strings were mostly hardcoded Chinese; generic metrics, server device ACL, complete personal information/control and ESP32 were absent. The old broad “V0.1” label did not establish full device acceptance.

## Implemented changes

- Continue the repository as Pixora, Early Development, without resetting history or old release. Python namespace `pixora`, command `pixora-collect`, PWA wordmark and full bilingual docs. Retain APM env/CLI aliases and explain DB/volume changes before migration.
- EN/ZH Vue I18n key dictionaries, browser detection, explicit switch/persistence, English fallback, locale formatting and translated structured reason codes. Unknown legacy reason text is not shown verbatim.
- Fix old-request writeback on mode changes/disconnect, clock-based stale display, blocked/corrupt storage startup, and SQLite connection closure.
- Review actual implementation against README; mark public-screen ACL, full personal hub, controls, hardware and phone/PVE acceptance as incomplete.
- Keep original APM MIT notice; add Pixora contributor attribution, actual dependency license inventory and runtime license texts. Original pulse artwork only; no third-party logos/fonts copied.
- Audit npm and pinned Python advisories. Old pytest 8.4.2 had PYSEC-2026-1845; updated to 9.1.1 and reran tests/audit successfully. No application code was copied from a third-party project during migration.

## GitHub owner and naming

The public API returned 404 for `pixora-labs` and its candidate repo. 404 does not guarantee registration availability. Current GitHub app authorization and browser ownership are `kongjiestak`, no authorized organization. Do not create an organization with unconfirmed ownership/terms. Existing repository is renamed under the authorized user to `kongjiestak/pixora`; its repository identity/history/legacy release are preserved. No new tag or Pixora Release for this migration.

Pixora already has unrelated software uses; see BRAND.md. Working name only, no trademark clearance, exclusive brand rights, official domain, community or affiliation is claimed. This is a technical public repository, not a legal naming opinion.

## Security evidence and limits

`scripts/audit_release.py` scans the staged files and all reachable historical Git blobs for private paths, common access/private-key patterns, forbidden config/database names, and exact local token values. It reports locations only; no secrets are printed. `.env`, .codex/auth.json, logs/databases/credentials/caches are excluded. Real observations were only used in a private local verification DB; screenshots contain labeled demo values only.

This basic scan is not a professional security audit. Read/write tokens are separate but shared across one trust domain; local shared mode is not server ACL. No internet-scale rate limiter, per-device revocation, complete runtime isolation or guaranteed private vulnerability intake exists. PWA APIs are not cached. Files with third-party public license author notices are not private user contact data.

See VERIFICATION.md for executed tests, deployment limits and open acceptance gates. Future controls must use separate permissions and audit. The historical APM pre-release must not be represented as a new Pixora release.

## Metadata finding

The final review found non-noreply personal email metadata in existing public author/committer records. The earlier blob-only scan did not cover this. Keeping the historical commits without a force rewrite also keeps these metadata. The owner selected privacy-first cleanup and authorized execution. The remote main and legacy tag were atomically replaced with sanitized history using exact leases, preserving file trees, messages and timestamps. A fresh remote mirror scan found no original personal email in downloaded objects. The legacy Release and attachments were retained. Old objects may still be available by SHA through GitHub caches; this is not a guarantee of complete erasure. No email value or private original-history backup is published here. The scanner now blocks unreviewed non-noreply commit metadata.
