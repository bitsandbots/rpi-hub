# rpi-hub Portal v2 Incorporation Plan

## Goal
Replace the current captive-portal landing page (`www/portal/index.html`) with the redesigned `portal-v2.html` UI while preserving offline-first invariants, install/uninstall paths, and the existing nginx-backed asset pipeline.

## Status
**Completed.** The new landing page is live in `www/portal/index.html`. The out-of-tree `portal-v2.html` and the temporary `index-original.html` backup have been removed.

## Current state (post-incorporation)

| Item | Location | Notes |
|------|----------|-------|
| New landing page | `rpi-hub/www/portal/index.html` | Self-contained v2 design: grouped tiles, live status strip, SVG icons, offline-state probing. |
| Shared contrast script | `rpi-hub/www/portal/assets/js/contrast.js` | Loaded from `<head>` so fixes apply globally. |
| Shared assets | `rpi-hub/www/portal/assets/` | Other portal pages remain on existing `rpi-hub.css` for now. |
| Nginx config | `rpi-hub/config/nginx/rpi-hub-portal.conf` | No changes required; all v2 endpoints already proxied. |
| Install path | `rpi-hub/install.sh` phases 2/4 | `install_tree` already deploys the whole `www/portal/` tree. |

## Decisions taken

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Replace or coexist? | **Replaced** `index.html`. | Direct redesign of the same landing surface. |
| Inline or extract CSS/JS? | **Kept inline** for now. | Avoids a portal-wide CSS/JS refactor; can be extracted once the design stabilizes. |
| Contrast toggle | **External `/assets/js/contrast.js`**. | Removes duplication and keeps behavior consistent with other pages. |
| Version display | **Dynamic from `/api/status` `build_version`** in the status strip only. | Footer no longer hardcodes a version; avoids a stale or missing string when the API is down. |

## Implementation checklist

### 1. Pre-flight verification
- [x] All v2 `data-probe` URLs are served by existing nginx routes.
- [x] Font files fall back to system fonts when `scripts/fetch_fonts.sh` has not run.
- [x] No external requests in the page (only self-hosted fonts/assets and internal endpoints).

### 2. File placement
- [x] Moved `portal-v2.html` → `rpi-hub/www/portal/index.html`.
- [x] Removed temporary `index-original.html` backup.
- [x] Removed out-of-tree `portal-v2.html`.

### 3. Hardcoded values
- [x] Status-strip version now populated from `/api/status` `build_version`.
- [x] Footer no longer contains a hardcoded version string.
- [x] `/app/` tile points to the React SPA build output.
- [x] Core-resource tiles route to `/library/` (library home) as in the original design.

### 4. Contrast toggle
- [x] Inline contrast script removed; page loads `/assets/js/contrast.js`.

### 5. Asset pipeline
- [x] No new shared assets introduced.
- [x] Future extraction to `rpi-hub-v2.css` / `portal-v2.js` left as a follow-up polish item.

### 6. Install / uninstall
- [x] No changes required; `install_tree` handles deployment.

### 7. Nginx config
- [x] No new routes required.

### 8. Testing
- [x] HTML parses cleanly with `python -m html.parser`.
- [x] Local `http.server` sanity check returned 200 with expected markers.
- [x] pytest could not be run in this Windows environment (module not installed); must be validated on a Pi/dev container.
- [ ] Service probes on live device.
- [ ] No-JS fallback on live device.
- [ ] `make smoke` on a configured device.
- [ ] Keyboard/accessibility pass on a real browser.

### 9. Documentation
- [x] `docs/OVERVIEW.md` updated to describe the grouped layout and status strip.
- [x] `CHANGELOG.md` updated under `[Unreleased]`.

### 10. Release
- [ ] Run `scripts/release.sh` to stamp `VERSION` and `CHANGELOG`.
- [ ] Tag release.

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| v2 inline styles diverge from existing portal pages, creating a two-tone UI. | Accepted for this iteration; document as a polish item in `docs/GAP_ANALYSIS.md` if desired. |
| Hardcoded version string becomes stale. | Resolved by fetching `build_version` from `/api/status`. |
| Self-hosted font files missing on fresh install. | v2 falls back to system fonts; no broken functionality. |
| `data-probe` fetches log errors on missing hardware. | Expected; probes silently fail and mark tiles offline. |

## Acceptance criteria

- [x] `www/portal/index.html` is the v2 landing page.
- [x] All live-service `data-probe` URLs map to existing nginx routes.
- [x] Status strip and footer populate from `/api/status`.
- [x] Contrast toggle is served from shared asset.
- [x] No external network requests are made by the page.
- [ ] `http://hub.local/` serves the v2 landing page after `sudo ./install.sh` (verify on device).
- [ ] With all services running, every live-service tile resolves to `ready` and is clickable (verify on device).
- [ ] With services stopped or hardware absent, affected tiles fade to `offline` and are non-interactive (verify on device).
- [ ] `make smoke` passes on a configured device.
