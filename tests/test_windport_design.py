"""Design analyses: geometry and duration of alternative turns, transfer network of the two-tier storage, lifting exclusion
zone of side-by-side cradles, invariance of the E6 grid, analytic part."""
import csv
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

CONSERVATIVE_E6 = ROOT / "results/runs/conservative_runs_e6/points.csv"
PATCHED = [("windport.sim", "PortSim"), ("windport.sim2", "ConvoySim"), ("windport.sim3", "CutSim"), ("windport.sim2", "build_map"),
           ("windport.sim2", "get_net"), ("windport.check", "check"), ("windport.archetypes", "build"), ("windport.archetypes", "GEOMETRY"),
           ("windport.bound2", "chain_times"), ("windport.bound2", "quay_side_Q"), ("windport.bound2", "zone_Q"), ("windport.sim4", "build_map4"),
           ("windport.lift", "under_res"), ("windport.check_lift", "under"), ("windport_spatial", "cfg_of"), ("windport_spatial", "turn_extra"),
           ("windport_extra", "kassels_order"), ("windport.sim", "get_net"), ("windport.sim4", "get_net4")]


@pytest.fixture(autouse=True)
def restore():
    """Semantics installed by each test (main2, conservative lifting, transfer network, exclusion zone, the cfg_of wrapper of
    the main2 geometry, etc.) are restored one by one after the test, and the network caches are cleared."""
    import importlib
    mods = {m: importlib.import_module(m) for m, _ in PATCHED}
    old = [(mods[m], a, getattr(mods[m], a)) for m, a in PATCHED]
    yield
    for mod, a, v in old:
        setattr(mod, a, v)
    from windport import sim as WS, sim2 as S2
    S2._NETS.clear()
    WS._NETS.clear()


def _env():
    import windport_design as X
    X.init_sims({})
    return X


@pytest.mark.skipif(not (ROOT / "results/runs/conservative_runs_e6/points.csv").exists(), reason="E6 rerun under the conservative lifting rule: not part of the release")
def test_e6_without_turn_extra_reproduces_conservative():
    """The E6 single point of the design analyses (TurnNet, joint checker, W″_lift recorded separately) without alternative
    manoeuvres matches the committed rows of the conservative-lifting-rule rerun column by column."""
    import windport_runs as T
    X = _env()
    old = {r["key"]: r for r in csv.DictReader(open(CONSERVATIVE_E6, encoding="utf-8"))}
    ks = T.keys("e6")
    for k in (ks[0], ks[1234], ks[4321], ks[-1]):
        r = X.e6_point("feas", k)
        row = T.row_of("e6", k, r)
        assert {c: str(row.get(c, "")) for c in T.COLS} == {c: old[k][c] for c in T.COLS}, k
        assert r["sim"] <= r["w2_lift"]


def test_turn_extra_lookup_and_levels():
    import windport_design_lib as L
    _env()
    assert L.turn_extra("okpo", "runs", "base", "feas") == {}
    lo, hi = L.turn_extra("okpo", "runs", "base", "lo"), L.turn_extra("okpo", "runs", "slow", "hi")
    assert set(lo) == set(hi) and len(lo) == 4                       # the 4 turns of the single-tier storage that fail the sector check (as in the spatial additions)
    assert all(hi[k] >= lo[k] >= 0 for k in lo)


