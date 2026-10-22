"""W1: upper bound on the number of units delivered within a load-out window (statement and proof in the manuscript).

Loading direction. Window [a, b], L = b − a; the crane lifts one pile at a time only inside the window, each lift takes p and
must lie entirely inside the window; when a lift starts, the monopile must be on a quay cradle (cradle mode, S ≥ 1), or on a
loaded vehicle parked on the quay side (direct lift, S = 0, the vehicle is released when the lift starts). K SPMT sets.
Cut: every loaded trip must occupy one resource exclusively over its whole passage (the single-lane corridor), for tl; an
empty return trip that also uses it occupies it for te (te = 0 when the loop return does not use it).
c: minimum time between two consecutive handovers of one vehicle (cradle mode: placement complete; direct lift: lift start)
(pickup + loaded travel + placement + empty return).
dq: minimum time from leaving the cut (end of the occupation of the cut) to completing the handover (cradle mode includes
placement hd). Q: number of vehicles that can stand on the quay side (beyond the cut) at the same time.

Terms (each holds for any schedule, so their minimum is an upper bound; proofs in the manuscript):
  interface  ⌊L/p⌋                                        crane lifts one pile at a time
  turnover   S·(⌊(L−p)/hd⌋ + 1)                            cradle turnover (inactive when hd ≤ p)
  fleet      S + K·n(L − p)                                  handover interval of each vehicle ≥ c; n(Δ) = ⌈Δ/c⌉ (cradle),
                                                             ⌊Δ/c⌋ + 1 (direct lift)
  cut        S + max_{k ≤ q} [k + M(L − p − dq, q − k)], q = min(K, Q)
             M(Δ, y) = 0 (Δ ≤ 0), otherwise the largest m with tl·(m − [y ≥ 1]) + te·(m − y)⁺ ≤ Δ   (exclusive cut; the
             k vehicles on the quay side are on-vehicle buffers; for the q − k free places in the quay zone, a vehicle
             entering the zone need not wait for one to leave and return, and a trip straddling the window start also
             takes one place in the quay zone. Using K − k instead of q − k is too loose when 1 < Q < K and te > 0)
  zone       S + q + ⌊q·(L − p)/(tl + dq)⌋, q = min(K, Q)          at most Q vehicles in the quay zone (beyond the cut),
                                                                    each handover spends at least tl + dq in the zone;
             for q = 1: S + n(L − p) with interval tl + dq + te      listed only when tighter than fleet
  prep       cumulative transport from an empty system with a preparation time G before the window (all vehicles empty
             on the yard side, cradles empty)
Mixed lifting (mixed = True: in cradle mode the crane can also lift from a vehicle; Corollary 2 of the manuscript): c becomes
c − hd, dq = 0, counting on a closed interval, turnover dropped, S kept.
"""
import math
from dataclasses import dataclass, replace

EPS = 1e-9


@dataclass(frozen=True)
class Port:
    L: float            # window length
    p: float            # crane cycle per pile
    S: int              # number of quay cradles (0 = direct lift from the vehicle)
    K: int              # number of SPMT sets
    hp: float           # pickup at the yard
    hd: float           # placement onto a cradle (0 for direct lift)
    tl: float           # occupation of the cut by a loaded trip
    te: float           # occupation of the cut by an empty return (0 when the return avoids the cut)
    c: float            # lower bound on a vehicle's handover interval
    ce: float           # its empty-return part (c − ce is pickup + loaded + placement; from an empty system the first
                        # handover needs no return)
    dq: float           # lower bound from leaving the cut to completing the handover
    Q: int              # number of vehicles that can stand on the quay side
    mixed: bool = False  # in cradle mode the crane can also lift from a vehicle (Corollary 2)
    te_occ: float = None  # full occupation of the cut by one return (not divided by qe); used by the q = 1 zone term.
                          # None = te

    @property
    def direct(self):
        return self.S == 0


def lane(L, p, S, K, hp, hd, tl, te, er=0.0, Q=None, qe=1, mixed=False):
    """Small instance with only the cut and the handling (the model of windport.exact): the whole loaded trip is the cut
    passage; the return uses the cut when te > 0, and the loop with duration er when te = 0.
    qe: maximum number of empty vehicles on the cut at once when no loaded one is there; the cut term counts a return as
    te / qe (its duration is still te)."""
    hd = 0.0 if S == 0 else hd
    ce = te if te > 0 else er
    return Port(L=L, p=p, S=S, K=K, hp=hp, hd=hd, tl=tl, te=te / qe, c=hp + tl + hd + ce, ce=ce, dq=hd,
                Q=K if Q is None else min(Q, K), mixed=mixed and S > 0, te_occ=te)


