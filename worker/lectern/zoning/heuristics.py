"""Heuristic zoning: rules that are cheap, offline and explainable.

Each rule returns a zone, a confidence in [0, 1] and the signals it fired on.
Confidence is not a probability; it is a rank of how much we trust the rule:

- ≥ 0.85  structural certainty (page furniture, code blocks, a TOC)
- 0.7–0.85  strong lexical evidence (detector hit, a heading that names the
  section's role, imperative-dense text)
- < 0.7  a guess worth a second opinion — these go to the LLM pass

The rules are written for the documents in DESIGN §3: assignments, syllabi,
specs, RFPs, papers, web articles. The labeled set (week 3) is what makes them
measurable, and `signals` is what makes their mistakes debuggable.
"""

from __future__ import annotations

import re
from collections import defaultdict

from lectern.models import Finding, Segment, Zone
from lectern.segment import FURNITURE_FLAGS

TASK_HEADINGS = re.compile(
    r"\b(deliverables?|requirements?|submission|submitting|what to submit|instructions?|"
    r"tasks?|your (task|job)|to ?do|questions?|problems?|exercises?|grading|rubric|"
    r"assessment|due|deadlines?|specifications?|scope of work|statement of work|"
    r"evaluation criteria|acceptance criteria|must|shall|policies|policy|rules)\b",
    re.I,
)
BACKGROUND_HEADINGS = re.compile(
    r"\b(introduction|background|overview|motivation|context|related work|summary|"
    r"abstract|description|learning (objectives|outcomes|goals)|objectives|goals|purpose|"
    r"glossary|definitions?|terminology|schedule|about|why|history|concepts?|theory|notes?|"
    r"recap|review|discussion|conclusions?|results?|methods?|evaluation|experiments?)\b",
    re.I,
)
EXAMPLE_HEADINGS = re.compile(
    r"\b(examples?|sample|samples|illustration|case study|demo|walkthrough|"
    r"figures?|tables?|listings?|test cases?|expected output|starter code)\b",
    re.I,
)
STRUCTURE_HEADINGS = re.compile(
    r"\b(table of contents|contents|references|bibliography|acknowledge?ments|index|"
    r"revision history|version history|change ?log|colophon|legal notice|copyright|"
    r"terms( and conditions)?|legal|disclaimer|contact( us| information)?|"
    r"related (posts|articles))\b",
    re.I,
)

