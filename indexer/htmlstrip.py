"""Convert Kiwix ZIM article HTML into chunk.py-ready plain text.

chunk.py's section splitter looks for "== Heading ==" boundary lines
(see chunk.py:22-24) — this module is what produces that convention
from a ZIM entry's raw <h1>-<h6> tags, so build_index._iter_articles
can feed real article text (not markup) to the chunker and embedder.

Stdlib-only (html.parser) — no new workstation dependency.
"""

from __future__ import annotations

from html.parser import HTMLParser

_SKIP_TAGS = {"script", "style", "noscript", "template"}
_BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "nav",
    "table",
    "tr",
    "td",
    "th",
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    "blockquote",
    "pre",
    "br",
    "hr",
}
_HEADING_LEVEL = {"h1": 2, "h2": 2, "h3": 3, "h4": 4, "h5": 4, "h6": 4}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._heading_level: int | None = None
        self._heading_buf: list[str] = []
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in _HEADING_LEVEL:
            self._heading_level = _HEADING_LEVEL[tag]
            self._heading_buf = []
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS and not self._skip_depth:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in _HEADING_LEVEL and self._heading_level is not None:
            title = " ".join("".join(self._heading_buf).split())
            if title:
                eq = "=" * self._heading_level
                self._parts.append(f"\n{eq} {title} {eq}\n")
            self._heading_level = None
            self._heading_buf = []
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._heading_level is not None:
            self._heading_buf.append(data)
        else:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def html_to_text(html: str) -> str:
    """Strip a Kiwix article body down to plain text with `== Heading ==` markers."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()

    lines = [line.strip() for line in parser.text().splitlines()]
    out_lines: list[str] = []
    blank_run = 0
    for line in lines:
        if line:
            out_lines.append(line)
            blank_run = 0
        else:
            blank_run += 1
            if blank_run == 1:
                out_lines.append("")
    return "\n".join(out_lines).strip()
