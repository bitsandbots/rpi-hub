# rpi-POD Content Guide

How to choose, fetch, verify, and refresh the offline content payload.
This file is the living spec for the library — refresh it whenever you
change the manifest.

## Mental model

rpi-POD ships with an **empty library** by default. That choice is
deliberate: bundled ZIMs balloon the distributable image to tens of GB,
and the right content depends on where the hub will live (urban resilience
vs. wilderness vs. coastal vs. mountain). `content/manifest.yaml` is the
contract between this repo and a workstation that downloads the payload.

## The manifest

`content/manifest.yaml` lists every ZIM the hub *might* serve, tagged
into three tiers:

| Tier | Approx. size | Target hardware |
|---|---|---|
| `minimal` | ~12 GB | Pi Zero 2 W with a 16 GB SD card |
| `core` | ~20 GB | Pi 4 with a 64 GB SD card |
| `full` | ~150 GB | Pi 5 with a 256 GB+ SSD (assistant-enabled) |

Each entry has:

- `name` — basename of the ZIM file on disk
- `url` — Kiwix download URL (dated filename, will drift)
- `size_mb` — approximate footprint, for "do I have room" checks
- `sha256` — pinned hash, optional
- `description` — surfaced here in the guide
- `tier` — `minimal | core | full`

### About the sha256 field

Kiwix rebuilds ZIMs on a rolling schedule. The dated filenames in the
manifest *will* go stale — sometimes within months. We can't pre-pin a
hash that hasn't been built yet, so the shipped manifest has empty
hashes. The workflow:

1. Run `fetch.sh` for the first time. It prints the actual sha256 of
   each download.
2. Paste those hashes back into your manifest.
3. Commit the populated manifest to your own fork. Now everyone building
   the same image gets reproducible content.

If a future fetch finds the URL has been rebuilt (new dated filename),
the old URL will 404. Update the manifest entry's `url`, clear the
`sha256`, and re-fetch.

## Workflows

### First-time build

On your workstation (not the Pi):

```bash
git clone https://github.com/coreconduit/signal.git
cd signal
./content/fetch.sh core             # or `minimal` for tiny builds
                                    # or `full` for assistant-enabled
```

This produces `./payload/var/lib/kiwix/` with the ZIMs. Then:

```bash
rsync -avh --progress payload/var/lib/kiwix/ pi@hub.local:/var/lib/kiwix/
ssh pi@hub.local sudo systemctl restart rpi-pod-kiwix
```

### Pre-imaging an SD card

After flashing Raspberry Pi OS Lite, mount the SD card's root partition
and copy:

```bash
sudo mkdir -p /mnt/sd/var/lib/kiwix
sudo cp -av payload/var/lib/kiwix/. /mnt/sd/var/lib/kiwix/
sudo umount /mnt/sd
```

`install.sh` (run after boot) will pick up the existing content.

### Refreshing content

Kiwix periodically issues fresh ZIM rebuilds. To refresh:

1. Visit <https://library.kiwix.org/>
2. For each entry in the manifest, find the current dated filename
3. Update the `url` (and clear the `sha256` so fetch re-pins)
4. Re-run `fetch.sh`
5. Re-run `verify.sh` on the destination to confirm integrity
6. rsync over to the Pi as above

### Verifying a deployed Pi

```bash
ssh pi@hub.local
cd /opt/rpi-pod     # or wherever the repo is checked out
./content/verify.sh /var/lib/kiwix
```

Exit codes:
- `0` — everything matches the manifest
- `1` — at least one file is corrupt (hash mismatch)
- `2` — at least one manifest entry has no sha256 (incomplete pinning)

## Curation principles

When deciding what to include:

1. **Bias toward how-to over reference.** Practical guides (iFixit,
   the zimgit-post-disaster / water / food-preparation / knots bundle)
   are more useful in an emergency than encyclopedic prose. Pick the
   survival-oriented content first.
2. **English-only by default.** Multilingual ZIMs roughly double the
   payload. Make language an explicit regional-pack decision (Phase 9B)
   rather than a default.
3. **No-images first.** `_nopic` variants of Wikipedia and Wiktionary
   are 5-10x smaller and lose nothing on text content. Add image-heavy
   ZIMs only for `full` tier on SSD builds.
4. **Maps last.** OSM ZIMs are huge and overlap with what most users
   already have on their phones. Include only for regional packs that
   explicitly call for offline mapping.
5. **Verify licensing.** Kiwix's content is mostly CC-BY-SA or
   public domain. If you add a non-Kiwix ZIM, check its license and
   record it in this file.

## Licensing notes

The default manifest pulls only from <https://download.kiwix.org/>, whose
content is curated and license-checked by the Kiwix project. Each ZIM
contains its own license metadata that Kiwix-serve displays in the
library index.

If you build custom ZIMs (with `zimwriterfs` or similar), record their
source and license in your manifest's `description` field. rpi-POD is MIT
licensed, but each ZIM carries its own license — assume nothing redistributable
by default.

## Sizing reference

| Content | Tier | On-disk | Notes |
|---|---|---|---|
| Simple Wikipedia (no images) | minimal | ~940 MB | Surprisingly complete |
| zimgit-post-disaster | minimal | ~615 MB | Shelter, sanitation, recovery |
| zimgit-water | minimal | ~20 MB | Sourcing, purification, storage |
| zimgit-food-preparation | minimal | ~93 MB | Cook without modern utilities |
| zimgit-knots | minimal | ~27 MB | Illustrated knot reference |
| iFixit (all) | minimal | ~3.4 GB | Repair guides — electronics, appliances |
| Wiktionary (no images) | core | ~8.7 GB | Dictionary + thesaurus + etymology |
| WikEM | core | ~46 MB | Wiki of Emergency Medicine — physician-curated |
| zimgit-medicine | core | ~67 MB | Consumer-level medical reference |
| Wikipedia full (no images) | full | ~50 GB | English, every article |
| Project Gutenberg English | full | ~65 GB | Every public-domain book |
| OSM world basic | full | ~40 GB | Replace with regional pack if possible |

Add ~1 GB headroom for filesystem overhead and future regional packs.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `rpi-pod-kiwix` is inactive after install | `/var/lib/kiwix/` is empty | Fetch ZIMs and rsync them in |
| `502 Bad Gateway` at `/library/` | `rpi-pod-kiwix` is down | `systemctl status rpi-pod-kiwix`, look at journal |
| `verify.sh` reports MISMATCH | Corrupted transfer | Re-rsync the affected file; rsync's `--checksum` catches this |
| `fetch.sh` says yq is missing | yq not installed | `brew install yq` (macOS) / `apt-get install yq` (Debian/Ubuntu) |
| Kiwix-serve takes 30s+ to start | ZIMs being indexed | Normal on first start with a large library; cached afterward |
| Article opens but images don't load | ZIM is `_nopic` or `_mini` variant | Expected — pick the maxi variant if you want images |
