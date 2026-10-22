"""Port-time lower bound L* (windport/bound3.py), Muhabie-type single server, the cut as a single resource (windport/sim3.py)
and its independent check (windport/check3.py), consistency of the supplementary analysis script with the committed E3 results,
and code facts (turn angles, width thresholds)."""
import copy
import csv
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                        # noqa: E402
import windport_extra as X                                       # noqa: E402
from windport import bound3 as B3                                # noqa: E402
from windport import check3 as C3                                # noqa: E402
from windport import sim as S                                    # noqa: E402
from windport import sim2 as S2                                  # noqa: E402
from windport import sim3 as S3                                  # noqa: E402

E3 = ROOT / "results" / "runs/e3" / "points.csv"


def e3_rows():
    return {r["key"]: r for r in csv.DictReader(open(E3, encoding="utf-8"))}


def win_cfg(kind="A1", sc="base", mode="pull_in", K=2, S_=1, L=12, G=24, lift=None, hold=0):
    c = T.cfg_of("e4", T.enc(dict(kind=kind, scen=sc, mode=mode, lift=lift or T.lift_of(S_), rule="fcfs", L=L, K=K, S=S_, G=G)))
    c["hold"] = hold
    return c


CFGS = [win_cfg(), win_cfg(sc="lane"), win_cfg(sc="lane", mode="on_road", K=4, S_=3), win_cfg(S_=0), win_cfg(sc="lane", lift="mixed", K=3),
        win_cfg(kind="A2", sc="lane", K=3), win_cfg(kind="A3", sc="base", K=1, S_=2), win_cfg(sc="lane", hold=1, K=3), win_cfg(sc="longslow", K=5, L=6, G=3)]


@pytest.mark.parametrize("c", CFGS)
def test_wprime_matches_bounds2_and_is_monotone(c):
    D, net, p, *_ = S2.setup2(c)
    w = B3.wprime_parts(c)
    f = B3.wprime_fn(c, w)
    L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * 3600.0
    old = S2.bounds2(c, D, net, p)["bound"]
    assert f(L) >= old and (f(L) == old or w["P"].te_occ < w["te_occ0"] or w["P"].te < w["te0"])
    vals = [f(x * 900.0) for x in range(0, 200)]
    assert all(b >= a for a, b in zip(vals, vals[1:]))
    for n in (1, 3, 7):
        lo, hi = B3.lstar(f, n)
        assert f(lo) < n <= f(hi) and hi - lo <= 1e-3


def test_lstar_below_port_time_and_e3_reproduced():
    """port_cfg gives the same configuration as E3 (identical port time); L*(n) does not exceed the simulated port time."""
    rows = e3_rows()
    for key, (sc, mode, arr, K, n) in {"port|lane|pull_in|occ|n10|K2|S1|H0": ("lane", "pull_in", "S1", 2, 10),
                                       "port|base|on_road|occ|n3|K1|S0|H0": ("base", "on_road", "S0", 1, 3),
                                       "port|longslow|on_road|occ|n10|K3|S3|H0": ("longslow", "on_road", "S3", 3, 10)}.items():
        c = X.port_cfg(sc, mode, arr, K, n, 0)
        net, p, sim, r = S2.simulate2(c)
        ls = X.lifts_of(sim)
        ph = (ls[n - 1] - 24 * 3600.0) / 3600.0
        assert round(ph, 6) == float(rows[key]["port_h"])
        lo, _ = B3.lstar(B3.wprime_fn(c), n)
        assert lo / 3600.0 <= ph + 1e-9


def test_fix_group_reproduces_e3():
    rows = e3_rows()
    g = dict(X.GRIDS["fix"], K=[1, 2, 3])
    r = X.fix_group(dict(scen="base", mode="on_road", arr="S0", kref="1"), g)
    assert abs(r["factor"] - float(rows["fix|base|on_road|S0|R1|port10|K1"]["factor"])) < 1e-9
    for x in r["rows"]:
        assert round(x["port_h"], 6) == float(rows[f"fix|base|on_road|S0|R1|port10|K{x['K']}"]["port_h"])


