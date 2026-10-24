"""Small-instance enumeration check of W″ (Corollaries 6 and 7) under the conservative lifting rule: two-block chain
(windport/exact_chain_lift.py: a lift from the vehicle only starts after the vehicle tail has left the chain head block).
Grid as the tail grid of the dead-end coupling (TAIL in experiments/windport_deadend_ext.py, 12,000 instances): direct lift S = 0,
mixed lifting S = 1-2 × K = 1-3 × Qs = 1-2 × vehicle tail o = 1, 2 × hp, a1, a2, hd, p, G × window L = 8, 12, 16,
× closure time under the load tu = 0, 1, 2 (tu = 0 gives the original 12,000 instances).
Exact values are compared with lift_bound (W″ under the new rule: handover ≥ arrival at the quay side followed by the tail leaving,
dq = 0 on the chain; a direct-lift vehicle leaves no earlier than lift start + tu).
Output results/windport_conservative_exact_<config hash>/: config.json, progress.json, points.csv, summary.md.
Run: python experiments/windport_exact_conservative.py --procs 8 --chunk 4 --slots DIR
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

from batch import Progress, pin, slot_imap                   # noqa: E402

CODE = ["windport/bound.py", "windport/bound2.py", "windport/bound3.py", "windport/bound_dead.py", "windport/exact_chain.py",
        "windport/exact_chain_lift.py", "experiments/windport_deadend_ext.py", "experiments/windport_exact_conservative.py"]
TUS = [0, 1, 2]


def lift_bound(x):
    """W″ on the two-block chain under the conservative lifting rule: handover (set-down done or lift start) ≥ arrival at QL
    (a1 + a2 + o after entering the chain, with the tail already clear of block 2).
    Fleet: consecutive handovers ≥ hp + a1 + a2 + o + 2e (plus hd before the mixed-lifting conversion), first ≥ hp + a1 + a2 + o; cut:
    block 1 tl = a1 + o, dq = a2; block 2 tl = a2 + o, dq = 0; return te = e, e + o; chain: dq = 0, c_z = σ = a1 + a2 + o + 2e,
    f₁ = hp + a1 + a2 + o; Q = min(K, Qs). Returns (bound, binding terms)."""
    from windport import bound as WB
    from windport import bound2 as W2
    from windport import bound_dead as BD
    from windport import exact_chain as XC
    K, S, Qs, hp, a1, a2, e, o, hd, p, G, L = (x[k] for k in ("K", "S", "Qs", "hp", "a1", "a2", "e", "o", "hd", "p", "G", "L"))
    tu = x.get("tu", 0)
    mixed = S > 0
    q = min(K, Qs)
    c, ce = (hp + a1 + a2 + o + 2 * e + hd, 2 * e) if mixed else (hp + a1 + a2 + o + 2 * e + tu, 2 * e + tu)
    ch = dict(XC.chain_params(a1, a2, e, e, hd, S, o), dq=0)
    pl, pe = W2.span(1, ch["up"]), W2.span(1, ch["down"])
    zc = [(pl + pe, hp + pl, pl + pe)] if q == 1 else []
    best = None
    for tl, te, dq in ((a1 + o, e, a2), (a2 + o, e + o, 0)):
        P = WB.Port(L=L, p=p, S=S, K=K, hp=hp, hd=hd if S else 0, tl=tl, te=te, c=c, ce=ce, dq=dq, Q=q, mixed=mixed, te_occ=te)
        v, keys, _, _ = BD.binding(BD.terms4(dict(P=P, G=G, zc=zc, chains=[ch], bm=[q], hp=hp), L))
        best = (v, "+".join(keys)) if best is None or v < best[0] else best
    return best


def one(x):
    from windport import exact_chain_lift as XL
    n = XL.max_delivery(x["K"], x["S"], x["Qs"], x["hp"], x["a1"], x["a2"], x["e"], x["e"], x["hd"], x["p"], x["G"], x["L"], x["o"], mixed=x["S"] > 0, tu=x["tu"])
    v, why = lift_bound(x)
    return dict(x, key="|".join(f"{k}{x[k]}" for k in x), exact=n, bound=v, binding=why, over=int(n > v), tie=int(n == v))


def chunk(items):
    return [one(x) for x in items]


def init():
    pin(list(range(1, os.cpu_count())))


COLS = ["key", "K", "S", "Qs", "hp", "a1", "a2", "e", "o", "hd", "p", "G", "L", "tu", "exact", "bound", "binding", "over", "tie"]


def main():
    import windport_deadend_ext as EXT
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="conservative", part="exact", grid=EXT.TAIL, tu=TUS, code=code)
    out = ROOT / "results" / ("windport_conservative_exact_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = sorted((dict(x, tu=t) for x in EXT.tail_keys() for t in TUS), key=lambda x: -x["K"] * x["L"])
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "two-block chain enumeration under the conservative lifting rule", "conservative")
    rows = []
    try:
        for rs in slot_imap(chunk, [its[k:k + a.chunk] for k in range(0, len(its), a.chunk)], a.procs, initializer=init, slots_dir=a.slots, tag="conservative"):
            rows += rs
            prog.write(done=len(rows))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    rows.sort(key=lambda r: r["key"])
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    g = collections.defaultdict(list)
    for r in rows:
        g[("mixed" if r["S"] else "direct", r["o"], r["tu"])].append(r)
    L = ["# Two-block chain enumeration under the conservative lifting rule (lift from the vehicle only after its tail leaves the chain head block) vs W″", "",
         f"- {len(rows)} instances; exact > W″ in {sum(r['over'] for r in rows)}; = W″ in {sum(r['tie'] for r in rows)} ({sum(r['tie'] for r in rows) / len(rows):.1%}).", "",
         "| Lifting | o | tu | Instances | Over | Tie | Binding incl. chainzone / chainprep |", "|---|---:|---:|---:|---:|---:|---:|"]
    L += [f"| {k[0]} | {k[1]} | {k[2]} | {len(rs)} | {sum(r['over'] for r in rs)} | {sum(r['tie'] for r in rs)} | {sum('chain' in r['binding'] for r in rs)} |"
          for k, rs in sorted(g.items())]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=L[2][:300])
    print(out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
