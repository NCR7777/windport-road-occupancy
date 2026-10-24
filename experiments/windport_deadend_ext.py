"""Dead-end coupling, extension: Corollary 6 generalised to chains with dq < 0 (windport/bound_dead.parts4(signed=True), written W″ₛ; the
comparison under the original semantics "lifting may start while the vehicle's tail still occupies the single lane"), and a check of the
Corollary 6 premises under the conservative lifting semantics (base case: the SPMT leaves the single lane completely and stops at the lifting
position before the lift starts). Synthetic archetypes only; shipyard-derived maps are skipped.

--part tail    variant of the two-block chain enumeration in which a pile may be lifted from the vehicle while its tail still occupies the
               top block of the chain (windport/exact_chain_tail.py): direct lifting S = 0, mixed lifting S = 1–2 × K = 1–3 × Qs = 1–2 ×
               tail o = 1, 2 × hp, a1, a2, hd, p, G × window L = 8, 12, 16; exact values compared with W″ₛ (each block as a cut, the cut
               window truncated at the handover; chain dq = −o; σ).
--part random  per-pile regression on random archetypes (the dead and port generators of windport_random_deadend, same seeds): W″ₛ(T_j) ≥ j,
               W″ₛ ≤ W″, W″ₛ non-decreasing, L″ₛ* ≤ T_n.
--part port    port-time batch of the extra analyses (3,600 FCFS rows): L″ₛ*(n_v), W″ₛ(port time) ≥ n_v; under the conservative semantics
               (handover not earlier than the tail leaving the chain top, dq = max(0, dq)), whether the chains of each direct / mixed-lifting
               row satisfy the Corollary 6 premises, and the corresponding L*; for K = 1 the fleet term by the saddle row of each pile.
Output results/windport_deadend_ext_<part>_<config hash>/: config.json, progress.json, points.csv (or cases.csv), summary.md.
Run: python experiments/windport_deadend_ext.py --part tail --procs 8 --slots DIR
"""
import argparse
import collections
import csv
import hashlib
import itertools
import json
import math
import os
import sys
import traceback
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap                   # noqa: E402

CODE = ["windport/bound.py", "windport/bound2.py", "windport/bound3.py", "windport/bound_dead.py", "windport/sim.py", "windport/sim2.py",
        "windport/archetypes.py", "windport/exact_chain.py", "windport/exact_chain_tail.py", "occupancy/network.py", "occupancy/params.py",
        "occupancy/sim.py", "experiments/windport_extra.py", "experiments/windport_random.py", "experiments/windport_random_lift.py",
        "experiments/windport_random_deadend.py", "experiments/windport_deadend_ext.py"]
TAIL = dict(K=[1, 2, 3], S=[0, 1, 2], Qs=[1, 2], hp=[1, 2], a1=[1, 3], a2=[2, 3], e=[2], o=[1, 2], hd=[1, 2], p=[1, 2], G=[0, 4, 5, 6, 8], L=[8, 12, 16])
RAND = dict(dead=12000, port=12000)
SRC = dict(port="results/runs/port_time")
H = 3600.0
_C = {}


# ---------------------------------------------------------------- tail
def tail_keys():
    g, out = TAIL, []
    for K, S, Qs, hp, a1, a2, e, o, hd, p, G, L in itertools.product(*(g[k] for k in ("K", "S", "Qs", "hp", "a1", "a2", "e", "o", "hd", "p", "G", "L"))):
        if Qs > K or (S == 0 and hd > 1) or o > min(a2, e):
            continue
        out.append(dict(K=K, S=S, Qs=Qs, hp=hp, a1=a1, a2=a2, e=e, o=o, hd=hd, p=p, G=G, L=L))
    return out


