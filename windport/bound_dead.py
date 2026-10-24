"""Dead-end quay coupling (Corollary 6) and cradle coupling under single-sequence handover (Corollary 7), combined into W″
(statements and proofs: see the manuscript; windport/bound.py, bound2.py, bound3.py are unchanged).

Corollary 6 (dead-end quay coupling): when chain ch satisfies premises (i)-(iii) of Lemma C (no waiting place at the gate,
the first leg of the return trip leaving the quay traverses the whole chain in reverse, a threshold g beyond the chain top;
checked case by case by bound2._guard / exit_first), then whenever an up trip U that eventually completes a handover enters
any block of the chain, there is no down vehicle on the chain or on g, and U together with the up vehicles that entered the
chain before U and are still on the chain or on g, plus the vehicles standing at quay positions, number ≤ Q_s (vehicles
following U in a convoy are not counted).
Hence (a) Q = Q_s + number of blocks in Corollary 4 becomes Q = Q_s; (b) when q_s = min(K, Q_s) = 1 these up trips run one
after another: the next enters the chain no earlier than the previous one leaves it on the way down, so consecutive handovers
are ≥ c_z = Φ_l(1) + dq_c + δ_x + Φ_e(1) apart (whole chain, not only the cut; δ_x is a lower bound on the time from leaving
the quay position to entering the top block of the chain, the minimum over the first legs of all return routes); window form
S + n(Δ; c_z), preparation form ⌊(b − p − f₁)/c_z⌋ + 1, f₁ = hp + start0 + Φ_l(1) + dq_c.
Corollary 7 (cradle coupling under single-sequence handover, cradle mode, no mixed lifting): when handovers form one sequence
spaced ≥ c (the fleet term with K = 1; the quay-zone term with q = 1 and c_z above), if all S cradles are full at the window
start, every handover must be preceded by the start of a lift (≥ a) and then placement hd, so the first handover is
≥ a + hd; if a cradle is empty, the initial buffer is ≤ S − 1.
The term then becomes max{S − 1 + ⌈Δ/c⌉, S + ⌊(Δ − hd)/c⌋ + 1} (the second branch is S when Δ < hd).
Extension of Corollary 6 to dq < 0 (parts4(signed=True), a comparison case): with direct / mixed lifting the handover can occur on
arrival at the quay position while the vehicle tail still occupies the chain top block, and bound2.chain_times drops such a chain
because dq < 0. The extension uses signed dq (handover ≥ arrival) and the fact that the same vehicle cannot enter the chain top
block on its down trip before its own up-trip window on that block ends: consecutive effective up trips enter B_1 at intervals
σ = Φ_l(1) + max(0, dq + δ_x) + Φ_e(1); consecutive handovers are ≥ c_z for the first gap and ≥ σ for later gaps; from an empty
system h_N ≥ f₁ + (N − 1)σ. With dq ≥ 0, σ = c_z and the values equal the non-extended W″."""
import math
from dataclasses import replace

from windport import bound as WB
from windport import bound2 as W2
from windport import bound3 as B3
from windport import sim as WS
from windport import sim2 as S2

EPS = 1e-9


def count2(D, c1, c2, closed):
    """Upper bound on the number of handovers in an interval of length D: first gap ≥ c1, later gaps ≥ c2 (equals
    bound.n_fleet(D, c1) when c2 is not larger than c1). closed: closed interval."""
    if c2 is None or c2 <= c1 + EPS:
        return WB.n_fleet(D, c1, closed)
    if D < -EPS or (not closed and D <= EPS):
        return 0
    if (closed and D < c1 - EPS) or (not closed and D <= c1 + EPS):
        return 1
    return 2 + (math.floor((D - c1) / c2 + EPS) if closed else math.ceil((D - c1) / c2 - EPS) - 1)


def coupled(S, D, c, hd, closed, on=True, c2=None):
    """Corollary 7: upper bound on single-sequence handovers (spacing ≥ c; with c2, first gap ≥ c and later ≥ c2) in a window of
    length D plus the initial buffer; closed: direct / mixed lifting (no coupling); on = False disables Corollary 7."""
    if c2 is None or c2 <= c + EPS:                       # without the extension: same formula as the base version (equal values)
        base = S + WB.n_fleet(D, c, closed)
        if closed or S == 0 or hd <= EPS or not on:
            return base
        second = S + (math.floor((D - hd) / c + EPS) + 1 if D >= hd - EPS else 0)
        return min(base, max(S - 1 + WB.n_fleet(D, c, False), second))
    base = S + count2(D, c, c2, closed)
    if closed or S == 0 or hd <= EPS or not on:
        return base
    second = S + (count2(D - hd, c, c2, True) if D >= hd - EPS else 0)
    return min(base, max(S - 1 + count2(D, c, c2, False), second))


