# ADR-002: Spring Boot core API + Python ingestion worker

**Status:** accepted · 2026-09-22

## Context

Solo developer, 8 weeks. The default guidance for that budget is a single service. But the system has two workload shapes: interactive request/response (auth, CRUD, agent runs, SSE) and asynchronous batch document processing (fetch, parse, screen, chunk, embed). The developer is strong in Java and TypeScript; big-tech interview signal favors a "serious backend language". Python owns the document-parsing and (later) ML ecosystem.

## Decision

Two services: a Spring Boot (Java 21, Boot 3.5, virtual threads) API owning auth, domain CRUD, the agent loop, SSE, budgets; and a Python worker owning the ingestion pipeline stages and, in rec-module phase 2, batch scoring. They share PostgreSQL; jobs flow through a Postgres-backed queue (ADR-004). GROBID runs as a third, off-the-shelf container (we operate it, we don't write it).

## Rationale

The split is genuinely needed, not decorative: ingestion is naturally async with different failure/retry/scaling characteristics, and forcing PDF/HTML parsing into the JVM (or the agent loop into Python) fights both ecosystems. The queue boundary between the two is also the project's distributed-systems story (idempotency, retries, DLQ), which connects to 18-749 coursework.

## Consequences

- Two deployables + shared schema; Flyway migrations live with the API, the worker treats the schema as read/write contract.
- One language boundary to keep typed: job payloads and status enums defined once (SQL + mirrored constants, checked by an integration test).
- Fallback recorded: if Spring velocity is bad by end of week 2, cut product scope — never switch stacks mid-build.

## Revisit when

If the worker's job volume stays trivial and the split costs more than it teaches, fold phases into the API and keep the worker for parsing only (unlikely; parsing alone justifies it).