def te_full(P):
    return P.te if P.te_occ is None else P.te_occ


def _mixed(P):
    """Mixed lifting is counted like direct lift: a handover is placement complete or lift start, two consecutive ones are
    ≥ c − hd apart, and a vehicle can hand over as soon as it leaves the cut (dq = 0). After conversion mixed is set to
    False (the conversion is done once)."""
    return replace(P, c=P.c - P.hd, dq=0.0, mixed=False) if P.mixed else P


def n_fleet(D, c, closed):
    """Maximum number of handovers of one vehicle in an interval of length D, at least c apart. closed: the interval
    includes its left end (direct lift, a lift may start at the window start)."""
    if D < -EPS:
        return 0
    if closed:
        return math.floor(D / c + EPS) + 1
    return 0 if D <= EPS else math.ceil(D / c - EPS)


def M(D, ky, tl, te):
    """Maximum number of loaded trips whose cut departure falls in (a, a + D]: of m trips at most one straddles a (only
    if some vehicle is not on the quay side, ky ≥ 1), the rest lie inside the interval; each loaded trip of a vehicle on
    the quay side needs one empty return first, the first trip of the other ky vehicles does not."""
    if D <= EPS:
        return 0
    s = 1 if ky >= 1 else 0
    m = 0
    while tl * (m + 1 - s) + te * max(0, m + 1 - ky) <= D + EPS:
        m += 1
    return m


def terms(P, G=None):
    """Terms of W1 (units); with G given, prep is added."""
    assert P.tl > 0 and P.p > 0, "loaded occupation of the cut and crane cycle must be positive"
    mixed, closed = P.mixed, P.direct or P.mixed
    P = _mixed(P)
    D = P.L - P.p
    out = dict(interface=math.floor(P.L / P.p + EPS))
    if D < -EPS:
        return dict(out, turnover=0, fleet=0, cut=0) if G is None else dict(out, turnover=0, fleet=0, cut=0, prep=0)
    out["turnover"] = P.S * (math.floor(D / P.hd + EPS) + 1) if P.S and P.hd > EPS and not mixed else math.inf
    out["fleet"] = P.S + P.K * n_fleet(D, P.c, closed)
    kmax = min(P.K, P.Q)
    out["cut"] = P.S + max(k + M(D - P.dq, kmax - k, P.tl, P.te) for k in range(kmax + 1))
    # One vehicle in the quay zone at a time: the next enters only after this one has started and cleared its return over
    # the cut (full occupation te_occ); consecutive handovers ≥ tl + dq + te_occ
    if kmax == 1:
        out["zone"] = P.S + n_fleet(D, P.tl + P.dq + te_full(P), closed)
    else:
        out["zone"] = P.S + kmax + math.floor(kmax * D / (P.tl + P.dq) + EPS)
    if out["zone"] >= out["fleet"]:
        del out["zone"]                     # quay zone not listed when it is not tighter than the fleet (always so for Q ≥ K)
    if G is not None:
        out["prep"] = prep(P, G + P.L)
    return out


def prep(P, b):
    """Upper bound on the units lifted aboard by time b, starting from an empty system (time 0: all vehicles empty on the
    yard side, cradles and quay side empty): each pile must be handed over before b − p. Fleet: first handover ≥ c − te_r
    (pickup + loaded + placement), then every c; cut: no trip straddling the start and no vehicle on the quay side,
    tl·m + te·(m − q)⁺ ≤ b − p − dq − hp (q = min(K, Q): every zone entry after the q-th needs one exit-and-return first)."""
    assert P.tl > 0, "loaded occupation of the cut must be positive"
    P = _mixed(P)
    D = b - P.p
    first = P.c - P.ce                     # the first handover needs no return
    fleet = 0 if D < first - EPS else P.K * (math.floor((D - first) / P.c + EPS) + 1)
    Dc = D - P.dq - P.hp
    q = min(P.K, P.Q)
    m = 0
    while Dc >= -EPS and P.tl * (m + 1) + P.te * max(0, m + 1 - q) <= Dc + EPS:
        m += 1
    if q == 1:
        f1 = P.hp + P.tl + P.dq
        zone = 0 if D < f1 - EPS else math.floor((D - f1) / (P.tl + P.dq + te_full(P)) + EPS) + 1
    else:
        zone = math.floor(q * max(0.0, D - P.hp) / (P.tl + P.dq) + EPS)
    return min(fleet, m, zone)


