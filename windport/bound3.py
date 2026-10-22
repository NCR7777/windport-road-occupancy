"""Port-time lower bound derived from the window bound W′, and a Muhabie-type single-server representation
(windport/bound.py, bound2.py and sim2.py are unchanged).

1. W′ is non-decreasing in the window length L (G and the other parameters fixed). W′ = min{terms of W1 (geometric quay
   zone Q), preparation term, chain-cut preparation term Π_S}, and L enters in only three places: the interface term
   ⌊L/p⌋; D = L − p in the other window terms (turnover ⌊D/hd⌋ + 1, fleet n(D), cut max_k[k + M(D − dq, q − k)], quay
   zone); and the deadline b = G + L of the preparation term and Π_S. Each term is a non-decreasing function of these
   quantities (rounding and "the largest m with f(m) ≤ D" are non-decreasing in D), all terms are 0 for D < 0, and the
   minimum of non-decreasing functions is non-decreasing. The quay zone Q, the chains and threshold, t_ℓ, t_e, c, d_q do
   not depend on L.
2. Port-time lower bound (valid for any dispatching rule on fixed routes): the crane opens at G; if the n-th pile is
   finished at G + T_n, the first n lifts lie entirely in [G, G + T_n], so W′(T_n) ≥ n, and by 1, T_n ≥ L*(n) =
   inf{L : W′(L) ≥ n}. lstar finds L* by bisection and returns (lo, hi) with W′(lo) < n ≤ W′(hi), hi − lo ≤ tol;
   lo is the reportable lower bound (T_n > lo).
3. Muhabie-type single server: in-port handling is one server with a fixed time h per pile, independent of the number of
   vehicle sets; S cradles (with S = 0 the server holds the pile until the lift starts); the crane lifts one pile at a time
   from G, p per pile. muhabie_port gives the time at which n piles are lifted, minus G; muhabie_h finds the largest h that
   makes it equal to a given port time (calibration).
4. Corrections: the return occupation is the minimum over the return patterns (wprime_parts); the chain-cut preparation
   term counts up to ⌊L/p⌋ + 1 only (prep_chain_c)."""
import math
from dataclasses import replace

from windport import bound as WB
from windport import bound2 as W2
from windport import sim as WS
from windport import sim2 as S2


def return_occ(net, p, routes, cut, first=False):
    """Minimum over the return patterns between two up-trips (windport.sim2.routes_of: leave to the yard side or the
    off-site waiting area, then back to a saddle row; or leave to the gate holding place, then from the gate back to a
    saddle row) of the occupation of cut: first = False sums the wait-free windows of all empty legs (cut term); first =
    True takes the first window on the cut along the pattern (quay-zone term: the first time a vehicle passes the cut it is
    on the yard side and out of the quay zone; when the gate holding place is on the quay side of the cut, this window lies
    on the "gate → saddle row" leg, and a vehicle in the holding place still counts as in the quay zone).
    0 when a pattern does not pass the cut; inf when there is no pattern."""
    cap, size = net.capacities(p)
    best = math.inf
    for route in routes:
        tot = 0.0
        for s, d in route:
            if s == d:
                continue
            _, st, uses, _ = net.leg(s, d, p["v_empty"], p["plat_len"], p["plat_w"], False, p, cap, size, ("x",), 0.0, True)
            ws = sorted((st[a], st[r] + dl) for res, _, a, r, dl in uses if r is not None and res == cut)
            if first and ws:
                tot = ws[0][1] - ws[0][0]
                break
            tot += sum(e - b for b, e in ws)
        best = min(best, tot)
    return best


def wprime_parts(cfg):
    """Parts of W′ that do not depend on the window length: dict(P = Port with geometric quay-zone Q and corrected return
    occupation, t = occupancy_times, G, chains, bm = b_max of each chain, hp, te_occ0 / te0 = return occupation before
    correction).
    Correction: windport.bound.occupancy_times takes the return occupation t_e, t_e^occ from the direct "quay stop → saddle
    row" leg; in the simulation a vehicle, after release, first leaves to the yard side (or the off-site waiting area) or to
    the gate holding place, and with Q_h ≥ 1 the leg towards the gate can be shorter on the cut (e.g. road_trace_206: 324 s
    vs 530 s), so the q = 1 quay-zone term and the preparation term could be exceeded. Here t_e^occ of the quay-zone and
    preparation terms is min(original, smallest first-cut-passage window over the patterns) (a vehicle past the cut is out
    of the quay zone); t_e of the cut term is min(original, smallest total cut occupation over the patterns / q_e).
    Smaller return occupations shorten the spacing in the quay-zone and cut terms, so they can only raise (loosen) the
    bound; for archetypes whose return patterns occupy the cut equally (A1 etc.) the bound is unchanged."""
    D, net, p, *_ = S2.setup2(cfg)
    W = D["windport"]
    S, K = cfg["S"], cfg["K"]
    lift = "direct" if S == 0 else cfg.get("lift", "cradle")
    P, t = WS.w1_port(cfg, D, net, p)
    G = cfg["cal"]["crane"][0][0] * 3600.0
    rows, quay = W["storage"], W["cradles"][:max(1, S)]
    hold = WS.hold_of(cfg)
    unload = bool(cfg.get("n_unload"))
    routes = S2.routes_of(D, cfg, net)
    chains = W2.chain_times(net, p, rows, quay, p["Lv"], p["B"], 0.0 if lift in ("direct", "mixed") else p["hd_s"], routes)
    Q = K if unload else W2.zone_Q(net, p, rows, quay, p["Lv"], p["B"], t["res"], hold, chains, K)
    bm = [min(K, math.inf if unload else W2.quay_side_Q(net, p, rows, quay, p["Lv"], p["B"], ch, hold)) for ch in chains]
    occ0 = WB.te_full(P)
    low = lambda x: x if x < occ0 - 1e-6 else occ0                              # change only when really smaller (not on rounding)
    occ = low(return_occ(net, p, routes, t["res"], first=True))                 # quay-zone term: previous vehicle passes the cut, leaves the zone
    tot = low(return_occ(net, p, routes, t["res"]))                             # cut term: full cut occupation of one return
    te = P.te if P.te <= 0 or occ0 <= 0 else P.te * tot / occ0
    return dict(P=replace(P, Q=Q, te=te, te_occ=occ), t=t, G=G, chains=chains, bm=bm, hp=p["hp_s"], te_occ0=occ0, te0=P.te)


