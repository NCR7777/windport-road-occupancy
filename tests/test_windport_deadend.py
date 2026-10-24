"""Dead-end coupling: dead-end quay coupling (Corollary 6) and cradle coupling under single-sequence handover (Corollary 7), the W″ of
windport/bound_dead.py."""
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_extra as X                                   # noqa: E402
from windport import bound as WB                             # noqa: E402
from windport import bound2 as W2                            # noqa: E402
from windport import bound3 as B3                            # noqa: E402
from windport import bound_dead as B4                         # noqa: E402
from windport import check2 as C2                            # noqa: E402
from windport import exact as EX                             # noqa: E402
from windport import exact_chain as XC                       # noqa: E402
from windport import sim2 as S2                              # noqa: E402

H = 3600.0


def core(K=3, mode="pull_in", sc="lane", hold=0):
    return X.port_cfg(sc, mode, "S1", K, 10, hold)


def test_core_lstar_raised_to_near_fcfs():
    """Core instance: L′*(10) = 13.20 h (Q = 2 from Corollary 4) → 17.85 h with Q = Q_s = 1 → 18.418 h with Corollary 7, equal to the FCFS
    port time (66,304.14 s)."""
    c = core()
    w = B4.parts4(c)
    assert w["Q3"] == 2 and w["P"].Q == 1 and w["zc"]
    l3 = B3.lstar(B3.wprime_fn(c), 10)[0] / H
    la = B3.lstar(B4.wfn4(c, dict(w, zc=[]), couple=False), 10)[0] / H
    l4 = B3.lstar(B4.wfn4(c, w), 10)[0] / H
    assert abs(l3 - 13.197) < 1e-2 and abs(la - 17.854) < 1e-2 and abs(l4 - 18.418) < 1e-2
    _, _, sim, _ = S2.simulate2(c)
    T = sorted(x["F_vessel"] - 24 * H for x in sim.trips if x["F_vessel"] is not None)
    assert abs(T[9] - l4 * H) < 1e-2 and B4.wfn4(c, w)(T[9]) == 10 and B4.wfn4(c, w)(T[9] - 1.0) == 9


def test_longslow_chain_zone():
    """Long corridor (two-block chain): Corollary 6(a) only reaches 12.09 h (the cut is one block); the whole-chain quay-zone term
    (Corollary 6(b)) gives 17.92 h."""
    c = core(sc="longslow")
    w = B4.parts4(c)
    la = B3.lstar(B4.wfn4(c, dict(w, zc=[]), couple=False), 10)[0] / H
    lb = B3.lstar(B4.wfn4(c, w, couple=False), 10)[0] / H
    assert abs(la - 12.094) < 1e-2 and abs(lb - 17.918) < 1e-2


def test_wpp_never_above_wprime_and_holds_per_pile():
    for mode in ("pull_in", "on_road"):
        for K in (1, 2, 5):
            c = core(K, mode)
            f3, f4 = B3.wprime_fn(c), B4.wfn4(c)
            for L in (3 * H, 7.5 * H, 18 * H, 40 * H):
                assert f4(L) <= f3(L)
            net, p, sim, _ = S2.simulate2(c)
            T = sorted(x["F_vessel"] - 24 * H for x in sim.trips if x["F_vessel"] is not None)
            assert all(f4(t) >= j for j, t in enumerate(T, 1))


def test_trace_zone_at_most_qs():
    """Trajectory check of Corollary 6 (windows of the independent checker): with FCFS on the long single lane the quay zone holds at most
    Q_s = 1 vehicle at a time, and opposing passages do not overlap."""
    c = core(K=4)
    net, p, sim, _ = S2.simulate2(c)
    D, _, _, _, starts, quay, cal = S2.setup2(c)
    w = B4.parts4(c)
    ch = next(ch for ch in w["chains"] if ch["res"] == [("r", "corr_lane_0")])
    r = C2.hyp(net, p, sim.trips, starts, ["corr_lane_0"], ("r", "corr_lane_0"))
    assert r["zone"] == 1 and r["opp"] == 0 and ch["guard"]


def test_premises_off_with_holding_bay():
    """With a gate holding place (Q_h = 1) the Corollary 6 premises do not hold: Q unchanged, no whole-chain quay-zone term."""
    c = core(hold=1)
    w = B4.parts4(c)
    assert w["P"].Q == w["Q3"] and not w["zc"]


def test_coupled():
    # S = 1, c = 10, hd = 3: with the start cradle full, the first handover is ≥ a + 3
    assert B4.coupled(1, 21, 10, 3, False) == 3                          # max(S − 1 + ⌈21/10⌉, S + ⌊18/10⌋ + 1) = max(3, 3)
    assert 1 + WB.n_fleet(21, 10, False) == 4                            # uncoupled: S + ⌈21/10⌉ = 4
    assert B4.coupled(1, 25, 10, 3, False) == 4                          # Δ = 25: both branches give 4, no tightening
    assert B4.coupled(1, 25, 10, 3, True) == 1 + WB.n_fleet(25, 10, True)   # not used for direct / mixed lifting
    assert B4.coupled(1, 2, 10, 3, False) == 1                          # Δ < hd: only the pile at the start remains
    assert B4.coupled(1, 25, 10, 3, False, on=False) == 1 + WB.n_fleet(25, 10, False)