def tail_bound(x):
    """W″ₛ on the two-block chain where a pile may be lifted from the vehicle while its tail still occupies the top block (handover ≥ arrival
    at the quay side = a1 + a2 after entering the chain). Returns (W″ₛ, binding terms).
    Cuts: block 1 tl = a1 + o, dq = a2 − o; block 2 with the window truncated at the handover, tl = a2, dq = 0 (as in H4); return te = e, e + o.
    Fleet: direct lifting, consecutive handovers ≥ hp + a1 + a2 + 2e (the previous pile may be lifted after the tail leaves and the next one on
    arrival, so the tail wait o is not counted), first one ≥ hp + a1 + a2; mixed lifting, after conversion ≥ hp + a1 + a2 + 2e (straight back
    after setting down, next pile lifted on arrival). Chain: dq = −o, c_z = a1 + a2 + 2e, σ = a1 + a2 + o + 2e, f₁ = hp + a1 + a2;
    Q = min(K, Qs) (Corollary 6(a))."""
    from windport import bound as WB
    from windport import bound2 as W2
    from windport import bound_dead as BD
    from windport import exact_chain as XC
    K, S, Qs, hp, a1, a2, e, o, hd, p, G, L = (x[k] for k in ("K", "S", "Qs", "hp", "a1", "a2", "e", "o", "hd", "p", "G", "L"))
    mixed = S > 0
    q = min(K, Qs)
    if mixed:
        c, ce = hp + a1 + a2 + 2 * e + hd, 2 * e
    else:
        c, ce = hp + a1 + a2 + 2 * e, 2 * e                # previous pile lifted after the tail leaves (QL), next on arrival (QT): no tail wait
    ch = dict(XC.chain_params(a1, a2, e, e, hd, S, o), dq=-o)
    pl, pe = W2.span(1, ch["up"]), W2.span(1, ch["down"])
    zc = [(pl - o + pe, hp + pl - o, pl + max(0, -o) + pe)] if q == 1 else []
    best = None
    for tl, te, dq in ((a1 + o, e, a2 - o), (a2, e + o, 0)):
        P = WB.Port(L=L, p=p, S=S, K=K, hp=hp, hd=hd if S else 0, tl=tl, te=te, c=c, ce=ce, dq=dq, Q=q, mixed=mixed, te_occ=te)
        t = BD.terms4(dict(P=P, G=G, zc=zc, chains=[ch], bm=[q], hp=hp), L)
        v, keys, _, _ = BD.binding(t)
        best = (v, "+".join(keys)) if best is None or v < best[0] else best
    return best


def one_tail(x):
    from windport import exact_chain_tail as XT
    n = XT.max_delivery(x["K"], x["S"], x["Qs"], x["hp"], x["a1"], x["a2"], x["e"], x["e"], x["hd"], x["p"], x["G"], x["L"], x["o"], mixed=x["S"] > 0)
    v, why = tail_bound(x)
    return dict(x, key="|".join(f"{k}{x[k]}" for k in x), exact=n, bound=v, binding=why, over=int(n > v), tie=int(n == v))


# ---------------------------------------------------------------- random
def one_rand(arg):
    gen, i = arg
    import windport_random_deadend as R
    from windport import bound3 as B3
    from windport import bound_dead as BD
    from windport import sim2 as S2
    c = R.make(gen, i)
    if c["geo"]["kind"] == "map":
        return dict(gen=gen, i=i, skipped=1, why="")
    try:
        orig, S2.bounds2 = S2.bounds2, (lambda *a, **k: None)
        try:
            net, p, sim, r = S2.simulate2(c)
        finally:
            S2.bounds2 = orig
        G, b = c["cal"]["crane"][0][0] * H, c["cal"]["crane"][0][1] * H
        w = BD.parts4(c)
        ws = BD.parts4(c, signed=True)
        f, fs = BD.wfn4(c, w), BD.wfn4(c, ws)
        T = sorted(x["F_vessel"] - G for x in sim.trips if x["F_vessel"] is not None and x["s"] >= G - 1e-6 and x["F_vessel"] <= b + 1e-6)[:c["n_load"]]
        vs, v4 = [fs(t) for t in T], [f(t) for t in T]
        why = []
        viol = [n for n, v in enumerate(vs, 1) if v < n]
        if viol:
            why.append("def")
        if any(a > b_ for a, b_ in zip(vs, v4)):
            why.append("wle")
        if T and B3.lstar(fs, len(T))[0] > T[-1] + 1e-6:
            why.append("lstar")
        top = T[-1] + 3 * H if T else H
        grid = sorted(set(T) | {k * 1.5 * top / 30 for k in range(31)})
        vals = [fs(t) for t in grid]
        if any(v2 < v1 for v1, v2 in zip(vals, vals[1:])):
            why.append("mono")
        neg = sum(1 for z in ws["zc"] if z[2] > z[0] + 1e-9)
        return dict(gen=gen, i=i, skipped=0, kind=c["geo"]["kind"], lift=c.get("lift", "cradle"), S=c["S"], K=c["K"], hold=str(c["hold"]), n=len(T),
                    viol=len(viol), tight=int(any(a < b_ for a, b_ in zip(vs, v4))), neg=neg, zc_s=len(ws["zc"]), zc=len(w["zc"]),
                    eq_last=int(bool(T) and vs[-1] == len(T)), why="+".join(why))
    except Exception:
        return dict(gen=gen, i=i, skipped=0, why="error", error=traceback.format_exc()[-600:])


