#!/usr/bin/env python3
"""evoontology — the self-evolution kernel for DeepSeek Harness (phase E1)

Phase C core, deliberately ZERO-LLM: every mechanism here is deterministic and
stdlib-only, testable in CI, demoable without an API key. The LLM enters only
at the adapters (E2) and the semantic-layer build (E3).

Record store (issue #1): an append-only JSONL of five record types — Term,
Mapping, Relation, Constraint, Evidence — under <workspace>/records.jsonl.
Evidence is the constitution, with a dual representation for a free bridge to
the family formats:
  - inline:  record.evidence = [{"quote": "...", "source": "..."}]
  - by ref:  record.evidence_ids = [id, ...] pointing at Evidence records
A record carrying neither is invalid ("no record without evidence").

The validator also accepts the sibling format v0.1 ontology artifacts
(domain/tbox/abox with inline spans) so dsh-auto-ontology files validate here
unchanged — one family, one evidence contract.

Usage:
  python3 scripts/evoontology.py validate <paths...>        # records files AND/OR v0.1 artifacts
  python3 scripts/evoontology.py record add --json '{"type":"Term",...}'
  python3 scripts/evoontology.py record list [--type Term]
"""
import argparse, datetime as dt, json, os, sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG = os.environ.get("EVO_LANG") or "en"
def tt(en, zh):
    return en if LANG == "en" else zh

WORKSPACE = os.environ.get("EVO_HOME") or os.path.join(os.getcwd(), ".evo")
RECORD_TYPES = ("Term", "Mapping", "Relation", "Constraint", "Evidence")
FORMAT_VERSION = "evidence-linked/v0.2"


def ws():
    os.makedirs(WORKSPACE, exist_ok=True)
    return WORKSPACE


# ── record store (pure; CI-tested) ──────────────────────────────────────────

def _has_evidence(rec, evidence_ids):
    inline = [e for e in rec.get("evidence", []) if isinstance(e, dict) and e.get("quote")]
    return bool(inline) or any(i for i in rec.get("evidence_ids", []) if i in evidence_ids)


def validate_records(records):
    """Five-record conformance. Returns a list of violation strings (empty = ok)."""
    v, ids, evidence_ids = [], set(), set()
    for i, rec in enumerate(records):
        rid = rec.get("id")
        if not rid:
            v.append(f"record[{i}]: missing id")
        elif rid in ids:
            v.append(f"record[{i}]: duplicate id {rid!r}")
        else:
            ids.add(rid)
        if rec.get("type") not in RECORD_TYPES:
            v.append(f"{rid or i}: type {rec.get('type')!r} not in {RECORD_TYPES}")
            continue
        if not rec.get("recorded_at"):
            v.append(f"{rid}: missing recorded_at")
        if rec["type"] == "Evidence":
            if not (rec.get("quote") and rec.get("source")):
                v.append(f"{rid}: Evidence needs quote + source")
            else:
                evidence_ids.add(rid)
    for rec in records:
        rid, rtype = rec.get("id", "?"), rec.get("type")
        if rtype == "Evidence" or rtype not in RECORD_TYPES:
            continue
        if not _has_evidence(rec, evidence_ids):
            v.append(f"{rid}: no evidence (inline quote or evidence_ids) — the constitution")
        if rtype == "Term" and not rec.get("name"):
            v.append(f"{rid}: Term needs a name")
        if rtype == "Mapping" and not (rec.get("term") and rec.get("target")):
            v.append(f"{rid}: Mapping needs term + target")
        if rtype == "Relation" and not all(rec.get(k) for k in ("subject", "predicate", "object")):
            v.append(f"{rid}: Relation needs subject/predicate/object")
        if rtype == "Constraint" and not rec.get("rule"):
            v.append(f"{rid}: Constraint needs a rule")
        dangling = [i for i in rec.get("evidence_ids", []) if i not in evidence_ids and i not in ids]
        # refs to non-Evidence ids are dangling; refs to Evidence ids collected above
        ev_only = {r["id"] for r in records if r.get("type") == "Evidence"}
        dangling = [i for i in rec.get("evidence_ids", []) if i not in ev_only]
        if dangling:
            v.append(f"{rid}: evidence_ids {dangling} do not reference Evidence records")
    return v


