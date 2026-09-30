"""Markdown (and plain text) -> blocks. Also the second half of every converter
that produces Markdown (MarkItDown), so headings, lists, code fences and tables
end up as the same block types whatever the source format was.

Deliberately small: ATX and setext headings, fenced code, pipe tables, list
items with indented continuation lines, blank-line-separated paragraphs. No
inline parsing — the text stays as written, which is also what `clean` will emit.
"""

from __future__ import annotations

import re
from pathlib import Path

from lectern.models import Anchor, Block, BlockType, Document

_ATX = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_SETEXT = re.compile(r"^(=+|-+)\s*$")
_FENCE = re.compile(r"^(```|~~~)")
_LIST = re.compile(r"^(\s*)([-*+•]|\d+[.)]|[a-zA-Z][.)]|\(\d+\))\s+(.*)$")
_TABLE = re.compile(r"^\s*\|.*\|\s*$")


def markdown_to_blocks(text: str, *, page: int | None = None) -> list[Block]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[Block] = []

    def add(btype: BlockType, body: str, level: int | None = None) -> None:
        body = body.strip("\n")
        if not body.strip():
            return
        blocks.append(
            Block(type=btype, text=body, level=level, anchor=Anchor(page=page, block=len(blocks)))
        )

    para: list[str] = []

    def flush_para() -> None:
        if para:
            add(BlockType.paragraph, " ".join(s.strip() for s in para))
            para.clear()

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_para()
            i += 1
            continue

        fence = _FENCE.match(stripped)
        if fence:
            flush_para()
            marker = fence.group(1)
            j = i + 1
            while j < n and not lines[j].strip().startswith(marker):
                j += 1
            add(BlockType.code, "\n".join(lines[i : min(j + 1, n)]))
            i = j + 1
            continue

        m = _ATX.match(stripped)
        if m:
            flush_para()
            add(BlockType.heading, m.group(2), level=len(m.group(1)))
            i += 1
            continue

        if i + 1 < n and _SETEXT.match(lines[i + 1].strip()) and not para and stripped:
            flush_para()
            add(BlockType.heading, stripped, level=1 if lines[i + 1].strip()[0] == "=" else 2)
            i += 2
            continue

        if _TABLE.match(line):
            flush_para()
            j = i
            while j < n and _TABLE.match(lines[j]):
                j += 1
            add(BlockType.table, "\n".join(lines[i:j]))
            i = j
            continue

        lm = _LIST.match(line)
        if lm:
            flush_para()
            indent = len(lm.group(1))
            item = [stripped]
            j = i + 1
            # continuation lines: non-blank, indented deeper than the marker, not a new item
            while j < n and lines[j].strip() and not _LIST.match(lines[j]):
                if len(lines[j]) - len(lines[j].lstrip()) > indent:
                    item.append(lines[j].strip())
                    j += 1
                else:
                    break
            add(BlockType.list_item, " ".join(item))
            i = j
            continue

        para.append(line)
        i += 1

    flush_para()
    return blocks


class MarkdownConverter:
    name = "markdown"
    formats = frozenset({"md", "markdown", "txt", "text"})

    def convert(self, path: Path) -> Document:
        text = path.read_text(encoding="utf-8", errors="replace")
        blocks = markdown_to_blocks(text)
        title = next((b.text for b in blocks if b.type.value == "heading" and b.level == 1), None)
        return Document(
            source=str(path),
            format=path.suffix.lower().lstrip(".") or "txt",
            converter=self.name,
            title=title,
            blocks=blocks,
        )
