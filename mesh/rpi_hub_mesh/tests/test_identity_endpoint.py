"""Endpoint-level tests for ``GET /identity.svg`` and ``GET /identity``.

GAP §5 callout: the test image we ship doesn't have ``fastapi.testclient``
installed, so this surface had never been exercised at the HTTP layer.
We drive the FastAPI app directly with :class:`fastapi.testclient.TestClient`
to assert:

* (a) keys present → ``/identity.svg`` returns 200 with ``image/svg+xml``
* (b) keys absent → the endpoint *still* returns 200 with a valid SVG
  (the daemon synthesises a stub fingerprint in
  :func:`identity.load_from_credentials` so the trust UI is never blank)
* (c) the SVG embeds the same fingerprint string ``/identity`` exposes

A tmp dir backs the key paths — production ``/etc/rpi-hub``/``/var/lib/rpi-hub``
locations are never touched.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mesh.rpi_hub_mesh import identity, main


@pytest.fixture(autouse=True)
def _reset_bundle_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wipe the per-process identity cache between tests.

    ``main._BUNDLE`` is a module-level singleton; without resetting,
    the first test's fixture state would leak into the second.
    """

    monkeypatch.setattr(main, "_BUNDLE", None)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)


@pytest.fixture
def keyless_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Identity lookup falls through to the deterministic stub bundle."""

    monkeypatch.setattr(identity, "PRIV_PATH", tmp_path / "absent.priv")
    monkeypatch.setattr(identity, "PUB_PATH", tmp_path / "absent.pub")
    return TestClient(main.app)


@pytest.fixture
def keyed_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Pre-seeded keypair on disk, picked up via the dev fallback path."""

    priv = tmp_path / "ed25519.priv"
    pub = tmp_path / "ed25519.pub"
    priv.write_bytes(b"\x55" * 32)
    pub.write_bytes(b"\xaa" * 32)
    monkeypatch.setattr(identity, "PRIV_PATH", priv)
    monkeypatch.setattr(identity, "PUB_PATH", pub)
    return TestClient(main.app)


def test_identity_svg_returns_image_when_keys_present(keyed_client: TestClient) -> None:
    r = keyed_client.get("/identity.svg")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    body = r.text
    assert body.startswith("<svg")
    assert body.rstrip().endswith("</svg>")
    # Operator should be able to cache the printable code for a minute.
    assert "max-age=60" in r.headers.get("cache-control", "")


def test_identity_svg_serves_stub_when_keys_absent(keyless_client: TestClient) -> None:
    """No keys on disk and no CREDENTIALS_DIRECTORY → daemon still
    serves a valid SVG built from the deterministic stub fingerprint.

    This is by design (see :func:`identity.load_from_credentials`): the
    trust UI must render so the operator can see the empty-keys state,
    rather than getting a 5xx.
    """

    r = keyless_client.get("/identity.svg")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in r.text


def test_identity_svg_matches_identity_endpoint(keyed_client: TestClient) -> None:
    """The fingerprint surfaced at /identity is the same payload the QR
    encodes — otherwise a peer scanning our QR would paste a string
    that doesn't match what we report on /identity, breaking the trust
    handshake."""

    info = keyed_client.get("/identity").json()
    fp: str = info["fingerprint"]
    # Sanity: well-formed fingerprint shape (6 groups of 4 base32 chars).
    assert re.fullmatch(r"[A-Z2-7]{4}(-[A-Z2-7]{4}){5}", fp), fp

    svg = keyed_client.get("/identity.svg").text
    # The fingerprint isn't rendered as visible text in the SVG (it's
    # encoded in the QR matrix), so we re-encode it and assert the SVG
    # body matches what the encoder produces for the same input — that
    # is a stronger guarantee than substring search.
    from mesh.rpi_hub_mesh import qrcode

    expected = qrcode.to_svg(fp, module_px=8, quiet=4)
    assert svg == expected
