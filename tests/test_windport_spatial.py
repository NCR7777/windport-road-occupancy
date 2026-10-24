"""The spatial additions: crane reach, cradle rows and passing place, alternative turning manoeuvres, reserved periods on the shared
segment (windport/sim4.py), W″ and the five regimes (windport/bound4.py), independent check (windport/check4.py, including broken
schedules), relaxed storage area, and small functions of the turn-sweep check and campaign duration."""
import copy
import math
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                        # noqa: E402
from windport import bound as WB                                 # noqa: E402
from windport import bound3 as B3                                # noqa: E402
from windport import bound4 as B4                                # noqa: E402
from windport import check4 as C4                                # noqa: E402
from windport import sim as S                                    # noqa: E402
from windport import sim2 as S2                                  # noqa: E402
from windport import sim4 as S4                                  # noqa: E402


def win_cfg(kind="A1", sc="base", mode="pull_in", K=2, S_=1, L=12, G=24, lift=None):
    return T.cfg_of("e4", T.enc(dict(kind=kind, scen=sc, mode=mode, lift=lift or T.lift_of(S_), rule="fcfs", L=L, K=K, S=S_, G=G)))


def port_cfg(geo, p, S_, K, n, lift="cradle", G=3):
    return dict(geo=geo, p=p, S=S_, K=K, lift=lift, horizon_h=G + 120, cal=dict(crane=[[G, G + 120]]), n_load=n, hold=0, rule="fcfs")


def run_check(c, net, p, sim, r=None):
    D, _, _, _, starts, quay, cal = S4.setup4(c)
    g, y = S2.idle_nodes(D)
    rv = None
    if r is not None and r.get("reserve"):
        rv = dict(res=tuple(r["reserve"]["res"].split("|")), f=r["reserve"]["f"], T=r["reserve"]["T"], H_end=(c["horizon_h"] + 1) * 3600.0)
    return C4.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y, reserve=rv)


def lifts(sim):
    return sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)


# ---------------------------------------------------------------- existing behaviour unchanged
@pytest.mark.parametrize("c", [win_cfg(), win_cfg(sc="lane", K=3, S_=3, mode="on_road"), win_cfg(S_=0), win_cfg(sc="lane", lift="mixed", K=3),
                               T.cfg_of("e6", T.enc(dict(kind="map:okpo", scen="base", mode="pull_in", lift="cradle", rule="fcfs", L=12, K=3, S=1, G=24)))])
def test_simulate4_without_extensions_equals_simulate2(c):
    S2._NETS.clear()
    _, _, sim2, r2 = S2.simulate2(copy.deepcopy(c))
    S2._NETS.clear()
    _, _, sim4, r4 = S4.simulate4(dict(copy.deepcopy(c), w4=False))
    assert sim2.trips == sim4.trips and r2["n_vessel"] == r4["n_vessel"]


def test_turnnet_equals_portnet_without_extra():
    c = win_cfg(sc="lane", K=2, S_=2)
    D, net, p, *_ = S4.setup4(c)
    assert isinstance(net, S4.TurnNet)
    cap, size = net.capacities(p)
    W = D["windport"]
    for o in W["storage"][:3]:
        for d in W["cradles"][:2]:
            so, sd = net.stops[o], net.stops[d]
            a = net.leg(so["node"], sd["node"], p["v_loaded"], p["Lv"], p["B"], True, p, cap, size, sd["res"], 1.0)
            b = S.PortNet.leg(net, so["node"], sd["node"], p["v_loaded"], p["Lv"], p["B"], True, p, cap, size, sd["res"], 1.0)
            assert a == b


