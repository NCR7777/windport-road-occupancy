"""Rechecks every simulation row recomputed under main2 against the unified bound W″_lift (bound_all.w2_lift, cradle
mode including strings with signed dq); only the bound is recomputed.
Rows: splice of experiments/windport_main2_runs.py (the recomputed keys in each batch, as listed in diff.csv), core,
reachdist, cdv (the configurations computed now); per-row rules as in experiments/windport_recheck_maingeom.one (window
form: simulation > bound, equality, binding term and the five regimes; port time: W″_lift(port time) < n_v,
L″* > port time; for the cradle mode also whether strings with signed dq make it tighter). Configs are built as in each
batch; side-by-side cradles are replaced by the rebuilt rows via main2.rows_cfg.
Also: a sample of the reused rows (keys of windport_main2_runs.py --part sample) has its bound recomputed under main2 and
compared value by value with rows.csv of the main-geometry recheck (column same).
Not checked, as in the main-geometry recheck: rows in the fixed-duration representation and with "the cut as a single
resource", unloading rows of pub, port-time rows that are not fully loaded.
Output results/windport_main2_recheck_<config hash>/: config.json, progress.json, rows.csv, summary.csv, strat.csv,
summary.md, sample.csv.
Run: python experiments/windport_recheck_main2.py --procs 20 --slots DIR
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
import windport_recheck_maingeom as FK                          # noqa: E402
import windport_main2_runs as HX                                  # noqa: E402

H = 3600.0
CODE = FK.CODE + ["windport/main2.py", "experiments/windport_recheck_maingeom.py", "experiments/windport_main2_runs.py", "experiments/windport_recheck_main2.py"]
_ER_CFG = ER.cfg_of


def one_dir(pre):
    return FK.one_dir(pre)


def dirs():
    """Run directories of the main2 geometry."""
    return dict(splice=one_dir("windport_main2_splice_"), core=one_dir("windport_main2_core_"), reachdist=one_dir("windport_main2_reachdist_"),
                cdv=one_dir("windport_main2_cdv_"), sample=one_dir("windport_main2_sample_"))


def cfg_of(batch, row):
    from windport import main2 as M2
    if batch == "main2:core":
        return HX.core_cfg(T.dec(row["key"])), "port"
    if batch == "main2:reachdist":
        batch = "unified:reach"
    c, form = _ER_CFG(batch, row)
    return M2.rows_cfg(c), form


def items(D):
    out = []
    for b in HX.RERUN + [f"unified:{p}" for p in HX.SPATIAL]:
        d = D["splice"] / b.replace(":", "_")
        keys = {r["key"] for r in FK.load(d, "diff.csv")}
        for r in FK.load(d):
            if r["key"] not in keys:
                continue
            if b == "extra:pub" and r["pub"] != "out":
                continue
            out.append((b, "lift", r))
    out += [("main2:core", "lift", dict(r, key=T.enc({k: r[k] for k in ("scen", "lay", "arr", "K", "hold", "rule")}))) for r in FK.load(D["core"])]
    out += [("main2:reachdist", "lift", r) for r in FK.load(D["reachdist"])]
    new, _ = HX.cdv_todo(json.loads(HX.chosen_file().read_text(encoding="utf-8")))
    new = set(new)
    out += [("unified:cdv", "lift", r) for r in FK.load(D["cdv"]) if r["key"] in new]
    return out


def sample_items():
    """Sample of the reused rows: rows of the main-geometry directories for the keys of windport_main2_runs.py sample
    (batches handled as in the main-geometry recheck)."""
    FD = FK.dirs()
    out = []
    for k in HX.sample_keys():
        b, kk = json.loads(k)
        for r in FK.load(FD[b]):
            if r["key"] == kk or r["key"].startswith(kk + "|lat="):
                if b == "extra:fix" or r.get("rep") in ("fix", "cut") or r.get("key", "").startswith("fix|") or (b == "extra:pub" and r["pub"] != "out") \
                        or (b.startswith("unified:") and r.get("step") in ("s3", "cf")):
                    continue
                out.append((b, "lift", r))
    return out


def one(arg):
    """arg = (batch, rule, row, sampled); the result also records smp."""
    return dict(FK.one(arg[:3]), smp=arg[3])


def chunk(its):
    return [one(x) for x in its]


def init():
    pin(list(range(1, os.cpu_count())))
    HX.install()
    ER.cfg_of = cfg_of
    FK.cfg_of = cfg_of


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=20)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    init()
    D = dirs()
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    psha = {b: hashlib.sha256(b"".join(sorted(p.read_bytes() for p in d.rglob("*.csv")))).hexdigest() for b, d in D.items()}
    cfg = dict(task="main2", part="recheck", dirs={b: d.name for b, d in D.items()}, points_sha256=psha, code=code)
    out = ROOT / "results" / ("windport_main2_recheck_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = items(D)
    smp = sample_items()
    allits = [x + (0,) for x in its] + [x + (1,) for x in smp]
    prog = Progress(out / "progress.json", len(allits), 0, a.procs, "main2: recheck with unified W″_lift", "main2")
    res = []
    try:
        for rs in slot_imap(chunk, [allits[k:k + 100] for k in range(0, len(allits), 100)], a.procs, initializer=init, slots_dir=a.slots, tag="main2"):
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res, sres = [r for r in res if not r["smp"]], [r for r in res if r["smp"]]
    res.sort(key=lambda r: (r["batch"], str(r["key"])))
    COLS = FK.COLS
    with open(out / "rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(res)
    # sample of the reused rows: value-by-value comparison with the main-geometry recheck
    fr = {(r["batch"], r["key"]): r for r in FK.load(FK.one_dir("windport_maingeom_recheck_"), "rows.csv")}
    cmp_ = ("new", "lstar", "over", "tie", "lstar_hi", "cls", "keys")
    srow = []
    for r in sres:
        o = fr.get((r["batch"], str(r["key"])))
        same = o is not None and all(str(r.get(k, "")) == str(o.get(k, "")) for k in cmp_ if k in o and (k in r or o.get(k, "") == ""))
        srow.append(dict(batch=r["batch"], key=r["key"], form=r["form"], found=int(o is not None), same=int(same)))
    with open(out / "sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["batch", "key", "form", "found", "same"])
        w.writeheader()
        w.writerows(srow)
    by = collections.defaultdict(list)
    for r in res:
        by[r["batch"]].append(r)
    summ = []
    for b, rs in sorted(by.items()):
        win = [r for r in rs if r["form"] in ("win", "e2")]
        prt = [r for r in rs if r["form"] == "port" and not r.get("skip")]
        summ.append(dict(batch=b, rows=len(rs), win=len(win), port=len(prt), skipped=sum(r.get("skip", 0) for r in rs), over=sum(r.get("over", 0) for r in rs),
                         tie=sum(r["tie"] for r in win), tighter=sum(1 for r in win if r["new"] < r["branch"]), lstar_hi=sum(r["lstar_hi"] for r in prt),
                         signed=sum(r.get("signed", 0) for r in rs), signed_rows=sum(1 for r in rs if "signed" in r)))
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(summ[0]))
        w.writeheader()
        w.writerows(summ)
    pct = FK.pct
    tot = lambda k: sum(x[k] for x in summ)
    L = ["# Recheck: unified W″_lift under main2 (conservative lifting rule, cradle mode including strings with signed dq), "
         "bound recomputed only (recomputed rows)", "",
         "| Batch | Rows | Window form / port time | Simulation > W″_lift | Equality (window form) | "
         "Tighter by reach / reserved terms | L″* > port time | Tighter by strings with signed dq (rows with new strings) |",
         "|---|---:|---|---:|---|---:|---:|---|"]
    for x in summ:
        L.append(f"| {x['batch']} | {x['rows']:,} | {x['win']:,} / {x['port']:,}" + (f" (not fully loaded, not checked: {x['skipped']})" if x["skipped"] else "") +
                 f" | {x['over']} | {x['tie']:,} ({pct(x['tie'], x['win'])}) | {x['tighter']:,} | {x['lstar_hi']} | {x['signed']} ({x['signed_rows']}) |")
    L.append(f"| Total | {tot('rows'):,} | {tot('win'):,} / {tot('port'):,} | {tot('over')} | {tot('tie'):,} ({pct(tot('tie'), tot('win'))}) | {tot('tighter'):,} | "
             f"{tot('lstar_hi')} | {tot('signed')} ({tot('signed_rows')}) |")
    L += ["", f"Sample of reused rows ({len(srow)} rows of the main-geometry directories, bound recomputed under main2 and "
          f"compared value by value with rows.csv of the main-geometry recheck): found {sum(x['found'] for x in srow)}, "
          f"same {sum(x['same'] for x in srow)}."]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=f"{tot('rows')} rows; > W″_lift {tot('over')}; L″* > port {tot('lstar_hi')}; sample same {sum(x['same'] for x in srow)}/{len(srow)}")
    print(out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
