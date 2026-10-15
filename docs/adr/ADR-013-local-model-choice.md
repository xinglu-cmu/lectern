# ADR-013: Local model choice — qwen2.5:7b through Ollama, and the first heuristic / local / Claude ablation

**Status:** accepted · 2026-10-15 · implements the "measured option" of [ADR-012](ADR-012-local-first.md); DESIGN v3 §8 and §9

## Context

ADR-012 made the LLM pass optional and local: `--local` sends the same schema-constrained prompts to a model served on this machine through Ollama (`LocalLLM` in `lectern/llm.py`), Claude Haiku stays the quality reference, and DESIGN §9 asks for the heuristic / local / Haiku ablation to be published. Until now none of it had been measured: the build machine had no API key and no local model, and the README's ablation row said "not yet measured". The code default for `--local` was `llama3.2`, picked before any model had been tried.

This ADR records the first live runs of the Claude pass and of two local models, picks the local default, and states what the numbers say. Everything here was run on a fanless MacBook Air (Apple M5, 24 GiB, macOS 26.6) with Ollama 0.40.4 and the labeled set v0.2 (15 documents, 91 labeled segments).

## Decision

**`qwen2.5:7b` is the default local model** (`LOCAL_MODEL_DEFAULT`, `.env.example`, README). `qwen2.5:3b` is the documented smaller fallback for machines with less memory. `llama3.2` leaves the defaults; it was never measured and nothing recommends it over the two that were.

The ablation is published here and in the README metrics table. The zoning gate (macro-F1 ≥ 0.75 on the heuristic pass, armed at 30 documents) is unchanged; no gate is attached to the local or Claude columns yet.

## The numbers

Zoning accuracy on the labeled set, `python eval/zoning/run.py` with `--llm` (Claude) and `--local MODEL`. The LLM pass only re-zones segments the heuristics scored under 0.7, so every column starts from the same heuristic labels.

| mode | accuracy | macro-F1 | delta F1 | wall time, 15 docs | schema misses | cost |
|---|---:|---:|---:|---:|---:|---:|
| heuristic-only | 0.87 | 0.91 | — | 0.3 s | — | $0 |
| + Claude (`claude-haiku-4-5`) | 0.85 | 0.89 | −0.02 | 68 s (4.5 s/doc) | 0 | ≈ $0.05 (≈ $0.0034 per 7-segment document) |
| + local `qwen2.5:7b` | 0.74 | 0.81 | −0.10 | 116 s (7.7 s/doc) | 0 | $0 |
| + local `qwen2.5:3b` | 0.70 | 0.77 | −0.14 | 56 s (3.7 s/doc) | 0 | $0 |

Per zone, F1 (heuristic / Claude / qwen2.5:7b / qwen2.5:3b):

| zone | support | heuristic | Claude | qwen2.5:7b | qwen2.5:3b |
|---|---:|---:|---:|---:|---:|
| task | 18 | 0.83 | 0.79 | 0.68 | 0.58 |
| background | 40 | 0.86 | 0.81 | 0.66 | 0.70 |
| structure | 18 | 0.89 | 0.87 | 0.80 | 0.75 |
| example | 12 | 0.96 | 0.96 | 0.89 | 0.83 |
| ai_policy | 3 | 1.00 | 1.00 | 1.00 | 1.00 |

Single-document runs of `lectern scan eval/zoning/labeled/paper-injection.md` (7 segments, 5 D1 pattern hits, all of them the paper quoting injection text as its subject):

| | Claude Haiku | qwen2.5:7b | qwen2.5:3b |
|---|---|---|---|
| wall time | 4.8 s | 12.1 s cold, 7.6 s warm | 10.7 s cold, 3.7 s warm |
| calls, tokens | 2 calls, 2390 in / 191 out | 2 calls, 1581 in / 185 out | 2 calls, 1581 in / 181 out |
| cost | $0.0033 | $0 | $0 |
| overview | accurate | accurate | accurate |
| D1 confirmation of the 5 quoted directives | 5 × quoted (severity → info) | 1 × confirmed directive (stays warning), 2 × quoted, 2 × benign | 2 × confirmed directive (stay warning), 3 × quoted |