TASK_MARKERS = re.compile(
    r"\b(you (must|should|need to|will|are (required|expected|asked|encouraged) to|may)|"
    r"your (task|job|goal|submission|report|code|solution|answer|proposal|response)|"
    r"must|should|shall|required|deliverables?|due|deadline|submit|submission|"
    r"turn in|hand in|upload|points?|pts|marks?|rubric|graded?|grading|"
    r"requirements?|the (system|application|vendor|contractor|proposal|bidder|solution) "
    r"(shall|must|will)|question \d+|q\d+\b|problem \d+|exercise \d+|part [a-z]\b|"
    r"task \d+|step \d+)\b",
    re.I,
)
IMPERATIVE_START = re.compile(
    r"^(\W*\d*[.)]?\s*)?(submit|implement|write|describe|explain|compute|calculate|show|"
    r"prove|answer|complete|create|design|build|develop|use|include|provide|list|identify|"
    r"compare|discuss|analy[sz]e|evaluate|derive|plot|report|upload|choose|select|determine|"
    r"find|give|state|define|sketch|draw|justify|demonstrate|test|run|install|configure|"
    r"ensure|make sure|read|review|consider|note|attach|fill|follow|do not|don't|never|"
    r"always|avoid|verify|check|measure|record|document|specify|propose|deliver)\b",
    re.I,
)
BACKGROUND_MARKERS = re.compile(
    r"\b(in this (paper|chapter|section|document|course|lecture|module),? we|"
    r"we (present|propose|describe|show|introduce|study|argue)|is (a|an|the)|are (a|an|the)|"
    r"refers to|is defined as|consists of|recall that|historically|in general|"
    r"for instance|such as|because|therefore|however|whereas)\b",
    re.I,
)
EXAMPLE_MARKERS = re.compile(
    r"^(\W*)(for example|e\.g\.|example \d*|sample (input|output|solution|run)|"
    r"expected output|consider the following|suppose|input:|output:|>>>|\$ )",
    re.I | re.M,
)
LEGAL_BOILERPLATE = re.compile(
    r"(all rights reserved|©|\(c\) \d{4}|copyright|confidential|terms of (use|service)|"
    r"privacy policy|cookies?|unsubscribe|click here|skip to (main )?content|sign in|log in|"
    r"follow us|share this|related articles|advertisement|powered by|reserves? the right|"
    r"public records?|does not (commit|constitute|obligate)|no obligation|without (notice|"
    r"liability)|warrant(y|ies)|indemnif|liabilit(y|ies)|office hours|e-?mail:|phone:)",
    re.I,
)
TOC_LINE = re.compile(r"(\.{3,}|…)\s*\d{1,4}\s*$|^\s*\d+(\.\d+)*\s+\S.*\s\d{1,4}\s*$", re.M)
URL = re.compile(r"https?://|www\.|\]\([^)]+\)", re.I)  # bare URLs and Markdown links
CODE_LINE = re.compile(
    r"[;{}]\s*$|^\s*(def|class|import|from|return|if|for|while|var|let|const|int|void|public|#include)\b|[=<>!]=|\(\)|->|=>|\$\s"
)
_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")


def zone_heuristics(segments: list[Segment], findings: list[Finding]) -> None:
    """Sets zone / confidence / method=heuristic / signals in place."""
    by_segment: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        if f.segment_id:
            by_segment[f.segment_id].append(f)
    for seg in segments:
        zone, conf, signals = _classify(seg, by_segment.get(seg.id, []))
        seg.zone = zone
        seg.confidence = round(conf, 2)
        seg.signals = signals


