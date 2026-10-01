"""The typed result model shared by every stage, the CLI and the worker.

Three layers, each built from the one before:

- `Document` — what `load` produces: a flat list of `Block`s (heading, paragraph,
  list item, code, table) with the style hints and anchors the converter could
  recover. This is the normalized internal document; converters differ, this
  does not.
- `Segment` — what `segment` produces and `zone` labels: heading-bounded,
  paragraph-grouped units of ~100–400 tokens, each carrying a zone, a
  confidence and the method that assigned it.
- `Analysis` — the whole result: overview, segments, findings, zone shares,
  LLM usage. `lectern scan --json` prints exactly this.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- load


class BlockType(StrEnum):
    heading = "heading"
    paragraph = "paragraph"
    list_item = "list_item"
    code = "code"
    table = "table"
    other = "other"


class Style(BaseModel):
    """Style hints a converter recovered. Anything missing is simply None.

    These are the raw material for the hidden-text detectors (H1 colour, H2 size,
    H3 position) — they must survive conversion or those detectors have nothing
    to look at. Converters that read Markdown-ish output (MarkItDown) can't recover
    them; the PDF converter can.
    """

    font_size: float | None = None
    font_name: str | None = None
    color: str | None = Field(default=None, description="#rrggbb, as drawn on the page")
    bbox: tuple[float, float, float, float] | None = Field(
        default=None, description="x0, top, x1, bottom in PDF points"
    )
    background: str | None = Field(
        default=None,
        description="what is drawn behind the text: #rrggbb of the nearest filled shape, "
        "'image' when a picture is behind it, None when nothing is (the page itself)",
    )


class Run(BaseModel):
    """A stretch of text drawn with one style. Blocks keep their runs so a detector
    can find a single white or 1pt word inside an otherwise normal paragraph."""

    text: str
    style: Style = Field(default_factory=Style)
    flags: list[str] = Field(
        default_factory=list, description="converter observations, e.g. off_page"
    )


class Anchor(BaseModel):
    """Where a block came from: page number (1-based, PDF only) and its index in
    the document's block list. Enough to point a reader back to the source."""

    page: int | None = None
    block: int


class Block(BaseModel):
    type: BlockType
    text: str
    level: int | None = Field(default=None, description="heading level, 1 = largest")
    style: Style = Field(default_factory=Style, description="dominant style of the block")
    runs: list[Run] = Field(default_factory=list)
    flags: list[str] = Field(
        default_factory=list,
        description="converter observations (header, footer, repeated, page_number, off_page) and "
        "hiding evidence (hidden:<reason>, set by converters for format-level hiding and by the "
        "block detectors for style-level hiding)",
    )
    anchor: Anchor

    @property
    def hidden(self) -> bool:
        return any(f.startswith("hidden:") for f in self.flags)


class Document(BaseModel):
    source: str
    format: str = Field(description="pdf, docx, html, md, txt, …")
    converter: str
    pages: int | None = None
    title: str | None = None
    meta: dict[str, str] = Field(default_factory=dict)
    blocks: list[Block]

    @property
    def text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks)


# ------------------------------------------------------------------------ segment


class Zone(StrEnum):
    """The functional-role taxonomy (DESIGN §5). `hidden` is detector-derived and
    never assigned by an LLM — see `LLMZone` in `lectern.llm`."""

    task = "task"
    background = "background"
    structure = "structure"
    example = "example"
    ai_directive = "ai_directive"
    ai_policy = "ai_policy"
    hidden = "hidden"
    unknown = "unknown"


class Method(StrEnum):
    heuristic = "heuristic"
    llm = "llm"


class SegmentAnchor(BaseModel):
    page_start: int | None = None
    page_end: int | None = None
    block_start: int
    block_end: int = Field(description="inclusive")


class Segment(BaseModel):
    id: str = Field(description="s1, s2, … — stable within one analysis")
    seq: int
    heading_path: list[str] = Field(default_factory=list)
    text: str
    tokens_est: int = Field(description="rough token count (chars / 4), for shares and budgets")
    zone: Zone = Zone.unknown
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    method: Method = Method.heuristic
    signals: list[str] = Field(
        default_factory=list, description="why the heuristics chose this zone"
    )
    flags: list[str] = Field(
        default_factory=list,
        description="what the segment is made of: header, footer, repeated, heading_only, "
        "code_heavy, list_heavy, …",
    )
    anchor: SegmentAnchor


# ------------------------------------------------------------------------- screen


class Severity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


class FindingStatus(StrEnum):
    open = "open"
    quarantined = "quarantined"
    dismissed = "dismissed"


class Finding(BaseModel):
    detector: str = Field(description="D1, P1, H1 … the detector's short name")
    kind: str = Field(description="what was found: ai_directive, ai_policy, invisible_color …")
    severity: Severity
    segment_id: str | None = None
    page: int | None = None
    excerpt: str
    span: dict[str, int] = Field(
        default_factory=dict, description="character offsets inside the segment text"
    )
    status: FindingStatus = FindingStatus.open
    note: str | None = None
    block: int | None = Field(default=None, description="block index in the loaded document")


# ---------------------------------------------------------------------- summarize


class DocType(StrEnum):
    assignment = "assignment"
    syllabus = "syllabus"
    lecture_notes = "lecture_notes"
    exam = "exam"
    paper = "paper"
    report = "report"
    specification = "specification"
    rfp = "rfp"
    contract = "contract"
    article = "article"
    email = "email"
    manual = "manual"
    other = "other"


class Overview(BaseModel):
    overview: str = Field(description="one paragraph: what the document is and asks for")
    doc_type: DocType


# ------------------------------------------------------------------------- result


class LLMUsage(BaseModel):
    model: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    failures: int = Field(default=0, description="calls that returned nothing usable")


class Analysis(BaseModel):
    lectern_version: str
    taxonomy_v: str
    source: str
    format: str
    converter: str
    pages: int | None
    title: str | None
    mode: str = Field(description="'llm' or 'heuristic-only'")
    overview: Overview | None
    segments: list[Segment]
    findings: list[Finding]
    zone_shares: dict[str, float] = Field(
        description="share of estimated tokens per zone, 0–1, zones with content only"
    )
    llm: LLMUsage | None
    warnings: list[str] = Field(default_factory=list)

    def segment(self, segment_id: str) -> Segment:
        return next(s for s in self.segments if s.id == segment_id)
