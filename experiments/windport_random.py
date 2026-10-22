"""Random port-archetype regression: W1 strengthened (W1′ = w1g: geometric quay-zone Q, chain-cut preparation term), the joint
upper bound for a shared unloading/loading fleet, convoy dispatch, off-road pocket, shipyard maps.

Generator: the random port-archetype generator of the earlier W1 regression (gate holding places Q_h as levels and a separately
drawn release time), copied verbatim as make_base with seeds 1000 + i, so every case has the same archetype and parameters as that
regression. Seeds 500000 + i additionally draw: dispatch rule (fcfs / convoy), whether the archetype has an off-road pocket
(30 m stub), and, with a shared unloading/loading fleet, whether at most 1 vehicle may unload at a time (40%); 10% of the cases are
replaced by shipyard-derived maps (Okpo, Yantai, windport.shipyard) with equally random parameters.
Checks per case (independent checker windport/check.py with the idle positions of the archetype or derived map; hypothesis checks
windport/check2.py):
  over_w1   simulation > W1 (the earlier bound)    over_w1g  simulation > W1′
  check     checker fails                          thm3      pieces unloaded in some tidal window > Theorem 3
  joint     simultaneous unloading/loading: N_o + N_u > joint upper bound (Corollary 5; with a shared fleet, vehicle-time
            conservation is also used)
  opp       two opposing passes intersect on the chain (chain-cut lemma)
  phase     on return passes over the chain, a phase of consecutive upbound passes > b_max (Corollary 3)
  zone      simultaneous vehicles in the quay zone > Q (Corollary 4)
  (cases with unloading tasks are not checked for opp / phase / zone: Corollaries 3 and 4 do not apply to them)
Output results/windport_runs_random_<config hash>/: config.json, progress.json, summary.json, bad.csv (cases with a problem),
cases.csv (per-case summary, no wall clock).

Run: .venv/Scripts/python.exe experiments/windport_random.py --n 20000 --procs 23 --slots DIR
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

KMH = 1 / 3.6
CODE = ["windport/sim.py", "windport/sim2.py", "windport/bound.py", "windport/bound2.py", "windport/check.py", "windport/check2.py",
        "windport/archetypes.py", "windport/shipyard.py", "occupancy/sim.py", "occupancy/network.py", "occupancy/params.py",
        "exact/check.py", "experiments/windport_random.py"]


def make_base(i):
    """Random port archetype of the earlier W1 regression (verbatim)."""
    R = random.Random(1000 + i)
    kind = R.choice(["A1", "A2", "A3"])
    dist = R.choice([200.0, 400.0, 600.0, 1000.0, 1500.0])
    geo = dict(kind=kind, dist_m=dist, corridor_m=R.choice([0.3, 0.6, 0.8, 1.0]) * dist, n_junctions=R.choice([0, 1, 2]),
               cradle_mode=R.choice(["on_road", "pull_in"]), n_cradles=R.choice([2, 4, 6]), apron_w=R.choice([12.0, 12.0, 16.0]),
               ramp_at=R.choice(["end", "gate"]) if kind != "A3" else "end", bypass=R.choice([True, False]),
               cradle_spacing=R.choice([60.0, 110.0, 150.0]))
    if kind == "A3":
        geo.pop("ramp_at")
    else:
        geo.pop("bypass")
    p = dict(v_loaded=R.choice([0.5, 1.0, 2.5, 5.0]) * KMH, v_empty=R.choice([2.0, 5.0, 10.0]) * KMH, Lv=R.choice([60.0, 90.0, 110.0, 130.0]),
             hp_s=R.choice([300.0, 900.0, 1800.0, 3600.0]), hd_s=R.choice([300.0, 900.0, 1800.0, 5400.0]),
             lift_s=R.choice([900.0, 1800.0, 3600.0, 7200.0]), sweep_steer_s=R.choice([None, 0.0, 120.0, 900.0]))
    S_ = min(R.choice([0, 1, 2, 3, 4]), geo["n_cradles"])
    K = R.choice([1, 2, 3, 4, 6])
    L = R.choice([1, 2, 3, 5, 8, 12, 24])
    G = R.choice([0, 1, 3, 8, 24])
    lift = R.choice(["cradle", "mixed"]) if S_ else "cradle"
    c = dict(geo=geo, p=p, S=S_, K=K, lift=lift, horizon_h=G + L + 1, cal=dict(crane=[[G, G + L]]),
             n_load=int(L * 3600 // p["lift_s"]) + K + S_ + 2, hold=[0, 0, 1, 2, "inf"][i % 5])
    if R.random() < 0.8:
        p["release_frac"] = R.choice([0.0, 0.0, 0.25, 1.0])
    if R.random() < 0.3:
        T = 12.4206
        n = int((G + L + 1) // T) + 1
        c["cal"]["ramp"] = [[k * T, k * T + R.choice([3.0, 6.0])] for k in range(n)]
        c.update(n_unload=n, unload_release_h=[k * T for k in range(n)], K_u=R.choice([0, 1]))
        c["p"]["roro_s"] = R.choice([1800.0, 3 * 3600.0])
        if c["K_u"] == 0:
            c["p"]["unload_first"] = R.random() < 0.5
    return c


def make(i):
    R = random.Random(500000 + i)
    if R.random() < 0.1:                                    # shipyard-derived map
        site = R.choice(["okpo", "yantai"])
        nc = R.choice([1, 2, 3, 4, 6]) if site == "okpo" else 1
        p = dict(v_loaded=R.choice([0.5, 1.0, 2.5, 5.0]) * KMH, v_empty=R.choice([2.0, 5.0, 10.0]) * KMH, Lv=R.choice([60.0, 90.0, 110.0, 130.0]),
                 hp_s=R.choice([300.0, 900.0, 1800.0, 3600.0]), hd_s=R.choice([300.0, 900.0, 1800.0, 5400.0]),
                 lift_s=R.choice([900.0, 1800.0, 3600.0, 7200.0]), sweep_steer_s=R.choice([None, 0.0, 120.0, 900.0]),
                 release_frac=R.choice([0.0, 0.25, 1.0]))
        S_ = min(R.choice([0, 1, 2, 3, 4]), nc)
        K, L, G = R.choice([1, 2, 3, 4, 6]), R.choice([1, 2, 3, 5, 8, 12, 24]), R.choice([0, 1, 3, 8, 24])
        c = dict(geo=dict(kind="map", site=site, cradle_mode=R.choice(["on_road", "pull_in"]), n_cradles=nc), p=p, S=S_, K=K,
                 lift=R.choice(["cradle", "mixed"]) if S_ else "cradle", horizon_h=G + L + 1, cal=dict(crane=[[G, G + L]]),
                 n_load=int(L * 3600 // p["lift_s"]) + K + S_ + 2, hold=R.choice([0, 0, 1, 2, "inf"]))
    else:
        c = make_base(i)
        if R.random() < 0.4:
            c["geo"]["pocket"] = 30.0
    c["rule"] = R.choice(["fcfs", "convoy"])
    if c.get("n_unload") and not c.get("K_u") and R.random() < 0.4:      # shared fleet, at most 1 vehicle unloading at a time (windport.sim2.CapMixin)
        c["p"]["unload_cap"] = 1
    return c


def work(i):
    from windport import check as C
    from windport import check2 as C2
    from windport import sim as S
    from windport import sim2 as S2
    c = make(i)
    try:
        net, p, sim, r = S2.simulate2(c)
        D, _, _, _, starts, quay, cal = S2.setup2(c)
        g, y = S2.idle_nodes(D)
        ck = C.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
        n = r["n_vessel"][0]
        w = r["w1g"]
        out = dict(i=i, kind=c["geo"]["kind"], rule=c["rule"], pocket=int(bool(c["geo"].get("pocket"))), hold=str(c["hold"]), S=c["S"], K=c["K"],
                   lift=c.get("lift", "cradle"), n=n, w1=r["w1"]["bound"], w1g=w["bound"], binding=w["binding"], Q=w["Q"],
                   ok=int(ck["ok"]), err=" / ".join(ck["errors"][:2]),
                   thm3=int(bool(r.get("thm3") and any(a > b for a, b in zip(r["n_ramp"], r["thm3"]["bound"])))))
        if "joint_ub" in r:
            out.update(joint=sum(r["n_vessel"]) + sum(r["n_ramp"]), joint_ub=r["joint_ub"]["ub"], shared=int(not c.get("K_u")))
        if not c.get("n_unload"):
            ch = w["chain"]
            h = C2.hyp(net, p, sim.trips, starts, ch["res"].split("|") if ch else None, tuple(r["w1"]["cut"].split("|")))
            out.update(opp=h["opp"], phase=h["phase"], bmax=ch["bmax"] if ch else "", phased=int(bool(ch and ch["phased"])), zone=h["zone"])
        return out
    except Exception:
        return dict(i=i, error=traceback.format_exc()[-800:])


def bad_of(r):
    why = []
    if "error" in r:
        return ["error"]
    if r["n"] > r["w1"]:
        why.append("over_w1")
    if r["n"] > r["w1g"]:
        why.append("over_w1g")
    if not r["ok"]:
        why.append("check")
    if r["thm3"]:
        why.append("thm3")
    if "joint" in r and r["joint"] > r["joint_ub"]:
        why.append("joint")
    if "opp" in r:
        if r["opp"]:
            why.append("opp")
        if r["phased"] and r["bmax"] != "" and r["bmax"] != math.inf and r["phase"] > r["bmax"]:
            why.append("phase")
        if r["zone"] > r["Q"]:
            why.append("zone")
    return why


def init():
    pin(list(range(1, os.cpu_count())))


COLS = ["i", "kind", "rule", "pocket", "hold", "S", "K", "lift", "n", "w1", "w1g", "binding", "Q", "ok", "thm3", "joint", "joint_ub", "shared",
        "opp", "phase", "bmax", "phased", "zone", "why"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--procs", type=int, default=23)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=50)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="runs", part="random", start=a.start, n=a.n, code=code)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_runs_random_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    idx = list(range(a.start, a.start + a.n))
    chunks = [idx[k:k + a.chunk] for k in range(0, len(idx), a.chunk)]
    prog = Progress(out / "progress.json", len(idx), 0, a.procs, "Random port-archetype regression (W1′, joint bound, convoy, pocket, shipyard maps)", "runs")
    res = []
    for rs in slot_imap(work_chunk, chunks, a.procs, initializer=init, slots_dir=a.slots, tag="runs"):
        res += rs
        prog.write(done=len(res))
    res.sort(key=lambda r: r["i"])
    for r in res:
        r["why"] = "+".join(bad_of(r))
    bad = [r for r in res if r["why"]]
    with open(out / "cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(r for r in res if "error" not in r)
    with open(out / "bad.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS + ["err", "error"], extrasaction="ignore")
        w.writeheader()
        w.writerows(bad)
    ran = [r for r in res if "error" not in r]
    cnt = lambda k: sum(k in r["why"].split("+") for r in res)
    summ = dict(n=len(res), ran=len(ran), error=cnt("error"), over_w1=cnt("over_w1"), over_w1g=cnt("over_w1g"), check=cnt("check"), thm3=cnt("thm3"),
                joint=cnt("joint"), opp=cnt("opp"), phase=cnt("phase"), zone=cnt("zone"),
                tie_w1=sum(r["n"] == r["w1"] for r in ran), tie_w1g=sum(r["n"] == r["w1g"] for r in ran),
                tighter=sum(r["w1g"] < r["w1"] for r in ran), sum_w1=sum(r["w1"] for r in ran), sum_w1g=sum(r["w1g"] for r in ran),
                maps=sum(r["kind"] == "map" for r in ran), convoy=sum(r["rule"] == "convoy" for r in ran), pocket=sum(r["pocket"] for r in ran),
                joint_cases=sum("joint" in r for r in ran), hyp_cases=sum("opp" in r for r in ran),
                phased_bmax_lt_K=sum(1 for r in ran if r.get("phased") and r.get("bmax") not in ("", None) and r["bmax"] < r["K"]),
                zone_Q_lt_K=sum(1 for r in ran if r["Q"] < r["K"]))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(summ, ensure_ascii=False)[:300])
    print(out)
    print(json.dumps(summ, ensure_ascii=False))


def work_chunk(ks):
    return [work(i) for i in ks]


if __name__ == "__main__":
    main()
