"""main2 geometry (windport/main2.py: side-by-side cradles rebuilt from their real placement as rows parallel to the quay line, unloading ramp in
line with the apron, bound extension for multi-row dead ends).
The legacy geometry (legacy40) and main keep their maps and bounds byte for byte / value for value; main2 changes only the side-by-side cradles and
one node at the ramp top of A1 and A2, the loading network is unchanged; geometry check; the rebuilt side-by-side core case with S = 1 equals the
rule-independent lower bound; detection of the tree premise and the tightening; committed main-geometry rows reproduce byte for byte under main2."""
import pytest
import contextlib
import csv
import io
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                        # noqa: E402
import windport_extra as X                       # noqa: E402
import windport_spatial as TA                      # noqa: E402
from windport import archetypes as A             # noqa: E402
from windport import bound2 as W2                # noqa: E402
from windport import bound_all as BA             # noqa: E402
from windport import geomcheck as GC             # noqa: E402
from windport import lift as LF                  # noqa: E402
from windport import main2 as M2                 # noqa: E402
from windport import sim as WS                   # noqa: E402
from windport import sim2 as S2                  # noqa: E402
from windport import sim4 as S4                  # noqa: E402

H = 3600.0


@contextlib.contextmanager
def main2():
    """Install main2 and the conservative lifting rule; on exit restore the geometry, archetypes.build, the three bound2 functions and the caches."""
    old = A.build, W2.chain_times, W2.quay_side_Q, W2.zone_Q, A.GEOMETRY
    try:
        with LF.installed():
            M2.use()
            yield
    finally:
        A.build, W2.chain_times, W2.quay_side_Q, W2.zone_Q = old[:4]
        A.use(next(k for k, v in A.GEOMETRIES.items() if v is old[4]))


def test_legacy_and_main_unchanged_by_install():
    """After main2.install(), the maps of the three port types, the side-by-side short roads and the passing places under legacy40 and main
    are byte for byte those of the original functions."""
    sets = [{}, dict(ramp_at="gate"), dict(ramp_at=None), dict(n_cradles=6, cradle_mode="pull_in", dist_m=1500.0, corridor_m=1200.0, n_junctions=0)]
    ref = {}
    for g in ("legacy40", "main"):
        A.use(g)
        for kind, kw in itertools.product(A.KINDS, sets):
            ref[g, kind, str(kw)] = A.dumps(A.build(kind, **kw))
        ref[g, "side"] = A.dumps(S4.build_side(n_cradles=6))
        ref[g, "pass"] = A.dumps(S4.build_pass())
    with main2():
        for g in ("legacy40", "main"):
            A.use(g)
            for kind, kw in itertools.product(A.KINDS, sets):
                assert A.dumps(A.build(kind, **kw)) == ref[g, kind, str(kw)], (g, kind, kw)
            assert A.dumps(S4.build_side(n_cradles=6)) == ref[g, "side"]
            assert A.dumps(S4.build_pass()) == ref[g, "pass"]
    A.use("legacy40")


def _diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        return [x for k in sorted(set(a) | set(b)) for x in _diff(a.get(k), b.get(k), f"{path}/{k}")]
    return [] if a == b else [path]


def test_main2_changes_only_ramp_node():
    """Port-type maps of main2 vs main: A1, A2 (ramp at the east end) differ only in the ramp_V coordinates and the geometry record; A3 and the
    no-ramp maps differ only in the geometry record. The ramp keeps length ramp_m and lies in line with the apron."""
    A.use("main")
    m = {(k, str(kw)): A.build(k, **kw) for k in A.KINDS for kw in ({}, dict(ramp_at=None), dict(dist_m=1500.0, corridor_m=1200.0))}
    with main2():
        for (k, kw), D0 in m.items():
            D = A.build(k, **eval(kw))
            d = {"/windport/geometry" if x.startswith("/windport/geometry") else x for x in _diff(D0, D)}
            want = {"/windport/geometry"} | ({"/nodes/ramp_V/position"} if k in ("A1", "A2") and "ramp_at" not in kw else set())
            assert set(d) == want, (k, kw, d)
            if "/nodes/ramp_V/position" in d:
                (xj, yj, _), (xv, yv, _) = D["nodes"]["ramp_J"]["position"], D["nodes"]["ramp_V"]["position"]
                assert yv == yj and xv - xj == D["windport"]["params"]["ramp_m"]
    A.use("legacy40")


