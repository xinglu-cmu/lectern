"""`--local`: a model served on this machine, driven through a fake Ollama endpoint."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from lectern.llm import LLMUnavailable, LocalLLM
from lectern.models import DocType, Overview
from lectern.pipeline import analyze, make_llm
from lectern.zoning.llm_pass import ZoneBatch


class FakeOllama(BaseHTTPRequestHandler):
    """Answers /api/chat with a canned reply chosen by the schema it was sent."""

    replies: dict[str, object] = {}
    requests: list[dict] = []
    status = 200
    done_reason = "stop"

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        FakeOllama.requests.append(body)
        if FakeOllama.status != 200:
            self.send_response(FakeOllama.status)
            self.end_headers()
            return
        title = body["format"].get("title", "")
        reply = FakeOllama.replies.get(title, "")
        content = reply if isinstance(reply, str) else json.dumps(reply)
        out = {
            "message": {"role": "assistant", "content": content},
            "done_reason": FakeOllama.done_reason,
            "prompt_eval_count": 120,
            "eval_count": 30,
        }
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # quiet
        pass


@pytest.fixture
def ollama():
    FakeOllama.replies = {}
    FakeOllama.requests = []
    FakeOllama.status = 200
    FakeOllama.done_reason = "stop"
    srv = HTTPServer(("127.0.0.1", 0), FakeOllama)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_local_llm_parses_schema_constrained_reply(ollama):
    FakeOllama.replies = {"Overview": {"overview": "An assignment.", "doc_type": "assignment"}}
    llm = LocalLLM("tiny", base_url=ollama)
    out = llm.parse(system="s", user="u", schema=Overview, max_tokens=100)
    assert out == Overview(overview="An assignment.", doc_type=DocType.assignment)
    req = FakeOllama.requests[0]
    assert req["model"] == "tiny" and req["format"]["title"] == "Overview"
    assert req["options"] == {"temperature": 0, "num_predict": 100}
    assert [m["role"] for m in req["messages"]] == ["system", "user"]
    assert llm.model == "ollama:tiny" and llm.usage.calls == 1
    assert llm.usage.input_tokens == 120 and llm.usage.cost_usd == 0.0


def test_local_llm_bad_replies_keep_heuristics(ollama):
    llm = LocalLLM("tiny", base_url=ollama)
    FakeOllama.replies = {"Overview": "not json at all"}
    assert llm.parse(system="s", user="u", schema=Overview, max_tokens=10) is None
    FakeOllama.replies = {"Overview": {"overview": "x", "doc_type": "not-a-type"}}
    assert llm.parse(system="s", user="u", schema=Overview, max_tokens=10) is None
    FakeOllama.replies = {"Overview": {"overview": "x", "doc_type": "paper"}}
    FakeOllama.done_reason = "length"
    assert llm.parse(system="s", user="u", schema=Overview, max_tokens=10) is None
    assert llm.usage.failures == 3


def test_local_llm_unreachable_or_missing_model(ollama):
    with pytest.raises(LLMUnavailable):
        LocalLLM("tiny", base_url="http://127.0.0.1:9").parse(
            system="s", user="u", schema=Overview, max_tokens=10
        )
    FakeOllama.status = 404
    with pytest.raises(LLMUnavailable, match="ollama pull"):
        LocalLLM("tiny", base_url=ollama).parse(
            system="s", user="u", schema=Overview, max_tokens=10
        )
    FakeOllama.status = 500
    assert (
        LocalLLM("tiny", base_url=ollama).parse(
            system="s", user="u", schema=Overview, max_tokens=10
        )
        is None
    )


def test_make_llm_prefers_local_when_asked(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert make_llm() is None
    assert isinstance(make_llm(local=True), LocalLLM)
    assert make_llm(local="qwen2.5:3b").model == "ollama:qwen2.5:3b"
    monkeypatch.setenv("LECTERN_LOCAL_MODEL", "phi4")
    assert make_llm(local=True).model == "ollama:phi4"


def test_pipeline_with_a_local_model(ollama, assignment_md: Path, monkeypatch):
    monkeypatch.setenv("LECTERN_LOCAL_URL", ollama)
    FakeOllama.replies = {
        "ZoneBatch": {"labels": []},
        "Overview": {"overview": "A sorting assignment.", "doc_type": "assignment"},
        "D1Verdicts": {"verdicts": []},
    }
    a = analyze(assignment_md, local="tiny")
    assert a.mode == "llm" and a.llm is not None and a.llm.model == "ollama:tiny"
    assert a.overview is not None and a.overview.doc_type is DocType.assignment
    assert not any("ANTHROPIC_API_KEY" in w for w in a.warnings)
    assert any(r["format"]["title"] == "ZoneBatch" for r in FakeOllama.requests)


def test_pipeline_degrades_when_local_model_is_down(assignment_md: Path, monkeypatch):
    monkeypatch.setenv("LECTERN_LOCAL_URL", "http://127.0.0.1:9")
    a = analyze(assignment_md, local=True)
    assert a.mode == "heuristic-only"
    assert any("cannot reach a local model" in w for w in a.warnings)


def test_zone_schema_round_trips_through_json_schema():
    schema = ZoneBatch.model_json_schema()
    assert schema["title"] == "ZoneBatch"
    assert "hidden" not in json.dumps(schema)
