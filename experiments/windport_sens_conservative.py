"""Two sensitivity groups of the core case under the conservative lifting rule.
Grid: A1 long single lane (one 1.2 km segment) / long passage + 1 km/h × roadside / pull-in cradle × arrangement S0 direct lift,
S1, S3 cradle, S1m, S3m mixed lifting × K = 1-8, one vessel with 10 monopiles, Q_h = 0, vessel crane open for 200 h from G = 24 h
(as windport_extra.port_cfg), first come first served.
Variants:
  orig        original rule (windport.sim.PortSim: lifting may start while the vehicle tail is still on the single lane, no closure)
  tu0         conservative rule, closure time under the load t_u = 0 (at x = 0 only the clear constraint applies)
  tu05        conservative rule, t_u = 0.05 p (main rule)
  tu10        conservative rule, t_u = 0.1 p
  shift_orig  first cradle 150 m from the gate (≥ L_v = 110 m, whole vehicle stands on the apron), original rule
  shift_tu05  as above, conservative rule t_u = 0.05 p
Per point: time in port, new checker (windport/check_lift.py; points of the original rule are not checked against the new rule), and
for points of the conservative rule also L*(10) of W″_lift.
Output results/windport_conservative_sens_<config hash>/: config.json, progress.json, points.csv, summary.md.
Run: python experiments/windport_sens_conservative.py --procs 12 --slots DIR
"""
import argparse
import collections
import contextlib
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
        "occupancy/params.py", "experiments/windport_extra.py", "experiments/windport_sens_conservative.py"]
VARIANTS = dict(orig=dict(new=False, tu=None, first=None), tu0=dict(new=True, tu=0.0, first=None), tu05=dict(new=True, tu=0.05, first=None),
                tu10=dict(new=True, tu=0.1, first=None), shift_orig=dict(new=False, tu=None, first=150.0), shift_tu05=dict(new=True, tu=0.05, first=150.0))
GRID = dict(scen=["lane", "longslow"], mode=["on_road", "pull_in"], arr=["S0", "S1", "S1m", "S3", "S3m"], K=list(range(1, 9)), n_v=10)
H = 3600.0


def one(arg):
    var, sc, m, arr, K = arg
    import windport_extra as X
    from windport import bound3 as B3
    from windport import bound_lift as BL
    from windport import check_lift as CL
    from windport import lift as LF
    from windport import sim as S
    from windport import sim2 as S2
    v = VARIANTS[var]
    c = X.port_cfg(sc, m, arr, K, GRID["n_v"], 0, p_extra=None if v["tu"] is None else dict(lift_tu=v["tu"]))
    if v["first"] is not None:
        c["geo"] = dict(c["geo"], first_cradle_m=v["first"])
    saved = S2.build_map
    S2.build_map = LF.build_map                           # first cradle position (rule unchanged)
    try:
        with (LF.installed() if v["new"] else contextlib.nullcontext()):
            net, p, sim, r = S2.simulate2(c)
            D, _, _, _, starts, quay, cal = S2.setup2(c)
            out = dict(var=var, scen=sc, mode=m, arr=arr, K=K)
            ls = sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)
            out["port_h"] = round((ls[GRID["n_v"] - 1] - c["cal"]["crane"][0][0] * H) / H, 6)
            if v["new"]:
                g, y = S2.idle_nodes(D)
                ck = CL.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
                G = c["cal"]["crane"][0][0] * H
                out.update(check_ok=int(ck["ok"]), lstar=round(B3.lstar(BL.wfn_lift(c, dict(BL.lift_parts(c), G=G)), GRID["n_v"])[0] / H, 6))
        return out
    finally:
        S2.build_map = saved


def chunk(items):
    return [one(x) for x in items]


def init():
    pin(list(range(1, os.cpu_count())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="conservative", part="sens", round=4, variants=VARIANTS, grid=GRID, code=code)
    out = ROOT / "results" / ("windport_conservative_sens_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = [(v, sc, m, arr, K) for v, sc, m, arr, K in itertools.product(VARIANTS, GRID["scen"], GRID["mode"], GRID["arr"], GRID["K"])]
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "sensitivity to t_u and to the first cradle position", "conservative")
    rows = []
    for rs in slot_imap(chunk, [its[k:k + 8] for k in range(0, len(its), 8)], a.procs, initializer=init, slots_dir=a.slots, tag="conservative"):
        rows += rs
        prog.write(done=len(rows))
    rows.sort(key=lambda r: (list(VARIANTS).index(r["var"]), r["scen"], r["mode"], r["arr"], r["K"]))
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["var", "scen", "mode", "arr", "K", "port_h", "lstar", "check_ok"])
        w.writeheader()
        w.writerows(rows)
    g = collections.defaultdict(list)
    for r in rows:
        g[(r["scen"], r["mode"], r["arr"], r["var"])].append(r)
    fmt = lambda rs: f"{min(r['port_h'] for r in rs):.4f}" + (f" ({min(r['lstar'] for r in rs):.4f})" if "lstar" in rs[0] else "")
    L = ["# Sensitivity of the core case (one vessel, 10 monopiles, Q_h = 0, first come first served; shortest over K = 1-8; in parentheses L*(10) of W″_lift, also minimised over K)", "",
         "| Scenario | Cradle | Lifting | " + " | ".join(VARIANTS) + " |", "|---|---|---|" + "---:|" * len(VARIANTS)]
    for sc, m, arr in itertools.product(GRID["scen"], GRID["mode"], GRID["arr"]):
        L.append(f"| {sc} | {m} | {arr} | " + " | ".join(fmt(g[(sc, m, arr, v)]) for v in VARIANTS) + " |")
    L += ["", f"New checker fails at {sum(1 for r in rows if r.get('check_ok') == 0)} points (of {sum(1 for r in rows if 'check_ok' in r)} conservative-rule points); "
          f"time in port < L* at {sum(1 for r in rows if 'lstar' in r and r['port_h'] < r['lstar'] - 1e-6)} points."]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=L[-1][:300])
    print(out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
