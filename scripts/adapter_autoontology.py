#!/usr/bin/env python3
"""The dsh-auto-ontology adapter (E2) — the one place a model enters the kernel.

dsh-auto-ontology builds a typed layer from documents and exports what happened as
an ao-trajectory/0.1 stream: every claim with its quote and the judge's verdict on
that quote, every certification. This adapter runs ONE hypothesis round on it:

  import    the stream into the trajectory store — idempotent by event id
  project   the layer the stream describes (evoontology.project_auto_ontology: pure)
  propose   for each Term whose quotes the judge could not ground, a model reads the
            TBox and ALL the term's quotes and names ONE listed type that one quote
            states about the term — or nothing. A proposal whose type is not in the
            TBox, equals the current typing, or whose quote is not one of the term's
            own is dropped here, before any judge sees it — with its reason, and on
            disk. A quote that is one of the term's own as the sibling's verbatim rule
            sees it (markdown marks and whitespace aside) is snapped to the term's own
            string: what the judge sees and what comes back is never the model's copy.
  judge     every surviving proposal goes through dsh-auto-ontology's own eval CLI:
            the same prompt and one-quote protocol that flagged the term. Nothing
            about judging is re-implemented in this repo.
  round     candidate = the projection with its grounded re-typings, and for each
            the constraint its certification will add — the layer the trip back
            projects, no more — against the projection, under the kernel's gate.
            A won round publishes a layer and writes runs/<run>.proposals.json for
            the trip back (`auto-ontology apply --proposals`); a lost round
            publishes nothing.
            ONE stream, ONE run: an unchanged stream never opens a second run on its
            own — after a lost round, another try is `evolve extend` (recorded on the
            run); a changed stream is a new question and a new run. A crash closes its
            run as `aborted` with the reason on it. Every round keeps its own judge
            input and rows under runs/<run>.judge/round-N/.

What the gate can and cannot say: a re-typed term moves from −1 to +1 on the
endorsed share by construction, so a round with at least one judge-grounded
proposal always wins — the experiment is the judge, not the arithmetic. The
proposer and the judge are named on the run; when they are the same model the
result carries that caveat with it.
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evoontology


def _kernel(K):
    """The caller's kernel module when it hands one over — the CLI's own instance, a
    test's reloaded one — so both agree on the workspace; else the import."""
    return K or evoontology

PROPOSER_SYSTEM = (
    "You audit typed terms of an ontology built from documents. You get: a term, the type "
    "a build gave it, the ontology's type definitions, and every quote collected for the "
    "term, one JSON object per line. A strict judge found that none of the quotes states the "
    "given type about the term.\n"
    "Find the ONE listed type that one of the quotes STATES about the term, and return that "
    "line's quote value exactly as written. Rules: the value is copied from a line, never "
    "written anew and never with its source added in front of it; a quote that only mentions "
    "the term, or that is about a different thing, counts for nothing; never return the "
    "term's current type.\n"
    'Output JSON only: {"type": "<a listed type>", "quote": "<a quote value, exactly as '
    'written>", "why": "<one sentence>"} when a quote states another listed type about the '
    'term; otherwise {"type": null, "quote": null, "why": "<one sentence on why none does>"}')

HYPOTHESIS = ("For terms whose typing no carried quote grounds, one of the TBox's own types is "
              "stated by a quote the build judged against the wrong type; re-typing them raises "
              "the layer's endorsed share and changes nothing else.")
MAX_QUOTES = 40
SHOW = 8
APPLY_ACTOR = "agent:evoontology-adapter"   # what the trip back names — the candidate's constraint is written with it
_LOCK = threading.Lock()   # the proposer calls run concurrently; one ledger, no races


def resolve_auto_ontology(path=None):
    """Where the judge lives: --auto-ontology DIR, env AUTO_ONTOLOGY_HOME, or the
    `auto-ontology` executable on PATH. DIR may be the checkout or package root or
    its scripts/."""
    cands = [path, os.environ.get("AUTO_ONTOLOGY_HOME")]
    exe = shutil.which("auto-ontology")
    if exe:
        d = os.path.dirname(os.path.realpath(exe))
        cands += [os.path.join(d, ".."), d]
    for c in cands:
        for sub in ("", "scripts"):
            if c and os.path.isfile(os.path.join(c, sub, "eval_evidence.py")):
                return os.path.abspath(os.path.join(c, sub))
    sys.exit("auto-ontology not found — pass --auto-ontology <checkout or npm install>, set "
             "AUTO_ONTOLOGY_HOME, or have `auto-ontology` on PATH: its eval judges the proposals")


