"""Exhaustive small-instance check of the serial-cut corollary (Corollary 3 of the window bound) on two-block chains: exact values
from windport/exact_chain.py next to the bounds:
  W1    W1 with either block as the cut (Theorems 1 and 2, Q = K; computed once per block, the smaller is taken);
  Π_S   the serial-cut preparation term of Corollary 3 (b_max = min(K, Qs), all returns pass through the chain);
  W1′   min(W1, Π_S).
Grid: K = 1–3, S = 0–2, quay-side places Qs = 1–3, pick-up hp = 1–2, two upstream blocks a1, a2 ∈ {1, 3}, two downstream blocks
e1 = e2 ∈ {1, 2}, set-down hd = 1–2, crane p = 1–2, preparation G = 0, 4, window L = 5, 9 (empty-system start; vehicle tail
occupying the block o = 1).
Output results/windport_chain_<config hash>/: config.json, progress.json, points/ (per instance, resume cache), points.csv,
summary.md.

Run: .venv/Scripts/python.exe experiments/windport_chain_check.py --procs 23 --slots DIR
"""
import argparse
import collections
import csv
import hashlib
import itertools
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap, write_json      # noqa: E402
from windport import bound as WB                                 # noqa: E402
from windport import bound2 as W2                                # noqa: E402
from windport import exact_chain as X                            # noqa: E402

CODE = ["windport/exact_chain.py", "windport/bound.py", "windport/bound2.py", "experiments/windport_chain_check.py"]
GRID = dict(K=[1, 2, 3], S=[0, 1, 2], Qs=[1, 2, 3], hp=[1, 2], a1=[1, 3], a2=[1, 3], e=[1, 2], hd=[1, 2], p=[1, 2], G=[0, 4], L=[5, 9], o=1)


def keys():
    g = GRID
    out = []
    for K, S, Qs, hp, a1, a2, e, hd, p, G, L in itertools.product(g["K"], g["S"], g["Qs"], g["hp"], g["a1"], g["a2"], g["e"], g["hd"], g["p"],
                                                                  g["G"], g["L"]):
        if Qs > K or (S == 0 and hd > 1):
            continue
        out.append(f"K{K}|S{S}|Q{Qs}|hp{hp}|a{a1}-{a2}|e{e}|hd{hd}|p{p}|G{G}|L{L}")
    return out


def parse(k):
    f = k.split("|")
    a1, a2 = map(int, f[4][1:].split("-"))
    return dict(K=int(f[0][1:]), S=int(f[1][1:]), Qs=int(f[2][1:]), hp=int(f[3][2:]), a1=a1, a2=a2, e=int(f[5][1:]), hd=int(f[6][2:]),
                p=int(f[7][1:]), G=int(f[8][1:]), L=int(f[9][1:]))


def bounds(x):
    """(W1 with either block as the cut, the smaller one, and its binding terms; Π_S)."""
    o = GRID["o"]
    K, S, hp, a1, a2, e, hd, p, G, L = (x[k] for k in ("K", "S", "hp", "a1", "a2", "e", "hd", "p", "G", "L"))
    hd_ = hd if S else 0
    c = hp + a1 + a2 + o + hd_ + 2 * e
    best = None
    for tl, te, dq in ((a1 + o, e, a2 + hd_), (a2 + o, e + o, hd_)):
        P = WB.Port(L=L, p=p, S=S, K=K, hp=hp, hd=hd_, tl=tl, te=te, c=c, ce=2 * e, dq=dq, Q=K, te_occ=te)
        b = WB.bound(P, G)
        if best is None or b[0] < best[0]:
            best = b
    ch = X.chain_params(a1, a2, e, e, hd, S, o)
    pi = W2.prep_chain(ch, K, min(K, x["Qs"]), G + L, p, hp)
    return best, pi


def run_chunk(ks):
    out = []
    for k in ks:
        x = parse(k)
        n = X.max_delivery(x["K"], x["S"], x["Qs"], x["hp"], x["a1"], x["a2"], x["e"], x["e"], x["hd"], x["p"], x["G"], x["L"], GRID["o"])
        (w1, why), pi = bounds(x)
        r = dict(key=k, **x, exact=n, w1=w1, binding="+".join(why), serial=pi, w1s=min(w1, pi))
        write_json(OUT / "points" / (k.replace("|", "_") + ".json"), r)
        out.append(r)
    return out


OUT = None


def init(out):
    global OUT
    OUT = Path(out)
    pin(list(range(1, os.cpu_count())))


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=23)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="runs", part="chain", grid=GRID, code=code)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    OUT = ROOT / "results" / f"windport_chain_{h}"
    (OUT / "points").mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    ks = keys()
    todo = [k for k in ks if not (OUT / "points" / (k.replace("|", "_") + ".json")).exists()]
    prog = Progress(OUT / "progress.json", len(ks), len(ks) - len(todo), a.procs, "Serial cut: two-block chain exhaustive check", "runs")
    big = [k for k in todo if parse(k)["K"] == 3]
    todo = big + [k for k in todo if k not in set(big)]          # large instances first
    chunks = [todo[i:i + 4] for i in range(0, len(todo), 4)]
    for rs in slot_imap(run_chunk, chunks, a.procs, initializer=init, initargs=(str(OUT),), slots_dir=a.slots, tag="runs"):
        prog.write(done=prog.d["done"] + len(rs))
    rows = [json.loads((OUT / "points" / (k.replace("|", "_") + ".json")).read_text(encoding="utf-8")) for k in ks]
    cols = list(rows[0])
    with open(OUT / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    n = len(rows)
    over_w1 = sum(r["exact"] > r["w1"] for r in rows)
    over = sum(r["exact"] > r["w1s"] for r in rows)
    tight = [r for r in rows if r["w1s"] < r["w1"]]
    gap = collections.Counter(min(r["w1s"] - r["exact"], 3) for r in rows)
    gap0 = collections.Counter(min(r["w1"] - r["exact"], 3) for r in rows)
    L = ["# Serial-cut corollary (Corollary 3): two-block chain exhaustive check (windport_chain_check.py)\n",
         f"- Instances {n}; exact value above W1 (single block as cut): {over_w1}; above W1′ = min(W1, Π_S): {over}.",
         f"- Instances where Π_S is tighter than W1: {len(tight)} ({len(tight) / n:.1%}), total tightening {sum(r['w1'] - r['w1s'] for r in tight)} piles; "
         f"of these, tightened bound = exact value in {sum(r['w1s'] == r['exact'] for r in tight)}.",
         f"- Equality: W1 {gap0[0]} ({gap0[0] / n:.1%}) → W1′ {gap[0]} ({gap[0] / n:.1%}).",
         "- Gap distribution (0 / 1 / 2 / ≥3 piles): W1 " + " / ".join(str(gap0[i]) for i in range(4)) + "; W1′ " + " / ".join(str(gap[i]) for i in range(4)) + ".",
         "", "| Qs | instances | Π_S tighter | piles tightened | W1′ equality |", "|---:|---:|---:|---:|---:|"]
    for q in GRID["Qs"]:
        rs = [r for r in rows if r["Qs"] == q]
        L.append(f"| {q} | {len(rs)} | {sum(r['w1s'] < r['w1'] for r in rs)} | {sum(r['w1'] - r['w1s'] for r in rs)} | "
                 f"{sum(r['w1s'] == r['exact'] for r in rs)} |")
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=f"above W1′: {over} instances; Π_S tighter: {len(tight)} instances")
    print(OUT)
    print("\n".join(L))


if __name__ == "__main__":
    main()
