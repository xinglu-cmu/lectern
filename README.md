# Lectern

> **Know what your AI is reading.** Scan any document for hidden prompts and AI-directed content, see it zoned by what each part *is* — task, background, boilerplate — choose what survives, and get clean Markdown ready for any AI tool. **Everything runs on your machine.**

[![ci](https://github.com/xinglu-cmu/lectern/actions/workflows/ci.yml/badge.svg)](https://github.com/xinglu-cmu/lectern/actions/workflows/ci.yml) · [design doc](docs/DESIGN.md) · [decisions](docs/adr/) · [evals](eval/README.md)

Every AI workflow starts by feeding a document to a model that dives straight in. Nobody first asks: *what is this document, which parts are the actual work, and is anything in here — visible or hidden — trying to steer the AI?* Documents carry boilerplate that wastes context, stated AI policies, and sometimes literal hidden prompt injections: white text, 1pt fonts, `display:none`, metadata payloads, instructions smuggled in invisible Unicode characters. Lectern is the missing step in between:

```bash
pip install lectern-cli                              # (PyPI release: phase 4; until then, see Development)

lectern scan  assignment.pdf                         # overview + zone map + findings, with locations
lectern clean assignment.pdf -o clean.md --keep task,background   # distilled Markdown + removal report
lectern scan  vendor.pdf --fail-on critical          # exit 3 on a hidden directive: a CI / ingest gate
```

- **Screening** — six hidden-text detectors (colour against the real background, tiny font, off-page, format-level hiding in HTML and Word, metadata payloads, invisible-character tricks) plus detectors for AI-directed sentences and AI-use policies. Hidden content is quarantined *before any model reads the document* and reported with its location. *Detect → disclose → respect*: nothing is silently dropped, and instructions found inside documents are never obeyed.
- **Functional zoning** — segments classified as `task` / `background` / `structure` / `example` / `ai_directive` / `ai_policy` / `hidden`, with confidence, via explainable heuristics plus an optional LLM pass.
- **You choose** — keep/drop by zone (CLI flags, `--interactive`, or the local review UI), then export clean Markdown with a report of what was removed and why.
- **Local by design** — no accounts, no server, no telemetry. Conversion, zoning, all detectors and clean output run offline; an Anthropic key (or, next, a local model) upgrades zoning and adds the overview.

Three front doors on one engine, all local ([ADR-012](docs/adr/ADR-012-local-first.md)):

```bash
lectern brief assignment.pdf                         # one page: what it is, what it asks, what was found
lectern mcp                                          # the engine as tools for AI agents (stdio)
lectern serve                                        # review UI on localhost (in progress)
```

**For pipelines.** As a GitHub Action:

```yaml
- uses: xinglu-cmu/lectern@main          # pin a release tag once v0.1 is out
  with:
    paths: docs/*.pdf uploads/*.docx
    fail-on: critical                    # info | warning | critical
```

As a pre-commit hook (`.pre-commit-config.yaml`): `repo: https://github.com/xinglu-cmu/lectern`, hook id `lectern-scan`. Both run offline and fail the job with exit code 3 when a document carries hidden or AI-directed content at the chosen severity; the report says where.

**For agents.** Add Lectern to Claude Code with `claude mcp add lectern -- lectern mcp`, or to Claude Desktop with `{"mcpServers": {"lectern": {"command": "lectern", "args": ["mcp"]}}}`. The agent gets three tools — `scan_document`, `clean_document`, `brief_document` — and an instruction to call `scan_document` on any file before reading it. Hidden text is quarantined inside Lectern and only *described* to the agent; it never enters the agent's context. Install with `pip install "lectern-cli[mcp]"`.

**Status:** phase 1 done (CLI, detectors, evals; PRs #49, #50). Phase 2 — the local-first cut, MCP server and local UI — in progress. The [design doc](docs/DESIGN.md) (v3) and [ADRs](docs/adr/) explain every decision, including the two pivots.

## Metrics

Following the [success measures](docs/DESIGN.md#14-success-measures). Numbers come from the suites in [`eval/`](eval/README.md) and are recomputed on every PR.

| Measure | Now | Source |
|---|---|---|
| Hidden-text & directive detection | recall 1.00, precision 1.00 on every technique (white / 1pt / off-page text, CSS hiding, HTML comments, Word hidden runs, metadata payloads, Unicode tag smuggling, zero-width joiners, visible directives) over 72 attacked + 9 control synthetic documents; **0 false positives on controls** | [`eval/results/redteam.md`](eval/results/redteam.md), every PR |
| Zoning accuracy, heuristic-only | macro-F1 0.91, accuracy 0.87 on 91 labeled segments across 15 authored documents (assignment, syllabus, RFP, article, spec, paper, email, contract, manual, lecture, job post, lab report, minutes, grant call, README); gate arms at 30 | [`eval/results/zoning.md`](eval/results/zoning.md) |
| Zoning, +LLM / local ablation | not yet measured (no key and no local model on the build machine yet) | `python eval/zoning/run.py --llm` |
| Cost per document | $0 offline; with Claude Haiku the report prints tokens and dollars (target $0.02–0.05) | the report |
| Real users | phase 4 | — |

The red-team corpus is synthetic and the detectors were built against the same technique list, so 1.00 means "catches what it was designed to catch", not "catches everything". The first version of the colour detector scored 1.00 and then flagged white-on-red banners on a real slide deck; the fix (compare against the background actually drawn) is in [ADR-011](docs/adr/ADR-011-hidden-text-screening.md). New techniques go into the generator first.

## How it works

```
load → screen (blocks) → segment → screen (text) → zone → summarize → emit
```

Own converters for PDF, HTML and DOCX keep what Markdown converters discard — colour, size, position, hidden flags of every run of text — because that is the evidence the detectors need. Block-level detectors run before segmentation and carve hidden text into its own blocks; D1/P1 pattern detectors run on segments; heuristics label every segment with a confidence and the reasons; segments under 0.7 confidence may get a second opinion from a model, with the document text passed as quoted data under a schema that cannot even express `hidden`. The `Analysis` that comes out is what the terminal report, `--json`, the clean copy, the UI and the MCP tools all render.

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"                 # engine + CLI + test tools
make test                               # ruff + pytest
make eval                               # red-team suite (gated) + zoning accuracy
lectern scan README.md --no-llm         # it scans anything, including this file
export ANTHROPIC_API_KEY=…              # optional: Claude Haiku zoning pass, D1 confirmation, overview
lectern scan assignment.pdf --local     # or a model served on this machine (Ollama), no key, no network
```

Supported inputs: PDF, HTML, DOCX (own converters), PPTX (MarkItDown), Markdown, text. Python ≥ 3.12. The package is `lectern`; the distribution name on PyPI will be `lectern-cli`.

## License

[MIT](LICENSE) © 2026 Xing Lu