def bound(P, G=None):
    """W1 = minimum of the terms; returns (bound, binding terms)."""
    t = terms(P, G)
    v = min(t.values())
    return v, [k for k, x in t.items() if x == v]


def periodic(P, G, T, n):
    """Upper bound on the units lifted aboard over n periodic windows (from an empty system, window i is
    [G + iT, G + iT + L], i = 0 … n−1): each window is at most the single-window bound u, and the first i windows together
    at most the cumulative transport prep up to the end of window i. Maximum sum under prefix caps and per-window caps
    = min_i (prep_i + Σ_{j > i} u), prep_0 = 0."""
    u = bound(P)[0]
    caps = [0] + [prep(P, G + i * T + P.L) for i in range(n)]
    return min(caps[i] + (n - i) * u for i in range(n + 1))


def rate(P):
    """Long-run transport rate r = min(K/c, 1/(tl + te)) (units per unit time); with period T the long-run average per
    window is ≤ min(⌊L/p⌋, single-window bound, T·r)."""
    assert P.tl > 0
    return min(P.K / P.c, 1.0 / (P.tl + P.te))


def k_dagger(P):
    """Fleet plateau K† = c / (tl + te): beyond it the long-run transport rate no longer grows with K."""
    assert P.tl > 0
    return P.c / (P.tl + P.te)


def s_star(P):
    """Buffer limit S* (cradle mode): beyond S* cradles the interface term binds and more cradles do not help. Computed from
    the single-window terms: the smallest S ≥ 1 for which all other terms (turnover, fleet, cut, quay zone) are
    ≥ interface."""
    I = terms(P)["interface"]
    for S in range(1, I + 1):
        t = terms(replace(P, S=S))
        if min(v for k, v in t.items() if k != "interface") >= I:
            return S
    return max(I, 1)


# ---------------------------------------------------------------- unloading (Theorem 3); loading and unloading on one cut (Theorem 4)
def m_u(D, K, tl, te):
    """Maximum number of loaded cut passages towards the yard starting in [a + ρ, b) (length D): pairwise disjoint, at
    most one straddles b, and two consecutive trips of one vehicle need a return between them (≥ m − K returns)."""
    if D <= EPS:
        return 0
    m = 1
    while tl * m + te * max(0, m + 1 - K) <= D + EPS:
        m += 1
    return m


def unload_terms(L, rho, K, c_u, tl, te, Su=0, Q=None):
    """Theorem 3: ramp operations completed within a window of length L ≤ min{ramp ⌊L/ρ⌋, fleet K·(⌊(L − ρ)/c_u⌋ + 1),
    cut S_u + q + M_u(L − ρ)}.
    c_u: lower bound on the interval between two consecutive ramp-operation starts of one vehicle; tl, te: occupation of
    the cut by a loaded trip to the yard and an empty trip to the quay."""
    if L < rho - EPS:
        return dict(ramp=0, fleet=0, cut=0)
    q = K if Q is None else min(K, Q)
    D = L - rho
    return dict(ramp=math.floor(L / rho + EPS), fleet=K * (math.floor(D / c_u + EPS) + 1), cut=Su + q + m_u(D, K, tl, te))


def joint_gap(No, Nu, S, Su, q, K, tl_o, tl_u, te_q, te_y, Io, Iu):
    """Joint polyhedron of Theorem 4: returns right-hand side − left-hand side (≥ 0 means satisfied). x = (N_o − S − q)⁺,
    y = (N_u − S_u − q)⁺ are the minimum numbers of cut passages of the two flows; Io = (a_o, b_o − p − dq) is the interval
    in which the loading passages must end, Iu = (a_u + ρ, b_u) the interval in which the unloading passages must start, and
    J is the convex hull of the non-empty ones.
    Left: tl_o·x + tl_u·y + te_y·(x − y − K)⁺ + te_q·(y − x − K)⁺; right: |J| + 2·max(tl_o, tl_u) (at most two loaded trips
    straddling the ends of J)."""
    x, y = max(0, No - S - q), max(0, Nu - Su - q)
    ends = [I for I, n in ((Io, x), (Iu, y)) if n > 0]
    if not ends:
        return float("inf")
    J = max(b for _, b in ends) - min(a for a, _ in ends)
    lhs = tl_o * x + tl_u * y + te_y * max(0, x - y - K) + te_q * max(0, y - x - K)
    return J + 2 * max(tl_o, tl_u) - lhs


