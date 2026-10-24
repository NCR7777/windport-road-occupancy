"""E2 (the 540 small instances of Table 2 of the E1-E3 batches) rerun under the conservative lifting rule: all 540 instances are
recomputed with the simulation and CP-SAT (windport/cpsat_lift.py, with the same 60 s time limit, seed, time grid and number of
candidate monopiles as windport_e2.py; the simulated trips serve as the initial solution hint), and both schedules go to the new checker
(windport/check_lift.py). The cradle mode also keeps the area under the load closed, so the 360 cradle instances are recomputed with
CP-SAT as well; the 17 instances recomputed with 600 s in the E1-E3 batches (results/runs/e2_long) are recomputed again
with 600 s and written to e2long/points.csv in the same format.
Threads are taken from the machine-wide CPU slots: each instance first takes 1 and then up to 4, with at most 4 instances at a time;
thread counts and wall times are recorded only in the per-instance JSON.
Output results/windport_conservative_e2_<config hash>/: config.json, progress.json, points/, points.csv (same columns as the committed E2),
diff.csv, summary.json.
Run: python experiments/windport_e2_conservative.py --slots DIR
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_e2 as E2                                        # noqa: E402
from batch import Progress, write_json                       # noqa: E402

SRC = "results/runs/e2/points.csv"
LONG = "results/runs/e2_long/points.csv"
LCOLS = ["key", "w1", "sim", "cp60_best", "cp60_bound", "cp60_status", "cp_best", "cp_bound", "cp_status", "cp_check", "sim_check"]
MAX_T, PAR = 4, 4
CODE = ["windport/lift.py", "windport/check_lift.py", "windport/cpsat.py", "windport/cpsat_lift.py", "windport/sim.py", "windport/bound.py",
        "windport/check.py", "windport/archetypes.py", "occupancy/sim.py", "occupancy/network.py", "occupancy/params.py", "exact/check.py",
        "exact/model.py", "experiments/windport_e2.py", "experiments/windport_e2_conservative.py"]


def init():
    try:
        import psutil
        psutil.Process().cpu_affinity(list(range(1, os.cpu_count())))
    except Exception:
        pass
    from windport import check as C
    from windport import check_lift as CL
    from windport import lift as LF
    LF.install()
    C.check = CL.check


def run(arg):
    key, threads, row, time_s = arg
    from windport import cpsat_lift as CPL
    from windport import sim as S
    c = E2.cfg_of(key)
    _, _, sim, r = S.simulate(c)
    out = dict(row, sim=r["n_vessel"][0], sim_check=int(E2.checked(c, sim.trips, sim.H)))
    if True:
        inst = CPL.Inst(c)
        cp = CPL.solve(inst, time_s, threads, E2.GRID["seed"], E2.GRID["unit"], hint=sim.trips)
        w = inst.w1
        out.update(w1=w["bound"], w1_any=w["any_hist"], binding=w["binding"], n_cand=len(inst.tasks), cp_best=cp["best"], cp_bound=round(cp["bound"], 6),
                   cp_status=cp["status"], cp_check=int(E2.checked(c, cp["trips"], inst.H)) if cp["trips"] else "", cp_wall=round(cp["wall"], 3),
                   cp_threads=threads, trips=cp["trips"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    src = (ROOT / SRC).read_bytes()
    rows = list(csv.DictReader(src.decode("utf-8").splitlines()))
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="conservative", part="e2", round=4, src=SRC, long=LONG, src_sha256=hashlib.sha256(src).hexdigest(), grid=E2.GRID, max_threads=MAX_T, code=code)
    out = ROOT / "results" / ("windport_conservative_e2_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    (out / "points").mkdir(parents=True, exist_ok=True)
    cf = out / "config.json"
    if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != cfg:
        raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
    cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    fn = lambda k, lg=False: out / ("points_long" if lg else "points") / (k.replace("|", "_") + ".json")
    (out / "points_long").mkdir(exist_ok=True)
    lrows = list(csv.DictReader((ROOT / LONG).read_text(encoding="utf-8").splitlines()))
    lkeys = {r["key"] for r in lrows}
    byk = {r["key"]: r for r in rows}
    jobs = [(r["key"], r, E2.GRID["time_s"], False) for r in rows] + [(k, byk[k], 600.0, True) for k in sorted(lkeys)]
    todo = [j for j in jobs if not fn(j[0], j[3]).exists()]
    todo.sort(key=lambda j: not j[3])                                     # 600 s jobs first
    prog = Progress(out / "progress.json", len(jobs), len(jobs) - len(todo), PAR, "E2, conservative lifting (540 x CP-SAT 60 s + 17 x 600 s)", "conservative")
    slots, sd = None, a.slots or os.environ.get("CPU_SLOTS")
    if sd:
        sys.path.insert(0, sd)
        from cpu_slots import Slots
        slots = Slots(f"conservative-e2-{os.getpid()}")
    live = {}
    try:
        with ProcessPoolExecutor(PAR, initializer=init) as ex:
            while todo or live:
                while todo and len(live) < PAR:
                    n = 1
                    if slots:
                        slots.want(MAX_T * min(PAR, len(todo) + len(live)))
                        while not slots.take():
                            time.sleep(0.5)
                        while n < MAX_T and slots.take():
                            n += 1
                    k, r, ts, lg = todo.pop(0)
                    live[ex.submit(run, (k, n, r, ts))] = (n, lg)
                done, _ = wait(live, timeout=1.0, return_when=FIRST_COMPLETED)
                for f in done:
                    n, lg = live.pop(f)
                    if slots:
                        for _ in range(n):
                            slots.give()
                    res = f.result()
                    write_json(fn(res["key"], lg), res)
                    prog.write(done=prog.d["done"] + 1)
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    finally:
        if slots:
            slots.close()
    (out / "e2long").mkdir(exist_ok=True)
    with open(out / "e2long" / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, LCOLS)
        w.writeheader()
        for r in lrows:
            a60, b6 = json.loads(fn(r["key"]).read_text(encoding="utf-8")), json.loads(fn(r["key"], True).read_text(encoding="utf-8"))
            w.writerow(dict(key=r["key"], w1=b6["w1"], sim=b6["sim"], cp60_best=a60["cp_best"], cp60_bound=a60["cp_bound"], cp60_status=a60["cp_status"],
                            cp_best=b6["cp_best"], cp_bound=b6["cp_bound"], cp_status=b6["cp_status"], cp_check=b6["cp_check"], sim_check=b6["sim_check"]))
    res = [json.loads(fn(r["key"]).read_text(encoding="utf-8")) for r in rows]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, E2.COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(res)
    new = (out / "points.csv").read_text(encoding="utf-8").splitlines()
    old = src.decode("utf-8").splitlines()
    assert new[0] == old[0] and len(new) == len(old)
    diff = [dict(key=r["key"], cls="lift" if r["S"] == "0" else "cradle", same=int(a_ == b_)) for r, a_, b_ in zip(rows, new[1:], old[1:])]
    with open(out / "diff.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["key", "cls", "same"])
        w.writeheader()
        w.writerows(diff)
    d0 = [r for r in res if str(r["S"]) == "0"]
    s = dict(rows=len(res), cradle_rows=sum(x["cls"] == "cradle" for x in diff), cradle_same=sum(x["same"] for x in diff if x["cls"] == "cradle"),
             lift_rows=len(d0), lift_same=sum(x["same"] for x in diff if x["cls"] == "lift"), optimal=sum(r["cp_status"] == "OPTIMAL" for r in res),
             optimal_direct=sum(r["cp_status"] == "OPTIMAL" for r in d0), sim_over_cp=sum(int(r["sim"]) > int(r["cp_best"]) for r in res),
             cp_over_w1=sum(int(r["cp_best"]) > int(r["w1"]) for r in res),
             check_fail=sum(str(r["sim_check"]) != "1" for r in res) + sum(str(r["cp_check"]) == "0" for r in res), long=len(lrows),
             long_optimal=sum(1 for r in lrows if json.loads(fn(r["key"], True).read_text(encoding="utf-8"))["cp_status"] == "OPTIMAL"))
    (out / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(s, ensure_ascii=False))
    print(out)
    print(json.dumps(s, ensure_ascii=False))


if __name__ == "__main__":
    main()
