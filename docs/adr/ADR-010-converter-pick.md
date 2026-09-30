# ADR-010: Converters — own pdfplumber pass for PDF, MarkItDown for office and web formats, Docling deferred

**Status:** accepted · 2026-09-29 · resolves DESIGN §15 open decision 1

## Context

The engine's `load` stage turns any input into one normalized document: blocks with type, text, style hints and anchors (DESIGN §4). Two established MIT-licensed converter families were candidates to ride on: **MarkItDown** (Microsoft; Markdown out of PDF/DOCX/HTML/PPTX and more, small install) and **Docling** (IBM; layout-model PDF parsing with tables and reading order, large install: PyTorch plus downloaded models, slow on CPU). DESIGN planned a bake-off on the labeled corpus, which does not exist until week 3.

Two facts settled it earlier:

1. **Every Markdown-producing converter discards exactly what the hidden-text detectors need.** H1 (invisible colour), H2 (tiny font) and H3 (off-canvas) read colour, size and coordinates per word. MarkItDown's PDF path is a pdfminer text dump; Docling exposes layout boxes but not fill colour. Neither can be fixed from the outside.
2. pdfplumber exposes pdfminer's per-character data *with* those attributes, in a small pure-Python dependency that installs in seconds on the ARM VM (DESIGN §10).

## Decision

One `Converter` interface (`lectern/converters/__init__.py`), three implementations:

- **PDF → our own pdfplumber pass.** Words → lines → blocks; body font size by character count; headings by size rank and bold short lines; list items by bullet or enumerator with wrapped lines joined; page furniture (top/bottom 7% of the page) flagged `header`/`footer`, plus `repeated` across pages and `page_number`. Every block keeps `runs` — stretches of uniform (size, font, colour) with a bounding box — so a single white or 1pt word inside a normal paragraph is still visible to a detector. Nothing is filtered at this stage.
- **DOCX / HTML / PPTX → MarkItDown, then our Markdown block parser.** Good-enough structure in one dependency. Style passes for these formats come with their detectors in week 3: an HTML walk for H4 (`display:none`, zero size, fg≈bg) and a python-docx run-property pass for DOCX (vanish, colour). Both slot in behind the same interface.
- **Markdown / text → the block parser directly.**

Docling is **deferred**, not rejected: it stays a candidate behind the interface if the conversion snapshot suite (week 6) or the labeled set shows our PDF pass losing tables or reading order on real documents.

## Consequences

- Hidden-text detection on PDF is possible at all; the week-3 detectors consume `Block.runs` and `Block.flags` with no reparse.
- Our PDF pass is simpler than a layout model: no table extraction yet, two-column papers rely on pdfminer's text-flow ordering, and heading levels are by font-size rank (a deck with five title sizes gets five levels). These are known gaps to measure, not surprises.
- Slide decks produce many small heading-bounded segments and one furniture segment per page; the report collapses furniture into one line.
- PyPI: `lectern` is taken by an unrelated project, so the distribution is **`lectern-cli`**; the import package and the command stay `lectern` (resolves open decision 2).

## Revisit when

Conversion snapshots or the labeled set show PDF structure errors that cost zoning accuracy (tables read as prose, columns interleaved), or a user corpus is dominated by scanned PDFs (OCR is out of scope for v1 either way).
