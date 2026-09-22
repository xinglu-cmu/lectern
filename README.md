# Lectern

> **Know what your AI is reading.** Scan any document for hidden prompts and AI-directed content, see it zoned by what each part *is* — task, background, boilerplate — choose what survives, and get clean Markdown ready for any AI tool.

[![ci](https://github.com/xinglu-cmu/lectern/actions/workflows/ci.yml/badge.svg)](https://github.com/xinglu-cmu/lectern/actions/workflows/ci.yml) · [project board](https://github.com/users/xinglu-cmu/projects/1) · [milestones](https://github.com/xinglu-cmu/lectern/milestones) · [design doc](docs/DESIGN.md)

Every AI workflow starts by feeding a document to a model that dives straight in. Nobody first asks: *what is this document, which parts are the actual work, and is anything in here — visible or hidden — trying to steer the AI?* Documents carry boilerplate that wastes context, stated AI policies, and sometimes literal hidden prompt injections (white text, 1pt fonts, metadata payloads). Lectern is the missing step in between:

```bash
lectern scan  assignment.pdf                      # overview + zone map + findings
lectern clean assignment.pdf -o clean.md \
              --keep task,background              # distilled Markdown + removal report
```

- **Screening** — detects invisible text, encoding tricks, metadata payloads, and AI-directed instructions; quarantines hidden content with a human-review path. *Detect → disclose → respect*: nothing is silently dropped, and instructions found inside documents are never obeyed.
- **Functional zoning** — segments classified as `task` / `background` / `structure` / `example` / `ai_directive` / `ai_policy` / `hidden`, with confidence, via heuristics + an optional LLM pass.
- **You choose** — keep/drop by zone (CLI flags or the web review UI), then export clean Markdown with a report of what was removed and why.
- **Works offline** — conversion, heuristic zoning, all static detectors, and clean output run with `--no-llm`; an API key upgrades zoning quality and adds the overview.

A web app (upload → async pipeline → interactive review → export) ships alongside the CLI — same engine, two front doors.

**Status:** week 2 of an 8-week build. The [design doc](docs/DESIGN.md) (v2) and [ADRs](docs/adr/) — including [ADR-007](docs/adr/ADR-007-pivot-to-screening-tool.md), the pivot record — explain every decision.

## Stack

Python engine + CLI · Next.js/TypeScript web · Spring Boot (Java 21) API · PostgreSQL (`FOR UPDATE SKIP LOCKED` job queue) · Redis · Cloudflare R2 · Claude API (`claude-haiku-4-5`) · OpenTelemetry · CI gated by eval thresholds

## Learning modules

Each subsystem is a self-contained deep-dive with its own eval and narrative:

| Module | The hard part it owns |
|---|---|
| Engine & zoning | conversion interface over MarkItDown/Docling, functional-role classification, heuristic+LLM two-pass |
| Screening layer | hidden-text & injection detection over PDF/HTML/DOCX, quarantine + human review |
| CLI | scan/clean UX, offline mode, JSON output, CI-gate exit codes |
| Async pipeline | idempotent Postgres job queue, retries, DLQ, SSE progress |
| Web review UI | zone toggles, findings review, selection → export |
| Evals | red-team corpus (precision/recall per technique), labeled zoning set (macro-F1 + ablation), conversion snapshots |
| Ops | tracing, cost accounting per document, budgets, load testing, < $20/mo footprint |

## Metrics

Filled in as they become real (weeks 3–8): red-team detection precision/recall per technique, zoning macro-F1 (heuristic vs +LLM ablation), pipeline throughput, P95 API latency, cost per document, installs/users.

## Development

```bash
make infra   # postgres + redis in docker
make up      # build & run api + worker in docker too
make web     # next.js dev server on :3000  (first: make web-install)
```

Engine/CLI (from week 2): `pip install -e "./worker[dev]"` then `lectern scan …`. CI runs api (Maven verify), worker (ruff + pytest), and web (build) on every push; eval gates join in week 6.

## License

[MIT](LICENSE) © 2026 Xing Lu