# ---------------------------------------------------------------- port-type variants
def test_side_and_pass_layouts():
    D = S4.build_side(n_cradles=4, pitch_m=20.0, bay_m=40.0)
    W = D["windport"]
    assert W["layout"] == "side" and W["kind"] == "A1" and len(W["cradles"]) == 4
    assert sorted(f["roadId"] for f in D["zones"]["z_cradle"]["extensions"][S4.A.RS]["frontage"]) == [f"bay_{k}" for k in range(4)]
    P = S4.build_pass(**T.SCEN["lane"]["geo"])
    pw = P["windport"]["passing"]
    assert len(pw) == 1 and P["roads"][pw[0]]["widthM"]["value"] == 16.0
    assert all(P["roads"][r]["widthM"]["value"] == 10.0 for r in P["windport"]["corridor"])
    ys = sorted(P["nodes"][n]["position"][1] for n in (P["roads"][pw[0]]["fromNodeId"], P["roads"][pw[0]]["toNodeId"]))
    assert abs(ys[1] - ys[0] - 150.0) < 1e-6


def test_pass_and_widen_shorten_cut():
    """A passing place splits the cut of a long single lane in two; widened to 16 m, loaded and empty vehicles can pass each other
    (the cut no longer counts the return trip)."""
    base = win_cfg(sc="lane", K=3)
    pa = dict(copy.deepcopy(base), geo=dict(base["geo"], kind="A1pass"))
    wd = dict(copy.deepcopy(base), geo=dict(base["geo"], corridor_w=16.0))
    t = {k: B3.wprime_parts(dict(c))["P"] for k, c in (("base", base), ("pass", pa), ("wide", wd)) if S4.setup4(c)}
    assert t["pass"].tl < t["base"].tl
    assert t["wide"].te == 0.0 < t["base"].te


# ---------------------------------------------------------------- crane reach
def test_reach_far_lifts_take_longer_and_check():
    c = port_cfg(dict(kind="A1", n_cradles=4, cradle_mode="pull_in"), dict(reach=1, shift_s=1800.0), 3, 3, 8)
    net, p, sim, r = S4.simulate4(c)
    far = [x for x in sim.trips if x["s"] is not None and x["k"] >= 1]
    assert far and all(abs(x["F_vessel"] - x["s"] - 5400.0) < 1e-6 for x in far)
    assert all(abs(x["F_vessel"] - x["s"] - 3600.0) < 1e-6 for x in sim.trips if x["s"] is not None and x["k"] == 0)
    assert p["lift_s"] == 3600.0
    assert run_check(c, net, p, sim)["ok"]
    f = B4.wprime4_fn(c)
    G = 3 * 3600.0
    for n, t in enumerate(lifts(sim), 1):
        assert f(t - G) >= n


def test_check4_rejects_broken_reach_schedules():
    c = port_cfg(dict(kind="A1", n_cradles=4, cradle_mode="pull_in"), dict(reach=1, shift_s=1800.0), 3, 3, 8)
    net, p, sim, r = S4.simulate4(c)
    far = next(x for x in sim.trips if x["s"] is not None and x["k"] >= 1)
    x0 = dict(far)
    far["F_vessel"] = far["s"] + 3600.0                     # far cradle lifted in p: wrong
    assert not run_check(c, net, p, sim)["ok"]
    far.update(x0)
    nxt = min((x for x in sim.trips if x["s"] is not None and x["s"] > far["s"]), key=lambda x: x["s"])
    d = far["s"] + 3600.0 - nxt["s"]                         # next pile moved to start after p but before p + t_sh of the far lift: crane overlap
    if d < 0:
        for k in ("s", "F_vessel"):
            nxt[k] += d + 60.0
        assert any("crane" in e or "earlier than" in e or "F_vessel" in e for e in run_check(c, net, p, sim)["errors"])


