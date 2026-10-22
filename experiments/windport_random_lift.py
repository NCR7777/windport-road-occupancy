"""Random-layout regression: independent checks of the corrected W′ (windport/bound3.py), the port-time lower bound L*(n) and "cut
as a single resource" (windport/check3.py).

Three generators (--gen):
  main  generator of the earlier random regression (windport_random.make, same seeds; 10% are maps derived from Okpo and
        Yantai), crane window [G, G + L];
  port  port-time form: crane open for 120 h from G, n piles released at time 0 (seeds 31,000,000 + i; wider ranges of layouts,
        geometry, speeds and durations, 15% shipyard-derived maps, Q_h 0, 1, 2, unlimited, direct-lift release time 0–1);
  hold  targeted set: on-road quay positions (Okpo and Yantai derived maps 80%, A1 20%), Q_h 0, 1, 2, unlimited, slow empty
        vehicles, long set-down (seeds 32,000,000 + i): the class of cases in which W′ was found to be exceeded.
Each case is checked lift by lift (lift j completes at G + T_j, j = 1 … number of piles lifted aboard):
  def     W′(T_j) < j for some lift (the inequality behind the port-time lower bound)
  lstar   lower end of the bisected L*(n) > T_n (n = 1, median and last lift)
  mono    W′ is not non-decreasing over the points L = T_j and a uniform grid
  wfn     (main) the corrected W′ at the window length of the case is smaller than W1′ of windport.sim2.bounds2 (taking the smaller
          return-trip occupancy can only loosen the bound; it must not drop)
  check   road-occupancy simulation checker fails (windport/check.py)
  cut     cut as a single resource (fcfs cases without unloading tasks): windport/check3.py fails
Also recorded: corr, the correction reduced the return-trip occupancy of the case (te_occ before > after); raised, (main) the
corrected W′ is larger than bounds2.
Output results/windport_extra_random_<config hash>/: config.json, progress.json, summary.json, bad.csv, cases.csv (per case, no
wall-clock times).
Run: .venv/Scripts/python.exe experiments/windport_random_lift.py --gen main --start 0 --n 10000 --procs 22 --slots DIR
"""
import argparse
import csv
import hashlib
import json
import os
import random
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402

CODE = ["windport/sim.py", "windport/sim2.py", "windport/sim3.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py",
        "windport/check.py", "windport/check3.py", "windport/archetypes.py", "windport/shipyard.py", "occupancy/sim.py", "occupancy/network.py",
        "occupancy/params.py", "exact/check.py", "experiments/windport_random.py", "experiments/windport_random_lift.py"]
FLAGS = ["error", "wfn", "def", "lstar", "mono", "check", "cut"]
KMH = 1 / 3.6
OPEN_H = 120


