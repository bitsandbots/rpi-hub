# rpi-hub portal fonts

This directory is **empty by default**. The portal CSS expects four files
plus an OFL license:

| File | Family | Weight |
|---|---|---|
| `exo2-700.woff2` | Exo 2 | 700 |
| `jakarta-400.woff2` | Plus Jakarta Sans | 400 |
| `jakarta-700.woff2` | Plus Jakarta Sans | 700 |
| `plexmono-400.woff2` | IBM Plex Mono | 400 |
| `OFL.txt` | (shared license) | — |

## How to populate

On a workstation with internet:

```bash
./scripts/fetch_fonts.sh
```

That script downloads the woff2 files from
[`@fontsource`](https://fontsource.org/) (jsDelivr-hosted, OFL-compliant) and
prints a sha256 for each. After a known-good run you can pin those hashes
into `scripts/fetch_fonts.sh` for reproducible bakes.

## Why these are not committed

Binary assets in git churn diffs and bloat clones. They're also
licensing-sensitive — the OFL is permissive but requires the license to
travel with the files. Keeping the fetch step explicit makes both
intentional.

## Runtime behavior with no fonts present

The CSS uses `font-display: swap` and a system font fallback chain. With
this directory empty the portal still renders correctly in system fonts;
each missing `.woff2` produces one 404 in browser devtools, which is
harmless. For a clean bake — and a clean Lighthouse score — run
`fetch_fonts.sh` before `scripts/bake_image.sh` (Phase 5).

## Licensing

All three families ship under the
[SIL Open Font License v1.1](https://openfontlicense.org/), compatible
with the project's MIT license. `OFL.txt` is fetched alongside the
woff2 files and must travel with them in any redistribution.
