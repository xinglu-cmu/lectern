# ADR-004: Job queue in Postgres (FOR UPDATE SKIP LOCKED), Redis kept for rate-limit/cache

**Status:** accepted · 2026-09-22

## Context

The ingestion pipeline needs a queue between the Java API (producer) and the Python worker (consumer): per-stage jobs, retries with backoff, dead-lettering, idempotency. Candidates: Redis Streams/BullMQ-style broker, or a Postgres job table claimed with `SELECT … FOR UPDATE SKIP LOCKED`.

## Decision

Postgres-backed job table (`ingest_jobs`), claimed with `FOR UPDATE SKIP LOCKED`; visibility timeout via `locked_at` reclaim; `attempts` + `run_after` backoff; `dead` status as DLQ. Redis remains in the stack only for token-bucket rate limiting and short-lived response caching.

## Rationale

- Job state transitions and the data they mutate (`documents.status`, zones, chunks) commit in **one transaction** — no dual-write or outbox machinery between a broker and the DB.
- Throughput requirements are tiny (papers/day, not events/sec); SKIP LOCKED handles orders of magnitude more than needed.
- One less stateful system to operate correctly on a $20/month footprint; BullMQ is also Node-centric, which fits neither Java nor Python here.
- Boring-tech tradeoff made explicitly — and the reasoning is itself interview material (compare against Redis Streams consumer groups honestly).

## Consequences

- Polling consumer (short interval + jitter) instead of push; acceptable at this scale.
- Queue depth and reclaim metrics come from SQL, exported to the metrics pipeline.

## Revisit when

Sustained job throughput or fan-out grows beyond what polite polling handles (~tens/sec), or a second consumer service appears with competing latency needs.
