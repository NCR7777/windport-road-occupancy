"""Recheck of the batches rerun under the conservative lifting rule (experiments/windport_rerun_conservative.py, windport_e2_conservative.py) with
three upper bounds. The cradle mode also keeps the area under the load closed, so all road-occupancy simulation rows are rechecked
(cradle, direct lift, mixed lifting). Simulated counts and times in port come from points.csv of the new run directories (the
simulation is not rerun).
  W″_lift  W″ under the new rule (windport/bound_lift.lift_parts; see the manuscript)
  W″_clear bound_dead.parts4(signed = "clear") (dq on the chain taken as max(0, dq), other parameters as in the original rule; holds
           only for direct lifts, so the number of direct-lift rows that exceed it is recorded separately)
  W″       bound_dead.parts4 (Corollary 6 not extended)
Configurations are restored as in experiments/windport_recheck_deadend.cfg_of. Not checked: rows with the fixed-duration
representation or with the cut as a single resource (the occupancy bounds do not apply), and the unloading rows of pub.
Window-form rows: simulated count > bound, ties (also compared with the old bound w1g / w1 recorded in the row); E2: CP-SAT best
solution and simulation > bound, proven optimum = bound; time-in-port rows: bound(time in port) < n_v, L* > time in port (time in
port is the recorded 6-decimal value rounded up by 1.8 ms).
Output results/windport_conservative_recheck_<config hash>/: config.json, progress.json, rows.csv, summary.csv, summary.md.
Run: python experiments/windport_recheck_conservative.py --procs 16 --slots DIR
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402

CODE = ["windport/lift.py", "windport/bound_lift.py", "windport/sim.py", "windport/sim2.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py",
        "windport/bound_dead.py", "windport/archetypes.py", "windport/shipyard.py", "occupancy/network.py", "occupancy/params.py",
        "experiments/windport_sim.py", "experiments/windport_runs.py", "experiments/windport_random.py", "experiments/windport_extra.py",
        "experiments/windport_recheck.py", "experiments/windport_recheck_deadend.py", "experiments/windport_e2.py",
        "experiments/windport_rerun_conservative.py", "experiments/windport_recheck_conservative.py"]
H = 3600.0
_C = {}


def dirs():
    """New run directories: batch -> directory name (from windport_rerun_conservative.config; E2 takes the latest windport_e2_conservative directory)."""
    import windport_rerun_conservative as RR
    out = {}
    for b in RR.SRC:
        cfg = RR.config(b)
        out[b] = f"windport_conservative_{b.replace(':', '_')}_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    e2 = sorted((ROOT / "results").glob("windport_conservative_e2_*"), key=lambda p: p.stat().st_mtime)
    out["e1e3:e2"] = e2[-1].name
    return out


def cfg_of(batch, row):
    if batch == "e1e3:e2":
        import windport_e2 as E2
        return E2.cfg_of(row["key"]), "e2"
    import windport_recheck_deadend as RB
    return RB.cfg_of(batch, row)


def parts(c, kind):
    from windport import bound_dead as BD
    from windport import bound_lift as BL
    key = json.dumps([{k: v for k, v in c.items() if k not in ("cal", "horizon_h", "n_load", "rule", "record", "unload_release_h")}, kind],
                     sort_keys=True, default=str)
    if key not in _C:
        _C[key] = BL.lift_parts(c) if kind == "lift" else BD.parts4(c, signed=kind)
    return _C[key]


def one(arg):
    batch, row = arg
    from windport import bound3 as B3
    from windport import bound_dead as BD
    c, form = cfg_of(batch, row)
    G = c["cal"]["crane"][0][0] * H
    from windport import bound_lift as BL
    f = {k: (BL.wfn_lift if k == "lift" else BD.wfn4)(c, dict(parts(c, k), G=G)) for k in ("lift", "clear", False)}     # W″_lift: incl. cradle ε_U tightening
    out = dict(batch=batch, key=row.get("key"), form=form, lift="direct" if c["S"] == 0 else c.get("lift", "cradle"), map=int(c["geo"].get("kind") == "map"),
               group="|".join(str(row.get(k, "")) for k in ("kind", "scen", "mode", "lift", "arr", "hold")))
    name = dict(lift="lift", clear="clear", **{"False": "plain"})
    if form == "port":
        if row.get("port_h") in (None, ""):
            return dict(out, skip=1)
        n = int(row.get("n_v") or c["n_load"])
        ph = float(row["port_h"]) * H + 0.5e-6 * H
        out.update(sim=n, port_h=row["port_h"])
        for k, g in f.items():
            ls = B3.lstar(g, n)[0] / H
            out.update({f"over_{name[str(k)]}": int(g(ph) < n), f"lstar_{name[str(k)]}": round(ls, 6),
                        f"lstar_hi_{name[str(k)]}": int(ls > float(row["port_h"]) + 1e-6)})
        return out
    L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * H
    if form == "e2":
        sim, cp = int(row["sim"]), int(row["cp_best"])
        out.update(sim=sim, cp=cp, cp_status=row["cp_status"])
        for k, g in f.items():
            v = g(L)
            out.update({f"b_{name[str(k)]}": v, f"over_{name[str(k)]}": int(max(sim, cp) > v), f"tie_{name[str(k)]}": int(row["cp_status"] == "OPTIMAL" and cp == v)})
        return out
    sim = int(row["sim"])
    old = row.get("w1g") if row.get("w1g") not in (None, "") else row.get("w1")
    out.update(sim=sim, old=old, tie_old=int(old not in (None, "") and sim == int(float(old))))
    for k, g in f.items():
        v = g(L)
        out.update({f"b_{name[str(k)]}": v, f"over_{name[str(k)]}": int(sim > v), f"tie_{name[str(k)]}": int(sim == v)})
    return out


def chunk(items):
    return [one(x) for x in items]


def init():
    pin(list(range(1, os.cpu_count())))


def items(D):
    out = []
    for b, d in D.items():
        rows = list(csv.DictReader(open(ROOT / "results" / d / "points.csv", encoding="utf-8")))
        for r in rows:
            if b == "e1e3:e2":
                out.append((b, r))
                continue
            if b == "extra:fix" or r.get("repr") == "fixed" or r.get("rep") in ("fix", "cut") or r["key"].startswith("fix|"):
                continue
            if b == "extra:pub" and r["pub"] != "out":
                continue
            out.append((b, r))
    out.sort(key=lambda x: (x[0], json.dumps({k: v for k, v in x[1].items() if k in ("kind", "scen", "mode", "S", "K", "lift", "hold", "lev", "par", "val",
                                                                                     "arr", "geo", "x", "what", "site")}, sort_keys=True)))
    return out


COLS = ["batch", "key", "form", "lift", "map", "sim", "cp", "cp_status", "old", "tie_old", "port_h"] + \
    [f"{a}_{k}" for k in ("lift", "clear", "plain") for a in ("b", "over", "tie", "lstar", "lstar_hi")] + ["group"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    D = dirs()
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    src = {b: hashlib.sha256((ROOT / "results" / d / "points.csv").read_bytes()).hexdigest() for b, d in D.items()}
    cfg = dict(task="conservative", part="recheck", round=4, dirs=D, points_sha256=src, code=code)
    out = ROOT / "results" / ("windport_conservative_recheck_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = items(D)
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "recheck under the conservative lifting rule (W″_lift, W″_clear, W″)", "conservative")
    res = []
    try:
        for rs in slot_imap(chunk, [its[k:k + 200] for k in range(0, len(its), 200)], a.procs, initializer=init, slots_dir=a.slots, tag="conservative"):
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res.sort(key=lambda r: (r["batch"], str(r["key"])))
    with open(out / "rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(res)
    by = collections.defaultdict(list)
    for r in res:
        by[r["batch"]].append(r)
    K3 = ("lift", "clear", "plain")
    summ = []
    for b, rs in sorted(by.items()):
        win = [r for r in rs if r["form"] in ("win", "e2") and not r.get("skip")]
        prt = [r for r in rs if r["form"] == "port" and not r.get("skip")]
        s = dict(batch=b, rows=len(rs), maps=sum(r["map"] for r in rs), win=len(win), port=len(prt), skipped=sum(r.get("skip", 0) for r in rs),
                 tie_old=sum(r.get("tie_old", 0) for r in win), over_clear_direct=sum(r.get("over_clear", 0) for r in rs if r["lift"] == "direct"))
        for k in K3:
            s.update({f"over_{k}": sum(r.get(f"over_{k}", 0) for r in rs), f"tie_{k}": sum(r.get(f"tie_{k}", 0) for r in win),
                      f"lstar_hi_{k}": sum(r.get(f"lstar_hi_{k}", 0) for r in prt)})
        summ.append(s)
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(summ[0]))
        w.writeheader()
        w.writerows(summ)
    L = ["# Recheck: all road-occupancy simulation rows under the conservative lifting rule (new run directories, bounds recomputed only)", "",
         "| Batch | Rows | On shipyard maps | Window form / time-in-port form | Sim > W″_lift / W″_clear / W″ | Ties (window form) old bound → W″ → W″_clear → W″_lift | "
         "L* > time in port: W″_lift / W″_clear / W″ |", "|---|---:|---:|---|---|---|---|"]
    for s in summ:
        L.append(f"| {s['batch']} | {s['rows']:,} | {s['maps']:,} | {s['win']:,} / {s['port']:,}" + (f" (not filled, not checked: {s['skipped']})" if s["skipped"] else "") +
                 f" | {s['over_lift']} / {s['over_clear']} / {s['over_plain']} | {s['tie_old']:,} → {s['tie_plain']:,} → {s['tie_clear']:,} → {s['tie_lift']:,} | "
                 f"{s['lstar_hi_lift']} / {s['lstar_hi_clear']} / {s['lstar_hi_plain']} |")
    tot = {k: sum(s[k] for s in summ) for k in summ[0] if k != "batch"}
    L.append(f"| Total | {tot['rows']:,} | {tot['maps']:,} | {tot['win']:,} / {tot['port']:,} | {tot['over_lift']} / {tot['over_clear']} / {tot['over_plain']} | "
             f"{tot['tie_old']:,} → {tot['tie_plain']:,} → {tot['tie_clear']:,} → {tot['tie_lift']:,} | {tot['lstar_hi_lift']} / {tot['lstar_hi_clear']} / "
             f"{tot['lstar_hi_plain']} |")
    L += ["", "Ties in the E2 row count instances where the CP-SAT proven optimum = bound (540 instances). W″_clear holds only for direct lifts; "
          f"{tot['over_clear_direct']} direct-lift rows exceed it, the remaining rows are those where the handover is a set-down."]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=f"{tot['rows']} rows; sim > W″_lift {tot['over_lift']}, > W″_clear {tot['over_clear']}, > W″ {tot['over_plain']}")
    print(out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
