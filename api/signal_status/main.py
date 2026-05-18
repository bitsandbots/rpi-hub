"""FastAPI app exposing a single GET /status endpoint.

The endpoint is mounted at the root because nginx strips the /api/ prefix
before forwarding (see config/nginx/signal-portal.conf). So /api/status on
the public surface arrives here as GET /status.

This module is deliberately tiny — composition over framework magic. Every
host probe lives in `system.py` and is independently testable.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from . import __version__, system

app = FastAPI(
    title="signal-status",
    version=__version__,
    docs_url=None,  # No interactive docs on the device.
    redoc_url=None,
    openapi_url=None,
)


class StorageOut(BaseModel):
    kiwix_bytes_free: int | None
    kiwix_bytes_total: int | None


class VoltageOut(BaseModel):
    throttled: str | None
    undervoltage: bool | None


class ServicesOut(BaseModel):
    retrieve: str
    assist: str
    listen: str
    notes: str
    mesh: str
    mesh_fingerprint: str | None


class StatusResponse(BaseModel):
    uptime_seconds: float | None
    load_avg: tuple[float, float, float] | None
    storage: StorageOut
    voltage: VoltageOut
    dhcp_clients: int | None
    time_source: str
    build_version: str
    services: ServicesOut


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    s = system.storage()
    v = system.voltage()
    svc = system.services()
    return StatusResponse(
        uptime_seconds=system.uptime_seconds(),
        load_avg=system.load_avg(),
        storage=StorageOut(
            kiwix_bytes_free=s.kiwix_bytes_free,
            kiwix_bytes_total=s.kiwix_bytes_total,
        ),
        voltage=VoltageOut(
            throttled=v.throttled,
            undervoltage=v.undervoltage,
        ),
        dhcp_clients=system.dhcp_clients(),
        time_source=system.time_source(),
        build_version=system.build_version(),
        services=ServicesOut(
            retrieve=svc.retrieve,
            assist=svc.assist,
            listen=svc.listen,
            notes=svc.notes,
            mesh=svc.mesh,
            mesh_fingerprint=svc.mesh_fingerprint,
        ),
    )
