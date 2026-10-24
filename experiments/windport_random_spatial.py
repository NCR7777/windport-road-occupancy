"""The spatial additions: random regression for W″ (windport/bound4.py: W′ plus the crane-reach and reserved-period terms) and L*(n),
with the independent check of windport/check4.py.

Generator (seed 37,000,000 + i): port type A1 (various sizes), side-by-side cradles A1side, A1pass with a passing place, graphs derived
from Okpo / Yantai (one-voyage or relaxed storage area); random vehicle speeds, monopile length, jacking, set-down, crane cycle and
steering stops; about half of the cases have crane reach (S_r ∈ [1, S − 1], t_sh 5 min–2 h, FCFS only, x = 0; the quay-bay dispatch is
drawn from start / finish / prestage), about 30% have reserved periods on the shared road section (f = 10–50%, period 0.5–4 h), about 30%
add an alternative turning manoeuvre (5 min or 30 min) at randomly chosen nodes or turns; the reserved-period term is rounded per open
interval. The crane opens at G for 120 h; n piles are released at time 0. Each case is checked lift by lift (lift j finishes at G + T_j):
  def    some W″(T_j) < j
  lstar  lower end of L*(n) > T_n (n = 1, median, last)
  mono   W″ is not non-decreasing over the T_j and a grid of equally spaced points
  check  windport/check4.py fails
Also recorded, tight_reach / tight_res: the number of lifts at which the crane-reach term / reserved-period term is strictly below W′
(the new term binds).
Output results/windport_spatial_random_<config hash>/: config.json, progress.json, summary.json, bad.csv, cases.csv (per case, no
wall-clock times).
Run: python experiments/windport_random_spatial.py --start 0 --n 24000 --procs 11 --slots DIR
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

CODE = ["windport/sim.py", "windport/sim2.py", "windport/sim4.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py",
        "windport/bound4.py", "windport/check.py", "windport/check3.py", "windport/check4.py", "windport/archetypes.py", "windport/shipyard.py",
        "occupancy/sim.py", "occupancy/network.py", "occupancy/params.py", "exact/check.py", "experiments/windport_random_spatial.py"]
FLAGS = ["error", "def", "lstar", "mono", "check", "fast"]
KMH = 1 / 3.6
OPEN_H = 120


def make(i):
    R = random.Random(37_000_000 + i)
    p = dict(v_loaded=R.choice([0.5, 1.0, 2.5, 5.0]) * KMH, v_empty=R.choice([1.0, 2.0, 5.0, 10.0]) * KMH,
             Lv=R.choice([60.0, 90.0, 110.0, 130.0]), hp_s=R.choice([300.0, 900.0, 1800.0, 3600.0, 7200.0]),
             hd_s=R.choice([60.0, 300.0, 900.0, 1800.0, 5400.0]), lift_s=R.choice([900.0, 1800.0, 3600.0, 7200.0]),
             sweep_steer_s=R.choice([None, 120.0, 120.0, 900.0]), release_frac=0.0)
    u = R.random()
    if u < 0.15:
        site = R.choice(["okpo", "yantai"])
        geo = dict(kind="map", site=site, cradle_mode=R.choice(["on_road", "pull_in"]), n_cradles=R.choice([1, 2, 3, 4, 6]) if site == "okpo" else 1)
        if R.random() < 0.5:
            geo["storage"] = "multi"
    else:
        dist = R.choice([200.0, 400.0, 800.0, 1500.0])
        geo = dict(kind=R.choice(["A1", "A1", "A1side", "A1pass"]), dist_m=dist, corridor_m=R.choice([0.3, 0.6, 1.0]) * dist,
                   n_junctions=R.choice([0, 1, 2]), n_cradles=R.choice([1, 2, 3, 4, 6]))
        if geo["kind"] == "A1side":
            geo.update(pitch_m=R.choice([15.0, 20.0, 40.0]), bay_m=R.choice([20.0, 40.0, 80.0]))
        else:
            geo.update(cradle_mode=R.choice(["on_road", "pull_in"]), cradle_spacing=R.choice([60.0, 110.0, 150.0]), ramp_at=None)
            if geo["kind"] == "A1pass":
                geo.update(pp_m=R.choice([0.2, 0.4]) * geo["corridor_m"], pp_w=R.choice([16.0, 20.0]))
            elif R.random() < 0.3:
                geo["corridor_w"] = R.choice([10.0, 16.0])
        if R.random() < 0.3:
            geo["pocket"] = R.choice([10.0, 30.0])
    S_ = min(R.choice([0, 1, 2, 3, 4, 6]), geo["n_cradles"])
    K = R.choice([1, 2, 3, 4, 6, 8])
    G = R.choice([0, 1, 3, 8, 24])
    n = R.choice([3, 5, 8, 10, 12])
    lift = R.choice(["cradle", "mixed"]) if S_ else "cradle"
    c = dict(geo=geo, p=p, S=S_, K=K, lift=lift, horizon_h=G + OPEN_H, cal=dict(crane=[[G, G + OPEN_H]]), n_load=n,
             hold=R.choice([0, 0, 1, "inf"]), rule=R.choice(["fcfs", "fcfs", "convoy"]))
    if S_ >= 2 and R.random() < 0.5:
        p.update(reach=R.randint(1, S_ - 1), shift_s=R.choice([300.0, 1800.0, 3600.0, 7200.0]))
        c["rule"] = "fcfs"
        disp = R.choice(["start", "finish", "prestage"])          # dispatch variants for choosing the quay bay under reach
        if disp == "finish":
            p["reach_key"] = "finish"
        elif disp == "prestage":
            p["far_prestage"] = True
    if R.random() < 0.3:
        c["reserve"] = dict(f=R.choice([0.1, 0.25, 0.5]), T_h=R.choice([0.5, 1.0, 2.0, 4.0]))
    c["_turn"] = R.random() < 0.3
    c["_turn_x"] = R.choice([300.0, 1800.0])
    c["_turn_seed"] = R.random()
    return c


def work(i):
    from windport import bound3 as B3
    from windport import bound4 as B4
    from windport import check4 as C4
    from windport import sim as S
    from windport import sim2 as S2
    from windport import sim4 as S4
    c = make(i)
    try:
        tx, ts, tf = c.pop("_turn"), c.pop("_turn_x"), c.pop("_turn_seed")
        if tx:                                          # alternative manoeuvres at a random half of the nodes (or of the turns "node|from|to")
            D0, net0 = S4.get_net4(c["geo"], S.params(c))
            R = random.Random(tf)
            if R.random() < 0.5:
                ex = {n: ts for n in sorted(D0["nodes"]) if R.random() < 0.5}
            else:
                ex = {f"{n}|{a}|{b}": ts for n in sorted(net0.incident) for a in sorted(net0.incident[n]) for b in sorted(net0.incident[n])
                      if a != b and R.random() < 0.5}
            c["p"] = dict(c["p"], turn_extra=ex)
        c["w4"] = False
        net, p, sim, r = S4.simulate4(c)
        D, _, _, _, starts, quay, cal = S4.setup4(c)
        g, y = S2.idle_nodes(D)
        rv = None
        if r.get("reserve"):
            rv = dict(res=tuple(r["reserve"]["res"].split("|")), f=r["reserve"]["f"], T=r["reserve"]["T"], H_end=(c["horizon_h"] + 1) * 3600.0)
        ck = C4.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y, reserve=rv)
        G = cal["crane"][0][0]
        w = B4.parts4(c)
        f = B4.wprime4_fn(c, w)
        f3 = B4.wprime_fast(c, w)                       # same values as windport.bound3.wprime_fn (checked by tests), fast
        T = sorted(x["F_vessel"] - G for x in sim.trips if x["F_vessel"] is not None)[:c["n_load"]]
        why = []
        viol = [n for n, t in enumerate(T, 1) if f(t) < n]
        if viol:
            why.append("def")
        for n in (sorted({1, (len(T) + 1) // 2, len(T)}) if T else []):
            if B3.lstar(f, n)[0] > T[n - 1] + 1e-6:
                why.append("lstar")
                break
        top = T[-1] + 3 * 3600.0 if T else 3600.0
        grid = sorted(set(T) | {k * 1.5 * top / 30 for k in range(31)})
        vals = [f(x) for x in grid]
        if any(v2 < v1 for v1, v2 in zip(vals, vals[1:])):
            why.append("mono")
        if not ck["ok"]:
            why.append("check")
        if c["geo"]["kind"] != "map":                  # fast W′ equals the committed bound3.wprime_fn per lift (too slow on shipyard maps; tests check it)
            slow = B3.wprime_fn(c, w)
            if any(slow(t) != f3(t) for t in T):
                why.append("fast")
        P = w["P"]
        tr = sum(1 for t in T if B4.reach_R(P, w["G"], t, w["Sr"], w["sh"]) < f3(t))
        ts_ = sum(1 for t in T if B4.reserve_R(w["rp"], P.S, c["K"], w["G"], t, P.p, w["hp"]) < f3(t))
        tie = sum(1 for n, t in enumerate(T, 1) if f(t) == n)
        return dict(i=i, kind=c["geo"]["kind"], storage=c["geo"].get("storage", ""), rule=c["rule"], hold=str(c["hold"]), S=c["S"], K=c["K"],
                    lift=c["lift"], reach=p.get("reach", ""), shift=p.get("shift_s", ""),
                    disp="finish" if p.get("reach_key") == "finish" else ("prestage" if p.get("far_prestage") else ""), reserve=(c.get("reserve") or {}).get("f", ""),
                    turn=int(tx), n=len(T), viol=len(viol), tie=tie, tight_reach=tr, tight_res=ts_, n_far=ck["n_far"], n_res=ck["n_res"],
                    lstar_last=B3.lstar(f, len(T))[0] / 3600.0 if T else 0.0, T_last=T[-1] / 3600.0 if T else 0.0, why="+".join(why),
                    err=" / ".join((ck["errors"] or [])[:2]))
    except Exception:
        return dict(i=i, why="error", error=traceback.format_exc()[-800:])


def work_chunk(ks):
    return [work(k) for k in ks]


def init():
    pin(list(range(1, os.cpu_count())))


COLS = ["i", "kind", "storage", "rule", "hold", "S", "K", "lift", "reach", "shift", "disp", "reserve", "turn", "n", "viol", "tie", "tight_reach", "tight_res",
        "n_far", "n_res", "lstar_last", "T_last", "why"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24000)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--procs", type=int, default=11)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=25)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="spatial", part="random", start=a.start, n=a.n, code=code)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_spatial_random_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    idx = list(range(a.start, a.start + a.n))
    chunks = [idx[k:k + a.chunk] for k in range(0, len(idx), a.chunk)]
    cache = out / "chunks"                                       # written chunk by chunk, resumable: one JSON per chunk (not compared in the summary)
    cache.mkdir(exist_ok=True)
    done = {int(f.stem): json.loads(f.read_text(encoding="utf-8")) for f in cache.glob("*.json")}
    todo = [c for c in chunks if c[0] not in done]
    prog = Progress(out / "progress.json", len(idx), sum(len(v) for v in done.values()), a.procs, "Random regression (per-lift W″, L*, check4)", "spatial")
    res = [r for v in done.values() for r in v]
    for rs in slot_imap(work_chunk, todo, a.procs, initializer=init, slots_dir=a.slots, tag="spatial"):
        (cache / f"{rs[0]['i']}.json").write_text(json.dumps(rs, ensure_ascii=False), encoding="utf-8")
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
    summ = dict(n=len(res), ran=len(ran), **{k: sum(k in r["why"].split("+") for r in res) for k in FLAGS},
                lifts_checked=sum(r["n"] for r in ran), lifts_violating=sum(r["viol"] for r in ran), lifts_tie=sum(r["tie"] for r in ran),
                cases_reach=sum(1 for r in ran if r["reach"] != ""), cases_reserve=sum(1 for r in ran if r["reserve"] != ""),
                cases_turn=sum(r["turn"] for r in ran), cases_side=sum(r["kind"] == "A1side" for r in ran), cases_pass=sum(r["kind"] == "A1pass" for r in ran),
                cases_map=sum(r["kind"] == "map" for r in ran), cases_map_multi=sum(r["storage"] == "multi" for r in ran),
                far_lifts=sum(r["n_far"] for r in ran), lifts_tight_reach=sum(r["tight_reach"] for r in ran),
                cases_tight_reach=sum(1 for r in ran if r["tight_reach"]), lifts_tight_res=sum(r["tight_res"] for r in ran),
                cases_tight_res=sum(1 for r in ran if r["tight_res"]))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(summ, ensure_ascii=False)[:300])
    print(out)
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
