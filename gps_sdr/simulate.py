"""Synthetic GPS L1 C/A signal generator for acquisition testing.

Generates a realistic-looking baseband GPS signal without hardware:

  1. Resample each PRN code to the output sample rate.
  2. Apply a code-phase offset (circular shift).
  3. Apply Doppler by multiplying with the appropriate complex exponential.
  4. Sum all satellite signals and add complex AWGN.

The signal amplitude is chosen so that the peak-to-noise metric after
1 ms of correlation is roughly *snr_db* dB above the threshold.  These
are artificial levels that do not represent real link-budget figures.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Sequence

import numpy as np

from .constants import DEFAULT_SAMPLE_RATE
from .prn import resample_code

log = logging.getLogger(__name__)


@dataclasses.dataclass
class SimSatellite:
    """Parameters for one simulated GPS satellite."""

    prn: int
    doppler_hz: float = 0.0  # Doppler offset (Hz)
    code_phase: int = 0  # Code-phase offset (samples from start)
    amplitude: float = 0.20  # Signal amplitude relative to noise std=1
    # Rough metric guide at 2.048 Msps (spc=2048): the peak/noise-floor ratio
    # after 1 ms correlation is ≈ spc × amp² × scallop, where the scallop
    # factor (~0.4–0.5) accounts for Doppler-bin quantisation and the
    # ±1-chip noise-floor exclusion. amp=0.20 → metric ≈ 35–45. The
    # DEFAULT_SCENARIO amplitudes below are tuned to clear the real hardware
    # threshold (DEFAULT_ACQ_THRESHOLD=20) with ~2× margin; see
    # tests/gps_sdr/test_sim_e2e.py for the pinned values.


# Default scenario: four satellites in different parts of the sky.
#
# The simulator uses a SINGLE threshold — the real DEFAULT_ACQ_THRESHOLD
# (20), not a lowered demo threshold. The amplitudes below are chosen so all
# four synthetic satellites clear that real threshold with ~2× margin even
# under worst-case Doppler-bin scalloping, which keeps the demo honest: a
# satellite the sim marks ACQUIRED is one that would also be detected at the
# hardware detection bar. Verified across 20 noise seeds
# (worst scenario metric ≈ 41, worst non-scenario ≈ 17 — threshold 20 sits
# in the gap) by tests/gps_sdr/test_sim_e2e.py.
#
# Cross-correlations with non-scenario PRNs stay ≤ (65/1023)² of a source
# metric (~0.004× ≈ 0.2), far below 20; the non-scenario metrics (~9–17)
# are noise-floor maxima (ln(84k bins) ≈ 11), not cross-correlation leaks.
DEFAULT_SCENARIO: list[SimSatellite] = [
    SimSatellite(prn=1, doppler_hz=+1_200.0, code_phase=512, amplitude=0.22),
    SimSatellite(prn=5, doppler_hz=-2_500.0, code_phase=200, amplitude=0.20),
    SimSatellite(prn=14, doppler_hz=+4_000.0, code_phase=987, amplitude=0.18),
    SimSatellite(prn=22, doppler_hz=-750.0, code_phase=1500, amplitude=0.20),
]


class GPSSimulator:
    """Generate complex baseband GPS L1 signal blocks for testing."""

    def __init__(
        self,
        sample_rate: float = DEFAULT_SAMPLE_RATE,
        noise_std: float = 1.0,
        seed: int | None = 42,
    ) -> None:
        self.sample_rate = sample_rate
        self.noise_std = noise_std
        self.spc = int(round(sample_rate * 1e-3))  # samples per code period

        self._rng = np.random.default_rng(seed)

        # Pre-cache resampled codes (float32 ±1)
        self._codes: dict[int, np.ndarray] = {}

    def generate(
        self,
        satellites: Sequence[SimSatellite] | None = None,
        duration_ms: int = 1,
    ) -> np.ndarray:
        """Return *duration_ms* ms of complex64 IQ samples.

        Args:
            satellites:   List of :class:`SimSatellite`.  Defaults to
                          :data:`DEFAULT_SCENARIO`.
            duration_ms:  Number of 1 ms code periods to generate.

        Returns:
            Complex64 array of shape (duration_ms × spc,).
        """
        if satellites is None:
            satellites = DEFAULT_SCENARIO

        total = duration_ms * self.spc
        t = np.arange(total, dtype=np.float64) / self.sample_rate

        # Complex AWGN: each component ~ N(0, noise_std²/2)
        component_std = self.noise_std / np.sqrt(2.0)
        signal = (
            self._rng.standard_normal(total).astype(np.float32) * component_std
            + 1j * self._rng.standard_normal(total).astype(np.float32) * component_std
        ).astype(np.complex64)

        for sat in satellites:
            code = self._get_code(sat.prn, total, sat.code_phase)
            # Apply Doppler shift
            carrier = np.exp(1j * 2.0 * np.pi * sat.doppler_hz * t).astype(np.complex64)
            signal = signal + (sat.amplitude * code * carrier).astype(np.complex64)

        log.info(
            "Simulated %d satellite(s) in %d ms of samples",
            len(satellites),
            duration_ms,
        )
        return signal

    def _get_code(self, prn: int, total_samples: int, phase_offset: int) -> np.ndarray:
        """Return a tiled, phase-shifted C/A code covering *total_samples*."""
        if prn not in self._codes:
            self._codes[prn] = resample_code(prn, self.sample_rate)
        code = self._codes[prn]
        spc = len(code)
        # Phase shift by rolling the base code, then tile to fill total_samples
        shifted = np.roll(code, phase_offset)
        repeats = (total_samples + spc - 1) // spc
        return np.tile(shifted, repeats)[:total_samples]
