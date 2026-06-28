"""rpi-hub-listen — FastAPI app on 127.0.0.1:8300.

Mounted by nginx at ``/api/listen``. The endpoint surface is small
because the heavy work (audio decoding, SAME parsing) happens in helper
processes the :mod:`dongle` module supervises — the FastAPI app is just
a control plane and an alert mailbox.

Endpoints (all GET unless noted):

* ``/state``                 — current mode, frequency, label
* ``/presets`` (mode=…)      — preset list for the requested mode
* ``POST /tune`` {mode, frequency_hz, label} — switch modes
* ``POST /stop``             — go to idle
* ``/alerts``                — recent SAME alerts (for landing-page banner)
* ``POST /alerts/internal``  — internal feed from the SAME decoder
                                pipeline; localhost-bound only
* ``/gps``                   — Phase 13: sweep state + last sky-survey report
* ``POST /gps/sweep``        — Phase 13: start a finite GPS L1 acquisition sweep
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from . import __version__, alerts, dongle, gps, presets, same

app = FastAPI(
    title="rpi-hub-listen",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_TUNER = dongle.Tuner()
_ALERTS = alerts.AlertRing()
_GPS = gps.GPSSweeper(_TUNER)
# Phase 13: bench/dev escape hatch — run the GPS sweep against the
# gps_sdr simulator instead of hardware (no dongle/antenna required).
GPS_SIMULATE = os.environ.get("rpi_hub_GPS_SIMULATE", "") == "1"
# A pack-supplied county FIPS to filter banner-promoted alerts. Empty =
# promote everything (default).
FIPS_FILTER = os.environ.get("rpi_hub_LISTEN_FIPS", "")


class TuneIn(BaseModel):
    mode: Annotated[str, Field(pattern="^(weather|broadcast|bands)$")]
    frequency_hz: int = Field(ge=24_000_000, le=1_700_000_000)
    label: Annotated[str, Field(max_length=64)] = ""


class StateOut(BaseModel):
    mode: str
    frequency_hz: int
    label: str
    dongle_present: bool


class PresetOut(BaseModel):
    label: str
    frequency_hz: int


class PresetsOut(BaseModel):
    mode: str
    presets: list[PresetOut]


class AlertOut(BaseModel):
    event_code: str
    event_label: str
    fips_codes: list[str]
    duration_minutes: int
    station: str
    received_ts: float
    expires_ts: float
    promote_banner: bool


class AlertsOut(BaseModel):
    alerts: list[AlertOut]


class InternalAlertIn(BaseModel):
    line: Annotated[str, Field(min_length=4, max_length=512)]


def _state_payload() -> StateOut:
    st = _TUNER.state
    return StateOut(
        mode=st.mode,
        frequency_hz=st.frequency_hz,
        label=st.label,
        dongle_present=dongle.dongle_present(),
    )


@app.get("/health")
def health() -> dict[str, object]:
    return {"version": __version__, "dongle_present": dongle.dongle_present()}


@app.get("/state", response_model=StateOut)
def state() -> StateOut:
    return _state_payload()


@app.get("/presets", response_model=PresetsOut)
def list_presets(mode: str) -> PresetsOut:
    if mode == "weather":
        rows = presets.load_noaa()
    elif mode == "broadcast":
        rows = presets.FM_BAND
    elif mode == "bands":
        rows = presets.HAM_PRESETS
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown mode")
    return PresetsOut(
        mode=mode,
        presets=[PresetOut(label=p.label, frequency_hz=p.frequency_hz) for p in rows],
    )


@app.post("/tune", response_model=StateOut)
def tune(body: TuneIn) -> StateOut:
    # Always stop first — single-listener arbitration. Returns to idle
    # cleanly even when the previous mode was an error path.
    _TUNER.stop()
    try:
        if body.mode == "weather":
            _TUNER.start_weather(body.frequency_hz, body.label or "Weather")
        elif body.mode == "broadcast":
            _TUNER.start_broadcast(body.frequency_hz, body.label or "FM")
        elif body.mode == "bands":
            _TUNER.start_bands(body.frequency_hz, body.label or "Bands")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown mode")
    except dongle.TunerUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return _state_payload()


@app.post("/stop", response_model=StateOut)
def stop() -> StateOut:
    _TUNER.stop()
    return _state_payload()


# ── Phase 13: GPS sky survey ─────────────────────────────────────────────────


class GpsSweepIn(BaseModel):
    """Sweep parameters. Defaults are sane for a Pi 4/5 hardware sweep."""

    prns: list[Annotated[int, Field(ge=1, le=32)]] | None = None
    integration_ms: Annotated[int, Field(ge=1, le=10)] = 2


class GpsOut(BaseModel):
    running: bool
    dongle_present: bool
    simulate: bool
    # Last completed sweep record: requested_ts/completed_ts/ok/error/report.
    # report is the gps_sdr JSON contract (see gps_sdr/__main__.py).
    last: dict | None


def _gps_payload() -> GpsOut:
    return GpsOut(
        running=_GPS.running(),
        dongle_present=dongle.dongle_present(),
        simulate=GPS_SIMULATE,
        last=_GPS.last(),
    )


@app.get("/gps", response_model=GpsOut)
def gps_state() -> GpsOut:
    return _gps_payload()


@app.post("/gps/sweep", response_model=GpsOut, status_code=status.HTTP_202_ACCEPTED)
def gps_sweep(body: GpsSweepIn) -> GpsOut:
    # Unlike /tune we do NOT stop-then-start: a sweep is a background
    # diagnostic and must not silently kill someone's weather audio.
    if _TUNER.state.mode != "idle":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"dongle busy (mode={_TUNER.state.mode}); stop first",
        )
    if not GPS_SIMULATE and not dongle.dongle_present():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no RTL-SDR dongle detected",
        )
    try:
        _GPS.start(
            prns=body.prns,
            integration_ms=body.integration_ms,
            simulate=GPS_SIMULATE,
        )
    except dongle.TunerBusy as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except dongle.TunerUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return _gps_payload()


def _serialise_alert(a: alerts.StoredAlert) -> AlertOut:
    return AlertOut(
        event_code=a.alert.event_code,
        event_label=a.alert.event_label,
        fips_codes=a.alert.fips_codes,
        duration_minutes=a.alert.duration_minutes,
        station=a.alert.station,
        received_ts=a.received_ts,
        expires_ts=a.expires_ts,
        promote_banner=a.alert.affects_fips(FIPS_FILTER),
    )


@app.get("/alerts", response_model=AlertsOut)
def list_alerts() -> AlertsOut:
    return AlertsOut(alerts=[_serialise_alert(a) for a in _ALERTS.recent()])


@app.post("/alerts/internal", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def push_internal_alert(req: Request, body: InternalAlertIn) -> AlertOut:
    # Defence in depth: nginx already restricts this path, but we also
    # require a local peer. The SAME decoder pipeline runs on
    # 127.0.0.1; any non-loopback caller is a bug or an attack.
    client = req.client
    if client is None or client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    parsed = same.parse(body.line)
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unparseable SAME line")
    return _serialise_alert(_ALERTS.push(parsed))