def test_reach_term_is_monotone_and_binds():
    """The reach term is non-decreasing in L; with large t_sh, few near cradles and few vehicles (few hand-overs in the window, the
    cradles pre-staged far away need shifted lifts) it is tighter than W′."""
    c = port_cfg(dict(kind="A1", n_cradles=6, cradle_mode="pull_in"), dict(reach=1, shift_s=7200.0), 6, 1, 12, G=24)
    w = B4.parts4(c)
    P = w["P"]
    vals = [B4.reach_R(P, w["G"], x * 600.0, w["Sr"], w["sh"]) for x in range(0, 200)]
    assert all(b >= a for a, b in zip(vals, vals[1:]))
    f3, f = B3.wprime_fn(c, w), B4.wprime4_fn(c, w)
    assert any(f(L) < f3(L) for L in (3 * 3600.0, 6 * 3600.0, 12 * 3600.0, 24 * 3600.0))


def test_reach_dispatch_variants():
    """finish chooses the quay position by lift finish time, prestage uses only near cradles once the crane is open; both pass the
    checker and do not exceed W″."""
    out = {}
    for name, extra in (("start", {}), ("finish", dict(reach_key="finish")), ("prestage", dict(far_prestage=True))):
        c = win_cfg(K=2, S_=4)
        c["p"] = dict(c["p"], reach=1, shift_s=3600.0, **extra)
        net, p, sim, r = S4.simulate4(c)
        assert run_check(c, net, p, sim)["ok"]
        assert sum(r["n_vessel"]) <= r["w4"]["bound"]
        out[name] = sum(r["n_vessel"])
        if name == "prestage":
            G = c["cal"]["crane"][0][0] * 3600.0
            assert all(x["k"] < 1 for x in sim.trips if x["t0"] >= G - 1e-6 and x["flow"] == "load" and x["s"] is not None)
    assert out["finish"] >= out["start"]


def test_turn_extra_by_movement():
    """The key "node|from_road|to_road" only adds to this direction of turn."""
    c = win_cfg(K=2, S_=1)
    D, net, p, *_ = S4.setup4(c)
    W = D["windport"]
    path = net.path(net.stops[W["storage"][0]]["node"], net.stops[W["cradles"][0]]["node"])
    runs, dl = S.turn_delays(net, path, p["Lv"], p["v_loaded"], p)
    i = next(j for j in range(1, len(runs)) if dl[j])
    n = net.arc[runs[i][2]][0]
    right, wrong = f"{n}|{runs[i - 1][0]}|{runs[i][0]}", f"{n}|{runs[i][0]}|{runs[i - 1][0]}"
    a = S4.turn_delays4(net, path, p["Lv"], p["v_loaded"], dict(p, turn_extra={right: 500.0}))[1]
    b = S4.turn_delays4(net, path, p["Lv"], p["v_loaded"], dict(p, turn_extra={wrong: 500.0}))[1]
    assert abs(a[i] - dl[i] - 500.0) < 1e-9 and b == dl
    c2 = copy.deepcopy(c)
    c2["p"] = dict(c2["p"], turn_extra={right: 500.0})
    net2, p2, sim2, r2 = S4.simulate4(dict(c2, w4=False))
    assert run_check(c2, net2, p2, sim2)["ok"]


# ---------------------------------------------------------------- reserved periods
def test_open_pieces_fit():
    """Rounded down open piece by open piece; if an open piece is shorter than t_ℓ, not even one trip fits."""
    wins = S4.closures(3600.0, 0.9, 10 * 3600.0)             # open only 6 min per hour
    assert B4.open_pieces(0.0, 7200.0, wins) == pytest.approx([360.0, 360.0])
    assert B4.fit(0.0, 7200.0, wins, 400.0) == 0 < math.floor(B4.open_len(0.0, 7200.0, wins) / 400.0)
    assert B4.fit(0.0, 7200.0, [], 400.0) == 18
    vals = [B4.fit(0.0, x * 300.0, wins, 200.0) for x in range(0, 100)]
    assert all(b >= a for a, b in zip(vals, vals[1:]))


def test_open_len_and_reserve():
    wins = S4.closures(3600.0, 0.25, 10 * 3600.0)
    assert wins[0] == (0.0, 900.0) and wins[1] == (3600.0, 4500.0)
    assert B4.open_len(0.0, 7200.0, wins) == 5400.0
    assert B4.open_len(1000.0, 1000.0, wins) == 0.0


