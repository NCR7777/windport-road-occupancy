"""Rechecks every simulation row of the main geometry against the unified bound W″_lift (bound_all.w2_lift, cradle
mode including strings with signed dq); only the bound is recomputed, simulated counts and port times are taken from
the run directories.

Rows: the rerun batches of experiments/windport_maingeom.py, E2 (with the 600 s results merged in), the four batches of
the spatial additions and cdv, core, yards, span, xscan, and windport_sens_maingeom.py (its orig group, with the original
lifting rule, uses the unified W″ of the original rule). The per-row rules follow experiments/windport_recheck_unified.one
(window form: simulation / CP-SAT > bound, equality, binding term and the five regimes; port time:
W″_lift(port time) < n_v, L″* > port time); configs are built as in each batch (windport_recheck_unified.cfg_of; core and
yards use windport_maingeom.core_cfg / yard_cfg); every worker calls archetypes.use("main").
Also records signed: rows where the cradle mode has strings with dq < 0 and W″_lift with them is strictly tighter than
without them (bound_all.parts(signed=False)).
Not checked: rows in the fixed-duration representation and with "the cut as a single resource", unloading rows of pub,
port-time rows that are not fully loaded.
Output results/windport_maingeom_recheck_<config hash>/: config.json, progress.json, rows.csv, summary.csv, strat.csv, summary.md.
Run: python experiments/windport_recheck_maingeom.py --procs 16 --slots DIR
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402
import windport_runs as T                                    # noqa: E402
import windport_recheck_unified as ER                          # noqa: E402

H = 3600.0
CODE = ["windport/bound_all.py", "windport/bound_lift.py", "windport/bound_dead.py", "windport/bound4.py", "windport/bound.py", "windport/bound2.py",
        "windport/bound3.py", "windport/archetypes.py", "windport/sim.py", "windport/sim2.py", "windport/sim4.py", "windport/lift.py", "windport/shipyard.py",
        "occupancy/network.py", "occupancy/params.py", "experiments/windport_recheck_unified.py", "experiments/windport_maingeom.py",
        "experiments/windport_recheck_maingeom.py"]
LABEL = ER.LABEL


def one_dir(pre):
    ds = sorted(p for p in (ROOT / "results").glob(pre + "*") if p.is_dir() and len(p.name) == len(pre) + 12)
    assert len(ds) == 1, (pre, ds)
    return ds[0]


def dirs():
    """Batch → run directory of the main geometry (the unique one with the prefix)."""
    import windport_maingeom as F
    out = {b: one_dir(f"windport_maingeom_{b.replace(':', '_')}_") for b in F.rerun_batches()}
    out["e1e3:e2"] = one_dir("windport_maingeom_e2_")
    for p in F.SPATIAL:
        out[f"unified:{p}"] = one_dir(f"windport_maingeom_spatial_{p}_")
    out["unified:cdv"] = one_dir("windport_maingeom_cdv_")
    for p in ("core", "yards"):
        out[f"maingeom:{p}"] = one_dir(f"windport_maingeom_{p}_")
    for p in ("span", "xscan", "sens"):
        out[f"conservative:{p}"] = one_dir(f"windport_maingeom_{p}_")
    return out


def load(d, name="points.csv"):
    return list(csv.DictReader(open(d / name, encoding="utf-8")))


def items(D):
    out = []
    lng = {r["key"]: r for r in load(D["e1e3:e2"], "e2long/points.csv")}
    for b, d in D.items():
        for r in load(d):
            if b == "e1e3:e2":
                r = dict(r, **{k: v for k, v in lng.get(r["key"], {}).items() if k.startswith("cp_")})
            elif b == "extra:fix" or r.get("repr") == "fixed" or r.get("rep") in ("fix", "cut") or r.get("key", "").startswith("fix|"):
                continue
            elif b == "extra:pub" and r["pub"] != "out":
                continue
            elif b.startswith("unified:") and (r.get("step") in ("s3", "cf") or r.get("rep") == "fix"):
                continue
            out.append((b, "plain" if b == "conservative:sens" and r["var"] == "orig" else "lift", r))
    return out


def cfg_of(batch, row):
    src, part = batch.split(":")
    if src == "maingeom":
        import windport_maingeom as F
        d = T.dec(row["key"])
        return (F.core_cfg(d) if part == "core" else F.yard_cfg(d)), "port"
    return ER._cfg_of(batch, row)


def one(arg):
    from windport import bound_all as BA
    batch, sem, row = arg
    out = ER.one(arg)
    if out.get("skip") or out["lift"] != "cradle" or sem != "lift":
        return out
    c, form = cfg_of(batch, row)
    w = ER.parts(c, sem)
    if not any(ch["dq"] < -1e-6 for ch in w["chains"]):
        return out
    G = c["cal"]["crane"][0][0] * H
    f0 = BA.w2_lift(c, dict(BA.parts(c, lift=True, signed=False), G=G))
    if form == "port":
        n = int(row.get("n_v") or c["n_load"])
        out["signed"] = int(BA.lstar(f0, n)[0] / H < out["lstar"] - 1e-9)
    else:
        out["signed"] = int(f0((c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * H) > out["new"])
    return out


def chunk(its):
    return [one(x) for x in its]


def init():
    from windport import archetypes as A
    from windport import lift as LF
    pin(list(range(1, os.cpu_count())))
    LF.install()
    A.use("main")
    ER._cfg_of, ER.cfg_of = ER.cfg_of, cfg_of


COLS = ER.COLS[:-1] + ["signed", "group"]


def pct(a, n):
    return f"{a / n:.1%}" if n else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    D = dirs()
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    psha = {b: hashlib.sha256(b"".join((d / n).read_bytes() for n in ("points.csv", "e2long/points.csv") if (d / n).exists())).hexdigest() for b, d in D.items()}
    cfg = dict(task="maingeom", part="recheck", dirs={b: d.name for b, d in D.items()}, points_sha256=psha, code=code)
    out = ROOT / "results" / ("windport_maingeom_recheck_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = items(D)
    ck = lambda x: json.dumps({k: v for k, v in x[2].items() if k in ("kind", "scen", "mode", "S", "K", "lift", "hold", "lev", "par", "val", "arr", "geo", "x",
                                                                      "what", "site", "st", "lay", "reach", "disp", "first", "extra", "sub", "lv", "step", "cd")},
                              sort_keys=True)
    its.sort(key=lambda x: (x[0], ck(x)))
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "main geometry: recheck with unified W″_lift", "maingeom")
    res = []
    try:
        for rs in slot_imap(chunk, [its[k:k + 150] for k in range(0, len(its), 150)], a.procs, initializer=init, slots_dir=a.slots, tag="maingeom"):
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res.sort(key=lambda r: (r["batch"], str(r["key"])))
    with open(out / "rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(res)
    by = collections.defaultdict(list)
    for r in res:
        by[r["batch"]].append(r)
    summ = []
    for b, rs in sorted(by.items()):
        win = [r for r in rs if r["form"] in ("win", "e2")]
        prt = [r for r in rs if r["form"] == "port" and not r.get("skip")]
        summ.append(dict(batch=b, dir=D[b].name, rows=len(rs), win=len(win), port=len(prt), skipped=sum(r.get("skip", 0) for r in rs),
                         over=sum(r.get("over", 0) for r in rs), tie=sum(r["tie"] for r in win), tie_branch=sum(r["tie_branch"] for r in win),
                         tighter=sum(1 for r in win if r["new"] < r["branch"]), lstar_hi=sum(r["lstar_hi"] for r in prt),
                         signed=sum(r.get("signed", 0) for r in rs), signed_rows=sum(1 for r in rs if "signed" in r)))
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(summ[0]))
        w.writeheader()
        w.writerows(summ)
    strat = []
    for scope, ok in (("all window-form rows", lambda r: r["form"] == "win"), ("E2 proven optimal", lambda r: r["form"] == "e2" and r["cp_status"] == "OPTIMAL")):
        rs = [r for r in res if ok(r) and r["new"] > 0]
        for lab in sorted({r["lab"] for r in rs}) + ["road involved (incl. ties)", "total"]:
            a_ = [r for r in rs if (lab == "total") or (r["lab"] == lab) or (lab.startswith("road involved") and "road" in r["lab"])]
            strat.append(dict(scope=scope, lab=lab, n=len(a_), tie=sum(r["tie"] for r in a_)))
    with open(out / "strat.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(strat[0]))
        w.writeheader()
        w.writerows(strat)
    tot = lambda k: sum(x[k] for x in summ)
    L = ["# Recheck: unified W″_lift under the main geometry (conservative lifting rule, cradle mode including strings "
         "with signed dq), bound recomputed only", "",
         "| Batch | Run directory | Rows | Window form / port time | Simulation > W″_lift | Equality (window form) | "
         "Tighter by reach / reserved terms | L″* > port time | Tighter by strings with signed dq (rows with new strings) |",
         "|---|---|---:|---|---:|---|---:|---:|---|"]
    for x in summ:
        L.append(f"| {x['batch']} | `{x['dir']}` | {x['rows']:,} | {x['win']:,} / {x['port']:,}" + (f" (not fully loaded, not checked: {x['skipped']})" if x["skipped"] else "") +
                 f" | {x['over']} | {x['tie']:,} ({pct(x['tie'], x['win'])}) | {x['tighter']:,} | {x['lstar_hi']} | {x['signed']} ({x['signed_rows']}) |")
    L.append(f"| Total | | {tot('rows'):,} | {tot('win'):,} / {tot('port'):,} | {tot('over')} | {tot('tie'):,} ({pct(tot('tie'), tot('win'))}) | {tot('tighter'):,} | "
             f"{tot('lstar_hi')} | {tot('signed')} ({tot('signed_rows')}) |")
    L += ["", "## Tightness by class (denominator: classes under the unified W″_lift)", "", "| Scope | Class | Cases | = W″_lift |",
          "|---|---|---:|---|"]
    L += [f"| {x['scope']} | {x['lab']} | {x['n']:,} | {x['tie']:,} ({pct(x['tie'], x['n'])}) |" for x in strat]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=f"{tot('rows')} rows; > W″_lift {tot('over')}; L″* > port time {tot('lstar_hi')}")
    print(out)
    print("\n".join(L[:60]))


if __name__ == "__main__":
    main()
