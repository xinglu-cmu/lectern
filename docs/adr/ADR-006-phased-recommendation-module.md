# ADR-006: Recommendation module is phased behind v1, with a digest-first product surface

**Status:** accepted · 2026-09-22

## Context

A recommendation pipeline (event log → cleaning → features → recall → rank → re-rank → eval) is wanted for MLE-track interview breadth, per a senior's advice that interviewers walk the pipeline end to end on data you own. The temptation is to build it alongside v1 (+~3 weeks, interleaved). Two realities push back: (1) the 8-week v1 plan has no slack and a solo developer; (2) with ≤ 50 users, within-library collaborative signals are too sparse to train on, and an online A/B test has no statistical power.

## Decision

Four phases (detail in DESIGN.md §16): **phase 0** (inside v1) ships only the event schema with `exp_id` and impression logging; **phase 1** (post-v1 buffer, before winter break) ships a no-ML "daily digest" — recent arXiv papers ranked per user by embedding-similarity recall + rule re-rank, with explanations; **phase 2** (Dec–Jan) ships the learned ranker (documented data chain, LightGBM, time-split offline eval, `EVAL.md`); **phase 3** (Spring, optional) two-tower / generative-rec experiments and HAI study hooks.

The product surface recommends from the **arXiv stream**, not only within a user's library: unbounded item side, daily impression labels, and content-based cold start that works at N=1 users (the arxiv-sanity shape on owned infrastructure).

## Rationale

- Protects v1: the protected core (ingestion, search, agent loop, citations) never competes with model training for weeks.
- Fixes the data problem by product design rather than by pretending: the digest *generates* the labels phase 2 trains on — shipping phase 1 before the break is what makes a January model trainable.
- Honesty as strategy: résumé claims use offline time-split metrics and system numbers; the A/B plumbing is built and demonstrated, never presented as a powered experiment.

## Consequences

- v1 carries only the cheap obligations: append-only events, `exp_id`, impression logging.
- Each phase is a separable deep-dive module with its own eval and interview narrative (SDE / MLE / HAI from one codebase).

## Revisit when

User count or a public dataset changes the label economics, or the Kuaishou generative-rec side track materializes with a real deadline (evaluate only after v1 ships).
