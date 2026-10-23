# ADR-014: The distilled zoning classifier — a linear model over hashed features, trained on Claude's labels, shipped in the package

**Status:** accepted · 2026-10-23 · completes G7 of DESIGN v3 §8; follows [ADR-013](ADR-013-local-model-choice.md)

## Context

DESIGN §8 plans a classifier distilled from Claude's zone labels, so that the quality upgrade of the LLM pass is available with no key, no network and, unlike `--local`, no model server. ADR-013 settled what it should learn from: Claude Haiku with the definition-plus-examples prompt, level with the heuristics on the labeled set (macro-F1 0.88 vs 0.89 in that run; 0.87 in this one), while the local `qwen2.5:7b` sits below (0.82). PR #62 built the corpus: 59 redistributable public documents of the labeled set's kinds, every non-hidden segment labeled by Claude through the CLI's own prompt and batches (1845 segments, 108 calls, $0.71). Two facts from that run shape this decision: Claude and the heuristics agree on only 50% of those real-document segments, and Claude's confidence is uninformative (1818 of 1845 labels `high`).

## Decision

**The classifier is multinomial logistic regression over hashed features, written in pure Python, trained by `eval/distill/train.py` and shipped as `lectern/zoning/distilled.json.gz` (119 kB).** It runs as `--distilled`, an offline mode beside `--no-llm` and `--local`: the heuristics label everything, then the classifier re-zones the segments under the 0.7 confidence bar (the same gate as the LLM pass) and abstains below a top probability of 0.55. It never predicts `hidden`. The overview and the brief still need a language model; `--distilled` has neither.

Features, per segment, hashed by CRC-32 into 16 384 slots and L2-normalized: word unigrams and bigrams of the text (first 1500 characters, 300 words), the heading path and the last heading, the segment's own headings, its flags, the heuristic zone, a confidence bucket, the heuristic signal names, and a few shape counts (length, lines, bullet share, links, imperative starts, "you", digits, a code fence, a question mark). Training: SGD, 5 epochs, L2 1e-3, inverse-square-root class weights; weights under 0.1 are dropped on save.

## The numbers

Trained on 1844 segments (one `ai_directive` row dropped with the class: 747 background, 394 task, 378 structure, 300 example, 24 ai_policy, 1 ai_directive). Five-fold cross-validation **by document** (whole documents held out): agreement with Claude on unseen documents, accuracy 0.61, macro-F1 0.47. Training accuracy after the refit on everything: 0.94.

On the labeled set (30 authored documents, 184 gold segments, which no part of the pipeline above ever saw), same harness as ADR-013:

| zoning | accuracy | macro-F1 | delta F1 | cost, 30 docs | time, 30 docs |
|---|---:|---:|---:|---:|---:|
| heuristics only | 0.85 | 0.89 | — | $0 | 0.5 s |
| + distilled classifier | 0.86 | 0.89 | −0.00 | $0 | 0.6 s |
| + local `qwen2.5:7b` (Ollama) | 0.81 | 0.82 | −0.07 | $0 | ≈ 285 s |
| + Claude `claude-haiku-4-5` | 0.86 | 0.87 | −0.02 | ≈ $0.05 | ≈ 180 s |

Per zone, F1 (heuristics / distilled): task 0.82 / 0.83 · background 0.87 / 0.88 · structure 0.86 / 0.83 · example 0.97 / 0.97 · ai_policy 0.92 / 0.92.

What the classifier actually did on the labeled set: of 184 segments, 39 were under the bar and reached it; it changed 6 zones (4 `unknown` → `structure`, 1 `unknown` → `background`, 1 `task` → `background`). Pruning weights under 0.1 cut the file from 426 kB to 119 kB with no change in the score (0.864 / 0.887 at every threshold up to 0.1).

## What the numbers say

1. **Level with Claude and the heuristics, clearly above the local language model, at no cost.** On this labeled set the distilled classifier is the best offline option by a wide margin over `qwen2.5:7b` (+0.07 F1) and indistinguishable from Claude (+0.02 F1 on this run, −0.01 on ADR-013's: noise). It is not *better* than the heuristics alone: six changed zones is the whole difference, and the set is small and authored.
2. **The gate hides the ceiling.** A bag of words reproduces Claude on unseen documents only 61% of the time, yet scores level with Claude here, because the heuristics already settle the 145 confident segments and the classifier only sees 39. Were it asked to re-zone everything it would do worse than the heuristics; that is why it is not.
3. **Pure Python is enough at this size.** Training takes four seconds; the file is 119 kB; prediction is a few hundred multiply-adds per segment. scikit-learn, PyTorch or a model download would have bought nothing measurable on this set.

## Rationale

- **Linear over an encoder:** DESIGN §8 said "a small fine-tuned encoder if it earns its cost". It does not, yet: the measurement cannot tell the linear model from Claude. An encoder would add a PyTorch dependency and hundreds of megabytes to a tool whose install is `pip install lectern-cli`.
- **Hashed features over a vocabulary:** no vocabulary file to ship or version; the feature function in `distilled.py` *is* the vocabulary, and `FEATURE_VERSION` in the saved model refuses a mismatch.
- **Heuristic signals as features:** the classifier is a second opinion on the heuristics' doubtful cases, so it should know what the heuristics saw. This also makes it a stacked model rather than a replacement, which matches where it runs.
- **Same gate, same merge as the LLM pass:** a second opinion that overrules a confident first one would have to be measurably better first, and this one is not.
- **Its own mode, not inside `--local`:** `--local` means "a language model on this machine" and keeps the overview and brief. Folding the classifier into it would have made `--local` mean two different things depending on the step.

## Consequences

- `--distilled` on `scan`, `clean`, `brief`, `mcp` and `serve`; `Method.distilled` on the segments it relabels; `mode: distilled` in the analysis; signals `distilled:0.83` or `distilled:low(zone 0.41)` say what it did or would have done.
- The README metrics table carries the four-column ablation; `eval/zoning/run.py --distilled` adds the column.
- Retraining is `python eval/distill/train.py` after a new `label.py` run; the model's metadata records the labels' hash, the teacher, the counts and the cross-validation score.
- Open: the labeled set should grow with real, phrase-labeled documents (phase 4, target 60). That is what will say whether Claude or the heuristics are right where they disagree on real text, and whether the linear model's 0.61 ceiling costs anything a user would notice.
