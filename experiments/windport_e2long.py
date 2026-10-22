"""E2 instances that were only proven feasible within 60 s (all in the crane 0.5 h scenario): rerun with a CP-SAT time limit of
600 s; the other instances are unchanged.
The instances are the rows of the E2 result results/<E2>/points.csv with cp_status ≠ OPTIMAL (the SHA-256 of that file is
recorded); the configuration is cfg_of of experiments/windport_e2.py, the simulated trips are the initial hint; every solution is
verified in continuous time by the independent checker (windport/check.py).
Threads are taken from the machine-wide CPU slots: per instance first 1, then as many as possible up to 8; at most 3 instances at
a time. Thread count and run time are kept only in the per-instance JSON, not in points.csv.
Output results/windport_e2long_<config hash>/: config.json, progress.json, points/, points.csv (tracked in git).

Run: .venv/Scripts/python.exe experiments/windport_e2long.py --slots DIR
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
from batch import Progress, write_json                     # noqa: E402
from windport import cpsat as CP                                # noqa: E402
from windport import sim as S                                   # noqa: E402

SRC = "results/runs/e2/points.csv"
TIME_S, MAX_T, PAR = 600.0, 8, 3
CODE = ["windport/sim.py", "windport/bound.py", "windport/check.py", "windport/cpsat.py", "windport/archetypes.py", "experiments/windport_e2.py",
        "experiments/windport_e2long.py"]
COLS = ["key", "w1", "sim", "cp60_best", "cp60_bound", "cp60_status", "cp_best", "cp_bound", "cp_status", "cp_check", "sim_check"]


def init():
    try:
        import psutil
        psutil.Process().cpu_affinity(list(range(1, os.cpu_count())))
    except Exception:
        pass


def run(arg):
    key, threads, row = arg
    c = E2.cfg_of(key)
    _, _, sim, r = S.simulate(c)
    inst = CP.Inst(c)
    out = CP.solve(inst, TIME_S, threads, E2.GRID["seed"], E2.GRID["unit"], hint=sim.trips)
    return dict(key=key, w1=inst.w1["bound"], sim=r["n_vessel"][0], cp60_best=int(row["cp_best"]), cp60_bound=float(row["cp_bound"]),
                cp60_status=row["cp_status"], cp_best=out["best"], cp_bound=round(out["bound"], 6), cp_status=out["status"],
                cp_check=int(E2.checked(c, out["trips"], inst.H)) if out["trips"] else "", sim_check=int(E2.checked(c, sim.trips, sim.H)),
                cp_wall=round(out["wall"], 3), cp_threads=threads)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    src = (ROOT / SRC).read_bytes()
    rows = [r for r in csv.DictReader(src.decode("utf-8").splitlines()) if r["cp_status"] != "OPTIMAL"]
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="e1e3", part="e2long", title="E2 feasible-only instances: CP-SAT 600 s", src=SRC, src_sha256=hashlib.sha256(src).hexdigest(), time_s=TIME_S,
               keys=[r["key"] for r in rows], code=code, code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest())
    out = ROOT / "results" / ("windport_e2long_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    (out / "points").mkdir(parents=True, exist_ok=True)
    cf = out / "config.json"
    if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != cfg:
        raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
    cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    fn = lambda k: out / "points" / (k.replace("|", "_") + ".json")
    todo = [r for r in rows if not fn(r["key"]).exists()]
    prog = Progress(out / "progress.json", len(rows), len(rows) - len(todo), PAR, cfg["title"], "e1e3")
    slots, sd = None, a.slots or os.environ.get("CPU_SLOTS")
    if sd:
        sys.path.insert(0, sd)
        from cpu_slots import Slots
        slots = Slots(f"e2long-{os.getpid()}")
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
                    r = todo.pop(0)
                    live[ex.submit(run, (r["key"], n, r))] = n
                done, _ = wait(live, timeout=1.0, return_when=FIRST_COMPLETED)
                for f in done:
                    n = live.pop(f)
                    if slots:
                        for _ in range(n):
                            slots.give()
                    res = f.result()
                    write_json(fn(res["key"]), res)
                    prog.write(done=prog.d["done"] + 1)
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    finally:
        if slots:
            slots.close()
    res = [json.loads(fn(r["key"]).read_text(encoding="utf-8")) for r in rows]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(res)
    note = ""
    bad = sum(1 for r in res if r["cp_best"] > r["w1"] or r["sim"] > r["cp_best"] or not r["sim_check"] or r["cp_check"] == 0)
    prog.write(state="done", note=note + f"proven optimal {sum(r['cp_status'] == 'OPTIMAL' for r in res)} / {len(res)}; above W1, simulation above CP-SAT or checker failed: {bad} instances")
    print(out)


if __name__ == "__main__":
    main()
