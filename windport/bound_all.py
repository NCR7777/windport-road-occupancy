"""Unified bound entry combining the three branches (statements and proofs: see the manuscript; the branch modules bound4,
bound_dead and bound_lift are unchanged).

W″(L)      = min{ the terms of bound_dead.terms4 (Theorems 1, 2; Corollaries 2, 3, 4, 7, 8; unified numbering of the manuscript),
             the crane-reach term (Corollary 9), the two reserved-period terms (Corollary 10) }
W″_lift(L) = as above with parameters from bound_lift.lift_parts (Corollary 11); in cradle mode with t_u > 0 the interface term
             and Π_S use L, all other terms use max(L − ε_U, p)
             (the handover count X of the crane-reach term and the two reserved-period terms also use max(L − ε_U, p);
             the crane-time side uses L)
L″*(n)     = inf{L : W″(L) ≥ n} (Corollary 6), bisected with bound3.lstar.
X of the crane-reach term = the fleet, cut and quay-zone terms of bound.terms minus S (Q as modified by bound_dead.parts4); the
serial-cut term Π_S uses bound4.prep_chain_fast.
Main geometry: the cradle mode of W″_lift additionally counts chains with dq < 0 (Corollary 7(c), signed_cradle;
parts(..., signed=False) is the unified-bound form)."""
import math
from dataclasses import replace

from windport import bound as WB
from windport import bound2 as W2
from windport import bound3 as B3
from windport import bound4 as B4
from windport import bound_dead as BD
from windport import bound_lift as BL
from windport import sim as WS
from windport import sim2 as S2
from windport import sim4 as S4

EPS = 1e-9
lstar = B3.lstar
# Five binding classes: the reach term goes to crane (crane-side time), the two reserved-period terms to road; the preparation
# class holds the terms limited by preparation time before the window
CLASS = dict(BD.CLASS, reach="crane", reserve="road", reserve_pre="road")
PREP = BD.PREP | {"reserve_pre"}


def parts(cfg, lift=False, signed=True):
    """Parts independent of the window length: the result of bound_dead.parts4 (original semantics) or bound_lift.lift_parts
    (conservative semantics), plus Sr, sh (crane reach) and rp (reserved periods).
    sim4.setup4 builds the road network first (side-by-side cradles, passing places, relaxed storage area, alternative turns);
    the branch functions then take the same graph from the network cache of sim2.
    signed (conservative semantics, cradle mode): also count chains with dq < 0 (signed_cradle)."""
    D, net, p, *_ = S4.setup4(cfg)
    w = BL.lift_parts(cfg) if lift else BD.parts4(cfg)
    if lift and signed and w["lift"] == "cradle" and not cfg.get("n_unload"):
        w = signed_cradle(cfg, D, net, p, w)
    return dict(w, Sr=p.get("reach"), sh=float(p.get("shift_s") or 0.0), rp=B4.reserve_parts(cfg, net, p, D), sem="lift" if lift else "plain")


def signed_cradle(cfg, D, net, p, w):
    """Corollary 7(c) applied to cradle mode: handover = placement complete (arrival + h_d); when h_d is shorter than the time for
    the vehicle tail to leave the chain top after arrival, the chain has dq < 0 and bound2.chain_times drops it.
    Here the chains with dq < 0 are added (signed dq) as in bound_dead.parts4(signed=True); the existing chains (dq ≥ 0) are kept
    as in bound_lift.lift_parts, and Corollary 7(a)(b) is recomputed via bound_dead.parts4; returns w unchanged if there is
    no new chain."""
    W = D["windport"]
    rows, quay = W["storage"], W["cradles"][:max(1, cfg["S"])]
    hold, K, BIG = WS.hold_of(cfg), cfg["K"], 1e7
    new = [dict(ch, dq=ch["dq"] - BIG) for ch in W2.chain_times(net, p, rows, quay, p["Lv"], p["B"], p["hd_s"] + BIG, S2.routes_of(D, cfg, net))]
    new = [ch for ch in new if ch["dq"] < -1e-6]
    if not new:
        return w
    chains = w["chains"] + new
    bm = w["bm"] + [min(K, W2.quay_side_Q(net, p, rows, quay, p["Lv"], p["B"], ch, hold)) for ch in new]
    Q = min(w["Q3"], W2.zone_Q(net, p, rows, quay, p["Lv"], p["B"], w["t"]["res"], hold, chains, K))
    return dict(BD.parts4(cfg, dict(w, P=replace(w["P"], Q=Q), chains=chains, bm=bm)), Q3=w["Q3"])


