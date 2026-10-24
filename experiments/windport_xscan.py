"""Simulation check of the total threshold between direct lift S = 0 and cradle S = 1 (written as
(n − 1)(C + x·p) > h_d + (n − 2)(C + h_d − o); for the core case x·p > 884 s, x ≈ 0.25). Core case (A1 long single lane 1.2 km +
1 km/h, Q_h = 0, one vessel with 10 monopiles, first come first served, t_u = 0.05 p), roadside / pull-in cradle, direct lift on a
fine grid of x and cradle S = 1 as one level, shortest over K = 1-8 each; also records o (arrival to the vehicle body leaving the road,
lift.pair_times) for each (saddle row, lifting position) pair.
Output results/windport_conservative_xscan_<config hash>/: config.json, progress.json, points.csv, off.csv, summary.md.
Run: python experiments/windport_xscan.py --procs 4 --slots DIR
"""
import argparse
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

CODE = ["windport/lift.py", "windport/sim.py", "windport/sim2.py", "windport/archetypes.py", "occupancy/sim.py", "occupancy/network.py",
        "occupancy/params.py", "experiments/windport_extra.py", "experiments/windport_xscan.py"]
XS = [0.0, 0.1, 0.2, 0.22, 0.23, 0.24, 0.245, 0.25, 0.255, 0.26, 0.27, 0.3, 0.4, 0.5]
GRID = dict(scen="lane", mode=["on_road", "pull_in"], K=list(range(1, 9)), n_v=10)
H = 3600.0


def one(arg):
    m, arr, x, K = arg
    import windport_extra as X
    from windport import lift as LF
    from windport import sim2 as S2
    c = X.port_cfg(GRID["scen"], m, arr, K, GRID["n_v"], 0, p_extra=dict(release_frac=x) if arr == "S0" else None)
    with LF.installed():
        net, p, sim, r = S2.simulate2(c)
    ls = sorted(t["F_vessel"] for t in sim.trips if t["F_vessel"] is not None)
    return dict(mode=m, arr=arr, x=x, K=K, port_h=round((ls[GRID["n_v"] - 1] - c["cal"]["crane"][0][0] * H) / H, 6))


def chunk(items):
    return [one(a) for a in items]


def init():
    pin(list(range(1, os.cpu_count())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_extra as X
    from windport import lift as LF
    from windport import sim2 as S2
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="conservative", part="xscan", round=4, xs=XS, grid=GRID, tu=LF.TU, code=code)
    out = ROOT / "results" / ("windport_conservative_xscan_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = [(m, "S0", x, K) for m, x, K in itertools.product(GRID["mode"], XS, GRID["K"])] + [(m, "S1", 0.0, K) for m, K in itertools.product(GRID["mode"], GRID["K"])]
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "x threshold between direct lift and cradle", "conservative")
    rows = []
    for rs in slot_imap(chunk, [its[k:k + 8] for k in range(0, len(its), 8)], a.procs, initializer=init, slots_dir=a.slots, tag="conservative"):
        rows += rs
        prog.write(done=len(rows))
    rows.sort(key=lambda r: (r["mode"], r["arr"], r["x"], r["K"]))
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["mode", "arr", "x", "K", "port_h"])
        w.writeheader()
        w.writerows(rows)
    offs = []
    for m in GRID["mode"]:
        c = X.port_cfg(GRID["scen"], m, "S1", 1, GRID["n_v"], 0)
        D, net, p, *_ = S2.setup2(c)
        W = D["windport"]
        for (o, d), v in LF.pair_times(net, p, W["storage"], W["cradles"][:1]).items():
            offs.append(dict(mode=m, row=o, quay=d, TL=round(v["TL"], 3), TE=round(v["TE"], 3), off=round(v["off"], 3)))
    with open(out / "off.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(offs[0]))
        w.writeheader()
        w.writerows(offs)
    best = {}
    for r in rows:
        k = (r["mode"], r["arr"], r["x"])
        best[k] = min(best.get(k, 1e9), r["port_h"])
    L = ["# Direct lift S = 0 (fine grid of x) vs cradle S = 1: time in port of the core case (shortest over K = 1-8, t_u = 0.05 p)", "",
         "| Cradle | x | x·p s | Direct lift h | Cradle S = 1 h | Direct lift slower than cradle |", "|---|---:|---:|---:|---:|---|"]
    for m in GRID["mode"]:
        cr = best[(m, "S1", 0.0)]
        for x in XS:
            v = best[(m, "S0", x)]
            L.append(f"| {m} | {x:g} | {x * 3600:.0f} | {v:.4f} | {cr:.4f} | {'yes' if v > cr + 1e-9 else ''} |")
    L += ["", "o (arrival to the vehicle body leaving the road, lifting position = first cradle place): " + "; ".join(f"{r['mode']} {r['row']} {r['off']:.1f} s" for r in offs)]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done")
    print(out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
