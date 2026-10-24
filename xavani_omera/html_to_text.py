"""Convert HTML to readable text with the standard library only."""
from __future__ import annotations

from html.parser import HTMLParser

SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}
BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
    "section", "article", "header", "footer", "blockquote", "pre",
}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._in_title = False
        self._parts: list[str] = []
        self.title = ""

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title += data
            return
        self._parts.append(data)


def html_to_text(markup: str, max_chars: int = 6000) -> tuple[str, str]:
    """Return (title, body text) from an HTML document."""
    parser = _Extractor()
    parser.feed(markup)
    parser.close()
    lines = [" ".join(line.split()) for line in "".join(parser._parts).splitlines()]
    body = "\n".join(line for line in lines if line)
    return parser.title.strip(), body[:max_chars]
