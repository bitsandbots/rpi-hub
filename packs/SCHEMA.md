# Pack manifest schema (`pack.yaml`)

```yaml
name: pacific-northwest          # used by install.sh --pack=…; ASCII slug
display_name: Pacific Northwest  # shown on /print and the bake header
description: Cascadia earthquake, tsunami, regional flora/fauna.
version: 1
tier: core                       # minimal | core | full — drives storage budget
zims:                            # subset of content/manifest.yaml names
  - wikipedia_en_simple_all_nopic.zim
  - wikihow_en_maxi.zim
print:                           # printable PDFs served under /print/
  - file: water-purification.pdf
    title: Water purification — field methods
  - file: cascadia-shake.pdf
    title: Cascadia shake — first 30 minutes
noaa:                            # optional; consumed by signal-listen (Phase 8)
  preset_frequencies_mhz:
    - 162.400
    - 162.475
```

Validation:

* `name` must match the parent directory name.
* Each entry in `zims:` must exist in `content/manifest.yaml`.
* Each `print[].file` must exist in `packs/<name>/print/`.
* `noaa.preset_frequencies_mhz` is read by signal-listen at install time
  if Phase 8 is enabled; otherwise ignored cleanly.

## Field-card sources

The `.pdf` files referenced in `print:` are **generated artifacts**, not
checked into git. Each PDF has a same-name `.html` source in
`packs/<name>/print/<slug>.html`. The HTML uses the shared stylesheet at
`packs/_template/card.css` and the canonical structure from
`packs/_template/card-template.html`.

Workflow:

1. Author or edit `packs/<name>/print/<slug>.html`.
2. Run `./scripts/build_pack_pdfs.sh` once on the workstation — it walks
   every `packs/*/print/*.html` and emits a sibling `.pdf` (idempotent;
   skips PDFs newer than their source).
3. Then `./scripts/apply_pack.sh <name>` stages the resulting PDFs into
   `./payload/var/www/signal-portal/print/`.

PDFs are gitignored (`packs/*/print/*.pdf`). Re-running the build is the
only way to refresh them, and that is also the contract: source-of-truth
is the HTML, never the binary.

`apply_pack.sh` will error out with a pointer to `build_pack_pdfs.sh` if
a referenced `.pdf` is missing from `packs/<name>/print/`.