def _grounding(ao_dir):
    """The sibling's HTTP client, imported from the checkout that judges: one endpoint,
    one key lookup (DEEPSEEK_API_KEY, then ~/.bashrc) across the family."""
    sys.path.insert(0, ao_dir)
    import grounding
    return grounding


def tbox_of(build):
    """Entity types of a build event: [{name, desc}] — the definitions the export
    carries (`tbox.entity_type_descs`, a sibling since its apply --proposals), a
    desc on the type object for anything else shaped that way, names only for an
    export that predates both."""
    tbox = (build or {}).get("tbox", {})
    descs = tbox.get("entity_type_descs") or {}
    out = []
    for t in tbox.get("entity_types", []):
        if isinstance(t, dict):
            out.append({"name": t["name"], "desc": t.get("desc") or descs.get(t["name"], "")})
        else:
            out.append({"name": t, "desc": descs.get(t, "")})
    return out


def _propose(term, types, g, model, ledger):
    """One model call for one ungrounded Term -> (status, proposal).
    status: ok — the quote is one of the term's own, byte for byte · snapped — the same
    quote as the sibling's verbatim rule sees it (markdown marks and whitespace aside):
    the term's own string goes on, never the model's · none — the model returned null ·
    malformed — dropped with its reason, before any judge sees it."""
    defs = "".join(f"- {t['name']}: {t['desc']}\n" if t["desc"] else f"- {t['name']}\n" for t in types)
    quotes = "".join(f"[{i}] {json.dumps({'source': x.get('source', '?'), 'quote': x.get('quote', '')}, ensure_ascii=False)}\n"
                     for i, x in enumerate(term["evidence"][:MAX_QUOTES], 1))
    user = (f"Type definitions:\n{defs}\nTerm: {term['name']}\n"
            f"Current type (no quote states it): {term['ontology_type']}\n\n"
            f"Quotes collected for the term, one JSON object per line:\n{quotes}")
    out, usage = g.complete(model, [{"role": "system", "content": PROPOSER_SYSTEM},
                                    {"role": "user", "content": user}])
    with _LOCK:
        ledger["calls"] += 1
        ledger["in"] += int(usage.get("prompt_tokens") or 0)
        ledger["out"] += int(usage.get("completion_tokens") or 0)
    if not isinstance(out, dict) or out.get("type") is None:
        return "none", None
    typ, q = out.get("type"), out.get("quote")
    own = [x.get("quote") for x in term["evidence"]]

    def bad(why):
        return "malformed", {"name": term["name"], "from_type": term["ontology_type"], "to_type": typ,
                             "quote": q if isinstance(q, str) else str(q)[:80], "why": why}
    if typ not in {t["name"] for t in types}:
        return bad("a type outside the TBox")
    if typ == term["ontology_type"]:
        return bad("the term's current type")
    status = "ok"
    if q not in own:
        vis = getattr(g, "is_verbatim", None)   # a sibling older than its verbatim rule: exact match only
        both = [o for o in own if vis and isinstance(o, str) and isinstance(q, str) and vis(q, o) and vis(o, q)]
        if not both:
            part = [i for i, o in enumerate(own, 1) if vis and isinstance(o, str) and isinstance(q, str) and vis(q, o)]
            more = [i for i, o in enumerate(own, 1) if vis and isinstance(o, str) and isinstance(q, str) and vis(o, q)]
            return bad(f"part of own quote [{part[0]}], not the quote" if part else
                       f"own quote [{more[0]}] with more added" if more else "not one of the term's quotes")
        q, status = both[0], "snapped"
    doc = next(x.get("source", "?") for x in term["evidence"] if x.get("quote") == q)
    return status, {"term_id": term["id"], "name": term["name"], "domain": term["domain"],
                    "from_type": term["ontology_type"], "to_type": typ, "quote": q, "doc": doc,
                    "why": str(out.get("why") or "")[:200], **({"snapped": True} if status == "snapped" else {})}


