"""Block-level detectors H1–H6: hidden text, found before segmentation.

They work on the loaded document's blocks and runs, where the style evidence
lives, and they run before any segment is formed and long before any LLM call:

- H1 invisible colour — text drawn near-white on a (presumed) white page
- H2 tiny font — runs at ≤ 2.5pt or below a third of the body size
- H3 off-canvas — runs or blocks positioned outside the page
- H4 format-level hiding — what the HTML/DOCX converters observed:
  `display:none`, zero font size, text coloured like its background, the
  hidden attribute, HTML comments, Word's `vanish` flag
- H5 metadata payloads — directives or oversized text in document properties
- H6 encoding anomalies — zero-width / bidi / private-use characters, smuggled
  tag-character payloads, mixed-script look-alike words

`screen_blocks` applies them and rewrites the block list: a block whose runs are
only partly hidden is split so that the hidden part becomes its own block,
flagged `hidden:<reason>`. The segmenter then keeps hidden blocks in their own
segments, zoning labels those `hidden`, and nothing downstream ever puts them in
a prompt or a clean copy. Every hidden block has a finding the user can see:
detect → disclose → respect.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol

from lectern.models import Anchor, Block, Document, Finding, FindingStatus, Run, Severity, Style
from lectern.screen import encoding

CONTRAST_MIN = 0.08  # luminance difference below which text vanishes into its background
TINY_PT = 2.5  # unreadable at any zoom
TINY_RELATIVE_PT = 4.0  # below this *and* far below the body size: hidden, not a footnote
TINY_RATIO = 0.3
EXCERPT = 240


@dataclass
class Hit:
    block: int
    detector: str
    kind: str
    note: str
    runs: list[int] | None = None  # None = the whole block
    payload: str | None = None  # text to surface as a new hidden block (H6 tags)
    disclose_only: bool = False  # finding without quarantine (H6 counts, mixed scripts)
    severity: Severity = Severity.warning
    extra: dict = field(default_factory=dict)


class BlockDetector(Protocol):
    name: str

    def run(self, doc: Document) -> list[Hit]: ...


def default_block_detectors() -> list[BlockDetector]:
    return [InvisibleColor(), TinyFont(), OffCanvas(), FormatHiding(), EncodingAnomalies()]


# --------------------------------------------------------------------- helpers


def luminance(color: str | None) -> float | None:
    if not color or len(color) != 7:
        return None
    r, g, b = (int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def body_font_size(doc: Document) -> float | None:
    """Dominant font size, or None when most text carries no size (then only the absolute
    tiny-font threshold applies)."""
    weights: Counter[float] = Counter()
    total = 0
    for b in doc.blocks:
        total += len(b.text)
        if b.style.font_size:
            weights[round(b.style.font_size * 2) / 2] += len(b.text)
    if not weights or sum(weights.values()) < 0.3 * max(1, total):
        return None
    return weights.most_common(1)[0][0]


def _excerpt(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= EXCERPT else text[: EXCERPT - 1].rstrip() + "…"


# ------------------------------------------------------------------- detectors


class InvisibleColor:
    """Text whose colour matches what is drawn behind it.

    The background is the nearest filled shape under the word (recorded by the PDF
    converter), the page itself (white) when there is none, or an image — in which
    case we cannot know and do not flag. So white on a red banner is fine, white on
    the bare page is hidden, and black on a black box is hidden too."""

    name = "H1"

    def run(self, doc: Document) -> list[Hit]:
        if doc.format not in ("pdf", "docx"):
            return []
        hits = []
        for b in doc.blocks:
            idx = [i for i, r in enumerate(b.runs) if self._invisible(r.style)]
            if idx:
                st = b.runs[idx[0]].style
                hits.append(
                    Hit(
                        b.anchor.block,
                        self.name,
                        "invisible_color",
                        f"text colour {st.color} on background "
                        f"{st.background or 'the page (white)'}",
                        runs=idx,
                    )
                )
        return hits

    @staticmethod
    def _invisible(style: Style) -> bool:
        fg = luminance(style.color)
        if fg is None:
            return False
        if style.background == "image":
            return False
        bg = luminance(style.background) if style.background else 1.0
        if bg is None:
            return False
        return abs(fg - bg) < CONTRAST_MIN


class TinyFont:
    name = "H2"

    def run(self, doc: Document) -> list[Hit]:
        body = body_font_size(doc)
        hits = []
        for b in doc.blocks:
            idx = [
                i
                for i, r in enumerate(b.runs)
                if r.style.font_size is not None
                and (
                    r.style.font_size <= TINY_PT
                    or (
                        body
                        and r.style.font_size < TINY_RELATIVE_PT
                        and r.style.font_size < TINY_RATIO * body
                    )
                )
            ]
            if idx:
                size = b.runs[idx[0]].style.font_size
                hits.append(
                    Hit(
                        b.anchor.block,
                        self.name,
                        "tiny_font",
                        f"font size {size}pt (body {body}pt)",
                        runs=idx,
                    )
                )
        return hits


class OffCanvas:
    name = "H3"

    def run(self, doc: Document) -> list[Hit]:
        hits = []
        for b in doc.blocks:
            if "off_page" in b.flags:
                hits.append(
                    Hit(b.anchor.block, self.name, "off_page", "block positioned outside the page")
                )
                continue
            idx = [i for i, r in enumerate(b.runs) if "off_page" in r.flags]
            if idx:
                hits.append(
                    Hit(
                        b.anchor.block,
                        self.name,
                        "off_page",
                        "text positioned outside the page",
                        runs=idx,
                    )
                )
        return hits


class FormatHiding:
    """What the HTML and DOCX converters already observed, surfaced as findings."""

    name = "H4"

    def run(self, doc: Document) -> list[Hit]:
        hits = []
        for b in doc.blocks:
            reasons = [f.split(":", 1)[1] for f in b.flags if f.startswith("hidden:")]
            if reasons:
                kind = "html_comment" if reasons == ["comment"] else f"{doc.format}_hidden"
                hits.append(Hit(b.anchor.block, self.name, kind, "hidden by " + ", ".join(reasons)))
                continue
            idx = [i for i, r in enumerate(b.runs) if any(f.startswith("hidden:") for f in r.flags)]
            if idx:
                hits.append(
                    Hit(
                        b.anchor.block,
                        self.name,
                        f"{doc.format}_hidden",
                        "runs marked hidden (vanish)",
                        runs=idx,
                    )
                )
        return hits


class EncodingAnomalies:
    name = "H6"

    def run(self, doc: Document) -> list[Hit]:
        hits = []
        for b in doc.blocks:
            payload = encoding.decode_tags(b.text)
            if payload.strip():
                hits.append(
                    Hit(
                        b.anchor.block,
                        self.name,
                        "tag_characters",
                        "ASCII text smuggled in invisible Unicode tag characters",
                        payload=payload.strip(),
                    )
                )
            counts = {k: v for k, v in encoding.count_invisible(b.text).items() if k != "tag"}
            if counts:
                desc = ", ".join(f"{v} {k.replace('_', '-')}" for k, v in counts.items())
                first = next(
                    i
                    for i, ch in enumerate(b.text)
                    if ch in encoding.ZERO_WIDTH or ch in encoding.BIDI or encoding.is_pua(ch)
                )
                window = b.text[max(0, first - 60) : first + 180]
                hits.append(
                    Hit(
                        b.anchor.block,
                        self.name,
                        "invisible_characters",
                        f"{desc} character(s); removed in clean output",
                        disclose_only=True,
                        extra={**counts, "excerpt": window},
                    )
                )
            words = encoding.mixed_script_words(b.text)
            if words:
                hits.append(
                    Hit(
                        b.anchor.block,
                        self.name,
                        "mixed_script",
                        "words mixing Latin with look-alike Cyrillic/Greek letters: "
                        + ", ".join(words),
                        disclose_only=True,
                    )
                )
        return hits


# ------------------------------------------------------------------- metadata


def screen_metadata(doc: Document) -> list[Finding]:
    """H5: document properties are text a reader never sees but a model may be given."""
    from lectern.screen.patterns import DIRECTIVE_PATTERNS

    findings = []
    for key, value in doc.meta.items():
        if key in ("empty_pages",):
            continue
        directive = any(p.search(value) for p in DIRECTIVE_PATTERNS)
        if directive or len(value) > 300:
            findings.append(
                Finding(
                    detector="H5",
                    kind="metadata_payload",
                    severity=Severity.critical if directive else Severity.warning,
                    excerpt=_excerpt(value),
                    status=FindingStatus.quarantined,
                    note=f"document property '{key}' "
                    + (
                        "contains an AI-directed instruction"
                        if directive
                        else f"is unusually long ({len(value)} chars)"
                    ),
                )
            )
    return findings


# ----------------------------------------------------------------- the rewrite


def screen_blocks(
    doc: Document, detectors: list[BlockDetector] | None = None
) -> tuple[Document, list[Finding]]:
    """Apply the block detectors; return the rewritten document and its findings."""
    hits: dict[int, list[Hit]] = {}
    for det in detectors if detectors is not None else default_block_detectors():
        for h in det.run(doc):
            hits.setdefault(h.block, []).append(h)

    new_blocks: list[Block] = []
    findings: list[Finding] = list(screen_metadata(doc))

    def emit(block: Block) -> Block:
        block = block.model_copy(deep=True)
        block.anchor = Anchor(page=block.anchor.page, block=len(new_blocks))
        new_blocks.append(block)
        return block

    def finding(h: Hit, block: Block, text: str, quarantine: bool) -> None:
        findings.append(
            Finding(
                detector=h.detector,
                kind=h.kind,
                severity=h.severity,
                page=block.anchor.page,
                block=block.anchor.block,
                excerpt=_excerpt(h.extra.get("excerpt") or text),
                status=FindingStatus.quarantined if quarantine else FindingStatus.open,
                note=h.note,
            )
        )

    for block in doc.blocks:
        block_hits = hits.get(block.anchor.block, [])
        whole = [
            h for h in block_hits if h.runs is None and h.payload is None and not h.disclose_only
        ]
        partial = [h for h in block_hits if h.runs is not None and not h.disclose_only]
        payloads = [h for h in block_hits if h.payload]
        disclose = [h for h in block_hits if h.disclose_only]

        if whole or (
            partial
            and block.runs
            and set().union(*(set(h.runs) for h in partial)) >= set(range(len(block.runs)))
        ):
            lead = whole[0] if whole else partial[0]
            hidden = block.model_copy(deep=True)
            if not hidden.hidden:
                hidden.flags = hidden.flags + [f"hidden:{lead.kind}"]
            placed = emit(hidden)
            for h in whole + partial:  # every detector that fired gets its finding
                finding(h, placed, placed.text, quarantine=True)
        elif partial:
            hidden_idx = set().union(*(set(h.runs) for h in partial))
            groups: list[tuple[bool, list[Run]]] = []
            for i, run in enumerate(block.runs):
                is_hidden = i in hidden_idx
                if groups and groups[-1][0] == is_hidden:
                    groups[-1][1].append(run)
                else:
                    groups.append((is_hidden, [run]))
            for is_hidden, runs in groups:
                piece = block.model_copy(deep=True)
                piece.runs = runs
                piece.text = " ".join(r.text for r in runs).strip()
                piece.style = max(runs, key=lambda r: len(r.text)).style.model_copy()
                if is_hidden:
                    kinds = sorted({h.kind for h in partial})
                    piece.flags = [f for f in piece.flags if not f.startswith("hidden:")] + [
                        f"hidden:{k}" for k in kinds
                    ]
                    placed = emit(piece)
                    for h in partial:
                        if set(h.runs) & {block.runs.index(r) for r in runs}:
                            finding(h, placed, placed.text, quarantine=True)
                else:
                    piece.flags = [f for f in piece.flags if not f.startswith("hidden:")]
                    emit(piece)
        else:
            placed = emit(block)
            for h in disclose:
                finding(h, placed, block.text, quarantine=False)
        for h in payloads:
            extra = Block(
                type=block.type,
                text=h.payload or "",
                flags=[f"hidden:{h.kind}"],
                style=Style(),
                runs=[],
                anchor=Anchor(page=block.anchor.page, block=0),
            )
            placed = emit(extra)
            finding(h, placed, placed.text, quarantine=True)
        if not whole and not partial:
            pass

    return doc.model_copy(update={"blocks": new_blocks}), findings