def prep_chain_c(ch, K, bmax, b_end, p_lift, hp, cap):
    """As windport.bound2.prep_chain, but counts only up to cap (cap = ⌊L/p⌋ + 1 exceeds the interface term, so the minimum
    in W′ is unchanged); the original raises an error past 10⁴ in long windows, this one does not."""
    D = b_end - p_lift - ch["dq"] - hp - ch["start0"]
    m = 0
    while m < cap and W2.f_min(m + 1, K, bmax, ch["up"], ch["down"]) <= D + 1e-9:
        m += 1
    return m


def wprime_fn(cfg, w=None):
    """Closure W′(L) (L in seconds; window [G, G + L], G = start of the crane window in cfg). Same algorithm as
    windport.sim2.bounds2 with L as an argument, plus the return correction of wprime_parts; without a correction and with L
    = the window length of cfg it equals the bound of bounds2, with a correction it can only be larger (checked by the
    tests and the wfn item of the random regression)."""
    w = w or wprime_parts(cfg)
    P2, G, K = w["P"], w["G"], cfg["K"]

    def f(L):
        b2 = WB.bound(replace(P2, L=L), G)[0]
        cap = math.floor(L / P2.p + 1e-9) + 1
        pi = min((prep_chain_c(ch, K, b, G + L, P2.p, w["hp"], cap) for ch, b in zip(w["chains"], w["bm"])), default=math.inf)
        return min(b2, pi)
    return f


def bounds2c(cfg):
    """Corrected W′ (window of cfg) and the return occupation before and after correction: dict(bound, te_occ0, te_occ,
    te0, te)."""
    w = wprime_parts(cfg)
    L = (cfg["cal"]["crane"][0][1] - cfg["cal"]["crane"][0][0]) * 3600.0
    f = wprime_fn(cfg, w)
    return dict(bound=f(L), te_occ0=w["te_occ0"], te_occ=w["P"].te_occ, te0=w["te0"], te=w["P"].te)


def lstar(f, n, tol=1e-3, hi0=3600.0):
    """L*(n) = inf{L : f(L) ≥ n} (f non-decreasing): returns (lo, hi) with f(lo) < n ≤ f(hi), hi − lo ≤ tol (seconds).
    (0, 0) for n ≤ 0."""
    if n <= 0:
        return 0.0, 0.0
    lo, hi = 0.0, hi0
    while f(hi) < n:
        lo, hi = hi, 2 * hi
        if hi > 1e9:
            raise AssertionError("W′ never reaches n: does the bound not grow with the window?")
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < n else (lo, mid)
    return lo, hi


def muhabie_port(n, S, h, p, G):
    """Single server, S cradles, crane from G: time at which the n-th pile is lifted, minus G (seconds). The server carries
    piles one by one from time 0, h each; on delivery it puts the pile down if a cradle is free and immediately takes the
    next one, otherwise it holds and waits (a cradle is freed when its lift starts); with S = 0 it holds until the lift
    starts. The crane lifts in order: lift start = max(G, pile in place, previous lift finished)."""
    free, lifts, s_prev = 0.0, [], -math.inf
    for j in range(n):
        d = free + h
        if S == 0:
            s = max(G, d, s_prev + p)
            free = s                                  # server released at lift start (as direct lift x = 0)
        else:
            place = d if j < S else max(d, lifts[j - S])
            free = place
            s = max(G, place, s_prev + p)
        lifts.append(s)
        s_prev = s
    return s_prev + p - G


def muhabie_h(n, S, p, G, target, tol=1e-3):
    """Largest h (seconds) with muhabie_port(n, S, h, p, G) ≤ target (port time is non-decreasing in h). Returns None if
    target is below the value at h = 0."""
    if muhabie_port(n, S, 0.0, p, G) > target + 1e-9:
        return None
    lo, hi = 0.0, 3600.0
    while muhabie_port(n, S, hi, p, G) <= target + 1e-9:
        lo, hi = hi, 2 * hi
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if muhabie_port(n, S, mid, p, G) <= target + 1e-9 else (lo, mid)
    return lo
