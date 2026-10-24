"""Heuristic zoning: rules that are cheap, offline and explainable.

Each rule returns a zone, a confidence in [0, 1] and the signals it fired on.
Confidence is not a probability; it is a rank of how much we trust the rule:

- ≥ 0.85  structural certainty (page furniture, code blocks, a TOC)
- 0.7–0.85  strong lexical evidence (detector hit, a heading that names the
  section's role, imperative-dense text)
- < 0.7  a guess worth a second opinion — these go to the LLM pass

The rules are written for the documents in DESIGN §3: assignments, syllabi,
specs, RFPs, papers, web articles. The labeled set (eval/zoning) is what makes them
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
    r"evaluation criteria|acceptance criteria|criteria|how to apply|installation|setup|"
    r"fees?|payment|must|shall|policies|policy|rules|announcements?|action items?|step \d+)\b",
    re.I,
)
BACKGROUND_HEADINGS = re.compile(
    r"\b(introduction|background|overview|motivation|context|related work|summary|"
    r"abstract|description|learning (objectives|outcomes|goals)|objectives|goals|purpose|"
    r"glossary|definitions?|terminology|schedule|about|why|history|concepts?|theory|notes?|"
    r"recap|discussion|conclusions?|results?|methods?|experiments?|"
    r"what is in the box|what you will do|what we are looking for|minutes)\b",
    re.I,
)
ROLE_HEADINGS = re.compile(  # about someone else: background, however imperative (ADR-013)
    r"\b(what you(’|')?ll do|what you will do|what we(’|')?re looking for|what we are looking for|"
    r"responsibilities|duties|learning (objectives|outcomes|goals)|course (objectives|outcomes)|"
    r"qualifications|who you are|about the (role|team|job|position|company))\b",
    re.I,
)
EXAMPLE_HEADINGS = re.compile(
    r"\b(examples?|sample|samples|illustration|case study|demo|walkthrough|"
    r"listings?|test cases?|expected output|starter code|usage|worked example)\b",
    re.I,
)
STRUCTURE_HEADINGS = re.compile(
    r"\b(table of contents|contents|references|bibliography|acknowledge?ments|index|"
    r"revision history|version history|change ?log|colophon|legal notice|copyright|"
    r"terms and conditions|terms of (use|service)|legal|disclaimer|contact( us| information)?|"
    r"related (posts|articles))\b",
    re.I,
)

TASK_MARKERS = re.compile(
    r"\b(you (must|should|need to|will|are (required|expected|asked|encouraged) to|may)|"
    r"your (task|job|goal|submission|report|code|solution|answer|proposal|response)|"
    r"must|should|shall|required|deliverables?|due(?! to)|deadline|submit|submission|"
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
    r"always|avoid|verify|check|measure|record|document|specify|propose|deliver|send|apply|"
    r"email|register|pay|sign|photograph|label|mount|connect|restore|turn off|remove|press|"
    r"open|confirm|update|reply|schedule|circulate|install|download|enter|click|return)\b",
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
    r"^(\W*)(for example|e\.g\.|example( \d+)?\s*:|example \d+\b|"
    r"sample (input|output|solution|run)|expected output|consider the following|suppose|"
    r"input:|output:|>>>|\$ )",
    re.I | re.M,
)
LEGAL_BOILERPLATE = re.compile(
    r"(all rights reserved|©|\(c\) \d{4}|copyright|confidential|terms of (use|service)|"
    r"privacy policy|cookies?|unsubscribe|click here|skip to (main )?content|sign in|log in|"
    r"follow us|share this|related articles|advertisement|powered by|reserves? the right|"
    r"public records?|does not (commit|constitute|obligate)|no obligation|without (notice|"
    r"liability)|\bwarrant(y|ies)\b|indemnif|\bliabilit(y|ies)\b|not for redistribution|"
    r"intended only for the addressee|subject to change without notice|governed by the laws|"
    r"unenforceable|severab|supersedes any prior|not a contract|subject to bcp 78|"
    r"trademarks? (and|or) logos|brand guidelines|official websites use \.gov|"
    r"secure \.gov websites|request an accessible format|users of assistive technology|"
    r"legal provisions relating to ietf documents|simplified bsd license|"
    r"official website of the|here(’|')s how you know|jump to content|return to top|back to top)",
    re.I,
)
TABLE_CONTENT_HEADINGS = re.compile(
    r"\b(schedule|timetable|calendar|plans?|pricing|agenda|important dates|office hours)\b", re.I
)
TERMS_HEADING = re.compile(r"^(\d+[.)]?\s*)?terms$", re.I)
POINTER_HEADINGS = re.compile(  # a short section that only points elsewhere
    r"\b(license|licen[cs]ing|documentation|contributing|trademarks?|further reading|see also|"
    r"next steps|sponsors?|credits|maintainers?)\b",
    re.I,
)
SITE_CHROME_HEADINGS = re.compile(  # a web page's own furniture, whatever its length
    r"\b(share this page|explore the topic|updates to this page|get help|about this site|"
    r"sign up for emails|is this page useful|help us improve)\b",
    re.I,
)
METADATA_KEY = re.compile(r"(?:^|\s)[A-Za-z][\w-]{1,24}(?: [A-Za-z]+)?:\s+\S")  # "Title: …"
CITATION_LINE = re.compile(r"^\s*\[[\w.-]+\]\s", re.M)  # [RFC2119] Bradner, S., …
BADGE = re.compile(r"\[!\[|img\.shields\.io|badge\.fury\.io")
MARKUP = re.compile(r"\{%.*?%\}|\{\{.*?\}\}|`[^`\n]*`")  # templating, inline code: not code lines
LINK_ITEM = re.compile(r"^\s*[-*+]\s+\[[^\]]+\]\(")  # "* [Title](url)"
NAV_SPLIT = re.compile(r"(?:^|\s)[-•*]\s+")
INSTRUCTION = re.compile(  # prose that tells the reader to run what follows
    r"\b(run|enter|type|execute|paste) (the following|this)\b|\binstall (with|using|via)\b|"
    r"(?:^|[.:]\s+)(install|run|open|type|enter|execute)\b",
    re.I,
)
FENCED_CODE = re.compile(r"```.*?```", re.S)
TOC_LINE = re.compile(r"((\.\s?){3,}|…)\s*\d{1,4}\s*$|^\s*\d+(\.\d+)*\s+\S.*\s\d{1,4}\s*$", re.M)
URL = re.compile(r"https?://|www\.|\]\([^)]+\)", re.I)  # bare URLs and Markdown links
CODE_LINE = re.compile(
    r"[;{}]\s*$|^\s*(def|class|import|from|return|if|for|while|var|let|const|int|void|public|#include)\b|[=<>!]=|\(\)|->|=>|\$\s"
)
_SENTENCES = re.compile(r"(?<=[.!?])(?<![A-Z]\.)\s+|\n+")


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
    # the section this segment belongs to: its last heading line if it carries one (a segment
    # that pools the title with the first section is judged by that section), else the path
    own_headings = [ln.lstrip("#").strip() for ln in text.splitlines() if ln.startswith("#")]
    heading = (
        own_headings[-1] if own_headings else (seg.heading_path[-1] if seg.heading_path else "")
    )
    flags = set(seg.flags)

    # 0. hidden text: proved by a detector, never argued with
    hidden_flags = [f for f in seg.flags if f.startswith("hidden:")]
    if hidden_flags:
        signals += [f"flag:{f}" for f in hidden_flags]
        return Zone.hidden, 0.95, signals

    # 1a. a title block: the first segment, a top-level heading plus at most a line or two
    #     (byline, course code, date) — the document's own masthead
    if (
        seg.seq == 1
        and seg.heading_path
        and seg.text.startswith("# ")
        and len(body) <= 160
        and body.count("\n") <= 1
        and not IMPERATIVE_START.match(body)
        and not TASK_MARKERS.search(body)
    ):
        signals.append("title_block")
        return Zone.structure, 0.6, signals

    # 1b. a metadata block: front matter, a PEP or RFC header, "Title: … Date: …" — at least
    #     three "key: value" lines and next to nothing else
    meta_keys = len(METADATA_KEY.findall(body[:600]))
    front_matter = body.startswith("---")
    if (meta_keys >= 2 and front_matter) or (meta_keys >= 3 and seg.seq == 1 and len(body) <= 900):
        signals.append(f"metadata_block={meta_keys}")
        return Zone.structure, 0.75, signals
    if len(body) <= 20 and body and not body[0].isalnum() and "```" not in body:
        signals.append("stub")
        return Zone.structure, 0.5, signals

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
    if STRUCTURE_HEADINGS.search(heading) or TERMS_HEADING.match(heading.strip()):
        signals.append("heading:structure")
        return Zone.structure, 0.75, signals
    if SITE_CHROME_HEADINGS.search(heading):
        signals.append("heading:site_chrome")
        return Zone.structure, 0.75, signals
    if (
        POINTER_HEADINGS.search(heading)
        and len(re.sub(r"\(https?://[^)]*\)", "", body)) <= 400
        and not IMPERATIVE_START.match(body.strip())
        and not INSTRUCTION.search(body)
    ):
        signals.append("heading:pointer")
        return Zone.structure, 0.7, signals
    if len(BADGE.findall(body)) >= 2 and seg.seq <= 2:
        rest = re.sub(r"\[!\[.*?\)\)|!\[.*?\)|\[.*?\]\(.*?\)|<[^>]+>", "", body).strip()
        if len(rest) <= 160:
            signals.append("badges")
            return Zone.structure, 0.7, signals

    # 4. code, tables, examples
    if "code_heavy" in flags:
        signals.append("flag:code_heavy")
        if re.search(r"\|\s*(revision|version)\s*\|", body, re.I):
            return Zone.structure, 0.75, signals
        if TABLE_CONTENT_HEADINGS.search(heading) and not EXAMPLE_HEADINGS.search(heading):
            return Zone.background, 0.6, signals
        return Zone.example, 0.9, signals
    fenced = "".join(FENCED_CODE.findall(body))
    prose_part = FENCED_CODE.sub("", body)
    if body.count("```") % 2 == 1:  # a fence the segmenter cut: code to the end
        tail = body[body.rfind("```") :]
        fenced += tail
        prose_part = prose_part.replace(tail, "")
    fenced_share = len(fenced) / max(1, len(body))
    if fenced and INSTRUCTION.search(prose_part) and fenced_share < 0.7:
        # "open a terminal and enter the following command: ```…```" tells the reader to act
        signals.append("instructions+code")
        return Zone.task, 0.65, signals
    if fenced and fenced_share >= 0.5:
        signals.append(f"fenced_code={fenced_share:.0%}")
        return Zone.example, 0.85 if fenced_share >= 0.7 else 0.7, signals
    code_lines = [ln for ln in MARKUP.sub("", body).splitlines() if ln.strip()]
    code_like = sum(1 for ln in code_lines if CODE_LINE.search(ln))
    grammar = sum(1 for ln in code_lines if re.match(r"^\s*[\w-]+\s*=\s", ln))
    rules = sum(1 for ln in code_lines if re.fullmatch(r"\s*[-=_ ]{6,}\s*", ln))
    if grammar >= 3 or rules >= 2:  # an ABNF grammar, or an ASCII table with rule lines
        signals.append(f"grammar={grammar},rules={rules}")
        return Zone.example, 0.7, signals
    if code_lines and len(code_lines) >= 3 and code_like / len(code_lines) >= 0.5:
        signals.append(f"code_like={code_like}/{len(code_lines)}")
        return Zone.example, 0.7, signals
    if EXAMPLE_HEADINGS.search(heading):
        signals.append("heading:example")
        return Zone.example, 0.75, signals
    if EXAMPLE_MARKERS.search(body) and (fenced or seg.tokens_est <= 250):
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
    prose = FENCED_CODE.sub("", body).strip()
    lines = [ln for ln in prose.splitlines() if ln.strip()]
    short_lines = sum(1 for ln in lines if len(ln.split()) <= 4)
    urls = len(URL.findall(prose))
    sentences = [s for s in _SENTENCES.split(prose) if s and s.strip()]
    legal = len(LEGAL_BOILERPLATE.findall(prose))
    # boilerplate must be most of the segment, not a footer merged into a real section
    legal_share = sum(len(s) for s in sentences if LEGAL_BOILERPLATE.search(s)) / max(1, len(prose))
    short = seg.tokens_est <= 80 or (legal >= 2 and seg.tokens_est <= 160)
    if legal and legal_share >= 0.5 and short:
        signals.append(f"boilerplate={legal}")
        return Zone.structure, 0.8, signals
    if urls >= 2 and seg.tokens_est <= 60 and len(lines) <= 3:
        signals.append(f"link_line:urls={urls}")
        return Zone.structure, 0.75, signals
    if lines and short_lines / len(lines) >= 0.7 and (urls >= 2 or len(lines) >= 6):
        signals.append(f"short_lines={short_lines}/{len(lines)},urls={urls}")
        return Zone.structure, 0.7, signals
    citations = len(CITATION_LINE.findall(prose))
    if citations >= 3 and citations / max(1, len(lines)) >= 0.5:
        signals.append(f"references={citations}")
        return Zone.structure, 0.75, signals
    link_items = sum(1 for ln in lines if LINK_ITEM.match(ln))
    if len(lines) >= 3 and link_items / len(lines) >= 0.8:
        signals.append(f"link_list={link_items}/{len(lines)}")
        return Zone.structure, 0.7, signals
    # a navigation list: many short items, no sentences, next to nothing imperative
    first_sep = NAV_SPLIT.search(prose)
    items = [it.strip() for it in NAV_SPLIT.split(prose) if it.strip()]
    if (
        first_sep
        and len(prose[: first_sep.start()].split()) <= 8
        and len(items) >= 3
        and sum(1 for it in items if len(it.split()) <= 6) / len(items) >= 0.8
        and not re.search(r"[a-z]{3}[.!?](\s|$)", prose)
        and sum(1 for it in items if IMPERATIVE_START.match(it)) / len(items) <= 0.1
        and sum(len(it.split()) for it in items) <= 200
    ):
        signals.append(f"nav_list={len(items)}")
        return Zone.structure, 0.7, signals

    # 5. task vs background
    if ROLE_HEADINGS.search(heading):
        signals.append("heading:role")
        return Zone.background, 0.7, signals
    n_sent = max(1, len(sentences))
    imperatives = sum(1 for s in sentences if IMPERATIVE_START.match(s.strip()))
    task_hits = len(TASK_MARKERS.findall(prose)) + imperatives
    bg_hits = len(BACKGROUND_MARKERS.findall(prose))
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

    if bg_heading and not task_heading and imperatives < 2:
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
    if sentences and avg_len >= 8 and prose.rstrip(")]*_`").endswith((".", "!", "?")):
        signals.append("prose")
        return Zone.background, 0.4, signals
    if task_heading:
        return Zone.task, 0.55, signals
    return Zone.unknown, 0.3, signals
