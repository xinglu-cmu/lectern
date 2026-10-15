# ADR-011: Hidden-text screening — block-level, before segmentation, judged against what is drawn behind the text

**Status:** accepted · 2026-10-01 · refines DESIGN §4 (screen stage)

## Context

Week 3 added the hidden-text detectors H1–H6. Two things were decided while building them that DESIGN §4 left open.

**Where in the pipeline they run.** The week-2 detectors (D1, P1) read segments. But a hidden run is usually a single white or 1pt line inside an otherwise normal paragraph; if detection happens after segmentation, the hidden text shares a segment with visible text, and quarantining it means either dropping the visible text with it or letting the hidden text reach the LLM pass and the clean copy.

**What "invisible colour" means.** The first H1 rule — text near-white on a presumed white page — scored 1.00 on the synthetic red-team corpus and then flagged 26 "Carnegie Mellon" headers on the first real slide deck tried: white text on a red banner, white labels in diagram boxes, white digits on dark cells. The synthetic controls could not expose this because the generator never draws backgrounds. Two more real decks showed the same pattern.

## Decision

1. **H1–H6 run on blocks, before segmentation.** `screen_blocks` applies them to the loaded document and rewrites the block list: a block whose runs are only partly hidden is split so the hidden part becomes its own block flagged `hidden:<reason>`; tag-character payloads become a new hidden block next to their carrier. The segmenter then gives every hidden block its own segment, zoning labels it `hidden` with confidence 0.95, the LLM pass and the overview skip it, and the clean copy never contains it. D1 and P1 keep running on segments afterwards; a directive inside a hidden segment is escalated to `critical`.

2. **H1 compares text colour with the background actually drawn behind it.** The PDF converter records, per word, the colour of the smallest filled rectangle or curve under it (`Style.background`), `image` when a picture is there, or nothing when it sits on the bare page. H1 flags a run when the luminance difference between text and background is below 0.08. White on a red banner passes; white on the bare page, and black on a black box, are hidden; text over an image is never judged (we cannot know). The same contrast rule serves the HTML converter's `fg-bg` reason.

3. **H2 is absolute first.** Text at ≤ 2.5pt is hidden at any zoom. The relative rule (below 30% of the body size) applies only under 4pt, because a 28pt slide deck has legitimate 7pt labels.

4. **Real documents are the false-positive check the synthetic corpus cannot be.** The red-team suite measures recall and precision against the technique list it was built from; it is gated in CI. Before a detector change ships, it is also run on a handful of real course PDFs on the author's machine (never committed; they are not ours to publish) and must raise no new findings. Week 6's conversion snapshots will make part of that repeatable with redistributable documents.

## Consequences

- A paragraph with a hidden word in the middle reads as two visible segments around one hidden segment. That is honest and slightly fragments the clean copy; the removal report explains the gap.
- Background lookup is O(words × shapes) per page and is skipped on pages with more than 3,000 filled shapes (dense vector drawings), where H1 then falls back to the page-is-white assumption.
- The red-team generator gained filled rectangles in its PDF writer so the "white on a dark box must not fire" case is a regression test, not only a memory.
- Detection numbers in the README say what they are: recall and precision on a synthetic corpus, with zero false positives on its controls — not immunity, and not a real-world precision figure. The labeled set and user reports supply that over time.

## Revisit when

A real document shows a hidden-text technique the generator does not cover (then the generator grows first, then the detector), or background lookup proves too slow on large vector-heavy PDFs.
