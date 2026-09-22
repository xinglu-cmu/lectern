# ADR-001: Build a paper-reading workspace (not a course copilot or job-search copilot)

**Status:** accepted · 2026-09-22

## Context

Three candidate scenarios were on the table (see the project context brief): A — course-study copilot, B — paper-reading agent, C — job-search copilot. The project must serve two goals at once: a public, deployed, non-toy system for SDE internship applications, and a testbed for a human–AI interaction study (editable plan checkpoint, per a private research plan) in Spring 2027.

## Decision

Scenario B: a provenance-first paper-reading workspace (Lectern).

## Rationale

- B is the only scenario where the CV and research goals compound: the research plan's main project *is* a reading agent with an editable plan checkpoint, so the study instrument is a feature flag on the product rather than a second codebase.
- A fails the "public demo" requirement: course slides are instructors' IP and cannot be republished in a deployed corpus. arXiv papers are open. B also subsumes A's realistic user base (paper-driven courses).
- C depends on ToS-hostile, brittle JD scraping; its user acquisition is harder than it looks; its tie to the existing research plan is weak; and "AI résumé tool" is the most common student AI project of this cycle.
- Incumbents (NotebookLM etc.) are not a blocker for either goal: recruiters judge rigor, not idea novelty, and for research the incumbent-shaped task adds ecological validity while lacking exactly the features under study (plan visibility, span-level verification).

## Consequences

- User acquisition targets grad students and paper-heavy courses at CMU.
- v1 corpus is arXiv-only (see ADR-005), which the scenario makes acceptable.

## Revisit when

Never for v1. C-style features (approve/edit/reject on state-changing actions) reappear naturally if the agent ever gains write tools.