`lectern brief` on `assignment-sorting.md` with Claude: 12 s, a correct "what it is" and a complete task list.

## What the numbers say

1. **The local path works mechanically.** Ollama's JSON-schema `format` plus the Pydantic validation produced zero schema misses across both models in the two evals and the four single-document scans (every call that ran kept its reply; no "keeping heuristic result" fallback fired). 8 seconds per document on a fanless laptop is usable for the CLI and the review UI, with a one-off model load of ~5 s.

2. **Both LLM passes score below the heuristics on this labeled set, and for the same reason.** Segment-by-segment comparison on the documents that lost the most (`minutes-board`, `syllabus-ml`, `jobpost-backend`) shows the models calling *task* what the labels call *background*: "Learning objectives", "What we are looking for", "What you will do", a treasurer's report with action items, a catalog-modernization decision. The prompt defines task as "instructions to the human reader"; the gold labels follow that; the models read any requirement-shaped text as task. Claude does it on 8 of 40 background segments, qwen2.5:7b and qwen2.5:3b on 14 each; the 3b model additionally turns 5 of 18 structure segments into task. This is a boundary question about the taxonomy (DESIGN §5), not a model failure, and it must be settled — in the labels, in the prompt, or both — before the gate arms at 30 documents and before Haiku labels anything for distillation (DESIGN §8, G7). It is left open here on purpose.

3. **D1 confirmation differs in temperament.** Haiku downgraded all five quoted injection sentences in the measurement paper to "quoted"; qwen2.5:7b kept one as a confirmed directive. On a screening tool the local model's error is the safer one (a warning the user can dismiss, versus a quiet downgrade), but it is still an error against the gold reading. The red-team suite does not cover this case; it should.

4. **Haiku costs cents.** A 7-segment document is a third of a cent; the whole labeled set is about five cents per `--llm` run, well under the $0.02–0.05 per 20-page document that DESIGN §8 budgets.

## Rationale

- **7b over 3b:** the 7b model is closer to Claude overall (macro-F1 0.81 vs 0.77) and on four of the five zones (task 0.68 vs 0.58, structure 0.80 vs 0.75; the 3b model edges it on background, 0.70 vs 0.66) and keeps the Claude reading on four of the five D1 hits versus three; the 3b model is twice as fast (3.7 s vs 7.7 s per document) and fits in 2 GB, which is why it stays documented as the fallback rather than the default. On a 24 GiB machine the 7b model's extra 4 seconds per document buy a visibly better zone map.
- **qwen2.5 over llama3.2:** the Qwen 2.5 instruct models were picked for schema-following (the local path depends on valid JSON on every call) and that held: no misses. llama3.2 was not measured, so it is not recommended; the ADR can be revisited with a third column when someone measures it.
- **No gate on the local column yet:** with a −0.10 delta driven by a labeling question, a gate now would freeze the wrong boundary.

## Consequences

- `--local` with no model name now means `qwen2.5:7b`; `LECTERN_LOCAL_MODEL` and `--local MODEL` still override it. Users need `brew install ollama` (or the Ollama app), `ollama serve`, `ollama pull qwen2.5:7b`, about 4.7 GB of disk and 6 GB of memory while a scan runs.
- The README metrics row "Zoning, +LLM / local ablation" carries the real numbers and links here.
- The zoning eval now prints the local row and its delta in `zoning.md`; before this change the local run landed in the JSON only.
- Open next steps, in order: settle the task/background boundary for "requirements about someone else" (labels or prompt), grow the labeled set to 30, re-run all three columns, then decide whether distillation labels come from Haiku as planned or from the corrected gold.
