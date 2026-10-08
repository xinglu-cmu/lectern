"""`lectern serve`: the local review API, the store, the review rules, the loopback guard."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lectern.serve.app import apply_review, create_app
from lectern.serve.store import Store


@pytest.fixture
def client(tmp_path: Path):
    store = Store(tmp_path / "home")
    app = create_app(store, use_llm=False)
    with TestClient(
        app, base_url="http://127.0.0.1"
    ) as c:  # the loopback guard rejects "testserver"
        yield c


def _upload(client: TestClient, path: Path) -> str:
    with open(path, "rb") as fh:
        r = client.post(
            "/api/analyses", files={"file": (path.name, fh, "application/octet-stream")}
        )
    assert r.status_code == 202, r.text
    aid = r.json()["id"]
    for _ in range(100):
        d = client.get(f"/api/analyses/{aid}").json()
        if d["status"] in ("ready", "failed"):
            break
        time.sleep(0.05)
    assert d["status"] == "ready", d
    return aid


def test_health_and_page(client: TestClient):
    assert client.get("/api/health").json()["ok"] is True
    assert "Lectern" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/../pyproject.toml").status_code in (404, 400)


def test_upload_analyze_review_export_delete(client: TestClient, assignment_pdf: Path):
    aid = _upload(client, assignment_pdf)
    d = client.get(f"/api/analyses/{aid}").json()
    a = d["analysis"]
    assert a["mode"] == "heuristic-only" and any(s["zone"] == "hidden" for s in a["segments"])
    assert d["review"]["policy_acknowledged"] is False

    # the policy banner gate: exports refused until acknowledged (json is allowed)
    r = client.post(f"/api/analyses/{aid}/exports", json={"kind": "clean"})
    assert r.status_code == 409 and "acknowledge" in r.json()["detail"]
    assert client.post(f"/api/analyses/{aid}/exports", json={"kind": "json"}).status_code == 200
    preview = client.post(
        f"/api/analyses/{aid}/exports", json={"kind": "clean", "dry_run": True, "report": False}
    )
    assert preview.status_code == 200  # previews stay on screen; only copies that leave are gated

    review = d["review"]
    review["policy_acknowledged"] = True
    review["keep_zones"] = ["task", "hidden", "ai_policy"]  # never-keep zones are dropped silently
    r = client.put(f"/api/analyses/{aid}/review", json=review)
    assert r.status_code == 200 and r.json()["keep_zones"] == ["task"]

    r = client.post(f"/api/analyses/{aid}/exports", json={"kind": "clean"})
    assert r.status_code == 200
    body, _, report = r.text.partition("\n---\n")
    assert (
        "## Deliverables" in body and "IGNORE PREVIOUS" not in body and "IGNORE PREVIOUS" in report
    )
    r = client.post(f"/api/analyses/{aid}/exports", json={"kind": "brief"})
    assert r.status_code == 200 and r.text.startswith("# Brief:")
    r = client.post(
        f"/api/analyses/{aid}/exports", json={"kind": "clean", "dry_run": True, "report": False}
    )
    assert r.status_code == 200 and "removal report" not in r.text

    d = client.get(f"/api/analyses/{aid}").json()
    assert [x["kind"] for x in d["exports"]] == ["json", "clean", "brief"]  # dry runs not recorded
    assert any(row["id"] == aid for row in client.get("/api/analyses").json())

    assert client.delete(f"/api/analyses/{aid}").status_code == 204
    assert client.get(f"/api/analyses/{aid}").status_code == 404
    assert client.delete(f"/api/analyses/{aid}").status_code == 404


def test_events_stream_ends_at_ready(client: TestClient, assignment_md: Path):
    aid = _upload(client, assignment_md)
    with client.stream("GET", f"/api/analyses/{aid}/events") as r:
        text = "".join(r.iter_text())
    assert "event: status" in text and '"ready"' in text


def test_rejects_unsupported_and_empty(client: TestClient):
    r = client.post("/api/analyses", files={"file": ("x.xyz", b"hi", "application/octet-stream")})
    assert r.status_code == 415
    r = client.post("/api/analyses", files={"file": ("x.md", b"", "text/markdown")})
    assert r.status_code == 400


def test_failed_analysis_is_reported(client: TestClient, tmp_path: Path):
    bad = tmp_path / "broken.pdf"
    bad.write_bytes(b"%PDF-1.4 not really a pdf")
    with open(bad, "rb") as fh:
        aid = client.post(
            "/api/analyses", files={"file": ("broken.pdf", fh, "application/pdf")}
        ).json()["id"]
    for _ in range(100):
        d = client.get(f"/api/analyses/{aid}").json()
        if d["status"] in ("ready", "failed"):
            break
        time.sleep(0.05)
    assert d["status"] == "failed" and d["error"]
    assert client.post(f"/api/analyses/{aid}/exports", json={"kind": "json"}).status_code == 409


def test_loopback_guard(tmp_path: Path):
    app = create_app(Store(tmp_path / "h"), use_llm=False)
    with TestClient(app, base_url="http://evil.example") as c:
        assert c.get("/api/health").status_code == 403
    with TestClient(app, base_url="http://localhost:8765") as c:
        assert c.get("/api/health", headers={"origin": "http://attacker.test"}).status_code == 403
        assert c.get("/api/health", headers={"origin": "http://127.0.0.1:8765"}).status_code == 200


def test_apply_review_rules(assignment_pdf: Path):
    from lectern.models import FindingStatus, Zone
    from lectern.pipeline import analyze

    a = analyze(assignment_pdf, use_llm=False)
    hidden = next(s for s in a.segments if s.zone is Zone.hidden)
    task = [s for s in a.segments if s.zone is Zone.task and s.id != "s2"][-1]
    quarantined_idx = next(
        i for i, f in enumerate(a.findings) if f.status is FindingStatus.quarantined
    )
    policy_idx = next(i for i, f in enumerate(a.findings) if f.kind == "ai_policy")
    review = {
        "keep_zones": ["task", "background"],
        "segments": {
            hidden.id: {"keep": True, "zone": "task"},  # must be ignored
            task.id: {"keep": False},
            "s2": {"zone": "example"},
        },
        "findings": {str(quarantined_idx): "dismissed", str(policy_idx): "dismissed"},
        "policy_acknowledged": True,
    }
    b = apply_review(a, review)
    assert b.segment(hidden.id).zone is Zone.hidden
    assert (
        b.segment(task.id).zone is Zone.structure and "review:dropped" in b.segment(task.id).signals
    )
    assert b.segment("s2").zone is Zone.example
    assert b.findings[quarantined_idx].status is FindingStatus.quarantined  # cannot dismiss hidden
    assert b.findings[policy_idx].status is FindingStatus.dismissed
    assert a.segment(task.id).zone is Zone.task  # the original is untouched


def test_store_roundtrip(tmp_path: Path):
    s = Store(tmp_path / "h")
    row = s.create("a.md", b"# hi", "abc" * 20)
    assert row.status == "queued" and Path(row.stored_path).exists()
    s.set_result(row.id, {"x": 1}, "heuristic-only")
    assert s.get(row.id).analysis == {"x": 1} and s.get(row.id).status == "ready"
    s.put_review(
        row.id,
        {"keep_zones": ["task"], "segments": {}, "findings": {}, "policy_acknowledged": True},
    )
    assert s.get_review(row.id)["keep_zones"] == ["task"]
    s.record_export(row.id, "clean", 10)
    assert s.exports(row.id)[0]["kind"] == "clean"
    assert s.delete(row.id) and s.get(row.id) is None and not Path(row.stored_path).exists()
    assert s.get_review("missing")["policy_acknowledged"] is False
