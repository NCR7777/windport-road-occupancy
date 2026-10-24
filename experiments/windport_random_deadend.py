"""Dead-end coupling: random-archetype regression, per-pile check of W″ (windport/bound_dead.py: Corollary 6 dead-end quay coupling,
Corollary 7 cradle coupling under single-sequence handover). Synthetic archetypes only: shipyard-derived maps from the generators
(geo.kind = "map") are skipped and not run (recorded as skipped).

Generators (--gen):
  port  port-time generator of the regression of the extra analyses (windport_random_lift.make_port, seed 31,000,000 + i, unchanged):
        A1/A2/A3, Q_h 0, 1, 2, unlimited, convoy dispatch, etc.;
  dead  targeted segment (new, seed 37,000,000 + i): a class in which most premises of Corollaries 6 and 7 hold: no gate holding place
        (90%), single lane split into blocks by 0–3 branch junctions, S = 0–3, pull-in / on-road cradles, cradle / mixed lifting, long
        corridor with slow vehicles, vessel crane open for 120 h from G;
  main  window-form generator of the E4-E7 regression (windport_random.make, same seeds).
Per-pile checks for each case (pile j finishes lifting at G + T_j):
  def    some pile with W″(T_j) < j (the inequality behind the port-time lower bound L″*)
  lstar  lower end of L″*(n) > T_n (n = 1, median, last pile)
  mono   W″ is not non-decreasing over the T_j and a set of equally spaced points
  wle    some pile with W″(T_j) > W′(T_j) (W″ only adds terms and only reduces Q, so it must not be larger)
  check  the road-occupancy simulation checker fails (windport/check.py)
  h5     for every chain where the Corollary 6 premises hold (bound2.quay_side_Q finite): the quay zone rebuilt from the windows of the
         independent checker (windport/check2.hyp, which does not call Net.leg), from the loaded vehicle entering the first block of the
         chain until the next empty vehicle enters that block, holds more than min(K, Q_s) vehicles at once, or opposing passages overlap
Also recorded: q6 (Corollary 6(a) reduces Q), zc (a whole-chain quay-zone term of Corollary 6(b) exists), tight (W″ strictly below W′ at
some pile).
Output results/windport_deadend_random_<config hash>/: config.json, progress.json, summary.json, bad.csv, cases.csv (per case, no wall time).
Run: python experiments/windport_random_deadend.py --gen dead --start 0 --n 12000 --procs 12 --slots DIR
"""
import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402

CODE = ["windport/sim.py", "windport/sim2.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py", "windport/bound_dead.py",
        "windport/check.py", "windport/check2.py", "windport/archetypes.py", "occupancy/sim.py", "occupancy/network.py", "occupancy/params.py",
        "exact/check.py", "experiments/windport_random.py", "experiments/windport_random_lift.py", "experiments/windport_random_deadend.py"]
FLAGS = ["error", "def", "lstar", "mono", "wle", "check", "h5"]
KMH = 1 / 3.6
OPEN_H = 120


