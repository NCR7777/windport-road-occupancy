"""Main geometry: main geometry of the parametric archetypes (first cradle position 170 m, quay line 20 m from the apron road,
gate turning area radius 60 m), geometry check, old geometry (legacy40) byte-identical, cradle-mode chains with signed dq in the
unified bound (Corollary 7(c)), value-by-value check of the conservative rule with crane reach and reserved periods, co-design
table note generated from the numbers."""
import pytest
import csv
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                        # noqa: E402
import windport_extra as X                       # noqa: E402
from windport import archetypes as A             # noqa: E402
from windport import bound4 as B4                # noqa: E402
from windport import bound_all as BA             # noqa: E402
from windport import bound_lift as BL            # noqa: E402
from windport import geomcheck as GC             # noqa: E402
from windport import lift as LF                  # noqa: E402
from windport import sim2 as S2                  # noqa: E402
from windport import sim4 as S4                  # noqa: E402

H = 3600.0
UNIFIED = "ac7c713"                                # last commit before the geometry change
GRID = [x * 900.0 for x in range(0, 120)] + [3600.0 - 54.0, 3600.0 + 1.0, 3654.0, 7254.0]


def _old(path):
    src = subprocess.run(["git", "-C", str(ROOT), "show", f"{UNIFIED}:{path}"], capture_output=True, check=True).stdout.decode("utf-8")
    ns = dict(__name__="old_" + Path(path).stem)
    exec(compile(src, f"old/{path}", "exec"), ns)
    return ns


def _main(fn):
    """Run fn() in the main geometry, then return to the old geometry (default)."""
    A.use("main")
    try:
        return fn()
    finally:
        A.use("legacy40")


