"""DOCX / HTML / PPTX via MarkItDown (MIT, Microsoft), then our block parser.

MarkItDown gives us good-enough Markdown for office and web formats in one
dependency. What it cannot give us is style: colour, size, `display:none`. For
HTML that pass arrives with detector H4 in week 3 (a BeautifulSoup walk over
the same file); for DOCX a python-docx pass over run properties (vanish, colour).
Both sit behind this same interface — the engine won't notice (ADR-010).
"""

from __future__ import annotations

from pathlib import Path

from lectern.converters.markdown_blocks import markdown_to_blocks
from lectern.models import Document


class MarkItDownConverter:
    name = "markitdown"
    formats = frozenset({"docx", "html", "htm", "pptx"})

    def convert(self, path: Path) -> Document:
        from markitdown import MarkItDown  # heavy import, keep it local

        result = MarkItDown(enable_plugins=False).convert(str(path))
        blocks = markdown_to_blocks(result.markdown)
        title = result.title or next(
            (b.text for b in blocks if b.type.value == "heading" and b.level == 1), None
        )
        return Document(
            source=str(path),
            format=path.suffix.lower().lstrip("."),
            converter=self.name,
            title=title,
            blocks=blocks,
        )
