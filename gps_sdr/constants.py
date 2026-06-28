"""GPS L1 C/A signal constants and PRN code phase assignments.

Reference: IS-GPS-200 Revision M (Interface Specification, 2021)
"""

# ── Frequencies ──────────────────────────────────────────────────────────────
GPS_L1_FREQ: float = 1_575.42e6   # Hz  (L1 carrier)
CA_CHIP_RATE: float = 1.023e6     # chips/s
CA_CODE_LENGTH: int = 1_023        # chips per period (1 ms)

# ── RTL-SDR defaults ─────────────────────────────────────────────────────────
# 2.048 Msps ≈ 2× the C/A chip rate; covers the main lobe bandwidth.
# The R820T/R820T2 tuner can reach 1575 MHz; the RTL-SDR Blog v3/v4 adds a
# hardware bias tee to supply ~4.5 V to the active antenna LNA.
DEFAULT_SAMPLE_RATE: float = 2.048e6  # Hz
DEFAULT_GAIN_DB: float = 49.6          # dB  (maximum; GPS is very weak)

# ── Acquisition defaults ──────────────────────────────────────────────────────
DEFAULT_DOPPLER_RANGE_HZ: float = 10_000.0   # typical satellite Doppler ≤ ±5 kHz
DEFAULT_DOPPLER_STEP_HZ: float = 500.0        # frequency resolution
DEFAULT_ACQ_THRESHOLD: float = 2.5            # peak-to-noise-floor ratio
DEFAULT_INTEGRATION_MS: int = 1               # non-coherent integration periods

# ── G2 code-phase tap assignments ────────────────────────────────────────────
# IS-GPS-200, Table 3-Ia.  For PRN n the C/A chip output is:
#   G1[0]  XOR  G2[tap_a − 1]  XOR  G2[tap_b − 1]
#
# NOTE: These assignments are believed correct per IS-GPS-200 but have not
# been independently verified here.  Cross-check against the spec before
# use in any safety-critical application.
PRN_G2_TAPS: dict[int, tuple[int, int]] = {
     1: ( 2,  6),   2: ( 3,  7),   3: ( 4,  8),   4: ( 5,  9),
     5: ( 1,  9),   6: ( 2, 10),   7: ( 1,  8),   8: ( 2,  9),
     9: ( 3, 10),  10: ( 2,  3),  11: ( 3,  4),  12: ( 5,  6),
    13: ( 6,  7),  14: ( 7,  8),  15: ( 8,  9),  16: ( 9, 10),
    17: ( 1,  4),  18: ( 2,  5),  19: ( 3,  6),  20: ( 4,  7),
    21: ( 5,  8),  22: ( 6,  9),  23: ( 1,  3),  24: ( 4,  6),
    25: ( 5,  7),  26: ( 6,  8),  27: ( 7,  9),  28: ( 8, 10),
    29: ( 1,  6),  30: ( 2,  7),  31: ( 3,  8),  32: ( 4,  9),
}