def test_muhabie_hand():
    h = 3600.0
    assert B3.muhabie_port(10, 1, h, h, 24 * h) == pytest.approx(10 * h)
    # S = 0: the server delivers and waits for the lift to start; h = 2 h, p = 1 h, G = 0: lifts start at 2, 4, 6 h,
    # 3rd done at 7 h
    assert B3.muhabie_port(3, 0, 2 * h, h, 0.0) == pytest.approx(7 * h)
    # S = 1: after delivery to the cradle the server fetches the next item at once; the cradle frees when the lift starts;
    # h = 2 h, p = 1 h, G = 0: placed at 2, 4, 6 h, done at 7 h
    assert B3.muhabie_port(3, 1, 2 * h, h, 0.0) == pytest.approx(7 * h)
    # cradle full: the server waits holding the item; S = 1, h = 0.5 h, p = 2 h, G = 0: lifts start at 0.5, 2.5, 4.5 h,
    # 3rd done at 6.5 h
    assert B3.muhabie_port(3, 1, 0.5 * h, 2 * h, 0.0) == pytest.approx(6.5 * h)
    t = 13.5 * h
    hh = B3.muhabie_h(10, 1, h, 24 * h, t)
    assert B3.muhabie_port(10, 1, hh, h, 24 * h) <= t + 1e-6 < B3.muhabie_port(10, 1, hh + 1.0, h, 24 * h)


def cut_case(sc="lane", mode="pull_in", K=3, arr="S1", n=10, hold=0):
    c = X.port_cfg(sc, mode, arr, K, n, hold, fixed=True)
    net, p, sim, r = S3.simulate3(c)
    D, _, _, _, starts, quay, cal = S2.setup2(c)
    g, y = S2.idle_nodes(D)
    return c, net, p, sim, (starts, quay, cal, S.ramp_res(D), S.hold_of(c), g, y)


def test_cut_sim_semantics_and_checker():
    """On one whole single-lane section (long single lane), port time with the cut as a single resource equals the
    road-occupancy model (18.42 h); pure fixed durations give a shorter time. The checker passes and reports a broken
    schedule."""
    c, net, p, sim, (starts, quay, cal, ramp, hold, g, y) = cut_case()
    ph = (X.lifts_of(sim)[9] - 24 * 3600.0) / 3600.0
    assert ph == pytest.approx(18.417817, abs=1e-5)
    assert sim.cut == (frozenset({("r", "corr_lane_0")}),)
    ck = C3.check(net, p, sim.trips, starts, quay, cal, ramp, hold, sim.H, gate=g, yard=y)
    assert ck["ok"] and ck["n_lane"] > 0, ck
    bad = copy.deepcopy(sim.trips)
    tr = sorted((x for x in bad if x["t1"] < 1e8), key=lambda x: x["t2"])
    dt = tr[1]["t2"] - tr[0]["t2"] - 600.0                       # 2nd loaded trip moved to 10 min after the 1st enters the lane
    for k in ("t1", "a", "t2", "tc"):
        tr[1][k] -= dt
    ck2 = C3.check(net, p, bad, starts, quay, cal, ramp, hold, sim.H, gate=g, yard=y)
    assert not ck2["ok"] and any("single lane" in e for e in ck2["errors"])
    # pure fixed durations (single lane not enforced) are faster for the same configuration
    c2 = X.port_cfg("lane", "pull_in", "S1", 3, 10, 0, fixed=True)
    _, _, sim2, _ = S2.simulate2(c2)
    assert (X.lifts_of(sim2)[9] - 24 * 3600.0) / 3600.0 < ph - 1


@pytest.mark.parametrize("args", [dict(sc="longslow", K=4), dict(sc="base", mode="on_road", K=2, arr="S3m"), dict(sc="lane", K=5, hold="inf"),
                                  dict(sc="fastcrane", K=6, arr="S0")])
def test_cut_sim_checker_passes(args):
    c, net, p, sim, (starts, quay, cal, ramp, hold, g, y) = cut_case(**args)
    ck = C3.check(net, p, sim.trips, starts, quay, cal, ramp, hold, sim.H, gate=g, yard=y)
    assert ck["ok"], ck
    assert [set(g) for g in C3.lane_groups(net)] == [set(g) for g in sim.cut]


