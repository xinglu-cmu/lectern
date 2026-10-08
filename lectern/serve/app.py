"""`lectern serve`: the local review UI (DESIGN v3 §7).

A FastAPI app bound to 127.0.0.1 that serves one page and a small JSON API:

    POST   /api/analyses              upload a file -> 202 {id}; analysis runs in a worker thread
    GET    /api/analyses              history
    GET    /api/analyses/{id}         status, analysis, review, exports
    GET    /api/analyses/{id}/events  server-sent events: status changes until ready/failed
    PUT    /api/analyses/{id}/review  keep/drop per zone and segment, zone overrides,
                                      finding statuses, policy acknowledgment
    POST   /api/analyses/{id}/exports {kind: clean|brief|json, dry_run?}  -> the text
    DELETE /api/analyses/{id}

Two rules carried over from the CLI: the review can only *reduce* what a model
or a clean copy sees (hidden / ai_directive / ai_policy can never be kept), and
an export is refused (409) while an AI-use policy statement is unacknowledged —
detect → disclose → respect, in a browser.

Loopback only: the server listens on 127.0.0.1 and refuses requests whose Host
or Origin is not local, so a page from elsewhere cannot drive it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from lectern.brief import render_brief, write_brief
from lectern.converters import supported_formats
from lectern.emit import NEVER_KEEP, clean_markdown
from lectern.models import Analysis, FindingStatus, Zone
from lectern.pipeline import analyze, make_llm
from lectern.serve.store import Store

log = logging.getLogger("lectern.serve")
STATIC = Path(__file__).parent / "static"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}


class ReviewIn(BaseModel):
    keep_zones: list[str] = Field(
        default_factory=lambda: ["task", "background", "example", "unknown"]
    )
    segments: dict[str, dict[str, Any]] = Field(default_factory=dict)
    findings: dict[str, str] = Field(default_factory=dict)
    policy_acknowledged: bool = False


class ExportIn(BaseModel):
    kind: str = Field(pattern="^(clean|brief|json)$")
    dry_run: bool = False
    report: bool = True


def _is_local(value: str | None) -> bool:
    if not value:
        return True
    host = value.split("://", 1)[-1].split("/", 1)[0]
    host = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    return host in LOCAL_HOSTS


def create_app(
    store: Store | None = None, *, use_llm: bool = True, model: str | None = None
) -> FastAPI:
    store = store or Store()
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lectern-analyze")
    app = FastAPI(title="Lectern", docs_url=None, redoc_url=None)
    app.state.store = store

    @app.middleware("http")
    async def loopback_only(request: Request, call_next):
        if not _is_local(request.headers.get("host")) or not _is_local(
            request.headers.get("origin")
        ):
            return JSONResponse(
                {"detail": "lectern serve answers local requests only"}, status_code=403
            )
        return await call_next(request)

    # -- page -----------------------------------------------------------------

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/static/{name}")
    def static(name: str):
        f = STATIC / name
        if not f.is_file() or ".." in name:
            raise HTTPException(404)
        return FileResponse(f)

    @app.get("/api/health")
    def health():
        return {"ok": True, "formats": sorted(supported_formats()), "llm": use_llm}

    # -- analyses -------------------------------------------------------------

    def _run(aid: str, path: Path) -> None:
        store.set_status(aid, "running")
        try:
            llm = make_llm(model) if use_llm and model else (make_llm() if use_llm else None)
            analysis = analyze(path, use_llm=llm is not None, llm=llm)
            store.set_result(aid, json.loads(analysis.model_dump_json()), analysis.mode)
        except Exception as exc:  # the file broke a converter: keep the row, say why
            log.exception("analysis %s failed", aid)
            store.set_status(aid, "failed", error=f"{exc.__class__.__name__}: {exc}")

    @app.post("/api/analyses", status_code=202)
    async def create(file: UploadFile):
        name = Path(file.filename or "upload").name
        fmt = Path(name).suffix.lower().lstrip(".")
        if fmt not in supported_formats():
            raise HTTPException(415, f"unsupported format '.{fmt}'")
        data = await file.read()
        if not data:
            raise HTTPException(400, "empty file")
        row = store.create(name, data, hashlib.sha256(data).hexdigest())
        pool.submit(_run, row.id, Path(row.stored_path))
        return {"id": row.id, "status": row.status}

    @app.get("/api/analyses")
    def list_analyses():
        return store.list()

    @app.get("/api/analyses/{aid}")
    def get_analysis(aid: str):
        row = store.get(aid)
        if row is None:
            raise HTTPException(404)
        return {
            "id": row.id,
            "filename": row.filename,
            "created_at": row.created_at,
            "status": row.status,
            "mode": row.mode,
            "error": row.error,
            "analysis": row.analysis,
            "review": store.get_review(aid),
            "exports": store.exports(aid),
        }

    @app.get("/api/analyses/{aid}/events")
    def events(aid: str):
        if store.get(aid) is None:
            raise HTTPException(404)

        def gen():
            last = None
            deadline = time.time() + 600
            while time.time() < deadline:
                row = store.get(aid)
                if row is None:
                    break
                if row.status != last:
                    last = row.status
                    payload = json.dumps({"status": row.status, "error": row.error})
                    yield f"event: status\ndata: {payload}\n\n"
                if row.status in ("ready", "failed"):
                    break
                time.sleep(0.5)

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.delete("/api/analyses/{aid}", status_code=204)
    def delete(aid: str):
        if not store.delete(aid):
            raise HTTPException(404)
        return PlainTextResponse("", status_code=204)

    # -- review and export ----------------------------------------------------

    @app.put("/api/analyses/{aid}/review")
    def put_review(aid: str, review: ReviewIn):
        if store.get(aid) is None:
            raise HTTPException(404)
        bad = [z for z in review.keep_zones if z not in {x.value for x in Zone}]
        if bad:
            raise HTTPException(422, f"unknown zone(s): {', '.join(bad)}")
        clean = review.model_dump()
        clean["keep_zones"] = [z for z in review.keep_zones if Zone(z) not in NEVER_KEEP]
        store.put_review(aid, clean)
        return clean

    @app.post("/api/analyses/{aid}/exports")
    def export(aid: str, body: ExportIn):
        row = store.get(aid)
        if row is None:
            raise HTTPException(404)
        if row.status != "ready" or row.analysis is None:
            raise HTTPException(409, f"analysis is {row.status}")
        review = store.get_review(aid)
        analysis = apply_review(Analysis.model_validate(row.analysis), review)
        if (
            body.kind != "json"
            and not body.dry_run  # a preview stays on screen; the gate is for copies that leave
            and any(f.kind == "ai_policy" for f in analysis.findings)
        ):
            if not review.get("policy_acknowledged"):
                raise HTTPException(
                    409,
                    "this document states a rule about AI use; acknowledge it before exporting",
                )
        keep = {Zone(z) for z in review["keep_zones"]} - NEVER_KEEP
        if body.kind == "clean":
            text = clean_markdown(analysis, keep, report=body.report)
            media = "text/markdown"
        elif body.kind == "brief":
            llm = make_llm() if use_llm and analysis.mode == "llm" else None
            text = render_brief(analysis, write_brief(analysis, llm), keep)
            media = "text/markdown"
        else:
            text = analysis.model_dump_json(indent=2)
            media = "application/json"
        if not body.dry_run:
            store.record_export(aid, body.kind, len(text.encode()))
        return PlainTextResponse(text, media_type=media)

    return app


def apply_review(analysis: Analysis, review: dict[str, Any]) -> Analysis:
    """The user's decisions, applied to a copy: zone overrides, per-segment keep/drop (expressed
    by moving a dropped segment to `structure` and a kept one to `task` when its zone is not
    kept), finding statuses. Hidden and AI zones cannot be overridden."""
    a = analysis.model_copy(deep=True)
    keep = {Zone(z) for z in review.get("keep_zones", [])} - NEVER_KEEP
    for seg in a.segments:
        decision = review.get("segments", {}).get(seg.id) or {}
        if seg.zone in NEVER_KEEP:
            continue
        zone = decision.get("zone")
        if zone and zone in {z.value for z in Zone} and Zone(zone) not in NEVER_KEEP:
            seg.zone = Zone(zone)
            seg.signals.append("review:zone_override")
        if decision.get("keep") is True and seg.zone not in keep:
            seg.zone = next(iter(keep)) if keep else Zone.task
            seg.signals.append("review:kept")
        elif decision.get("keep") is False and seg.zone in keep:
            seg.zone = Zone.structure if Zone.structure not in keep else Zone.unknown
            seg.signals.append("review:dropped")
    for idx, status in review.get("findings", {}).items():
        try:
            f = a.findings[int(idx)]
        except (ValueError, IndexError):
            continue
        if f.status is FindingStatus.quarantined:
            continue  # hidden stays hidden; a person can dismiss a warning, not a quarantine
        if status in ("open", "dismissed"):
            f.status = FindingStatus(status)
    return a


def main(
    port: int = 8765, *, open_browser: bool = True, use_llm: bool = True, model: str | None = None
) -> None:
    import threading
    import webbrowser

    import uvicorn

    app = create_app(use_llm=use_llm, model=model)
    url = f"http://127.0.0.1:{port}/"
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"lectern serve: {url}  (local only; Ctrl-C to stop)")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
