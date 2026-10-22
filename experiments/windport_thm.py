"""Exhaustive small-instance check of Theorem 3 (unloading) and Theorem 4 (unloading and loading sharing one cut) of the window
bound W1 (exhaustive search windport/exact_u.py; bounds windport/bound.py).

1. Consistency: with loading only and returns through the cut, exact_u equals windport.exact (the W1 exhaustive search) on every
   instance.
2. Theorem 3: unloading only, K = 1–3, supports behind the ramp S_u = 0–2, ramp operation ρ, cut crossing towards the yard tl,
   return te, set-down hy, support handling hs, each within 1–3 units, window L = 3, 5, 8, quay zone Q = 1–3; three starts:
   arbitrary history (the window start ranges over all compatible states), all vehicles empty on the quay side, all vehicles empty
   on the yard side.
   Bound min{⌊L/ρ⌋, K·(⌊(L − ρ)/c_u⌋ + 1), S_u + q + M_u(L − ρ)}, c_u = ρ + min(hs, tl + hy + te) (with supports).
3. Theorem 4: simultaneous unloading and loading (crane window [0, L_o], ramp window [d, d + L_u]); for every pair (N_o, N_u) in
   the Pareto set of each instance check N_o ≤ W1, N_u ≤ Theorem 3 and the joint polyhedron (windport.bound.joint_gap ≥ 0), and
   record the slack of the joint inequality.
Output results/windport_thm_<config hash>/: config.json, progress.json, consistency.csv, thm3.csv, thm4.csv, summary.md (single
process, about 1 min).

Run: .venv/Scripts/python.exe experiments/windport_thm.py
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

from windport import bound as B                    # noqa: E402
from windport.exact import max_delivery            # noqa: E402
from windport.exact_u import frontier              # noqa: E402

CONS = dict(K=[1, 2], S=[0, 1, 2], hp=[1, 2], tl=[1, 2], te=[1, 2], p=[1, 2], L=[4, 7], Q=[1, 2], start=["any", "empty"])
THM3 = dict(K=[1, 2, 3], Su=[0, 1, 2], rho=[1, 2, 3], tl=[1, 2], te=[1, 2], hy=[1, 2], hs=[1, 2], L=[3, 5, 8], Q=[1, 2, 3],
            start=["any", "quay", "empty"])
THM4 = dict(K=[1, 2], S=[0, 1], Q=[1, 2], tl_o=[1, 2], tl_u=[1, 2], te=[1], rho=[1, 2], p=[1, 2], Lo=[4, 7], d=[0, 2], Lu=[3, 6],
            start=["any", "empty", "quay"])
THM4B = dict(K=[2, 3], S=[0, 1], Q=[2, 3], tl_o=[3], tl_u=[3], te=[1, 2], rho=[1], p=[1], Lo=[10, 13], d=[0, 3], Lu=[10, 13],
             start=["empty", "quay"])
FILES = ("windport/bound.py", "windport/exact.py", "windport/exact_u.py", "experiments/windport_thm.py")


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def progress(out, t0, done, total, state, note=""):
    (out / "progress.json").write_text(json.dumps(dict(task="e1e3", title="Theorems 3 and 4: small-instance exhaustive check", total=total, done=done, reused=0, failed=0,
                                                       processes=1, started=t0, updated=time.time(), state=state, note=note),
                                                  ensure_ascii=False, indent=1), encoding="utf-8")


def thm4_rows(grid, tag):
    rows = []
    for K, S, Q, tl_o, tl_u, te, rho, p, Lo, d, Lu, start in itertools.product(*grid.values()):
        if Q > K or (start == "quay" and Q < K) or tl_o < te or tl_u < te:
            continue
        f = frontier(K, S, p, 1, 1, tl_o, te, [(0, Lo)], rho=rho, tl_u=tl_u, te_q=te, hy=1, ramp=[(d, d + Lu)], Q=Q, start=start)
        w1 = B.bound(B.lane(Lo, p, S, K, 1, 1, tl_o, te, Q=Q), 0 if start == "empty" else None)[0]
        u3 = min(B.unload_terms(Lu, rho, K, rho + tl_u + 1 + te, tl_u, te, 0, Q).values())
        q, dq = min(K, Q), (1 if S else 0)
        for No, Nu in f:
            g = B.joint_gap(No, Nu, S, 0, q, K, tl_o, tl_u, te, te, (0, Lo - p - dq), (d + rho, d + Lu))
            rows.append(dict(grid=tag, K=K, S=S, Q=Q, tl_o=tl_o, tl_u=tl_u, te=te, rho=rho, p=p, Lo=Lo, d=d, Lu=Lu, start=start, No=No, Nu=Nu,
                             w1=w1, thm3=u3, joint_slack="" if g == float("inf") else g, active=int(g != float("inf"))))
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}
    cfg = dict(task="e1e3", title="Theorems 3 and 4: small-instance exhaustive check", consistency=CONS, thm3=THM3, thm4=THM4, thm4b=THM4B, code=code)
    out = ROOT / "results" / ("windport_thm_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    t0 = time.time()
    progress(out, t0, 0, 4, "running")
    crow = []
    for K, S, hp, tl, te, p, L, Q, start in itertools.product(*CONS.values()):
        if Q > K:
            continue
        a = max_delivery(L, p, S, K, hp, 1, tl, te, 0, Q=Q, G=0, start=start)
        b = max(o for o, _ in frontier(K, S, p, hp, 1, tl, te, [(0, L)], Q=Q, unload=False, start=start))
        crow.append(dict(K=K, S=S, hp=hp, tl=tl, te=te, p=p, L=L, Q=Q, start=start, exact=a, exact_u=b, same=int(a == b)))
    write(out / "consistency.csv", crow)
    progress(out, t0, 1, 4, "running")
    trow = []
    for K, Su, rho, tl, te, hy, hs, L, Q, start in itertools.product(*THM3.values()):
        if Q > K or (K == 3 and (Su == 2 or start == "any")) or (start == "quay" and Q < K):
            continue
        x = max(u for _, u in frontier(K, 0, 1, 1, 1, 1, te, [], Su=Su, hs=hs, rho=rho, tl_u=tl, te_q=te, hy=hy, ramp=[(0, L)], Q=Q,
                                       load=False, start=start))
        t = B.unload_terms(L, rho, K, rho + min(hs if Su else 10 ** 9, tl + hy + te), tl, te, Su, Q)
        ub = min(t.values())
        trow.append(dict(K=K, Su=Su, rho=rho, tl=tl, te=te, hy=hy, hs=hs, L=L, Q=Q, start=start, exact=x, bound=ub, gap=ub - x,
                         binding="+".join(k for k, v in t.items() if v == ub), **t))
    write(out / "thm3.csv", trow)
    progress(out, t0, 2, 4, "running")
    frow = thm4_rows(THM4, "main") + thm4_rows(THM4B, "cut")
    write(out / "thm4.csv", frow)
    progress(out, t0, 3, 4, "running")
    g3 = collections.Counter(r["gap"] for r in trow)
    by3 = collections.defaultdict(lambda: [0, 0])
    for r in trow:
        for k in r["binding"].split("+"):
            by3[k][0] += 1
            by3[k][1] += r["gap"] == 0
    act = [r for r in frow if r["active"]]
    sl = collections.Counter(r["joint_slack"] for r in act)
    L = ["# Theorems 3 and 4: small-instance exhaustive check\n",
         f"- Consistency (loading only): {len(crow)} instances, exact_u differs from windport.exact in {sum(1 - r['same'] for r in crow)}.",
         f"- Theorem 3: {len(trow)} instances, bound exceeded in {sum(r['gap'] < 0 for r in trow)}, equality in {g3[0]} ({g3[0] / len(trow):.1%}), gap distribution "
         + ", ".join(f"{k}: {v}" for k, v in sorted(g3.items())) + ".",
         "  - Binding terms (binding with equality / binding): " + "; ".join(f"{k} {e}/{n}" for k, (n, e) in sorted(by3.items())) + ".",
         f"- Theorem 4: {len(set((r['grid'],) + tuple(r[k] for k in THM4) for r in frow))} instances, {len(frow)} Pareto points; N_o above W1: "
         f"{sum(r['No'] > r['w1'] for r in frow)}, N_u above Theorem 3: {sum(r['Nu'] > r['thm3'] for r in frow)}, joint inequality violated: "
         f"{sum(1 for r in act if r['joint_slack'] < 0)}; slack distribution on the {len(act)} points where the joint inequality is active (both flows cross the cut): "
         + ", ".join(f"{k}: {v}" for k, v in sorted(sl.items())) + ".\n"]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    progress(out, t0, 4, 4, "done", f"consistency {len(crow)}, Theorem 3 {len(trow)}, Theorem 4 {len(frow)} points")
    print(out)


if __name__ == "__main__":
    main()