# ---------------------------------------------------------------- port
def parts(c, signed):
    from windport import bound_dead as BD
    key = json.dumps([{k: v for k, v in c.items() if k not in ("cal", "horizon_h", "n_load", "rule", "record")}, signed], sort_keys=True, default=str)
    if key not in _C:
        _C[key] = BD.parts4(c, signed=signed)
    return _C[key]


def one_port(row):
    import windport_extra as X
    from windport import bound2 as W2
    from windport import bound3 as B3
    from windport import bound_dead as BD
    from windport import sim as WS
    from windport import sim2 as S2
    c = X.port_cfg(row["scen"], row["mode"], row["arr"], int(row["K"]), int(row["n_v"]), X.hold_v(row["hold"]))
    n = int(row["n_v"])
    G = c["cal"]["crane"][0][0] * H
    ws = dict(parts(c, True), G=G)
    fs = BD.wfn4(c, ws)
    ph = float(row["port_h"]) * H + 0.5e-6 * H
    lift = "direct" if c["S"] == 0 else c.get("lift", "cradle")
    prem = ""
    # premises under the conservative semantics: gate threshold behind the chain top, first departure leg runs back through the chain,
    # Q_h = 0 (geometry), dq ≥ 0 (semantics)
    if lift in ("direct", "mixed") and X.hold_v(row["hold"]) == 0:
        D, net, p, *_ = S2.setup2(c)
        W = D["windport"]
        chs = W2.chain_times(net, p, W["storage"], W["cradles"][:max(1, c["S"])], p["Lv"], p["B"], 1e7, S2.routes_of(D, c, net))
        prem = int(any(W2.quay_side_Q(net, p, W["storage"], W["cradles"][:max(1, c["S"])], p["Lv"], p["B"], ch, 0) < math.inf for ch in chs))
    fc = BD.wfn4(c, dict(parts(c, "clear"), G=G))
    return dict(key=row["key"], scen=row["scen"], mode=row["mode"], arr=row["arr"], K=row["K"], n_v=n, hold=row["hold"], port_h=row["port_h"],
                lstar_s=round(B3.lstar(fs, n)[0] / H, 6), viol=int(fs(ph) < n), neg=sum(1 for z in ws["zc"] if z[2] > z[0] + 1e-9),
                lstar_clear=round(B3.lstar(fc, n)[0] / H, 6), premise_clear=prem)


