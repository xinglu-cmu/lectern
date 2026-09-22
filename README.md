# Lectern

> **Read with receipts.** A provenance-first reading workspace: every claim shows its source, and every document is treated as untrusted input.

Lectern lets you build a corpus of arXiv papers and ask questions against it. Three things make it different from "chat with your PDF":

- **Verifiable citations** — every generated claim links to an exact quoted span in the source, machine-verified verbatim; unverifiable citations are visibly badged.
- **Plan checkpoints** — the agent proposes an editable plan (sub-questions, targets, constraints) *before* retrieving or writing; you edit or approve, then it executes.
- **Documents as untrusted input** — an ingestion-time screening layer detects hidden text, prompts embedded for AI consumption, and stated AI-use policies, and surfaces everything in a per-document trust report with human-review quarantine.

**Status:** week 1 of an 8-week build (design → deploy). See [docs/DESIGN.md](docs/DESIGN.md) for the full design and [docs/adr/](docs/adr/) for the key decisions.

## Stack

Next.js/TypeScript · Spring Boot (Java 21) · Python ingestion worker · PostgreSQL + pgvector · Redis · Cloudflare R2 · Claude API (`claude-sonnet-5` / `claude-haiku-4-5`) · Voyage embeddings · OpenTelemetry · GitHub Actions CI with eval gates

## Learning modules

Each subsystem is a self-contained deep-dive with its own eval and narrative:

| Module | The hard part it owns |
|---|---|
| Ingestion pipeline | idempotent job queue (`FOR UPDATE SKIP LOCKED`), retries, DLQ, arXiv-HTML-first parsing |
| Screening layer | hidden-text & prompt-injection detection, quarantine + human review, red-team eval |
| Retrieval & grounding | hybrid BM25 + vector search, span-level citation contract, verified-citation rate |
| Agent loop | hand-rolled resumable state machine with a human-editable plan checkpoint |
| Eval harness | gold Q&A with evidence spans + red-team corpus, both gating CI |
| Recommendation (phased) | event log → features → LightGBM ranking → diversity re-rank, offline time-split eval |
| Ops | tracing, structured logs, per-user cost budgets, load testing, < $20/mo footprint |

## Metrics

Filled in as they become real (week 6–8): P95 search latency, sustained RPS, verified-citation rate, retrieval recall@20, red-team precision/recall, eval trend, users served, cost/month.

## Development

```bash
make infra   # postgres (pgvector) + redis in docker
make up      # build & run api + worker in docker too
make web     # next.js dev server on :3000  (first: make web-install)
```

API: `GET :8080/api/health`. Worker logs a DB heartbeat. CI runs api (Maven verify), worker (ruff + pytest), and web (build) on every push; eval gates join in week 6.

## License

[MIT](LICENSE) © 2026 Xing Lu
