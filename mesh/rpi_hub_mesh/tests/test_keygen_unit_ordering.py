"""Static parse of the two systemd units to guard the keygen ordering.

GAP §5 callout: only ``identity.load_or_create()`` was unit-tested; the
systemd unit's ordering vs. ``rpi-hub-mesh.service`` had no automated
check. A regression here means first boot ships with keys but the
daemon races keygen and starts with no usable credentials.

We use :mod:`configparser` because systemd units are INI-like. Two
caveats worth documenting:

1. systemd allows the same key to appear more than once in a section
   (e.g. ``LoadCredential=`` twice). :class:`configparser.ConfigParser`
   only keeps the last value under default settings; we set
   ``strict=False`` and ``dict_type=lambda: _MultiDict()`` so we can
   read every directive.
2. systemd treats ``After=foo bar`` and two ``After=foo``/``After=bar``
   lines identically. We normalise into a set of tokens.
"""

from __future__ import annotations

import configparser
from collections import OrderedDict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
KEYGEN_UNIT = REPO_ROOT / "systemd" / "rpi-hub-mesh-keygen.service"
MESH_UNIT = REPO_ROOT / "systemd" / "rpi-hub-mesh.service"


class _MultiDict(OrderedDict):  # type: ignore[type-arg]
    """Allow duplicate keys in a single section.

    systemd directives like ``LoadCredential=`` legitimately repeat;
    configparser would otherwise raise ``DuplicateOptionError``.
    """

    def __setitem__(self, key: str, value: Any) -> None:  # noqa: ANN401
        if isinstance(value, list) and key in self:
            existing = super().__getitem__(key)
            if isinstance(existing, list):
                super().__setitem__(key, existing + value)
                return
        super().__setitem__(key, value)


def _parse_unit(path: Path) -> configparser.RawConfigParser:
    cp = configparser.RawConfigParser(dict_type=_MultiDict, strict=False, allow_no_value=True)
    # Preserve case — systemd directives are case-sensitive.
    cp.optionxform = str  # type: ignore[assignment]
    cp.read(path)
    return cp


def _tokens(section: configparser.SectionProxy, key: str) -> set[str]:
    """Split a directive's value(s) into whitespace-separated tokens.

    Handles both forms: ``After=a b c`` and repeated ``After=`` lines.
    """

    if not section.parser.has_option(section.name, key):
        return set()
    raw = section[key]
    # configparser concatenates duplicates with newlines.
    tokens: set[str] = set()
    for line in raw.splitlines():
        tokens.update(line.split())
    return tokens


def test_keygen_runs_before_mesh() -> None:
    """Either keygen says Before= mesh, or mesh says After= keygen.

    systemd treats the two as equivalent ordering directives; we
    accept either form so a future refactor doesn't break this test."""

    keygen = _parse_unit(KEYGEN_UNIT)
    mesh = _parse_unit(MESH_UNIT)

    keygen_before = _tokens(keygen["Unit"], "Before")
    mesh_after = _tokens(mesh["Unit"], "After")

    assert "rpi-hub-mesh.service" in keygen_before or "rpi-hub-mesh-keygen.service" in mesh_after, (
        "keygen must be ordered ahead of rpi-hub-mesh.service " "(keygen Before= or mesh After=)"
    )


def test_mesh_requires_keygen() -> None:
    """Ordering alone isn't enough — without a hard dep, systemd will
    happily start rpi-hub-mesh even when keygen failed."""

    mesh = _parse_unit(MESH_UNIT)
    requires = _tokens(mesh["Unit"], "Requires")
    wants = _tokens(mesh["Unit"], "Wants")
    assert (
        "rpi-hub-mesh-keygen.service" in requires or "rpi-hub-mesh-keygen.service" in wants
    ), "rpi-hub-mesh.service must Requires= or Wants= the keygen unit"


def test_keygen_is_oneshot_remain_after_exit() -> None:
    """A oneshot unit that doesn't RemainAfterExit= would be considered
    "inactive" after running, which breaks ``Requires=`` semantics on
    later starts of rpi-hub-mesh."""

    keygen = _parse_unit(KEYGEN_UNIT)
    service = keygen["Service"]
    assert service.get("Type") == "oneshot"
    # systemd accepts yes/true/1; we use the canonical form in the unit.
    assert service.get("RemainAfterExit", "").lower() in {"yes", "true", "1"}


def test_mesh_load_credential_points_at_keygen_output() -> None:
    """The daemon never reads ``/var/lib/rpi-hub/keys`` directly at
    runtime — it relies on the credential manager. If the
    ``LoadCredential=`` source path drifts from the path keygen writes
    (``StateDirectory=rpi-hub/keys`` → ``/var/lib/rpi-hub/keys``), the
    daemon will start with no credentials."""

    mesh = _parse_unit(MESH_UNIT)
    raw = mesh["Service"]["LoadCredential"]
    # Possible duplicates land on consecutive lines.
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    by_name: dict[str, str] = {}
    for line in lines:
        # Form: <credential-id>:<source-path>
        cred_id, _, source = line.partition(":")
        by_name[cred_id.strip()] = source.strip()

    assert by_name.get("ed25519_priv") == "/var/lib/rpi-hub/keys/ed25519.priv"
    assert by_name.get("ed25519_pub") == "/var/lib/rpi-hub/keys/ed25519.pub"

    # And the keygen unit really does land its output under
    # /var/lib/rpi-hub/keys (StateDirectory=rpi-hub/keys is the systemd
    # convention for /var/lib/<value>).
    keygen = _parse_unit(KEYGEN_UNIT)
    assert keygen["Service"].get("StateDirectory") == "rpi-hub/keys"