def test_reserve_sim_check_and_broken_schedule():
    c = T.cfg_of("e6", T.enc(dict(kind="map:okpo", scen="base", mode="pull_in", lift="cradle", rule="fcfs", L=12, K=3, S=1, G=24)))
    c["reserve"] = dict(f=0.5, T_h=2.0)
    net, p, sim, r = S4.simulate4(c)
    ck = run_check(c, net, p, sim, r)
    assert ck["ok"] and ck["n_res"] > 0
    assert sum(r["n_vessel"]) <= r["w4"]["bound"]
    rv = dict(res=tuple(r["reserve"]["res"].split("|")), f=0.5, T=7200.0, H_end=(c["horizon_h"] + 1) * 3600.0)
    D, _, _, _, starts, quay, cal = S4.setup4(c)
    g, y = S2.idle_nodes(D)
    j = min(range(len(sim.trips)), key=lambda i: sim.trips[i]["t1"])
    caught = 0
    for dt in range(-7200, 7201, 600):                       # shift the whole first trip: some shift always makes it hit a reserved period on the reserved segment
        bad = copy.deepcopy(sim.trips)
        x = bad[j]
        for k in ("t1", "a", "t2", "tc", "s", "r0", "F_quay", "F_vessel", "rel"):
            if x.get(k) is not None:
                x[k] += dt
        if x.get("exit"):
            x["exit"] = [x["exit"][0], x["exit"][1] + dt, x["exit"][2]]
        ck2 = C4.check(net, p, bad, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y, reserve=rv)
        caught += any("reserved" in e for e in ck2["errors"])
    assert caught > 0


def test_reserve_term_tightens_and_is_monotone():
    c = port_cfg(dict(kind="A1", n_cradles=6, cradle_mode="pull_in", **T.SCEN["lane"]["geo"]), dict(T.SCEN["lane"]["p"]), 1, 8, 12)
    c["reserve"] = dict(f=0.5, T_h=2.0)
    w = B4.parts4(c)
    assert w["rp"] is not None
    vals = [B4.reserve_R(w["rp"], 1, 8, w["G"], x * 900.0, 3600.0, w["hp"]) for x in range(0, 150)]
    assert all(b >= a for a, b in zip(vals, vals[1:]))
    net, p, sim, r = S4.simulate4(c)
    assert run_check(c, net, p, sim, r)["ok"]
    f = B4.wprime4_fn(c, w)
    for n, t in enumerate(lifts(sim), 1):
        assert f(t - w["G"]) >= n


# ---------------------------------------------------------------- alternative turning manoeuvres
def test_turn_extra_sim_and_check():
    c = win_cfg(K=2, S_=1)
    D, net, p, *_ = S4.setup4(c)
    nodes = sorted(D["nodes"])
    c2 = copy.deepcopy(c)
    c2["p"] = dict(c2["p"], turn_extra={n: 900.0 for n in nodes})
    net2, p2, sim2, r2 = S4.simulate4(dict(c2, w4=False))
    assert run_check(c2, net2, p2, sim2)["ok"]
    _, _, sim1, _ = S4.simulate4(dict(c, w4=False))
    assert run_check(c, net, p, sim1)["ok"]
    # a trip table computed without the alternative manoeuvres, checked under the rule with them: arrival times do not match
    D2, _, _, _, starts, quay, cal = S4.setup4(c2)
    g, y = S2.idle_nodes(D2)
    ck = C4.check(net2, p2, sim1.trips, starts, quay, cal, False, S.ramp_res(D2), 0, sim1.H, gate=g, yard=y)
    has_turn = any(dl for dl in S.turn_delays(net2, net2.path(net2.stops[D2["windport"]["storage"][0]]["node"],
                                                              net2.stops[D2["windport"]["cradles"][0]]["node"]), p2["Lv"], p2["v_loaded"], p2)[1])
    assert has_turn and not ck["ok"]


