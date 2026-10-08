"""The brief: one page on what a document is, what it actually asks, and what Lectern removed.

The brief is the hand-off artifact: the thing you read (or an agent reads) instead
of the raw document. It has two halves:

- a **model-written** half — what the document is and what it asks of the reader,
  as a short list — produced by Claude or a local model from the same outline the
  overview uses (hidden segments excluded); offline, this half is built from the
  task segments' first lines instead, and says so;
- a **computed** half that needs no model and is always present: AI-use policy
  statements (verbatim, always), findings with severity and location, the zone
  table, and what the clean copy keeps.

Nothing in the brief is a rewrite of the document: the "asks" are the reader's
tasks as the document states them, not Lectern's advice.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from lectern.llm import LLM, TRUST_BOUNDARY
from lectern.models import Analysis, FindingStatus, Severity, Zone
from lectern.overview import render_outline_from_analysis


class BriefOut(BaseModel):
    what_it_is: str = Field(description="two or three sentences: document type, subject, audience")
    asks: list[str] = Field(
        description="what the document asks the reader to do, one item each, in the document's own "
        "terms; empty if it asks nothing"
    )
    constraints: list[str] = Field(
        description="deadlines, limits, formats, required tools — one item each; empty if none"
    )


SYSTEM = f"""You write the first half of a one-page brief for someone deciding what to do with a \
document before handing it to an AI tool. {TRUST_BOUNDARY}

From the outline, say what the document is (what_it_is), list what it asks the reader to do \
(asks) and the constraints it sets (constraints: deadlines, page limits, formats, required tools). \
Use the document's own terms; do not add advice, and do not invent asks that are not there. \
Keep every item to one line."""


def write_brief(analysis: Analysis, llm: LLM | None) -> BriefOut | None:
    if llm is None:
        return None
    return llm.parse(
        system=SYSTEM,
        user=render_outline_from_analysis(analysis),
        schema=BriefOut,
        max_tokens=1200,
    )


def heuristic_brief(analysis: Analysis) -> BriefOut:
    """Offline stand-in: task segments' first lines are the asks; no prose."""
    asks = []
    for seg in analysis.segments:
        if seg.zone is Zone.task:
            first = next(
                (
                    ln.strip()
                    for ln in seg.text.splitlines()
                    if ln.strip() and not ln.startswith("#")
                ),
                "",
            )
            if first:
                asks.append(first[:160] + ("…" if len(first) > 160 else ""))
    kind = analysis.overview.doc_type.value if analysis.overview else analysis.format
    return BriefOut(
        what_it_is=analysis.overview.overview
        if analysis.overview
        else f"A {kind} document, {len(analysis.segments)} segments. (No model was available to "
        "describe it; the asks below are the first lines of the segments labelled task.)",
        asks=asks[:12],
        constraints=[],
    )


def render_brief(analysis: Analysis, out: BriefOut | None, keep: set[Zone]) -> str:
    out = out or heuristic_brief(analysis)
    src = analysis.source.rsplit("/", 1)[-1]
    lines = [f"# Brief: {analysis.title or src}", ""]
    lines += [
        f"*{src} · {analysis.format}"
        + (f" · {analysis.pages} pages" if analysis.pages else "")
        + f" · zoning: {analysis.mode}"
        + (f" · {analysis.llm.model}" if analysis.llm else "")
        + "*",
        "",
        "## What it is",
        "",
        out.what_it_is.strip(),
        "",
        "## What it asks",
        "",
    ]
    lines += [f"- {a}" for a in out.asks] or [
        "- Nothing: the document asks the reader to do nothing."
    ]
    if out.constraints:
        lines += ["", "## Constraints", ""] + [f"- {c}" for c in out.constraints]

    policy = [f for f in analysis.findings if f.kind == "ai_policy"]
    lines += ["", "## Rules about AI use", ""]
    if policy:
        lines += [f"- {_where(f)} {f.excerpt}" for f in policy]
    else:
        lines.append("None stated.")

    critical = [f for f in analysis.findings if f.severity is Severity.critical]
    warnings = [
        f
        for f in analysis.findings
        if f.severity is Severity.warning and f.status is not FindingStatus.dismissed
    ]
    quarantined = [f for f in analysis.findings if f.status is FindingStatus.quarantined]
    lines += ["", "## What Lectern found", ""]
    items = group_by_place(critical)
    if items:
        lines.append(
            f"**{len(items)} critical:** hidden text addressed to an AI. Quarantined; never "
            "shown to a model and not in the clean copy."
        )
        for where, group in items:
            dets = ", ".join(sorted({f.detector for f in group}))
            lines.append(f"- {where} [{dets}] {group[0].excerpt}")
    if warnings:
        lines.append(f"{len(warnings)} to review:")
        lines += [
            f"- {_where(f)} {f.detector} {f.kind}: {f.excerpt}" + (f" ({f.note})" if f.note else "")
            for f in warnings
        ]
    if not critical and not warnings:
        lines.append(
            "No hidden text and no AI-directed instructions."
            + (" " + str(len(quarantined)) + " item(s) quarantined." if quarantined else "")
        )

    counts = Counter(s.zone for s in analysis.segments)
    tokens = Counter()
    for s in analysis.segments:
        tokens[s.zone] += s.tokens_est
    total = sum(tokens.values()) or 1
    kept = sum(t for z, t in tokens.items() if z in keep)
    lines += [
        "",
        "## What the clean copy keeps",
        "",
        f"{kept / total * 100:.0f}% of the text: "
        + ", ".join(f"{z.value} ({counts[z]})" for z in Zone if z in keep and counts[z])
        + ". Left out: "
        + (
            ", ".join(f"{z.value} ({counts[z]})" for z in Zone if z not in keep and counts[z])
            or "nothing"
        )
        + ".",
    ]
    for w in analysis.warnings:
        lines.append(f"- note: {w}")
    return "\n".join(lines) + "\n"


def group_by_place(findings) -> list[tuple[str, list]]:
    """Several detectors firing on one hidden line are one item for a reader."""
    groups: dict[str, list] = {}
    for f in findings:
        groups.setdefault(_where(f), []).append(f)
    return list(groups.items())


def _where(f) -> str:
    bits = []
    if f.page:
        bits.append(f"p{f.page}")
    if f.segment_id:
        bits.append(f.segment_id)
    return "(" + ", ".join(bits) + ")" if bits else "(document properties)"
