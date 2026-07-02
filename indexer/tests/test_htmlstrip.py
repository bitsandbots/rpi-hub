"""Unit tests for htmlstrip — runs without any optional deps."""

from __future__ import annotations

from indexer.htmlstrip import html_to_text


def test_strips_tags_and_keeps_text() -> None:
    html = "<html><body><p>Boil water for one minute.</p></body></html>"
    assert html_to_text(html) == "Boil water for one minute."


def test_headings_become_equals_markers() -> None:
    html = (
        "<h1>Water Purification</h1>"
        "<p>Intro text.</p>"
        "<h2>Boiling</h2>"
        "<p>Bring to a rolling boil.</p>"
        "<h3>Altitude</h3>"
        "<p>Boil longer above 2000m.</p>"
    )
    text = html_to_text(html)
    assert "== Water Purification ==" in text
    assert "== Boiling ==" in text
    assert "=== Altitude ===" in text


def test_script_and_style_content_dropped() -> None:
    html = (
        "<html><head><style>body { color: red; }</style></head>"
        "<body><script>var x = 1;</script><p>Real content.</p></body></html>"
    )
    text = html_to_text(html)
    assert "color" not in text
    assert "var x" not in text
    assert text == "Real content."


def test_entities_decoded() -> None:
    html = "<p>Fish &amp; chips &mdash; caf&eacute;</p>"
    assert html_to_text(html) == "Fish & chips — café"


def test_table_cells_get_line_breaks() -> None:
    html = "<table><tr><td>Adult</td><td>2 mg</td></tr></table>"
    text = html_to_text(html)
    assert "<td>" not in text
    assert "Adult" in text
    assert "2 mg" in text
