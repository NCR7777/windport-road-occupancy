"""Random-archetype pile-by-pile regression of the unified bound under the main2 geometry (windport/main2.py), two
lifting rules per case (as in the work of experiments/windport_random_maingeom.py: W″ under the original rule, W″_lift
under the conservative rule with and without strings with signed dq, checker, pile-by-pile comparison with the original
function of each branch).
Generators as in the main geometry (a: generator of the spatial additions; dead: dead-end directed segments with
reserved periods and vessel-crane reach), with a separate seed range; every worker calls lift.install() and main2.use().
Side-by-side cradles (A1side) are always replaced by the rebuilt rows (main2.rows_cfg); in addition, seed
37,700,000 + i turns about 40% of the A1 cases (not passing-place cases, not shipyard maps) into rebuilt rows (number of
cradles max(S, original number of cradles, random 1-6)), to cover the new road network (rows on branch roads, one cradle
per row, with alternative turns and vessel-crane reach).
Output results/windport_main2_random_<config hash>/: config.json, progress.json, summary.json, bad.csv, cases.csv,
chunks/ (resume cache, deleted when done).
Run: python experiments/windport_random_main2.py --gen a --start 72000 --n 12000 --procs 8 --slots DIR
"""
import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402
import windport_random_maingeom as FR                           # noqa: E402

CODE = FR.CODE + ["windport/main2.py", "experiments/windport_random_maingeom.py", "experiments/windport_random_main2.py"]
ROWS_SHARE = 0.4
_make = FR.make


def make(gen, i):
    from windport import main2 as M2
    from windport import sim as WS
    c = _make(gen, i)
    g = c["geo"]
    R = random.Random(37_700_000 + i)
    if g["kind"] == "A1" and R.random() < ROWS_SHARE:
        n = max(int(c["S"]), int(g.get("n_cradles", 1)), R.randint(1, 6))
        g = dict({k: v for k, v in g.items() if k not in ("cradle_mode", "ramp_at", "n_cradles")}, kind="A1side", n_cradles=n)
        c = dict(c, geo=g)
    if c["geo"]["kind"] == "A1side":
        c = dict(c, geo=M2.rows_geo(c["geo"], WS.params(c)))
    return c


def work_chunk(ks):
    """FR.work; for rebuilt rows also records tree: the conservative-rule strings include some that rely on the extended premise
    "the quay side is a tree" (item 3 in windport/main2.py)."""
    from windport import bound_all as BA
    out = []
    for k in ks:
        r = FR.work(k)
        if r.get("kind") == "A1rows" and r["why"] != "error":
            r["tree"] = int(any(x.get("tree") for x in BA.parts(make(*k), lift=True)["chains"]))
        out.append(r)
    return out


def init():
    from windport import main2 as M2
    pin(list(range(1, os.cpu_count())))
    M2.use()
    FR.make = make


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", choices=["a", "dead"], required=True)
    ap.add_argument("--n", type=int, default=12000)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=10)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    from windport import main2 as M2
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="main2", part="random", gen=a.gen, start=a.start, n=a.n, first=FR.FIRST, rows_share=ROWS_SHARE, geometry=M2.MAIN2, code=code)
    out = ROOT / "results" / f"windport_main2_random_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    (out / "chunks").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    idx = [(a.gen, i) for i in range(a.start, a.start + a.n)]
    chunks = [idx[k:k + a.chunk] for k in range(0, len(idx), a.chunk)]
    cache = out / "chunks"
    done = {int(f.stem): json.loads(f.read_text(encoding="utf-8")) for f in cache.glob("*.json")}
    todo = [ch for ch in chunks if ch[0][1] not in done]
    res = [r for v in done.values() for r in v]
    prog = Progress(out / "progress.json", len(idx), len(res), a.procs, f"random regression ({a.gen}: main2, both rules)", "main2")
    try:
        for rs in slot_imap(work_chunk, todo, a.procs, initializer=init, slots_dir=a.slots, tag="main2"):
            (cache / f"{rs[0]['i']}.json").write_text(json.dumps(rs, ensure_ascii=False), encoding="utf-8")
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res.sort(key=lambda r: r["i"])
    ran = [r for r in res if r["why"] != "error"]
    with open(out / "cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FR.COLS + ["tree"], extrasaction="ignore")
        w.writeheader()
        w.writerows(ran)
    with open(out / "bad.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FR.COLS + ["err", "error"], extrasaction="ignore")
        w.writeheader()
        w.writerows(r for r in res if r["why"])
    rows = [r for r in ran if r["kind"] == "A1rows"]
    summ = dict(gen=a.gen, n=len(res), ran=len(ran), **{k: sum(k in r["why"].split("+") for r in res) for k in FR.FLAGS},
                lifts=sum(r["n"] for r in ran), lifts_lift=sum(r["n_lift"] for r in ran), viol=sum(r["viol"] for r in ran),
                viol_lift=sum(r["viol_lift"] for r in ran), tie=sum(r["tie"] for r in ran), tie_lift=sum(r["tie_lift"] for r in ran),
                cases_new_chains=sum(1 for r in ran if r["new_chains"]), cases_tight_signed=sum(1 for r in ran if r["tight_signed"]),
                tight_signed=sum(r["tight_signed"] for r in ran), by_lift={k: sum(r["lift"] == k for r in ran) for k in ("cradle", "direct", "mixed")},
                maps=sum(r["kind"] == "map" for r in ran), reach=sum(r["reach"] != "" for r in ran), reserve=sum(r["reserve"] != "" for r in ran),
                turn=sum(r["turn"] for r in ran), rows=len(rows), rows_lifts=sum(r["n"] + r["n_lift"] for r in rows),
                rows_by_S={str(s): sum(1 for r in rows if int(r["S"]) == s) for s in range(0, 7)}, rows_reach=sum(r["reach"] != "" for r in rows),
                rows_turn=sum(r["turn"] for r in rows), rows_tree=sum(r.get("tree", 0) for r in rows),
                rows_tree_viol=sum(r["viol"] + r["viol_lift"] for r in rows if r.get("tree")),
                rows_tree_lifts=sum(r["n"] + r["n_lift"] for r in rows if r.get("tree")), rows_hold=sum(r["hold"] != "0" for r in rows), pass_=sum(r["kind"] == "A1pass" for r in ran),
                far=sum(r["n_far"] for r in ran), vehicle_lifts=sum(r["n_clear"] for r in ran), under=sum(r["n_under"] for r in ran))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(summ, ensure_ascii=False)[:300])
    shutil.rmtree(cache)
    print(out)
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
