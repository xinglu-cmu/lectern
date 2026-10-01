"""PPTX (and other MarkItDown formats) via MarkItDown, then our block parser.

MarkItDown gives good-enough Markdown in one dependency, but no style: colour,
size, hidden flags are gone. That is why PDF, HTML and DOCX have their own
converters; this one covers the long tail where hidden-text detection is not
yet attempted (ADR-010).
"""

from __future__ import annotations

from pathlib import Path

from lectern.converters.markdown_blocks import markdown_to_blocks
from lectern.models import Document


class MarkItDownConverter:
    name = "markitdown"
    formats = frozenset({"pptx", "xlsx", "epub", "rtf"})

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