def reach(P, G, L, Lx, Sr, sh):
    """Corollary 9 (crane reach): X is the fleet, cut and quay-zone terms of bound.terms at window length Lx minus S; crane time
    uses L. With Lx = L the algorithm equals bound4.reach_R."""
    if Sr is None or P.S <= Sr:
        return math.inf
    tm = WB.terms(replace(P, L=Lx), G)
    X = min(tm[k] for k in ("fleet", "cut", "zone") if k in tm) - P.S
    nn = max(0, min(Sr + X, math.floor(L / P.p + EPS)))
    return nn + max(0, math.floor((L - nn * P.p) / (P.p + sh) + EPS))


def reserve(rp, S, K, G, L, p_lift, hp):
    """Corollary 10 (reserved periods): (window term, preparation term); (inf, inf) when rp is None. Same algorithm as the two
    terms of bound4.reserve_R."""
    if rp is None:
        return math.inf, math.inf
    lam = L - p_lift - rp["dq"]
    win = S + K + (B4.fit(G, G + lam, rp["wins"], rp["tl"]) + 1 if lam > EPS else 0)
    return win, B4.fit(hp, G + L - p_lift - rp["dq"], rp["wins"], rp["tl"])


def terms(w, L, empty=True):
    """Terms of W″(L) or W″_lift(L): dict(term → piles) ("prep" is the total of bound.prep and is not part of the minimum)."""
    P = w["P"]
    e = w.get("eps_u", 0.0)
    Lx = max(L - e, P.p) if e > 0 and L >= P.p - EPS else L
    w0 = dict(w, chains=[], bm=[])
    t = BD.terms4(w0, L, empty)
    t.pop("serial", None)
    if Lx != L:
        r = BD.terms4(w0, Lx, empty)
        t = dict({k: v for k, v in r.items() if k not in ("interface", "serial")}, interface=t["interface"])
    if empty:
        cap = math.floor(L / P.p + EPS) + 1
        t["serial"] = min((B4.prep_chain_fast(ch, P.K, bm, w["G"] + L, P.p, w["hp"], cap) for ch, bm in zip(w["chains"], w["bm"])),
                          default=math.inf)
    t["reach"] = reach(P, w["G"], L, Lx, w.get("Sr"), w.get("sh", 0.0))
    rw, rpre = reserve(w.get("rp"), P.S, P.K, w["G"], Lx, P.p, w["hp"])
    t["reserve"] = rw
    if empty:
        t["reserve_pre"] = rpre
    return {k: v for k, v in t.items() if v != math.inf}


def _fn(w):
    return lambda L: min(v for k, v in terms(w, L).items() if k != "prep")


def w2(cfg, w=None):
    """Closure of W″(L) under the original lifting semantics (L in seconds; window [G, G + L])."""
    return _fn(w or parts(cfg))


def w2_lift(cfg, w=None):
    """Closure of W″_lift(L) under the conservative lifting semantics."""
    return _fn(w or parts(cfg, lift=True))


def binding(t):
    """(bound, binding terms, binding class, subclass): "prep" (preparation time) when all binding terms are strictly below the
    window terms, otherwise the first of crane, cradle turnover, fleet, road (same order as bound4.classify); the subclass
    lists the binding preparation terms. Also returns a classification "by nature": preparation time with Π_F only goes to
    fleet, the rest to road."""
    t = {k: v for k, v in t.items() if k != "prep"}
    v = min(t.values())
    keys = sorted(k for k, x in t.items() if x == v)
    win = min((x for k, x in t.items() if k not in PREP), default=math.inf)
    if v < win:
        cls = "prep"
    else:
        cls = next(c for c in ("crane", "cradle", "fleet", "road") if any(CLASS[k] == c for k in keys if k not in PREP))
    sub = "+".join(k for k in keys if k in PREP) if cls == "prep" else ""
    nature = cls if cls != "prep" else ("fleet" if "prep_fleet" in keys else "road")
    return v, keys, cls, sub, nature