def test_loading_network_identical():
    """A1, A2 under main and main2: the wait-free windows and network capacities of the loading legs (saddle row → cradle position) and the
    departure legs (cradle position → gate / yard side) are equal value for value; the unloading leg differs (no stop to turn at the ramp foot)."""
    def legs():
        out = []
        for kind, m in itertools.product(("A1", "A2"), T.MODES):
            c = X.port_cfg("lane", m, "S3", 2, 10, 1)
            c["geo"] = dict(c["geo"], kind=kind)
            D, net, p, *_ = S2.setup2(c)
            W = D["windport"]
            cap, size = net.capacities(p)
            g, y = S2.idle_nodes(D)
            row = [cap, size]
            for o, d in itertools.product(W["storage"], W["cradles"][:3]):
                so, sd = net.stops[o], net.stops[d]
                row.append(net.leg(so["node"], sd["node"], p["v_loaded"], p["Lv"], p["B"], True, p, cap, size, sd["res"], net.demand(sd["res"], p["B"], True, p, cap)))
                for t in (g, y):
                    row.append(net.leg(sd["node"], t, p["v_empty"], p["plat_len"], p["plat_w"], False, p, cap, size, ("x",), 0.0, True))
            vr = net.stops[W["storage"][0]]
            unl = WS.turn_delays(net, net.path(W["ramp"][0], vr["node"]), p["Lv"], p["v_loaded"], p)[1]
            out.append((row, unl))
        return out
    A.use("main")
    a = legs()
    with main2():
        b = legs()
    A.use("legacy40")
    for (ra, ua), (rb, ub) in zip(a, b):
        assert ra == rb
        assert sum(ub) < sum(ua) and ua[1] > 0 and ub[1] == 0.0      # the stop to turn at the ramp foot (decision point 1: ramp → apron) is gone


def test_rows_geometry_and_check():
    """Rebuilt side-by-side rows: pitch B + w_e + c = 15.36 m, piles in [60, 170] m, cradle position 0 nearest to the quay line (8.25 m); the
    geometry check passes all turns (entry turns counted), also at the ramp and at the A2 loop junction."""
    with main2():
        for sc, h in itertools.product(("base", "lane"), (0, 1)):
            c = X.port_cfg(sc, "on_road", "S1", 2, 10, h)
            c["geo"], c["S"] = TA.side_geo(sc), 6
            c = M2.rows_cfg(c)
            assert c["geo"]["kind"] == "A1rows" and c["geo"]["pitch_m"] == 15.36 and (c["geo"]["x0_m"], c["geo"]["head_m"]) == (60.0, 170.0)
            r = GC.check(c)
            assert r["ok"] == 1 and r["piles_on_land"] == 1 and not r["assumed"], r
            assert any(x["route"] == "bay entry" for x in r["rows"]) and min(r["min_clear"].values()) >= 5.0
            D, _, p, *_ = S4.setup4(c)
            W = D["windport"]
            assert W["row_y"][0] == max(W["row_y"]) and abs(GC.quay_edge(D, p) - W["row_y"][0] - 8.25) < 1e-9
        for kind in ("A1", "A2"):
            c = X.port_cfg("lane", "on_road", "S3", 2, 10, 0)
            c["geo"] = dict(c["geo"], kind=kind)
            r = GC.check(c)
            assert r["ok"] == 1 and r["ok_unload"] == 1 and not r["assumed"] and r["min_unload"]["flanks"] > 5.0, (kind, r)


@pytest.mark.skipif(not (ROOT / "results/runs/maingeom_geom/turns.csv").exists(), reason="geometry check of the main geometry: not part of the release")
def test_maingeom_geometry_check_reproduces():
    """Under legacy40 / main, turns.csv of the main-geometry check directory reproduces row by row (the main2 branches of geomcheck run only
    under main2)."""
    A.use("main")
    old = list(csv.DictReader(open(ROOT / "results/runs/maingeom_geom/turns.csv", encoding="utf-8")))
    new = []
    for first in (40.0, 150.0, 170.0):
        geo = dict(A.GEOMETRIES["main"] if first != 40.0 else A.GEOMETRIES["legacy40"], gate_cradle_m=first)
        for kind, sc, m, arr in itertools.product(A.KINDS, ("base", "lane"), T.MODES, ("S1", "S3")):
            c = X.port_cfg(sc, m, arr, 2, 10, 0)
            c["geo"] = dict(c["geo"], kind=kind, **geo)
            new += [dict(first=first, kind=kind, scen=sc, mode=m, arr=arr, **x) for x in GC.check(c)["rows"]]
    A.use("legacy40")
    assert len(old) == len(new) and all({k: o[k] for k in o} == {k: str(n.get(k, "")) for k in o} for o, n in zip(old, new))


