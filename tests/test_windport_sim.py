"""Port simulation (windport/sim.py), independent checker (windport/check.py), CP-SAT small instances (windport/cpsat.py),
enumeration for unloading and joint unloading/load-out (windport/exact_u.py), and the related parts of bound.py.
E0 semantic checks: the whole ramp operation lies inside a tide window, a vehicle cannot be reused before it is released, the ship
crane lifts only during berthing and not before set-down completes, one item per cradle at a time.
Further checks: W1 is never exceeded on random archetypes (including counterexample seeds found in checking), idle places (gate
holding place / yard side), stop-and-steer delays at turns, the release time for direct lifting, checker blind spots, archetypes
without a ramp."""
import copy
import itertools
import json
import math
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from occupancy.network import Net                    # noqa: E402
from windport import bound as B                      # noqa: E402
from windport import check as C                      # noqa: E402
from windport import sim as S                        # noqa: E402
from windport.exact import max_delivery              # noqa: E402
from windport.exact_u import frontier                # noqa: E402

KMH = 1 / 3.6


def cfg(kind="A1", mode="on_road", K=2, Sn=2, lift="cradle", L=6, G=3, n_unload=0, ramp=None, **kw):
    c = dict(dict(geo=dict(kind=kind, n_cradles=4, cradle_mode=mode), S=Sn, K=K, lift=lift, horizon_h=G + L + 30,
                  cal=dict(crane=[[G, G + L]]), n_load=L + K + Sn + 2, n_unload=n_unload, p=kw.pop("p", {})), **kw)
    if ramp:
        c["cal"]["ramp"] = ramp
    return c


def check_of(c, sim, trips=None):
    D, net, p, _, starts, quay, cal = S.setup(c)
    return C.check(net, p, sim.trips if trips is None else trips, starts, quay, cal, c.get("fixed", False), S.ramp_res(D), S.hold_of(c), sim.H)


def checked(c, trips=None):
    net, p, sim, r = S.simulate(c)
    return check_of(c, sim, trips), sim, r


# ---------------------------------------------------------------- road network: stop-and-steer at turns and swept area
def test_turn_delays_trip_and_sweeps_arms():
    """The A2 gate is a three-way junction: a loaded vehicle turning 90° from the single lane onto the apron stops for
    δ = sweep_steer_s + angle·(Lv/2)/v; trip time and junction occupancy grow by δ, and the loop-return arm is held exclusively
    over the same interval. The A1 gate is a two-way corner (not a junction resource): trip time also grows by δ.
    With sweep_steer_s = None the result equals Net.leg term by term."""
    for kind in ("A2", "A1"):
        c = cfg(kind)
        D, net, p, _, _, quay, _ = S.setup(c)
        W = D["windport"]
        cap, size = net.capacities(p)
        o, d = net.stops[W["storage"][0]], net.stops[quay[0]]
        args = (o["node"], d["node"], p["v_loaded"], p["Lv"], p["B"], True, p, cap, size, d["res"], net.demand(d["res"], p["B"], True, p, cap))
        T, st, uses, arr = net.leg(*args)
        q = dict(p, sweep_steer_s=None)
        T0 = Net.leg(net, *args[:6], q, *args[7:])[0]
        n90 = sum(1 for dl in S.turn_delays(net, net.path(o["node"], d["node"]), p["Lv"], p["v_loaded"], p)[1] if dl)
        delta = p["sweep_steer_s"] + (math.pi / 2) * p["Lv"] / 2 / p["v_loaded"]
        assert n90 >= 1 and T == pytest.approx(T0 + n90 * delta, rel=1e-6)
        assert net.leg(*args[:6], q, *args[7:]) == Net.leg(net, *args[:6], q, *args[7:])
        if kind == "A2":
            g = W["gates"][0]
            node = [u for u in uses if u[0] == ("n", g)]
            arm = [u for u in uses if u[0] == ("r", W["loop"][0])]
            assert len(node) == 1 and len(arm) == 1 and arm[0][1] == cap[("r", W["loop"][0])] and arm[0][2:] == node[0][2:]
            assert node[0][4] == pytest.approx((size[g] + p["Lv"] + p["long_clear"]) / p["v_loaded"] + delta, rel=1e-6)


