"""PDF -> blocks, keeping the style of every word.

Why our own pass instead of MarkItDown's PDF path (pdfminer text dump): the
hidden-text detectors need colour, font size and position, and a Markdown string
has none of them. pdfplumber exposes the same pdfminer character data *with*
those attributes, so we group words into lines, lines into blocks, and keep a
`Run` for every stretch of uniform style. Nothing is filtered here — a white 1pt
word is still a word. Deciding that it is suspicious is the detectors' job
(week 3); this module only makes sure the evidence survives.

Structure recovered:
- body font size = the size that carries the most characters;
- headings = short lines noticeably larger than the body (levels by size), or
  bold short lines;
- list items = lines starting with a bullet or an enumerator, with wrapped
  continuation lines joined;
- page furniture = lines in the top/bottom 7% of the page, flagged `header` /
  `footer`, plus `repeated` when the same text recurs across pages and
  `page_number` when it is just a number. Zoning turns these into `structure`.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from lectern.models import Anchor, Block, BlockType, Document, Run, Style

_BULLET = re.compile(
    r"^([•·▪◦‣●○■□➢➤►✓✗Ø¢§\-–—*]|\d{1,3}[.)]|[a-zA-Z][.)]|\(\d{1,3}\)|\([a-z]\)|[ivx]+[.)])\s*$"
)
_PAGE_NUMBER = re.compile(r"^(page\s*)?[-–]?\s*\d{1,4}\s*[-–]?(\s*(of|/)\s*\d{1,4})?$", re.I)
_BOLD = re.compile(r"bold|black|heavy|semibold|demibold", re.I)
FURNITURE_BAND = 0.07  # top / bottom share of the page height counted as header / footer


@dataclass
class _Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float
    font: str
    color: str | None
    background: str | None = None


MAX_SHAPES = 3000  # beyond this, skip background lookup (dense vector drawings)


def _backgrounds(page) -> list[tuple[float, float, float, float, str]]:
    """Filled rectangles/curves and images on the page, as (x0, top, x1, bottom, colour)."""
    shapes: list[tuple[float, float, float, float, str]] = []
    for obj in list(page.rects) + list(page.curves):
        if not obj.get("fill"):
            continue
        color = color_to_hex(obj.get("non_stroking_color"))
        if color is None:
            continue
        shapes.append((obj["x0"], obj["top"], obj["x1"], obj["bottom"], color))
    for img in page.images:
        shapes.append((img["x0"], img["top"], img["x1"], img["bottom"], "image"))
    return shapes if len(shapes) <= MAX_SHAPES else []


def _background_at(shapes, x: float, y: float) -> str | None:
    """The smallest shape under the point: the one actually drawn behind the text."""
    best = None
    best_area = None
    for x0, top, x1, bottom, color in shapes:
        if x0 <= x <= x1 and top <= y <= bottom:
            area = (x1 - x0) * (bottom - top)
            if best_area is None or area < best_area:
                best, best_area = color, area
    return best


@dataclass
class _Line:
    words: list[_Word]
    page: int

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def size(self) -> float:
        return statistics.median(w.size for w in self.words)

    @property
    def top(self) -> float:
        return min(w.top for w in self.words)

    @property
    def bottom(self) -> float:
        return max(w.bottom for w in self.words)

    @property
    def x0(self) -> float:
        return min(w.x0 for w in self.words)

    @property
    def x1(self) -> float:
        return max(w.x1 for w in self.words)

    @property
    def bold(self) -> bool:
        return sum(len(w.text) for w in self.words if _BOLD.search(w.font)) > 0.6 * max(
            1, sum(len(w.text) for w in self.words)
        )


@dataclass
class _ProtoBlock:
    lines: list[_Line]
    type: BlockType
    level: int | None = None
    flags: list[str] = field(default_factory=list)


def color_to_hex(value: object) -> str | None:
    """pdfminer colours arrive as gray (1 value), RGB (3) or CMYK (4), 0–1 floats."""
    if value is None:
        return None
    if isinstance(value, int | float):
        value = [value]
    if not isinstance(value, list | tuple) or not value:
        return None
    try:
        nums = [float(v) for v in value]
    except (TypeError, ValueError):
        return None
    if any(n > 1.0 for n in nums):  # some producers write 0–255
        nums = [n / 255.0 for n in nums]
    if len(nums) == 1:
        r = g = b = nums[0]
    elif len(nums) == 3:
        r, g, b = nums
    elif len(nums) == 4:
        c, m, y, k = nums
        r, g, b = (1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k)
    else:
        return None
    clamp = lambda v: max(0, min(255, round(v * 255)))  # noqa: E731
    return f"#{clamp(r):02x}{clamp(g):02x}{clamp(b):02x}"


def _normalize(text: str) -> str:
    return re.sub(r"\d+", "#", text.lower()).strip()


class PdfConverter:
    name = "pdfplumber"
    formats = frozenset({"pdf"})

    def convert(self, path: Path) -> Document:
        import pdfplumber  # heavy import, keep it local

        pages_lines: list[tuple[list[_Line], list[_Line], list[_Line], float, float]] = []
        meta: dict[str, str] = {}
        with pdfplumber.open(str(path)) as pdf:
            for key in ("Title", "Author", "Subject", "Keywords", "Producer", "Creator"):
                val = (pdf.metadata or {}).get(key)
                if isinstance(val, str) and val.strip():
                    meta[key.lower()] = val.strip()
            for pno, page in enumerate(pdf.pages, start=1):
                lines = self._lines(page, pno)
                header, body, footer = self._split_furniture(lines, page.height)
                pages_lines.append((header, body, footer, page.width, page.height))
            n_pages = len(pdf.pages)

        body_size = self._body_size([ln for _, body, _, _, _ in pages_lines for ln in body])
        heading_sizes = self._heading_sizes(
            [ln for _, body, _, _, _ in pages_lines for ln in body], body_size
        )
        repeated = self._repeated_furniture(pages_lines)

        blocks: list[Block] = []
        empty_pages = 0
        for header, body, footer, width, height in pages_lines:
            if not (header or body or footer):
                empty_pages += 1
            page_blocks: list[_ProtoBlock] = []
            page_blocks += self._furniture_blocks(header, "header", repeated)
            page_blocks += self._body_blocks(body, body_size, heading_sizes)
            page_blocks += self._furniture_blocks(footer, "footer", repeated)
            for pb in page_blocks:
                blocks.append(self._to_block(pb, len(blocks), width, height))

        if empty_pages:
            meta["empty_pages"] = str(empty_pages)
        title = meta.get("title") or next(
            (b.text for b in blocks if b.type is BlockType.heading and b.level == 1), None
        )
        return Document(
            source=str(path),
            format="pdf",
            converter=self.name,
            pages=n_pages,
            title=title,
            meta=meta,
            blocks=blocks,
        )

    # -- words -> lines -------------------------------------------------------

    def _lines(self, page, pno: int) -> list[_Line]:
        words = page.extract_words(
            keep_blank_chars=False,
            use_text_flow=True,
            extra_attrs=["size", "fontname", "non_stroking_color"],
        )
        shapes = _backgrounds(page)
        lines: list[_Line] = []
        for w in words:
            word = _Word(
                text=w["text"],
                x0=float(w["x0"]),
                x1=float(w["x1"]),
                top=float(w["top"]),
                bottom=float(w["bottom"]),
                size=float(w.get("size") or 0.0),
                font=str(w.get("fontname") or ""),
                color=color_to_hex(w.get("non_stroking_color")),
            )
            if shapes:
                word.background = _background_at(
                    shapes, (word.x0 + word.x1) / 2, (word.top + word.bottom) / 2
                )
            if lines and self._same_line(lines[-1], word):
                lines[-1].words.append(word)
            else:
                lines.append(_Line(words=[word], page=pno))
        for ln in lines:
            ln.words.sort(key=lambda w: w.x0)
        return lines

    @staticmethod
    def _same_line(line: _Line, word: _Word) -> bool:
        last = line.words[-1]
        tol = max(2.0, 0.5 * max(last.size, word.size, 1.0))
        return abs(word.top - last.top) <= tol

    # -- furniture ------------------------------------------------------------

    @staticmethod
    def _split_furniture(lines: list[_Line], height: float):
        header, body, footer = [], [], []
        for ln in lines:
            if ln.bottom <= FURNITURE_BAND * height:
                header.append(ln)
            elif ln.top >= (1 - FURNITURE_BAND) * height:
                footer.append(ln)
            else:
                body.append(ln)
        return header, body, footer

    @staticmethod
    def _repeated_furniture(pages_lines) -> set[str]:
        if len(pages_lines) < 2:
            return set()
        counts: Counter[str] = Counter()
        for header, _, footer, _, _ in pages_lines:
            seen = {_normalize(ln.text) for ln in header + footer}
            counts.update(seen)
        return {text for text, c in counts.items() if c >= 2 and text}

    @staticmethod
    def _furniture_blocks(lines: list[_Line], kind: str, repeated: set[str]) -> list[_ProtoBlock]:
        out: list[_ProtoBlock] = []
        for ln in lines:
            flags = [kind]
            if _normalize(ln.text) in repeated:
                flags.append("repeated")
            if _PAGE_NUMBER.match(ln.text.strip()):
                flags.append("page_number")
            out.append(_ProtoBlock(lines=[ln], type=BlockType.other, flags=flags))
        return out

    # -- body -----------------------------------------------------------------

    @staticmethod
    def _body_size(lines: list[_Line]) -> float:
        weights: Counter[float] = Counter()
        for ln in lines:
            for w in ln.words:
                weights[round(w.size * 2) / 2] += len(w.text)
        return weights.most_common(1)[0][0] if weights else 10.0

    @staticmethod
    def _heading_sizes(lines: list[_Line], body: float) -> list[float]:
        """Distinct sizes clearly above the body size, largest first -> heading levels."""
        sizes = {
            round(ln.size * 2) / 2 for ln in lines if ln.size >= body * 1.15 and len(ln.text) <= 120
        }
        return sorted(sizes, reverse=True)[:4]

    def _body_blocks(
        self, lines: list[_Line], body_size: float, heading_sizes: list[float]
    ) -> list[_ProtoBlock]:
        blocks: list[_ProtoBlock] = []
        for ln in lines:
            text = ln.text.strip()
            if not text:
                continue
            size = round(ln.size * 2) / 2
            level = None
            btype = BlockType.paragraph
            bulleted = bool(ln.words and _BULLET.match(ln.words[0].text))
            if bulleted:
                btype = BlockType.list_item
            elif size in heading_sizes and len(text) <= 120:
                level = heading_sizes.index(size) + 1
                btype = BlockType.heading
            elif ln.bold and len(text.split()) <= 12 and not text.endswith((".", ",", ";")):
                level = len(heading_sizes) + 1
                btype = BlockType.heading
            elif (
                ln.words
                and _BULLET.match(ln.words[0].text + " ") is None
                and re.match(r"^(\d{1,3}[.)]|[•·▪◦‣●○■□➢➤►\-–*])\S", ln.words[0].text)
            ):
                btype = BlockType.list_item

            prev = blocks[-1] if blocks else None
            if prev is not None and self._continues(prev, ln, btype, body_size):
                prev.lines.append(ln)
                continue
            blocks.append(_ProtoBlock(lines=[ln], type=btype, level=level))
        return blocks

    @staticmethod
    def _continues(prev: _ProtoBlock, ln: _Line, btype: BlockType, body_size: float) -> bool:
        last = prev.lines[-1]
        if last.page != ln.page:
            return False
        if prev.type is BlockType.heading or btype is BlockType.heading:
            return False
        gap = ln.top - last.bottom
        line_h = max(last.bottom - last.top, ln.bottom - ln.top, 1.0)
        if gap > 0.9 * line_h:
            return False
        if abs(ln.size - last.size) > 1.5:
            return False
        if btype is BlockType.list_item:
            return False  # each item starts its own block
        if prev.type is BlockType.list_item:
            # a wrapped item continues if the line is indented past the bullet
            return ln.x0 > prev.lines[0].x0 + 2.0
        return True

    # -- proto -> model -------------------------------------------------------

    @staticmethod
    def _to_block(pb: _ProtoBlock, index: int, width: float, height: float) -> Block:
        words = [w for ln in pb.lines for w in ln.words]
        runs: list[Run] = []
        for w in words:
            key = (round(w.size, 1), w.font, w.color, w.background)
            if (
                runs
                and runs[-1].style.font_size is not None
                and key
                == (
                    round(runs[-1].style.font_size, 1),
                    runs[-1].style.font_name,
                    runs[-1].style.color,
                    runs[-1].style.background,
                )
            ):
                prev = runs[-1]
                x0, top, x1, bottom = prev.style.bbox or (w.x0, w.top, w.x1, w.bottom)
                prev.text += " " + w.text
                prev.style.bbox = (
                    min(x0, w.x0),
                    min(top, w.top),
                    max(x1, w.x1),
                    max(bottom, w.bottom),
                )
            else:
                runs.append(
                    Run(
                        text=w.text,
                        style=Style(
                            font_size=w.size,
                            font_name=w.font or None,
                            color=w.color,
                            bbox=(w.x0, w.top, w.x1, w.bottom),
                            background=w.background,
                        ),
                    )
                )
        sizes: Counter[float] = Counter()
        colors: Counter[str | None] = Counter()
        fonts: Counter[str] = Counter()
        for w in words:
            sizes[round(w.size, 1)] += len(w.text)
            colors[w.color] += len(w.text)
            fonts[w.font] += len(w.text)
        bbox = (
            min(w.x0 for w in words),
            min(w.top for w in words),
            max(w.x1 for w in words),
            max(w.bottom for w in words),
        )
        flags = list(pb.flags)
        for run in runs:
            rb = run.style.bbox
            if rb and (rb[2] <= 0 or rb[0] >= width or rb[3] <= 0 or rb[1] >= height):
                run.flags.append("off_page")
        if bbox[2] <= 0 or bbox[0] >= width or bbox[3] <= 0 or bbox[1] >= height:
            flags.append("off_page")
        text = " ".join(ln.text for ln in pb.lines)
        return Block(
            type=pb.type,
            text=text,
            level=pb.level,
            style=Style(
                font_size=sizes.most_common(1)[0][0] if sizes else None,
                font_name=fonts.most_common(1)[0][0] or None if fonts else None,
                color=colors.most_common(1)[0][0] if colors else None,
                bbox=bbox,
            ),
            runs=runs,
            flags=flags,
            anchor=Anchor(page=pb.lines[0].page, block=index),
        )
