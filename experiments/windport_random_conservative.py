"""Random port-type regression: per-monopile check of W″ under the conservative lifting rule (windport/lift.py). The generator is that
of the dead-end coupling (experiments/windport_random_deadend.make: dead directed segments, port time-in-port, main window form, same
seed). The cradle mode also keeps the area under the load closed (t_u), so cradle, direct-lift and mixed-lifting instances all run;
instances on the maps derived from Okpo and Yantai run as well (they read the two maps). Each instance: simulation (lift.install),
new checker (windport/check_lift.py), three upper bounds:
  W″_lift  W″ under the new rule (bound_lift.lift_parts; see the manuscript)
  W″_clear bound_dead.parts4(signed = "clear") (dq on the chain taken as max(0, dq), other parameters as in the original rule)
  W″       bound_dead.parts4 (Corollary 6 not extended)
Checks (monopile j finishes lifting at G + T_j): def (W″_lift(T_j) < j), lstar (lower end of L″_lift*(n) > T_n, with n the first,
median and last monopile), mono (W″_lift not non-decreasing), wle (W″_lift > W″ somewhere), def_clear / def_plain (W″_clear / W″
exceeded at some monopile, recorded separately: W″ takes the handover lower limit of the original rule and should hold under the new
rule; W″_clear holds only for direct lifts and can be exceeded when the handover is a set-down trip whose h_d is shorter than the time
for the tail to clear the chain head; see the manuscript), check (new checker fails), h5 (on chains where the premise of Corollary 6
holds, the number of vehicles in the quay zone rebuilt by the independent checker windows > min(K, Q_s), or opposing passes
intersect; windport/check2.hyp). Also recorded: tight (W″_lift strictly below W″_clear at some monopile), eq_last (W″_lift(T_n) = n).
Output results/windport_conservative_random_<config hash>/: config.json, progress.json, summary.json, bad.csv, cases.csv (per instance,
without wall times).
Run: python experiments/windport_random_conservative.py --gen dead --n 30000 --procs 16 --slots DIR
"""
import argparse
import csv
import hashlib
import json
import math
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402

CODE = ["windport/lift.py", "windport/bound_lift.py", "windport/check_lift.py", "windport/sim.py", "windport/sim2.py", "windport/bound.py", "windport/bound2.py",
        "windport/bound3.py", "windport/bound_dead.py", "windport/check.py", "windport/check2.py", "windport/archetypes.py", "windport/shipyard.py",
        "occupancy/sim.py", "occupancy/network.py", "occupancy/params.py", "exact/check.py", "experiments/windport_random.py",
        "experiments/windport_random_lift.py", "experiments/windport_random_deadend.py", "experiments/windport_random_conservative.py"]
FLAGS = ["error", "def", "lstar", "mono", "wle", "check", "h5", "def_clear", "def_plain"]
H = 3600.0


