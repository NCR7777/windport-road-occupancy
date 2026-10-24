"""Dead-end coupling: best feasible schedules and dual bounds for the core instances. CP-SAT (windport/cpsat.py unchanged; same semantics as
the simulation since the E1-E3 batches: same vehicles, quay places, gate holding places, departure rule; the class of schedules in which
vehicles wait only at their start, at quay places and at idle positions, never on the road, on a 1 s time grid, slightly conservative)
lowers L step by step in decision form: "can 10 piles be lifted within the window [G, G + L]?".

Instances: A1 × long single lane (1.2 km in one section, 10 m, loaded 1 km/h) / long corridor (same length, split into two blocks by a branch
junction, 1 km/h) × on-road / pull-in cradles × S = 1 cradle × Q_h = 0 × K = 1, 2, 3, 8 × 10 piles per vessel, vessel crane open from
G = 24 h (as in the port-time batch of the extra analyses; for K = 4–7 FCFS and L″* equal those of K = 2, 3, 8).
Per instance: FCFS port time T_f (windport/sim2.py), rule-independent lower bound L″* (windport/bound_dead.py). Lower end =
max(L″*, largest L proven infeasible by CP-SAT), upper end = shortest port time found so far (initially T_f). Each probe uses
L = ⌊upper − 60 s⌋ (also when L″* = T_f, to record how far CP-SAT can prove by itself; never below the lower end), descending while
schedules are found; after the first infeasibility proof it bisects, L = ⌊(lower + upper)/2⌋; at most 30 probes, stop when upper − lower ≤ 2 s:
  10 piles found → record the schedule (independent checker windport/check.py in continuous time, check W″(T_cp) ≥ 10), upper = T_cp;
  OPTIMAL and < 10 → this class of schedules cannot lift 10 piles within L (proof), lower = L;
  only FEASIBLE (< 10) → undecided, stop.
Solution hint for each probe: the FCFS simulation of the same window. Time limit time_s seconds per probe; threads are taken from the
machine-wide CPU slots (first 1, then up to MAX_THREADS = 4).
Time-limited CP-SAT runs multithreaded, so the results (best solution, solver bound, where the search stops) are not guaranteed to reproduce
bit for bit; points.csv omits wall time and thread count (they are in the per-probe JSON).
Output results/windport_deadend_cp_<config hash>/: config.json, progress.json, points/ (per-probe JSON, resume cache), points.csv, summary.md.
Run: python experiments/windport_deadend_cpsat.py --shard 0 --of 3 --slots DIR (after all shards finish,
     aggregate with --aggregate-only)
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, write_json                       # noqa: E402

CODE = ["windport/cpsat.py", "windport/sim.py", "windport/sim2.py", "windport/check.py", "windport/bound.py", "windport/bound2.py",
        "windport/bound3.py", "windport/bound_dead.py", "windport/archetypes.py", "occupancy/sim.py", "occupancy/network.py", "exact/model.py",
        "experiments/windport_extra.py", "experiments/windport_runs.py", "experiments/windport_deadend_cpsat.py"]
GRID = dict(scen=["lane", "longslow"], mode=["on_road", "pull_in"], K=[1, 2, 3, 8], arr="S1", n_v=10, hold=0, G=24, open_h=200, step_s=60.0,
            probes=30, time_s=1200.0, unit=1.0, seed=0)
MAX_THREADS = 4          # max slots per shard (machine-wide slots shared with other runs); not part of the config


def inst_keys():
    return [f"{sc}|{m}|K{K}" for sc, m, K in itertools.product(GRID["scen"], GRID["mode"], GRID["K"])]


def base_cfg(key):
    import windport_extra as X
    sc, m, K = key.split("|")
    return X.port_cfg(sc, m, GRID["arr"], int(K[1:]), GRID["n_v"], GRID["hold"], G=GRID["G"], open_h=GRID["open_h"])


def lifts_end(trips):
    return sorted(x["F_vessel"] for x in trips if x["F_vessel"] is not None)


def anchors(key):
    """(T_f in s, upper end of L″* in s)."""
    from windport import bound3 as B3
    from windport import bound_dead as B4
    from windport import sim2 as S2
    c = base_cfg(key)
    _, _, sim, _ = S2.simulate2(c)
    G = GRID["G"] * 3600.0
    Tf = lifts_end(sim.trips)[GRID["n_v"] - 1] - G
    return Tf, B3.lstar(B4.wfn4(c), GRID["n_v"])[1]


def probe(key, L, threads):
    """Decide whether 10 piles can be lifted within the window [G, G + L] (L in s, whole seconds)."""
    from windport import bound_dead as B4
    from windport import check as C
    from windport import cpsat as CP
    from windport import sim as S
    from windport import sim2 as S2
    G = GRID["G"]
    c = base_cfg(key)
    c = dict(c, cal=dict(crane=[[G, G + L / 3600.0]]), horizon_h=G + L / 3600.0 + 1)
    _, _, sim, _ = S2.simulate2(c)
    inst = CP.Inst(c, n=GRID["n_v"])
    t0 = time.time()
    out = CP.solve(inst, GRID["time_s"], threads, GRID["seed"], GRID["unit"], hint=sim.trips)
    res = dict(L=L, status=out["status"], best=out["best"], cp_bound=round(out["bound"], 6), hint=sum(1 for x in sim.trips if x["F_vessel"] is not None),
               wall=round(time.time() - t0, 1), threads=threads)
    if out["trips"]:
        D, net, p, _, starts, quay, cal = S.setup(c)
        res["check"] = int(C.check(net, p, out["trips"], starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), inst.H)["ok"])
        ls = lifts_end(out["trips"])
        if len(ls) >= GRID["n_v"]:
            T = ls[GRID["n_v"] - 1] - G * 3600.0
            res.update(T_cp=T, w4_at_T=B4.wfn4(base_cfg(key))(T), trips=out["trips"])
    return res


def take(slots):
    n = 1
    if slots:
        slots.want(MAX_THREADS)
        while not slots.take():
            time.sleep(0.5)
        while n < MAX_THREADS and slots.take():
            n += 1
    return n


def run_inst(key, out, slots, prog):
    f = out / "points" / (key.replace("|", "_") + ".json")
    d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    if "Tf" not in d:
        d["Tf"], d["lstar4"] = anchors(key)
        write_json(f, d)
    d.setdefault("probes", [])
    while not d.get("done"):
        ps = d["probes"]
        lo_b = max([d["lstar4"]] + [p["L"] for p in ps if p["status"] == "OPTIMAL" and p["best"] < GRID["n_v"]])
        hi_b = min([d["Tf"]] + [p["T_cp"] for p in ps if p["best"] >= GRID["n_v"]])
        if ps and ps[-1]["best"] < GRID["n_v"] and ps[-1]["status"] != "OPTIMAL":
            d["done"] = "unknown"
        elif ps and hi_b - lo_b <= 2.0:
            d["done"] = "closed"
        elif len(ps) >= GRID["probes"]:
            d["done"] = "probes"
        if d.get("done"):
            break
        descend = all(p["best"] >= GRID["n_v"] for p in ps)          # all found so far: lower by step_s; bisect after the first infeasibility proof
        L = max(math.floor(lo_b), math.floor(hi_b - GRID["step_s"])) if descend else math.floor((lo_b + hi_b) / 2)
        n = take(slots)
        try:
            prog.write(note=f"{key}: L = {L / 3600:.4f} h, {n} threads")
            ps.append(probe(key, L, n))
        finally:
            if slots:
                for _ in range(n):
                    slots.give()
        write_json(f, d)
    write_json(f, d)
    return d


COLS = ["key", "scen", "mode", "K", "fcfs_h", "lstar4_h", "best_h", "fcfs_minus_best_s", "best_minus_lstar_s", "proven_gt_h", "end", "probes",
        "statuses", "checks", "w4_ok"]


def row(key, d):
    sc, m, K = key.split("|")
    ps = d["probes"]
    found = [p for p in ps if p["best"] >= GRID["n_v"]]
    best = min([d["Tf"]] + [p["T_cp"] for p in found])
    proven = [p["L"] for p in ps if p["status"] == "OPTIMAL" and p["best"] < GRID["n_v"]]
    return dict(key=key, scen=sc, mode=m, K=int(K[1:]), fcfs_h=round(d["Tf"] / 3600, 6), lstar4_h=round(d["lstar4"] / 3600, 6),
                best_h=round(best / 3600, 6), fcfs_minus_best_s=round(d["Tf"] - best, 1), best_minus_lstar_s=round(best - d["lstar4"], 1),
                proven_gt_h=round(max(proven) / 3600, 6) if proven else "", end=d.get("done", ""), probes=len(ps),
                statuses="/".join(f"{p['L'] / 3600:.4f}h:{p['status']}:{p['best']}:{p['cp_bound']}" for p in ps),
                checks="/".join(str(p.get("check", "")) for p in ps), w4_ok=int(all(p["w4_at_T"] >= GRID["n_v"] for p in found)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slots", default=None)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--aggregate-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="deadend", part="cp", grid=GRID, code=code)
    out = ROOT / "results" / ("windport_deadend_cp_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    (out / "points").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    ks = inst_keys()
    if not a.aggregate_only:
        mine = ks[a.shard::a.of]
        mine.sort(key=lambda k: int(k.split("|")[2][1:]))         # small cases first
        prog = Progress(out / f"progress_{a.shard}.json" if a.of > 1 else out / "progress.json", len(mine), 0, 1,
                        f"Dead-end coupling CP-SAT probes (shard {a.shard}/{a.of})", "deadend")
        slots, sd = None, a.slots or os.environ.get("CPU_SLOTS")
        if sd:
            sys.path.insert(0, sd)
            from cpu_slots import Slots
            slots = Slots(f"deadend-cp-{os.getpid()}")
        try:
            for i, k in enumerate(mine):
                run_inst(k, out, slots, prog)
                prog.write(done=i + 1)
        except BaseException as e:
            prog.write(state="failed", note=repr(e)[:300])
            raise
        finally:
            if slots:
                slots.close()
        prog.write(state="done")
        return
    rows, best = [], {}
    for k in ks:
        f = out / "points" / (k.replace("|", "_") + ".json")
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("done"):
                rows.append(row(k, d))
                found = [p for p in d["probes"] if p["best"] >= GRID["n_v"]]
                if found:                                          # best schedule shorter than FCFS (per trip, verified by the checker)
                    b = min(found, key=lambda p: p["T_cp"])
                    best[k] = dict(T_cp=b["T_cp"], L=b["L"], trips=b["trips"])
    (out / "best.json").write_text(json.dumps(best, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(rows)
    L = ["# Dead-end coupling CP-SAT: best feasible schedules and dual bounds for the core instances", "",
         f"- {len(rows)} / {len(ks)} instances done; time limit {GRID['time_s']:.0f} s per probe, at most {GRID['probes']} probes; the CP-SAT conclusions hold only for the class of schedules 'no waiting on the road, 1 s grid'; "
         "the rule-independent dual bound is L″* (windport/bound_dead.py).", "",
         "| Scenario | Cradle | K | FCFS h | L″* h | Best feasible h | FCFS − best (s) | Best − L″* (s) | Window proven infeasible by CP-SAT h | Stop reason | Probes (L:status:items:item bound) | Checker |",
         "|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['scen']} | {r['mode']} | {r['K']} | {r['fcfs_h']:.4f} | {r['lstar4_h']:.4f} | {r['best_h']:.4f} | {r['fcfs_minus_best_s']} | "
                 f"{r['best_minus_lstar_s']} | {r['proven_gt_h'] or '-'} | {r['end']} | {r['statuses']} | {r['checks']} |")
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
