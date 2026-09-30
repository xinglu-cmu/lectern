"""`summarize`: one paragraph on what the document is and asks for, plus a type guess.

Built from an outline (section path + the first lines of every segment) rather
than the full text: cheaper, and enough to say what a document *is*. Segments
zoned `hidden` are left out — they never reach a prompt. Skipped entirely in
`--no-llm` mode.
"""

from __future__ import annotations

from lectern.llm import LLM, TRUST_BOUNDARY
from lectern.models import Document, Overview, Segment, Zone

OUTLINE_BUDGET_TOKENS = 8000
PER_SEGMENT_CHARS = 320

SYSTEM = f"""You write a one-paragraph overview of a document for someone deciding what to do \
with it. {TRUST_BOUNDARY}

Say what kind of document it is, what it is about, and — if it asks the reader to do \
anything — what the actual task is. Plain language, 3–5 sentences, no bullet points. If the \
outline shows text addressed to an AI system or rules about AI use, mention that in one clause. \
Pick doc_type from the list; use "other" when unsure."""


def summarize(doc: Document, segments: list[Segment], llm: LLM) -> Overview | None:
    return llm.parse(
        system=SYSTEM, user=render_outline(doc, segments), schema=Overview, max_tokens=800
    )


def render_outline(doc: Document, segments: list[Segment]) -> str:
    lines = [
        f"Filename: {doc.source.rsplit('/', 1)[-1]}",
        f"Format: {doc.format}" + (f", {doc.pages} pages" if doc.pages else ""),
        f"Title: {doc.title}" if doc.title else "Title: (none)",
        "",
        "<document>",
    ]
    used = 0
    truncated = False
    for seg in segments:
        if (
            seg.zone is Zone.hidden
            or seg.zone is Zone.structure
            and "heading_only" not in seg.flags
        ):
            continue
        snippet = " ".join(seg.text.split())
        if len(snippet) > PER_SEGMENT_CHARS:
            snippet = snippet[:PER_SEGMENT_CHARS].rstrip() + " […]"
        section = " > ".join(seg.heading_path)
        entry = f"[{seg.id}] ({section}) {snippet}" if section else f"[{seg.id}] {snippet}"
        cost = len(entry) // 4 + 1
        if used + cost > OUTLINE_BUDGET_TOKENS:
            truncated = True
            break
        lines.append(entry)
        used += cost
    if truncated:
        lines.append("[… outline truncated; later sections omitted …]")
    lines.append("</document>")
    return "\n".join(lines)