def work(arg):
    gen, i = arg
    import windport_random_deadend as R
    from windport import bound3 as B3
    from windport import bound_dead as BD
    from windport import bound_lift as BL
    from windport import check_lift as CL
    from windport import sim as S
    from windport import sim2 as S2
    c = R.make(gen, i)
    lift = "direct" if c["S"] == 0 else c.get("lift", "cradle")
    try:
        if gen != "main":                                      # whole-window W1′ over 120 h not needed (per-monopile only)
            orig, S2.bounds2 = S2.bounds2, (lambda *a, **k: None)
        try:
            net, p, sim, r = S2.simulate2(c)
        finally:
            if gen != "main":
                S2.bounds2 = orig
        D, _, _, _, starts, quay, cal = S2.setup2(c)
        g, y = S2.idle_nodes(D)
        ck = CL.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
        G, b = cal["crane"][0]
        L = b - G
        w = BL.lift_parts(c)
        f, fc, f0 = BL.wfn_lift(c, w), BD.wfn4(c, BD.parts4(c, signed="clear")), BD.wfn4(c, BD.parts4(c))
        T = sorted(x["F_vessel"] - G for x in sim.trips if x["F_vessel"] is not None and x["s"] >= G - 1e-6 and x["F_vessel"] <= b + 1e-6)
        if gen != "main":
            T = T[:c["n_load"]]
        why = []
        v, vc, v0 = [f(t) for t in T], [fc(t) for t in T], [f0(t) for t in T]
        viol = [n for n, x in enumerate(v, 1) if x < n]
        if viol:
            why.append("def")
        if any(a > b_ for a, b_ in zip(v, v0)):
            why.append("wle")
        vc_ = [n for n, x in enumerate(vc, 1) if x < n]
        v0_ = [n for n, x in enumerate(v0, 1) if x < n]
        if vc_:
            why.append("def_clear")
        if v0_:
            why.append("def_plain")
        for n in (sorted({1, (len(T) + 1) // 2, len(T)}) if T else []):
            if B3.lstar(f, n)[0] > T[n - 1] + 1e-6:
                why.append("lstar")
                break
        top = L if gen == "main" else (T[-1] + 3 * H if T else H)
        grid = sorted(set(T) | {k * 1.5 * top / 30 for k in range(31)})
        vals = [f(x) for x in grid]
        if any(v2 < v1 for v1, v2 in zip(vals, vals[1:])):
            why.append("mono")
        if not ck["ok"]:
            why.append("check")
        hb, hn = R.h5(c, net, p, sim.trips, starts, w)
        if hb:
            why.append("h5")
        return dict(gen=gen, i=i, kind=c["geo"]["kind"], map=int(c["geo"]["kind"] == "map"), rule=c["rule"], hold=str(c["hold"]), S=c["S"], K=c["K"],
                    lift=lift, x=p.get("release_frac", 0.0), hd=p["hd_s"], n=len(T), viol=len(viol), viol_clear=len(vc_), viol_plain=len(v0_), tight=int(any(a < b_ for a, b_ in zip(v, vc))),
                    eq_last=int(bool(T) and v[-1] == len(T)), n_clear=ck["n_clear"], n_under=ck["n_under"], h5_chains=hn,
                    lstar=round(B3.lstar(f, len(T))[0] / H, 6) if T else 0.0, T_last=round(T[-1] / H, 6) if T else 0.0,
                    why="+".join(why), err=" / ".join((ck["errors"] or [])[:2]), skipped=0)
    except Exception:
        return dict(gen=gen, i=i, why="error", error=traceback.format_exc()[-800:], skipped=0)


def work_chunk(ks):
    return [work(k) for k in ks]


def init():
    pin(list(range(1, os.cpu_count())))
    from windport import lift as LF
    LF.install()


COLS = ["gen", "i", "kind", "map", "rule", "hold", "S", "K", "lift", "x", "hd", "n", "viol", "viol_clear", "viol_plain", "tight", "eq_last", "n_clear", "n_under", "h5_chains", "lstar",
        "T_last", "why"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", choices=["main", "port", "dead"], default="dead")
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=25)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="conservative", part="random", round=4, gen=a.gen, start=a.start, n=a.n, code=code)
    out = ROOT / "results" / f"windport_conservative_random_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    idx = [(a.gen, i) for i in range(a.start, a.start + a.n)]
    prog = Progress(out / "progress.json", len(idx), 0, a.procs, f"random port-type regression ({a.gen}: per-monopile W″ under conservative lifting)", "conservative")
    res = []
    try:
        for rs in slot_imap(work_chunk, [idx[k:k + a.chunk] for k in range(0, len(idx), a.chunk)], a.procs, initializer=init, slots_dir=a.slots,
                            tag="conservative"):
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res.sort(key=lambda r: r["i"])
    ran = [r for r in res if not r["skipped"] and r["why"] != "error"]
    with open(out / "cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(ran)
    with open(out / "bad.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS + ["err", "error"], extrasaction="ignore")
        w.writeheader()
        w.writerows(r for r in res if r["why"])
    summ = dict(gen=a.gen, n=len(res), skipped_cradle=sum(r["skipped"] for r in res), ran=len(ran), maps=sum(r["map"] for r in ran),
                cradle=sum(r["lift"] == "cradle" for r in ran), direct=sum(r["lift"] == "direct" for r in ran), mixed=sum(r["lift"] == "mixed" for r in ran),
                **{k: sum(k in r["why"].split("+") for r in res) for k in FLAGS}, lifts_checked=sum(r["n"] for r in ran),
                lifts_violating=sum(r["viol"] for r in ran), lifts_violating_clear=sum(r["viol_clear"] for r in ran), clear_viol_by_lift={k: sum(r["viol_clear"] > 0 for r in ran if r["lift"] == k) for k in ("cradle", "direct", "mixed")}, lifts_violating_plain=sum(r["viol_plain"] for r in ran), tight=sum(r["tight"] for r in ran), eq_last=sum(r["eq_last"] for r in ran),
                vehicle_lifts_checked=sum(r["n_clear"] for r in ran), under_checked=sum(r["n_under"] for r in ran),
                h5_cases=sum(r["h5_chains"] > 0 for r in ran), h5_chains=sum(r["h5_chains"] for r in ran))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(summ, ensure_ascii=False)[:300])
    print(out)
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