def test_exact_single_lane_corollary7():
    """Abstract single-lane enumeration (windport/exact.py): Corollary 7 tightens the q = 1 quay-zone term to the exact value."""
    L, p, S, K, hp, hd, tl, te, er, Q = 5, 1, 1, 2, 1, 2, 1, 0, 2, 1
    x = EX.max_delivery(L, p, S, K, hp, hd, tl, te, er, Q=Q, G=0, start="any")
    P = WB.lane(L, p, S, K, hp, hd, tl, te, er, Q)
    w = dict(P=P, G=0, zc=[], chains=[], bm=[], hp=hp)
    new = min(v for k, v in B4.terms4(w, L, empty=False).items() if k != "prep")
    assert WB.bound(P)[0] == 3 and new == 2 == x


def test_exact_chain_long_window():
    """Two-block chain enumeration (windport/exact_chain.py): in a long window the whole-chain quay-zone preparation term of Corollary 6(b)
    tightens the bound to the exact value (W1′ 3 → W″ 2)."""
    K, S, Qs, hp, a1, a2, e, hd, p, G, L, o = 2, 1, 1, 1, 1, 1, 1, 1, 1, 0, 16, 1
    x = XC.max_delivery(K, S, Qs, hp, a1, a2, e, e, hd, p, G, L, o)
    ch = XC.chain_params(a1, a2, e, e, hd, S, o)
    up = W2.span(1, ch["up"]) + ch["dq"]
    zc = [(up + W2.span(1, ch["down"]), hp + up)]
    c = hp + a1 + a2 + o + hd + 2 * e
    vals = []
    for tl, te, dq in ((a1 + o, e, a2 + hd), (a2 + o, e + o, hd)):
        P = WB.Port(L=L, p=p, S=S, K=K, hp=hp, hd=hd, tl=tl, te=te, c=c, ce=2 * e, dq=dq, Q=1, te_occ=te)
        vals.append(min(v for k, v in B4.terms4(dict(P=P, G=G, zc=zc, chains=[ch], bm=[1], hp=hp), L).items() if k != "prep"))
    assert x == 2 == min(vals)
    old = min(WB.bound(replace(P, Q=K), G)[0], W2.prep_chain(ch, K, 1, G + L, p, hp))
    assert old == 3


# ---------------------------------------------------------------- Corollary 6 extended to dq < 0 (parts4(signed=True))
def test_count2():
    assert B4.count2(25, 10, None, False) == WB.n_fleet(25, 10, False)
    # first gap ≥ 10, later gaps ≥ 12: the half-open interval (0, 25] fits three (0⁺, 10⁺, 22⁺), (0, 22] only two; the closed [0, 22] three
    assert B4.count2(25, 10, 12, False) == 3 and B4.count2(22, 10, 12, False) == 2 and B4.count2(22, 10, 12, True) == 3
    assert B4.count2(21.9, 10, 12, True) == 2
    assert B4.count2(5, 10, 12, True) == 1 and B4.count2(0, 10, 12, False) == 0 and B4.count2(0, 10, 12, True) == 1


def test_signed_direct_lift_core():
    """Long single lane, on-road, direct lifting (S = 0, K = 2): the original form reaches only 13.85 h, the generalisation gives
    L″ₛ* = 16.0685 h, equal to FCFS; W″ₛ ≤ W″, and it holds per pile."""
    c = X.port_cfg("lane", "on_road", "S0", 2, 10, 0)
    w, ws = B4.parts4(c), B4.parts4(c, signed=True)
    assert not w["zc"] and ws["zc"] and ws["zc"][0][2] > ws["zc"][0][0]           # only the generalisation yields a chain with dq < 0, σ > c_z
    f, fs = B4.wfn4(c, w), B4.wfn4(c, ws)
    assert abs(B3.lstar(f, 10)[0] / H - 13.854) < 1e-2 and abs(B3.lstar(fs, 10)[0] / H - 16.0685) < 1e-3
    _, _, sim, _ = S2.simulate2(c)
    T = sorted(x["F_vessel"] - 24 * H for x in sim.trips if x["F_vessel"] is not None)
    assert all(j <= fs(t) <= f(t) for j, t in enumerate(T, 1)) and abs(T[9] / H - 16.0685) < 1e-3


def test_signed_unchanged_when_dq_nonnegative():
    """In cradle mode (dq ≥ 0) the generalisation equals W″ value by value."""
    c = core()
    f, fs = B4.wfn4(c), B4.wfn4(c, signed=True)
    assert all(f(L * H) == fs(L * H) for L in (2, 6, 12, 17.9, 18.5, 30))


def test_tail_exhaustive_case():
    """Two-block chain enumeration where a pile may be lifted from the vehicle while its tail occupies the chain top
    (windport/exact_chain_tail.py): a direct-lifting case with tail o = 2, exact = W″ₛ."""
    import windport_deadend_ext as E
    r = E.one_tail(dict(K=2, S=0, Qs=1, hp=1, a1=1, a2=2, e=2, o=2, hd=1, p=1, G=0, L=16))
    assert r["over"] == 0 and r["tie"] == 1 and "chain" in r["binding"]
