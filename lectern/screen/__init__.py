"""`screen`: static detectors that run *before* any LLM reads the document.

Ordering is a security property (DESIGN §4): what a detector flags as hidden is
quarantined and never enters a prompt. In week 2 the suite holds the two
text-pattern detectors zoning needs anyway — D1 (AI-directed instructions) and
P1 (AI-use policy statements). The hidden-text detectors H1–H6 join in week 3
and read the style hints the PDF converter preserved.

Every detector has the same shape: look at the document and its segments,
return findings. Nothing here changes the document — detect, disclose, and let
the human decide.
"""

from __future__ import annotations

from typing import Protocol

from lectern.models import Document, Finding, Segment


class Detector(Protocol):
    name: str

    def run(self, doc: Document, segments: list[Segment]) -> list[Finding]: ...


def default_detectors() -> list[Detector]:
    from lectern.screen.patterns import DirectivePatterns, PolicyPatterns

    return [DirectivePatterns(), PolicyPatterns()]


def screen(
    doc: Document, segments: list[Segment], detectors: list[Detector] | None = None
) -> list[Finding]:
    findings: list[Finding] = []
    for det in detectors if detectors is not None else default_detectors():
        findings.extend(det.run(doc, segments))
    return findings
