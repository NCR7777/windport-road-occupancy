"""Random-port per-lift regression of the unified bound in the main geometry (both lifting rules per case), also checking the
cradle-mode chains with signed dq (signed in bound_all.parts, Corollary 7(c)).

Generators and per-lift checks as in experiments/windport_random_unified.py (a: generator of the spatial additions; dead: directed
dead-end segments of the dead-end coupling plus reserved periods and crane reach), with a separate seed range;
each worker process calls archetypes.use("main"), and the first cradle position of the archetypes (A1, A2, A3, side-by-side
cradles, passing places) is drawn from 40, 110, 170, 250 m with seed 37,600,000 + i (covers the new parameter; shipyard maps are
not affected). Each case: original-rule W″ (bound_all.w2), conservative-rule W″_lift (with the signed-dq chains) and W″_lift
without these chains (signed=False).
Flags (why):
  def / def_lift / lstar / lstar_lift / mono / mono_lift / check / check_lift   as in the unified-bound regression
  branch     without crane reach and reserved periods: W″ ≠ bound_dead.wfn4 or W″_lift without the new chains ≠ bound_lift.wfn_lift
             (per lift); with them: W″ > min(bound4.wprime4_fn, wfn4) or W″_lift > wfn_lift
  signed_up  W″_lift with the new chains above W″_lift without them at some lift (terms are only added, must not occur)
  wle        W″_lift above the W″ of the same case at some lift
Also recorded: new_chains (number of added chains with dq < 0), tight_signed (lifts where W″_lift with the new chains is strictly
below W″_lift without them).
Output results/windport_maingeom_random_<config hash>/: config.json, progress.json, summary.json, bad.csv, cases.csv, chunks/
(resume cache, deleted at the end).
Run: python experiments/windport_random_maingeom.py --gen a --start 48000 --n 12000 --procs 12 --slots DIR
"""
import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402
import windport_random_unified as ER                           # noqa: E402

CODE = ER.CODE[:-1] + ["experiments/windport_random_unified.py", "experiments/windport_random_maingeom.py"]
FIRST = [40.0, 110.0, 170.0, 250.0]
FLAGS = ER.FLAGS + ["signed_up"]
H = 3600.0


def make(gen, i):
    c = ER.make(gen, i)
    if c["geo"]["kind"] in ("A1", "A2", "A3", "A1side", "A1pass"):
        c["geo"] = dict(c["geo"], gate_cradle_m=random.Random(37_600_000 + i).choice(FIRST))
    return c


def work(arg):
    gen, i = arg
    from windport import bound4 as B4
    from windport import bound_all as BA
    from windport import bound_dead as BD
    from windport import bound_lift as BL
    from windport import bound3 as B3
    c = make(gen, i)
    try:
        c = ER.turn({k: v for k, v in c.items() if not k.startswith("_turn")}, c.get("_turn"), c.get("_turn_x"), c.get("_turn_seed"))
        why = []
        T0, ck0 = ER.one_sem(c, False)
        T1, ck1 = ER.one_sem(c, True)
        w0, w1, w1u = BA.parts(c), BA.parts(c, lift=True), BA.parts(c, lift=True, signed=False)
        f0, f1, f1u = BA.w2(c, w0), BA.w2_lift(c, w1), BA.w2_lift(c, w1u)
        v0, t0 = ER.flags(f0, T0, "", why)
        v1, t1 = ER.flags(f1, T1, "_lift", why)
        if not ck0["ok"]:
            why.append("check")
        if not ck1["ok"]:
            why.append("check_lift")
        ext = w0["Sr"] is not None or w0["rp"] is not None
        if c["geo"]["kind"] != "map":
            b0, b1 = BD.wfn4(c, w0), BL.wfn_lift(c, w1u)
            if not ext:
                bad = any(f0(t) != b0(t) for t in T0) or any(f1u(t) != b1(t) for t in T1)
            else:
                a0 = B4.wprime4_fn(c)
                bad = any(f0(t) > min(a0(t), b0(t)) for t in T0) or any(f1u(t) > b1(t) for t in T1)
            if bad:
                why.append("branch")
        if any(f1(t) > f1u(t) for t in T0 + T1):
            why.append("signed_up")
        if any(f1(t) > f0(t) for t in T0 + T1):
            why.append("wle")
        p = c["p"]
        return dict(gen=gen, i=i, kind=c["geo"]["kind"], first=c["geo"].get("gate_cradle_m", ""), storage=c["geo"].get("storage", ""), rule=c["rule"],
                    hold=str(c["hold"]), S=c["S"], K=c["K"], lift=c["lift"] if c["S"] else "direct", hd=p.get("hd_s", ""), x=p.get("release_frac", 0.0),
                    reach=p.get("reach", ""), reserve=(c.get("reserve") or {}).get("f", ""), turn=int(bool(p.get("turn_extra"))), n=len(T0), n_lift=len(T1),
                    viol=v0, viol_lift=v1, tie=t0, tie_lift=t1, new_chains=len(w1["chains"]) - len(w1u["chains"]),
                    tight_signed=sum(1 for t in T1 if f1(t) < f1u(t)), n_far=ck0["n_far"], n_res=ck0["n_res"], n_clear=ck1["n_clear"], n_under=ck1["n_under"],
                    lstar=round(B3.lstar(f0, len(T0))[0] / H, 6) if T0 else 0.0, lstar_lift=round(B3.lstar(f1, len(T1))[0] / H, 6) if T1 else 0.0,
                    T_last=round(T0[-1] / H, 6) if T0 else 0.0, T_last_lift=round(T1[-1] / H, 6) if T1 else 0.0, why="+".join(why),
                    err=" / ".join((ck0["errors"] or [])[:1] + (ck1["errors"] or [])[:1]))
    except Exception:
        return dict(gen=gen, i=i, why="error", error=traceback.format_exc()[-800:])