@pytest.mark.skipif(subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", UNIFIED + "^{commit}"], capture_output=True).returncode != 0, reason="compares with the code of an earlier commit of the research repository: not part of the release")
def test_legacy_maps_byte_identical():
    """Default geometry (legacy40) and explicit legacy40 parameters: maps of the three archetypes, side-by-side cradles and passing
    places are byte-identical to those before the change."""
    old = _old("windport/archetypes.py")
    sets = [{}, dict(ramp_at="gate"), dict(ramp_at=None), dict(n_cradles=6, cradle_mode="pull_in", dist_m=1500.0, corridor_m=1200.0, n_junctions=0)]
    for kind in A.KINDS:
        for kw in sets:
            if kind == "A3" and "ramp_at" in kw:
                continue
            ref = old["dumps"](old["build"](kind, **kw))
            assert A.dumps(A.build(kind, **kw)) == ref, (kind, kw)
            assert A.dumps(A.build(kind, **dict(kw, **A.GEOMETRIES["legacy40"]))) == ref, (kind, kw)
    o4 = _old("windport/sim4.py")
    assert A.dumps(S4.build_side(n_cradles=6, pitch_m=20.0, bay_m=40.0)) == A.dumps(o4["build_side"](n_cradles=6, pitch_m=20.0, bay_m=40.0))
    assert A.dumps(S4.build_pass(pp_m=150.0, pp_w=16.0)) == A.dumps(o4["build_pass"](pp_m=150.0, pp_w=16.0))


@pytest.mark.skipif(not (ROOT / "results/runs/unified_reach/points.csv").exists(), reason="reach batch of the unified bound: not part of the release")
def test_committed_side_row_reproduces():
    """Committed side-by-side cradle rows in the old geometry (unified-bound reach, conservative rule) reproduce byte for byte
    (sim4.build_side behaves the same after it reads the first cradle position)."""
    import io
    import windport_rerun_spatial as E
    lines = (ROOT / "results/runs/unified_reach/points.csv").read_text(encoding="utf-8").splitlines()
    cols = lines[0].split(",")
    side = [ln for ln in lines[1:] if "lay=side" in ln]
    with LF.installed():
        for line in (side[0], side[len(side) // 2]):
            key = next(csv.DictReader([lines[0], line]))["key"]
            buf = io.StringIO()
            csv.DictWriter(buf, cols, extrasaction="raise", lineterminator="\n").writerow(E.row_of(key, E.run_point("reach", key)))
            assert buf.getvalue().rstrip("\n") == line


def test_use_switch_and_cache():
    """use() clears the network cache when switching geometry: the same geo gives different maps in the two geometries, and switching
    back gives the previous map."""
    c = X.port_cfg("lane", "on_road", "S1", 2, 10, 0)
    a = S2.get_net(c["geo"], S2.WS.params(c))[1].map_sha256
    b = _main(lambda: S2.get_net(c["geo"], S2.WS.params(c))[1].map_sha256)
    assert a != b and S2.get_net(c["geo"], S2.WS.params(c))[1].map_sha256 == a
    D = _main(lambda: A.build("A1", n_cradles=3))
    x0 = D["zones"]["z_cradle"]["extensions"][A.RS]["frontage"][0]
    assert (x0["sStartM"] + x0["sEndM"]) / 2 == 170.0 and D["windport"]["geometry"] == A.GEOMETRIES["main"]
    assert "geometry" not in A.build("A1")["windport"]
    side = _main(lambda: S4.build_side(n_cradles=2, pitch_m=20.0, bay_m=40.0))
    assert side["nodes"]["apron_0"]["position"][0] == 170.0


def test_geometry_check():
    """In the main geometry the swept circle of the 90° gate turn (radius L_v/2) keeps clearance (about 5 m) from the berth water, the
    piles on the cradles and the lane flanks, for the three archetypes and both cradle modes; the old geometry overlaps all three
    (−48 to −50 m); with the first cradle at 150 m the pile tail on the cradle is still inside the turning circle (−14.4 m); a 120 m
    monopile exceeds the turning area of the main geometry."""
    def run(kind, mode, geo):
        c = X.port_cfg("lane", mode, "S3", 2, 10, 0)
        c["geo"] = dict(c["geo"], kind=kind, **geo)
        return GC.check(c)
    for kind in A.KINDS:
        for mode in T.MODES:
            r = _main(lambda: run(kind, mode, {}))
            assert r["ok"] == 1 and r["piles_on_land"] == 1, (kind, mode, r["min_clear"])
            assert 5.0 <= min(r["min_clear"].values()) or kind == "A2" and r["min_clear"]["flanks"] > 1.0
            old = run(kind, mode, {})
            assert old["ok"] == 0 and old["min_clear"]["water"] == -49.0 and old["piles_on_land"] == 0
    r = _main(lambda: run("A1", "on_road", dict(gate_cradle_m=150.0)))
    assert r["ok"] == 0 and r["min_clear"]["water"] > 0 and abs(r["min_clear"]["piles"] + 14.39) < 0.01
    c = X.port_cfg("base", "on_road", "S1", 2, 10, 0)
    c["p"] = dict(c["p"], Lv=120.0, B=12.0)
    assert _main(lambda: GC.check(c))["ok"] == 0


def test_geometry_check_unload_and_side():
    """Unloading routes are listed separately: in the main geometry the loaded 90° turn at the A1 ramp foot overlaps the water by
    35 m and is only recorded under the crab / reorientation assumption, not counted in the pass; A2 unloading via the return loop
    overlaps the lane flanks where it rejoins the south end of the lane (ok_unload = 0), loading still passes. Side-by-side cradle
    quay line at bay_m + long_clear = 45 m (geometry check only): the gate turn passes, the short dead end lies on land, the turn
    into the bay is only recorded."""
    import windport_spatial as TA

    def run(kind):
        c = X.port_cfg("lane", "on_road", "S1", 2, 10, 0)
        c["geo"] = dict(c["geo"], kind=kind)
        return GC.check(c)
    r1, r2, r3 = (_main(lambda k=k: run(k)) for k in A.KINDS)
    assert r1["ok"] == r2["ok"] == r3["ok"] == 1
    assert r1["assumed"]["ramp foot"]["water"] == -35.0 and r1["ok_unload"] == 1
    assert r2["ok_unload"] == 0 and r2["min_unload"]["flanks"] < 0 and r3["ok_unload"] == 1
    assert any(x["route"] == "ramp foot" and not x["ok"] for x in r1["rows"])
    c = X.port_cfg("lane", "on_road", "S1", 2, 10, 0)
    c["geo"] = TA.side_geo("lane")
    s = _main(lambda: GC.check(c))
    assert s["ok"] == 1 and s["bays_on_land"] == 1 and s["min_clear"]["water"] == 5.0 and "piles" not in s["min_clear"]
    assert s["assumed"]["bay entry"]["water"] < 0
    D, _, p, *_ = _main(lambda: S4.setup4(c))
    assert GC.quay_edge(D, p) == 45.0
    q = GC.obstacles(D, p)
    assert q["water"][0][2] == D["windport"]["params"]["dist_m"] + 45.0


def test_main_geometry_lift_span_on_apron():
    """Main geometry: when lifting at the first cradle position the load span (L_v back from the vehicle front) lies entirely on the
    apron road, without the gate and the lane (in the old geometry it extends about 70 m past the gate)."""
    def spans():
        c = X.port_cfg("lane", "on_road", "S1", 2, 10, 0)
        D, net, p, *_ = S2.setup2(c)
        W = D["windport"]
        d, o = W["cradles"][0], W["storage"][0]
        res, nodes = LF.span_res(net, d, p["Lv"], net.path(net.stops[o]["node"], net.stops[d]["node"]))
        return W["gates"][0] in nodes
    assert spans() and not _main(spans)


def test_core_values_main_geometry():
    """Core example (long single lane 1 km/h, 10 piles per vessel, Q_h = 0, K = 2) in the main geometry, FCFS = L″_lift*: cradle
    S = 1 20.0465 h, direct lift on-road 17.3865 h, pull-in 18.4215 h."""
    def one(m, arr):
        c = X.port_cfg("lane", m, arr, 2, 10, 0)
        with LF.installed():
            net, p, sim, r = S2.simulate2(c)
        ls = sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)
        return (ls[9] - 24 * H) / H, BA.lstar(BA.w2_lift(c), 10)[0] / H
    for (m, arr), v in {("on_road", "S1"): 20.0465, ("pull_in", "S1"): 20.0465, ("on_road", "S0"): 17.3865, ("pull_in", "S0"): 18.4215}.items():
        ph, ls = _main(lambda: one(m, arr))
        assert abs(ph - v) < 1e-3 and abs(ls - ph) < 1e-6, (m, arr, ph, ls)


def test_signed_cradle_chains():
    """Corollary 7(c) applied to cradle mode: without chains with dq < 0 equal to the W″_lift of the unified bound value by value;
    with short h_d new chains are added, W″_lift only decreases and stays at or above the simulation."""
    for c in (X.port_cfg("lane", "on_road", "S1", 2, 10, 0), X.port_cfg("longslow", "pull_in", "S3", 4, 10, 0), X.port_cfg("base", "pull_in", "S1", 1, 10, 0)):
        w, w0 = BA.parts(c, lift=True), BA.parts(c, lift=True, signed=False)
        assert len(w["chains"]) == len(w0["chains"])
        f, f0, g = BA.w2_lift(c, w), BA.w2_lift(c, w0), BL.wfn_lift(c)
        assert all(f(L) == f0(L) == g(L) for L in GRID)
    c = X.port_cfg("lane", "pull_in", "S1", 2, 10, 0, p_extra=dict(hd_s=300.0))
    w, w0 = BA.parts(c, lift=True), BA.parts(c, lift=True, signed=False)
    assert len(w["chains"]) > len(w0["chains"]) and any(ch["dq"] < 0 for ch in w["chains"])
    f, f0 = BA.w2_lift(c, w), BA.w2_lift(c, w0)
    assert all(f(L) <= f0(L) for L in GRID)
    with LF.installed():
        net, p, sim, r = S2.simulate2(c)
    Ts = sorted(x["F_vessel"] - 24 * H for x in sim.trips if x["F_vessel"] is not None)
    assert Ts and all(f(t) >= j for j, t in enumerate(Ts, 1))


def test_lift_reach_reserve_values():
    """Conservative rule + crane reach + reserved periods: W″_lift = min(bound_lift.wfn_lift, reach term, reserved-period term), value
    by value; the reach term with L_x = L equals bound4.reach_R, the reserved-period term with L_x equals bound4.reserve_R. One case
    each for cradle mode (ε_U > 0, L_x < L) and mixed lift-and-carry (ε_U = 0)."""
    for lift in ("cradle", "mixed"):
        c = T.cfg_of("e4", T.enc(dict(kind="A1", scen="base", mode="pull_in", lift=lift, rule="fcfs", L=12, K=1, S=6, G=24)))
        c["lift"] = lift
        c["p"] = dict(c["p"], reach=1, shift_s=7200.0)
        c["reserve"] = dict(f=0.5, T_h=1.0)
        w = BA.parts(c, lift=True)
        P, G, e = w["P"], w["G"], w.get("eps_u", 0.0)
        assert (e > 0) == (lift == "cradle")
        f, g = BA.w2_lift(c, w), BL.wfn_lift(c)
        for L in GRID:
            Lx = max(L - e, P.p) if e > 0 and L >= P.p - 1e-9 else L
            assert BA.reach(P, G, L, L, w["Sr"], w["sh"]) == B4.reach_R(P, G, L, w["Sr"], w["sh"])
            want = min(g(L), BA.reach(P, G, L, Lx, w["Sr"], w["sh"]), B4.reserve_R(w["rp"], P.S, P.K, G, Lx, P.p, w["hp"]))
            assert f(L) == want, (lift, L)
        assert any(BA.terms(w, L).get("reach", 1e9) < g(L) for L in GRID)


@pytest.mark.skipif(not (ROOT / "results/runs/unified_cdv/points.csv").exists(), reason="co-design batches of the spatial additions and the unified bound: not part of the release")
def test_codesign_note_generated():
    """The note of the co-design table is generated from the numbers: with the inputs of the unified bound it states the effect of
    adding only a gate holding place, −2,585 € (13.92 vs 13.67 h)."""
    import windport_report_spatial as AR
    rep = ROOT / "results/tables/unified/spatial_lift"
    cdv = AR.rd(ROOT / "results/runs/unified_cdv/points.csv")
    src = ROOT / "results/runs/spatial_codesign"
    with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as d:
        AR.codesign(AR.rd(src / "best.csv"), AR.rd(src / "codesign.csv"), cdv, Path(d), {})
        new = (Path(d) / "table_codesign.md").read_text(encoding="utf-8").splitlines()
    old = (rep / "table_codesign.md").read_text(encoding="utf-8").splitlines()
    note = next(x for x in new if x.startswith("Table note"))
    assert "-2,585 €" in note and "13.92 vs 13.67 h" in note and note.count("gate holding place alone") == 1
    assert [x for x in new if not x.startswith("Table note")] == [x for x in old if not x.startswith("Table note")]