def test_maneuver_search_on_synthetic_grid():
    """Empty site: in-place rotation feasible; obstacle in the north-east quadrant of the junction: in-place rotation blocked,
    the swept area of the alternative manoeuvre hits no obstacle and its duration is not negative."""
    import windport_turn_alt as TI
    J, L, B = (0.0, 0.0), 110.0, 9.5
    roads = [([(-300.0, 0.0), (0.0, 0.0)], 12.0), ([(0.0, 0.0), (0.0, 300.0)], 12.0)]
    sq = [(15.0, 15.0), (60.0, 15.0), (60.0, 60.0), (15.0, 60.0)]
    empty = dict(building=[], water=[], other=[])
    blocked = dict(building=[(sq, (15.0, 15.0, 60.0, 60.0))], water=[], other=[])
    sp = dict(base=2.5 / 3.6)
    r0 = TI.analyse(TI.Grid(J, empty, roads), J, 0.0, math.pi / 2, L, B, sp)
    assert r0["base_block"] == 0 and TI.classify(r0).startswith("in place")
    G = TI.Grid(J, blocked, roads)
    r1 = TI.analyse(G, J, 0.0, math.pi / 2, L, B, sp)
    assert r1["base_block"] > 0 and r1["n_feas"] > 0
    fam, best = TI.best_alt(r1, "base", 0)
    assert best["ok_fine"] == 1 and best["t"] >= 0
    # generic formula: reverse one pile length + crab by the road-width difference (at least B) + two switches
    v = 2.5 / 3.6
    assert TI.generic_s(L, B, v, 30.0, 12.0, 12.0) == pytest.approx(L / v + B / v + 60.0)


def test_grid_carves_roads():
    """Parts of obstacle polygons that overlap the road surface are not obstacles (map tracing error); parts off the road still count."""
    import windport_turn_alt as TI
    poly = [(-20.0, -20.0), (20.0, -20.0), (20.0, 20.0), (-20.0, 20.0)]
    G = TI.Grid((0.0, 0.0), dict(building=[(poly, (-20.0, -20.0, 20.0, 20.0))], water=[], other=[]), [([(-100.0, 0.0), (100.0, 0.0)], 10.0)])
    assert G.count(np.array([[0.0, 0.0], [10.0, 4.0]])) == 0
    assert G.count(np.array([[0.0, 10.0], [-15.0, -15.0]])) == 2


def test_transfer_network_and_bound():
    """Far → near transfer network: origin is the three-tier storage area, destinations are the road-side sections of the near
    yard; the simulated placement times satisfy W″_lift(T_j) ≥ j and the checker passes."""
    import windport_design_lib as L
    from windport import sim4 as S4
    X = _env()
    c = L.transfer_cfg("okpo", 2, 10, {})
    D, net, *_ = S4.setup4(c)
    W = D["windport"]
    assert W["transfer"] == dict(far="zone_trace_001", near="zone_trace_027") and len(W["cradles"]) == len(L.near_slots("okpo")) == 4
    r = X.port_point(c)
    assert r["check_ok"] == 1 and r["viol"] == 0 and r["port_h"] >= r["lstar_lo"] - 1e-9


def test_rows_exclusion_sim_and_checker_agree():
    """When lifting from row k of side-by-side cradles, rows 0…k−1 are also below the load: the simulation side
    (lift.under_res) and the checker side (check_lift.under) give the same segments; with the rule in the checker but not in
    the simulation, the checker detects the load passing over an occupied nearer row."""
    import windport_rows_exclusion as RX
    import windport_runs as T
    import windport_spatial as TA
    from windport import check_all as CA
    from windport import check_lift as CL
    from windport import lift as LF
    from windport import sim as S
    from windport import sim2 as S2
    from windport import sim4 as S4
    RX.install(False)
    key = "lay=side|kind=A1side|scen=lane|mode=side|lift=cradle|rule=fcfs|reach=all|L=12|K=3|S=3|G=24"
    c = dict(TA.cfg_of("reach", T.dec(key)), w4=False)
    net, p, sim, _ = S4.simulate4(c)
    D, _, _, _, starts, quay, cal = S4.setup4(c)
    g, y = S2.idle_nodes(D)
    base_s, base_c = LF.under_res, CL.under
    try:
        RX.install_rows_exclusion(sim=False, check=True)
        ck = CA.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
        assert not ck["ok"] and "row_" in ck["errors"][0]
        RX.install_rows_exclusion(sim=True, check=False)
        k2 = [s for s in quay if net.stops[s]["node"].split("|")[1] == "row_2"][0]
        a = {x for x in LF.under_res(net, k2, p["Lv"], True) if x[0] == "r"}
        b = {x for x in CL.under(net, k2, p["Lv"], True) if x[0] == "r"}
        assert a == b and {x[1].split("#")[0] for x in a} >= {"row_0", "row_1", "row_2"}
        net, p, sim, _ = S4.simulate4(c)
        ck = CA.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
        assert ck["ok"], ck["errors"][:2]
    finally:
        LF.under_res, CL.under = base_s, base_c


