"""Checks of the window bound W1 (windport/bound.py) against small-case enumeration (windport/exact.py).
1. Hand-computed cases; 2. on small single-lane cases (K = 1-3, S = 0-3, short windows) enumerate the maximum delivery within
the window and confirm the bound is never exceeded and every term is attained by some case; 3. monotonicity of the enumeration;
4. in the road-occupancy model (A1 archetype, full-path reservation), deliveries from an empty system do not exceed the transport
terms whose parameters come from Net.leg.
The full-grid check is experiments/windport_w1_check.py (released results: results/runs/w1_grid)."""
import itertools
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from exact.model import FPR                                        # noqa: E402
from occupancy import params as PP                                 # noqa: E402
from windport import archetypes as A                               # noqa: E402
from windport.bound import (Port, bound, k_dagger, lane, occupancy_times, periodic, port, prep, rate, s_star,   # noqa: E402
                            terms)
from windport.exact import max_delivery                            # noqa: E402


# ---------------------------------------------------------------- 1. hand-computed
def test_hand_fleet_and_cut():
    """L = 10, p = 2, 1 cradle, 1 vehicle set, pick-up 1, cut crossing 2, set-down 1, return crossing 2 (c = 6).
    Interface 5; fleet 1 + ⌈8/6⌉ = 3; cut: with 0 vehicles on the quay side M(7, 1) = 2 (tl·1 + te·1 = 4 ≤ 7), with 1 vehicle
    1 + M(7, 0) = 1 + 1 -> 3; turnover 9.
    A feasible schedule attains 3: one item in the cradle and one loaded vehicle on the quay side; lift at 0, set-down 0-1,
    return 1-3, pick-up 3-4, cross 4-6, set-down 6-7, lift at 7 (7 + 2 ≤ 10)."""
    P = lane(10, 2, 1, 1, 1, 1, 2, 2)
    assert terms(P) == dict(interface=5, turnover=9, fleet=3, cut=3)
    assert bound(P) == (3, ["fleet", "cut"])
    assert max_delivery(10, 2, 1, 1, 1, 1, 2, 2, start="any") == 3


def test_hand_direct_lift():
    """S = 0 (direct lift from the vehicle): L = 4, p = 2, c = 1 + 1 + 1 = 3. Fleet ⌊2/3⌋ + 1 = 1, cut 2, interface 2 -> 1."""
    P = lane(4, 2, 0, 1, 1, 1, 1, 1)
    assert P.direct and P.c == 3
    assert terms(P) == dict(interface=2, turnover=float("inf"), fleet=1, cut=2)
    assert max_delivery(4, 2, 0, 1, 1, 1, 1, 1, start="any") == 1


def test_hand_interface_and_prep():
    P = lane(6, 3, 3, 3, 1, 1, 1, 1)                     # cradles full, many vehicles: the ship crane is the bottleneck
    assert bound(P) == (2, ["interface"]) and max_delivery(6, 3, 3, 3, 1, 1, 1, 1, start="any") == 2
    P = lane(4, 1, 3, 1, 1, 1, 2, 2)                     # empty system, no preparation: first handover at 4, later than b − p = 3
    assert bound(P, 0) == (0, ["prep"]) and max_delivery(4, 1, 3, 1, 1, 1, 2, 2, G=0) == 0
    # preparation G = 5: b = 9, fleet ⌊(8 − 4)/6⌋ + 1 = 1, cut tl·m + te·(m − 1)⁺ ≤ 9 − 1 − 1 − 1 -> m = 2 -> prep = 1
    assert prep(P, 9) == 1 and max_delivery(4, 1, 3, 1, 1, 1, 2, 2, G=5) == 1