def _classify(seg: Segment, findings: list[Finding]) -> tuple[Zone, float, list[str]]:
    signals: list[str] = []
    text = seg.text
    body = re.sub(r"^#+ .*$", "", text, flags=re.M).strip()  # text without its headings
    heading = seg.heading_path[-1] if seg.heading_path else ""
    flags = set(seg.flags)

    # 0. hidden text: proved by a detector, never argued with
    hidden_flags = [f for f in seg.flags if f.startswith("hidden:")]
    if hidden_flags:
        signals += [f"flag:{f}" for f in hidden_flags]
        return Zone.hidden, 0.95, signals

    # 1. page furniture: headers, footers, page numbers
    furniture = flags & FURNITURE_FLAGS
    if furniture:
        signals += [f"flag:{f}" for f in sorted(furniture)]
        return Zone.structure, 0.92, signals

    # 2. detector hits that make up the segment
    covered = sum(f.span.get("end", 0) - f.span.get("start", 0) for f in findings)
    share = covered / max(1, len(text))
    d1 = [f for f in findings if f.detector == "D1"]
    p1 = [f for f in findings if f.detector == "P1"]
    if p1:
        signals.append(f"P1×{len(p1)}")
        if share >= 0.4 or seg.tokens_est <= 60:
            return Zone.ai_policy, 0.85, signals
    if d1:
        signals.append(f"D1×{len(d1)}")
        if share >= 0.3 or seg.tokens_est <= 60:
            return Zone.ai_directive, 0.8, signals

    # 3. sections whose heading says "boilerplate" (before the code/table rules: a
    #    revision-history table is structure, not an example)
    if STRUCTURE_HEADINGS.search(heading):
        signals.append("heading:structure")
        return Zone.structure, 0.75, signals

    # 4. code, tables, examples
    if "code_heavy" in flags:
        signals.append("flag:code_heavy")
        return Zone.example, 0.9, signals
    code_lines = [ln for ln in body.splitlines() if ln.strip()]
    code_like = sum(1 for ln in code_lines if CODE_LINE.search(ln))
    if code_lines and len(code_lines) >= 2 and code_like / len(code_lines) >= 0.5:
        signals.append(f"code_like={code_like}/{len(code_lines)}")
        return Zone.example, 0.7, signals
    if EXAMPLE_HEADINGS.search(heading):
        signals.append("heading:example")
        return Zone.example, 0.75, signals
    if EXAMPLE_MARKERS.search(body):
        signals.append("marker:example")
        return Zone.example, 0.6, signals

    # 4. structure by content
    if "heading_only" in flags:
        signals.append("flag:heading_only")
        return Zone.structure, 0.6, signals
    toc_lines = len(TOC_LINE.findall(body))
    if toc_lines >= 3 or re.search(r"\btable of contents\b", heading + " " + text[:80], re.I):
        signals.append(f"toc_lines={toc_lines}")
        return Zone.structure, 0.85, signals
    lines = [ln for ln in body.splitlines() if ln.strip()]
    short_lines = sum(1 for ln in lines if len(ln.split()) <= 4)
    urls = len(URL.findall(body))
    legal = len(LEGAL_BOILERPLATE.findall(body))
    if legal and (seg.tokens_est <= 80 or (legal >= 2 and seg.tokens_est <= 160)):
        signals.append(f"boilerplate={legal}")
        return Zone.structure, 0.8, signals
    if urls >= 2 and seg.tokens_est <= 60 and len(lines) <= 3:
        signals.append(f"link_line:urls={urls}")
        return Zone.structure, 0.75, signals
    if lines and short_lines / len(lines) >= 0.7 and (urls >= 2 or len(lines) >= 6):
        signals.append(f"short_lines={short_lines}/{len(lines)},urls={urls}")
        return Zone.structure, 0.7, signals

    # 5. task vs background
    sentences = [s for s in _SENTENCES.split(body) if s and s.strip()]
    n_sent = max(1, len(sentences))
    imperatives = sum(1 for s in sentences if IMPERATIVE_START.match(s.strip()))
    task_hits = len(TASK_MARKERS.findall(body)) + imperatives
    bg_hits = len(BACKGROUND_MARKERS.findall(body))
    task_density = task_hits / n_sent
    avg_len = sum(len(s.split()) for s in sentences) / n_sent
    task_heading = bool(TASK_HEADINGS.search(heading))
    bg_heading = bool(BACKGROUND_HEADINGS.search(heading))
    if imperatives:
        signals.append(f"imperatives={imperatives}")
    if task_hits:
        signals.append(f"task_markers={task_hits}/{n_sent}")
    if bg_hits:
        signals.append(f"background_markers={bg_hits}")
    if task_heading:
        signals.append("heading:task")
    if bg_heading:
        signals.append("heading:background")

    if bg_heading and not task_heading and task_density < 1.0:
        # an overview, introduction or glossary stays background unless it is nothing but
        # instructions ("you will implement …" in an overview is still context)
        return Zone.background, 0.7 if task_density < 0.25 else 0.65, signals
    if task_density >= 0.6 and task_hits >= 2:
        return Zone.task, min(0.9, 0.7 + 0.1 * task_density), signals
    if task_heading and task_hits >= 1:
        return Zone.task, 0.75, signals
    if bg_heading and task_density < 0.25:
        return Zone.background, 0.7, signals
    if task_density >= 0.35:
        return Zone.task, 0.6, signals
    if avg_len >= 12 and task_density < 0.2 and (bg_hits or n_sent >= 2):
        signals.append(f"narrative:avg_len={avg_len:.0f}")
        return Zone.background, 0.6, signals
    if task_hits:
        return Zone.task, 0.5, signals
    if bg_hits:
        return Zone.background, 0.5, signals
    return Zone.unknown, 0.3, signals
