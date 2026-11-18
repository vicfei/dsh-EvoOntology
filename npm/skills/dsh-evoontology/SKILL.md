---
name: dsh-evoontology
description: Self-evolving ontology layer for DeepSeek Harness — evolution engine with evidence on every record. Trajectories in, hypothesis rounds under a frozen budget, evaluation-gated publishing. Zero-LLM kernel + SQLite semantic seed.
---

Use this skill when asked to make an agent's knowledge evolve from what it
actually did ("let the agent learn from its runs", "evolve the ontology layer").
**Evidence is the contract; evaluation is the gate.**

## Run

`evoontology` must be on PATH (`npm i -g dsh-evoontology`).

```bash
evoontology seed --sqlite data.db              # Term+Mapping from DDL (zero LLM)
evoontology trajectory append --json '{"agent":"my-agent","summary":"..."}'
evoontology trigger                           # due? (N new or M days)
evoontology evolve start --hypothesis "..."   # open a budgeted run
evoontology evolve round --records cand.jsonl # gate: publish iff it wins
evoontology validate .evo/records.jsonl       # format conformance
evoontology record list
```

## The covenant

- Trajectories are append-only and evidence-linked;
- Evolution is hypothesis-framed with a frozen budget; extension is explicit;
- A candidate publishes only by winning an evaluation — deterministic, rerunnable;
- No record without a verbatim source span.