def port(t, L, p, S, K, Q=None):
    """Result t of occupancy_times plus window and configuration → Port (cradle mode, S ≥ 1)."""
    assert S >= 1, "parameters from the road-occupancy model are only derived for cradle mode"
    return Port(L=L, p=p, S=S, K=K, hp=t["hp"], hd=t["hd"], tl=t["tl"], te=t["te"], c=t["c"], ce=t["ce"], dq=t["dq"],
                Q=K if Q is None else min(Q, K), te_occ=t.get("te_occ"))


# ---------------------------------------------------------------- parameters from the road-occupancy model (occupancy.Net)
def occupancy_times(net, p, stops_o, stops_d, Lv, B, cut=None):
    """Parameters of the loading task (yard stops stops_o → quay cradle stops stops_d) in the road-occupancy model, from the
    wait-free occupation windows of Net.leg, minimised over all (origin, destination) pairs (smaller is looser, so the bound
    still holds).
    Cut: a resource on the loaded leg that cannot hold two loaded vehicles (Net.demand); without cut, the one passed by all
    loaded legs with the largest tl + te. The return counts if all empty legs pass it and an empty and a loaded vehicle
    cannot share it: at most qe empty vehicles in parallel, te = empty occupation / qe; otherwise te = 0. The road holding a
    roadside cradle (cradle_mode = "on_road") is also a candidate: its loaded occupation runs from entering it to placement
    complete (then dq = 0). Each row's loaded window on the cut is truncated at the handover (TL + unload_s).
    Returns dict(res, tl, te, te_occ, c, ce, dq, hd, hp); valid for the fixed shortest routes (Net.path); if routes can
    vary, the cut must be a cut of the graph."""
    cap, size = net.capacities(p)
    rows = []
    for o in stops_o:
        for d in stops_d:
            so, sd = net.stops[o], net.stops[d]
            d_sd = net.demand(sd["res"], B, True, p, cap)
            TL, stL, uL, _ = net.leg(so["node"], sd["node"], p["v_loaded"], Lv, B, True, p, cap, size, sd["res"], d_sd)
            d_so = net.demand(so["res"], p["plat_w"], False, p, cap)
            TE, stE, uE, _ = net.leg(sd["node"], so["node"], p["v_empty"], p["plat_len"], p["plat_w"], False, p, cap, size,
                                     so["res"], d_so, True)
            occ = lambda st, uses: {r: (st[a], st[rr] + dl, d) for r, d, a, rr, dl in uses if rr is not None}
            oL = occ(stL, uL)
            if sd["res"][0] == "r":           # roadside cradle: road held during placement, released at placement complete (handover)
                a = next(st_a for r, _, st_a, rr, _ in uL if r == sd["res"] and rr is None)
                oL[sd["res"]] = (stL[a], TL + p["unload_s"], d_sd)
            # A "passage" is truncated at the handover: the tail window or the junction sweep window can outlast the
            # handover (stop closer to the junction than the vehicle-plus-cargo length, sweep holding the other arms);
            # after the handover the vehicle is released and may drive back over this road. The truncated sub-interval is
            # still exclusive, so the proof holds and dq is never truncated to 0
            hand = TL + p["unload_s"]
            oL = {r: (s0, min(e0, hand), w) for r, (s0, e0, w) in oL.items() if min(e0, hand) > s0 + EPS}
            rows.append((oL, occ(stE, uE), TL, TE, o))
    cand = [cut] if cut else sorted(set.intersection(*(set(x[0]) for x in rows)), key=str)
    best = None
    for r in cand:
        dl = max(w[2] for x in rows for w in [x[0][r]])
        de = [x[1][r][2] for x in rows if r in x[1]]
        if 2 * dl <= cap[r] + EPS:              # two loaded vehicles fit side by side: not a cut
            continue
        # If empty and loaded vehicles cannot share it, the return counts on the cut; at most qe empty vehicles in parallel
        # (width container), so the union of E returns is ≥ E·te / qe, counted as te / qe
        excl = len(de) == len(rows) and all(e + dl > cap[r] + EPS for e in de)
        qe = max(math.floor(cap[r] / e + EPS) for e in de) if excl else 0
        tl = min(x[0][r][1] - x[0][r][0] for x in rows)
        te_occ = min(x[1][r][1] - x[1][r][0] for x in rows) if excl else 0.0
        dq = min(max(0.0, x[2] + p["unload_s"] - x[0][r][1]) for x in rows)
        if best is None or tl + te_occ / max(qe, 1) > best["tl"] + best["te"]:
            best = dict(res=r, tl=tl, te=te_occ / qe if excl else 0.0, te_occ=te_occ, dq=dq)
    assert best, "no mutually exclusive resource on the loaded leg: no cut"
    # Consecutive handovers: empty (any cradle → next origin o) + pickup + loaded (o → any cradle) + placement; the first
    # handover only needs pickup + loaded + placement
    tl_o = {o: min(x[2] for x in rows if x[4] == o) for o in stops_o}
    te_o = {o: min(x[3] for x in rows if x[4] == o) for o in stops_o}
    first = p["load_s"] + p["unload_s"] + min(tl_o.values())
    c = p["load_s"] + p["unload_s"] + min(tl_o[o] + te_o[o] for o in stops_o)
    return dict(best, c=c, ce=c - first, hp=p["load_s"], hd=p["unload_s"])


