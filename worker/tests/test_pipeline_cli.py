import json
from pathlib import Path

from lectern.cli import main
from lectern.models import Analysis, DocType, LLMUsage, Overview, Zone
from lectern.pipeline import analyze


def test_analyze_offline_on_pdf(assignment_pdf: Path):
    a = analyze(assignment_pdf, use_llm=False)
    assert a.mode == "heuristic-only" and a.overview is None and a.llm is None
    assert a.taxonomy_v == "1" and a.pages == 2
    assert abs(sum(a.zone_shares.values()) - 1.0) < 0.01
    kinds = {f.detector for f in a.findings}
    assert kinds == {"D1", "P1"}
    policy = next(s for s in a.segments if s.zone is Zone.ai_policy)
    assert policy.heading_path[-1] == "Policies"
    assert any("heuristic-only" in w for w in a.warnings)
    Analysis.model_validate_json(a.model_dump_json())  # round-trips


def test_analyze_without_credentials_degrades_and_says_so(assignment_md: Path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    a = analyze(assignment_md, use_llm=True)
    assert a.mode == "heuristic-only"
    assert any("ANTHROPIC_API_KEY" in w for w in a.warnings)


def test_analyze_with_an_llm(assignment_md: Path):
    from tests.test_llm_pass import FakeLLM

    llm = FakeLLM(
        labels={},
        overview=Overview(overview="A sorting assignment.", doc_type=DocType.assignment),
    )
    a = analyze(assignment_md, llm=llm)
    assert a.mode == "llm"
    assert a.overview is not None and a.overview.doc_type is DocType.assignment
    assert a.llm is not None and a.llm.calls >= 2  # at least one zoning batch + the overview
    assert not any("heuristic-only" in w for w in a.warnings)


def test_analyze_unavailable_llm_falls_back(assignment_md: Path):
    from lectern.llm import LLMUnavailable

    class Down:
        model = "down"
        usage = LLMUsage(model="down")

        def parse(self, **kw):
            raise LLMUnavailable("cannot reach the Anthropic API: offline")

    a = analyze(assignment_md, llm=Down())
    assert a.mode == "heuristic-only" and a.overview is None
    assert any("cannot reach" in w for w in a.warnings)


def test_cli_scan_json(assignment_md: Path, capsys):
    code = main(["scan", str(assignment_md), "--no-llm", "--json"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "heuristic-only"
    assert out["segments"][0]["id"] == "s1"
    assert "zone_shares" in out and "findings" in out


def test_cli_scan_terminal(assignment_pdf: Path, capsys):
    code = main(["scan", str(assignment_pdf), "--no-llm", "--full-text"])
    out = capsys.readouterr().out
    assert code == 0
    assert "lectern scan" in out and "Zone map" in out and "Findings (2)" in out
    assert "IGNORE PREVIOUS INSTRUCTIONS" in out  # --full-text prints segment bodies


def test_cli_errors(tmp_path: Path, capsys):
    assert main(["scan", str(tmp_path / "missing.pdf"), "--no-llm"]) == 1
    assert "file not found" in capsys.readouterr().err
    weird = tmp_path / "a.xyz"
    weird.write_text("x")
    assert main(["scan", str(weird), "--no-llm"]) == 1
    assert "unsupported format" in capsys.readouterr().err
