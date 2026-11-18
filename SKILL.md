---
name: dsh-evoontology
description: Self-evolving ontology layer for DeepSeek Harness — an evolution engine (trajectory store, threshold triggers, hypothesis rounds under a frozen budget, evaluation-gated publishing) with evidence on every record. Phase 1 powers the family agents; phase 3 is the full semantic layer. English-first, --lang zh for Chinese.
---

Use this skill when asked to make an agent's knowledge evolve from what it
actually did ("let the agent learn from its runs", "evolve the ontology layer",
"build a self-improving semantic layer"). Evidence is the contract; evaluation
is the gate.

## Status

Phase E1 (the kernel) in development — trajectory store, threshold trigger,
hypothesis rounds with a frozen budget, evaluation gate, and a SQLite semantic
seed. See [ROADMAP](ROADMAP.md).

## The covenant

- Trajectories are append-only and evidence-linked — what the agent did,
  verbatim, forever;
- Evolution is hypothesis-framed with a frozen budget; exhaustion marks the run
  incomplete and extension is an explicit human act;
- A candidate publishes only by winning an evaluation — rerunnable, seeded,
  reported as-is;
- No record without a verbatim source span.