def k1_rows():
    """Fleet term for K = 1 by the saddle row of each pile: at the window start one pile is on the cradle and one on the vehicle; each of the
    n − 2 later handovers needs a full cycle, which depends on the saddle row of that pile; pile j is in row j mod 8.
    L ≥ p + hd + (sum of the 8 smallest of the 10 pile cycles). Cycles per row from bound.occupancy_times on a single row."""
    import windport_extra as X
    from windport import bound as WB
    from windport import sim2 as S2
    out = []
    for sc, mode in itertools.product(("lane", "longslow"), ("on_road", "pull_in")):
        c = X.port_cfg(sc, mode, "S1", 1, 10, 0)
        D, net, p, *_ = S2.setup2(c)
        W = D["windport"]
        pt = dict(p, load_s=p["hp_s"], unload_s=p["hd_s"])
        cyc = [WB.occupancy_times(net, pt, [row], W["cradles"][:1], p["Lv"], p["B"])["c"] for row in W["storage"]]
        piles = sorted(cyc[j % len(cyc)] for j in range(10))
        out.append(dict(scen=sc, mode=mode, cycles="/".join(f"{x:.1f}" for x in cyc), bound_h=round((p["lift_s"] + p["hd_s"] + sum(piles[:8])) / H, 6)))
    return out


# ---------------------------------------------------------------- dispatch
def work(arg):
    part, r = arg
    if part == "tail":
        return one_tail(r)
    if part == "random":
        return one_rand(r)
    return one_port(r)


def chunk(items):
    return [work(x) for x in items]


def init():
    pin(list(range(1, os.cpu_count())))


def items(part):
    if part == "tail":
        return sorted(tail_keys(), key=lambda x: -x["K"] * x["L"])
    if part == "random":
        return [(g, i) for g, n in RAND.items() for i in range(n)]
    return [r for r in csv.DictReader(open(ROOT / SRC["port"] / "points.csv", encoding="utf-8")) if r["rep"] == "fcfs"]


def summary(part, rows, extra):
    if part == "tail":
        L = ["# Dead-end coupling extension, tail: two-block chain enumeration with lifting from the vehicle while its tail occupies the chain top, and W″ₛ", "",
             f"- {len(rows)} cases; exact > W″ₛ {sum(r['over'] for r in rows)} cases; = W″ₛ {sum(r['tie'] for r in rows)} cases ({sum(r['tie'] for r in rows) / len(rows):.1%}).",
             "", "| Lifting | o | Cases | Over | Equal | Binding includes chainzone / chainprep |", "|---|---:|---:|---:|---:|---:|"]
        for (S, o), rs in sorted(collections.defaultdict(list, {k: [r for r in rows if (r["S"] > 0, r["o"]) == k] for k in {(r["S"] > 0, r["o"]) for r in rows}}).items()):
            L.append(f"| {'mixed' if S else 'direct'} | {o} | {len(rs)} | {sum(r['over'] for r in rs)} | {sum(r['tie'] for r in rs)} | "
                     f"{sum('chain' in r['binding'] for r in rs)} |")
        return L
    if part == "random":
        ran = [r for r in rows if not r["skipped"] and r["why"] != "error"]
        L = ["# Dead-end coupling extension, random: per-pile regression of W″ₛ", ""]
        for g in RAND:
            rs = [r for r in ran if r["gen"] == g]
            L.append(f"- {g}: {sum(1 for r in rows if r['gen'] == g)} cases, shipyard-derived maps skipped {sum(r['skipped'] for r in rows if r['gen'] == g)}, run {len(rs)}; errors "
                     f"{sum(1 for r in rows if r['gen'] == g and r['why'] == 'error')}; {sum(r['n'] for r in rs):,} piles checked, W″ₛ(T_j) < j for {sum(r['viol'] for r in rs)} piles; "
                     f"W″ₛ > W″ {sum('wle' in r['why'] for r in rs)} cases, non-monotone {sum('mono' in r['why'] for r in rs)} cases, L″ₛ* > T_n {sum('lstar' in r['why'] for r in rs)} cases; "
                     f"chains with dq < 0 (σ > c_z) in {sum(r['neg'] > 0 for r in rs)} cases, W″ₛ strictly below W″ in {sum(r['tight'] for r in rs)} cases.")
        return L
    L = ["# Dead-end coupling extension, port: W″ₛ and the conservative semantics (3,600 FCFS rows)", "",
         f"- W″ₛ(port time) < n_v: {sum(r['viol'] for r in rows)} rows; L″ₛ* > port time: {sum(r['lstar_s'] > float(r['port_h']) + 1e-6 for r in rows)} rows; rows with a dq < 0 chain: "
         f"{sum(r['neg'] > 0 for r in rows)}.",
         f"- of the {sum(r['premise_clear'] != '' for r in rows)} direct / mixed-lifting rows with Q_h = 0 under the conservative semantics, the geometric premise of Corollary 6 holds in {sum(r['premise_clear'] == 1 for r in rows)} rows.", "",
         "## Direct / mixed lifting (n_v = 10, Q_h = 0, minimum over K = 1–8)", "",
         "| Scenario | Cradle | Lifting | FCFS h | L″* (Corollary 6 as stated) | L″ₛ* (generalised, original semantics) | FCFS / L″ₛ* | L* under the conservative semantics (simulation pending) |", "|---|---|---|---:|---:|---:|---:|---:|"]
    grp = collections.defaultdict(list)
    for r in rows:
        if r["n_v"] == 10 and r["hold"] == "0" and r["arr"] in ("S0", "S1m", "S3m"):
            grp[(r["scen"], r["mode"], r["arr"])].append(r)
    l4 = {r["key"]: float(r["lstar4"]) for r in extra}
    for k, rs in sorted(grp.items()):
        ph = min(float(r["port_h"]) for r in rs)
        L.append(f"| {k[0]} | {k[1]} | {k[2]} | {ph:.4f} | {min(l4[r['key']] for r in rs):.4f} | {min(r['lstar_s'] for r in rs):.4f} | "
                 f"{ph / min(r['lstar_s'] for r in rs):.3f} | {min(r['lstar_clear'] for r in rs):.4f} |")
    L += ["", "## K = 1 fleet term by the saddle row of each pile (S = 1 cradle, n = 10)", "", "| Scenario | Cradle | Cycle per row s | L ≥ p + hd + sum of the 8 smallest cycles |", "|---|---|---|---:|"]
    for r in k1_rows():
        L.append(f"| {r['scen']} | {r['mode']} | {r['cycles']} | {r['bound_h']:.4f} h |")
    return L


