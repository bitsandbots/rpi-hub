# gps-sdr

GPS L1 C/A satellite acquisition via RTL-SDR.

Detects which GPS satellites are visible by searching all 32 PRN codes across
code phase (0–1022 chips) and Doppler frequency (±10 kHz) simultaneously using
the Parallel Code Phase Search (PCPS) algorithm.  For each detected satellite
it reports the Doppler offset, code phase alignment, and a signal strength
metric.

> **What this does and does not do**
>
> - ✅ Detects visible GPS satellites and measures their Doppler offset
> - ✅ Reports code-phase alignment (first step toward tracking)
> - ❌ Does **not** decode the navigation message or compute a position fix
>
> Computing a position fix requires full tracking loops (DLL/PLL) and
> navigation message decoding, which is a significantly larger system.
> For a complete solution see [GNSS-SDR](https://gnss-sdr.org/).

---

## Hardware requirements

| Item | Notes |
|------|-------|
| RTL-SDR dongle | RTL-SDR Blog v3/v4 strongly recommended (hardware bias tee) |
| Active GPS patch antenna | Must have built-in LNA (powered via bias tee) |
| SMA or MCX adapter | Match your antenna connector to the dongle |

### Why the bias tee matters

GPS signals arrive at roughly −130 dBm after antenna gain, far below an
unassisted RTL-SDR's noise floor.  The active patch antenna's LNA (≈27 dB gain,
≈1 dB NF) is what makes reception possible, but it needs ~4.5 V supplied on
the coax centre conductor — that is what the bias tee does.

Without a powered LNA acquisition will almost certainly fail.

### Supported dongles

| Dongle | Bias tee | Notes |
|--------|----------|-------|
| RTL-SDR Blog v3/v4 | ✅ hardware GPIO | controlled automatically |
| Generic R820T/R820T2 | ❌ none | use external LNA with separate power |
| Nooelec NESDR | varies | check model specs |

---

## System dependencies

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install librtlsdr-dev rtl-sdr python3-pip
# Block kernel DVB-T driver so librtlsdr can open the device:
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtlsdr.conf
sudo modprobe -r dvb_usb_rtl28xxu   # or reboot
```

### macOS

```bash
brew install librtlsdr
```

### Windows

Download the RTL-SDR Blog driver package from <https://www.rtl-sdr.com/rtl-sdr-quick-start-guide/>
and follow the Zadig WinUSB installation steps.

---

## Python setup

```bash
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Usage

### Simulation mode (no hardware needed)

```bash
python -m gps_sdr --simulate
```

Generates a synthetic signal with PRNs 1, 5, 14, 22 at known Dopplers and
verifies the acquisition engine finds them.

> **Simulator threshold note:** The simulator uses a *single* detection
> threshold — the real `DEFAULT_ACQ_THRESHOLD` (20.0), not a lowered demo
> bar. Its signal amplitudes are tuned so the four synthetic satellites
> (PRNs 1, 5, 14, 22) clear that real threshold with ~2× margin while
> cross-correlations and noise-floor maxima on the other 28 PRNs stay below
> it, so the sim reports exactly the injected constellation at the same bar
> hardware uses. See `tests/gps_sdr/test_sim_e2e.py`.
>
> ```bash
> python -m gps_sdr --simulate
> ```
>
> In hardware mode the same threshold applies. The threshold is a
> peak-to-noise-floor ratio over the 41 Doppler × 2048 code-phase search
> space; the default of 20 is derived from a false-alarm budget (P_FA ≈
> 84k·e⁻²⁰ ≈ 2e-4 per PRN per sweep). **Do not lower it to ~2–3** — at that
> level the noise-floor maximum (ln(84k) ≈ 11) is exceeded on nearly every
> PRN every sweep, producing constant false acquisitions. See
> `gps_sdr/constants.py` and `tests/gps_sdr/test_false_alarm.py`.

### Hardware mode

```bash
python -m gps_sdr
```

Place your active GPS antenna outdoors (or near a window with sky view).
The bias tee will be enabled automatically.

### Common options

```text
--simulate              Use synthetic signal instead of hardware
--no-bias-tee           Disable bias tee (external LNA or passive antenna)
--ppm N                 Frequency correction in ppm (check with kalibrate-rtl)
--gain DB               RF gain in dB (default: 49.6 = max)
--sample-rate MSPS      Sample rate in Msps (default: 2.048)
--prns N [N ...]        Restrict search to specific PRN numbers
--threshold RATIO       Detection threshold (default: 20.0; see constants.py — do not lower without re-deriving the false-alarm budget)
--integration-ms MS     Non-coherent integration length in ms (default: 1)
--doppler-range HZ      Doppler search ±range in Hz (default: 10000)
--doppler-step HZ       Doppler bin step in Hz (default: 500)
--interval SEC          Seconds between sweeps (default: 5)
--once                  Run one sweep and exit
-v, --verbose           Enable debug logging
```

### Examples

Single sweep, save time:

```bash
python -m gps_sdr --once
```

Outdoor session with a slightly drifty dongle:

```bash
python -m gps_sdr --ppm 15 --interval 10
```

Longer integration for marginal signals (2 ms non-coherent):

```bash
python -m gps_sdr --integration-ms 2
```

Integration raises the peak/noise-floor ratio without lowering the
detection bar, so it is the preferred lever for weak signals. Lower
`--threshold` only with care (see the false-alarm note above).

---

## Troubleshooting

### No satellites acquired

- Ensure antenna has clear sky view (GPS cannot penetrate buildings)
- Check bias tee is on — look for "Bias tee ENABLED ✓" in output
- Try `--ppm` calibration (use `kalibrate-rtl` with a known FM station)
- Increase integration: `--integration-ms 2` (raises the metric without
  lowering the detection bar)
- As a last resort, lower `--threshold` slightly (e.g. 18) — but re-check
  the false-alarm budget, since each unit dropped roughly multiplies the
  per-PRN false-acquisition probability by e ≈ 2.7

### `set_bias_tee` not available

- Your pyrtlsdr or librtlsdr is too old.  Enable manually before running:

  ```bash
  rtl_biast -b 1
  python -m gps_sdr --no-bias-tee
  ```

### `usb_claim_interface` / permission errors

- On Linux: `sudo usermod -aG plugdev $USER` and re-login, or run with `sudo`
- Ensure the `dvb_usb_rtl28xxu` kernel module is blacklisted (see above)

### Only noise, metric never exceeds 1.5

- Noise floor may be elevated by interference near 1575 MHz (Wi-Fi, LTE)
- Move antenna away from electronics; try a USB extension cable

---

## Architecture

```text
gps_sdr/
├── constants.py      GPS L1 constants and PRN G2 tap table (IS-GPS-200)
├── prn.py            C/A Gold code generator + FFT pre-computation
├── hardware.py       RTL-SDR wrapper with dual-path bias tee control
├── acquisition.py    Vectorised PCPS engine (numpy batch FFT)
├── simulate.py       Synthetic GPS signal generator
└── __main__.py       CLI entry point + Rich terminal dashboard
```

### Signal processing notes

- The C/A code is a 1023-chip Gold code at 1.023 Mchip/s (1 ms period).
- At 2.048 Msps the code is oversampled by ~2×, giving 2048 samples/ms.
- The PCPS algorithm FFT-correlates each millisecond block against all 32
  pre-computed PRN code replicas for every Doppler bin simultaneously.
- Non-coherent integration sums `|correlation|²` over multiple milliseconds
  without needing to track the navigation data bit phase.
- Peak-to-noise-floor metric > 2.5 (default) → satellite detected.

### Next steps toward a position fix

1. **Tracking loops** — DLL (code) + Costas PLL (carrier) maintain lock
2. **Navigation message decoding** — 50 bps BPSK data: ephemeris, clock, almanac
3. **Pseudorange measurement** — time-of-arrival from code phase + subframe sync
4. **Least-squares position solution** — 4+ satellites required

These are implemented in full by [GNSS-SDR](https://gnss-sdr.org/) (C++ with
Python/GNURadio integration), which can consume samples captured with this tool.

---

## Reference

Borre, K. et al., *A Software-Defined GPS and Galileo Receiver: A
Single-Frequency Approach*, Birkhäuser, 2007.  ISBN 978-0-8176-4540-3.