# ---------------------------------------------------------------- E0: semantics
def test_ramp_operation_inside_tide_window():
    """The whole ramp operation (empty vehicle drives onto the ramp -> loaded vehicle's tail leaves the ramp) lies inside a tide
    window: if the first window cannot hold a whole operation it is pushed to the next window; not only the start time counts."""
    c = cfg(K=1, Sn=1, n_unload=2, ramp=[[0, 3], [12.42, 18.42], [24.84, 30.84]], p=dict(roro_s=4 * 3600.0), n_load=0)
    c["cal"].pop("crane")
    chk, sim, r = checked(c)
    assert chk["ok"], chk["errors"]
    u = sorted((x for x in sim.trips if x["flow"] == "unload"), key=lambda x: x["t1"])
    assert len(u) == 2 and all(x["F_ramp"] is not None for x in u)
    assert r["n_ramp"] == [0, 1, 1]                          # a 3 h window cannot hold a 4 h operation
    assert all(12.42 * 3600 - 1e-6 <= x["a"] for x in u)    # may leave early, enters ramp in window
    assert "thm3" in r and all(a <= b for a, b in zip(r["n_ramp"], r["thm3"]["bound"]))


def test_vehicle_reuse_and_crane_window():
    """One vehicle set: the next empty run starts no earlier than arrival at an idle place after leaving the quay on the previous
    trip; the whole lift lies within the berthing period and not before set-down completes; at most one item per cradle."""
    c = cfg(K=1, Sn=1, L=4, G=2)
    chk, sim, r = checked(c)
    assert chk["ok"], chk["errors"]
    tr = sorted((x for x in sim.trips if x["t1"] < 1e8), key=lambda x: x["t1"])
    for a, b in zip(tr, tr[1:]):
        assert b["t1"] >= a["rel"] - 1e-6 and a["exit"][2] == "yard" and a["rel"] > a["exit"][1] >= a["r0"]
    for x in tr:
        if x["s"] is not None:
            assert 2 * 3600 <= x["s"] and x["F_vessel"] <= 6 * 3600 + 1e-6 and x["s"] >= x["F_quay"] - 1e-6
    lifts = sorted((x["tc"], x["s"]) for x in tr if x["s"] is not None)
    assert all(s0 <= tc1 + 1e-6 for (_, s0), (tc1, _) in zip(lifts, lifts[1:]))
    assert r["n_vessel"][0] <= r["w1"]["bound"]


@pytest.mark.parametrize("kind", ["A1", "A2", "A3"])
def test_checker_passes_and_catches(kind):
    """Three archetypes, unloading and load-out together (tide windows + two berthing periods), 1 gate holding place: the
    simulated schedule passes the independent checker; moving one trip 30 min earlier, moving a lift earlier, switching to the
    same cradle, or moving a ramp operation into a closed period is each reported by the checker."""
    c = cfg(kind, K=3, Sn=2, L=6, n_unload=3, ramp=[[0, 5], [12.42, 17.42], [24.84, 29.84]], p=dict(v_loaded=1 * KMH), hold=1)
    c["cal"]["crane"] = [[3, 9], [20, 24]]
    chk, sim, r = checked(c)
    assert chk["ok"] and chk["max_ratio"] <= 1 + 1e-9, chk["errors"]
    live = [x for x in sim.trips if x["t1"] < 1e8]

    def caught(f, word):
        for j in range(len(live)):
            tr = copy.deepcopy(sim.trips)
            x = next(y for y in tr if y["id"] == live[j]["id"])
            if f(x) is False:
                continue
            if any(word in e for e in check_of(c, sim, tr)["errors"]):
                return True
        return False

    def early(x):                                       # whole trip 30 min earlier: enters the single lane with another vehicle
        if x["flow"] != "load" or x["s"] is None:
            return False
        for k in ("t1", "a", "t2", "tc", "F_quay", "rel", "s", "F_vessel", "r0"):
            x[k] -= 1800
        x["exit"][1] -= 1800

    def lift(x):
        if x["s"] is None:
            return False
        x["s"] -= 600
        x["F_vessel"] -= 600

    def same(x):
        if x["flow"] != "load" or x["k"] == 0:
            return False
        x["k"], x["d"] = 0, S.setup(c)[5][0]

    def tide(x):
        if x["flow"] != "unload":
            return False
        d = 5.5 * 3600 - x["t1"]
        for k in ("t1", "a", "t2", "tc", "F_ramp", "F_yard", "rel"):
            x[k] += d
    assert caught(early, "('r', ") and caught(lift, "('c', 'crane')") and caught(same, "('c', 'cr', 0)") and caught(tide, "tidal window")


