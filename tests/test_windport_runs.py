"""windport/sim2.py (off-road waiting pocket, convoy dispatch, shipyard-derived maps), windport/bound2.py (W1′: serial cuts,
geometric quay zone Q, vehicle-time conservation), windport/check2.py (assumption checks), windport/exact_chain.py (two-block
chain enumeration).
Broken schedules must all be reported by the independent checker: a convoy-dispatch exit moved before the release, an exit moved
into another vehicle's window on the single lane, a pocket exit relabelled to the south end of the single lane."""
import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from windport import bound2 as W2                   # noqa: E402
from windport import check as C                     # noqa: E402
from windport import check2 as C2                   # noqa: E402
from windport import exact_chain as X               # noqa: E402
from windport import sim as S                       # noqa: E402
from windport import sim2 as S2                     # noqa: E402

KMH = 1 / 3.6
LONG = dict(dist_m=1500.0, corridor_m=1200.0)


def cfg(kind="A1", mode="pull_in", K=3, Sn=2, L=5, G=3, rule="fcfs", pocket=None, hold=0, geo=None, p=None, lift="cradle"):
    g = dict(dict(kind=kind, n_cradles=6, cradle_mode=mode), **(geo or {}))
    if pocket:
        g["pocket"] = pocket
    return dict(geo=g, p=dict(p or {}), S=Sn, K=K, lift=lift if Sn else "cradle", horizon_h=G + L + 1, cal=dict(crane=[[G, G + L]]),
                n_load=int(L) + K + Sn + 2, hold=hold, rule=rule)


def checked(c, trips=None, sim=None):
    D, net, p, tasks, starts, quay, cal = S2.setup2(c)
    g, y = S2.idle_nodes(D)
    return C.check(net, p, sim.trips if trips is None else trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)


LONGSLOW = dict(geo=LONG, p=dict(v_loaded=1.0 * KMH))


def test_fcfs_without_pocket_matches_sim():
    for c in (cfg(), cfg(mode="on_road", K=2, Sn=1, L=12, **LONGSLOW), cfg(kind="A2", K=4, Sn=0, L=6), cfg(kind="A3", K=3, Sn=3, L=8, hold=1)):
        a = S.simulate(copy.deepcopy(c))[2].trips
        b = S2.simulate2(copy.deepcopy(c))[2].trips
        assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_pocket_geometry_and_checker():
    D = S2.build_map(dict(kind="A1", n_cradles=4, pocket=30.0))
    pid = D["windport"]["pocket"]
    assert D["nodes"][pid]["kind"] == "endpoint" and D["roads"][f"{pid}_stub"]["fromNodeId"] == S.yard_node(D)
    assert any(m["outgoingArc"]["roadId"] == f"{pid}_stub" and m["allowed"] for m in D["movements"].values())
    c = cfg(mode="pull_in", K=3, Sn=2, L=12, pocket=30.0, **LONGSLOW)
    net, p, sim, r = S2.simulate2(c)
    assert all(x["exit"][0] == pid for x in sim.trips if x["exit"])
    assert checked(c, sim=sim)["ok"]
    bad = copy.deepcopy(sim.trips)                       # broken: pocket exit relabelled to lane south end
    x = next(x for x in bad if x["exit"])
    x["exit"][0] = S.yard_node(S2.build_map(c["geo"]))
    assert not checked(c, trips=bad, sim=sim)["ok"]


def test_convoy_forms_and_checker_catches_mutations():
    # E2 case pull_in|longslow|K2|S2|L5|G3|H0: CP-SAT proves optimum 3, fcfs gives 2
    c = cfg(mode="pull_in", K=2, Sn=2, L=5, G=3, **LONGSLOW)
    nf = sum(S2.simulate2(dict(c))[3]["n_vessel"])
    net, p, sim, r = S2.simulate2(dict(c, rule="convoy"))
    assert sum(r["n_vessel"]) == 3 > nf and sim.bumps > 0
    assert checked(c, sim=sim)["ok"]
    ch = r["w1g"]["chain"]
    h = C2.hyp(net, p, sim.trips, S2.setup2(c)[4], ch["res"].split("|"), tuple(r["w1"]["cut"].split("|")))
    assert h["opp"] == 0 and h["phase"] <= ch["bmax"] and h["zone"] <= r["w1g"]["Q"]
    bad = copy.deepcopy(sim.trips)                       # broken 1: exit moved before the release
    x = next(x for x in bad if x["exit"] and x["r0"] is not None and x["exit"][1] > x["r0"] + 600)
    x["exit"][1] = x["r0"] - 60.0
    assert not checked(c, trips=bad, sim=sim)["ok"]
    bad = copy.deepcopy(sim.trips)                       # broken 2: yielded exits moved back (lane conflict)
    ys = sorted((x for x in bad if x["exit"] and x["r0"] is not None and x["exit"][1] > x["r0"] + 600), key=lambda x: x["r0"])
    for x in ys:
        x["rel"] -= x["exit"][1] - x["r0"]
        x["exit"][1] = x["r0"]
    assert not checked(c, trips=bad, sim=sim)["ok"]


