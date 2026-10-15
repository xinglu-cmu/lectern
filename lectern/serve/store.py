"""Local history for `lectern serve`: one SQLite file under `~/.lectern/`.

What is kept: the uploaded file (so an analysis can be re-run), the analysis as
JSON, the user's review decisions (keep/drop per segment, zone overrides,
finding statuses, whether the policy banner was acknowledged) and a record of
exports. Delete removes the row, the review and the stored file. The file is
the user's: copy it, inspect it with any SQLite tool, or delete it.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,            -- queued | running | ready | failed
    mode TEXT,
    error TEXT,
    analysis_json TEXT
);
CREATE TABLE IF NOT EXISTS reviews (
    analysis_id TEXT PRIMARY KEY REFERENCES analyses(id) ON DELETE CASCADE,
    review_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exports (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,              -- clean | brief | json
    created_at TEXT NOT NULL,
    bytes INTEGER NOT NULL
);
"""

EMPTY_REVIEW: dict[str, Any] = {
    "keep_zones": ["task", "background", "example", "unknown"],
    "segments": {},  # segment id -> {"keep": bool | None, "zone": str | None}
    "findings": {},  # finding index (str) -> "open" | "dismissed" | "quarantined"
    "policy_acknowledged": False,
}


def home() -> Path:
    return Path(os.environ.get("LECTERN_HOME", Path.home() / ".lectern")).expanduser()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Row:
    id: str
    filename: str
    sha256: str
    stored_path: str
    created_at: str
    status: str
    mode: str | None
    error: str | None
    analysis: dict | None


class Store:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or home()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "uploads").mkdir(exist_ok=True)
        self.path = self.root / "lectern.sqlite"
        with self._conn() as con:
            con.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10)
        con.execute("PRAGMA foreign_keys = ON")
        con.row_factory = sqlite3.Row
        return con

    # -- analyses -------------------------------------------------------------

    def create(self, filename: str, data: bytes, sha256: str) -> Row:
        aid = uuid.uuid4().hex[:12]
        suffix = Path(filename).suffix.lower() or ".bin"
        stored = self.root / "uploads" / f"{sha256[:16]}{suffix}"
        stored.write_bytes(data)
        with self._conn() as con:
            con.execute(
                "INSERT INTO analyses (id, filename, sha256, stored_path, created_at, status) "
                "VALUES (?, ?, ?, ?, ?, 'queued')",
                (aid, filename, sha256, str(stored), _now()),
            )
        return self.get(aid)  # type: ignore[return-value]

    def set_status(self, aid: str, status: str, *, error: str | None = None) -> None:
        with self._conn() as con:
            con.execute(
                "UPDATE analyses SET status = ?, error = ? WHERE id = ?", (status, error, aid)
            )

    def set_result(self, aid: str, analysis: dict, mode: str) -> None:
        with self._conn() as con:
            con.execute(
                "UPDATE analyses SET status = 'ready', mode = ?, analysis_json = ?, error = NULL "
                "WHERE id = ?",
                (mode, json.dumps(analysis), aid),
            )

    def get(self, aid: str) -> Row | None:
        with self._conn() as con:
            r = con.execute("SELECT * FROM analyses WHERE id = ?", (aid,)).fetchone()
        if r is None:
            return None
        return Row(
            id=r["id"],
            filename=r["filename"],
            sha256=r["sha256"],
            stored_path=r["stored_path"],
            created_at=r["created_at"],
            status=r["status"],
            mode=r["mode"],
            error=r["error"],
            analysis=json.loads(r["analysis_json"]) if r["analysis_json"] else None,
        )

    def list(self) -> list[dict[str, Any]]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT id, filename, created_at, status, mode, error FROM analyses "
                "ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, aid: str) -> bool:
        row = self.get(aid)
        if row is None:
            return False
        with self._conn() as con:
            con.execute("DELETE FROM analyses WHERE id = ?", (aid,))
            still_used = con.execute(
                "SELECT 1 FROM analyses WHERE stored_path = ? LIMIT 1", (row.stored_path,)
            ).fetchone()
        if not still_used:
            Path(row.stored_path).unlink(missing_ok=True)
        return True

    # -- reviews --------------------------------------------------------------

    def get_review(self, aid: str) -> dict[str, Any]:
        with self._conn() as con:
            r = con.execute(
                "SELECT review_json FROM reviews WHERE analysis_id = ?", (aid,)
            ).fetchone()
        if r is None:
            return json.loads(json.dumps(EMPTY_REVIEW))
        return json.loads(r["review_json"])

    def put_review(self, aid: str, review: dict[str, Any]) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT INTO reviews (analysis_id, review_json, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(analysis_id) DO UPDATE SET review_json = excluded.review_json, "
                "updated_at = excluded.updated_at",
                (aid, json.dumps(review), _now()),
            )

    # -- exports --------------------------------------------------------------

    def record_export(self, aid: str, kind: str, size: int) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT INTO exports (id, analysis_id, kind, created_at, bytes) "
                "VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex[:12], aid, kind, _now(), size),
            )

    def exports(self, aid: str) -> list[dict[str, Any]]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT kind, created_at, bytes FROM exports WHERE analysis_id = ? "
                "ORDER BY created_at",
                (aid,),
            ).fetchall()
        return [dict(r) for r in rows]
