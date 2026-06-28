"""Parallel Code Phase Search (PCPS) GPS L1 acquisition engine.

Algorithm
─────────
For each PRN, search all (code phase, Doppler) combinations simultaneously:

  For each integration millisecond:
    1. Block select:  blk = samples[ms·N : (ms+1)·N]          (N = spc)
    2. Carrier wipe:  W[d, n] = blk[n] · exp(−j2π·f_d·n/fs)  (vectorised over all f_d)
    3. FFT:           S[d, :] = FFT(W[d, :])                   along axis-1
    4. Correlate:     R[d, :] = IFFT(S[d, :] · C*[prn, :])    C* pre-computed
    5. Accumulate:    P[d, :] += |R[d, :]|²                    non-coherent sum

After integration:
  - Peak:        (d̂, ĉ) = argmax(P)
  - Noise floor: mean of P excluding a ±1-chip exclusion zone
  - Metric:      P[d̂, ĉ] / noise_floor  >  threshold  →  ACQUIRED

Vectorising the Doppler loop over NumPy axes makes the inner loop ~10× faster
than a Python for-loop over frequency bins.

Reference: Borre et al., "A Software-Defined GPS and Galileo Receiver" (2007).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .constants import (
    CA_CODE_LENGTH,
    DEFAULT_ACQ_THRESHOLD,
    DEFAULT_DOPPLER_RANGE_HZ,
    DEFAULT_DOPPLER_STEP_HZ,
    DEFAULT_INTEGRATION_MS,
    DEFAULT_SAMPLE_RATE,
)
from .prn import precompute_code_ffts

log = logging.getLogger(__name__)


@dataclass
class AcquisitionResult:
    """Outcome of a satellite search for one PRN."""
    prn: int
    acquired: bool
    doppler_hz: float = 0.0
    code_phase: int = 0          # samples (offset into 1 ms block)
    peak_power: float = 0.0
    noise_floor: float = 1.0

    @property
    def metric(self) -> float:
        """Peak-to-noise-floor power ratio."""
        return self.peak_power / self.noise_floor if self.noise_floor > 0 else 0.0

    @property
    def cn0_proxy_db(self) -> float:
        """C/N₀ proxy in dB  (10·log₁₀(metric)).
        Not a calibrated C/N₀ — use only for relative comparison."""
        m = self.metric
        return 10.0 * np.log10(m) if m > 0 else -99.0


class GPSAcquisition:
    """Vectorised PCPS acquisition for all 32 GPS C/A PRN codes."""

    def __init__(
        self,
        sample_rate: float = DEFAULT_SAMPLE_RATE,
        doppler_range_hz: float = DEFAULT_DOPPLER_RANGE_HZ,
        doppler_step_hz: float = DEFAULT_DOPPLER_STEP_HZ,
        integration_ms: int = DEFAULT_INTEGRATION_MS,
        threshold: float = DEFAULT_ACQ_THRESHOLD,
    ) -> None:
        self.sample_rate = sample_rate
        self.integration_ms = integration_ms
        self.threshold = threshold

        # Samples per 1 ms C/A code period
        self.spc = int(round(sample_rate * 1e-3))

        # Doppler frequency bins  (shape: n_dop)
        self.doppler_bins = np.arange(
            -doppler_range_hz,
            doppler_range_hz + doppler_step_hz,
            doppler_step_hz,
            dtype=np.float64,
        )
        n_dop = len(self.doppler_bins)

        # Sample time axis for one code period  (shape: spc)
        t = np.arange(self.spc, dtype=np.float64) / sample_rate

        # Pre-compute complex carrier wipe-off vectors for every Doppler bin.
        # Shape: (n_dop, spc) — avoids recomputing exp() in the inner loop.
        log.info(
            "Pre-computing %d Doppler carriers and 32 PRN FFTs …", n_dop
        )
        t0 = time.monotonic()
        self._carriers = np.exp(
            -1j * 2.0 * np.pi * self.doppler_bins[:, np.newaxis] * t[np.newaxis, :]
        ).astype(np.complex64)   # (n_dop, spc)

        # Pre-compute conjugate FFTs of all 32 resampled C/A codes.
        # Shape of each value: (spc,)  complex64
        self._code_ffts = precompute_code_ffts(sample_rate)  # {prn: array}
        log.info("  done in %.2f s", time.monotonic() - t0)

        # One-chip exclusion half-width in samples (for noise floor estimation)
        self._chip_samps = max(1, self.spc // CA_CODE_LENGTH)

    # ── public ────────────────────────────────────────────────────────────────

    def run(
        self,
        samples: np.ndarray,
        prns: Sequence[int] | None = None,
    ) -> list[AcquisitionResult]:
        """Search for GPS satellites in *samples*.

        Args:
            samples:  Complex IQ array.  Must contain ≥ integration_ms × spc
                      samples (e.g. 2048 samples for 1 ms at 2.048 Msps).
            prns:     PRN numbers to search (default: all 32).

        Returns:
            ``list[AcquisitionResult]`` sorted by metric (best first).
        """
        if prns is None:
            prns = list(range(1, 33))

        required = self.spc * self.integration_ms
        if len(samples) < required:
            raise ValueError(
                f"Need ≥ {required} samples ({self.integration_ms} ms "
                f"at {self.sample_rate/1e6:.3f} Msps); got {len(samples)}"
            )

        results = [self._search_prn(int(p), samples) for p in prns]
        results.sort(key=lambda r: r.metric, reverse=True)
        return results

    # ── internal ──────────────────────────────────────────────────────────────

    def _search_prn(self, prn: int, samples: np.ndarray) -> AcquisitionResult:
        """Non-coherent PCPS integration across all Doppler bins for one PRN."""
        n_dop = len(self.doppler_bins)
        code_fft_c = self._code_ffts[prn]   # shape: (spc,)

        # Accumulate power over integration_ms code periods
        power_sum = np.zeros((n_dop, self.spc), dtype=np.float64)

        for ms in range(self.integration_ms):
            blk = samples[ms * self.spc : (ms + 1) * self.spc].astype(np.complex64)

            # Vectorised carrier wipe: (n_dop, spc) * (spc,) → (n_dop, spc)
            wiped = blk[np.newaxis, :] * self._carriers   # broadcast

            # Batch FFT along axis-1
            S = np.fft.fft(wiped, axis=1)

            # Correlate with PRN code (broadcast code along axis-0)
            R = np.fft.ifft(S * code_fft_c[np.newaxis, :], axis=1)

            # Non-coherent power accumulation
            power_sum += np.abs(R) ** 2

        # ── peak detection ────────────────────────────────────────────────────
        d_idx, c_idx = np.unravel_index(np.argmax(power_sum), power_sum.shape)
        best_peak = float(power_sum[d_idx, c_idx])
        best_dop = float(self.doppler_bins[d_idx])
        best_phase = int(c_idx)

        # ── noise floor ───────────────────────────────────────────────────────
        # Exclude ±1 chip around the peak column from the noise estimate.
        excl_lo = max(0, c_idx - self._chip_samps)
        excl_hi = min(self.spc, c_idx + self._chip_samps + 1)
        mask = np.ones(power_sum.shape, dtype=bool)
        mask[:, excl_lo:excl_hi] = False
        valid = power_sum[mask]
        noise_floor = float(valid.mean()) if valid.size > 0 else float(power_sum.mean())

        acquired = noise_floor > 0 and (best_peak / noise_floor) >= self.threshold

        if acquired:
            log.info(
                "PRN %2d  ACQUIRED  doppler=%+.0f Hz  phase=%d  metric=%.1f",
                prn, best_dop, best_phase, best_peak / noise_floor,
            )

        return AcquisitionResult(
            prn=prn,
            acquired=acquired,
            doppler_hz=best_dop,
            code_phase=best_phase,
            peak_power=best_peak,
            noise_floor=noise_floor,
        )