def parts4(cfg, w=None, signed=False):
    """Parts of W″ independent of the window length: the result of bound3.wprime_parts with Q of P changed to Q_s by
    Corollary 6(a), plus dict(zc = [(c_z, f₁, σ)] (the chains of Corollary 6(b)), Q3 = Q before the change, lift, signed).
    signed = True: Corollary 6 extended to chains with dq < 0 (last part of the module docstring); signed = "clear": conservative
    lifting semantics, chain dq taken as max(0, dq)."""
    w = w or B3.wprime_parts(cfg)
    D, net, p, *_ = S2.setup2(cfg)
    W = D["windport"]
    S, K = cfg["S"], cfg["K"]
    lift = "direct" if S == 0 else cfg.get("lift", "cradle")
    rows, quay = W["storage"], W["cradles"][:max(1, S)]
    hold = WS.hold_of(cfg)
    P, cut = w["P"], w["t"]["res"]
    Q, zc = P.Q, []
    if not cfg.get("n_unload"):
        cap, size = net.capacities(p)
        exits = [W2.windows(net, p, cap, size, s, d, False, p["plat_len"], p["plat_w"], start_node=True)[1]
                 for s, d in {r[0] for r in S2.routes_of(D, cfg, net)} if s != d]
        chains = w["chains"]
        if signed:                       # ponytail: shift dq by BIG so dq < 0 chains pass chain_times, then shift back
            BIG = 1e7
            un = 0.0 if lift in ("direct", "mixed") else p["hd_s"]
            chains = [dict(ch, dq=ch["dq"] - BIG) for ch in W2.chain_times(net, p, rows, quay, p["Lv"], p["B"], un + BIG, S2.routes_of(D, cfg, net))]
            if signed == "clear":        # conservative lifting semantics: dq = max(0, dq)
                chains = [dict(ch, dq=max(0.0, ch["dq"])) for ch in chains]
        for ch in chains:
            Qs = W2.quay_side_Q(net, p, rows, quay, p["Lv"], p["B"], ch, hold)   # INF when premises (i)-(iii) fail
            if Qs == math.inf:
                continue
            if cut in ch["res"]:
                Q = min(Q, max(1, min(K, Qs)))                                 # Corollary 6(a)
            if min(K, Qs) == 1 and ch["down"] is not None:                     # Corollary 6(b)
                up = W2.span(1, ch["up"]) + ch["dq"]
                dx = min((next((x[1] for x in e if x[0] == ch["top"]), 0.0) for e in exits), default=0.0)   # quay → chain top
                cz = up + max(0.0, dx) + W2.span(1, ch["down"])
                sg = cz if ch["dq"] >= 0 else W2.span(1, ch["up"]) + max(0.0, ch["dq"] + max(0.0, dx)) + W2.span(1, ch["down"])
                zc.append((cz, w["hp"] + ch["start0"] + up, sg))
    return dict(w, P=replace(P, Q=Q), Q3=P.Q, zc=zc, lift=lift, signed=signed)


def terms4(w, L, empty=True, couple=True):
    """Terms of W″(L): dict(term → piles). Keys: the terms of bound.terms (Q already by Corollary 6(a); fleet with K = 1
    and zone with q = 1 by Corollary 7), serial (Π_S of Corollary 3, bound3.prep_chain_c), chainzone / chainprep
    (Corollary 6(b), minimum over chains). prep is further split into prep_fleet / prep_cut / prep_zone.
    empty = False: arbitrary history (Theorem 1), no preparation terms. couple = False: without Corollary 7 (for gap
    decomposition). w needs at least P, G, zc, chains, bm, hp (the small-case enumeration checks build these directly)."""
    P0, G = w["P"], w["G"]
    P = replace(P0, L=L)
    t = WB.terms(P, G if empty else None)
    Pm = WB._mixed(P)
    closed = Pm.direct or P.mixed
    D = L - P.p
    hd = 0.0 if (P.direct or P.mixed) else P.hd
    if D >= -EPS:
        if P.K == 1:
            t["fleet"] = coupled(P.S, D, Pm.c, hd, closed, couple)
        if min(P.K, P.Q) == 1:
            t["zone"] = coupled(P.S, D, Pm.tl + Pm.dq + WB.te_full(Pm), hd, closed, couple)
        for z in w["zc"]:
            cz, sg = z[0], z[2] if len(z) > 2 else z[0]
            t["chainzone"] = min(t.get("chainzone", math.inf), coupled(P.S, D, cz, hd, closed, couple, sg))
    if not empty:
        return t
    b = G + L
    for z in w["zc"]:
        f1, sg = z[1], z[2] if len(z) > 2 else z[0]
        m = 0 if b - P.p < f1 - EPS else math.floor((b - P.p - f1) / sg + EPS) + 1
        t["chainprep"] = min(t.get("chainprep", math.inf), m)
    cap = math.floor(L / P.p + EPS) + 1
    t["serial"] = min((B3.prep_chain_c(ch, P.K, bm, b, P.p, w["hp"], cap) for ch, bm in zip(w["chains"], w["bm"])), default=math.inf)
    t.update(prep_split(Pm, b))
    return t


def prep_split(P, b):
    """The three components of bound.prep (same algorithm split apart, for classifying by binding term; their min is bound.prep).
    P is already converted for mixed lifting."""
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


def wfn4(cfg, w=None, couple=True, signed=False):
    """Closure of W″(L) (L in seconds). W″ ≤ W′ (bound3.wprime_fn) holds term by term: terms are only added and Q only decreases.
    signed: Corollary 6 extended to dq < 0 (parts4)."""
    w = w if w and "zc" in w else parts4(cfg, w, signed)
    return lambda L: min(v for k, v in terms4(w, L, couple=couple).items() if k != "prep")


# Binding-term classes (the five classes): crane, cradle turnover, fleet, road; "prep" holds the terms limited by preparation time
# before the window (prep_*, serial, chainprep)
CLASS = dict(interface="crane", turnover="cradle", fleet="fleet", cut="road", zone="road", chainzone="road",
             prep_fleet="fleet", prep_cut="road", prep_zone="road", serial="road", chainprep="road")
PREP = {"prep_fleet", "prep_cut", "prep_zone", "serial", "chainprep"}


def binding(t):
    """(bound, binding terms, set of binding classes, whether a preparation term binds)."""
    t = {k: v for k, v in t.items() if k != "prep"}
    v = min(t.values())
    keys = sorted(k for k, x in t.items() if x == v)
    return v, keys, sorted({CLASS[k] for k in keys}), any(k in PREP for k in keys)
