# ADR-003: Hand-rolled agent loop, no orchestration framework

**Status:** accepted · 2026-09-22

## Context

The agent run is: plan generation → optional human checkpoint (pause/resume, editable plan) → per-sub-question retrieval → synthesis → citation verification → optional corrections. Frameworks (LangGraph, ADK, CopilotKit/AG-UI for state sync) offer interrupts and human-in-the-loop primitives.

## Decision

Hand-roll the loop as an explicit state machine persisted in Postgres, streamed over plain SSE, with a custom plan-editor UI. Use the Anthropic SDK directly (Java SDK from the API service); no orchestration framework, no agent-state-sync library.

## Rationale

- The pausable, human-editable plan checkpoint is the *research object*. We need to own the plan representation, the interrupt/resume semantics, and the logging of every edit — precisely the parts a framework abstracts away.
- The loop is ~4 LLM calls with read-only tools; as an engineering artifact it is a state machine over a database row, which Spring handles natively. A framework would add a dependency layer larger than the code it replaces.
- Interview value: "show me your agent loop" has a real answer.

## Consequences

- We write our own resumability (state + SSE snapshot-on-reconnect) and tool-permission layer (trivial in v1 — all tools read-only — but the gate exists for future write tools).
- No framework lock-in when the study needs a custom mode.

## Revisit when

If v2 needs multi-agent fan-out or long tool chains, reconsider a framework for orchestration only — the checkpoint and its logging stay ours.