@pytest.mark.skipif(not (ROOT / "results/runs/survey/haulpaths.json").exists(), reason="haul paths measured on imagery: not part of the release")
def test_eemshaven_threshold_is_a_crossing():
    """Eemshaven: τ_cut / p lies on opposite sides of 1 on the two sides of the speed threshold (occupancy-time formula, monotone)."""
    import windport_analytic as A6
    import windport_design_analytic as AN
    import windport_survey as TS
    import json
    from windport import sim2 as S2
    h = TS.haul_survey(json.loads(TS.HAUL.read_text(encoding="utf-8")))["eemshaven_gw3"]
    rows = [r for r in csv.DictReader(open(sorted(ROOT.glob("results/windport_design_analytic_*/eem.csv"))[0], encoding="utf-8"))
            if r["geometry"] == "legacy40" and r["mode"] == "on_road"]
    v = float(rows[0]["v_cut"])
    S2._NETS.clear()
    lo = A6.tau(AN.eem_cfg(h["len_m"], h["lane_m"], "on_road", v - 0.01))["cut"]
    hi = A6.tau(AN.eem_cfg(h["len_m"], h["lane_m"], "on_road", v + 0.01))["cut"]
    assert lo > 3600.0 > hi


@pytest.mark.skipif(not sorted(ROOT.glob("results/windport_design_analytic_*/campaign.csv")), reason="run experiments/windport_design_analytic.py first (its eem part needs the imagery haul paths, not part of the release)")
def test_campaign_reproduces_paper_numbers():
    """Campaign model: the parameter table reproduces the manuscript's 1.21–1.22 days (long single lane, two groups, one vessel
    with 10 piles, q = 0.6 / 0.8)."""
    rows = list(csv.DictReader(open(sorted(ROOT.glob("results/windport_design_analytic_*/campaign.csv"))[0], encoding="utf-8")))
    got = sorted(round(float(r["diff_mean"]), 2) for r in rows if r["scen"] == "lane" and r["n_v"] == "10" and r["K"] == "2")
    assert got == [1.21, 1.22]


def test_net_cache_keys_on_build_params():
    """In one process, networks with 75 m and 300 m blocks built one after the other for the same geo have 16 and 4 blocks
    (windport_netcache wraps the network cache); without it, the second build reuses the first network."""
    import windport_netcache as NC
    import windport_runs as T
    import windport_codesign_blocks2 as B2
    from windport import sim as WS, sim2 as S2, sim4 as S4
    X = _env()
    k = next(k for k in B2.keys() if k.endswith("|blk=75"))
    c75, c300 = B2.cfg(T.dec(k)), B2.cfg(T.dec(k.replace("blk=75", "blk=300")))
    c0 = X.cd_cfg(T.dec(k.split("|blk=")[0].replace("|disp=finish", "")))
    assert c75["geo"] == c300["geo"] == c0["geo"]
    nblk = lambda c: len(S4.get_net4(c["geo"], WS.params(c))[1].sec.get("corr_lane_0", ["corr_lane_0"]))
    S2._NETS.clear()
    assert (nblk(c75), nblk(c300)) == (16, 16)          # before the fix: the 75 m network built first is reused
    NC.install()
    S2._NETS.clear()
    assert (nblk(c75), nblk(c300), nblk(c0), nblk(c75)) == (16, 4, 1, 16)
    a, b = S2.get_net(c0["geo"], WS.params(c0))[1], S2.get_net(c300["geo"], WS.params(c300))[1]
    assert a is not b and set(a.road) != set(b.road)     # networks differ before and after the rebuild
