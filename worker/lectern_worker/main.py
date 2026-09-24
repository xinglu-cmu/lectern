"""Week-1 hello worker: prove DB connectivity and the poll-loop shape.

From week 4 the worker claims jobs from `ingest_jobs` with FOR UPDATE SKIP
LOCKED (ADR-004) and runs the engine stages on them (load -> segment ->
screen -> zone -> summarize -> emit, DESIGN §4). This loop already has the
structure they will use: connect, poll, backoff on failure, exit cleanly.
"""

import logging
import os
import sys
import time

import psycopg

log = logging.getLogger("lectern.worker")

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://lectern:lectern@localhost:5432/lectern"
)
POLL_INTERVAL_S = float(os.environ.get("POLL_INTERVAL_S", "10"))


def backoff_seconds(attempt: int, base: float = 1.0, cap: float = 60.0) -> float:
    """Exponential backoff with a ceiling; shared by the connect loop and, later, job retries."""
    return min(cap, base * (2**attempt))


def read_schema_version(conn: psycopg.Connection) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM app_meta WHERE key = 'schema_version'")
        row = cur.fetchone()
    return row[0] if row else "unknown"


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    attempt = 0
    try:
        while True:
            try:
                with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
                    schema = read_schema_version(conn)
                attempt = 0  # reset only after a fully successful poll
                log.info("worker alive, db schema=%s", schema)
            except (psycopg.OperationalError, psycopg.errors.UndefinedTable) as exc:
                # Unreachable database, or reachable but not yet migrated: the api
                # owns the schema (Flyway, ADR-002) and may start after us.
                wait = backoff_seconds(attempt)
                attempt += 1
                reason = str(exc).splitlines()[0]
                log.warning("db not ready (%s); retrying in %.0fs", reason, wait)
                time.sleep(wait)
                continue
            time.sleep(POLL_INTERVAL_S)
    except KeyboardInterrupt:
        log.info("worker shutting down")
        return 0


if __name__ == "__main__":
    sys.exit(main())