def test_sens_override_and_pub_cfg():
    k = [x for x in X.keys("sens") if "par=platlen" in x and "sub=e4" in x and "scen=base" in x][0]
    r = X.run_sens(T.dec(k), k)
    assert r["w1"]["te"] > 169.2 and r["check_ok"]
    k = [x for x in X.keys("pub") if x.startswith("pub=out|geo=ronne|mode=pull_in|arr=S1m|K=1")][0]
    r = X.run_pub(T.dec(k))
    assert r["check_ok"] and r["lstar_lo"] <= r["port_h"] + 1e-9
    assert sorted(r["how"]) != ["cradle"] * 3 or r["port_h"] >= 3.0


def test_facts_turns_and_widths():
    import windport_facts as F
    r = F.route_facts("A1", None, "pull_in")
    turns = r["loaded"][0]["turns"]
    assert [t["deg"] for t in turns] == [90.0, 90.0]
    assert turns[-1]["node"] == "corr_N" and not turns[-1]["junction"]
    assert turns[-1]["delta_s"][0] == pytest.approx(120 + math.pi / 2 * 55 / (2.5 / 3.6), abs=0.1)
    w = F.width_facts()
    assert w["threshold_loaded_empty_m"] == pytest.approx(15.36)
    assert not w["roads"]["apron 12 m"]["loaded_empty_pass"] and w["roads"]["double lane 20 m"]["two_loaded_pass"]


def test_return_route_correction_review_case():
    """Typical counterexample found in checking (case 9422 of the random generator rand_lstar: Okpo roadside, S = 1,
    Q_h = unlimited): W′ without the return-route correction is exceeded by 7 lifts; with it (return occupancy taken from the leg
    to the gate holding place) every lift is within the bound; return occupancy of the A1 report cells is unchanged."""
    from dataclasses import replace
    import windport_random_lift as R
    c = R.make("port", 9422)
    w = B3.wprime_parts(c)
    assert w["P"].te_occ < w["te_occ0"] - 100
    f, f0 = B3.wprime_fn(c, w), B3.wprime_fn(c, dict(w, P=replace(w["P"], te=w["te0"], te_occ=w["te_occ0"])))
    orig, S2.bounds2 = S2.bounds2, (lambda *a, **k: None)
    try:
        _, _, sim, _ = S2.simulate2(c)
    finally:
        S2.bounds2 = orig
    G = c["cal"]["crane"][0][0] * 3600.0
    T_ = sorted(x["F_vessel"] - G for x in sim.trips if x["F_vessel"] is not None)[:c["n_load"]]
    assert sum(1 for n, t in enumerate(T_, 1) if f0(t) < n) > 0
    assert all(f(t) >= n for n, t in enumerate(T_, 1))
    for hold in (0, 1, "inf"):
        w = B3.wprime_parts(X.port_cfg("lane", "on_road", "S1", 3, 10, hold))
        assert w["P"].te_occ == w["te_occ0"] and w["P"].te == w["te0"]


def test_prep_chain_long_window_and_cut_groups():
    c = X.port_cfg("longslow", "pull_in", "S1", 4, 10, 0, open_h=400)
    f = B3.wprime_fn(c)
    # prep_chain must not count past 10^4 in long windows; it stops at ⌊L/p⌋ + 1
    assert f(400 * 3600.0) <= 400
    c3 = X.port_cfg("lane", "pull_in", "S1", 3, 10, 0, fixed=True, geo_extra=dict(kind="A3"))
    net, p, sim, r = S3.simulate3(c3)
    assert len(sim.cut) == 2 and not (sim.cut[0] & sim.cut[1])
    D, _, _, _, starts, quay, cal = S2.setup2(c3)
    g, y = S2.idle_nodes(D)
    assert C3.check(net, p, sim.trips, starts, quay, cal, S.ramp_res(D), S.hold_of(c3), sim.H, gate=g, yard=y)["ok"]


def test_kassels_order_ronne_handling():
    """Rønne handling (h_p = 2 h, h_d = 0.5 h), one vehicle set, S = 1 mixed lifting: port time under the Kassels order equals the
    branch of the formula where the round trip and jacking to fetch the third item is ≥ 2p, and equals L*(3) (the rule-independent
    lower bound); first-come-first-served order is slower."""
    k = [x for x in X.keys("pub") if x.startswith("pub=out|geo=ronne|mode=pull_in|arr=S1m|K=1|hand=ronne")][0]
    r = X.run_pub(T.dec(k))
    assert r["check_ok"] and abs(r["kassels_h"] - r["lstar_lo"]) < 1e-3 and r["port_h"] > r["kassels_h"] + 0.3
