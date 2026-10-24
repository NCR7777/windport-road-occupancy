"""Random-port per-lift regression of the unified bound entry (windport/bound_all.py); each case runs under both lifting rules.

Generators (--gen):
  a     generator of the spatial additions (experiments/windport_random_spatial.make: A1 / side-by-side cradles / passing places /
        maps derived from Okpo and Yantai with relaxed storage areas; crane reach, reserved periods and alternative turns random);
  dead  directed dead-end segments of the dead-end coupling (experiments/windport_random_deadend.make_dead: mostly Q_h = 0, single
        lane split into 0–3 blocks, S = 0–3, x ∈ {0, 0.5, 1}), plus, with seed 37,500,000 + i, reserved periods (30 %) and crane
        reach (40 % when S ≥ 2, with first-come-first-served and x = 0).
Each case: original lifting rule (sim4.simulate4, windport/check4.py, W″ = bound_all.w2) and conservative lifting rule (simulate4
under lift.installed(), windport/check_all.py, W″_lift = bound_all.w2_lift). Per-lift checks (lift j completes at G + T_j):
  def / def_lift      W″(T_j) < j / W″_lift(T_j) < j
  lstar / lstar_lift  lower end of L″*(n) > T_n (n = 1, median, last lift)
  mono / mono_lift    not non-decreasing (at every T_j and at 31 equally spaced points)
  check / check_lift  independent checker fails
  branch              without crane reach and reserved periods: W″ ≠ bound_dead.wfn4 (per lift) or W″_lift ≠ bound_lift.wfn_lift;
                      with them: W″ > bound4.wprime4_fn or W″ > wfn4
  wle                 W″_lift above the W″ of the same case at some lift (with equal parameters the conservative rule only adds
                      terms and only increases parameters)
Also recorded: tight (the unified entry is strictly below the minimum of the branch functions at some lift) and tie (number of
lifts with W″(T_j) = j).
Output results/windport_unified_random_<config hash>/: config.json, progress.json, summary.json, bad.csv, cases.csv (per case, no
wall-clock times), chunks/ (resume cache).
Run: python experiments/windport_random_unified.py --gen a --start 24000 --n 12000 --procs 23 --slots DIR
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

CODE = ["windport/sim.py", "windport/sim2.py", "windport/sim3.py", "windport/sim4.py", "windport/lift.py", "windport/bound.py", "windport/bound2.py",
        "windport/bound3.py", "windport/bound4.py", "windport/bound_dead.py", "windport/bound_lift.py", "windport/bound_all.py", "windport/check.py",
        "windport/check3.py", "windport/check4.py", "windport/check_lift.py", "windport/check_all.py", "windport/archetypes.py", "windport/shipyard.py",
        "occupancy/sim.py", "occupancy/network.py", "occupancy/params.py", "exact/check.py", "experiments/windport_random_spatial.py",
        "experiments/windport_random_deadend.py", "experiments/windport_random_unified.py"]
FLAGS = ["error", "def", "lstar", "mono", "check", "def_lift", "lstar_lift", "mono_lift", "check_lift", "branch", "wle"]
H = 3600.0


def make(gen, i):
    if gen == "a":
        import windport_random_spatial as RA
        return RA.make(i)
    import windport_random_deadend as RB
    c = RB.make_dead(i)
    R = random.Random(37_500_000 + i)
    if R.random() < 0.3:
        c["reserve"] = dict(f=R.choice([0.1, 0.25, 0.5]), T_h=R.choice([0.5, 1.0, 2.0, 4.0]))
    if c["S"] >= 2 and R.random() < 0.4:
        c["p"] = dict(c["p"], reach=R.randint(1, c["S"] - 1), shift_s=R.choice([300.0, 1800.0, 3600.0]), release_frac=0.0,
                      **R.choice([{}, dict(reach_key="finish"), dict(far_prestage=True)]))
        c["rule"] = "fcfs"
    c["_turn"] = False
    return c


def turn(c, tx, ts, tf):
    """As in windport_random_spatial.work: add alternative turn actions to a random half of the nodes or of the turns."""
    from windport import sim as S
    from windport import sim4 as S4
    if not tx:
        return c
    D0, net0 = S4.get_net4(c["geo"], S.params(c))
    R = random.Random(tf)
    if R.random() < 0.5:
        ex = {n: ts for n in sorted(D0["nodes"]) if R.random() < 0.5}
    else:
        ex = {f"{n}|{a}|{b}": ts for n in sorted(net0.incident) for a in sorted(net0.incident[n]) for b in sorted(net0.incident[n]) if a != b and R.random() < 0.5}
    return dict(c, p=dict(c["p"], turn_extra=ex))


def one_sem(c, lift):
    """One lifting rule: (lift completion times T, checker result)."""
    from windport import check4 as C4
    from windport import check_all as CA
    from windport import lift as LF
    from windport import sim as S
    from windport import sim2 as S2
    from windport import sim4 as S4
    import contextlib
    with (LF.installed() if lift else contextlib.nullcontext()):
        net, p, sim, r = S4.simulate4(dict(c, w4=False))
        D, _, _, _, starts, quay, cal = S4.setup4(c)
        g, y = S2.idle_nodes(D)
        rv = None
        if r.get("reserve"):
            rv = dict(res=tuple(r["reserve"]["res"].split("|")), f=r["reserve"]["f"], T=r["reserve"]["T"], H_end=(c["horizon_h"] + 1) * H)
        ck = (CA if lift else C4).check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y, reserve=rv)
    G = cal["crane"][0][0]
    T = sorted(x["F_vessel"] - G for x in sim.trips if x["F_vessel"] is not None)[:c["n_load"]]
    return T, ck


def flags(f, T, tag, why):
    from windport import bound3 as B3
    viol = [n for n, t in enumerate(T, 1) if f(t) < n]
    if viol:
        why.append("def" + tag)
    for n in (sorted({1, (len(T) + 1) // 2, len(T)}) if T else []):
        if B3.lstar(f, n)[0] > T[n - 1] + 1e-6:
            why.append("lstar" + tag)
            break
    top = T[-1] + 3 * H if T else H
    grid = sorted(set(T) | {k * 1.5 * top / 30 for k in range(31)})
    vals = [f(x) for x in grid]
    if any(v2 < v1 for v1, v2 in zip(vals, vals[1:])):
        why.append("mono" + tag)
    return len(viol), sum(1 for n, t in enumerate(T, 1) if f(t) == n)


def work(arg):
    gen, i = arg
    from windport import bound3 as B3
    from windport import bound4 as B4
    from windport import bound_all as BA
    from windport import bound_dead as BD
    from windport import bound_lift as BL
    c = make(gen, i)
    try:
        c = turn({k: v for k, v in c.items() if not k.startswith("_turn")}, c.get("_turn"), c.get("_turn_x"), c.get("_turn_seed"))
        why = []
        T0, ck0 = one_sem(c, False)
        T1, ck1 = one_sem(c, True)
        w0, w1 = BA.parts(c), BA.parts(c, lift=True)
        f0, f1 = BA.w2(c, w0), BA.w2_lift(c, w1)
        v0, t0 = flags(f0, T0, "", why)
        v1, t1 = flags(f1, T1, "_lift", why)
        if not ck0["ok"]:
            why.append("check")
        if not ck1["ok"]:
            why.append("check_lift")
        ext = w0["Sr"] is not None or w0["rp"] is not None
        tight = 0
        if c["geo"]["kind"] != "map":                   # branch functions enumerate cuts; too slow on maps (see tests)
            b0, b1 = BD.wfn4(c, w0), BL.wfn_lift(c, w1)
            a0 = B4.wprime4_fn(c) if ext else None
            bad = (any(f0(t) != b0(t) for t in T0) or any(f1(t) != b1(t) for t in T1)) if not ext else \
                (any(f0(t) > min(a0(t), b0(t)) for t in T0) or any(f1(t) > b1(t) for t in T1))
            if bad:
                why.append("branch")
            tight = sum(1 for t in T0 if ext and f0(t) < min(a0(t), b0(t))) + sum(1 for t in T1 if ext and f1(t) < b1(t))
        if any(f1(t) > f0(t) for t in T0 + T1):
            why.append("wle")
        p = c["p"]
        return dict(gen=gen, i=i, kind=c["geo"]["kind"], storage=c["geo"].get("storage", ""), rule=c["rule"], hold=str(c["hold"]), S=c["S"], K=c["K"],
                    lift=c["lift"] if c["S"] else "direct", x=p.get("release_frac", 0.0), reach=p.get("reach", ""), reserve=(c.get("reserve") or {}).get("f", ""),
                    turn=int(bool(p.get("turn_extra"))), n=len(T0), n_lift=len(T1), viol=v0, viol_lift=v1, tie=t0, tie_lift=t1, tight=tight,
                    n_far=ck0["n_far"], n_res=ck0["n_res"], n_clear=ck1["n_clear"], n_under=ck1["n_under"],
                    lstar=round(B3.lstar(f0, len(T0))[0] / H, 6) if T0 else 0.0, lstar_lift=round(B3.lstar(f1, len(T1))[0] / H, 6) if T1 else 0.0,
                    T_last=round(T0[-1] / H, 6) if T0 else 0.0, T_last_lift=round(T1[-1] / H, 6) if T1 else 0.0, why="+".join(why),
                    err=" / ".join((ck0["errors"] or [])[:1] + (ck1["errors"] or [])[:1]))
    except Exception:
        return dict(gen=gen, i=i, why="error", error=traceback.format_exc()[-800:])


def work_chunk(ks):
    return [work(k) for k in ks]


def init():
    pin(list(range(1, os.cpu_count())))


COLS = ["gen", "i", "kind", "storage", "rule", "hold", "S", "K", "lift", "x", "reach", "reserve", "turn", "n", "n_lift", "viol", "viol_lift", "tie", "tie_lift",
        "tight", "n_far", "n_res", "n_clear", "n_under", "lstar", "lstar_lift", "T_last", "T_last_lift", "why"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", choices=["a", "dead"], required=True)
    ap.add_argument("--n", type=int, default=12000)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--procs", type=int, default=23)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=10)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="unified", part="random", gen=a.gen, start=a.start, n=a.n, code=code)
    out = ROOT / "results" / f"windport_unified_random_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    (out / "chunks").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    idx = [(a.gen, i) for i in range(a.start, a.start + a.n)]
    chunks = [idx[k:k + a.chunk] for k in range(0, len(idx), a.chunk)]
    cache = out / "chunks"
    done = {int(f.stem): json.loads(f.read_text(encoding="utf-8")) for f in cache.glob("*.json")}
    todo = [ch for ch in chunks if ch[0][1] not in done]
    res = [r for v in done.values() for r in v]
    prog = Progress(out / "progress.json", len(idx), len(res), a.procs, f"unified bound random regression ({a.gen}: per-lift W″ / W″_lift under both lifting rules)", "unified")
    try:
        for rs in slot_imap(work_chunk, todo, a.procs, initializer=init, slots_dir=a.slots, tag="unified"):
            (cache / f"{rs[0]['i']}.json").write_text(json.dumps(rs, ensure_ascii=False), encoding="utf-8")
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res.sort(key=lambda r: r["i"])
    ran = [r for r in res if r["why"] != "error"]
    with open(out / "cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(ran)
    with open(out / "bad.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS + ["err", "error"], extrasaction="ignore")
        w.writeheader()
        w.writerows(r for r in res if r["why"])
    summ = dict(gen=a.gen, n=len(res), ran=len(ran), **{k: sum(k in r["why"].split("+") for r in res) for k in FLAGS},
                lifts=sum(r["n"] for r in ran), lifts_lift=sum(r["n_lift"] for r in ran), viol=sum(r["viol"] for r in ran),
                viol_lift=sum(r["viol_lift"] for r in ran), tie=sum(r["tie"] for r in ran), tie_lift=sum(r["tie_lift"] for r in ran),
                tight=sum(r["tight"] for r in ran), cases_tight=sum(1 for r in ran if r["tight"]),
                by_lift={k: sum(r["lift"] == k for r in ran) for k in ("cradle", "direct", "mixed")}, maps=sum(r["kind"] == "map" for r in ran),
                reach=sum(r["reach"] != "" for r in ran), reserve=sum(r["reserve"] != "" for r in ran), turn=sum(r["turn"] for r in ran),
                side=sum(r["kind"] == "A1side" for r in ran), pass_=sum(r["kind"] == "A1pass" for r in ran), far=sum(r["n_far"] for r in ran),
                vehicle_lifts=sum(r["n_clear"] for r in ran), under=sum(r["n_under"] for r in ran))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(summ, ensure_ascii=False)[:300])
    import shutil
    shutil.rmtree(cache)
    print(out)
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
