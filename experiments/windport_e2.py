"""E2 (Table 2): maximum delivery within the window on small instances - W1, the optimal schedule with waiting only at the origin
(CP-SAT, windport/cpsat.py) and the simulation (windport/sim.py) side by side.

Small instances: layout A1 (6 quay positions, the first S used as cradles; S = 0 is direct lift) × cradle placement (on_road: the
quay front is the cut; pull_in: the single lane is the cut) × scenario (base; slow loaded 1 km/h; fastcrane crane 0.5 h; longslow
yard-quay 1,500 m and 1 km/h; lane as longslow but the single lane is one segment) × K = 1–3 × S = 0–2 × crane window L = 3, 5 h
× preparation time G = 1, 3 h × gate holding places Q_h = 0 (base case); for L = 3 h also Q_h = 1. Empty-system start.
Per instance: W1 (Theorem 2 ∧ Theorem 1) and W1 for an arbitrary history; CP-SAT optimum, bound and status (candidate monopiles
= W1 + 2, more than the bound so that W1 can be tested; time limit 60 s; the simulated trips are the initial hint); the simulation;
both schedules are verified in continuous time by the independent checker (windport/check.py). CP-SAT and the simulation share one
semantics (header of windport/cpsat.py).
Threads are taken from the machine-wide CPU slots (first 1, then as many as possible up to 8); the thread count and CP-SAT run
time are not part of the configuration and are not written to points.csv.
Output results/windport_e2_<config hash>/: config.json, progress.json, points/ (per-instance JSON, resume cache, with thread count
and run time), points.csv (tracked in git).

Run: .venv/Scripts/python.exe experiments/windport_e2.py --slots DIR
"""
import argparse
import csv
import hashlib
import itertools
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, write_json                     # noqa: E402
from windport import check as C                                 # noqa: E402
from windport import cpsat as CP                                # noqa: E402
from windport import sim as S                                   # noqa: E402

KMH = 1 / 3.6
CODE = ["windport/sim.py", "windport/bound.py", "windport/check.py", "windport/cpsat.py", "windport/archetypes.py", "occupancy/sim.py",
        "occupancy/network.py", "occupancy/params.py", "occupancy/tasks.py", "exact/check.py", "exact/model.py", "experiments/windport_e2.py"]
LONG = dict(dist_m=1500.0, corridor_m=1200.0)
SCEN = dict(base={}, slow=dict(p=dict(v_loaded=1.0 * KMH)), fastcrane=dict(p=dict(lift_s=1800.0)),
            longslow=dict(geo=LONG, p=dict(v_loaded=1.0 * KMH)), lane=dict(geo=dict(LONG, n_junctions=0), p=dict(v_loaded=1.0 * KMH)))
GRID = dict(modes=["on_road", "pull_in"], scen=list(SCEN), K=[1, 2, 3], S=[0, 1, 2], L=[3, 5], G=[1, 3], hold=[0, 1], hold1_L=[3], n_cradles=6,
            time_s=60.0, unit=1.0, seed=0, max_threads=8)
COLS = ["key", "mode", "scen", "K", "S", "L", "G", "hold", "w1", "w1_any", "binding", "n_cand", "cp_best", "cp_bound", "cp_status", "cp_check",
        "sim", "sim_check"]


def keys():
    return [f"{m}|{sc}|K{K}|S{s}|L{L}|G{G}|H{h}" for m, sc, K, s, L, G, h in
            itertools.product(GRID["modes"], GRID["scen"], GRID["K"], GRID["S"], GRID["L"], GRID["G"], GRID["hold"])
            if h == 0 or L in GRID["hold1_L"]]


def cfg_of(key):
    m, sc, K, s, L, G, h = key.split("|")
    K, s, L, G, h = int(K[1:]), int(s[1:]), int(L[1:]), int(G[1:]), int(h[1:])
    lift_s = SCEN[sc].get("p", {}).get("lift_s", S.BASE["lift_s"])
    geo = dict(dict(kind="A1", n_cradles=GRID["n_cradles"], cradle_mode=m), **SCEN[sc].get("geo", {}))
    return dict(geo=geo, p=dict(SCEN[sc].get("p", {})), S=s, K=K, horizon_h=G + L + 1,
                cal=dict(crane=[[G, G + L]]), n_load=int(L * 3600 // lift_s) + K + s + 2, hold=h)


def checked(cfg, trips, H):
    D, net, p, _, starts, quay, cal = S.setup(cfg)
    return C.check(net, p, trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(cfg), H)["ok"]


def run(key, threads):
    c = cfg_of(key)
    _, _, sim, r = S.simulate(c)
    inst = CP.Inst(c)
    out = CP.solve(inst, GRID["time_s"], threads, GRID["seed"], GRID["unit"], hint=sim.trips)
    w = inst.w1
    return dict(key=key, w1=w["bound"], w1_any=w["any_hist"], binding=w["binding"], n_cand=len(inst.tasks), cp_best=out["best"],
                cp_bound=round(out["bound"], 6), cp_status=out["status"], cp_check=int(checked(c, out["trips"], inst.H)) if out["trips"] else "",
                sim=r["n_vessel"][0], sim_check=int(checked(c, sim.trips, sim.H)), cp_wall=round(out["wall"], 3), cp_threads=threads)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slots", default=None)
    ap.add_argument("--aggregate-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="e1e3", part="e2", title="E2 small instances, exact: W1 / CP-SAT / simulation (Table 2)", grid=GRID, scen=SCEN, base=S.BASE, code=code,
               code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest())
    out = ROOT / "results" / ("windport_e2_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    ks = keys()
    if not a.aggregate_only:
        (out / "points").mkdir(parents=True, exist_ok=True)
        cf = out / "config.json"
        if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != cfg:
            raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
        cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        todo = [k for k in ks if not (out / "points" / (k.replace("|", "_") + ".json")).exists()]
        prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), 1, cfg["title"], "e1e3")
        slots, sd = None, a.slots or os.environ.get("CPU_SLOTS")
        if sd:
            sys.path.insert(0, sd)
            from cpu_slots import Slots
            slots = Slots(f"e2-{os.getpid()}")
        try:
            for k in todo:
                n = 1
                if slots:
                    slots.want(GRID["max_threads"])
                    while not slots.take():
                        time.sleep(0.5)
                    while n < GRID["max_threads"] and slots.take():
                        n += 1
                res = run(k, n)
                if slots:
                    for _ in range(n):
                        slots.give()
                write_json(out / "points" / (k.replace("|", "_") + ".json"), res)
                prog.write(done=prog.d["done"] + 1, processes=n)
        except BaseException as e:
            prog.write(state="failed", note=repr(e)[:300])
            raise
        finally:
            if slots:
                slots.close()
    rows = [json.loads((out / "points" / (k.replace("|", "_") + ".json")).read_text(encoding="utf-8")) for k in ks]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            m_, sc, K, s, L, G, h = r["key"].split("|")
            w.writerow(dict(r, mode=m_, scen=sc, K=int(K[1:]), S=int(s[1:]), L=int(L[1:]), G=int(G[1:]), hold=int(h[1:])))
    if not a.aggregate_only:
        bad = sum(1 for r in rows if r["sim"] > r["w1"] or r["cp_best"] > r["w1"] or not r["sim_check"] or r["cp_check"] == 0)
        prog.write(state="done", note=(f"dataset {m['records']} records; " if m else "") + f"above W1 or checker failed: {bad} instances")
    print(out)


if __name__ == "__main__":
    main()
