"""Unified bound: the unified entry (windport/bound_all.py) equals each branch function value by value within its scope; combined
checker (windport/check_all.py); committed results reproduce byte for byte."""
import csv
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                        # noqa: E402
import windport_extra as X                       # noqa: E402
from windport import bound3 as B3                # noqa: E402
from windport import bound4 as B4                # noqa: E402
from windport import bound_all as BA             # noqa: E402
from windport import bound_dead as BD            # noqa: E402
from windport import bound_lift as BL            # noqa: E402
from windport import check_all as CA             # noqa: E402
from windport import lift as LF                  # noqa: E402
from windport import sim as S                    # noqa: E402
from windport import sim2 as S2                  # noqa: E402
from windport import sim4 as S4                  # noqa: E402

H = 3600.0
GRID = [x * 900.0 for x in range(0, 120)] + [3600.0 - 54.0, 3600.0 + 1.0, 3654.0, 7254.0]


def e4(kind="A1", sc="base", mode="pull_in", S_=1, K=2, L=12, G=24, lift=None):
    return T.cfg_of("e4", T.enc(dict(kind=kind, scen=sc, mode=mode, lift=lift or T.lift_of(S_), rule="fcfs", L=L, K=K, S=S_, G=G)))


PLAIN = [X.port_cfg("lane", "on_road", "S1", 2, 10, 0), X.port_cfg("lane", "pull_in", "S0", 3, 10, 0), X.port_cfg("lane", "on_road", "S1m", 3, 10, 0),
         X.port_cfg("longslow", "pull_in", "S3", 4, 10, 0), X.port_cfg("lane", "on_road", "S3m", 2, 10, 1), e4("A2", "lane", "on_road", 2, 3),
         e4("A3", "base", "pull_in", 0, 2), X.port_cfg("fastcrane", "pull_in", "S1", 1, 10, "inf")]


@pytest.mark.parametrize("c", PLAIN)
def test_unified_equals_branches_without_extensions(c):
    """Without crane reach and reserved periods: W″ = bound_dead.wfn4 (dead-end coupling), W″_lift = bound_lift.wfn_lift (conservative
    lifting rule), value by value (incl. L < p and near ε_U)."""
    f, g, f0, g0 = BA.w2(c), BA.w2_lift(c), BD.wfn4(c), BL.wfn_lift(c)
    for L in GRID:
        assert f(L) == f0(L), L
        assert g(L) == g0(L), L
        assert g(L) <= f(L)


def test_unified_on_map_equals_branch():
    """Okpo map with relaxed storage area (series-cut terms by fast bisection): equal to the branches value by value."""
    c = T.cfg_of("e6", T.enc(dict(kind="map:okpo", scen="base", mode="pull_in", lift="cradle", rule="fcfs", L=12, K=2, S=1, G=24)))
    c["geo"] = dict(c["geo"], storage="multi")
    f, g, f0, g0 = BA.w2(c), BA.w2_lift(c), BD.wfn4(c), BL.wfn_lift(c)
    for L in (4 * H, 12 * H, 15 * H):
        assert f(L) == f0(L) and g(L) == g0(L)


def test_reach_and_reserve_terms_match_spatial():
    """Crane reach and reserved periods: with the parameters of W′ equal to bound4.reach_R, reserve_R value by value; unified
    W″ = min(branch W″, both terms), and not above the W″ of the spatial additions."""
    c = e4("A1", "base", "pull_in", 6, 1)
    c["p"] = dict(c["p"], reach=1, shift_s=7200.0)
    c["reserve"] = dict(f=0.5, T_h=1.0)
    w, w3 = BA.parts(c), B4.parts4(c)
    f, fa, f0 = BA.w2(c, w), B4.wprime4_fn(c, w3), BD.wfn4(c)
    for L in GRID:
        assert BA.reach(w3["P"], w3["G"], L, L, w3["Sr"], w3["sh"]) == B4.reach_R(w3["P"], w3["G"], L, w3["Sr"], w3["sh"])
        assert min(BA.reserve(w3["rp"], 6, 1, w3["G"], L, w3["P"].p, w3["hp"])) == B4.reserve_R(w3["rp"], 6, 1, w3["G"], L, w3["P"].p, w3["hp"])
        t = BA.terms(w, L)
        assert f(L) == min(f0(L), t.get("reach", 1e9), t.get("reserve", 1e9), t.get("reserve_pre", 1e9))
        assert f(L) <= fa(L)
    assert any(BA.terms(w, L).get("reach", 1e9) < f0(L) for L in GRID)


