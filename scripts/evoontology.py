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
