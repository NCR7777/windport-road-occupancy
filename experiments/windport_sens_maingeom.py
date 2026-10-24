"""t_u sensitivity of the core example (the four groups orig, tu0, tu05, tu10 of experiments/windport_sens_conservative.one; the two
first-cradle-150 m groups are covered by windport_maingeom.py --part core) rerun in the main geometry. Grid as for the conservative
lifting rule: long single lane / long corridor 1 km/h × on-road / pull-in × S0, S1, S1m, S3, S3m × K = 1–8, 10 piles per vessel,
Q_h = 0.
Output results/windport_maingeom_sens_<config hash>/: config.json, progress.json, points.csv, summary.md.
Run: python experiments/windport_sens_maingeom.py --procs 8 --slots DIR
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
import windport_sens_conservative as M                              # noqa: E402

VARS = ["orig", "tu0", "tu05", "tu10"]
CODE = M.CODE[:-1] + ["experiments/windport_sens_conservative.py", "windport/bound_all.py", "windport/sim4.py", "experiments/windport_sens_maingeom.py"]


def chunk(items):
    return [M.one(x) for x in items]


def init():
    from windport import archetypes as A
    pin(list(range(1, os.cpu_count())))
    A.use("main")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    from windport import archetypes as A
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="maingeom", part="sens", variants={k: M.VARIANTS[k] for k in VARS}, grid=M.GRID, geometry=A.GEOMETRIES["main"], code=code)
    out = ROOT / "results" / ("windport_maingeom_sens_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    g = M.GRID
    its = list(itertools.product(VARS, g["scen"], g["mode"], g["arr"], g["K"]))
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "main geometry: t_u sensitivity of the core example", "maingeom")
    rows = []
    for rs in slot_imap(chunk, [its[k:k + 8] for k in range(0, len(its), 8)], a.procs, initializer=init, slots_dir=a.slots, tag="maingeom"):
        rows += rs
        prog.write(done=len(rows))
    rows.sort(key=lambda r: (VARS.index(r["var"]), r["scen"], r["mode"], r["arr"], r["K"]))
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["var", "scen", "mode", "arr", "K", "port_h", "lstar", "check_ok"])
        w.writeheader()
        w.writerows(rows)
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["scen"], r["mode"], r["arr"], r["var"])].append(r)
    fmt = lambda rs: f"{min(r['port_h'] for r in rs):.4f}" + (f" ({min(r['lstar'] for r in rs):.4f})" if "lstar" in rs[0] else "")
    L = ["# Main geometry: t_u sensitivity of the core example (10 piles per vessel, Q_h = 0, FCFS; shortest over K = 1–8; "
         "L*(10) of W″_lift in brackets)", "",
         "| Scenario | Cradle | Lifting | " + " | ".join(VARS) + " |", "|---|---|---|" + "---:|" * len(VARS)]
    for sc, m, arr in itertools.product(g["scen"], g["mode"], g["arr"]):
        L.append(f"| {sc} | {m} | {arr} | " + " | ".join(fmt(by[(sc, m, arr, v)]) for v in VARS) + " |")
    L += ["", f"new checker failed {sum(1 for r in rows if r.get('check_ok') == 0)} points (of {sum(1 for r in rows if 'check_ok' in r)} conservative-rule points); "
          f"port time < L* {sum(1 for r in rows if 'lstar' in r and r['port_h'] < r['lstar'] - 1e-6)} points."]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=L[-1][:300])
    print(out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
