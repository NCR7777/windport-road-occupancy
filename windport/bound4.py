"""W′ with two extra terms (crane reach, reserved periods on a shared road segment) and the five binding classes.
Statements and proofs: see the manuscript.

Window [G, G + L]; W′(L) is windport.bound3.wprime_fn (geometric quay zone Q, return-trip correction, serial-cut
preparation term).
1. Crane reach (Corollary 7): a lift at quay position k ≥ S_r takes p + t_sh per pile. The fleet, cut and quay-zone
   terms of W1 all have the form S + X_j, where X_j bounds the number of handovers (placed on a cradle or lifted from a
   vehicle) after the window start; X = min_j X_j. The number of reachable lifts N_n ≤ S_r + X and
   N_n·p + N_f·(p + t_sh) ≤ L, hence N ≤ R(L) = N_n* + ⌊(L − N_n*·p)/(p + t_sh)⌋, N_n* = min(S_r + X, ⌊L/p⌋)⁺
   (N_n + ⌊(L − N_n·p)/(p + t_sh)⌋ is non-decreasing in N_n). Not added when S ≤ S_r.
2. Reserved periods on a shared segment (Corollary 8; the shared cut of Theorem 4 with a fixed reservation table): each
   loaded vehicle occupies segment c exclusively for at least t_ℓ^c, and needs at least d_q^c from leaving c to handover;
   no vehicle may occupy c during a reserved period R. A monopile lifted aboard within the window is either on a cradle at
   the window start (≤ S), on a loaded vehicle on the quay side of c (≤ K), or its loaded pass leaves c within
   (G, G + Λ], Λ = L − p − d_q^c. These passes are pairwise disjoint, at most one spans G, and each lies entirely in one
   open piece: m − 1 ≤ Σ_k ⌊ℓ_k / t_ℓ^c⌋, with ℓ_k the lengths of the open pieces of (G, G + Λ] after removing R
   (rounded per piece; the total open time would be looser). From an empty system: all passes lie in
   [h_p, G + L − p − d_q^c], m ≤ the same per-piece sum. Both are non-decreasing in L.
W″(L) = min{W′(L), R(L), the two reserved-period terms} is non-decreasing in L, so windport.bound3.lstar applies
unchanged.
3. Five binding classes: crane (interface), cradle turnover (turnover), fleet (fleet), road (cut, zone, serial cut Π_S), and
   preparation time (preparation term strictly binding: W′ below all window terms); the preparation class is further split
   (Π_F fleet, Π_C cut, Π_Z quay zone, Π_S serial cut). Ties go to the first of crane, turnover, fleet, road."""
import math
from dataclasses import replace

from windport import bound as WB
from windport import bound2 as W2
from windport import bound3 as B3
from windport import sim as WS

EPS = 1e-9


def open_len(a, b, wins):
    """Length of [a, b] after removing the reserved periods wins."""
    if b <= a:
        return 0.0
    return (b - a) - sum(max(0.0, min(b, y) - max(a, x)) for x, y in wins)


def open_pieces(a, b, wins):
    """Lengths of the open pieces of [a, b] after removing the (disjoint) reserved periods wins."""
    out, t = [], a
    for x, y in sorted(wins):
        if y <= t or x >= b:
            continue
        if x > t:
            out.append(min(x, b) - t)
        t = max(t, y)
        if t >= b:
            break
    if t < b:
        out.append(b - t)
    return out


def fit(a, b, wins, tl):
    """Each pass lies entirely in one open piece: [a, b] holds at most Σ_k ⌊ℓ_k / tl⌋ pairwise disjoint passes of length ≥ tl."""
    return sum(math.floor(x / tl + EPS) for x in open_pieces(a, b, wins))


def reach_R(P, G, L, Sr, sh):
    """R(L) of Corollary 7; inf when S ≤ S_r."""
    if Sr is None or P.S <= Sr:
        return math.inf
    tm = WB.terms(replace(P, L=L), G)
    X = min(tm[k] for k in ("fleet", "cut", "zone") if k in tm) - P.S
    nn = max(0, min(Sr + X, math.floor(L / P.p + EPS)))
    return nn + max(0, math.floor((L - nn * P.p) / (P.p + sh) + EPS))


def reserve_parts(cfg, net, p, D):
    """Parameters of the reserved periods: dict(tl, dq, wins, res) or None."""
    from windport import sim4 as S4
    rv = S4.reserve_of(cfg, D, net, p)
    if rv is None:
        return None
    W = D["windport"]
    lift = "direct" if cfg["S"] == 0 else cfg.get("lift", "cradle")
    pt = dict(p, load_s=p["hp_s"], unload_s=0.0 if lift in ("direct", "mixed") else p["hd_s"])
    t = WB.occupancy_times(net, pt, W["storage"], W["cradles"][:max(1, cfg["S"])], p["Lv"], p["B"], cut=rv["res"][0])
    return dict(tl=t["tl"], dq=t["dq"], wins=rv["wins"], res=rv["res"][0])


def reserve_R(rp, S, K, G, L, p_lift, hp):
    """Minimum of the two terms of Corollary 8; inf when rp is None."""
    if rp is None:
        return math.inf
    tl, dq, wins = rp["tl"], rp["dq"], rp["wins"]
    lam = L - p_lift - dq
    win = S + K + (fit(G, G + lam, wins, tl) + 1 if lam > EPS else 0)
    pre = fit(hp, G + L - p_lift - dq, wins, tl)
    return min(win, pre)


def parts4(cfg):
    from windport import sim4 as S4
    D, net, p, *_ = S4.setup4(cfg)
    w = B3.wprime_parts(cfg)
    w["Sr"], w["sh"] = p.get("reach"), float(p.get("shift_s") or 0.0)
    w["rp"] = reserve_parts(cfg, net, p, D)
    return w


