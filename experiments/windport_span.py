"""Sensitivity to the extent of the area under the load. Main rule (head): the resources under the load are the apron segments,
end junctions and pull-in places within reach; the part of the reach beyond the gate is not counted, following the convention of the
occupancy model (after clear the vehicle body counts as having left the single lane). Sensitivity (gate): all segments and junctions
passed when tracing back L_v from the stopping point along the loaded route of the trip count (including the gate and the top segment of
the single lane, lift.span_res / check_lift.span); if the gate with the gate holding place lies within the reach of a used lifting
position, the gate holding place is under the load and cannot be used (Q_h set to 0; column hold_eff records the Q_h actually used).
Grid: scenarios of Table 6 of the manuscript (base, 1 km/h, long passage + 1 km/h, long single lane + 1 km/h, vessel crane 0.5 h)
× roadside / pull-in × S0, S1, S1m, S3, S3m × Q_h = 0, 1, ∞ × K = 1-8, one vessel with 10 monopiles, vessel crane open for 200 h from
G = 24 h (windport_extra.port_cfg), first come first served, t_u = 0.05 p.
Per point: time in port, new checker, L*(10) of W″_lift (a larger reach only adds constraints, so W″_lift remains an upper bound).
Output results/windport_conservative_span_<config hash>/: config.json, progress.json, points.csv, summary.md.
Run: python experiments/windport_span.py --procs 8 --slots DIR
"""
import argparse
import collections
import csv
import hashlib
import itertools
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402

CODE = ["windport/lift.py", "windport/bound_lift.py", "windport/check_lift.py", "windport/sim.py", "windport/sim2.py", "windport/bound.py",
        "windport/bound2.py", "windport/bound3.py", "windport/bound_dead.py", "windport/archetypes.py", "occupancy/sim.py", "occupancy/network.py",
        "occupancy/params.py", "experiments/windport_extra.py", "experiments/windport_span.py"]
GRID = dict(span=["head", "gate"], scen=["base", "slow", "longslow", "lane", "fastcrane"], mode=["on_road", "pull_in"],
            arr=["S0", "S1", "S1m", "S3", "S3m"], hold=["0", "1", "inf"], K=list(range(1, 9)), n_v=10)
H = 3600.0


def gate_reached(c):
    """Whether the load reach of any used lifting position (traced back L_v along the loaded route from any saddle row) extends past
    the gate where the gate holding place is."""
    from windport import lift as LF
    from windport import sim2 as S2
    D, net, p, *_ = S2.setup2(c)
    W = D["windport"]
    g = S2.idle_nodes(D)[0]
    return any(g in LF.span_res(net, d, p["Lv"], net.path(net.stops[o]["node"], net.stops[d]["node"]))[1]
               for d in W["cradles"][:max(1, c["S"])] for o in W["storage"])


def one(arg):
    span, sc, m, arr, hold, K = arg
    import windport_extra as X
    from windport import bound3 as B3
    from windport import bound_lift as BL
    from windport import check_lift as CL
    from windport import lift as LF
    from windport import sim as S
    from windport import sim2 as S2
    h = hold if hold == "inf" else int(hold)
    c = X.port_cfg(sc, m, arr, K, GRID["n_v"], h, p_extra=dict(lift_span=span) if span == "gate" else None)
    eff = hold
    if span == "gate" and hold != "0" and gate_reached(c):
        eff = "0"
        c = dict(c, hold=0)
    with LF.installed():
        net, p, sim, r = S2.simulate2(c)
        D, _, _, _, starts, quay, cal = S2.setup2(c)
        g, y = S2.idle_nodes(D)
        ck = CL.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
    G = c["cal"]["crane"][0][0] * H
    ls = sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)
    port = round((ls[GRID["n_v"] - 1] - G) / H, 6) if len(ls) >= GRID["n_v"] else ""
    lstar = round(B3.lstar(BL.wfn_lift(c, dict(BL.lift_parts(c), G=G)), GRID["n_v"])[0] / H, 6)
    return dict(span=span, scen=sc, mode=m, arr=arr, hold=hold, hold_eff=eff, K=K, port_h=port, lstar=lstar,
                check_ok=int(ck["ok"]), err=" / ".join(ck["errors"][:1]))


def chunk(items):
    return [one(x) for x in items]


def init():
    pin(list(range(1, os.cpu_count())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="conservative", part="span", round=4, grid=GRID, code=code)
    out = ROOT / "results" / ("windport_conservative_span_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = list(itertools.product(GRID["span"], GRID["scen"], GRID["mode"], GRID["arr"], GRID["hold"], GRID["K"]))
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "sensitivity to the reach under the load up to the gate", "conservative")
    rows = []
    for rs in slot_imap(chunk, [its[k:k + 8] for k in range(0, len(its), 8)], a.procs, initializer=init, slots_dir=a.slots, tag="conservative"):
        rows += rs
        prog.write(done=len(rows))
    key = lambda r: (GRID["span"].index(r["span"]), GRID["scen"].index(r["scen"]), r["mode"], r["arr"], GRID["hold"].index(r["hold"]), r["K"])
    rows.sort(key=key)
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["span", "scen", "mode", "arr", "hold", "hold_eff", "K", "port_h", "lstar", "check_ok", "err"])
        w.writeheader()
        w.writerows(rows)
    g = collections.defaultdict(list)
    for r in rows:
        g[(r["scen"], r["mode"], r["arr"], r["hold"], r["span"])].append(r)
    best = lambda rs: min((r["port_h"] for r in rs if r["port_h"] != ""), default=None)
    f4 = lambda v: "-" if v is None else f"{v:.4f}"
    L = ["# Reach under the load (head = apron segments, end junctions; gate = L_v back along the route, incl. gate and lane top)", "",
         "One vessel, 10 monopiles, FCFS, t_u = 0.05 p; min over K = 1-8; gate column: Q_h used in parentheses (0 if reached).", "",
         "| Scenario | Cradle | Lifting | Q_h | head h | gate h | Diff h |", "|---|---|---|---|---:|---:|---:|"]
    for sc, m, arr, hold in itertools.product(GRID["scen"], GRID["mode"], GRID["arr"], GRID["hold"]):
        a_, b_ = best(g[(sc, m, arr, hold, "head")]), best(g[(sc, m, arr, hold, "gate")])
        eff = sorted({r["hold_eff"] for r in g[(sc, m, arr, hold, "gate")]})
        L.append(f"| {sc} | {m} | {arr} | {hold} | {f4(a_)} | {f4(b_)} ({'/'.join(eff)}) | "
                 f"{'-' if a_ is None or b_ is None else f'{b_ - a_:+.4f}'} |")
    bad = sum(1 for r in rows if not r["check_ok"])
    lo = sum(1 for r in rows if r["port_h"] != "" and r["port_h"] < r["lstar"] - 1e-6)
    L += ["", f"Checker fails: {bad} of {len(rows)}; time in port < L*(10): {lo}; 10 not loaded: {sum(1 for r in rows if r['port_h'] == '')}."]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=L[-1][:300])
    print(out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
