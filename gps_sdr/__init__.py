"""gps_sdr – GPS L1 C/A signal acquisition via RTL-SDR."""

__version__ = "1.0.0"
__all__ = ["GPSAcquisition", "GPSRadio", "GPSSimulator", "AcquisitionResult"]

from .acquisition import AcquisitionResult, GPSAcquisition
from .hardware import GPSRadio
from .simulate import GPSSimulator
