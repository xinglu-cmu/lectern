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

**Status:** week 3 of an 8-week build — the CLI is feature-complete for v1: `lectern scan` and `lectern clean` work end to end on PDF / DOCX / HTML / Markdown, offline or with Claude Haiku; hidden-text detectors H1–H6 quarantine invisible content; the red-team suite gates every PR. The web app starts in week 4. The [design doc](docs/DESIGN.md) (v2) and [ADRs](docs/adr/) — including [ADR-007](docs/adr/ADR-007-pivot-to-screening-tool.md), the pivot record — explain every decision.

## Stack

Python engine + CLI · Next.js/TypeScript web · Spring Boot (Java 21) API · PostgreSQL (`FOR UPDATE SKIP LOCKED` job queue) · Redis · Cloudflare R2 · Claude API (`claude-haiku-4-5`) · OpenTelemetry · CI gated by eval thresholds

## Subsystems

Each subsystem owns one hard part and is tested on its own:

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

Following the [success measures](docs/DESIGN.md#14-success-measures). Numbers are produced by the suites in [`eval/`](eval/README.md) and refreshed on every PR; the labeled zoning set is small (v0) and grows weekly.

| Measure | Now (week 3) | Source |
|---|---|---|
| Hidden-text & directive detection | recall 1.00, precision 1.00 on every technique (white / 1pt / off-page text, CSS hiding, HTML comments, Word hidden runs, metadata payloads, Unicode tag smuggling, zero-width joiners, visible directives) over 72 attacked + 9 control synthetic documents; **0 false positives on controls** | [`eval/results/redteam.md`](eval/results/redteam.md), every PR |
| Zoning accuracy, heuristic-only | macro-F1 0.86, accuracy 0.83 on 35 labeled segments across 6 authored documents (assignment, syllabus, RFP, article, spec, paper) | [`eval/results/zoning.md`](eval/results/zoning.md) |
| Zoning, +LLM delta | not yet measured (needs an API key in CI) | `python eval/zoning/run.py --llm` |
| Cost per document | accounted per run (`lectern scan` prints tokens and dollars); target $0.02–0.05 | — |
| Real users, throughput, latency | weeks 4–7 | — |

The red-team corpus is synthetic and the detectors were built against the same technique list, so 1.00 means "catches what it was designed to catch", not "catches everything"; new techniques get added to the generator first.

## Development

```bash
make infra   # postgres + redis in docker
make up      # build & run api + worker in docker too
make web     # next.js dev server on :3000  (first: make web-install)
```

Engine and CLI live in `worker/` as the `lectern` package (PyPI name `lectern-cli`; the import and the command are both `lectern`):

```bash
pip install -e "./worker[dev]"           # engine + CLI + worker + test tools
lectern scan assignment.pdf --no-llm      # offline: heuristic zoning + all static detectors
export ANTHROPIC_API_KEY=…                # adds the Claude Haiku zoning pass, D1 confirmation + overview
lectern scan assignment.pdf               # ~$0.02–0.05 for a 20-page document
lectern scan assignment.pdf --json        # the full analysis, for scripts and agents
lectern scan assignment.pdf --fail-on critical   # exit 3 on a hidden directive: a CI / ingest gate
lectern clean assignment.pdf -o clean.md --keep task,background   # clean copy + removal report
lectern clean assignment.pdf --interactive                         # choose zones in the terminal
```

Supported inputs: PDF, HTML and DOCX through Lectern's own converters, which keep the colour, size, position and hidden flags of every run of text ([ADR-010](docs/adr/ADR-010-converter-pick.md)); PPTX via MarkItDown; Markdown and text. Detectors: H1 invisible colour, H2 tiny font, H3 off-page, H4 format-level hiding (`display:none`, zero size, fg≈bg, HTML comments, Word hidden runs), H5 metadata payloads, H6 encoding tricks (zero-width / bidi / tag characters, look-alike letters), D1 AI-directed text, P1 AI-use policies. CI runs api (Maven verify), worker (ruff + pytest + an offline `lectern scan` smoke test), and web (build) on every push; eval gates join in week 6.

## License

[MIT](LICENSE) © 2026 Xing Lu