def make_port(i):
    """Port-time generator (seeds 31,000,000 + i)."""
    R = random.Random(31_000_000 + i)
    p = dict(v_loaded=R.choice([0.3, 0.5, 1.0, 2.5, 5.0]) * KMH, v_empty=R.choice([1.0, 2.0, 5.0, 10.0]) * KMH,
             Lv=R.choice([40.0, 60.0, 90.0, 110.0, 130.0, 150.0]), hp_s=R.choice([300.0, 900.0, 1800.0, 3600.0]),
             hd_s=R.choice([60.0, 300.0, 900.0, 1800.0, 5400.0]), lift_s=R.choice([600.0, 900.0, 1800.0, 3600.0, 7200.0]),
             sweep_steer_s=R.choice([None, 0.0, 120.0, 900.0, 1800.0]), release_frac=R.choice([0.0, 0.0, 0.25, 0.5, 1.0]))
    if R.random() < 0.15:
        site = R.choice(["okpo", "yantai"])
        nc = R.choice([1, 2, 3, 4, 6]) if site == "okpo" else 1
        geo = dict(kind="map", site=site, cradle_mode=R.choice(["on_road", "pull_in"]), n_cradles=nc)
    else:
        kind = R.choice(["A1", "A1", "A2", "A3"])
        dist = R.choice([200.0, 400.0, 800.0, 1500.0, 2000.0])
        geo = dict(kind=kind, dist_m=dist, corridor_m=R.choice([0.3, 0.6, 0.9, 1.0]) * dist, n_junctions=R.choice([0, 1, 2, 3]),
                   cradle_mode=R.choice(["on_road", "pull_in"]), n_cradles=R.choice([1, 2, 3, 4, 6]), apron_w=R.choice([12.0, 12.0, 16.0, 20.0, 30.0]),
                   cradle_spacing=R.choice([60.0, 110.0, 150.0]))
        if kind != "A3":
            geo["ramp_at"] = R.choice(["end", "gate", None])
        if R.random() < 0.35:
            geo["pocket"] = R.choice([10.0, 30.0, 100.0])
        if R.random() < 0.15:
            p["section"] = "stops"
    S_ = min(R.choice([0, 1, 2, 3, 4, 6]), geo["n_cradles"])
    K = R.choice([1, 2, 3, 4, 5, 6, 8])
    G = R.choice([0, 1, 3, 8, 24])
    n = R.choice([2, 3, 5, 8, 10, 12])
    lift = R.choice(["cradle", "mixed"]) if S_ else "cradle"
    return dict(geo=geo, p=p, S=S_, K=K, lift=lift, horizon_h=G + OPEN_H, cal=dict(crane=[[G, G + OPEN_H]]), n_load=n,
                hold=R.choice([0, 0, 1, 2, "inf"]), rule=R.choice(["fcfs", "convoy"]))


def make_hold(i):
    """Targeted generator for on-road quay positions (seeds 32,000,000 + i)."""
    R = random.Random(32_000_000 + i)
    p = dict(v_loaded=R.choice([1.0, 2.5, 5.0]) * KMH, v_empty=R.choice([1.0, 2.0, 5.0]) * KMH, Lv=R.choice([60.0, 90.0, 110.0, 150.0]),
             hp_s=R.choice([300.0, 900.0, 1800.0, 3600.0]), hd_s=R.choice([900.0, 1800.0, 3600.0, 5400.0]), lift_s=R.choice([900.0, 1800.0, 3600.0]),
             sweep_steer_s=R.choice([None, 120.0]), release_frac=R.choice([0.0, 0.5]))
    if R.random() < 0.8:
        site = R.choice(["okpo", "yantai"])
        geo = dict(kind="map", site=site, cradle_mode="on_road", n_cradles=R.choice([1, 2]) if site == "okpo" else 1)
    else:
        geo = dict(kind="A1", cradle_mode="on_road", n_cradles=R.choice([1, 2]), dist_m=R.choice([400.0, 800.0]), corridor_m=200.0)
    S_ = min(R.choice([1, 2]), geo["n_cradles"])
    G = R.choice([0, 1, 3])
    n = R.choice([5, 8, 12])
    return dict(geo=geo, p=p, S=S_, K=R.choice([2, 3, 4, 6, 8]), lift="cradle", horizon_h=G + OPEN_H, cal=dict(crane=[[G, G + OPEN_H]]), n_load=n,
                hold=R.choice([0, 1, 2, "inf"]), rule=R.choice(["fcfs", "convoy"]))


def make(gen, i):
    if gen == "main":
        import windport_random as R
        return R.make(i)
    return make_port(i) if gen == "port" else make_hold(i)