def test_rows_core_s1_equals_bound():
    """Long single lane at 1 km/h, 10 piles per vessel: rebuilt side-by-side rows with S = 1 (K = 2) under FCFS = L″_lift* (after the chain head
    there is only the row of the cradle, so the original premise holds)."""
    import windport_maingeom as F
    with main2():
        c = M2.rows_cfg(F.core_cfg(dict(first=170.0, scen="lane", lay="side", arr="S1", K=2, hold="0", extra=0.0)))
        r = F.port_point(c)
        assert r["check_ok"] == 1 and abs(r["port_h"] - r["lstar_lo"]) < 1e-6 and abs(r["port_h"] - 20.783824) < 1e-6


def test_tree_premise():
    """tree premise: active only on networks whose quay positions all lie on "row_" roads; for the side-by-side row of Table 7 on the long single
    lane with S = 2, K = 3 (cradle) it tightens W″_lift(12 h) from 11 to 10 (simulation 7); not used with gate holding places; chains of
    tandem port types carry no tree flag and their bound is unchanged."""
    with main2():
        d = T.dec("lay=side|kind=A1side|scen=lane|mode=side|lift=cradle|rule=fcfs|reach=all|L=12|K=3|S=2|G=24")
        c = dict(TA.cfg_of("reach", d), fixed=False)
        c = M2.rows_cfg(c)
        G, L = c["cal"]["crane"][0][0] * H, 12 * H
        w = BA.parts(c, lift=True)
        assert any(ch.get("tree") for ch in w["chains"])
        assert BA.w2_lift(c, dict(w, G=G))(L) == 10
        new = W2.chain_times, W2.quay_side_Q, W2.zone_Q
        W2.chain_times, W2.quay_side_Q, W2.zone_Q = M2._CHAIN, M2._QS, M2._ZQ
        try:
            assert BA.w2_lift(c, dict(BA.parts(c, lift=True), G=G))(L) == 11
        finally:
            W2.chain_times, W2.quay_side_Q, W2.zone_Q = new
        D, net, p, *_ = S4.setup4(c)
        ch = next(x for x in w["chains"] if x.get("tree"))
        assert W2.quay_side_Q(net, p, D["windport"]["storage"], D["windport"]["cradles"][:2], p["Lv"], p["B"], ch, 1) == W2.INF
        s = X.port_cfg("lane", "on_road", "S3", 3, 10, 0)
        assert not any(x.get("tree") for x in BA.parts(s, lift=True)["chains"])


@pytest.mark.skipif(not (ROOT / "results/runs/maingeom_core/points.csv").exists(), reason="core batch of the main geometry: not part of the release")
def test_maingeom_rows_reproduce_under_main2():
    """Basis for the reuse: main-geometry tandem loading rows (core case cradle S = 1, one E4 row) reproduce byte for byte under main2."""
    import windport_maingeom as F
    import windport_rerun_spatial as E
    rows = {r["key"]: r for r in csv.DictReader(open(ROOT / "results/runs/maingeom_core/points.csv", encoding="utf-8"))}
    key = T.enc(dict(first=170.0, scen="lane", lay="on_road", arr="S1", K=2, hold="0", extra=0.0))
    lines = (ROOT / "results/runs/maingeom_spatial_reach/points.csv").read_text(encoding="utf-8").splitlines()
    tandem = next(ln for ln in lines[1:] if "lay=tandem" in ln and "K=3|S=3" in ln)
    with main2():
        r = F.port_point(F.core_cfg(T.dec(key)))
        assert f"{r['port_h']}" == rows[key]["port_h"] and f"{r['lstar_lo']}" == rows[key]["lstar_lo"]
        k = next(csv.DictReader([lines[0], tandem]))["key"]
        buf = io.StringIO()
        csv.DictWriter(buf, lines[0].split(","), extrasaction="ignore", lineterminator="\n").writerow(E.row_of(k, E.run_point("reach", k)))
        assert buf.getvalue().rstrip("\n") == tandem