def test_checker_blind_spots_closed():
    """Cradle number not matching the quay stop, F_ramp not the end of the loaded window on the ramp, the same task done twice,
    and an overfull gate holding place are all reported by the checker."""
    c = cfg(K=3, Sn=2, L=12, hold=1, n_unload=2, ramp=[[0, 6], [12.42, 18.42]], unload_release_h=[0, 12.42], p=dict(roro_s=3 * 3600.0))
    chk, sim, r = checked(c)
    assert chk["ok"], chk["errors"]
    tr = copy.deepcopy(sim.trips)
    x = next(y for y in tr if y["flow"] == "load" and y["k"] == 1)
    x["k"] = 0                                           # cradle recorded as 0 while the quay stop is still quay[1]
    assert any("is not this trip's quay stop" in e for e in check_of(c, sim, tr)["errors"])
    tr = copy.deepcopy(sim.trips)
    x = next(y for y in tr if y["flow"] == "unload" and y["F_ramp"] is not None)
    x["F_ramp"] += 3600
    assert any("F_ramp" in e for e in check_of(c, sim, tr)["errors"])
    tr = copy.deepcopy(sim.trips)
    tr.append(dict(next(y for y in tr if y["flow"] == "load" and y["t1"] < 1e8)))
    assert any("done 2 times" in e for e in check_of(c, sim, tr)["errors"])
    holds = [y for y in sim.trips if y["exit"] and y["exit"][2] == "hold"]
    yards = [y for y in sim.trips if y["exit"] and y["exit"][2] == "yard"]
    assert holds and yards                               # when the gate holding place is full, go to the yard side
    tr = copy.deepcopy(sim.trips)
    for y in tr:
        if y["exit"] and y["exit"][2] == "yard" and y["exit"][0] == S.yard_node(S.setup(c)[0]):
            y["exit"] = [S.exit_node(S.setup(c)[0]), y["exit"][1], "hold"]
    errs = check_of(c, sim, tr)["errors"]
    assert any("('b', 'hold', 0)" in e for e in errs) or any("release time" in e for e in errs)


def test_checker_idle_labels():
    """The checker verifies exit destinations and nodes against the archetype topology. G1: one exit to the gate holding place
    relabelled as yard side (node still the gate); G2: a schedule with unlimited gate holding places fully relabelled as yard side
    and checked with Q_h = 0 (phantom waiting at the gate); G3: a Q_h = 1 schedule checked with Q_h = 0. All three are reported,
    with no division by zero."""
    c = dict(geo=dict(kind="A1", n_cradles=2, cradle_mode="on_road", dist_m=1500.0, corridor_m=1200.0, n_junctions=0), S=0, K=3, lift="cradle",
             horizon_h=16, cal=dict(crane=[[3, 15]]), n_load=14, p=dict(v_loaded=1 * KMH), hold=1)
    net, p, sim, r = S.simulate(c)
    D, _, _, _, starts, quay, cal = S.setup(c)
    chk = lambda tr, h, H: C.check(net, p, tr, starts, quay, cal, False, S.ramp_res(D), h, H)
    assert C.idle_nodes(net) == (S.exit_node(D), S.yard_node(D)) and chk(sim.trips, 1, sim.H)["ok"]
    tr = copy.deepcopy(sim.trips)
    x = next(x for x in tr if x["exit"] and x["exit"][2] == "hold")
    x["exit"][2] = "yard"
    assert any("is not the yard-side node" in e for e in chk(tr, 1, sim.H)["errors"])                       # G1
    _, _, simi, _ = S.simulate(dict(c, hold="inf"))
    tr = copy.deepcopy(simi.trips)
    for x in tr:
        if x["exit"]:
            x["exit"][2] = "yard"
    assert any("is not the yard-side node" in e for e in chk(tr, 0, simi.H)["errors"])                       # G2
    assert any("number of gate holding places is 0" in e for e in chk(sim.trips, 0, sim.H)["errors"])                    # G3


