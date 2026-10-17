# Evals

Three suites, versioned in-repo (DESIGN §9). All run offline with the engine installed
(`pip install -e "./worker[dev]"`); results land in `results/` (`redteam.md`, `zoning.md` and
their JSON twins) and the generated corpora in `results/local/` (gitignored).

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

## `conversion/` — converter snapshots (every PR)

`run.py` renders the red-team seeds clean as PDF/HTML/DOCX with Lectern's own writers and compares
what the converters read (block type, level, flags, page, text) with the snapshots in `snapshots/`;
any difference fails CI, `--update` rewrites after an intended change.

```bash
python eval/conversion/run.py            # compare
python eval/conversion/run.py --update   # accept a change
```
