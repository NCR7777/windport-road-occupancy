"""Dead-end coupling: splitting the gap between 13.19 h and 18.42 h in the core instance. W″ (windport/bound_dead.py), which combines the
dead-end quay coupling (Corollary 6) and the cradle coupling under single-sequence handover (Corollary 7), is checked on the committed batches
and broken down by binding term. Synthetic archetypes only; the committed modules under windport/, occupancy/, bounds/ and exact/ are unchanged.

--part port    port-time batch of the extra analyses (results/runs/port_time, 3,600 FCFS rows; A1 × five scenarios ×
               cradle mode × five lift arrangements × K = 1–8 × n_v = 3, 5, 10 × Q_h = 0, 1, unlimited): L′*(n_v) (extra analyses, bound3),
               gap decomposition L*_a (Corollary 6(a): Q = Q_s), L*_b (plus the whole-chain quay-zone term of Corollary 6(b)), L″* (plus
               Corollary 7), check W″(port time) ≥ n_v, binding term at L″*. The core instance (long single lane / long corridor, S = 1,
               Q_h = 0, n_v = 10) is 32 of these rows.
--part exact   enumerations of the W grid check and the E1-E3 batches (results/runs/w1_grid: 18,144 single-window cases, plus
               mixed lifting and two-lane cut, 4,800 cases) and the two-block chain enumeration of the E4-E7 batches
               (results/runs/chain, 3,840 cases): exact values unchanged, only the bounds (W1 / W1′ and W″) recomputed;
               check exact ≤ W″, broken down by binding term.
--part chain2  two-block chain enumeration with long windows (new, windport/exact_chain.py unchanged): L = 12, 16, 20 (5, 9 in the E4-E7
               batches), so that Corollary 6(b) and Corollary 7 take effect; grid K = 1–3, S = 0–2, Qs = 1–2 (Qs ≤ K), hp = 1–2,
               a1, a2 ∈ {1, 3}, e = 1–2, hd = 1–2, p = 1–2, G = 0, 4.
--part strat   tightness breakdown: E2 (540 small CP-SAT cases of the E1-E3 batches, optimum from results/runs/e2 and the
               600 s rerun e2long) and E4 (E4-E7 batches, results/runs/e4, 10,080 FCFS simulation points): W′, W″ and
               the binding term per case.
Output results/windport_deadend_<part>_<config hash>/: config.json (grid, input directories, code SHA-256), progress.json, points.csv, summary.md.
Run: python experiments/windport_deadend.py --part port --procs 16 --slots DIR
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
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap                   # noqa: E402

CODE = ["windport/bound.py", "windport/bound2.py", "windport/bound3.py", "windport/bound_dead.py", "windport/sim.py", "windport/sim2.py",
        "windport/archetypes.py", "windport/exact.py", "windport/exact_chain.py", "occupancy/network.py", "occupancy/params.py",
        "experiments/windport_runs.py", "experiments/windport_extra.py", "experiments/windport_e2.py", "experiments/windport_deadend.py"]
SRC = dict(port="results/runs/port_time", w1="results/runs/w1_grid", chain="results/runs/chain",
           e2="results/runs/e2", e2long="results/runs/e2_long", e4="results/runs/e4")
CHAIN2 = dict(K=[1, 2, 3], S=[0, 1, 2], Qs=[1, 2], hp=[1, 2], a1=[1, 3], a2=[1, 3], e=[1, 2], hd=[1, 2], p=[1, 2], G=[0, 4], L=[12, 16, 20], o=1)
LABEL = dict(crane="crane", cradle="cradle turnover", fleet="fleet", road="road")
_CACHE = {}


def load(d, name="points.csv"):
    return list(csv.DictReader(open(ROOT / d / name, encoding="utf-8")))


def parts(c):
    """bound_dead.parts4 cached by (geometry, parameters, S, K, lifting, Q_h) (as windport_recheck.parts); G is taken per row."""
    from windport import bound_dead as B4
    key = json.dumps({k: v for k, v in c.items() if k not in ("cal", "horizon_h", "n_load", "rule", "record", "unload_release_h")}, sort_keys=True,
                     default=str)
    if key not in _CACHE:
        _CACHE[key] = B4.parts4(c)
    return dict(_CACHE[key], G=c["cal"]["crane"][0][0] * 3600.0)


def old_w(w):
    """W′ (extra analyses, bound3) expressed in bound_dead.terms4: Q from Corollary 4, no Corollary 6(b), no Corollary 7."""
    return dict(w, P=replace(w["P"], Q=w["Q3"]), zc=[])


def label(t):
    """Label for the binding-term breakdown: (bound, class label, binding terms). A tie across classes gets the tie label listing the
    classes; a binding preparation term gets the preparation suffix (the labels are data strings, see LABEL)."""
    from windport import bound_dead as B4
    t = dict(t)
    for k in ("zone", "chainzone"):                       # as in bound.terms: a quay-zone term not tighter than the fleet term is not listed
        if k in t and "fleet" in t and t[k] >= t["fleet"]:
            del t[k]
    v, keys, cls, prep = B4.binding(t)
    lab = LABEL[cls[0]] if len(cls) == 1 else "tie (" + ", ".join(LABEL[c] for c in cls) + ")"
    return v, lab + ("·preparation" if prep and len(cls) == 1 else ""), "+".join(keys)


def lst(f, n):
    from windport import bound3 as B3
    return B3.lstar(f, n)[0] / 3600.0


# ---------------------------------------------------------------- port
def one_port(row):
    import windport_extra as X
    from windport import bound3 as B3
    from windport import bound_dead as B4
    c = X.port_cfg(row["scen"], row["mode"], row["arr"], int(row["K"]), int(row["n_v"]), X.hold_v(row["hold"]))
    w = parts(c)
    n = int(row["n_v"])
    wa = dict(w, zc=[])
    f_a, f_b, f4 = B4.wfn4(c, wa, couple=False), B4.wfn4(c, w, couple=False), B4.wfn4(c, w)
    ph = float(row["port_h"]) * 3600.0 + 0.5e-6 * 3600.0 if row["port_h"] else None    # stored port time has 6 decimals (h); add back the rounding
    lo4, hi4 = B3.lstar(f4, n)
    v, lab, keys = label(B4.terms4(w, hi4))
    return dict(key=row["key"], scen=row["scen"], mode=row["mode"], arr=row["arr"], K=row["K"], n_v=n, hold=row["hold"], port_h=row["port_h"],
                lstar3=row["lstar_lo"], lstar_a=round(lst(f_a, n), 6), lstar_b=round(lst(f_b, n), 6), lstar4=round(lo4 / 3600.0, 6),
                Q3=w["Q3"], Q4=w["P"].Q, n_zc=len(w["zc"]), cz=round(min((z[0] for z in w["zc"]), default=0.0), 3),
                w4_at_port="" if ph is None else f4(ph), viol=int(ph is not None and f4(ph) < n), binding=keys, cls=lab)


# ---------------------------------------------------------------- exact / chain2
def wabs(P, G, zc=(), chains=(), bm=(), hp=0):
    return dict(P=P, G=G or 0, zc=list(zc), chains=list(chains), bm=list(bm), hp=hp)


def one_w1(r):
    """One case of the abstract single-lane enumeration (W grid check / E1-E3 batches): W1 (stored) and W″ (Corollary 7; there are no chains
    here, so Corollary 6 does not apply)."""
    from windport import bound as WB
    from windport import bound_dead as B4
    f = r.get("family", "single")
    g = lambda k: int(r[k])
    P = WB.lane(g("L"), g("p"), g("S"), g("K"), g("hp"), g("hd"), g("tl"), g("te"), g("er"), g("Q"), qe=2 if f == "qe2" else 1, mixed=f == "mixed")
    empty = r["start"] == "empty"
    w = wabs(P, g("G") if empty else None, hp=g("hp"))
    v0, lab0, k0 = label(B4.terms4(w, P.L, empty=empty, couple=False))
    v, lab, k = label(B4.terms4(w, P.L, empty=empty))
    return dict(src="exact", family=f, key="|".join(f"{c}{r[c]}" for c in ("K", "S", "Q", "hp", "tl", "hd", "te", "er", "p", "L", "start", "G")),
                exact=g("exact"), w_old=v0, cls_old=lab0, w_new=v, cls_new=lab, binding=k, stored=g("bound"))


def chain_bounds(x, o=1):
    """Two-block chain: W1′ (E4-E7 batches: W1 with each block as a cut, Q = K, min with Π_S) and W″ (each block as a cut,
    Q = min(K, Qs) (Corollary 6(a)), the whole-chain quay-zone term of Corollary 6(b), Corollary 7).
    Returns ((W1′, label), (W″, label, terms))."""
    from windport import bound as WB
    from windport import bound2 as W2
    from windport import bound_dead as B4
    from windport import exact_chain as XC
    K, S, Qs, hp, a1, a2, e, hd, p, G, L = (x[k] for k in ("K", "S", "Qs", "hp", "a1", "a2", "e", "hd", "p", "G", "L"))
    hd_ = hd if S else 0
    c = hp + a1 + a2 + o + hd_ + 2 * e
    ch = XC.chain_params(a1, a2, e, e, hd, S, o)
    q = min(K, Qs)
    up = W2.span(1, ch["up"]) + ch["dq"]
    zc = [(up + W2.span(1, ch["down"]), hp + ch["start0"] + up)] if q == 1 else []
    old = new = None
    for tl, te, dq in ((a1 + o, e, a2 + hd_), (a2 + o, e + o, hd_)):
        P = WB.Port(L=L, p=p, S=S, K=K, hp=hp, hd=hd_, tl=tl, te=te, c=c, ce=2 * e, dq=dq, Q=K, te_occ=te)
        o_ = label(B4.terms4(wabs(P, G, (), [ch], [q], hp), L, couple=False))
        n_ = label(B4.terms4(wabs(replace(P, Q=q), G, zc, [ch], [q], hp), L))
        old = o_ if old is None or o_[0] < old[0] else old
        new = n_ if new is None or n_[0] < new[0] else new
    return old, new


def one_chain(r, src):
    from windport import exact_chain as XC
    x = {k: int(r[k]) for k in ("K", "S", "Qs", "hp", "a1", "a2", "e", "hd", "p", "G", "L")}
    if src == "chain2":
        r = dict(r, exact=XC.max_delivery(x["K"], x["S"], x["Qs"], x["hp"], x["a1"], x["a2"], x["e"], x["e"], x["hd"], x["p"], x["G"], x["L"],
                                          CHAIN2["o"]))
    (v0, lab0, _), (v, lab, k) = chain_bounds(x)
    out = dict(src=src, family="chain", key=r["key"], exact=int(r["exact"]), w_old=v0, cls_old=lab0, w_new=v, cls_new=lab, binding=k,
               stored=r.get("w1s", ""))
    return out


def chain2_keys():
    g = CHAIN2
    out = []
    for K, S, Qs, hp, a1, a2, e, hd, p, G, L in itertools.product(*(g[k] for k in ("K", "S", "Qs", "hp", "a1", "a2", "e", "hd", "p", "G", "L"))):
        if Qs > K or (S == 0 and hd > 1):
            continue
        out.append(dict(key=f"K{K}|S{S}|Q{Qs}|hp{hp}|a{a1}-{a2}|e{e}|hd{hd}|p{p}|G{G}|L{L}", K=K, S=S, Qs=Qs, hp=hp, a1=a1, a2=a2, e=e, hd=hd, p=p,
                        G=G, L=L))
    return out


# ---------------------------------------------------------------- strat
def one_e2(r):
    import windport_e2 as E2
    from windport import bound_dead as B4
    c = E2.cfg_of(r["key"])
    w = parts(c)
    L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * 3600.0
    v0, lab0, k0 = label(B4.terms4(old_w(w), L, couple=False))
    v, lab, k = label(B4.terms4(w, L))
    return dict(src="e2", key=r["key"], status=r["cp_status"], best=int(r["cp_best"]), cp_bound=r["cp_bound"], sim=int(r["sim"]), w_old=v0,
                cls_old=lab0, w_new=v, cls_new=lab, binding=k, binding_old=k0)


def one_e4(r):
    import windport_runs as T
    from windport import bound_dead as B4
    c = T.cfg_of("e4", r["key"])
    w = parts(c)
    L = float(r["L"]) * 3600.0
    v0, lab0, k0 = label(B4.terms4(old_w(w), L, couple=False))
    v, lab, k = label(B4.terms4(w, L))
    return dict(src="e4", key=r["key"], kind=r["kind"], scen=r["scen"], mode=r["mode"], S=r["S"], K=r["K"], sim=int(r["sim"]), stored=r["w1g"],
                w_old=v0, cls_old=lab0, w_new=v, cls_new=lab, binding=k, binding_old=k0)


# ---------------------------------------------------------------- dispatch
def work(arg):
    part, r = arg
    if part == "port":
        return one_port(r)
    if part == "exact":
        return one_chain(r, "chain") if r.get("_src") == "chain" else one_w1(r)
    if part == "chain2":
        return one_chain(r, "chain2")
    return one_e2(r) if r.get("_src") == "e2" else one_e4(r)


def chunk(items):
    return [work(x) for x in items]


def init():
    pin(list(range(1, os.cpu_count())))


def items(part):
    if part == "port":
        return [r for r in load(SRC["port"]) if r["rep"] == "fcfs"]
    if part == "exact":
        return load(SRC["w1"]) + load(SRC["w1"], "extra.csv") + [dict(r, _src="chain") for r in load(SRC["chain"])]
    if part == "chain2":
        return chain2_keys()
    lng = {r["key"]: r for r in load(SRC["e2long"])}
    e2 = [dict(r, **{k: v for k, v in lng.get(r["key"], {}).items() if k.startswith("cp_")}, _src="e2") for r in load(SRC["e2"])]
    return e2 + load(SRC["e4"])


def pct(a, n):
    return f"{a / n:.1%}" if n else "-"


def strat_table(rows, title, ok=lambda r: True, ref="exact"):
    """Breakdown by binding term: per class the number of cases and the number and share with = W′ / = W″ (ref is the delivery column
    compared against)."""
    rs = [r for r in rows if ok(r) and r["w_new"] > 0]
    cls = sorted({r["cls_new"] for r in rs} | {r["cls_old"] for r in rs})
    L = [f"### {title}", "", "| Binding class | Cases (W′) | = W′ | Attained W′ | Cases (W″) | = W″ | Attained W″ |", "|---|---:|---:|---:|---:|---:|---:|"]
    for c in cls + ["Total"]:
        a = [r for r in rs if c in ("Total", r["cls_old"])]
        b = [r for r in rs if c in ("Total", r["cls_new"])]
        ea, eb = sum(r[ref] == r["w_old"] for r in a), sum(r[ref] == r["w_new"] for r in b)
        L.append(f"| {c} | {len(a)} | {ea} | {pct(ea, len(a))} | {len(b)} | {eb} | {pct(eb, len(b))} |")
    road = lambda key: [r for r in rs if "road" in r[key]]
    ra, rb = road("cls_old"), road("cls_new")
    L += ["", f"Road involved in the binding term (incl. ties): W′ {len(ra)} cases, {sum(r[ref] == r['w_old'] for r in ra)} attained; "
          f"W″ {len(rb)} cases, {sum(r[ref] == r['w_new'] for r in rb)} attained.", ""]
    return L


def summary(part, rows):
    if part == "port":
        core = [r for r in rows if r["scen"] in ("lane", "longslow") and r["arr"] == "S1" and r["n_v"] == 10 and r["hold"] == "0"]
        L = ["# Dead-end coupling, port: L″* on the port-time batch of the extra analyses (3,600 FCFS rows)", "",
             f"- W″(port time) < n_v: {sum(r['viol'] for r in rows)} rows; L″* > port time: {sum(r['lstar4'] > float(r['port_h']) + 1e-6 for r in rows if r['port_h'])} rows.",
             f"- rows with L″* > L′*: {sum(r['lstar4'] > float(r['lstar3']) + 1e-6 for r in rows)}; rows with Q reduced from the Corollary 4 value: {sum(r['Q4'] < r['Q3'] for r in rows)}; "
             f"rows with a whole-chain quay-zone term of Corollary 6(b): {sum(r['n_zc'] > 0 for r in rows)}.", "",
             "## Core instance (S = 1 cradle, Q_h = 0, n_v = 10)", "",
             "| Scenario | Cradle | K | FCFS h | L′* (extra analyses) | L*_a: Q = Q_s | L*_b: + whole-chain quay zone | L″*: + cradle coupling | FCFS − L″* | Binding at L″* |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for r in sorted(core, key=lambda r: (r["scen"], r["mode"], int(r["K"]))):
            L.append(f"| {r['scen']} | {r['mode']} | {r['K']} | {float(r['port_h']):.2f} | {float(r['lstar3']):.2f} | {r['lstar_a']:.2f} | "
                     f"{r['lstar_b']:.2f} | {r['lstar4']:.3f} | {float(r['port_h']) - r['lstar4']:.3f} | {r['binding']} ({r['cls']}) |")
        L += ["", "## Full table: cells where L″* is raised (n_v = 10; per scenario × lift arrangement × Q_h, minimum port time and minimum L″* over K = 1–8)", "",
              "| Scenario | Cradle | Lifting | Q_h | Min port time h | min L′* | min L″* | Min port time / min L″* |", "|---|---|---|---|---:|---:|---:|---:|"]
        grp = collections.defaultdict(list)
        for r in rows:
            if r["n_v"] == 10 and r["port_h"]:
                grp[(r["scen"], r["mode"], r["arr"], r["hold"])].append(r)
        for k, rs in sorted(grp.items()):
            ph, l3, l4 = min(float(r["port_h"]) for r in rs), min(float(r["lstar3"]) for r in rs), min(r["lstar4"] for r in rs)
            if l4 > l3 + 1e-6:
                L.append(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {ph:.2f} | {l3:.2f} | {l4:.2f} | {ph / l4:.3f} |")
        return L
    if part in ("exact", "chain2"):
        L = [f"# Dead-end coupling, {part}: exact values from enumeration and W″", ""]
        for fam in sorted({(r["src"], r["family"]) for r in rows}):
            rs = [r for r in rows if (r["src"], r["family"]) == fam]
            L.append(f"- {fam[0]} / {fam[1]}: {len(rs)} cases; exact > W″ {sum(r['exact'] > r['w_new'] for r in rs)} cases; exact > W′ {sum(r['exact'] > r['w_old'] for r in rs)} cases; "
                     f"W″ < W′ {sum(r['w_new'] < r['w_old'] for r in rs)} cases (total tightening {sum(r['w_old'] - r['w_new'] for r in rs)} items, tightened to the exact value in "
                     f"{sum(r['w_new'] < r['w_old'] and r['w_new'] == r['exact'] for r in rs)} cases); equality W′ {sum(r['exact'] == r['w_old'] for r in rs)} → W″ "
                     f"{sum(r['exact'] == r['w_new'] for r in rs)}; stored bound differs from W′ in {sum(str(r['stored']) not in ('', str(r['w_old'])) for r in rs)} cases.")
        L.append("")
        if part == "exact":
            L += strat_table(rows, "Table A1 (single-window enumeration of the W grid check / E1-E3 batches, 18,144 cases) by binding term", lambda r: r["src"] == "exact" and r["family"] == "single")
            L += strat_table(rows, "Two-block chain enumeration (E4-E7 batches, 3,840 cases) by binding term", lambda r: r["src"] == "chain")
        else:
            L += strat_table(rows, "Two-block chain enumeration with long windows by binding term", lambda r: True)
        return L
    e2 = [r for r in rows if r["src"] == "e2"]
    e4 = [r for r in rows if r["src"] == "e4"]
    opt = [r for r in e2 if r["status"] == "OPTIMAL"]
    L = ["# Dead-end coupling, strat: tightness breakdown (E2 small CP-SAT cases, E4 FCFS)", "",
         f"- E2: {len(e2)} cases, {len(opt)} proven optimal; CP-SAT best > W″ {sum(r['best'] > r['w_new'] for r in e2)} cases; proven optimum = W′ "
         f"{sum(r['best'] == r['w_old'] for r in opt)} → = W″ {sum(r['best'] == r['w_new'] for r in opt)} cases; Σ(bound − optimum) "
         f"{sum(r['w_old'] - r['best'] for r in opt)} → {sum(r['w_new'] - r['best'] for r in opt)}.",
         f"- E4: {len(e4)} points; simulation > W″ {sum(r['sim'] > r['w_new'] for r in e4)}; W″ < W′ {sum(r['w_new'] < r['w_old'] for r in e4)} points; "
         f"W′ differs from the stored W1′ of the E4-E7 batches at {sum(str(r['w_old']) != r['stored'] for r in e4)} points.", ""]
    L += strat_table(opt, "E2 cases proven optimal (CP-SAT optimum vs bound)", ref="best")
    L += ["### E2 cases not proven optimal (best feasible, solver item bound, proof status, W″)", "", "| Case | Best feasible | CP-SAT bound | Status | W′ | W″ | min(W″, CP bound) − best |",
          "|---|---:|---:|---|---:|---:|---:|"]
    for r in e2:
        if r["status"] != "OPTIMAL":
            ub = min(r["w_new"], math.floor(float(r["cp_bound"]) + 1e-6))
            L.append(f"| {r['key']} | {r['best']} | {r['cp_bound']} | {r['status']} | {r['w_old']} | {r['w_new']} | {ub - r['best']} |")
    L.append("")
    L += strat_table(e4, "E4 (A1, A2, A3 × base / long single lane × cradle mode, L = 12 h, FCFS): FCFS = bound", ref="sim")
    L += strat_table(e4, "E4, A1 (Layout 1)", lambda r: r["kind"] == "A1", ref="sim")
    L += strat_table(e4, "E4, A1 long single lane", lambda r: r["kind"] == "A1" and r["scen"] == "lane", ref="sim")
    return L


COLS = dict(port=["key", "scen", "mode", "arr", "K", "n_v", "hold", "port_h", "lstar3", "lstar_a", "lstar_b", "lstar4", "Q3", "Q4", "n_zc", "cz",
                  "w4_at_port", "viol", "binding", "cls"],
            exact=["src", "family", "key", "exact", "stored", "w_old", "cls_old", "w_new", "cls_new", "binding"],
            strat=["src", "key", "kind", "scen", "mode", "S", "K", "status", "best", "cp_bound", "sim", "stored", "w_old", "cls_old", "binding_old",
                   "w_new", "cls_new", "binding"])
COLS["chain2"] = COLS["exact"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["port", "exact", "chain2", "strat"], required=True)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=20)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="deadend", part=a.part, src=SRC, chain2=CHAIN2 if a.part == "chain2" else None, code=code)
    out = ROOT / "results" / ("windport_deadend_" + a.part + "_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = items(a.part)
    if a.part == "chain2":
        its.sort(key=lambda r: -r["K"] * r["L"])                    # large cases first
    prog = Progress(out / "progress.json", len(its), 0, a.procs, f"Dead-end coupling {a.part}: W″ check and tightness breakdown", "deadend")
    chunks = [[(a.part, r) for r in its[k:k + a.chunk]] for k in range(0, len(its), a.chunk)]
    rows = []
    try:
        for rs in slot_imap(chunk, chunks, a.procs, initializer=init, slots_dir=a.slots, tag="deadend"):
            rows += rs
            prog.write(done=len(rows))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    rows.sort(key=lambda r: (r.get("src", ""), r.get("family", ""), r["key"]))
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS[a.part], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    L = summary(a.part, rows)
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=L[2][:300] if len(L) > 2 else "")
    print(out)
    print("\n".join(L[:40]))


if __name__ == "__main__":
    main()
