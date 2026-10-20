# Pixora UI direction — V0.2

Taste-Skill: [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), MIT, reviewed at `63aba5f43b5056758b15bbe7d683da8c86a7a7ad`. Applied its `skills/taste-skill/SKILL.md` and complete `references/app-screens.md` app workflow; not the landing-page rules. No upstream install script or remote code loader was added to Pixora.

Draw: **True-black flat**, seed **1899116366**, no redraws. Existing Pixora mint is retained as the data accent and system fonts as the typeface, passed via `--keep palette,type`. This avoids remote font requests and preserves offline/Chinese/old-phone fallbacks. The brand mark is an original screen-aperture SVG, not a vendor asset.

## Data and intent

- Objects: quota windows with percentages and reset timestamps; Linux host CPU/memory/root-disk values with units; observations with source, collection and expiry; authorized history rows.
- Magnitudes come exclusively from connectors; source snapshots remain snapshots, not invented continuous telemetry.
- Used by one owner glancing at an iPhone/old screen, or configuring it in a desktop browser.
- Primary question: **How much AI capacity remains, and is the monitored host healthy?**
- Primary jobs: read current values, refresh server data, enter display mode, inspect history, manage the current device.
- Distinct Pixora element: the paired allowance windows and their next-reset times, with the collection freshness beside them.
- Keep: English/Chinese, real/demo separation, auth, logout/shared privacy, history scopes, wake lock and settled rotation.
- Remove: settings wall on the first screen, oversized empty clock tile, navy-tinted surfaces, large green buttons, heavy rounded borders.
- Ground/surface/raised: neutral `#0b0b0b` / `#171717` / `#242424`; pale mint on progress marks, neutral figures and controls. Light theme uses the same roles.
- Desktop canvas: `1120 = 2 × 552 + 16`; time and sync span both columns. At tablet width, full-width stacked panels preserve legibility. Phone uses 16px gutters and ≥44px controls.
- Display mode deliberately exceeds the app guideline's 40px figure ceiling for distance viewing. The normal dashboard uses ≤36px figures. This is a functional exception, not a marketing hero.
- No fake charts, data, deltas or activity. Refresh reads server data; it does not claim to trigger an upstream collector.

## Verification method

Run the upstream static `lint.mjs --app` and normal project tests/build. Browser interaction in this environment must use the supported CUA browser tools, so do not run the upstream inspector's separate Chrome automation. Instead capture before/after at 1440, 768 and 390; measure document overflow, heading, body font floor, native settings, history, theme/language, shared privacy and display/rotation layouts through CUA. Report this substitution explicitly; do not claim the upstream browser inspector passed.

Use the actual screenshots for a critique: first-screen data placement, equal edges, colour limited to data, consistent numbers, honest missing states, no label collisions, phone usability. Physical iPhone V0.2 confirmation remains distinct from desktop viewport tests.

## Final critique and checks (2026-10-20)

1. **Question and reading order:** quota/host metrics precede configuration; the time is a compact shared strip, not an oversized card. Display mode keeps larger figures for distance reading.
2. **Grid:** paired desktop cards share edges and bottoms; tablet panels stack. Source and reset labels wrap naturally, without clipping figures.
3. **Colour and identity:** neutral opaque surfaces, one mint data hue, original screen-aperture mark. No new image/font/icon dependencies or gradients.
4. **Data agreement:** existing connector values remain unchanged. New bars use those exact metric values; reset durations derive from the same timestamp as the reset label. Refresh explicitly reads server state.
5. **States:** before connection the screen keeps its real empty state; expired and unknown remain explicit. No fabricated demo metrics, activity or trends were added. Missing values use translated “Unknown” rather than a silent zero.
6. **History and controls:** actual history rows loaded. Numeric table columns are right-aligned; the table scrolls inside its frame on narrow screens. Shared mode removed quota cards, system cards and history rows (all measured 0).
7. **Phone:** at 390px quota begins around y=352, where the previous screen still showed configuration; 768px and 1440px also passed overflow checks. Measured visible text floor 12px. English/light theme and exit/display interactions checked. At 956×440 the clock fits its column and ends before the system card starts.

Upstream static lint: **0 FAIL, 0 WARN**. Frontend: **15 tests passed**, production build passed. Screenshots at all three widths were opened for visual review. The upstream Chrome inspector was not run; supported CUA screenshots and DOM measurements were used instead, as required by this environment. These are browser checks, not a physical iPhone/old Android approval.

Three problems corrected after the first look: unequal peer-card bottoms, verbose reset timestamps that wrapped excessively, and English phone controls needing a narrower layout. Remaining limits: no new trend chart without sufficient real history; dense history can require internal horizontal scrolling; actual iPhone V0.2 validation is still pending. Before/after captures have different actual observation times because live data continued changing; this is a layout comparison, not a performance benchmark.

Local development against an existing API may set `PIXORA_DEV_API=http://127.0.0.1:<private-forward-port>` when starting Vite. It is a development-only proxy target; no upstream credentials are bundled in the browser build.
