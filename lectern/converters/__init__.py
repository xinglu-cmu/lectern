"""`load`: any supported file -> a normalized `Document` (DESIGN §4).

One `Converter` interface, several implementations behind it (ADR-010):

- PDF: our own pdfplumber pass (`pdf.py`), because it keeps the font size,
  colour and position of every word — the raw material for the hidden-text
  detectors, which every Markdown-producing converter throws away.
- HTML: our own DOM walk (`html.py`) that records how the page hides text
  (`display:none`, zero font size, text coloured like its background, comments).
- DOCX: our own XML read (`docx.py`) that keeps run colour, size and the
  hidden flag.
- PPTX and anything else MarkItDown handles: MarkItDown (`markitdown_conv.py`),
  then our Markdown block parser.
- Markdown / plain text: the block parser directly (`markdown_blocks.py`).

The engine calls `load(path)`; nothing above this module knows which converter ran.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from lectern.models import Document


class UnsupportedFormat(ValueError):
    pass


class Converter(Protocol):
    name: str
    formats: frozenset[str]

    def convert(self, path: Path) -> Document: ...


def _registry() -> list[Converter]:
    # Imported lazily so `lectern --help` doesn't pay for pdfplumber/markitdown.
    from lectern.converters.docx import DocxConverter
    from lectern.converters.html import HtmlConverter
    from lectern.converters.markdown_blocks import MarkdownConverter
    from lectern.converters.markitdown_conv import MarkItDownConverter
    from lectern.converters.pdf import PdfConverter

    return [
        PdfConverter(),
        HtmlConverter(),
        DocxConverter(),
        MarkdownConverter(),
        MarkItDownConverter(),
    ]


def supported_formats() -> set[str]:
    return {f for c in _registry() for f in c.formats}


def pick_converter(path: Path) -> Converter:
    fmt = path.suffix.lower().lstrip(".")
    for conv in _registry():
        if fmt in conv.formats:
            return conv
    raise UnsupportedFormat(
        f"unsupported format '.{fmt}' — supported: {', '.join(sorted(supported_formats()))}"
    )


def load(path: str | Path) -> Document:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    return pick_converter(path).convert(path)