def test_monotone_and_lift_below_plain():
    """W″ and W″_lift are non-decreasing in L, W″_lift ≤ W″ (incl. crane reach, reserved periods, pull-in / on-road, cradle ε_U)."""
    cs = PLAIN[:4]
    c = e4("A1", "lane", "on_road", 4, 2)
    c["p"] = dict(c["p"], reach=2, shift_s=1800.0)
    c["reserve"] = dict(f=0.25, T_h=2.0)
    for c in cs + [c]:
        f, g = BA.w2(c), BA.w2_lift(c)
        a, b = [f(L) for L in sorted(GRID)], [g(L) for L in sorted(GRID)]
        assert all(y >= x for x, y in zip(a, a[1:])) and all(y >= x for x, y in zip(b, b[1:]))
        assert all(y <= x for x, y in zip(a, b))


def test_core_values():
    """Core example: L″*(10) original rule 18.4178 h (dead-end coupling); conservative rule 18.6425 h (cradle S = 1) and 17.0175 h
    (pull-in direct lift) (conservative lifting rule)."""
    lo = lambda c, lift: BA.lstar(BA.w2_lift(c) if lift else BA.w2(c), 10)[1] / H
    assert abs(lo(X.port_cfg("lane", "on_road", "S1", 2, 10, 0), False) - 18.4178) < 1e-3
    assert abs(lo(X.port_cfg("lane", "pull_in", "S1", 4, 10, 0), True) - 18.6425) < 1e-3
    assert abs(lo(X.port_cfg("lane", "pull_in", "S0", 2, 10, 0), True) - 17.0175) < 1e-3


def test_binding_classes():
    """Five case classes: the crane-reach term counts as crane, reserved periods as road; otherwise the order of bound4.classify."""
    t = dict(interface=12, fleet=12, reach=10, cut=20, prep_fleet=30)
    assert BA.binding(t)[2] == "crane"
    t = dict(interface=12, fleet=12, reserve=9, prep_fleet=30)
    assert BA.binding(t)[2] == "road"
    t = dict(interface=12, fleet=12, reserve=19, reserve_pre=8, prep_fleet=30)
    assert BA.binding(t)[2:4] == ("prep", "reserve_pre")
    for c in (e4("A1", "base", "pull_in", 2, 3, L=6), e4("A1", "lane", "on_road", 3, 2, L=4, G=3), e4("A1", "fastcrane", "pull_in", 1, 2)):
        cl = B4.classify(c)
        v, keys, cls, sub, nat = BA.binding(BA.terms(BA.parts(c), (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * H))
        if v == cl["wprime"] and keys == sorted(cl["binding"].split("+")):        # no new term binds: as in bound4.classify
            assert cls == dict(turnover="cradle").get(cl["cls"], cl["cls"]) and nat == dict(turnover="cradle").get(cl["nature"], cl["nature"])
            ok = True
    assert ok


def _sim(c, lift):
    with (LF.installed() if lift else __import__("contextlib").nullcontext()):
        net, p, sim, r = S4.simulate4(dict(c, w4=False))
        D, _, _, _, starts, quay, cal = S4.setup4(c)
    g, y = S2.idle_nodes(D)
    return net, p, sim, (starts, quay, cal, S.ramp_res(D), S.hold_of(c), g, y)


def test_check_all_passes_and_catches_breaks():
    """Conservative rule + crane reach: the combined checker passes; a far lift finished in p and a direct lift started before the
    vehicle body has left the road are both reported."""
    c = e4("A1", "lane", "pull_in", 3, 3)
    c["p"] = dict(c["p"], reach=1, shift_s=1800.0)
    c["lift"] = "mixed"
    net, p, sim, (st, q, cal, ramp, hold, g, y) = _sim(c, True)
    ck = lambda tr: CA.check(net, p, tr, st, q, cal, False, ramp, hold, sim.H, gate=g, yard=y)
    r = ck(sim.trips)
    assert r["ok"], r["errors"]
    assert r["n_far"] > 0 and r["n_under"] > 0
    far = next(x for x in sim.trips if x.get("k") is not None and x["k"] >= 1 and x.get("s") is not None)
    bad = [dict(x, F_vessel=x["s"] + p["lift_s"]) if x is far else x for x in sim.trips]
    assert not ck(bad)["ok"]
    c2 = X.port_cfg("lane", "on_road", "S0", 2, 10, 0)
    net, p, sim, (st, q, cal, ramp, hold, g, y) = _sim(c2, False)            # original rule: lift with tail on the lane
    r = CA.check(net, p, sim.trips, st, q, cal, False, ramp, hold, sim.H, gate=g, yard=y)
    assert any("before the vehicle body left the road" in e for e in r["errors"])


def _line(cols, row):
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, extrasaction="raise", lineterminator="\n")
    w.writerow(row)
    return buf.getvalue().rstrip("\n")