def judge_proposals(props, types, ao_dir, model, jobs, workdir):
    """Every proposal through dsh-auto-ontology's own eval CLI — the same prompt and
    one-quote protocol that flagged the term. One temporary artifact holds the
    proposals as the assertions they would become, each carrying exactly the one
    quote to judge. -> the proposals with `judged` (True | False | None = judge error)
    and the judge's reason. The artifact and the judge's rows stay in `workdir`."""
    art = {"domain": "dsh-auto-ontology adapter proposals", "built_at": "1970-01-01T00:00:00",
           "tbox": {"entity_types": types, "relation_types": []},
           "abox": {"entities": [{"name": p["name"], "type": p["to_type"],
                                  "evidences": [{"quote": p["quote"], "doc": p["doc"]}]} for p in props],
                    "relations": []}}
    os.makedirs(workdir, exist_ok=True)
    src, rows = os.path.join(workdir, "proposals.json"), os.path.join(workdir, "rows.jsonl")
    json.dump(art, open(src, "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run([sys.executable, os.path.join(ao_dir, "eval_evidence.py"), "--from", src,
                        "--n", "0", "--jobs", str(jobs), "--judge-model", model, "--out", rows],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(rows):
        sys.exit("the judge (auto-ontology eval) failed — nothing is judged, nothing is proposed:\n"
                 f"{r.stdout[-600:]}\n{r.stderr[-600:]}")
    verdicts = {}
    for line in open(rows, encoding="utf-8"):
        row = json.loads(line)
        verdicts.setdefault(row["assertion"], []).append(row)
    out = []
    for p in props:
        row = (verdicts.get(f"{p['name']} is of type '{p['to_type']}'") or [{}])[0]
        out.append(dict(p, judged=row.get("supported"), judge_reason=row.get("reason")))
    return out


def retype(term, p, judge_model, K=None):
    """The re-typed Term: the judged quote first with its verdict; the term's other
    quotes follow unjudged — their old verdicts were about the old typing and say
    nothing about this one."""
    ev = [{"quote": p["quote"], "source": p["doc"], "verdict": "grounded",
           "by": f"judge:{judge_model}", "reason": p.get("judge_reason")}]
    ev += [{"quote": x.get("quote"), "source": x.get("source", "?"), "verdict": "unjudged"}
           for x in term["evidence"] if x.get("quote") != p["quote"]]
    K = _kernel(K)
    return dict(term, id=f"ao:term:{K._h(term['domain'], K._nk(term['name']), p['to_type'])}",
                ontology_type=p["to_type"], verdict="grounded", evidence=ev)


def _show(title, props, why="proposed"):
    for p in props[:SHOW]:
        print(f"           {title} {p['name']}: {p['from_type']} → {p['to_type']} — \"{p['quote'][:70]}\""
              + (f" ({p['judge_reason'][:60]})" if p.get("judge_reason") else "")
              + (f" — {why}: {p['why']}" if p.get("why") else ""))
    if len(props) > SHOW:
        print(f"           … and {len(props) - SHOW} more")


def run(path, auto_ontology=None, dry_run=False, proposer_model="deepseek-chat", judge_model=None, jobs=8, budget=1, K=None):
    K = _kernel(K)
    added, skipped = K.trajectory_import(path)
    print(f"import   {path}: +{added} event(s) · {skipped} already present · {K.trajectory_count()} in the store")
    proj, builds = K.project_auto_ontology(K.trajectories())
    kinds, verdicts = {}, {}
    for r in proj:
        kinds[r["type"]] = kinds.get(r["type"], 0) + 1
        verdicts[str(r.get("verdict"))] = verdicts.get(str(r.get("verdict")), 0) + 1
    print("project  " + " · ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
          + " — verdicts: " + " · ".join(f"{k} {v}" for k, v in sorted(verdicts.items())))
    bad = K.validate_records(proj)
    if bad:
        print(f"⚠ {len(bad)} projected record(s) do not validate (first: {bad[0]})")
    inc = K.evaluation_score(proj)
    print(f"gate     coverage {inc['coverage']} · cleanliness {inc['cleanliness']} · diversity {inc['diversity']}"
          f" · endorsed {inc['endorsed']} → total {inc['total']}")
    terms = [r for r in proj if r["type"] == "Term" and r.get("verdict") == "ungrounded"]
    if dry_run:
        print(f"dry run  {len(terms)} ungrounded Term(s) would go to the proposer (no model called, no run opened)")
        return

    ao_dir = resolve_auto_ontology(auto_ontology)
    g = _grounding(ao_dir)
    judge = judge_model or next(iter(builds.values()), {}).get("artifact", {}).get("judge") or "deepseek-chat"
    missing = sorted({r["domain"] for r in terms if not tbox_of(builds.get(r["domain"]))})
    if missing:
        sys.exit(f"the stream carries no build event (no TBox) for: {', '.join(missing)} — nothing to propose from")
    types = {}
    for b in builds.values():
        for t in tbox_of(b):
            types.setdefault(t["name"], t["desc"])
    types = [{"name": n, "desc": d} for n, d in types.items()]

    run_ = K.run_for_stream(K.stream_fingerprint(path), HYPOTHESIS, budget)
    try:
        return _round(K, run_, terms, proj, builds, types, proposer_model, judge, jobs, ao_dir, g)
    except BaseException as exc:          # the run is closed with the reason on it, then the error goes on
        K.run_abort(run_, f"{type(exc).__name__}: {exc}"[:200])
        raise


def _round(K, run_, terms, proj, builds, types, proposer_model, judge, jobs, ao_dir, g):
    workdir = os.path.join(K.runs_dir(), run_["run_id"] + ".judge", f"round-{run_['budget']['rounds_used'] + 1}")
    print(f"run      {run_['run_id']} · {run_['budget']['rounds_used']}/{run_['budget']['max_rounds']} round(s) used "
          f"before this one · proposer {proposer_model} · judge {judge} (auto-ontology eval) · "
          f"{len(terms)} ungrounded Term(s) to propose for")
    ledger = {"calls": 0, "in": 0, "out": 0}
    props, tally = [], {"ok": 0, "snapped": 0, "none": 0, "malformed": 0}
    malformed = []
    with cf.ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        for status, p in ex.map(lambda t: _propose(t, tbox_of(builds.get(t["domain"])), g, proposer_model, ledger), terms):
            tally[status] += 1
            (props if status in ("ok", "snapped") else malformed if p else []).append(p)
    print(f"propose  {tally['ok']} proposal(s) · {tally['snapped']} snapped to the term's own quote · "
          f"{tally['none']} null · {tally['malformed']} malformed (dropped) · "
          f"{ledger['calls']} call(s) · {ledger['in']:,} in / {ledger['out']:,} out tokens")
    _show("malformed:", malformed, why="dropped")
    os.makedirs(workdir, exist_ok=True)  # everything the proposer said is on disk before a judge runs
    json.dump({"terms": len(terms), "tally": tally, "proposals": props, "malformed": malformed},
              open(os.path.join(workdir, "proposed.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    props = judge_proposals(props, types, ao_dir, judge, jobs, workdir) if props else []
    grounded = [p for p in props if p["judged"] is True]
    refused = [p for p in props if p["judged"] is False]
    errors = [p for p in props if p["judged"] is None]
    print(f"judge    {len(grounded)} grounded · {len(refused)} not grounded · {len(errors)} judge error(s) — {judge}")
    _show("✓", grounded)
    _show("✗", refused)

    by_id = {r["id"]: r for r in proj}
    swap = {p["term_id"]: retype(by_id[p["term_id"]], p, judge) for p in grounded}
    # the candidate is the layer the trip back will project: `apply --proposals` records each
    # re-typing as a reject certification on the old typing, and that is one more record
    cand = [swap.get(r["id"], r) for r in proj]
    cand += [K.reject_constraint(by_id[p["term_id"]]["name"], p["from_type"], by_id[p["term_id"]]["domain"],
                                 APPLY_ACTOR, f"re-typed as {p['to_type']}: judge {judge} grounded another quote",
                                 dt.datetime.now().isoformat(timespec="seconds"),
                                 by_id[p["term_id"]]["evidence"][0].get("quote"),
                                 by_id[p["term_id"]]["evidence"][0].get("source", "?")) for p in grounded]
    note = {"adapter": "dsh-auto-ontology", "terms_proposed_for": len(terms), "proposals": tally,
            "grounded": len(grounded), "refused": len(refused), "judge_errors": len(errors),
            "proposer": proposer_model, "judge": judge}
    run_, rec = K.run_round(cand, run_, incumbent=proj, note=note)
    c, i = rec["candidate_score"], rec["incumbent_score"]
    print(f"round    candidate {c['total']} (endorsed {c['endorsed']}) vs incumbent {i['total']} (endorsed {i['endorsed']})")
    if rec["won"]:
        out = os.path.join(K.runs_dir(), run_["run_id"] + ".proposals.json")
        json.dump({"run_id": run_["run_id"], "at": rec["at"], "hypothesis": run_["hypothesis"],
                   "proposer_model": proposer_model, "judge_model": judge, "apply_actor": APPLY_ACTOR,
                   "proposals": [dict(p, grounded=p["judged"] is True) for p in props]},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"▲ WON    → published layer_v{rec['published_version']} · the judge's input and rows: {workdir}")
        print(f"           proposals -> {out}")
        print(f"           trip back: auto-ontology apply --proposals {out} --from <artifact.json> --actor {APPLY_ACTOR}")
    else:
        why = "no proposal survived the judge" if not grounded else "the gate kept the incumbent"
        print(f"· LOST   — {why}: nothing published (run {run_['run_id']} is {run_['status']}, "
              f"{run_['budget']['rounds_used']}/{run_['budget']['max_rounds']} round(s) used)")
