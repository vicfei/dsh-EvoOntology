# ROADMAP — dsh-EvoOntology (founded 2026-11-18; phase C start, phase A destination)

North star: the DSH-native slot of the self-evolving ontology layer — eating
ruc-datalab/EvoOntology's rising search traffic ("evoontology deepseek/dsh") while
the category is hot (upstream: 1.3k★ in 2 months, arXiv-backed). Metric: top-20
DSH plugin within 30 days of the first real release.

**Strategy (owner decision 2026-11-18):** build as **phase C first — the general
self-evolution engine — and grow into phase A — the full semantic-layer
implementation of the upstream concept.** Three things are pre-embedded from day
one so the C→A transition costs nothing: the five-record schema (Term/Mapping/
Relation/Constraint/Evidence — E1 may fill only a subset, but the store IS the
final format), upstream-aligned vocabulary on every SEO surface, and a live
semantic-layer seed demo on the README.

Owner policies baked in: English-first everywhere (README/SKILL/engine
output/demo assets; zh-CN secondary), development via issue → branch → PR,
CI gates from day one, evidence on every record, honest metrics reported as-is.

## E1 · Evolution kernel (phase C core)

- [ ] Five-record store (#1): evidence-linked JSON store (append-only records,
      id-referenced Evidence with verbatim spans), format versioned as the
      evidence-linked family format; stdlib validator + CI enforcement.
- [ ] Trajectory store (#2): append-only per-task records (decisions, outcomes,
      quotes, provenance: model/calls/tokens/elapsed) — the corpus agents write.
- [ ] Threshold trigger (#3): evolve after N new trajectories or M days
      (configurable, state persisted); cheap and predictable.
- [ ] Evolution session (#4): hypothesis-framed rounds, candidate versions with
      parent lineage (`layer_vN`), **frozen budget** (exhaustion = incomplete;
      extension requires explicit user confirmation), atomic writes, resume.
- [ ] Evaluation gate (#5): adapter contract (evaluate a candidate vs incumbent,
      comparable results) + a seeded honest eval as the first adapter; nothing
      publishes without winning.
- [ ] SQLite semantic seed (#6): minimal Term→table/column records over one
      SQLite database — the README's live promise of phase A.
- [ ] CLI + CI + npm 0.1.0 vehicle (#7): EN-first engine, the family's proven
      distribution pattern (bin + skill + empty patch), every CI gate the
      family paid for.

## E2 · Family integration (phase C proof of generality)

- [ ] Adapter: dsh-TradingAgents verdict ledger (#8) — its settle/reflection
      loop becomes a trajectory source; evolution rounds over verdict lessons.
- [ ] Adapter: dsh-auto-ontology certifications (#9) — accepted/rejected
      verdicts as trajectory records; the ontology evolves under the same gate.
- [ ] WrenAI boundary + optional adapter (#10): settle the family division
      (this engine evolves layers; WrenAI answers through them) before E3.
- [ ] typed-tools plugin 0.2.0 (#11): `evolution_run` / `evolution_status` via
      defineTool, live-session verified before tagging.

## E3 · Semantic layer (phase A landing)

- [ ] Workload collection (#12): three sources per upstream — user questions,
      same-data history, evidence-grounded generated questions; dedupe +
      coverage-gap report.
- [ ] Schema introspection + mapping extraction (#13): SQLite → DuckDB → CSV;
      Term→table/column mappings with evidence quotes; constraints.
- [ ] `browse` answer-time semantics (#14): the agent-facing query tool.
- [ ] README story pivot (#15): first screen becomes "EvoOntology for DSH" —
      the full concept, with the honest eval numbers.

## E4 · Ecosystem

- [ ] Bounded connector breadth (#16): DuckDB/CSV solid; more only on demand —
      never chase the upstream's eight.
- [ ] Visualization (#17): session-map SVG per evolution run (family recipe).
- [ ] Format positioning (#18): evidence-linked evolution records as a
      versioned open spec — the IC-MEMO play.

## Explicit non-goals

MCP-first serving (DSH typed tools are native); eight-connector chase;
benchmark leaderboards (BEAVER et al.); competing with dsh-WrenAI on Q&A;
silent auto-modification (budget exhaustion always marks incomplete);
multi-model routing.

## Discipline (non-negotiables)

- Evidence on every record — verbatim span + source; no record without it;
- Trajectories and records are append-only; corrections are new records;
- Hypothesis before round; frozen budgets; extension is an explicit human act;
- Nothing publishes without winning an evaluation — rerunnable, seeded,
  reported as-is, even when the number is ugly;
- Every run carries provenance (model / temperature / calls / tokens / elapsed).