def test_closed_forms():
    P = lane(10, 2, 1, 2, 1, 1, 2, 2)                    # c = 6, tl + te = 4
    assert k_dagger(P) == 1.5 and rate(P) == 0.25
    assert rate(lane(10, 2, 1, 1, 1, 1, 2, 2)) == pytest.approx(1 / 6)
    rest = lambda S: min(v for k, v in terms(Port(**{**P.__dict__, "S": S})).items() if k != "interface")
    # interface 5; fleet S + 2·⌈8/6⌉ = S + 4, cut S + 3 (3 for all kq) -> S* = 2
    S = s_star(P)
    assert S == 2 and rest(2) >= terms(P)["interface"] > rest(1)
    P = lane(12, 1, 1, 1, 1, 1, 2, 2)                    # interface 12; fleet S + ⌈11/6⌉ = S + 2, cut S + 3 -> S* = 10
    assert s_star(P) == 10 and rest(10) >= 12 > rest(9)
    # S* must include the quay-zone term when it binds: Q = 1, S = 6 gives W1 = 9 (quay zone), S* = 9 gives W1 = I = 12;
    # enumeration agrees
    P = lane(12, 1, 1, 3, 1, 1, 1, 2, Q=1)
    assert s_star(P) == 9
    W = lambda S: bound(Port(**{**P.__dict__, "S": S}))
    assert W(6) == (9, ["zone"]) and W(9)[0] == 12
    assert max_delivery(12, 1, 6, 3, 1, 1, 1, 2, Q=1, start="any") == 9 and max_delivery(12, 1, 9, 3, 1, 1, 1, 2, Q=1, start="any") == 12


def test_release_before_acquire():
    """A place freed by a vehicle leaving the quay zone at time t can be used by a vehicle entering at the same t (half-open
    intervals of H5): K = 2, S = 1, Q = 1, hp = tl = hd = 1, loop return er = 2, p = 1, L = 12, any history: enumeration gives 6
    (5 under the closed-interval rule), W1 = 7."""
    assert max_delivery(12, 1, 1, 2, 1, 1, 1, 0, 2, Q=1, start="any") == 6
    assert bound(lane(12, 1, 1, 2, 1, 1, 1, 0, 2, Q=1))[0] == 7


def test_zone_aware_cut():
    """With 1 < Q < K and the return crossing the cut, every zone entry after the q-th needs a prior zone exit on the return
    (cut term C′): Q = 2, te = 3, S = 1, L = 12; for K = 2-5 W1 is always 5 (the zone-blind cut term gives 5, 6, 7, 8), and the
    enumeration also gives 5."""
    for K in (2, 3, 4, 5):
        assert bound(lane(12, 1, 1, K, 1, 1, 1, 3, Q=2))[0] == 5
    assert max_delivery(12, 1, 1, 3, 1, 1, 1, 3, Q=2, start="any") == 5


def test_mixed_lifting():
    """In cradle mode the ship crane may also lift from a vehicle (Corollary 2): W1 computed for cradle mode only is exceeded
    (K = 1, S = 1, L = 5: mixed 3, cradle-mode W1 = 2), while the Corollary 2 bound is not."""
    assert max_delivery(5, 1, 1, 1, 1, 1, 1, 1, start="any", mixed=True) == 3 > bound(lane(5, 1, 1, 1, 1, 1, 1, 1))[0]
    for K, S, Q, hd, (te, er), p, L, G in itertools.product([1, 2], [1, 2], [1, 2], [1, 3], [(1, 0), (0, 2)], [1, 2], [5, 9], [None, 3]):
        if Q > K:
            continue
        x = max_delivery(L, p, S, K, 1, hd, 1, te, er, Q=Q, G=G or 0, start="any" if G is None else "empty", mixed=True)
        assert x <= bound(lane(L, p, S, K, 1, hd, 1, te, er, Q, mixed=True), G)[0], (K, S, Q, hd, te, er, p, L, G, x)


def test_two_lane_cut_share():
    """Two-lane cut (with no loaded vehicle, at most 2 empty vehicles on the cut at once, qe = 2): the return counts as te / 2 in
    the cut term, and the bound is not exceeded."""
    for K, S, Q, tl, te, p, L in itertools.product([2, 3], [0, 1, 2], [1, 3], [1, 2], [2, 3], [1, 2], [6, 10]):
        Q = min(Q, K)
        x = max_delivery(L, p, S, K, 1, 1, tl, te, Q=Q, start="any", qe=2)
        assert x <= bound(lane(L, p, S, K, 1, 1, tl, te, Q=Q, qe=2))[0], (K, S, Q, tl, te, p, L, x)


def test_degenerate_inputs_rejected():
    with pytest.raises(AssertionError):
        terms(Port(L=5, p=1, S=1, K=1, hp=1, hd=1, tl=0, te=0, c=2, ce=0, dq=1, Q=1))


# ---------------------------------------------------------------- 2. enumeration check
GRID = list(itertools.product([1, 2, 3], [0, 1, 2, 3], [1, 2], [1, 3], [(1, 0), (2, 0), (0, 2)], [1, 3], [3, 6, 9]))


