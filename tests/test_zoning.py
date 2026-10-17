from pathlib import Path

from lectern.converters import load
from lectern.models import Finding, Segment, SegmentAnchor, Severity, Zone
from lectern.screen import screen
from lectern.segment import est_tokens, segment
from lectern.zoning import zone_heuristics


def _seg(text: str, path=None, flags=None, sid="s1") -> Segment:
    return Segment(
        id=sid,
        seq=1,
        heading_path=path or [],
        text=text,
        tokens_est=est_tokens(text),
        flags=flags or [],
        anchor=SegmentAnchor(block_start=0, block_end=0),
    )


def _zone(text, **kw):
    seg = _seg(text, **kw)
    zone_heuristics([seg], [])
    return seg


def test_furniture_is_structure_with_high_confidence():
    seg = _zone("Page 3 of 12", flags=["footer", "page_number"])
    assert seg.zone is Zone.structure and seg.confidence >= 0.85
    assert "flag:footer" in seg.signals


def test_code_and_examples():
    assert _zone("```\nx = 1\n```", flags=["code_heavy"]).zone is Zone.example
    assert _zone("Consider the following input: 3 1 2", path=["Sample run"]).zone is Zone.example
    code = _zone("frontier = new PriorityQueue();\nframe.put(start, 0);\ncame_from = new Map();")
    assert code.zone is Zone.example and any(s.startswith("code_like") for s in code.signals)


def test_task_by_imperatives_and_heading():
    seg = _zone(
        "Implement the parser in parser.py. Submit your code by Friday. "
        "Include unit tests. Your report must not exceed two pages.",
        path=["Deliverables"],
    )
    assert seg.zone is Zone.task and seg.confidence >= 0.7
    assert "heading:task" in seg.signals


def test_background_by_narrative_prose():
    seg = _zone(
        "Sorting is one of the oldest problems in computer science, and it is a good "
        "place to start because the algorithms are simple enough to reason about. "
        "Historically, the first sorting machines were built for census data, such as "
        "the tabulators of the 1890s, which used punched cards.",
        path=["Introduction"],
    )
    assert seg.zone is Zone.background


def test_toc_and_references_are_structure():
    toc = _zone("1 Introduction ........ 3\n2 Methods ........ 7\n3 Results ........ 12")
    assert toc.zone is Zone.structure and toc.confidence >= 0.8
    refs = _zone(
        "- Knuth, TAOCP. https://a.example\n- CLRS. https://b.example", path=["References"]
    )
    assert refs.zone is Zone.structure
    nav = _zone("[Home](/) | [About](/about) | [Contact](/contact)")
    assert nav.zone is Zone.structure


def test_unknown_when_nothing_fires():
    seg = _zone("Blue.")
    assert seg.zone is Zone.unknown and seg.confidence < 0.5


def test_detector_findings_drive_ai_zones():
    text = "Use of generative AI tools is not permitted for this assignment."
    seg = _seg(text)
    f = Finding(
        detector="P1",
        kind="ai_policy",
        severity=Severity.info,
        segment_id="s1",
        excerpt=text,
        span={"start": 0, "end": len(text)},
    )
    zone_heuristics([seg], [f])
    assert seg.zone is Zone.ai_policy and seg.confidence >= 0.8

    long_text = ("Late work loses ten percent per day. " * 12) + text
    mixed = _seg(long_text, path=["Policies"])
    f2 = f.model_copy(update={"span": {"start": len(long_text) - len(text), "end": len(long_text)}})
    zone_heuristics([mixed], [f2])
    assert mixed.zone is not Zone.ai_policy  # a single sentence doesn't relabel a long section
    assert "P1×1" in mixed.signals


def test_end_to_end_heuristics_on_the_assignment(assignment_md: Path):
    doc = load(assignment_md)
    segs = segment(doc)
    zone_heuristics(segs, screen(doc, segs))
    by_heading = {tuple(s.heading_path[-1:]): s for s in segs}
    assert by_heading[("Deliverables",)].zone is Zone.task
    assert by_heading[("Example",)].zone is Zone.example
    assert by_heading[("Policies",)].zone is Zone.ai_policy
    assert by_heading[("References",)].zone is Zone.structure
    assert by_heading[("Assignment 2: Sorting",)].zone in (Zone.background, Zone.task)


def test_role_headings_stay_background_even_when_imperative():
    # ADR-013: requirement-shaped text about someone else's work is background
    seg = _zone(
        "- Design and build services in Go and Java that process settlements.\n"
        "- Own the reliability of what you ship: dashboards, alerts, runbooks.",
        path=["Backend Engineer", "What you will do"],
    )
    assert seg.zone is Zone.background and "heading:role" in seg.signals


def test_a_footer_merged_into_a_real_section_is_not_boilerplate():
    seg = _zone(
        "Read chapter 11 of the textbook and attempt exercise 11.3; we will start from "
        "its solution.\n\nSlides based on material by the course staff. Not for redistribution.",
        path=["Before next class"],
    )
    assert seg.zone is Zone.task
    assert _zone("© 2026 Example Corp. All rights reserved. Not for redistribution.").zone is (
        Zone.structure
    )


def test_initials_do_not_split_sentences():
    seg = _zone(
        "- K. Osei reported income of $12,400 and expenditure of $9,850 for August, "
        "leaving reserves of $61,200. The roof repair invoice has not yet arrived. "
        "The report was received.",
        path=["Minutes", "Treasurer's report"],
    )
    assert seg.zone is Zone.background


def test_fenced_code_does_not_turn_a_step_into_structure():
    seg = _zone(
        "Run the following in a repository with at least one commit. Use a name that says "
        "what the branch is for.\n\n```\ngit switch -c add-readme\ncat .git/HEAD\n"
        "cat .git/refs/heads/add-readme\n```\n\nThe first `cat` shows that HEAD now names "
        "your new branch.",
        path=["Step 1: Create a branch"],
    )
    assert seg.zone is Zone.task


def test_tables_are_content_under_schedule_headings_and_structure_as_revision_history():
    table = "| Week | Topic |\n|---|---|\n| 1 | Overview |\n| 2 | Regression |"
    assert _zone(table, path=["Schedule"], flags=["code_heavy"]).zone is Zone.background
    assert _zone(table, path=["Results"], flags=["code_heavy"]).zone is Zone.example
    rev = "| Revision | Date | Change |\n|---|---|---|\n| 1 | 2022-05-10 | First issue |"
    assert _zone(rev, flags=["code_heavy"]).zone is Zone.structure