@pytest.mark.skipif(not (ROOT / "results/runs/spatial_reach/points.csv").exists(), reason="batches of the spatial additions: not part of the release")
def test_committed_rows_reproduce():
    """Committed run directories reproduce byte for byte (branch modules unchanged): two reach rows of the spatial additions (original
    rule), two e4 rows of the conservative-rule rerun, and the bound columns of the dead-end-coupling and conservative-rule rechecks."""
    import windport_spatial as A
    import windport_rerun_conservative as RR
    lines = (ROOT / "results/runs/spatial_reach/points.csv").read_text(encoding="utf-8").splitlines()
    cols = lines[0].split(",")
    for line in (lines[1], lines[4000]):
        key = next(csv.DictReader([lines[0], line]))["key"]
        assert _line(cols, A.row_of(key, A.run_point("reach", key))) == line
    lines = (ROOT / "results/runs/conservative_runs_e4/points.csv").read_text(encoding="utf-8").splitlines()
    cols = lines[0].split(",")
    from windport import check as C
    from windport import check_lift as CL
    with LF.installed():
        old, C.check = C.check, CL.check
        try:
            for line in (lines[7], lines[9000]):
                key = next(csv.DictReader([lines[0], line]))["key"]
                assert _line(cols, RR.rows("runs:e4", key, RR.compute("runs:e4", key))[0]) == line
        finally:
            C.check = old
    import windport_recheck_deadend as RB
    rows = list(csv.DictReader(open(ROOT / "results/runs/deadend_recheck/rows.csv", encoding="utf-8")))
    for r in (rows[3], rows[60000], rows[140000]):
        if r["form"] != "win" or r["batch"] == "runs:random":
            continue
        c, _ = RB.cfg_of(r["batch"], dict(key=r["key"]))
        L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * H
        assert BA.w2(c)(L) == int(r["new"])
    rows = list(csv.DictReader(open(ROOT / "results/runs/conservative_recheck/rows.csv", encoding="utf-8")))
    import windport_recheck_conservative as RD
    for r in (rows[5], rows[50000], rows[100000]):
        if r["form"] != "win":
            continue
        c, _ = RD.cfg_of(r["batch"], dict(key=r["key"]))
        L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * H
        assert BA.w2_lift(c)(L) == int(r["b_lift"])
