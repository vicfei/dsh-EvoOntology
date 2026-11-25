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
evoontology adapt auto-ontology --from trajectory.ndjson \
  --auto-ontology <sibling checkout> --proposer-model M --judge-model N   # propose → judge → gate
auto-ontology apply --proposals .evo/runs/<run>.proposals.json \
  --from ontologies/x.json --actor agent:evoontology-adapter              # and back
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
   again, a quote that is not the term's own) is dropped before a judge sees
   it, with its reason, on disk. A quote that is the term's own as the
   sibling's verbatim rule sees it (markdown marks and whitespace aside) is
   snapped to the term's own string: the judge never sees the model's copy.
4. **judge** — every surviving proposal goes through auto-ontology's **own eval
   CLI**: the same prompt and one-quote protocol that flagged the term. Nothing
   about judging is re-implemented here.
5. **round** — the projection with its grounded re-typings, and for each the
   constraint its certification will add — the layer the trip back projects —
   against the projection, under the gate. A won round publishes a layer and
   writes `runs/<run>.proposals.json`; `auto-ontology apply --proposals` carries
   it back as a recorded certification plus a new assertion — never as a silent
   edit. CI asserts the published layer equals the trip-back projection.

Two rules a live round taught (below). **One stream, one run:** an unchanged
stream never opens a second run on its own — a lost round spent its budget, and
another try is `evolve extend --run <id> --extra N --note "why"`, recorded on
the run; a changed stream is a new question. **A crash closes its run** as
`aborted` with the reason on it, never `running` for ever. Each round keeps its
own judge input and rows under `runs/<run>.judge/round-N/`.

The gate counts verdicts: `endorsed` — (endorsed − judged against) / records —
is a fourth term next to coverage, cleanliness and diversity, so a layer wins by
being better evidenced. A layer from a source that judges nothing carries no
verdicts and scores exactly as before.

**What a won round does not mean.** A re-typed term moves from −1 to +1 by
construction, so any round with one judge-grounded proposal wins: the experiment
is the judge, not the arithmetic. Name two different models for proposer and
judge when you can (`--proposer-model`, `--judge-model`); the run records both.

### The first live round (2026-11-25), as measured

One stream, three attempts, every number below from the run files and console
logs — published in the sibling repo under
[`eval/live-round/`](https://github.com/vicfei/dsh-auto-ontology/tree/main/eval/live-round).

**The stream.** A dsh-auto-ontology build over the 23 public READMEs of the
plugin family, folded once and certified twice: 374 events (1 build · 1 fold ·
370 assertion · 2 certification), 226 of 370 quotes grounded. It projects to
128 Terms, 177 Relations and 1 Constraint; 47 Terms are typed on quotes the
build's judge could not ground, and those went to the proposer every time.
Gate before any round: coverage 1.0 · cleanliness 1.0 · diversity 0.6 ·
endorsed 0.3627 → **2.9627**. Proposer `deepseek-chat`, judge
`deepseek-reasoner`, the sibling's engine pinned at `2f5e4d9`.

| # | Run · round | Proposer (47 terms) | Judge | Outcome |
|---|---|---|---|---|
| 1 | `20261125-183646` · none | 8 valid · 39 malformed · 46,097 in / 3,423 out tokens | never reached | **Crashed** before the judge: the adapter's own print of the malformed list raised `KeyError: 'from_type'`. The run sat `running` until it was closed `aborted` with the reason on it. No round, nothing judged |
| 2 | `20261125-184149` · round 1 | 10 valid · 37 malformed · 46,097 in / 3,423 out | 0 grounded · 10 not grounded | **Lost**: candidate 2.9627 vs 2.9627. Nothing published |
| 3 | `20261125-184149` · round 2 | 13 valid · 34 null · 0 malformed · 48,535 in / 2,585 out | 1 grounded · 12 not grounded | **Won**: 2.9693 vs 2.9627 → published `layer_v1` |

The 37 malformed proposals of attempt 2, by the reason the adapter recorded:
19 copied a source label in front of the quote (the prompt put one there), 11
named a type outside the TBox — the literal `json_object`, because JSON mode
will not return a bare null and the model invented a placeholder — and 7
proposed the term's current type. The proposer's prompt was rewritten between
attempts 2 and 3: quotes as JSON lines, the null spelled out. Attempt 3 had no
malformed proposal at all.

**The extension was not a human act.** After attempt 2 the run had spent its
budget (1/1). The one-stream-one-run rule refused two un-extended re-runs (exit
1, no model called). The extra round came from
`evolve extend --run 20261125-184149 --extra 1 --note "…"` — issued by
`agent:shanghai-window` on the owner's standing delegation for this work, and
recorded on the run as such. The kernel calls an extension the explicit human
act; this one was not. All three attempts are published for that reason.

**The one the judge grounded:** `OAR: dsh_plugin → upstream_project`, on
"*- **OAR** (`src/adapters/oar.ts`) — [Open Agent Runtime](https://github.com/botiverse/oar): the host owns the OAR session…*" —
"Quote names OAR as Open Agent Runtime with GitHub link and an adapter
integrating it." The 22 refusals across the two judged rounds each turn on a
quote that is about something else than the term (the plugin that *provides*
admission control for CLI agents is not a CLI agent; a ticket *for* an agent is
not one) — the 12 of round 2 are on disk, the 10 of round 1 were read before
round 2 overwrote them — and none should have passed.

**The trip back, measured.** `auto-ontology apply --proposals` re-typed 1
entity, skipped the 12 not grounded, and a replay was a no-op (1 stale). The
re-exported stream grew by 2 events — the new assertion and the reject
certification whose `retyped_to` names the judge and the run — and imported
idempotently (+2, 373 already present). The projection then holds one `OAR`,
typed `upstream_project`, grounded, its `dsh_plugin` typing suppressed.

The trip back exposed two gaps, and the round's headline number is one of them:

- **The published layer was one record too light.** It scored 2.9693; the real
  trip back scores **2.9681**. The certification adds a Constraint
  (`OAR is not a dsh_plugin — rejected by agent:evoontology-adapter: …`) that
  the in-memory candidate did not carry. The candidate carries it since
  218ee6c, and CI now asserts that the published layer equals the trip-back
  projection (same ids, verdicts, rules, evidence and score). Under the fixed
  construction the round still wins: 2.9681 vs 2.9627.
- **The re-typed assertion came back with no judge named** (`by: "judge"`,
  `reason: null`): `apply` folds it without the judge that grounded it — the
  certification says `deepseek-reasoner`, the assertion does not. The published
  layer's copy did name it. Fixed on the sibling's side in its 0.3.0 (an
  evidence carries its judge).

**What the round does not show.** One true positive out of 23 judged
proposals, on one stream, with the only round that won reached through an
extension the owner did not grant by hand. Once allowed to say null, the
proposer had nothing for 34 of 47 terms. And the judge's work directory was per
run, so round 2 overwrote round 1's judge input and rows: what survives of
round 1's ten refusals is the console log (eight shown) and the run file's
tally — the 19/11/7 breakdown above was read from the file before it was
overwritten. Directories are per round since 218ee6c. Attempts 1 and 2 logged
identical token totals with different tallies (8/39 and 10/37); attempt 1 wrote
nothing to disk before it crashed, so the difference cannot be reconstructed.

## License

MIT; concept credit to the MIT upstream — zero upstream code used.
