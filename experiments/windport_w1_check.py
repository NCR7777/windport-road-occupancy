"""Exhaustive check of W1 on a grid of small instances.

Single-lane instances (cut + loading/unloading), K = 1–3, S = 0–3, quay-zone capacity Q ∈ {1, 2, K}, pick-up / cut crossing /
set-down / return (through the cut or via a loop) of 1–3 units each, crane period p = 1–3, window L = 3, 5, 8, 12; three starts:
arbitrary history (the window start ranges over all compatible states), and empty-system start with preparation G = 0, 4 before
the window. Also periodic windows (empty start, n = 2, 3 windows, gap 3) and two supplementary families: mixed lifting (in cradle
mode the crane can also lift from the vehicle, Corollary 2) and a two-lane cut (qe = 2, two empty vehicles at once). Exact values
from windport.exact.max_delivery (exhaustive search), bounds from windport.bound.
Output results/windport_w1_<config hash>/: config.json, points.csv, periodic.csv, extra.csv, summary.md, progress.json. Single
process, about 4 min. The config hash covers the grid and the SHA-256 of windport/bound.py and windport/exact.py.

Run: .venv/Scripts/python.exe experiments/windport_w1_check.py
"""
import collections
import csv
import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from windport.bound import bound, lane, periodic, rate, terms     # noqa: E402
from windport.exact import max_delivery                    # noqa: E402

GRID = dict(K=[1, 2, 3], S=[0, 1, 2, 3], hp=[1, 2], tl=[1, 3], hd=[1, 2], ret=[[1, 0], [2, 0], [0, 2]], p=[1, 2, 3],
            L=[3, 5, 8, 12], start=[["any", None], ["empty", 0], ["empty", 4]])
PERIODIC = dict(K=[1, 2], S=[0, 1, 2], hp=[1], tl=[1, 2], hd=[1], ret=[[1, 0], [0, 2]], p=[1, 2], L=[3, 5], G=[0, 4], gap=3, n=[2, 3])
EXTRA = dict(K=[1, 2, 3], S=[1, 2], hp=[1, 2], tl=[1, 2], hd=[1, 3], ret=[[1, 0], [2, 0], [0, 2]], p=[1, 2], L=[5, 8, 11],
             start=[["any", None], ["empty", 3]], family=[["mixed", 1], ["qe2", 2]])
TERMS = ("interface", "turnover", "fleet", "cut", "zone", "prep")


def code_sha():
    """Code that computes the results (bound and exhaustive search); the grid is in the config. Progress and summary writers are
    not hashed."""
    h = hashlib.sha256()
    for f in ("windport/bound.py", "windport/exact.py"):
        h.update(f.encode() + (ROOT / f).read_bytes())
    return h.hexdigest()


def write_progress(out, **kw):
    """progress.json in the dashboard format: replace the whole file."""
    (out / "progress.json").write_text(json.dumps(dict(task="w1", title="W1 small-instance exhaustive check", reused=0, failed=0, processes=1, **kw),
                                                  ensure_ascii=False, indent=1), encoding="utf-8")


def cases(g):
    for K, S, hp, tl, hd, (te, er), p, L, (start, G) in itertools.product(*(g[k] for k in ("K", "S", "hp", "tl", "hd", "ret", "p", "L", "start"))):
        if S == 0 and hd != g["hd"][0]:
            continue                                 # direct lift: no set-down
        for Q in sorted({1, min(2, K), K}):
            yield dict(K=K, S=S, Q=Q, hp=hp, tl=tl, hd=hd if S else 0, te=te, er=er, p=p, L=L, start=start, G=G)


