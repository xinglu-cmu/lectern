"""`analyze`: the whole engine as one function.

    load -> segment -> screen -> zone (heuristics, then LLM) -> summarize -> emit

`emit` is the caller's job: the CLI renders an `Analysis` as a terminal report or
JSON; the worker will store it. Everything before that is here, in order, with
the ordering that matters spelled out: screening runs before any LLM call.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

import lectern
from lectern.converters import load
from lectern.llm import DEFAULT_MODEL, LLM, AnthropicLLM, LLMUnavailable, credentials_present
from lectern.models import Analysis, Overview, Segment, Zone
from lectern.overview import summarize
from lectern.screen import Detector, screen
from lectern.segment import segment
from lectern.zoning import zone_heuristics, zone_with_llm

log = logging.getLogger("lectern.pipeline")


def analyze(
    path: str | Path,
    *,
    use_llm: bool = True,
    llm: LLM | None = None,
    model: str = DEFAULT_MODEL,
    detectors: list[Detector] | None = None,
) -> Analysis:
    """Run the pipeline on one file.

    `use_llm=False` is `--no-llm`: heuristics only, no overview. With `use_llm=True`
    and no `llm` given, an Anthropic client is created when credentials are present;
    otherwise the analysis degrades to heuristic-only and says so in `warnings`.
    """
    warnings: list[str] = []
    doc = load(path)
    if doc.meta.get("empty_pages"):
        warnings.append(
            f"{doc.meta['empty_pages']} page(s) had no extractable text (scanned or image-only?)"
        )
    if not doc.blocks:
        warnings.append("no text could be extracted from this document")

    segments = segment(doc)
    findings = screen(doc, segments, detectors)  # before any LLM sees the text
    zone_heuristics(segments, findings)

    overview: Overview | None = None
    mode = "heuristic-only"
    if use_llm and llm is None:
        if credentials_present():
            llm = AnthropicLLM(model)
        else:
            warnings.append(
                "no ANTHROPIC_API_KEY found: zoning is heuristic-only and there is no overview "
                "(same as --no-llm)"
            )
    if use_llm and llm is not None:
        try:
            zone_with_llm(segments, llm, title=doc.title)
            overview = summarize(doc, segments, llm)
            mode = "llm"
        except LLMUnavailable as exc:
            warnings.append(f"{exc}; zoning is heuristic-only and there is no overview")
            llm = None
        if llm is not None and llm.usage.failures:
            warnings.append(
                f"{llm.usage.failures} LLM call(s) returned nothing usable; those segments keep "
                "their heuristic labels"
            )
    if mode == "heuristic-only":
        warnings.append("zoning is heuristic-only; ai_directive detection is regex-only")

    return Analysis(
        lectern_version=lectern.__version__,
        taxonomy_v=lectern.TAXONOMY_V,
        source=str(path),
        format=doc.format,
        converter=doc.converter,
        pages=doc.pages,
        title=doc.title,
        mode=mode,
        overview=overview,
        segments=segments,
        findings=findings,
        zone_shares=zone_shares(segments),
        llm=llm.usage if llm is not None else None,
        warnings=warnings,
    )


def zone_shares(segments: list[Segment]) -> dict[str, float]:
    totals: dict[Zone, int] = defaultdict(int)
    for seg in segments:
        totals[seg.zone] += seg.tokens_est
    total = sum(totals.values()) or 1
    return {z.value: round(t / total, 4) for z, t in totals.items() if t}