def work_chunk(ks):
    return [work(k) for k in ks]


def init():
    from windport import archetypes as A
    pin(list(range(1, os.cpu_count())))
    A.use("main")


COLS = ["gen", "i", "kind", "first", "storage", "rule", "hold", "S", "K", "lift", "hd", "x", "reach", "reserve", "turn", "n", "n_lift", "viol", "viol_lift", "tie",
        "tie_lift", "new_chains", "tight_signed", "n_far", "n_res", "n_clear", "n_under", "lstar", "lstar_lift", "T_last", "T_last_lift", "why"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", choices=["a", "dead"], required=True)
    ap.add_argument("--n", type=int, default=12000)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=10)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    from windport import archetypes as A
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="maingeom", part="random", gen=a.gen, start=a.start, n=a.n, first=FIRST, geometry=A.GEOMETRIES["main"], code=code)
    out = ROOT / "results" / f"windport_maingeom_random_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    (out / "chunks").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    idx = [(a.gen, i) for i in range(a.start, a.start + a.n)]
    chunks = [idx[k:k + a.chunk] for k in range(0, len(idx), a.chunk)]
    cache = out / "chunks"
    done = {int(f.stem): json.loads(f.read_text(encoding="utf-8")) for f in cache.glob("*.json")}
    todo = [ch for ch in chunks if ch[0][1] not in done]
    res = [r for v in done.values() for r in v]
    prog = Progress(out / "progress.json", len(idx), len(res), a.procs, f"main geometry random regression ({a.gen}: per lift under both lifting rules)", "maingeom")
    try:
        for rs in slot_imap(work_chunk, todo, a.procs, initializer=init, slots_dir=a.slots, tag="maingeom"):
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
                cases_new_chains=sum(1 for r in ran if r["new_chains"]), cases_tight_signed=sum(1 for r in ran if r["tight_signed"]),
                tight_signed=sum(r["tight_signed"] for r in ran), by_first={str(x): sum(1 for r in ran if r["first"] == x) for x in FIRST},
                by_lift={k: sum(r["lift"] == k for r in ran) for k in ("cradle", "direct", "mixed")}, maps=sum(r["kind"] == "map" for r in ran),
                reach=sum(r["reach"] != "" for r in ran), reserve=sum(r["reserve"] != "" for r in ran), turn=sum(r["turn"] for r in ran),
                side=sum(r["kind"] == "A1side" for r in ran), pass_=sum(r["kind"] == "A1pass" for r in ran), far=sum(r["n_far"] for r in ran),
                vehicle_lifts=sum(r["n_clear"] for r in ran), under=sum(r["n_under"] for r in ran))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(summ, ensure_ascii=False)[:300])
    shutil.rmtree(cache)
    print(out)
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
