# ADR-005: arXiv-only corpus, HTML-first parsing, GROBID as fallback

**Status:** accepted · 2026-09-22

## Context

General PDF parsing is the tarpit that sinks document-AI side projects: layout variance, two-column text, tables, scanned pages. The product needs reliable section structure and stable anchors for span-level citations. arXiv has served LaTeXML-generated HTML for most new submissions since late 2023 (plus ar5iv for older papers), and papers are openly redistributable for this use.

## Decision

v1 ingests **arXiv papers only**. Parse the arXiv HTML rendering as the primary source (clean section tree, element-path + char-offset anchors, easy quote highlighting in the verification view). Where HTML is unavailable, fall back to GROBID (containerized) over the PDF for structure, with page-level anchors. Arbitrary PDF upload is explicitly out of v1.

## Rationale

- This one decision converts the highest-variance workstream into a bounded one; it is most of the difference between shipping in 8 weeks and not.
- HTML-first also improves the *product*: verification views can highlight the exact quote in rendered context, which PDF coordinates make hard.
- Screening detectors adapt cleanly: hidden-text tricks surface as inspectable styles in HTML (e.g., white `\textcolor` becomes a color style) and as content-stream anomalies in PDF.

## Consequences

- Some papers (old, PDF-only) get degraded anchors (page-level); the UI states this.
- Upload support in v1.1 reuses the same pipeline with GROBID as primary and the screening layer doing more work.

## Revisit when

v1.1 (upload), or if target users' corpora turn out to live mostly outside arXiv (e.g., ACL Anthology — likely an easy additional source, same pipeline).