def work(arg):
    gen, i = arg
    from windport import bound3 as B3
    from windport import check as C
    from windport import check3 as C3
    from windport import sim as S
    from windport import sim2 as S2
    from windport import sim3 as S3
    c = make(gen, i)
    try:
        if gen != "main":                                      # per-lift checks only: skip the 120 h whole-window W1′ (serial cut term fails on long windows)
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
        w = B3.wprime_parts(c)
        f = B3.wprime_fn(c, w)
        T = sorted(x["F_vessel"] - G for x in sim.trips if x["F_vessel"] is not None and x["s"] >= G - 1e-6 and x["F_vessel"] <= b + 1e-6)
        if gen != "main":
            T = T[:c["n_load"]]
        why, raised = [], 0
        if gen == "main":
            fl, old = f(L), r["w1g"]["bound"]
            if fl < old:
                why.append("wfn")
            raised = int(fl > old)
        viol = [n for n, t in enumerate(T, 1) if f(t) < n]
        if viol:
            why.append("def")
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
        cut = None
        if not c.get("n_unload") and c["rule"] == "fcfs":
            c3 = dict(c, fixed=True)
            net3, p3, sim3, r3 = S3.simulate3(c3)
            k3 = C3.check(net3, p3, sim3.trips, starts, quay, cal, S.ramp_res(D), S.hold_of(c3), sim3.H, gate=g, yard=y)
            cut = dict(n=len([x for x in sim3.trips if x["F_vessel"] is not None]), lane=k3["n_lane"], cut_set=sum(len(x) for x in sim3.cut))
            if not k3["ok"]:
                why.append("cut")
        return dict(gen=gen, i=i, kind=c["geo"]["kind"], rule=c["rule"], hold=str(c["hold"]), S=c["S"], K=c["K"], lift=c.get("lift", "cradle"),
                    n=len(T), L_h=L / 3600.0, lstar_last=B3.lstar(f, len(T))[0] / 3600.0 if T else 0.0, T_last=T[-1] / 3600.0 if T else 0.0,
                    viol=len(viol), corr=int(w["P"].te_occ < w["te_occ0"] - 1e-9), raised=raised, te_occ0=round(w["te_occ0"], 3),
                    te_occ=round(w["P"].te_occ, 3), cut_n="" if cut is None else cut["n"], cut_lane="" if cut is None else cut["lane"],
                    cut_set="" if cut is None else cut["cut_set"], why="+".join(why), err=" / ".join((ck["errors"] or [])[:2]))
    except Exception:
        return dict(gen=gen, i=i, why="error", error=traceback.format_exc()[-800:])


def work_chunk(ks):
    return [work(k) for k in ks]


def init():
    pin(list(range(1, os.cpu_count())))


COLS = ["gen", "i", "kind", "rule", "hold", "S", "K", "lift", "n", "L_h", "lstar_last", "T_last", "viol", "corr", "raised", "te_occ0", "te_occ",
        "cut_n", "cut_lane", "cut_set", "why"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", choices=["main", "port", "hold"], default="main")
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--procs", type=int, default=22)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=25)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="extra", part="random", gen=a.gen, start=a.start, n=a.n, code=code)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_extra_random_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    idx = [(a.gen, i) for i in range(a.start, a.start + a.n)]
    chunks = [idx[k:k + a.chunk] for k in range(0, len(idx), a.chunk)]
    prog = Progress(out / "progress.json", len(idx), 0, a.procs, f"Random-layout regression ({a.gen}: per-lift W′, L*, cut as a single resource)", "extra")
    res = []
    for rs in slot_imap(work_chunk, chunks, a.procs, initializer=init, slots_dir=a.slots, tag="extra"):
        res += rs
        prog.write(done=len(res))
    res.sort(key=lambda r: r["i"])
    with open(out / "cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(r for r in res if "error" not in r)
    with open(out / "bad.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS + ["err", "error"], extrasaction="ignore")
        w.writeheader()
        w.writerows(r for r in res if r["why"])
    ran = [r for r in res if "error" not in r]
    summ = dict(gen=a.gen, n=len(res), ran=len(ran), **{k: sum(k in r["why"].split("+") for r in res) for k in FLAGS},
                lifts_checked=sum(r["n"] for r in ran), lifts_violating=sum(r["viol"] for r in ran), corrected=sum(r["corr"] for r in ran),
                raised=sum(r["raised"] for r in ran), cut_cases=sum(r["cut_n"] != "" for r in ran),
                cut_with_lane=sum(1 for r in ran if r["cut_set"] not in ("", 0)), maps=sum(r["kind"] == "map" for r in ran),
                maps_hold=sum(1 for r in ran if r["kind"] == "map" and r["hold"] != "0"),
                lstar_tie=sum(1 for r in ran if r["n"] and abs(r["lstar_last"] - r["T_last"]) < 1e-6))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(summ, ensure_ascii=False)[:300])
    print(out)
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