def test_joint_dedicated_fleet():
    """Unloading and load-out together on a shared single lane, with 1 extra vehicle set dedicated to unloading: load-out is
    dispatched only to the first K sets and unloading only to the dedicated set; the checker passes; unloadings per tide window do
    not exceed Theorem 3, items in the crane window do not exceed W1, and the Theorem 4 slack is ≥ 0."""
    c = cfg(K=2, Sn=2, L=12, G=3, n_unload=3, ramp=[[0, 6], [12.42, 18.42], [24.84, 30.84]], K_u=1, joint_cut="corr_lane_0",
            unload_release_h=[0, 12.42, 24.84], p=dict(roro_s=3 * 3600.0))
    chk, sim, r = checked(c)
    assert chk["ok"], chk["errors"]
    assert {x["vid"] for x in sim.trips if x["flow"] == "unload"} == {2} and {x["vid"] for x in sim.trips if x["flow"] == "load"} <= {0, 1}
    assert sum(r["n_ramp"]) == 3 and all(a <= b for a, b in zip(r["n_ramp"], r["thm3"]["bound"]))
    assert r["n_vessel"][0] <= r["w1"]["bound"] and r["thm4_gap"] >= 0


def test_never_exceeds_w1_small_grid():
    """A1 with both cradle access modes × cradle / direct / mixed lifting × K × S × L × gate holding places 0 / 1 / unlimited:
    items lifted on board in simulation do not exceed the corresponding W1."""
    for mode, lift, K, Sn, L, G, h in itertools.product(["on_road", "pull_in"], ["cradle", "mixed"], [1, 3], [0, 1, 3], [3, 8], [1, 24],
                                                        [0, 1, "inf"]):
        if Sn == 0 and lift == "mixed":
            continue
        r = S.run_point(cfg(mode=mode, lift=lift, K=K, Sn=Sn, L=L, G=G, p=dict(lift_s=1800.0), hold=h))
        assert r["n_vessel"][0] <= r["w1"]["bound"], (mode, lift, K, Sn, L, G, h, r["n_vessel"], r["w1"])


