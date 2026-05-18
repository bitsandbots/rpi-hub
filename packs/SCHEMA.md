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