def test_w1g_never_below_cpsat_examples():
    """Three E2 cases with CP-SAT-proven optima (results/runs/e2): W1′ is not below them and is tight at the
    optimum in the first case."""
    for kw, opt, w1 in ((dict(mode="pull_in", K=3, Sn=2, L=5, G=3, **LONGSLOW), 4, 5), (dict(mode="on_road", K=2, Sn=1, L=5, G=3, **LONGSLOW), 2, None),
                        (dict(mode="pull_in", K=1, Sn=0, L=3, G=1), 2, None)):
        r = S2.simulate2(cfg(**kw))[3]
        assert r["w1g"]["bound"] >= opt and r["w1g"]["bound"] <= r["w1"]["bound"]
        if w1:
            assert r["w1"]["bound"] == w1 and r["w1g"]["bound"] == opt


def test_serial_cut_exhaustive_small():
    """Two-block chain: exact value ≤ min(W1, Π_S); with Qs = 1 there is a case where Π_S is tighter than W1 with a single block
    as the cut and is attained."""
    from windport_chain_check import bounds
    tighter = 0
    for K, Sn, Qs, a1, a2, e, L in ((2, 1, 1, 1, 3, 1, 9), (2, 0, 1, 1, 1, 2, 9), (3, 2, 2, 3, 1, 1, 9), (3, 1, 1, 3, 3, 2, 9), (2, 2, 2, 1, 3, 2, 5)):
        x = dict(K=K, S=Sn, Qs=Qs, hp=1, a1=a1, a2=a2, e=e, hd=1, p=1, G=4, L=L)
        n = X.max_delivery(K, Sn, Qs, 1, a1, a2, e, e, 1, 1, 4, L, 1)
        (w1, _), pi = bounds(x)
        assert n <= min(w1, pi), x
        tighter += pi < w1 and pi == n
    assert tighter >= 1


def test_vehicle_time_bound_shared_fleet():
    for K, x in ((2, 1.0), (4, 0.5), (3, 1.0)):
        c = cfg(mode="pull_in", K=K, Sn=1, L=24, G=24)
        u0 = 24 + (1 - x) * 24
        c["p"].update(roro_s=3 * 3600.0, unload_first=True)
        c["cal"]["ramp"] = [[u0, u0 + 24]]
        c.update(K_u=0, n_unload=9, unload_release_h=[u0] * 9, joint_cut="corr_lane_0", horizon_h=max(48, u0 + 24) + 1)
        net, p, sim, r = S2.simulate2(c)
        assert sum(r["n_vessel"]) + sum(r["n_ramp"]) <= r["joint_ub"]["ub"]
        assert checked(c, sim=sim)["ok"]


def test_guard_condition_on_archetypes():
    """A1 pull-in: after the chain head there is only the apron section, exclusive between loaded and empty vehicles, and it is
    the first section of the exit, so a guard exists; with a gate holding place, or when the return avoids the chain (A2),
    b_max = K."""
    for kind, hold, want_finite in (("A1", 0, True), ("A1", 1, False), ("A2", 0, False)):
        c = cfg(kind=kind, mode="pull_in", K=3, Sn=2, L=5, hold=hold, **LONGSLOW)
        r = S2.simulate2(c)[3]
        ch = r["w1g"]["chain"]
        assert (ch is not None and ch["bmax"] < c["K"]) == want_finite, (kind, hold, ch)


def test_guard_checks_model_facts():
    """Besides the guard road g itself: a quay-stop reservation later than entering g, or having already left g when exiting the
    chain head, both count as no guard."""
    cap = {("r", "T"): 11.0, ("r", "g"): 13.0}
    p = dict(lat_clear=1.0, plat_w=4.86)
    ex = [[(("r", "g"), 0.0, 10.0), (("r", "T"), 10.0, 50.0)]]
    good = (["r_T", ("r", "T"), ("r", "g")][1:], ("b", "z", 0), {("r", "T"): (0.0, 100.0), ("r", "g"): (90.0, 200.0)}, 90.0)
    assert W2._guard(cap, p, 9.5, ("r", "T"), [good], ex)
    late = (good[0], good[1], good[2], 95.0)                         # quay-stop reservation later than entering g
    assert not W2._guard(cap, p, 9.5, ("r", "T"), [late], ex)
    gone = (good[0], good[1], {("r", "T"): (0.0, 100.0), ("r", "g"): (90.0, 99.0)}, 90.0)     # left g before chain-head exit
    assert not W2._guard(cap, p, 9.5, ("r", "T"), [gone], ex)


def test_random_ports_small():
    """Random archetype and shipyard cases (the shipyards from the derived graphs of data/networks/)."""
    import windport_random as R
    for i in list(range(60)) + [7, 432, 8072, 2292]:
        r = R.work(i)
        assert not R.bad_of(r), (i, r)


def test_shipyard_run_from_derived_graph():
    """A shipyard point runs on the derived graph (no coordinates), passes the checker and stays below W1′ ≤ W1."""
    from windport import shipyard as SY
    c = dict(geo=dict(kind="map", site="okpo", cradle_mode="pull_in", n_cradles=6), p={}, S=2, K=3, horizon_h=16, cal=dict(crane=[[3, 15]]),
             n_load=17, hold=0, rule="convoy")
    net, p, sim, r = S2.simulate2(c)
    assert checked(c, sim=sim)["ok"] and sum(r["n_vessel"]) <= r["w1g"]["bound"] <= r["w1"]["bound"]
    D = S2.setup2(c)[0]
    assert not any("position" in n for n in D["nodes"].values()) and not any("geometry" in x for x in D["roads"].values())
    assert D["windport"]["source"]["network"] == "data/networks/" + SY.NETWORK["okpo"] and D["windport"]["pocket"] == "pocket"