def unload_times(net, p, ramp_stop, rows, Lv, B, cut=None):
    """Theorem 3 parameters of the unloading task (ramp top ramp_stop → saddle rows rows) in the road-occupancy model, from
    the wait-free occupation windows of Net.leg, minimised over all saddle rows.
    rho: ramp operation = from the empty vehicle entering the ramp road, through the on-vessel operation load_s, until the
    loaded vehicle's tail leaves the ramp road (including longitudinal clearance); c_u: lower bound on the interval between
    two consecutive ramp-operation starts of one vehicle = on-vessel operation + full loaded trip + placement unload_s +
    empty trip back to the ramp top; cut: a resource on the loaded leg that cannot hold two loaded vehicles (excluding the
    ramp road and the on-vessel pickup point); the return counts if it also passes there and cannot share it with a loaded
    vehicle (at most qe empty vehicles at once, te = occupation / qe); the one with the largest tl + te is taken (or the
    given cut)."""
    cap, size = net.capacities(p)
    sr = net.stops[ramp_stop]
    rows_ = []
    for o in rows:
        so = net.stops[o]
        TL, stL, uL, _ = net.leg(sr["node"], so["node"], p["v_loaded"], Lv, B, True, p, cap, size, so["res"], net.demand(so["res"], B, True, p, cap))
        TE, stE, uE, arr = net.leg(so["node"], sr["node"], p["v_empty"], p["plat_len"], p["plat_w"], False, p, cap, size, sr["res"],
                                   net.demand(sr["res"], B, True, p, cap), True)
        oL = {r: (stL[a], stL[rr] + dl, d) for r, d, a, rr, dl in uL if rr is not None}
        oE = {r: (stE[a], stE[rr] + dl, d) for r, d, a, rr, dl in uE if rr is not None}
        first = next(r for r, d, a, rr, dl in uL if a == 0 and r[0] == "r")          # ramp road: first road of the loaded leg
        rows_.append((oL, oE, TL, TE, TE - stE[arr - 1] + p["load_s"] + oL[first][1], first))
    ramp = {sr["res"], rows_[0][5]}
    cand = [cut] if cut else sorted(set.intersection(*(set(x[0]) for x in rows_)) - ramp, key=str)
    best = None
    for r in cand:
        dl = max(x[0][r][2] for x in rows_)
        if 2 * dl <= cap[r] + EPS:
            continue
        de = [x[1][r][2] for x in rows_ if r in x[1]]
        excl = len(de) == len(rows_) and all(e + dl > cap[r] + EPS for e in de)
        qe = max(math.floor(cap[r] / e + EPS) for e in de) if excl else 0
        tl = min(x[0][r][1] - x[0][r][0] for x in rows_)
        te_occ = min(x[1][r][1] - x[1][r][0] for x in rows_) if excl else 0.0
        te = te_occ / qe if excl else 0.0
        if best is None or tl + te > best["tl"] + best["te"]:
            best = dict(res=r, tl=tl, te=te, te_occ=te_occ)
    assert best, "no mutually exclusive resource on the loaded leg: no cut"
    return dict(best, rho=min(x[4] for x in rows_), c_u=p["load_s"] + p["unload_s"] + min(x[2] + x[3] for x in rows_), ramp=sorted(ramp, key=str))
