# Phase 3 — Content Layer (Kiwix)

## Goal

The hub serves real offline content. A client opens the captive portal,
taps a link, and reads a Wikipedia article without any internet — pulled
straight off the Pi's SD card.

## What was built

| Artifact | Path |
|---|---|
| ZIM manifest | `content/manifest.yaml` (tiered minimal / core / full) |
| Workstation fetch | `content/fetch.sh` (downloads ZIMs into `./payload/var/lib/kiwix/`) |
| Disk verifier | `content/verify.sh` (re-hashes against manifest) |
| Kiwix service | `systemd/signal-kiwix.service` (`127.0.0.1:8080`, `DynamicUser`) |
| Nginx route | `config/nginx/signal-portal.conf` adds `location /library/` |
| Installer step | `phase3()` in `install.sh` (default `PHASE=3`) |
| Content guide | `docs/CONTENT_GUIDE.md` |

## How it works

1. **Fetch (off the Pi).** On a workstation:
   `./content/fetch.sh core` downloads the core tier into
   `./payload/var/lib/kiwix/`. Big files (~5 GB to ~50 GB each); plan the
   tier and the disk accordingly.
2. **Transfer.** `rsync -avh --progress payload/var/lib/kiwix/
   pi@hub.local:/var/lib/kiwix/` — or copy onto the SD card pre-flash.
3. **Verify.** On the Pi (or workstation):
   `./content/verify.sh /var/lib/kiwix` confirms hashes match.
4. **Serve.** `signal-kiwix.service` starts as soon as any `.zim` appears
   in `/var/lib/kiwix/`. nginx's `/library/` block proxies to it.

## How to verify on a Pi

From a Phase 1+2 install, after fetching a small ZIM and copying it over:

```bash
sudo ./install.sh                    # PHASE=3 by default
sudo systemctl status signal-kiwix   # should be "active (running)"
```

Then:

1. **Direct probe (on the Pi):**
   ```bash
   curl -fsSI http://127.0.0.1:8080/library/
   ```
   should return `200 OK`.
2. **Proxied probe (from a client on `SIGNAL_INFOHUB`):**
   ```bash
   curl -fsSI http://hub.local/library/
   ```
   also `200 OK`.
3. **Browse on a phone.** Open `http://hub.local/library/`, pick a ZIM,
   navigate to an article. Should render with no spinner / no external
   asset failures (verify in dev tools — every URL should be on hub.local).
4. **Empty-library state.** If `/var/lib/kiwix` is empty:
   `systemctl status signal-kiwix` shows `inactive (condition failed)`
   (because of `ConditionPathExistsGlob`). `curl http://hub.local/library/`
   returns `502 Bad Gateway` from nginx. That's the intended UX cue.

## Acceptance criteria (from build plan)

- ✅ `curl http://hub.local/library/` returns the Kiwix index
- ✅ Browsing a Wikipedia article on a phone works without internet

## Known limitations going into Phase 4

- **No landing-page integration.** The captive portal page doesn't link to
  the library yet — Phase 4 adds the category tiles.
- **Empty-library UX is a 502.** That's accurate but unfriendly. Phase 4's
  frontend will detect missing services and render a "library not yet
  installed" panel instead of a raw proxy error.
- **No regional packs.** Phase 9B adds `install.sh --pack=<name>` which
  swaps the manifest for one of the curated regional bundles.
- **Manifest sha256 fields are blank by default.** Kiwix rebuilds ZIMs
  on a rolling schedule, so we can't pin hashes from this side. Run
  `fetch.sh` once to capture them, then commit the populated manifest
  to your own fork for reproducibility. See `CONTENT_GUIDE.md`.

## Rollback

`sudo ./uninstall.sh` stops and removes the Kiwix unit but **leaves**
`/var/lib/kiwix/` and its ZIMs in place. Rationale: re-downloading tens
of GB on a workstation is the kind of pain we shouldn't impose by
accident. Delete the directory manually if you really mean it.

## Tag

`v0.3.0-phase3`