def make_dead(i):
    R = random.Random(37_000_000 + i)
    p = dict(v_loaded=R.choice([0.5, 1.0, 2.5, 5.0]) * KMH, v_empty=R.choice([1.0, 2.0, 5.0, 10.0]) * KMH, Lv=R.choice([60.0, 90.0, 110.0, 150.0]),
             hp_s=R.choice([300.0, 900.0, 1800.0, 3600.0]), hd_s=R.choice([60.0, 300.0, 900.0, 1800.0, 3600.0]),
             lift_s=R.choice([600.0, 1800.0, 3600.0, 7200.0]), sweep_steer_s=R.choice([None, 0.0, 120.0]), release_frac=R.choice([0.0, 0.5, 1.0]))
    kind = R.choice(["A1"] * 8 + ["A2", "A3"])
    dist = R.choice([400.0, 800.0, 1500.0, 2000.0])
    geo = dict(kind=kind, dist_m=dist, corridor_m=R.choice([0.6, 0.9, 1.0]) * dist, n_junctions=R.choice([0, 1, 2, 3]),
               cradle_mode=R.choice(["on_road", "pull_in"]), n_cradles=R.choice([1, 2, 3]), apron_w=R.choice([12.0, 12.0, 16.0]))
    if R.random() < 0.25:
        geo["pocket"] = R.choice([10.0, 30.0])
    S_ = min(R.choice([0, 1, 1, 2, 3]), geo["n_cradles"])
    G = R.choice([0, 1, 3, 8, 24])
    return dict(geo=geo, p=p, S=S_, K=R.choice([1, 2, 3, 4, 5, 6, 8]), lift=R.choice(["cradle", "cradle", "mixed"]) if S_ else "cradle",
                horizon_h=G + OPEN_H, cal=dict(crane=[[G, G + OPEN_H]]), n_load=R.choice([3, 5, 8, 10, 12]), hold=0 if R.random() < 0.9 else 1,
                rule=R.choice(["fcfs", "convoy"]))


def make(gen, i):
    if gen == "main":
        import windport_random as R
        return R.make(i)
    if gen == "port":
        import windport_random_lift as R
        return R.make_port(i)
    return make_dead(i)


def h5(c, net, p, trips, starts, w):
    """Trajectory check of Corollary 6: maximum vehicle count in the quay zone and opposing overlaps on each chain whose premises hold.
    Returns (violation, number of chains checked)."""
    from windport import bound2 as W2
    from windport import check2 as C2
    from windport import sim as S
    from windport import sim2 as S2
    if c.get("n_unload"):
        return False, 0
    D, *_ = S2.setup2(c)
    W = D["windport"]
    rows, quay = W["storage"], W["cradles"][:max(1, c["S"])]
    bad, n = False, 0
    for ch in w["chains"]:
        Qs = W2.quay_side_Q(net, p, rows, quay, p["Lv"], p["B"], ch, S.hold_of(c))
        if Qs == math.inf:
            continue
        n += 1
        r = C2.hyp(net, p, trips, starts, [res[1] for res in ch["res"]], ch["res"][0])
        bad |= r["zone"] > min(c["K"], Qs) or (ch["down"] is not None and r["opp"] > 0)
    return bad, n


