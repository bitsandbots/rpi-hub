"""RTL-SDR hardware abstraction for GPS L1 reception.

GPS signal budget (rough):
  Satellite EIRP at surface        ≈ −130 dBm
  Active patch antenna gain        ≈ +27 dB (LNA 1 dB NF, 27 dB gain)
  Coax loss                        ≈ −1 dB
  RTL-SDR noise figure             ≈ 6–8 dB
  Net pre-ADC SNR                  << 0 dB  (requires spreading-code gain)

The active antenna LNA must be powered via the bias tee (typically 4.5 V on
the coax centre conductor).  Without it, the passive patch receives at
≈ −160 dBm — far below the RTL-SDR noise floor.

Bias-tee support:
  • RTL-SDR Blog v3/v4: hardware GPIO-switched bias tee.
  • Controlled via librtlsdr 'rtlsdr_set_bias_tee()' or the rtl_biast CLI.
  • Other dongles: no hardware bias tee; use an external powered LNA instead.
"""

from __future__ import annotations

import logging
import shutil
import subprocess

import numpy as np

from .constants import DEFAULT_GAIN_DB, DEFAULT_SAMPLE_RATE, GPS_L1_FREQ

log = logging.getLogger(__name__)


class GPSRadio:
    """RTL-SDR wrapper configured for GPS L1 C/A acquisition.

    Usage::

        with GPSRadio(bias_tee=True) as radio:
            samples = radio.read_samples(radio.samples_for_ms(5))
    """

    def __init__(
        self,
        device_index: int = 0,
        sample_rate: float = DEFAULT_SAMPLE_RATE,
        ppm_correction: int = 0,
        bias_tee: bool = True,
        gain_db: float = DEFAULT_GAIN_DB,
    ) -> None:
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.ppm_correction = ppm_correction
        self.bias_tee = bias_tee
        self.gain_db = gain_db
        self._sdr = None
        self._bias_tee_active = False

    # ── context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "GPSRadio":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── public API ────────────────────────────────────────────────────────────

    def open(self) -> None:
        """Open the RTL-SDR device and apply GPS-optimised settings."""
        try:
            from rtlsdr import RtlSdr
        except ImportError as e:
            raise RuntimeError(
                "pyrtlsdr is not installed.\n"
                "  pip install pyrtlsdr\n"
                "You also need the librtlsdr system library:\n"
                "  Ubuntu/Debian: sudo apt install librtlsdr-dev\n"
                "  macOS:         brew install librtlsdr\n"
                "  Windows:       see https://www.rtl-sdr.com/rtl-sdr-quick-start-guide/"
            ) from e

        log.info("Opening RTL-SDR device %d …", self.device_index)
        self._sdr = RtlSdr(device_index=self.device_index)

        self._sdr.sample_rate = self.sample_rate
        self._sdr.center_freq = GPS_L1_FREQ
        self._sdr.freq_correction = self.ppm_correction
        self._sdr.gain = self.gain_db

        self._enable_bias_tee()

        log.info(
            "RTL-SDR ready  %.2f MHz  %.3f Msps  gain=%.1f dB  ppm=%+d",
            GPS_L1_FREQ / 1e6,
            self.sample_rate / 1e6,
            self.gain_db,
            self.ppm_correction,
        )

    def close(self) -> None:
        """Disable the bias tee and release the device."""
        if self._sdr is None:
            return
        try:
            if self._bias_tee_active:
                self._set_bias_tee_state(enable=False)
        finally:
            try:
                self._sdr.close()
            except Exception:
                pass
            self._sdr = None
            log.info("RTL-SDR closed")

    def read_samples(self, num_samples: int) -> np.ndarray:
        """Return *num_samples* complex64 IQ samples from the device."""
        if self._sdr is None:
            raise RuntimeError("Device is not open; call open() first")
        return np.array(self._sdr.read_samples(num_samples), dtype=np.complex64)

    def samples_for_ms(self, ms: int = 1) -> int:
        """Return the number of samples covering *ms* milliseconds."""
        return int(round(self.sample_rate * ms * 1e-3))

    # ── bias tee ──────────────────────────────────────────────────────────────

    def _enable_bias_tee(self) -> None:
        if not self.bias_tee:
            log.info("Bias tee disabled by user (--no-bias-tee)")
            return
        if self._set_bias_tee_state(enable=True):
            return
        log.warning(
            "⚠  Could not enable the bias tee automatically.\n"
            "   Options:\n"
            "     1. Enable manually before running:  rtl_biast -b 1\n"
            "        Then re-run with --no-bias-tee\n"
            "     2. Use an externally powered LNA on your feed line\n"
            "   Without a powered LNA, GPS acquisition is unlikely to succeed."
        )

    def _set_bias_tee_state(self, *, enable: bool) -> bool:
        """Try all known bias-tee control paths.  Returns True on success."""
        if self._try_pyrtlsdr_bias_tee(enable=enable):
            return True
        if self._try_rtl_biast_cli(enable=enable):
            return True
        return False

    def _try_pyrtlsdr_bias_tee(self, *, enable: bool) -> bool:
        """Use pyrtlsdr's set_bias_tee() if the library supports it."""
        try:
            self._sdr.set_bias_tee(1 if enable else 0)
            self._bias_tee_active = enable
            log.info("Bias tee %s via pyrtlsdr", "ENABLED ✓" if enable else "disabled")
            return True
        except AttributeError:
            # Older pyrtlsdr / librtlsdr builds lack this function
            return False
        except Exception as exc:
            log.debug("pyrtlsdr set_bias_tee failed: %s", exc)
            return False

    def _try_rtl_biast_cli(self, *, enable: bool) -> bool:
        """Fall back to the rtl_biast command-line utility."""
        if not shutil.which("rtl_biast"):
            return False
        try:
            cmd = [
                "rtl_biast",
                "-d", str(self.device_index),
                "-b", "1" if enable else "0",
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=5)
            self._bias_tee_active = enable
            log.info("Bias tee %s via rtl_biast", "ENABLED ✓" if enable else "disabled")
            return True
        except Exception as exc:
            log.debug("rtl_biast CLI failed: %s", exc)
            return False
