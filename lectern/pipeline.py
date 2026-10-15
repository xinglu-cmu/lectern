"""`analyze`: the whole engine as one function.

    load -> screen (blocks) -> segment -> screen (text) -> zone -> summarize -> emit

Two screening passes, both before any LLM call: the block detectors H1–H6 read
style and encoding evidence and carve hidden text into its own blocks; the text
detectors D1/P1 read segments for AI-directed and AI-policy sentences. A
directive inside hidden text is critical and quarantined; a visible one is a
warning the model may later soften to "quoted". `emit` is the caller's job: the
CLI renders an `Analysis` as a terminal report, JSON or clean Markdown; the
worker will store it.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

import lectern
from lectern.converters import load
from lectern.llm import (
    DEFAULT_MODEL,
    LLM,
    AnthropicLLM,
    LLMUnavailable,
    LocalLLM,
    credentials_present,
)
from lectern.models import Analysis, Finding, FindingStatus, Overview, Segment, Severity, Zone
from lectern.overview import summarize
from lectern.screen import Detector, screen
from lectern.screen.confirm import confirm_directives
from lectern.screen.hidden import BlockDetector, screen_blocks
from lectern.segment import segment
from lectern.zoning import zone_heuristics, zone_with_llm

log = logging.getLogger("lectern.pipeline")


def analyze(
    path: str | Path,
    *,
    use_llm: bool = True,
    llm: LLM | None = None,
    model: str = DEFAULT_MODEL,
    local: bool | str = False,
    detectors: list[Detector] | None = None,
    block_detectors: list[BlockDetector] | None = None,
) -> Analysis:
    """Run the pipeline on one file.

    `use_llm=False` is `--no-llm`: heuristics only, no overview, no D1 confirmation.
    With `use_llm=True` and no `llm` given, an Anthropic client is created when
    credentials are present; otherwise the analysis degrades to heuristic-only and
    says so in `warnings`.
    """
    warnings: list[str] = []
    doc = load(path)
    if doc.meta.get("empty_pages"):
        warnings.append(
            f"{doc.meta['empty_pages']} page(s) had no extractable text (scanned or image-only?)"
        )
    if not doc.blocks:
        warnings.append("no text could be extracted from this document")

    doc, findings = screen_blocks(doc, block_detectors)  # H1–H6, before anything else
    segments = segment(doc)
    _attach_segments(findings, segments)
    findings += screen(doc, segments, detectors)  # D1, P1 on segment text
    _escalate_hidden_directives(findings, segments)
    zone_heuristics(segments, findings)

    overview: Overview | None = None
    mode = "heuristic-only"
    if use_llm and llm is None:
        llm = make_llm(model, local=local)
        if llm is None:
            warnings.append(
                "no ANTHROPIC_API_KEY found: zoning is heuristic-only and there is no overview "
                "(same as --no-llm; or use --local with a model served by Ollama)"
            )
    if use_llm and llm is not None:
        try:
            zone_with_llm(segments, llm, title=doc.title)
            confirm_directives(findings, segments, llm)
            overview = summarize(doc, segments, llm)
            mode = "llm"
        except LLMUnavailable as exc:
            warnings.append(f"{exc}; zoning is heuristic-only and there is no overview")
            llm = None
        if llm is not None and llm.usage.failures:
            warnings.append(
                f"{llm.usage.failures} LLM call(s) returned nothing usable; those results keep "
                "their heuristic values"
            )
    if mode == "heuristic-only":
        warnings.append(
            "zoning is heuristic-only; ai_directive detection is regex-only (a document that "
            "quotes injection text will raise warnings)"
        )

    findings.sort(key=_finding_order)
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


def make_llm(model: str = DEFAULT_MODEL, *, local: bool | str = False) -> LLM | None:
    """The model client for this run: a local model when asked for (`--local`, optionally
    naming the model), else Claude when credentials are present, else None."""
    if local:
        return LocalLLM(local if isinstance(local, str) else None)
    return AnthropicLLM(model) if credentials_present() else None


def _attach_segments(findings: list[Finding], segments: list[Segment]) -> None:
    """Block-level findings learn which segment holds their block."""
    for f in findings:
        if f.block is None or f.segment_id:
            continue
        for s in segments:
            if s.anchor.block_start <= f.block <= s.anchor.block_end:
                f.segment_id = s.id
                f.page = f.page or s.anchor.page_start
                break


def _escalate_hidden_directives(findings: list[Finding], segments: list[Segment]) -> None:
    """hidden ∧ directive ⇒ critical, quarantined (DESIGN §4 action matrix)."""
    hidden_ids = {s.id for s in segments if any(f.startswith("hidden:") for f in s.flags)}
    directive_ids = {
        f.segment_id for f in findings if f.detector == "D1" and f.segment_id in hidden_ids
    }
    for f in findings:
        if f.segment_id in hidden_ids:
            f.status = FindingStatus.quarantined
            if f.detector == "D1":
                f.severity = Severity.critical
                f.note = "AI-directed instruction inside hidden text"
            elif f.segment_id in directive_ids:
                f.severity = Severity.critical


_SEVERITY_RANK = {Severity.critical: 0, Severity.warning: 1, Severity.info: 2}


def _finding_order(f: Finding) -> tuple:
    return (_SEVERITY_RANK[f.severity], f.page or 0, f.block or 0, f.detector)


def zone_shares(segments: list[Segment]) -> dict[str, float]:
    totals: dict[Zone, int] = defaultdict(int)
    for seg in segments:
        totals[seg.zone] += seg.tokens_est
    total = sum(totals.values()) or 1
    return {z.value: round(t / total, 4) for z, t in totals.items() if t}


def fails_threshold(analysis: Analysis, level: Severity) -> bool:
    """`scan --fail-on LEVEL`: any non-dismissed finding at or above LEVEL."""
    rank = _SEVERITY_RANK[level]
    return any(
        _SEVERITY_RANK[f.severity] <= rank and f.status is not FindingStatus.dismissed
        for f in analysis.findings
    )
