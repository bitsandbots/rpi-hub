# rpi-POD — Regional Content Packs

A pack is a manifest + a set of pre-curated artefacts (ZIM list, printable
PDFs, optional NOAA station presets) that turns a generic rpi-POD image
into one tuned for a specific region's failure modes.

`install.sh --pack=<name>` reads `packs/<name>/pack.yaml` and:

1. Fetches the named ZIMs into `/var/lib/kiwix` (via `content/fetch.sh`)
2. Stages printable PDFs under `/var/www/rpi-pod-portal/print/`
3. Optionally sets NOAA preset frequencies (Phase 8 dependency)

| Pack | Use case |
|------|----------|
| `general-purpose` | Default; Wikipedia/iFixit/WikEM/survival/Gutenberg + global OSM |
| `pacific-northwest` | Cascadia earthquake, tsunami, Pacific flora/fauna |
| `gulf-coast` | Hurricane prep, flood maps, mosquito-borne disease |
| `mountain-west` | Wildfire, altitude medicine, winter survival |
| `urban-resilience` | Power outage, water disruption, civil-unrest first aid |

Adding a pack: copy `packs/general-purpose/` as a starting point, edit
`pack.yaml`, drop your PDFs into `print/`. The schema lives in
`packs/SCHEMA.md`.
