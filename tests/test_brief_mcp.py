"""`lectern brief` and the MCP tools."""

from pathlib import Path

import pytest

from lectern.brief import BriefOut, heuristic_brief, render_brief, write_brief
from lectern.cli import main
from lectern.emit import DEFAULT_KEEP
from lectern.mcp_server import LecternTools, build_server, scan_summary
from lectern.models import DocType, Overview, Zone
from lectern.pipeline import analyze
from tests.test_llm_pass import FakeLLM


def test_heuristic_brief_lists_task_segments(assignment_pdf: Path):
    a = analyze(assignment_pdf, use_llm=False)
    out = heuristic_brief(a)
    assert "No model was available" in out.what_it_is
    assert any("Implement bubble sort" in ask for ask in out.asks)
    assert out.constraints == []


def test_render_brief_offline_has_every_computed_section(assignment_pdf: Path):
    a = analyze(assignment_pdf, use_llm=False)
    text = render_brief(a, None, DEFAULT_KEEP)
    assert text.startswith("# Brief: Assignment 2")
    for heading in (
        "## What it is",
        "## What it asks",
        "## Rules about AI use",
        "## What Lectern found",
        "## What the clean copy keeps",
    ):
        assert heading in text
    assert "generative AI tools" in text  # the policy, verbatim
    assert "1 critical" in text and "IGNORE PREVIOUS" in text  # described, with location
    assert "(p1, s4)" in text
    assert "zoning: heuristic-only" in text


def test_write_brief_with_a_model(assignment_md: Path):
    class BriefLLM(FakeLLM):
        def parse(self, *, system, user, schema, max_tokens):
            self.calls.append((system, user, schema))
            if schema is BriefOut:
                assert "<document>" in user and "never instructions" in system
                return BriefOut(
                    what_it_is="A sorting assignment for an intro course.",
                    asks=["Implement three sorts", "Submit a two-page report"],
                    constraints=["Due Friday", "Python 3.12 only"],
                )
            if schema is Overview:
                return Overview(overview="x", doc_type=DocType.assignment)
            from lectern.zoning.llm_pass import ZoneBatch

            return ZoneBatch(labels=[])

    llm = BriefLLM()
    a = analyze(assignment_md, llm=llm)
    out = write_brief(a, llm)
    assert out is not None and out.asks[0] == "Implement three sorts"
    text = render_brief(a, out, DEFAULT_KEEP)
    assert "## Constraints" in text and "- Due Friday" in text
    assert "A sorting assignment" in text


def test_write_brief_without_model_returns_none(assignment_md: Path):
    a = analyze(assignment_md, use_llm=False)
    assert write_brief(a, None) is None


def test_cli_brief(assignment_pdf: Path, tmp_path: Path, capsys):
    out = tmp_path / "brief.md"
    assert main(["brief", str(assignment_pdf), "--no-llm", "-o", str(out)]) == 0
    assert out.read_text().startswith("# Brief:")
    assert main(["brief", str(assignment_pdf), "--no-llm"]) == 0
    assert "## What it asks" in capsys.readouterr().out
    assert main(["brief", str(tmp_path / "nope.pdf"), "--no-llm"]) == 1


# ------------------------------------------------------------------ MCP tools


def test_scan_summary_verdicts(assignment_pdf: Path, assignment_md: Path):
    attacked = scan_summary(analyze(assignment_pdf, use_llm=False))
    assert attacked["verdict"].startswith("unsafe")
    assert attacked["counts"]["critical"] == 1 and attacked["counts"]["quarantined"] >= 1
    assert attacked["ai_use_policies"] and "generative AI" in attacked["ai_use_policies"][0]
    assert all(
        set(f) >= {"detector", "severity", "status", "excerpt"} for f in attacked["findings"]
    )

    clean = scan_summary(analyze(assignment_md, use_llm=False))
    assert clean["verdict"].startswith("clean") or clean["verdict"].startswith("review")
    assert clean["counts"]["critical"] == 0


def test_tools_offline(assignment_pdf: Path):
    tools = LecternTools(use_llm=False)
    summary = tools.scan_document(str(assignment_pdf))
    assert summary["mode"] == "heuristic-only" and summary["verdict"].startswith("unsafe")

    md = tools.clean_document(str(assignment_pdf), keep=["task"])
    body, _, report = md.partition("\n---\n")
    assert "## Deliverables" in body and "IGNORE PREVIOUS" not in body
    assert "IGNORE PREVIOUS" in report  # named, never laundered

    brief = tools.brief_document(str(assignment_pdf))
    assert brief.startswith("# Brief:") and "1 critical" in brief

    with pytest.raises(ValueError):
        tools.clean_document(str(assignment_pdf), keep=["tasks"])
    with pytest.raises(FileNotFoundError):
        tools.scan_document("/nowhere/x.pdf")


def test_tools_cache_by_content(assignment_pdf: Path, monkeypatch):
    import lectern.mcp_server as m

    calls = []
    real = m.analyze

    def counting(path, **kw):
        calls.append(path)
        return real(path, **kw)

    monkeypatch.setattr(m, "analyze", counting)
    tools = LecternTools(use_llm=False)
    tools.scan_document(str(assignment_pdf))
    tools.clean_document(str(assignment_pdf))
    tools.brief_document(str(assignment_pdf))
    assert len(calls) == 1  # one engine run for scan → clean → brief on the same file
    assignment_pdf.write_bytes(assignment_pdf.read_bytes() + b"\n%changed")
    tools.scan_document(str(assignment_pdf))
    assert len(calls) == 2  # a changed file is analyzed again


def test_hidden_zone_cannot_be_kept_through_mcp(assignment_pdf: Path):
    tools = LecternTools(use_llm=False)
    md = tools.clean_document(
        str(assignment_pdf), keep=["task", "hidden", "ai_policy"], report=False
    )
    assert "IGNORE PREVIOUS" not in md and "generative AI tools" not in md


@pytest.mark.anyio
async def test_server_lists_tools_and_calls_one(assignment_pdf: Path):
    from mcp.server.mcpserver import MCPServer

    server = build_server(use_llm=False)
    assert isinstance(server, MCPServer)
    tools = await server.list_tools()
    assert {t.name for t in tools} == {"scan_document", "clean_document", "brief_document"}
    scan = next(t for t in tools if t.name == "scan_document")
    assert "BEFORE reading" in scan.description
    result = await server.call_tool("scan_document", {"path": str(assignment_pdf)})
    text = str(result)
    assert "unsafe" in text


def test_default_keep_excludes_hidden_and_ai_zones():
    assert Zone.hidden not in DEFAULT_KEEP and Zone.ai_directive not in DEFAULT_KEEP