def prep_chain_fast(ch, K, bmax, b_end, p_lift, hp, cap):
    """Same value as windport.bound3.prep_chain_c, using bisection instead of counting one by one: f_min(m) is non-decreasing in m
    (removing one trip from an optimal phase plan for m + 1 trips, or using m phases instead of m + 1, stays feasible; each phase
    Φ(b) is non-decreasing in b; the number of down trips does not increase), so "f_min(m) ≤ D" is true then false in m and the
    largest m can be bisected."""
    D = b_end - p_lift - ch["dq"] - hp - ch["start0"]
    ok = lambda m: W2.f_min(m, K, bmax, ch["up"], ch["down"]) <= D + 1e-9
    if cap <= 0 or not ok(1):
        return 0
    if ok(cap):
        return cap
    lo, hi = 1, cap                     # ok(lo), not ok(hi)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


def wprime_fast(cfg, w):
    """W′(L) with the same value as windport.bound3.wprime_fn; the serial-cut preparation term uses prep_chain_fast (tests check
    equality point by point)."""
    P2, G, K = w["P"], w["G"], cfg["K"]

    def f(L):
        b2 = WB.bound(replace(P2, L=L), G)[0]
        cap = math.floor(L / P2.p + 1e-9) + 1
        pi = min((prep_chain_fast(ch, K, b, G + L, P2.p, w["hp"], cap) for ch, b in zip(w["chains"], w["bm"])), default=math.inf)
        return min(b2, pi)
    return f


def wprime4_fn(cfg, w=None):
    """Closure of W″(L) (L in seconds)."""
    w = w or parts4(cfg)
    f3 = wprime_fast(cfg, w)
    P, G, K = w["P"], w["G"], cfg["K"]

    def f(L):
        return min(f3(L), reach_R(P, G, L, w["Sr"], w["sh"]), reserve_R(w["rp"], P.S, K, G, L, P.p, w["hp"]))
    return f


def bound4(cfg):
    """W″ and its parts on the window of cfg: dict(bound, wprime, reach, reserve)."""
    w = parts4(cfg)
    L = (cfg["cal"]["crane"][0][1] - cfg["cal"]["crane"][0][0]) * 3600.0
    P, G = w["P"], w["G"]
    wp = wprime_fast(cfg, w)(L)
    r = reach_R(P, G, L, w["Sr"], w["sh"])
    rv = reserve_R(w["rp"], P.S, cfg["K"], G, L, P.p, w["hp"])
    return dict(bound=min(wp, r, rv), wprime=wp, reach=None if r == math.inf else r, reserve=None if rv == math.inf else rv)


# ---------------------------------------------------------------- five binding classes
CLASSES = ("crane", "turnover", "fleet", "road", "prep")


def prep_parts(P, b):
    """The three parts of windport.bound.prep (fleet Π_F, cut Π_C, quay zone Π_Z), same algorithm line by line."""
    P = WB._mixed(P)
    D = b - P.p
    first = P.c - P.ce
    fleet = 0 if D < first - EPS else P.K * (math.floor((D - first) / P.c + EPS) + 1)
    Dc = D - P.dq - P.hp
    q = min(P.K, P.Q)
    m = 0
    while Dc >= -EPS and P.tl * (m + 1) + P.te * max(0, m + 1 - q) <= Dc + EPS:
        m += 1
    if q == 1:
        f1 = P.hp + P.tl + P.dq
        zone = 0 if D < f1 - EPS else math.floor((D - f1) / (P.tl + P.dq + WB.te_full(P)) + EPS) + 1
    else:
        zone = math.floor(q * max(0.0, D - P.hp) / (P.tl + P.dq) + EPS)
    return dict(prep_fleet=fleet, prep_cut=m, prep_zone=zone)


def classify(cfg, w=None):
    """Binding term of W′ and the five binding classes on the window of cfg: dict(wprime, terms, binding, cls, sub).
    terms holds the window terms (interface, turnover, fleet, cut, zone), the three parts of the preparation term, and
    the serial cut serial."""
    w = w or B3.wprime_parts(cfg)
    P, G, K = w["P"], w["G"], cfg["K"]
    L = (cfg["cal"]["crane"][0][1] - cfg["cal"]["crane"][0][0]) * 3600.0
    tm = WB.terms(replace(P, L=L), G)
    win = {k: v for k, v in tm.items() if k != "prep"}
    pp = prep_parts(replace(P, L=L), G + L)
    assert min(pp.values()) == tm["prep"], (pp, tm["prep"])
    cap = math.floor(L / P.p + 1e-9) + 1
    ser = min((B3.prep_chain_c(ch, K, b, G + L, P.p, w["hp"], cap) for ch, b in zip(w["chains"], w["bm"])), default=math.inf)
    allt = dict(win, **pp, serial=ser)
    v = min(allt.values())
    binding = [k for k, x in allt.items() if x == v]
    group = dict(interface="crane", turnover="turnover", fleet="fleet", cut="road", zone="road")
    wmin = min(win.values())
    if v < wmin:
        cls = "prep"
        sub = "+".join(dict(prep_fleet="Π_F", prep_cut="Π_C", prep_zone="Π_Z", serial="Π_S")[k] for k in binding)
    else:
        cls = next(c for c in ("crane", "turnover", "fleet", "road") if any(group.get(k) == c for k in binding))
        sub = ""
    nature = cls if cls != "prep" else ("fleet" if binding == ["prep_fleet"] or "prep_fleet" in binding else "road")
    return dict(wprime=v, terms={k: (None if x == math.inf else x) for k, x in allt.items()}, binding="+".join(binding), cls=cls, sub=sub, nature=nature)
