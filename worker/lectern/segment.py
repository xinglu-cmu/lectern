"""`segment`: blocks -> classification units (DESIGN §4).

A segment is the unit that gets one zone label. Units are heading-bounded
(a new heading starts a new segment), paragraph-grouped (consecutive paragraphs
and list items are pooled), and sized ~100–400 estimated tokens: big enough for
a classifier to see the function of the text, small enough that "keep the task,
drop the rest" doesn't drop the task along with its neighbour.

Every segment keeps a `heading_path` (the section breadcrumb at that point), an
anchor (pages and block indices) and `flags` summarizing what it is made of, so
zoning can see "this is page furniture" or "this is mostly code" without
re-reading the blocks.

Token estimates are chars / 4 — deliberately crude. They are used for size
bounds, zone shares and LLM batch budgets, none of which need to be exact.
"""

from __future__ import annotations

import math
import re

from lectern.models import Block, BlockType, Document, Segment, SegmentAnchor

MAX_TOKENS = 400
MIN_TOKENS = 100
FURNITURE_FLAGS = {"header", "footer", "repeated", "page_number"}

_PDF_BULLET = re.compile(r"^[•·▪◦‣●○■□➢➤►✓✗Ø¢§–—]\s*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def est_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def render_block(block: Block) -> str:
    """How a block reads inside a segment (and, later, inside the clean Markdown)."""
    if block.type is BlockType.heading:
        return "#" * min(6, block.level or 1) + " " + block.text
    if block.type is BlockType.list_item:
        text = block.text
        if re.match(r"^\s*([-*+]|\d+[.)])\s", text):
            return text  # already Markdown
        # PDF bullets come from symbol fonts (●, ¢, §, …): normalize to a Markdown dash
        return "- " + _PDF_BULLET.sub("", text, count=1)
    return block.text


def segment(doc: Document) -> list[Segment]:
    builder = _Builder()
    for block in doc.blocks:
        if set(block.flags) & FURNITURE_FLAGS:
            builder.add_furniture(block)
        elif block.type is BlockType.heading:
            builder.add_heading(block)
        else:
            builder.add_content(block)
    return builder.finish()


class _Builder:
    def __init__(self) -> None:
        self.done: list[Segment] = []
        self.current: list[Block] = []
        self.current_path: list[str] = []
        self.stack: list[tuple[int, str]] = []  # (level, heading text)
        self.furniture: list[Block] = []

    # -- input ----------------------------------------------------------------

    def add_furniture(self, block: Block) -> None:
        self.furniture.append(block)

    def add_heading(self, block: Block) -> None:
        self._flush_furniture()
        if any(b.type is not BlockType.heading for b in self.current):
            self._flush()
        level = block.level or 1
        while self.stack and self.stack[-1][0] >= level:
            self.stack.pop()
        self.stack.append((level, block.text))
        if not self.current:
            self.current_path = [t for _, t in self.stack]
        self.current.append(block)

    def add_content(self, block: Block) -> None:
        self._flush_furniture()
        pieces = self._split_if_huge(block)
        for piece in pieces:
            have = sum(est_tokens(render_block(b)) for b in self.current)
            need = est_tokens(render_block(piece))
            if self.current and have + need > MAX_TOKENS and have >= MIN_TOKENS:
                self._flush()
            if not self.current:
                self.current_path = [t for _, t in self.stack]
            self.current.append(piece)

    def finish(self) -> list[Segment]:
        self._flush()
        self._flush_furniture()
        self._merge_small_tails()
        self.done.sort(key=lambda s: s.anchor.block_start)
        for i, seg in enumerate(self.done, start=1):
            seg.id = f"s{i}"
            seg.seq = i
        return self.done

    # -- internals ------------------------------------------------------------

    def _flush(self) -> None:
        if self.current:
            self.done.append(self._make(self.current, self.current_path))
            self.current = []

    def _flush_furniture(self) -> None:
        if self.furniture:
            self.done.append(self._make(self.furniture, [t for _, t in self.stack]))
            self.furniture = []

    def _make(self, blocks: list[Block], path: list[str]) -> Segment:
        text = "\n\n".join(render_block(b) for b in blocks)
        pages = [b.anchor.page for b in blocks if b.anchor.page is not None]
        flags = sorted({f for b in blocks for f in b.flags})
        chars = max(1, sum(len(b.text) for b in blocks))
        code_chars = sum(len(b.text) for b in blocks if b.type in (BlockType.code, BlockType.table))
        list_chars = sum(len(b.text) for b in blocks if b.type is BlockType.list_item)
        if all(b.type is BlockType.heading for b in blocks):
            flags.append("heading_only")
        if code_chars / chars >= 0.5:
            flags.append("code_heavy")
        if list_chars / chars >= 0.6:
            flags.append("list_heavy")
        return Segment(
            id="",
            seq=0,
            heading_path=list(path),
            text=text,
            tokens_est=est_tokens(text),
            flags=flags,
            anchor=SegmentAnchor(
                page_start=min(pages) if pages else None,
                page_end=max(pages) if pages else None,
                block_start=blocks[0].anchor.block,
                block_end=blocks[-1].anchor.block,
            ),
        )

    @staticmethod
    def _split_if_huge(block: Block) -> list[Block]:
        """A single paragraph far above the ceiling is split at sentence ends."""
        if (
            block.type in (BlockType.code, BlockType.table)
            or est_tokens(block.text) <= MAX_TOKENS * 1.5
        ):
            return [block]
        sentences = _SENTENCE_END.split(block.text)
        pieces: list[Block] = []
        buf: list[str] = []
        for s in sentences:
            if buf and est_tokens(" ".join(buf)) + est_tokens(s) > MAX_TOKENS:
                pieces.append(block.model_copy(update={"text": " ".join(buf)}))
                buf = []
            buf.append(s)
        if buf:
            pieces.append(block.model_copy(update={"text": " ".join(buf)}))
        return pieces

    def _merge_small_tails(self) -> None:
        """A tiny trailing segment under the same heading joins its predecessor."""
        merged: list[Segment] = []
        for seg in self.done:
            prev = merged[-1] if merged else None
            if (
                prev is not None
                and seg.tokens_est < MIN_TOKENS // 2
                and seg.heading_path == prev.heading_path
                and not (set(seg.flags) | set(prev.flags)) & FURNITURE_FLAGS
                and "heading_only" not in prev.flags
                and prev.tokens_est + seg.tokens_est <= MAX_TOKENS * 1.25
                and seg.anchor.block_start == prev.anchor.block_end + 1
            ):
                prev.text = prev.text + "\n\n" + seg.text
                prev.tokens_est = est_tokens(prev.text)
                prev.anchor.block_end = seg.anchor.block_end
                prev.anchor.page_end = seg.anchor.page_end or prev.anchor.page_end
                prev.flags = sorted(set(prev.flags) | set(seg.flags))
                continue
            merged.append(seg)
        self.done = merged