def main():
    cfg = dict(task="w1", title="W1 small-instance exhaustive check", grid=GRID, grid_q=[1, 2, "K"], periodic=PERIODIC, extra=EXTRA,
               semantics="release-before-acquire", code_sha256=code_sha())
    out = ROOT / "results" / ("windport_w1_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    todo = list(cases(GRID))
    t0 = time.time()
    total = len(todo) + 2                     # single-window instances + one batch of periodic windows + one batch of supplements
    note = f"single window {len(todo)} instances; periodic windows and supplements one batch each (single process)"

    def progress(done, state="running"):
        write_progress(out, total=total, done=done, started=t0, updated=time.time(), state=state, note=note)
    try:
        run(out, todo, progress)
    except BaseException:
        progress(0, "failed")
        raise
    progress(total, "done")
    print(out)


def run(out, todo, progress):
    rows = []
    for i, c in enumerate(todo):
        P = lane(c["L"], c["p"], c["S"], c["K"], c["hp"], c["hd"], c["tl"], c["te"], c["er"], c["Q"])
        G = c["G"] if c["start"] == "empty" else None
        x = max_delivery(c["L"], c["p"], c["S"], c["K"], c["hp"], c["hd"], c["tl"], c["te"], c["er"], Q=c["Q"],
                         G=c["G"] or 0, start=c["start"])
        b, why = bound(P, G)
        t = terms(P, G)
        plan = min(c["L"] / c["p"], c["S"] + c["L"] * rate(P))     # simple candidate formula (without boundary terms)
        rows.append(dict(c, G="" if G is None else G, exact=x, bound=b, gap=b - x, binding="+".join(why), plan=round(plan, 4),
                         **{k: ("" if k not in t else ("inf" if t[k] == float("inf") else t[k])) for k in TERMS}))
        if i % 500 == 0:
            progress(i)
    cols = list(rows[0])
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    prow = []
    for K, S, hp, tl, hd, (te, er), p, L, G, n in itertools.product(*(PERIODIC[k] for k in ("K", "S", "hp", "tl", "hd", "ret", "p", "L", "G", "n"))):
        T = L + PERIODIC["gap"]
        P = lane(L, p, S, K, hp, hd, tl, te, er)
        x = max_delivery(L, p, S, K, hp, hd, tl, te, er, G=G, T=T, n=n)
        prow.append(dict(K=K, S=S, hp=hp, tl=tl, hd=hd if S else 0, te=te, er=er, p=p, L=L, G=G, T=T, n=n, exact=x,
                         bound=periodic(P, G, T, n), single=bound(P)[0]))
    with open(out / "periodic.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(prow[0]))
        w.writeheader()
        w.writerows(prow)
    erow = []
    keys = ("K", "S", "hp", "tl", "hd", "ret", "p", "L", "start", "family")
    for K, S, hp, tl, hd, (te, er), p, L, (start, G), (fam, qe) in itertools.product(*(EXTRA[k] for k in keys)):
        if fam == "qe2" and te == 0:
            continue
        mixed = fam == "mixed"
        for Q in sorted({1, K}):
            x = max_delivery(L, p, S, K, hp, hd, tl, te, er, Q=Q, G=G or 0, start=start, qe=qe, mixed=mixed)
            b, why = bound(lane(L, p, S, K, hp, hd, tl, te, er, Q, qe=qe, mixed=mixed), G)
            plain = bound(lane(L, p, S, K, hp, hd, tl, te, er, Q))[0] if mixed and G is None else ""
            erow.append(dict(family=fam, K=K, S=S, Q=Q, hp=hp, tl=tl, hd=hd, te=te, er=er, p=p, L=L, start=start,
                             G="" if G is None else G, exact=x, bound=b, gap=b - x, binding="+".join(why), cradle_only_W1=plain))
    with open(out / "extra.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(erow[0]))
        w.writeheader()
        w.writerows(erow)
    (out / "summary.md").write_text(summary(rows, prow, erow), encoding="utf-8")


def stat(rs):
    g = collections.Counter(r["gap"] for r in rs)
    return (f"{len(rs)} instances, bound exceeded in {sum(r['exact'] > r['bound'] for r in rs)}, equality in {g[0]} ({g[0] / max(1, len(rs)):.1%}), "
            "gap distribution " + ", ".join(f"{k}: {v}" for k, v in sorted(g.items())))


def summary(rows, prow, erow):
    pbad = [r for r in prow if r["exact"] > r["bound"]]
    old = [r for r in rows if r["Q"] in (1, r["K"])]
    L = [f"# W1 small-instance exhaustive check (release before acquire at the same instant)\n",
         f"- Single window: {stat(rows)} (of which with exact value > 0 and equality: {sum(r['gap'] == 0 and r['exact'] > 0 for r in rows)}).",
         f"  - Q ∈ {{1, K}} (original grid): {stat(old)}.",
         f"  - 1 < Q < K (added grid points): {stat([r for r in rows if 1 < r['Q'] < r['K']])}.",
         f"- Periodic windows: {len(prow)} instances, bound exceeded in {len(pbad)}; equality in {sum(r['exact'] == r['bound'] for r in prow)}.",
         f"- Mixed lifting (Corollary 2): {stat([r for r in erow if r['family'] == 'mixed'])}; the W1 computed for cradle mode only is exceeded in "
         f"{sum(r['exact'] > r['cradle_only_W1'] for r in erow if r['family'] == 'mixed' and r['cradle_only_W1'] != '')} instances"
         f" (out of {sum(1 for r in erow if r['family'] == 'mixed' and r['cradle_only_W1'] != '')} arbitrary-history instances).",
         f"- Two-lane cut (qe = 2): {stat([r for r in erow if r['family'] == 'qe2'])}.\n"]
    over = [r for r in rows if r["exact"] > r["plan"] + 1e-9]
    L.append(f"The simple candidate formula min{{L/p, S + L·r}} (without boundary terms) is exceeded by the exact value in {len(over)} instances"
             f" (arbitrary history {sum(r['start'] == 'any' for r in over)}; largest excess {max((r['exact'] - r['plan'] for r in over), default=0):.2f} piles). "
             "First 5:\n\n| K | S | Q | hp | tl | hd | te | er | p | L | start | G | exact | candidate | W1 |\n|" + "---|" * 15)
    for r in sorted(over, key=lambda r: r["plan"] - r["exact"])[:5]:
        L.append("| " + " | ".join(str(r[k]) for k in ("K", "S", "Q", "hp", "tl", "hd", "te", "er", "p", "L", "start", "G", "exact", "plan", "bound")) + " |")
    L.append("")
    L.append("| start | binding term | instances | equality | share with equality |\n|---|---|---:|---:|---:|")
    by = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["exact"] == 0 and r["bound"] == 0:
            continue
        for k in r["binding"].split("+"):
            key = (r["start"] if r["start"] == "any" else f"empty G={r['G']}", k)
            by[key][0] += 1
            by[key][1] += r["gap"] == 0
    for (s, k), (n, e) in sorted(by.items()):
        L.append(f"| {s} | {k} | {n} | {e} | {e / n:.0%} |")
    L.append("\nInstances with bound = 0 are not counted in the table above (window shorter than one lift or too short for the first hand-over).\n")
    L.append("Instances with gap ≥ 2 (first 15):\n\n| K | S | Q | hp | tl | hd | te | er | p | L | start | G | exact | bound | binding |\n|" + "---|" * 15)
    for r in [r for r in rows if r["gap"] >= 2][:15]:
        L.append("| " + " | ".join(str(r[k]) for k in ("K", "S", "Q", "hp", "tl", "hd", "te", "er", "p", "L", "start", "G", "exact", "bound", "binding")) + " |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
