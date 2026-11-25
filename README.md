# dsh-EvoOntology — a self-evolving ontology layer for DeepSeek Harness

**An evolution engine with evidence on every record: trajectories in, hypothesis-framed
rounds out, nothing publishes without winning an evaluation. Phase 1 powers the
family's own agents; the same engine grows into the full document/data ontology layer.**

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![npm](https://img.shields.io/npm/v/dsh-evoontology)](https://www.npmjs.com/package/dsh-evoontology)

> Implements the concept of [ruc-datalab/EvoOntology](https://github.com/ruc-datalab/EvoOntology)
> (1.3k★, MIT, arXiv 2609.15779) natively for DSH — clean-room, zero upstream code,
> not affiliated. [中文文档](README.zh-CN.md)
> Family: [dsh-TradingAgents](https://github.com/vicfei/dsh-TradingAgents) ·
> [dsh-auto-ontology](https://github.com/vicfei/dsh-auto-ontology) ·
> [dsh-WrenAI](https://github.com/vicfei/dsh-WrenAI)

## Why

Agents re-learn what they already learned. Every session rediscovers the same
tables, the same definitions, the same dead ends — because what an agent learned
lives and dies inside one conversation. The fix is not a bigger context window;
it is a **layer that remembers, and that only changes when the evidence says so**:

- **Trajectories are the corpus.** What agents actually did — decisions, outcomes,
  quotes — is appended to an evidence-linked store, never edited.
- **Evolution is hypothesis-framed and budgeted.** Rounds carry a formal
  hypothesis and a frozen budget; exhaustion marks the run incomplete and needs
  an explicit extension. No silent midnight self-modification.
- **Nothing publishes without winning.** A candidate version only replaces the
  incumbent when it beats it on an evaluation adapter — rerunnable, seeded,
  reported as-is (see our sibling repo's honest 10%).
- **Evidence on every record.** The five-record schema (Term, Mapping, Relation,
  Constraint, Evidence) inherits the family's evidence-linked format: no record
  without a verbatim source span.

## The route (phase 1 = the kernel, phase 3 = the full layer)

| Phase | Ships |
|---|---|
| **E1 · evolution kernel** | trajectory store (append-only, evidence-linked) · threshold triggers (N trajectories / M days) · hypothesis rounds under a frozen budget · evaluation-gate adapter contract · SQLite semantic-layer seed on the README |
| **E2 · family integration** | the family's own agents plug in (verdict ledgers, certification flows, drift alarms) as first proof of generality · npm bundle + typed tools |
| **E3 · semantic layer** | workload collection (questions / same-data history / evidence-grounded generation) · Term→table/column mapping extraction · `browse` answer-time semantics · the full EvoOntology concept, DSH-native |
| **E4 · ecosystem** | bounded connector breadth · visualization · the evidence-linked evolution records as a versioned open format |

Non-goals, stated up front: MCP-first serving (DSH typed tools are the native
surface), chasing eight database connectors, benchmark leaderboard chasing,
and competing with the family's own dsh-WrenAI on Q&A (this engine evolves
layers; WrenAI answers questions through them).

## Status

**Phase E1 complete** — the zero-LLM kernel ships:

```bash
npm i -g dsh-evoontology
evoontology seed --sqlite mydata.db              # Term+Mapping from DDL, zero LLM
evoontology evolve start --hypothesis "..."      # open a budgeted evolution run
evoontology validate .evo/records.jsonl          # evidence-linked format conformance
```

**E2, the first adapter** — the family's own [dsh-auto-ontology](https://github.com/vicfei/dsh-auto-ontology)
plugs in: its `ao-trajectory/0.1` export becomes trajectories, one hypothesis
round proposes re-typings for the terms no quote grounds, and the sibling's own
eval judges them.

```bash
auto-ontology export ontologies/x.json > trajectory.ndjson     # there: what happened
evoontology trajectory import --from trajectory.ndjson         # idempotent by event id
evoontology adapt auto-ontology --from trajectory.ndjson       # propose → judge → gate
auto-ontology apply --proposals .evo/runs/<run>.proposals.json --actor agent:<name>   # and back
```

See [ROADMAP](ROADMAP.md) for the full plan (E2 family integration → E3 semantic
layer → E4 ecosystem).

## E2 · the dsh-auto-ontology adapter

dsh-auto-ontology builds a typed layer from documents and keeps the judge's
verdict on every quote. `auto-ontology export` writes what happened as an
`ao-trajectory/0.1` stream; this adapter runs one hypothesis round on it and is
the only place in this repo where a model is called — the kernel stays zero-LLM.

1. **import** — the stream becomes trajectory records, idempotent by event id
   (a replay adds nothing).
2. **project** — the layer the stream describes, a pure function of the store:
   one Term per (entity, type), one Relation per triple, each carrying its quotes
   **with their verdicts**. A rejected certification suppresses its typing and
   becomes a Constraint; a conflict stays as an open Constraint.
3. **propose** — for each Term the judge could not ground, a model reads the TBox
   and all the term's quotes and names one listed type a quote states — or
   nothing. Anything malformed (a type outside the TBox, the current typing
   again, a quote that is not the term's own) is dropped before a judge sees it.
4. **judge** — every surviving proposal goes through auto-ontology's **own eval
   CLI**: the same prompt and one-quote protocol that flagged the term. Nothing
   about judging is re-implemented here.
5. **round** — the projection with its grounded re-typings, against the
   projection, under the gate. A won round publishes a layer and writes
   `runs/<run>.proposals.json`; `auto-ontology apply --proposals` carries it back
   as a recorded certification plus a new assertion — never as a silent edit.

The gate counts verdicts: `endorsed` — (endorsed − judged against) / records —
is a fourth term next to coverage, cleanliness and diversity, so a layer wins by
being better evidenced. A layer from a source that judges nothing carries no
verdicts and scores exactly as before.

**What a won round does not mean.** A re-typed term moves from −1 to +1 by
construction, so any round with one judge-grounded proposal wins: the experiment
is the judge, not the arithmetic. Name two different models for proposer and
judge when you can (`--proposer-model`, `--judge-model`); the run records both.

## License

MIT; concept credit to the MIT upstream — zero upstream code used.