def random_port(i):
    """Random archetype generator used in checking (the "no exit booking" option is replaced by gate holding place levels; the
    release time is also drawn)."""
    R = random.Random(1000 + i)
    kind = R.choice(["A1", "A2", "A3"])
    dist = R.choice([200.0, 400.0, 600.0, 1000.0, 1500.0])
    geo = dict(kind=kind, dist_m=dist, corridor_m=R.choice([0.3, 0.6, 0.8, 1.0]) * dist, n_junctions=R.choice([0, 1, 2]),
               cradle_mode=R.choice(["on_road", "pull_in"]), n_cradles=R.choice([2, 4, 6]), apron_w=R.choice([12.0, 12.0, 16.0]),
               ramp_at=R.choice(["end", "gate"]) if kind != "A3" else "end", bypass=R.choice([True, False]),
               cradle_spacing=R.choice([60.0, 110.0, 150.0]))
    geo.pop("ramp_at" if kind == "A3" else "bypass")
    p = dict(v_loaded=R.choice([0.5, 1.0, 2.5, 5.0]) * KMH, v_empty=R.choice([2.0, 5.0, 10.0]) * KMH, Lv=R.choice([60.0, 90.0, 110.0, 130.0]),
             hp_s=R.choice([300.0, 900.0, 1800.0, 3600.0]), hd_s=R.choice([300.0, 900.0, 1800.0, 5400.0]),
             lift_s=R.choice([900.0, 1800.0, 3600.0, 7200.0]), sweep_steer_s=R.choice([None, 0.0, 120.0, 900.0]))
    S_ = min(R.choice([0, 1, 2, 3, 4]), geo["n_cradles"])
    K = R.choice([1, 2, 3, 4, 6])
    L = R.choice([1, 2, 3, 5, 8, 12, 24])
    G = R.choice([0, 1, 3, 8, 24])
    lift = R.choice(["cradle", "mixed"]) if S_ else "cradle"
    c = dict(geo=geo, p=p, S=S_, K=K, lift=lift, horizon_h=G + L + 1, cal=dict(crane=[[G, G + L]]),
             n_load=int(L * 3600 // p["lift_s"]) + K + S_ + 2, hold=[0, 0, 1, 2, "inf"][i % 5])
    if R.random() < 0.8:
        p["release_frac"] = R.choice([0.0, 0.0, 0.25, 1.0])
    if R.random() < 0.3:
        n = int((G + L + 1) // 12.4206) + 1
        c["cal"]["ramp"] = [[k * 12.4206, k * 12.4206 + R.choice([3.0, 6.0])] for k in range(n)]
        c.update(n_unload=n, unload_release_h=[k * 12.4206 for k in range(n)], K_u=R.choice([0, 1]))
        c["p"]["roro_s"] = R.choice([1800.0, 3 * 3600.0])
        if c["K_u"] == 0:
            c["p"]["unload_first"] = R.random() < 0.5
    return c


REVIEW_SEEDS = [851, 1355, 1404, 2074, 6243, 9069, 12870, 14749, 15242, 19003, 19044, 19378]     # counterexample seeds (12 of 58)


def test_random_ports_never_exceed_w1():
    """Regression on random archetypes (200 seeds + the 12 counterexample seeds): items lifted on board in simulation ≤ W1, the
    checker passes, and unloading does not exceed Theorem 3."""
    for i in list(range(200)) + REVIEW_SEEDS:
        c = random_port(i)
        net, p, sim, r = S.simulate(c)
        chk = check_of(c, sim)
        assert chk["ok"], (i, chk["errors"][:2])
        assert r["n_vessel"][0] <= r["w1"]["bound"], (i, r["n_vessel"], r["w1"])
        if r.get("thm3"):
            assert all(a <= b for a, b in zip(r["n_ramp"], r["thm3"]["bound"])), i


def test_hold_pocket():
    """Gate holding place: with Q_h = 1 at most one vehicle waits at the gate at any time (the checker verifies occupancy);
    when full, vehicles drive through the single lane to the yard side; with Q_h = 0 all go to the yard side.
    Long single lane + 1 km/h, direct lifting: unlimited gate holding places deliver no less than any other level; under
    first-come-first-served, delivery is not necessarily monotone in Q_h (here Q_h = 1, 2 give 6 items, Q_h = 0 and unlimited
    give 7: a vehicle waiting at the gate must still cross the single lane against the flow on its next trip)."""
    base = cfg(K=3, Sn=0, L=12, G=3, p=dict(v_loaded=1 * KMH))
    base["geo"].update(dist_m=1500.0, corridor_m=1200.0, n_junctions=0)
    out = {}
    for h in (0, 1, 2, "inf"):
        c = dict(base, hold=h)
        chk, sim, r = checked(c)
        assert chk["ok"], (h, chk["errors"][:2])
        kinds = {x["exit"][2] for x in sim.trips if x["exit"]}
        assert kinds == {"yard"} if h == 0 else "hold" in kinds
        out[h] = r["n_vessel"][0]
    assert max(out.values()) == out["inf"], out


def test_direct_release_fraction():
    """Release time for direct lifting: the vehicle is released release_frac·p after the lift starts; later release never
    increases delivery, the W1 cycle c grows by release_frac·p, and the simulation does not exceed W1."""
    n = []
    for x in (0.0, 0.25, 0.5, 1.0):
        c = cfg(K=1, Sn=0, L=12, G=3, p=dict(release_frac=x))
        chk, sim, r = checked(c)
        assert chk["ok"] and r["n_vessel"][0] <= r["w1"]["bound"]
        assert all(abs(t["r0"] - t["s"] - x * 3600.0) < 1e-6 for t in sim.trips if t["s"] is not None)
        n.append(r["n_vessel"][0])
    assert n == sorted(n, reverse=True) and n[0] > n[-1]


def test_archetype_without_ramp():
    """An archetype with ramp_at = None (no ramp, no origin category) can be simulated with load-out only; asking for unloading
    tasks raises a clear error."""
    c = cfg(K=2, Sn=1)
    c["geo"]["ramp_at"] = None
    chk, sim, r = checked(c)
    assert chk["ok"] and 0 < r["n_vessel"][0] <= r["w1"]["bound"]
    with pytest.raises(AssertionError, match="ramp"):
        S.simulate(dict(c, n_unload=1))


def test_fixed_time_ignores_road():
    """Fixed-duration representation: when the cut binds on a single lane (1,200 m, no side branches, 1 km/h), it lifts more items
    on board than the road-occupancy W1 (RQ3); ramp, cradles and ship crane are still checked."""
    c = cfg(K=3, Sn=0, L=12, G=24, p=dict(v_loaded=1 * KMH))
    c["geo"].update(dist_m=1500.0, corridor_m=1200.0, n_junctions=0)
    occ = S.run_point(c)
    chk, _, r = checked(dict(c, fixed=True))
    assert chk["ok"] and occ["n_vessel"][0] <= occ["w1"]["bound"] < r["n_vessel"][0]


# ---------------------------------------------------------------- CP-SAT small instance
def test_cpsat_small_instance():
    """K = 2, S = 1, L = 5 h, G = 1 h (ship crane 0.5 h): W1 + 2 candidate monopiles; CP-SAT proves the optimum ≤ W1 and
    ≥ simulation; its schedule, in continuous time, passes the independent checker (0 and 1 gate holding places)."""
    from windport import cpsat as CP
    for h in (0, 1):
        c = cfg(K=2, Sn=1, L=5, G=1, p=dict(lift_s=1800.0), hold=h)
        c["geo"]["n_cradles"] = 3
        _, _, sim, r = S.simulate(c)
        inst = CP.Inst(c)
        assert len(inst.tasks) == inst.w1["bound"] + 2
        out = CP.solve(inst, 60, 2, hint=sim.trips)
        chk = C.check(inst.net, inst.p, out["trips"], inst.starts, inst.quay, inst.cal, False, S.ramp_res(inst.D), inst.hold, inst.H)
        assert out["status"] == "OPTIMAL" and r["n_vessel"][0] <= out["best"] <= inst.w1["bound"] and chk["ok"], (h, chk["errors"])


# ---------------------------------------------------------------- Theorems 3 and 4, and bound.py
def test_exact_u_matches_exact_load_only():
    for K, Sn, tl, te, p, L, Q, start in itertools.product([1, 2], [0, 1], [1, 2], [1, 2], [1, 2], [4, 6], [1, 2], ["any", "empty"]):
        Q = min(Q, K)
        a = max_delivery(L, p, Sn, K, 1, 1, tl, te, 0, Q=Q, G=0, start=start)
        assert a == max(o for o, _ in frontier(K, Sn, p, 1, 1, tl, te, [(0, L)], Q=Q, unload=False, start=start))


def test_theorem3_and_4_small():
    """Theorem 3 (unloading only) and Theorem 4 (unloading and load-out together) are not exceeded on a small grid; each of the
    three Theorem 3 terms has a case where it binds with equality."""
    hit = set()
    for K, Su, rho, tl, te, L, start in itertools.product([1, 2], [0, 1], [1, 2, 3], [1, 2], [1, 2], [3, 5, 8], ["any", "quay"]):
        x = max(u for _, u in frontier(K, 0, 1, 1, 1, 1, te, [], Su=Su, rho=rho, tl_u=tl, te_q=te, ramp=[(0, L)], load=False, start=start))
        t = B.unload_terms(L, rho, K, rho + min(1 if Su else 99, tl + 1 + te), tl, te, Su)
        assert x <= min(t.values())
        if x == min(t.values()) > 0:
            hit |= {k for k, v in t.items() if v == x}
    assert hit == {"ramp", "fleet", "cut"}
    for K, Sn, tl, rho, d, start in itertools.product([1, 2], [0, 1], [1, 2], [1, 2], [0, 2], ["any", "empty"]):
        for No, Nu in frontier(K, Sn, 1, 1, 1, tl, 1, [(0, 7)], rho=rho, tl_u=tl, te_q=1, ramp=[(d, d + 6)], start=start):
            assert No <= B.bound(B.lane(7, 1, Sn, K, 1, 1, tl, 1), 0 if start == "empty" else None)[0]
            assert B.joint_gap(No, Nu, Sn, 0, K, K, tl, tl, 1, 1, (0, 7 - 1 - (1 if Sn else 0)), (d + rho, d + 6)) >= 0


def test_zone_term_uses_full_return_occupancy():
    """With qe = 2 the q = 1 quay-zone term uses the full return occupancy: K = 2, S = 1, Q = 1, tl = 1, te = 3, L = 10; the
    quay-zone term changes from S + n(Δ) (spacing 1 + 1 + 1.5) to spacing 1 + 1 + 3, the bound tightens from 4 to 3, and the
    enumeration also gives 3."""
    P = B.lane(10, 1, 1, 2, 1, 1, 1, 3, Q=1, qe=2)
    assert P.te == 1.5 and P.te_occ == 3
    assert B.terms(P)["zone"] == 1 + 2 and B.bound(P)[0] == 3 == max_delivery(10, 1, 1, 2, 1, 1, 1, 3, Q=1, start="any", qe=2)


def test_cut_window_truncated_at_handover():
    """The loaded window on the cut is truncated at the handover: when the stop is closer to the gate than the vehicle-plus-cargo
    length, the tail window extends past the handover; after truncation dq ≥ 0 and tl ≤ travel + set-down."""
    c = cfg(Sn=0)
    D, net, p, *_ = S.setup(c)
    W = D["windport"]
    t = B.occupancy_times(net, dict(p, load_s=p["hp_s"], unload_s=0.0), W["storage"], W["cradles"][:1], 130.0, p["B"])
    cap, size = net.capacities(p)
    o, d = net.stops[W["storage"][0]], net.stops[W["cradles"][0]]
    TL = net.leg(o["node"], d["node"], p["v_loaded"], 130.0, p["B"], True, p, cap, size, d["res"], 1.0)[0]
    assert t["dq"] >= 0 and t["tl"] <= TL + 1e-6


def test_unload_times_on_archetype():
    """A1 unloading: ρ = empty drive onto the ramp + on-board operation + loaded drive off the ramp (including tail and clearance;
    stop-and-steer at the 90° turn at the ramp foot while the tail is still on the ramp); the cut is not the ramp; c_u > ρ."""
    c = cfg()
    D, net, p, *_ = S.setup(c)
    W = D["windport"]
    u = B.unload_times(net, dict(p, load_s=p["roro_s"], unload_s=p["hy_s"]), W["ramp"][0], W["storage"], p["Lv"], p["B"])
    ramp = W["params"]["ramp_m"]
    want = ramp / p["v_empty"] + p["roro_s"] + (ramp + p["Lv"] + p["long_clear"]) / p["v_loaded"] + \
        p["sweep_steer_s"] + (math.pi / 2) * p["Lv"] / 2 / p["v_loaded"]
    assert u["rho"] == pytest.approx(want, abs=1.0) and u["res"] not in u["ramp"] and u["res"][0] == "r" and u["c_u"] > u["rho"]