COLS = dict(tail=["key", "K", "S", "Qs", "hp", "a1", "a2", "e", "o", "hd", "p", "G", "L", "exact", "bound", "binding", "over", "tie"],
            random=["gen", "i", "kind", "lift", "S", "K", "hold", "n", "viol", "tight", "neg", "zc_s", "zc", "eq_last", "why"],
            port=["key", "scen", "mode", "arr", "K", "n_v", "hold", "port_h", "lstar_s", "viol", "neg", "lstar_clear", "premise_clear"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["tail", "random", "port"], required=True)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=20)
    ap.add_argument("--port4", default=None, help="run directory of the dead-end coupling port part (source of the L″* column)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="deadend", round=1, part=a.part, tail=TAIL if a.part == "tail" else None, rand=RAND if a.part == "random" else None, src=SRC,
               port4=a.port4, code=code)
    out = ROOT / "results" / ("windport_deadend_ext_" + a.part + "_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = items(a.part)
    prog = Progress(out / "progress.json", len(its), 0, a.procs, f"Dead-end coupling extension {a.part}", "deadend")
    chunks = [[(a.part, r) for r in its[k:k + a.chunk]] for k in range(0, len(its), a.chunk)]
    rows = []
    try:
        for rs in slot_imap(chunk, chunks, a.procs, initializer=init, slots_dir=a.slots, tag="deadend"):
            rows += rs
            prog.write(done=len(rows))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    rows.sort(key=lambda r: (r.get("gen", ""), r.get("i", 0), r.get("key", "")))
    with open(out / ("cases.csv" if a.part == "random" else "points.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS[a.part], extrasaction="ignore")
        w.writeheader()
        w.writerows(r for r in rows if not r.get("skipped"))
    extra = list(csv.DictReader(open(ROOT / a.port4 / "points.csv", encoding="utf-8"))) if a.part == "port" else None
    L = summary(a.part, rows, extra)
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=L[2][:300])
    print(out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
