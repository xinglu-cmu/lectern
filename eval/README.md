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
heuristic-vs-LLM delta (needs `ANTHROPIC_API_KEY`). v0 has 6 authored documents (assignment,
syllabus, RFP, article, spec, paper); the plan is 30 by the midpoint and 60 by week 6, curated
from real documents at ~5 a day.

```bash
python eval/zoning/run.py            # heuristic-only
python eval/zoning/run.py --llm      # + Claude Haiku, with the ablation delta
```

## `conversion/` — converter snapshots (week 6)

Golden-file outputs of the converters on a fixed corpus; catches converter-upgrade regressions.