def validate_v01_artifact(o):
    """Sibling-format acceptance: dsh-auto-ontology v0.1 ontology artifacts."""
    v = []
    for k in ("domain", "built_at", "tbox", "abox", "stats"):
        if k not in o:
            v.append(f"artifact missing key: {k}")
    tbox_types = {t.get("name") for t in o.get("tbox", {}).get("entity_types", [])}
    for e in o.get("abox", {}).get("entities", []):
        if not (e.get("evidences") or [{}])[0].get("quote") and not e.get("evidence"):
            v.append(f"entity {e.get('name')!r}: no evidence span")
        if e.get("type") not in tbox_types:
            v.append(f"entity {e.get('name')!r}: type not in tbox")
    for r in o.get("abox", {}).get("relations", []):
        if not (r.get("evidences") or [{}])[0].get("quote") and not r.get("evidence"):
            v.append(f"relation {r.get('subject')}-{r.get('predicate')}: no evidence span")
    return v


def load_records(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def record_add(payload):
    rec = dict(payload)
    rec.setdefault("id", f"rec_{dt.datetime.now().strftime('%H%M%S%f')[:10]}")
    rec.setdefault("recorded_at", dt.datetime.now().isoformat(timespec="seconds"))
    errs = validate_records([rec] + load_records(os.path.join(ws(), "records.jsonl"))
                             if os.path.exists(os.path.join(ws(), "records.jsonl")) else [rec])
    blocking = [e for e in errs if rec["id"] in e]
    if blocking:
        sys.exit(tt("record rejected:\n  " + "\n  ".join(blocking), "记录被拒：\n  " + "\n  ".join(blocking)))
    with open(os.path.join(ws(), "records.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


# ── trajectory store (issue #2, pure) ────────────────────────────────────────

def trajectory_dir():
    d = os.path.join(ws(), "trajectories")
    os.makedirs(d, exist_ok=True)
    return d


def trajectory_append(payload):
    """One per-task record, append-only: what the agent did, verbatim.
    Deterministic fields auto-filled (task_id, recorded_at); provenance
    (model/calls/tokens/elapsed) passes through when the source carries it."""
    rec = dict(payload)
    if not rec.get("agent") or not rec.get("summary"):
        sys.exit(tt("trajectory needs at least agent + summary (what ran, what happened)",
                    "轨迹至少需要 agent + summary（谁跑的、结果如何）"))
    rec.setdefault("task_id", f"traj_{dt.datetime.now().strftime('%H%M%S%f')[:10]}")
    rec.setdefault("recorded_at", dt.datetime.now().isoformat(timespec="seconds"))
    path = os.path.join(trajectory_dir(), rec["task_id"] + ".json")
    if os.path.exists(path):
        sys.exit(tt(f"task_id {rec['task_id']} already exists — trajectories are append-only, pick a new id",
                    f"task_id {rec['task_id']} 已存在——轨迹 append-only，请换新 id"))
    json.dump(rec, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return rec


def trajectory_count():
    d = trajectory_dir()
    return len([f for f in os.listdir(d) if f.endswith(".json")]) if os.path.isdir(d) else 0


# ── threshold trigger (issue #3, pure) ───────────────────────────────────────

def trigger_state():
    """Persisted under <workspace>/state.json: cheap, predictable, inspectable."""
    path = os.path.join(ws(), "state.json")
    return json.load(open(path)) if os.path.exists(path) else {}


def trigger_due(state, trajectory_count, now=None, min_trajectories=10, min_days=7):
    """Evolve after N new trajectories or M days since the last evolution —
    deterministic: same inputs, same verdict, same reason string."""
    now = now or dt.datetime.now()
    last = state.get("last_evolution_at")
    last_count = state.get("trajectory_count_at_last", 0)
    new_since = trajectory_count - last_count
    if new_since >= min_trajectories:
        return True, f"due: {new_since} new trajectories (threshold {min_trajectories})"
    if last is None and trajectory_count > 0:
        return True, "due: first evolution with a non-empty corpus"
    if last is not None:
        days = (now - dt.datetime.fromisoformat(last)).days
        if days >= min_days and new_since > 0:
            return True, f"due: {days} days elapsed with {new_since} new trajectories"
    return False, (f"not due: {new_since}/{min_trajectories} new trajectories"
                   if last is not None else "not due: empty corpus")


def trigger_mark(state):
    state["last_evolution_at"] = dt.datetime.now().isoformat(timespec="seconds")
    state["trajectory_count_at_last"] = trajectory_count()
    json.dump(state, open(os.path.join(ws(), "state.json"), "w"), indent=1)
    return state


# ── version store (issue #4) ─────────────────────────────────────────────────

def versions_dir():
    d = os.path.join(ws(), "versions")
    os.makedirs(d, exist_ok=True)
    return d


def latest_version():
    """Highest layer_vN on disk (0 = no version yet)."""
    import re
    best = 0
    for f in os.listdir(versions_dir()):
        m = re.match(r"layer_v(\d+)\.json$", f)
        if m:
            best = max(best, int(m.group(1)))
    return best


def snapshot_version(n, records, note=""):
    """Persist a version: layer_vN.json = records snapshot + metadata."""
    path = os.path.join(versions_dir(), f"layer_v{n}.json")
    if os.path.exists(path):
        sys.exit(tt(f"layer_v{n} already exists — versions are immutable", f"layer_v{n} 已存在——版本不可改"))
    doc = {"version": n, "recorded_at": dt.datetime.now().isoformat(timespec="seconds"),
           "note": note, "record_count": len(records), "records": records}
    json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return path


def load_version(n):
    return json.load(open(os.path.join(versions_dir(), f"layer_v{n}.json"), encoding="utf-8"))


# ── evaluation gate (issue #5) — the first adapter is deterministic ─────────

def evaluation_score(records):
    """Deterministic scoring: rerunnable by anyone, zero LLM.
    Higher is better; ties keep the incumbent (conservative)."""
    if not records:
        return {"total": 0.0, "coverage": 0.0, "cleanliness": 0.0, "diversity": 0.0, "count": 0}
    evidence_ids = {r["id"] for r in records if r.get("type") == "Evidence" and r.get("quote")}
    with_ev = sum(1 for r in records if r.get("type") != "Evidence" and
                  _has_evidence(r, evidence_ids))
    non_ev = sum(1 for r in records if r.get("type") != "Evidence")
    coverage = with_ev / non_ev if non_ev else 1.0
    violations = validate_records(records)
    cleanliness = 1.0 / (1.0 + len(violations))
    types_used = len({r.get("type") for r in records if r.get("type") in RECORD_TYPES})
    diversity = types_used / len(RECORD_TYPES)
    return {"total": round(coverage + cleanliness + diversity, 4),
            "coverage": round(coverage, 4), "cleanliness": round(cleanliness, 4),
            "diversity": round(diversity, 4), "violations": len(violations), "count": len(records)}


def gate_decides(candidate_score, incumbent_score):
    """Publish iff candidate.total > incumbent.total (strict: ties keep the incumbent)."""
    return candidate_score["total"] > incumbent_score["total"]


# ── evolution session (issue #4) ─────────────────────────────────────────────

def runs_dir():
    d = os.path.join(ws(), "runs")
    os.makedirs(d, exist_ok=True)
    return d


def run_path(run_id):
    return os.path.join(runs_dir(), f"{run_id}.json")


def run_start(hypothesis, budget=3):
    """Open an evolution run: hypothesis required, budget frozen from birth."""
    if not hypothesis.strip():
        sys.exit(tt("a run needs a hypothesis — what are you trying to improve?", "一次运行需要假设——你想改进什么？"))
    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    parent = latest_version()
    run = {"run_id": run_id, "hypothesis": hypothesis, "parent_version": parent,
           "budget": {"max_rounds": budget, "rounds_used": 0},
           "status": "running", "rounds": [], "accepted_version": None,
           "started_at": dt.datetime.now().isoformat(timespec="seconds")}
    json.dump(run, open(run_path(run_id), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return run


def run_load(run_id=None):
    """Load a run by id, or the newest running one."""
    if run_id:
        return json.load(open(run_path(run_id), encoding="utf-8"))
    runs = sorted(f for f in os.listdir(runs_dir()) if f.endswith(".json"))
    for f in reversed(runs):
        r = json.load(open(os.path.join(runs_dir(), f), encoding="utf-8"))
        if r["status"] == "running":
            return r
    sys.exit(tt("no running evolution session (start one with evolve start)", "无运行中的演化会话（先 evolve start）"))


def run_save(run):
    json.dump(run, open(run_path(run["run_id"]), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def run_round(candidate_records, run=None):
    """One round: evaluate a candidate against the incumbent, publish iff it wins.
    Budget is frozen at birth; exhaustion marks incomplete (extension is explicit)."""
    run = run or run_load()
    if run["status"] != "running":
        sys.exit(tt(f"run {run['run_id']} is {run['status']} — cannot open rounds", f"运行 {run['run_id']} 已 {run['status']}——无法开轮"))
    if run["budget"]["rounds_used"] >= run["budget"]["max_rounds"]:
        run["status"] = "incomplete"
        run["incomplete_reason"] = "budget_exhausted"
        run_save(run)
        sys.exit(tt(f"budget exhausted after {run['budget']['max_rounds']} rounds; "
                    f"extend with evolve extend (explicit human act) or end the run",
                    f"预算耗尽（{run['budget']['max_rounds']} 轮）；用 evolve extend 显式扩展或结束运行"))
    incumbent_n = run.get("accepted_version") or run["parent_version"]
    incumbent_records = (load_version(incumbent_n)["records"] if incumbent_n > 0
                         else load_records(os.path.join(ws(), "records.jsonl"))
                         if os.path.exists(os.path.join(ws(), "records.jsonl")) else [])
    cand_score = evaluation_score(candidate_records)
    inc_score = evaluation_score(incumbent_records)
    won = gate_decides(cand_score, inc_score)
    run["budget"]["rounds_used"] += 1
    round_rec = {"round": run["budget"]["rounds_used"],
                 "candidate_score": cand_score, "incumbent_score": inc_score,
                 "won": won, "at": dt.datetime.now().isoformat(timespec="seconds")}
    if won:
        new_n = latest_version() + 1
        snapshot_version(new_n, candidate_records,
                         note=run["hypothesis"])
        run["accepted_version"] = new_n
        run["status"] = "completed"
        round_rec["published_version"] = new_n
    run["rounds"].append(round_rec)
    run_save(run)
    return run, round_rec


def run_extend(run_id=None, extra=2):
    """Explicit budget extension — the human act."""
    run = run_load(run_id)
    run["budget"]["max_rounds"] += extra
    if run["status"] == "incomplete":
        run["status"] = "running"
        run.pop("incomplete_reason", None)
    run_save(run)
    return run


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    global LANG
    ap = argparse.ArgumentParser(prog="evoontology")
    ap.add_argument("--lang", choices=("en", "zh"), default=LANG)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("paths", nargs="+")
    ra = sub.add_parser("record")
    rsub = ra.add_subparsers(dest="rcmd", required=True)
    add = rsub.add_parser("add")
    add.add_argument("--json", required=True, help="record payload JSON (id/recorded_at auto-filled)")
    rsub.add_parser("list")
    ev = sub.add_parser("evolve")
    esub = ev.add_subparsers(dest="ecmd", required=True)
    estart = esub.add_parser("start")
    estart.add_argument("--hypothesis", required=True)
    estart.add_argument("--budget", type=int, default=3)
    eround = esub.add_parser("round")
    eround.add_argument("--records", required=True, help="path to candidate records JSONL")
    eround.add_argument("--run", default=None)
    estatus = esub.add_parser("status")
    estatus.add_argument("--run", default=None)
    eextend = esub.add_parser("extend")
    eextend.add_argument("--extra", type=int, default=2)
    eextend.add_argument("--run", default=None)
    tg = sub.add_parser("trigger")
    tg.add_argument("--trajectories", type=int, default=10, help="N new trajectories to trigger (default 10)")
    tg.add_argument("--days", type=int, default=7, help="M days to trigger (default 7)")
    tg.add_argument("--mark", action="store_true", help="record that an evolution just ran")
    tr = sub.add_parser("trajectory")
    tsub = tr.add_subparsers(dest="tcmd", required=True)
    tadd = tsub.add_parser("append")
    tadd.add_argument("--json", required=True, help="trajectory payload (agent+summary required; task_id/recorded_at auto)")
    tsub.add_parser("count")
    args = ap.parse_args()
    LANG = args.lang

    if args.cmd == "validate":
        bad = 0
        for p in args.paths:
            try:
                text = open(p, encoding="utf-8").read()
                if text.lstrip().startswith("{") and "domain" in text[:400] and "abox" in text[:2000]:
                    errs = validate_v01_artifact(json.loads(text))
                    kind = "v0.1 artifact"
                else:
                    errs = validate_records(load_records(p))
                    kind = "records"
            except Exception as exc:
                print(f"✗ {p}: unreadable ({exc})")
                bad += 1
                continue
            if errs:
                bad += 1
                print(f"✗ {p} ({kind}):")
                for e in errs[:10]:
                    print(f"  - {e}")
            else:
                print(f"✓ {p} conforms ({kind}, {FORMAT_VERSION})")
        sys.exit(1 if bad else 0)

    if args.cmd == "evolve":
        if args.ecmd == "start":
            run = run_start(args.hypothesis, args.budget)
            print(f"run {run['run_id']} opened · hypothesis: {run['hypothesis'][:60]}")
            print(f"  parent: layer_v{run['parent_version']} · budget: {run['budget']['max_rounds']} rounds (frozen)")
        elif args.ecmd == "round":
            run, rec = run_round(load_records(args.records), run=json.load(open(run_path(args.run))) if args.run else None)
            won = "▲ WON" if rec["won"] else "· LOST"
            print(f"round {rec['round']}: {won}")
            print(f"  candidate {rec['candidate_score']['total']} vs incumbent {rec['incumbent_score']['total']}")
            if rec.get("published_version"):
                print(f"  → published as layer_v{rec['published_version']} · run {run['run_id']} completed")
        elif args.ecmd == "status":
            run = run_load(args.run) if args.run else run_load()
            print(f"run {run['run_id']} · {run['status']} · hypothesis: {run['hypothesis'][:60]}")
            print(f"  rounds {run['budget']['rounds_used']}/{run['budget']['max_rounds']}"
                  + (f" · accepted: layer_v{run['accepted_version']}" if run.get("accepted_version") else ""))
            for r in run["rounds"]:
                mark = "▲" if r["won"] else "·"
                print(f"  {mark} round {r['round']}: cand {r['candidate_score']['total']} vs inc {r['incumbent_score']['total']}")
        elif args.ecmd == "extend":
            run = run_extend(args.run, args.extra)
            print(f"extended to {run['budget']['max_rounds']} rounds · status: {run['status']}")

    if args.cmd == "trigger":
        state = trigger_state()
        if args.mark:
            trigger_mark(state)
            print(tt(f"marked: last_evolution_at={state['last_evolution_at']} · counted {state['trajectory_count_at_last']}",
                     f"已标记：last_evolution_at={state['last_evolution_at']} · 计 {state['trajectory_count_at_last']} 条"))
        else:
            due, why = trigger_due(state, trajectory_count(), min_trajectories=args.trajectories, min_days=args.days)
            print(("▲ " if due else "· ") + why)

    if args.cmd == "trajectory":
        if args.tcmd == "append":
            rec = trajectory_append(json.loads(args.json))
            print(f"+ {rec['task_id']} ({rec['agent']}) → {os.path.join(ws(), 'trajectories')}")
        else:
            print(trajectory_count())

    if args.cmd == "record":
        path = os.path.join(ws(), "records.jsonl")
        if args.rcmd == "add":
            rec = record_add(json.loads(args.json))
            print(f"+ {rec['id']} ({rec['type']}) → {path}")
        else:  # list
            if not os.path.exists(path):
                print(tt("(no records yet)", "（暂无记录）"))
                return
            for rec in load_records(path):
                ev = (rec.get("evidence") or [{}])[0].get("quote", "") or ",".join(rec.get("evidence_ids", []))
                print(f"{rec['id']}  {rec['type']:<11} {str(rec.get('name') or rec.get('rule') or rec.get('predicate') or rec.get('quote'))[:38]:<38} | {ev[:40]}")


if __name__ == "__main__":
    main()
