"""Input sanitisation for the notes board.

Two jobs:

* ``clean_text(s)`` — strip control chars, collapse whitespace, enforce
  the 280-char hard cap. Returns ``None`` if the result is empty.
* ``clean_name(s)`` — same idea for the optional display name, 24-char
  cap, and stripped of newlines so a name can't masquerade as a note
  body in the UI render.

The spec says "URLs shown but not clickable" — that's enforced in the
UI by rendering plain text. We deliberately do *not* match URLs here:
trying to detect them in 280 chars of arbitrary text is more
false-positive than help.
"""

from __future__ import annotations

import re
import unicodedata

TEXT_MAX = 280
NAME_MAX = 24

# Strip every C0/C1 control char except newline (the UI renders \n as a
# soft break). \t collapses with the whitespace squash below.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_WS_RUN = re.compile(r"[ \t]+")
_LINE_RUN = re.compile(r"\n{3,}")


def clean_text(raw: str) -> str | None:
    if raw is None:
        return None
    s = unicodedata.normalize("NFC", raw)
    s = _CONTROL.sub("", s)
    s = _WS_RUN.sub(" ", s)
    s = _LINE_RUN.sub("\n\n", s)
    s = s.strip()
    if not s:
        return None
    if len(s) > TEXT_MAX:
        s = s[:TEXT_MAX].rstrip()
    return s


def clean_name(raw: str | None) -> str:
    if not raw:
        return ""
    s = unicodedata.normalize("NFC", raw)
    s = _CONTROL.sub("", s).replace("\n", " ").replace("\r", " ")
    s = _WS_RUN.sub(" ", s).strip()
    if len(s) > NAME_MAX:
        s = s[:NAME_MAX].rstrip()
    return s