def work(arg):
    gen, i = arg
    from windport import bound3 as B3
    from windport import bound_dead as B4
    from windport import check as C
    from windport import sim as S
    from windport import sim2 as S2
    c = make(gen, i)
    if c["geo"]["kind"] == "map":
        return dict(gen=gen, i=i, why="", skipped=1)
    try:
        if gen != "main":                                      # the full-window W1′ over 120 h is not needed (per-pile checks only)
            orig, S2.bounds2 = S2.bounds2, (lambda *a, **k: None)
        try:
            net, p, sim, r = S2.simulate2(c)
        finally:
            if gen != "main":
                S2.bounds2 = orig
        D, _, _, _, starts, quay, cal = S2.setup2(c)
        g, y = S2.idle_nodes(D)
        ck = C.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
        G, b = cal["crane"][0]
        L = b - G
        w3 = B3.wprime_parts(c)
        w = B4.parts4(c, dict(w3))
        f3, f = B3.wprime_fn(c, w3), B4.wfn4(c, w)
        T = sorted(x["F_vessel"] - G for x in sim.trips if x["F_vessel"] is not None and x["s"] >= G - 1e-6 and x["F_vessel"] <= b + 1e-6)
        if gen != "main":
            T = T[:c["n_load"]]
        why = []
        v4 = [f(t) for t in T]
        v3 = [f3(t) for t in T]
        viol = [n for n, v in enumerate(v4, 1) if v < n]
        if viol:
            why.append("def")
        if any(a > b_ for a, b_ in zip(v4, v3)):
            why.append("wle")
        for n in (sorted({1, (len(T) + 1) // 2, len(T)}) if T else []):
            if B3.lstar(f, n)[0] > T[n - 1] + 1e-6:
                why.append("lstar")
                break
        top = L if gen == "main" else (T[-1] + 3 * 3600.0 if T else 3600.0)
        grid = sorted(set(T) | {k * 1.5 * top / 30 for k in range(31)})
        vals = [f(x) for x in grid]
        if any(v2 < v1 for v1, v2 in zip(vals, vals[1:])):
            why.append("mono")
        if not ck["ok"]:
            why.append("check")
        hb, hn = h5(c, net, p, sim.trips, starts, w)
        if hb:
            why.append("h5")
        l3 = B3.lstar(f3, len(T))[0] / 3600.0 if T else 0.0
        l4 = B3.lstar(f, len(T))[0] / 3600.0 if T else 0.0
        return dict(gen=gen, i=i, kind=c["geo"]["kind"], rule=c["rule"], hold=str(c["hold"]), S=c["S"], K=c["K"], lift=c.get("lift", "cradle"),
                    n=len(T), L_h=L / 3600.0, T_last=T[-1] / 3600.0 if T else 0.0, lstar3=l3, lstar4=l4, viol=len(viol),
                    tight=int(any(a < b_ for a, b_ in zip(v4, v3))), q6=int(w["P"].Q < w["Q3"]), zc=len(w["zc"]), h5_chains=hn,
                    eq_last=int(bool(T) and v4[-1] == len(T)), why="+".join(why), err=" / ".join((ck["errors"] or [])[:2]), skipped=0)
    except Exception:
        return dict(gen=gen, i=i, why="error", error=traceback.format_exc()[-800:], skipped=0)


def work_chunk(ks):
    return [work(k) for k in ks]


def init():
    pin(list(range(1, os.cpu_count())))


COLS = ["gen", "i", "kind", "rule", "hold", "S", "K", "lift", "n", "L_h", "T_last", "lstar3", "lstar4", "viol", "tight", "q6", "zc", "h5_chains",
        "eq_last", "why"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", choices=["main", "port", "dead"], default="dead")
    ap.add_argument("--n", type=int, default=12000)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=25)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="deadend", part="random", gen=a.gen, start=a.start, n=a.n, code=code)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_deadend_random_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    idx = [(a.gen, i) for i in range(a.start, a.start + a.n)]
    chunks = [idx[k:k + a.chunk] for k in range(0, len(idx), a.chunk)]
    prog = Progress(out / "progress.json", len(idx), 0, a.procs, f"Dead-end coupling random-archetype regression ({a.gen}: per-pile W″, Corollary 6 trajectory check)", "deadend")
    res = []
    for rs in slot_imap(work_chunk, chunks, a.procs, initializer=init, slots_dir=a.slots, tag="deadend"):
        res += rs
        prog.write(done=len(res))
    res.sort(key=lambda r: r["i"])
    ran = [r for r in res if not r["skipped"] and "error" not in r]
    with open(out / "cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(ran)
    with open(out / "bad.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS + ["err", "error"], extrasaction="ignore")
        w.writeheader()
        w.writerows(r for r in res if r["why"])
    summ = dict(gen=a.gen, n=len(res), skipped_maps=sum(r["skipped"] for r in res), ran=len(ran),
                **{k: sum(k in r["why"].split("+") for r in res) for k in FLAGS}, lifts_checked=sum(r["n"] for r in ran),
                lifts_violating=sum(r["viol"] for r in ran), tight=sum(r["tight"] for r in ran), q6=sum(r["q6"] for r in ran),
                zc=sum(r["zc"] > 0 for r in ran), h5_cases=sum(r["h5_chains"] > 0 for r in ran), h5_chains=sum(r["h5_chains"] for r in ran),
                lstar_raised=sum(r["lstar4"] > r["lstar3"] + 1e-9 for r in ran), eq_last=sum(r["eq_last"] for r in ran))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(summ, ensure_ascii=False)[:300])
    print(out)
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