@pytest.mark.parametrize("c", [win_cfg(sc="lane", K=3), win_cfg(sc="longslow", K=5, S_=3),
                               dict(T.cfg_of("e6", T.enc(dict(kind="map:okpo", scen="slow", mode="pull_in", lift="cradle", rule="fcfs", L=12, K=2, S=1, G=24))),
                                    geo=dict(kind="map", site="okpo", cradle_mode="pull_in", n_cradles=6, storage="multi")),
                               dict(T.cfg_of("e6", T.enc(dict(kind="map:yantai", scen="base", mode="on_road", lift="cradle", rule="fcfs", L=12, K=4, S=1, G=3))),
                                    geo=dict(kind="map", site="yantai", cradle_mode="on_road", n_cradles=1, storage="multi"))])
def test_wprime_fast_equals_bound3(c):
    """bound4.wprime_fast (bisection on the serial-cut preparation term) agrees point by point with the existing bound3.wprime_fn."""
    S4.setup4(c)
    w = B3.wprime_parts(c)
    f, g = B3.wprime_fn(c, w), B4.wprime_fast(c, w)
    for x in [0.0, 900.0, 3599.0, 3600.0] + [k * 2700.0 for k in range(2, 60)]:
        assert f(x) == g(x), x


# ---------------------------------------------------------------- five regimes
@pytest.mark.parametrize("c", [win_cfg(), win_cfg(sc="lane", K=3), win_cfg(sc="lane", K=1, S_=3), win_cfg(S_=0, K=1, L=4, G=3),
                               win_cfg(sc="fastcrane", K=6, S_=6), win_cfg(sc="lane", lift="mixed", K=2, S_=1, L=4, G=3)])
def test_classify_consistent(c):
    w = B3.wprime_parts(c)
    L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * 3600.0
    cl = B4.classify(c, w)
    assert cl["wprime"] == B3.wprime_fn(c, w)(L)
    assert cl["cls"] in B4.CLASSES
    assert (cl["cls"] == "prep") == bool(cl["sub"])


# ---------------------------------------------------------------- site selection, turn check, campaign
@pytest.mark.skipif(not (ROOT / "experiments/windport_sites_multi.py").exists(), reason="site selection on the yard maps: not part of the release")
def test_sites_multi_follows_rule():
    import windport_sites as TS
    for site in ("okpo", "yantai"):
        TS.MIN_HA = 30 * 0.165
        try:
            assert TS.pick(site)[0] == S4.SITES_MULTI[site]
        finally:
            TS.MIN_HA = 1.65


def test_turn_geometry_helpers():
    import windport_turn_sweep as TT
    sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert TT.inside((5.0, 5.0), sq) and not TT.inside((15.0, 5.0), sq)
    g = TT.GRIDS["turn"]
    pts = TT.sweep_pts((0.0, 0.0), 0.0, math.pi / 2, 110.0, 9.5, g)
    assert max(math.hypot(x, y) for x, y in pts) <= math.hypot(55.0, 4.75) + 1e-6
    assert all(math.hypot(x, y) >= g["inner_m"] - 1e-6 for x, y in pts)
    obs = {"building": [(sq, (0.0, 0.0, 10.0, 10.0))]}
    assert TT.hits([(5.0, 5.0), (20.0, 20.0)], obs)["building"] == 1


def test_campaign_len_all_workable():
    import windport_spatial_analytic as AN
    g = dict(AN.GRIDS["campaign"])
    n = g["n_total"]
    t = AN.campaign_len(10.0, g, 10, [1] * 10000)
    assert abs(t - (6 * (10.0 + 2 * g["transit_h"]) + n * g["install_h"])) < 1e-9
    assert AN.campaign_len(12.0, g, 10, [1] * 10000) > t
