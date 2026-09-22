# ADR-007: Pivot — from paper-reading workspace to document screening & distillation tool

**Status:** accepted · 2026-09-23 · supersedes ADR-001 (in part), ADR-005, ADR-006; ADR-003's agent loop is cut from v1

## Context

One week in (scaffold shipped, no product code yet), the product thesis sharpened. v1's plan — a paper-reading workspace with cited Q&A — served a narrow audience, and its most differentiated component was never the Q&A: it was the ingestion-time **screening layer** treating documents as untrusted input, plus the human checkpoint. Meanwhile the daily, universal problem sits one step earlier than reading: everyone feeds documents to AI tools with no high-level view of what is inside — how much is actual task vs boilerplate, and whether anything (visible or hidden) is addressed to the AI itself. Adjacent open-source projects (MarkItDown, Docling) solve format conversion only; injection defense exists as API middleware, not as a document tool with human review. The intersection — convert + functionally zone + screen + human-select + emit clean Markdown — is unoccupied.

## Decision

Refocus Lectern on that intersection: **one engine, two front doors** — a Python package/CLI (`scan`, `clean`) as the everyday open-source tool, and the web app as an upload → analysis → interactive selection → export flow. Full detail in DESIGN v2.

Cut from v1: the Q&A agent loop, span-level citation contract, hybrid retrieval, embeddings/pgvector, arXiv-centricity, GROBID. Kept unchanged: the screening detector suite and its red-team eval, the Postgres job queue (ADR-004), the service split (ADR-002, now API + worker sharing the engine package), auth/budgets/observability designs, deploy plan, week-1 scaffold. Parked: the recommendation module (ADR-006) — the new product has no recommendation surface; the event log stays, and the MLE-narrative slot is taken by a better-fitting phase-2 candidate (distilling the zoning classifier into a local model). Research instrumentation survives in the selection UI's telemetry but is descoped from v1 planning.

## Rationale

- **Timing:** week 1 was deliberately product-agnostic infrastructure; pivoting now costs ~nothing, pivoting after the agent/retrieval build would cost a month.
- **Dogfooding and adoption:** the author will use this daily; a CLI reaches users organically (PyPI/GitHub) in a way a niche web app cannot.
- **The differentiator becomes the product:** "documents are untrusted input" was v1's most defensible idea; v2 makes it the whole identity instead of a feature.
- **Leaner risk profile:** parsing-fidelity requirements drop (output is Markdown for AI consumption, not character-anchored citations), so arbitrary uploads move from tarpit to core; LLM spend drops to Haiku-only; evals shift toward deterministic suites.
- **Both résumé narratives strengthen:** open-source tool with measured detection/zoning numbers + the same full-stack rigor (queue, SSE pipeline, eval-gated CI, cost accounting).

## Consequences

- DESIGN.md rewritten (v2); ~40% of the seeded issues closed as obsolete, the rest re-scoped/re-milestoned; milestones 2–8 re-themed on the same dates.
- The "human checkpoint" idea survives translated: plan-approval → selection/review UI (same detect → disclose → decide design language).
- ADR-001's scenario analysis remains a faithful record of why B beat A/C at the time; this ADR records why B then evolved.

## Revisit when

If zoning accuracy or detector value disappoints against the labeled set by week 4, the fallback is not a return to Q&A but a narrowing to the strongest layer (screening-only, `scan --fail-on` as a CI/ingest gate for agent pipelines).
