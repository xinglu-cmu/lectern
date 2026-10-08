# ADR-012: Local-first — no hosted service; a local review UI, an MCP server and a local model instead

**Status:** accepted · 2026-10-08 · supersedes the web/deploy parts of ADR-002, ADR-004, ADR-008, ADR-009; DESIGN v3 carries the new plan

## Context

Lectern's premise is that documents are untrusted input to AI. The v2 plan nevertheless included a hosted web app: upload a document to our server, run the pipeline there, review in the browser. That contradicts the premise. The people most likely to want Lectern — anyone handling course material, client documents, RFPs, manuscripts under review — are exactly the people who will not upload those documents to a stranger's server, and a hosted service would have to defend that trust with auth, budgets, backups, a privacy policy and an ops budget, none of which makes the tool catch one more hidden prompt.

Meanwhile the CLI is feature-complete for v1 three weeks in (PR #50): scan, clean, six hidden-text detectors, a red-team suite gating CI, zoning with an LLM pass. What is missing is not a server; it is the ways people and agents actually reach a local tool.

## Decision

**Nothing leaves the machine.** Lectern ships as a local tool with three front doors on one engine:

1. **CLI** (`lectern scan` / `clean`) — done; the everyday tool and the CI/ingest gate (`--fail-on`).
2. **Local review UI** (`lectern serve`) — a FastAPI server bound to localhost that opens the browser: drop a file, see the report, toggle zones, review findings, export clean Markdown and a one-page *brief* (what the document is, what it actually asks, what was removed and why). Analyses are kept in a local SQLite file so a user can come back to them. No accounts, no network.
3. **MCP server** (`lectern mcp`) — the same engine as tools (`scan_document`, `clean_document`, `brief_document`) for Claude Desktop, Claude Code and any MCP-capable agent, so an agent screens a document *before* it reads it. This is the front door for the users who most need it: agents are the ones a hidden instruction is aimed at.

**The LLM goes local too, as a measured option.** Claude Haiku remains the quality reference and the labeling source. A local path (a small model through Ollama/llama.cpp, then a classifier distilled from Haiku's labels) makes zoning and the brief work with no API key and no network, with the heuristic / local / Haiku ablation published. The distillation moves from the post-v1 buffer into the plan.

**Cut:** Vercel, the Spring Boot API, the Postgres job queue, Redis, R2, Hetzner, Caddy, DNS, JWT auth, per-user budgets and rate limits, OTel on a server, k6. Postgres and Spring Boot leave the stack; the `api/` and `web/` scaffolds are removed (git history keeps them). `worker/` is renamed in spirit: it is simply the package.

**Kept, unchanged:** the engine and its security ordering (ADR-011), structured outputs (DESIGN §8), the evals and their gates (DESIGN §9), the removal report, PyPI release, success measures — restated for local use.

## Rationale

- **The product and the threat model finally agree.** "Nothing leaves your machine" is a feature a security or compliance reviewer can verify, not a promise.
- **Real users are reachable without a server.** PyPI for people, MCP for agents, `--fail-on` for pipelines. A hosted app would have added a sign-up wall in front of a tool whose point is privacy.
- **The engineering gets deeper, not shallower.** A localhost full-stack app still has an API, a UI, persistence and an export path; MCP adds an agent-integration surface; distillation adds a real ML component with an ablation. What goes is operational plumbing that served no user.
- **Cost drops to zero** for both the author and users; the $20/month ceiling becomes "$0 unless you choose Haiku".

## Consequences

- DESIGN v3 replaces the dated weeks with phases; the remaining learning topics change (Spring Boot, login/security, going-live → FastAPI, MCP, local models and distillation; Postgres → SQLite).
- The `Analysis` model and the removal report become the contract between the engine and both new front doors; no second data model.
- Backups, uptime and data retention stop being our concern; the user's files stay the user's files.
- The web review UI from DESIGN v2 §7 (toggles, per-segment overrides, reorder, preview, findings review, policy acknowledgment) survives in full, served from localhost.
- Java leaves the project. A Java component kept only for its résumé value would be busywork; Lectern's backend language is the engine's language.

## What "cloud" can still mean

Two shapes fit the premise, and both are in the plan (DESIGN v3 §11). What never fits is a Lectern-run service that holds other people's documents.

- **Organizations: a self-hosted Gateway (phase 4, optional module, Java / Spring Boot).** A company that wants every document entering its internal AI pipelines screened first runs a policy enforcement point on its own infrastructure: a REST service that accepts a document, calls the Python engine as a sidecar, applies a policy (the `--fail-on` threshold), writes an audit record (who, which file, which findings, which decision) and returns the clean copy or a refusal. The documents stay in the organization's network. Java is the right tool there because that is what organizations run and integrate with; Spring Boot, Postgres (audit log, idempotent job table), Docker Compose, Testcontainers and OpenTelemetry each have a reason in that setting. *Why Java* has an answer; it is not kept for its own sake.
- **Individuals: connectors to their own storage (phase 4).** `lectern serve` can export the brief, the clean copy and the report to places the user already works in — Google Docs / Drive first — through the user's own account (OAuth from the local app). Data goes where the user chose, not to us; without configuration, nothing is ever sent.

## Revisit when

A team wants shared review with roles across organizations, or a user asks for Lectern to host anything on their behalf — both would be a separate product decision, built on the same engine, after v1.
