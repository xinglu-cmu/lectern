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

## `zoning/` — functional zoning accuracy (labeled set, reported now, gated from week 6)

`labeled/` holds documents with a sidecar `*.labels.json`: `{"match": "<distinctive phrase>",
"zone": "<zone>"}` entries; a produced segment takes the gold zone of the first phrase it
contains, so labels survive changes in how the segmenter cuts. `run.py` reports accuracy, macro-F1
per zone and a confusion matrix for heuristic-only zoning; `--llm` adds the Claude pass and the
heuristic-vs-model delta (`--llm` needs `ANTHROPIC_API_KEY`; `--local` a model served by Ollama).
v0.2 has 15 authored documents of as many kinds (assignment, syllabus, RFP, article, spec, paper,
email, contract, manual, lecture, job post, lab report, minutes, grant call, README); `--check`
arms the macro-F1 ≥ 0.75 gate once the set reaches 30 documents. Authored documents are a start;
the set should grow with real ones, labelled by phrase.

```bash
python eval/zoning/run.py            # heuristic-only
python eval/zoning/run.py --llm      # + Claude Haiku, with the ablation delta
```

## `conversion/` — converter snapshots (every PR)

`run.py` renders the red-team seeds clean as PDF/HTML/DOCX with Lectern's own writers and compares
what the converters read (block type, level, flags, page, text) with the snapshots in `snapshots/`;
any difference fails CI, `--update` rewrites after an intended change.

```bash
python eval/conversion/run.py            # compare
python eval/conversion/run.py --update   # accept a change
```