@pytest.mark.parametrize("start,G", [("any", None), ("empty", 0), ("empty", 3)])
def test_never_exceeded_and_attained(start, G):
    """Grid over K, S, pick-up, cut crossing, return, p, L (set-down 1, Q ∈ {1, 2, K}): exact value ≤ W1; every term has a case
    where it binds with equality."""
    hit = set()
    for K, S, hp, tl, (te, er), p, L in GRID:
        for Q in sorted({1, min(2, K), K}):
            P = lane(L, p, S, K, hp, 1, tl, te, er, Q)
            b, why = bound(P, G)
            x = max_delivery(L, p, S, K, hp, 1, tl, te, er, Q=Q, G=G or 0, start=start)
            assert x <= b, (K, S, hp, tl, te, er, p, L, Q, start, G, x, terms(P, G))
            if x == b > 0:
                hit |= set(why)
    want = {"fleet", "cut"} | ({"prep"} if start == "empty" else set()) | ({"interface"} if G != 0 else set())
    assert want <= hit, hit                              # empty system, no preparation (G = 0): the ship crane never binds first


def test_turnover_term():
    """Set-down slower than lifting (hd = 3 > p = 1) makes cradle turnover bind: 1 cradle, L = 7, ⌊6/3⌋ + 1 = 3."""
    P = lane(7, 1, 1, 3, 1, 3, 1, 1)
    assert bound(P)[1] == ["turnover"] and bound(P)[0] == 3 == max_delivery(7, 1, 1, 3, 1, 3, 1, 1, start="any")


def test_periodic_windows():
    for K, S, tl, (te, er), L, G, n in itertools.product([1, 2], [0, 1, 2], [1, 2], [(1, 0), (0, 2)], [3, 5], [0, 4], [2, 3]):
        P = lane(L, 1, S, K, 1, 1, tl, te, er)
        x = max_delivery(L, 1, S, K, 1, 1, tl, te, er, G=G, T=L + 3, n=n)
        assert x <= periodic(P, G, L + 3, n) <= n * bound(P)[0], (K, S, tl, te, er, L, G, n)


# ---------------------------------------------------------------- 3. monotonicity of the enumeration (one more vehicle set,
# one more cradle or a longer window never gives less)
def test_exact_monotone():
    for hp, tl, (te, er), p in itertools.product([1, 2], [1, 2], [(1, 0), (0, 2)], [1, 2]):
        f = lambda K, S, L: max_delivery(L, p, S, K, hp, 1, tl, te, er, G=2)
        for K, S, L in itertools.product([1, 2], [1, 2], [4, 6]):
            v = f(K, S, L)
            assert v <= f(K + 1, S, L) and v <= f(K, S + 1, L) and v <= f(K, S, L + 1)


# ---------------------------------------------------------------- 4. transport terms in the road-occupancy model
P_SPMT = dict(PP.DEFAULTS, v_loaded=1 / 3.6, v_empty=5 / 3.6, plat_len=30.0, plat_w=4.86, load_s=1800.0, unload_s=1800.0)


@pytest.mark.parametrize("kind", ["A1", "A2"])
def test_occupancy_deliveries_within_transport_term(kind):
    """Full-path reservation (FPR) on an archetype does 8 load-outs from an empty system: the number completed before any time t
    is ≤ prep (ship-crane cycle set to 0, i.e. transport only).
    The transport-term parameters come from Net.leg via occupancy_times, so this checks that the cut + fleet argument holds
    under road-occupancy semantics."""
    with tempfile.TemporaryDirectory() as d:
        D = A.build(kind, n_cradles=2, n_rows=3)
        net = A.to_net(D, P_SPMT, Path(d) / "m.json")
    W = D["windport"]
    t = occupancy_times(net, P_SPMT, W["storage"], W["cradles"], Lv=100.0, B=10.0)
    tasks = [dict(id=j, flow="load", o=W["storage"][j % 3], d=W["cradles"][j % 2], B=10.0, Lv=100.0, release=0.0) for j in range(8)]
    for K in (1, 2, 3):
        sim = FPR(net, dict(P_SPMT, days=30), "reserve", K, 1, None, tasks=[dict(x) for x in tasks])
        for k, v in enumerate(sim.vs):
            v.loc = net.stops[W["storage"][k % 3]]["node"]
        sim.run()
        done = sorted(r["done"] for r in sim.done)
        assert len(done) == 8
        P = Port(**{**port(t, 0.0, 0.0, 1, K).__dict__, "p": 0.0})
        for j, x in enumerate(done):
            assert j + 1 <= prep(P, x + 1e-6), (kind, K, j, x, prep(P, x))
