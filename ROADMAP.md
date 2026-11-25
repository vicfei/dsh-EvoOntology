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

- [x] Five-record store (2026-11-19, PR #19): Term/Mapping/Relation/Constraint/
      Evidence in append-only JSONL (<workspace>/.evo, EVO_HOME); dual evidence
      representation (inline span OR evidence_ids); the validator also accepts
      sibling v0.1 ontology artifacts — one family, one evidence contract; ghost
      records rejected at add time; CI: pure semantics + clean-workspace CLI e2e.
- [x] Trajectory store (2026-11-19, PR #20): <workspace>/trajectories/<task_id>.json;
      agent + summary required; task_id/recorded_at auto-filled; provenance passthrough;
      append-only enforced (duplicate task_id rejected, never silently overwritten).
- [x] Threshold trigger (2026-11-19, PR #21): deterministic (state, count, now) →
      (due, reason); three paths — first-evolution bootstrap (non-empty corpus with no
      prior state), volume (≥ N new), time (≥ M days AND new material — never an empty
      spin); state.json persisted; --mark records an evolution ran.
- [x] Evolution session (#4) (2026-11-19, PR #23): hypothesis-framed rounds,
      candidate versions with parent lineage (`layer_vN`), **frozen budget**
      (exhaustion = incomplete; extension requires explicit user confirmation).
- [x] Evaluation gate (2026-11-19, PR #23): the first adapter is fully deterministic
      (evidence coverage + cleanliness 1/(1+violations) + type diversity); strict
      publishing: candidate.total > incumbent.total (ties keep the incumbent).
      Ghost records lower the score; zero LLM.
- [x] SQLite semantic seed (2026-11-19, PR #24): sqlite_master DDL → Term+Mapping
      per column, evidence = verbatim CREATE TABLE; deterministic (same DB same
      records, zero LLM); CI-tested.
- [x] CLI + CI + npm 0.1.0 vehicle (2026-11-19, PR #25): bin 'evoontology' + skill +
      empty patch (typed-tools is 0.2.0 #11); CI: syntax + record/trajectory/trigger/
      session+gate/seed pure tests + node --check bin + pack clean; fresh-install
      smoke verified (seed/validate/trigger/record list).

## E2 · Family integration (phase C proof of generality)

- [ ] Adapter: dsh-TradingAgents verdict ledger (#8) — its settle/reflection
      loop becomes a trajectory source; evolution rounds over verdict lessons.
- [x] Adapter: dsh-auto-ontology (#9) (2026-11-25, PR #27): its
      `ao-trajectory/0.1` export imports as trajectories (idempotent by event
      id) and projects to a layer where every record carries its quotes with
      their verdicts; accepted/rejected certifications ride along (a reject
      becomes a Constraint). One hypothesis round: a proposer re-types the terms
      no quote grounds, the sibling's **own eval CLI** judges, the gate adds an
      `endorsed` term; the round trip is `auto-ontology apply --proposals`
      (recorded certification + new assertion, never a silent edit). Kernel
      stays zero-LLM; the model calls live in `scripts/adapter_autoontology.py`.
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
