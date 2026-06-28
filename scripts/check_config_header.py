#!/usr/bin/env python3
"""Fail if any file under config/ lacks the required rpi-hub header comment.

Every config file must declare:
  - Purpose: one line
  - Unit: the systemd unit (or "n/a") that consumes it
  - Phase: integer phase that introduced it
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED = ("Purpose:", "Unit:", "Phase:")


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    head = "\n".join(text.splitlines()[:15])
    missing = [tag for tag in REQUIRED if tag not in head]
    if missing:
        return [f"{path}: missing header fields: {', '.join(missing)}"]
    return []


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: check_config_header.py <path> [path ...]", file=sys.stderr)
        return 2

    targets: list[Path] = []
    for arg in argv:
        p = Path(arg)
        if p.is_dir():
            targets.extend(p.rglob("*.conf"))
            targets.extend(p.rglob("*.yaml"))
            targets.extend(p.rglob("*.yml"))
        elif p.is_file():
            targets.append(p)

    errors: list[str] = []
    for path in sorted(targets):
        if re.search(r"\.(conf|ya?ml)$", path.name):
            errors.extend(check(path))

    for err in errors:
        print(err, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
