"""The distillation corpus tools (eval/distill): manifest parsing, redaction, raw labels."""

import sys
from pathlib import Path

from lectern.models import Method, Zone
from lectern.zoning.llm_pass import ask_llm
from tests.test_llm_pass import FakeLLM, _seg

sys.path.insert(0, str(Path(__file__).parent.parent / "eval" / "distill"))
import collect  # noqa: E402


def test_manifest_parses_every_row_with_a_licence_and_url():
    sources = collect.read_manifest()
    assert 40 <= len(sources) <= 60
    assert len({s.id for s in sources}) == len(sources)
    for s in sources:
        assert s.url.startswith("https://"), s
        assert s.format in {"txt", "md", "html"}, s
        assert s.licence and s.kind, s


def test_manifest_kinds_are_spread():
    sources = collect.read_manifest()
    kinds = {s.kind for s in sources}
    assert len(kinds) >= 12
    for k in kinds:
        assert sum(1 for s in sources if s.kind == k) <= len(sources) / 5, k


def test_redaction_removes_emails_and_phones_but_keeps_dates_and_numbers():
    text = (
        "Contact alice.smith+x@example.org or +1 (202) 555-0147; UK 020 7946 0000.\n"
        "Published 2024-10-16, see RFC 8259 section 4.1; 18,000 students."
    )
    out, n = collect.redact(text)
    assert n == 3
    assert "example.org" not in out and "555-0147" not in out and "7946" not in out
    assert "2024-10-16" in out and "RFC 8259" in out and "18,000" in out


def test_truncate_cuts_at_a_paragraph_boundary():
    text = "\n\n".join(f"paragraph {i} " + "x" * 50 for i in range(100))
    out, cut = collect.truncate(text, max_chars=1000)
    assert cut and len(out) <= 1001 and out.endswith("\n")
    assert out.rstrip().endswith("x")
    assert collect.truncate("short", max_chars=1000) == ("short", False)


def test_ask_llm_returns_raw_labels_without_merging():
    segs = [_seg(1, Zone.task, 0.9), _seg(2, Zone.unknown, 0.3), _seg(3, Zone.task, 0.6)]
    llm = FakeLLM(
        labels={
            "s1": [dict(zone="background", confidence="low")],
            "s2": [dict(zone="example", confidence="high")] * 2,  # duplicated id
        }
    )
    labels = ask_llm(segs, llm, title="T")
    assert len(llm.calls) == 1  # confident segments are sent too: the caller chose them
    assert labels["s1"].zone.value == "background" and labels["s1"].confidence.value == "low"
    assert labels["s2"] is None and labels["s3"] is None
    assert all(s.method is Method.heuristic for s in segs)  # nothing merged
    assert segs[0].zone is Zone.task


def test_ask_llm_omits_segments_of_a_failed_batch():
    segs = [_seg(1, Zone.unknown, 0.3)]
    assert ask_llm(segs, FakeLLM(fail=True)) == {}
