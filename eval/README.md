# Evals

Three suites, versioned in-repo (DESIGN §9), plus the distillation corpus tools (`distill/`,
DESIGN §8). The suites run offline with the engine installed (`pip install -e ".[dev]"`); results
land in `results/` (`redteam.md`, `zoning.md` and their JSON twins) and the generated or
downloaded corpora in `results/local/` (gitignored).

## `redteam/` — hidden-text and directive detection (every PR, gated)

`generate.py` renders each clean seed in `seeds/` as PDF, HTML and DOCX (the controls), then
applies every hiding technique that applies to the format — white text, 1pt text, off-page text,
`display:none` / off-screen / comments, Word hidden runs, metadata payloads, Unicode tag-character
smuggling, zero-width joiners, and a plain visible directive — each with one AI-directed payload,
and writes `manifest.json` with the detectors expected to fire. `run.py` scans every file with
`--no-llm`, counts a detection when an expected detector's finding covers the payload, and reports
recall and precision per technique plus whether D1 also caught the directive and whether the text
was quarantined. `--check` applies the gates (recall ≥ 0.90, precision ≥ 0.80) and fails CI.

```bash
python eval/redteam/run.py --check
```

## `zoning/` — functional zoning accuracy (labeled set, gated)

`labeled/` holds documents with a sidecar `*.labels.json`: `{"match": "<distinctive phrase>",
"zone": "<zone>"}` entries; a produced segment takes the gold zone of the first phrase it
contains, so labels survive changes in how the segmenter cuts. `run.py` reports accuracy, macro-F1
per zone and a confusion matrix for heuristic-only zoning; `--llm` adds the Claude pass and the
heuristic-vs-model delta (`--llm` needs `ANTHROPIC_API_KEY`; `--local` a model served by Ollama).
v0.3 has 30 authored documents of as many kinds (assignment, syllabus, RFP, article, spec, paper,
email, contract, manual, lecture, job post, lab report, minutes, grant call, README, newsletter,
press release, tutorial, terms of service, exam, résumé, release notes, FAQ, SOP, call for papers,
bug report, meeting agenda, offer letter, landing page, company AI policy). With 30 documents the
gate is armed: `--check` fails CI when heuristic macro-F1 drops below 0.75. Authored documents are
a start; the set should grow with real ones, labelled by phrase.

**Labeling rule for task vs background** (settled in [ADR-013](../docs/adr/ADR-013-local-model-choice.md)
after the first ablation): `task` is what *the reader of this document* is asked to do, answer,
deliver, decide or build. Requirement-shaped text is task only when the reader is the one who acts
on it: a spec read by its implementers, an RFP read by its bidders, action items assigned to the
people the minutes go to. Text that describes someone or something else, however many *must* and
*will* it carries — a role's duties, a course's learning outcomes, a product's behaviour explained
to its user, a decision already taken, a report of results — is `background`. Ask: who acts on
this sentence, and is it the reader? Zones are per segment: a single visible directive sentence
inside a larger paragraph is a D1 finding, not a zone, so label the segment by what most of it is.

```bash
python eval/zoning/run.py            # heuristic-only
python eval/zoning/run.py --check    # the gate (CI)
python eval/zoning/run.py --llm      # + Claude Haiku, with the ablation delta
python eval/zoning/run.py --local    # + the local model (qwen2.5:7b through Ollama)
```

## `distill/` — the distillation corpus (DESIGN §8, G7)

The local classifier planned in DESIGN §8 is trained on Claude's zone labels over real,
unlabeled documents and evaluated on the labeled set above, which stays held out. `corpus.md`
is the corpus: 59 redistributable public documents of the labeled set's kinds (RFCs, PEPs,
READMEs, manuals, policies, GitHub's terms, FAR clauses, 18F procurement guides, NIH funding
announcements, NASA / NIST / GOV.UK press releases, FOMC minutes, Wikipedia articles, two CC BY
arXiv papers, MIT OCW and CS50 course pages, Rust and Django tutorials, …), each with its licence
and URL, plus the rules for adding one (public and redistributable, a kind from the labeled set,
no personal data, not in the labeled set). `collect.py` downloads them into
`results/local/distill/` (gitignored), redacting e-mail addresses and phone numbers, and writes
`manifest.json` with bytes and hashes. `label.py` runs the heuristics on every document, then
sends **every** non-hidden segment to the model through the CLI's own zoning prompt in the CLI's
own batches, and keeps the raw reply (no merge rule, so a `low` model label is recorded even
where the CLI would keep the heuristic). Output: `labels.jsonl`, one row per segment (document,
segment id, heading path, text, heuristic zone and confidence, model zone and confidence, cost),
and `summary.json` / `summary.md`. Documents already in the output are skipped, so a stopped
run resumes without paying twice.

```bash
python eval/distill/collect.py                  # ~4 MB into results/local/distill/
python eval/distill/label.py --dry-run          # heuristics only, estimates the model input
keys ANTHROPIC_API_KEY && python eval/distill/label.py   # the Claude run
```

**First run, 2026-10-17** (`claude-haiku-4-5`, the definition-plus-examples prompt of ADR-013):

| | |
|---|---:|
| documents / segments / text | 59 / 1845 / ≈ 349k tokens |
| model calls / schema misses | 108 / 0 |
| cost / wall time | $0.71 (≈ $0.0004 per segment, ≈ $0.012 per document) / 6.0 min |

Label distribution, Claude vs heuristic-only on the same segments:

| zone | Claude | share | heuristics |
|---|---:|---:|---:|
| task | 394 | 21% | 466 |
| background | 747 | 40% | 645 |
| structure | 378 | 20% | 210 |
| example | 300 | 16% | 236 |
| ai_directive | 1 | 0% | 6 |
| ai_policy | 24 | 1% | 23 |
| unknown | 1 | 0% | 259 |

What the first run says, to be read before anything trains on these labels:

- **Claude and the heuristics agree on only 50% of segments** (68% where the heuristics were
  confident, ≥ 0.7), against two columns that score within 0.01 of each other on the authored
  labeled set. Real documents are messier than authored ones: navigation, link lists and
  reference sections (135 of the heuristics' 259 `unknown` become `structure`), API manuals and
  RFC prose full of *must* / *should* that the heuristics call `task` and Claude `background`
  (188 segments), and `ai_policy` sentences inside policy documents that Claude reads as the
  document's own `task` (18). By kind, agreement runs from 5% (the newsletter) and 13% (FAR
  clauses) to 70–76% (manuals, minutes, lectures, papers); plain-text RFCs and PEPs are the
  worst format (27%), the Markdown block parser being written for Markdown.
- **Claude's confidence is not informative**: 1818 of 1845 labels are `high`, 27 `medium`, none
  `low`. A classifier trained on these labels cannot weight by it; disagreement with the
  heuristics is the better signal for what to look at.
- Which column is right is the open question: the labeled set is the referee, and on it both
  score 0.88–0.89, so the next step is a few dozen real documents labelled by phrase (the
  labeled set's phase-4 target), not more Claude labels. The rows are in
  `results/local/distill/labels.jsonl`; `summary.json` has the per-document costs and the
  heuristic-vs-model confusion.

## `conversion/` — converter snapshots (every PR)

`run.py` renders the red-team seeds clean as PDF/HTML/DOCX with Lectern's own writers and compares
what the converters read (block type, level, flags, page, text) with the snapshots in `snapshots/`;
any difference fails CI, `--update` rewrites after an intended change.

```bash
python eval/conversion/run.py            # compare
python eval/conversion/run.py --update   # accept a change
```
