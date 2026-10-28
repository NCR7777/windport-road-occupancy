"""Revision studies: overlays for cradle spacing, near-yard slots and turn bans (byte-identical to the committed results with
default parameters), geometry rules of the near-yard layout, and the definition of the staging criterion."""
import csv
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

pytestmark = pytest.mark.usefixtures("restore")      # overlays patch modules globally (tests/conftest.py)


def _env(group):
    import windport_revision as KK
    plans, _ = KK.load_plans(make=False)
    KK.init(group, {}, plans)
    return KK, plans


def _released(*paths):
    """Skip a comparison whose committed batches (default spacing 110 m) are not part of the release."""
    miss = [q for q in paths if not (ROOT / q).exists()]
    return pytest.mark.skipif(bool(miss), reason=f"{', '.join(miss)}: not part of the release")


def _committed(path, key):
    return next(r for r in csv.DictReader(open(ROOT / path, encoding="utf-8")) if r["key"] == key)


@_released("results/runs/maingeom_extra_port", "results/runs/maingeom_runs_e4", "results/runs/main2_splice", "results/tables/main2/recheck")
def test_spacing_default_reproduces_committed_rows():
    """With all overlays of the revision studies installed and the default spacing 110 m, single points of Tables 8 and 10 equal
    the committed rows field by field; at 115 m the cradle positions of tandem S = 3 move back."""
    import windport_revision_lib as K
    from windport import archetypes as A
    KK, _ = _env("a")
    K.install_spacing(110.0)
    cases = [("t8:port", "scen=lane|mode=pull_in|arr=S3|K=2|n_v=10|hold=0|rep=fcfs", "results/runs/maingeom_extra_port/points.csv"),
             ("rate:e4", "kind=A1|scen=lane|mode=pull_in|lift=cradle|rule=fcfs|L=12|K=2|S=3|G=24", "results/runs/maingeom_runs_e4/points.csv"),
             ("rate:reach", "lay=tandem|kind=A1|scen=lane|mode=pull_in|lift=cradle|rule=fcfs|reach=2_3600|L=12|K=2|S=3|G=24|disp=finish",
              "results/runs/main2_splice/unified_reach/points.csv")]
    for part, key, path in cases:
        row = KK.rows_of(part, key, KK.point(part, key))[0]
        old = _committed(path, key)
        assert {c: str(row[c]) for c in old if c in row} == {c: old[c] for c in old if c in row}, part
    # L*(10) of W″_lift (the L* column of Table 8) equals the same row of the main2-geometry recheck
    r = KK.point("t8:port", cases[0][1])
    rec = _committed("results/tables/main2/recheck/rows.csv", cases[0][1])
    assert abs(r["lstar_w2"] - float(rec["lstar"])) < 1e-6
    D = A.build("A1", n_cradles=6)
    K.install_spacing(115.0)
    D2 = A.build("A1", n_cradles=6)
    assert D2["windport"]["params"]["cradle_spacing"] == 115.0 and D["windport"]["params"]["cradle_spacing"] == 110.0
    ramp = lambda D_: D_["nodes"]["ramp_J"]["position"][0]                 # ramp junction half a spacing past the last cradle
    assert abs((ramp(D2) - ramp(D)) - (5 * 5.0 + 2.5)) < 1e-9


@_released("results/runs/design_cdblk2", "results/runs/design_cdblk", "results/runs/design_codesign")
def test_codesign_point_default_spacing_and_s01_invariance():
    """The co-design tandem point at the default spacing equals cdblk2 of the design analyses; points with S ≤ 1 at 115 m
    equal the committed ones (the basis for reusing them)."""
    import windport_revision_lib as K
    KK, _ = _env("b")
    K.install_spacing(110.0)
    key = next(k for k in KK.keys("cd") if k.endswith("|rc=main|disp=finish|blk=150"))
    d = dict(f.split("=", 1) for f in key.split("|"))
    r = KK.point("cd", key)
    old = next(x for x in csv.DictReader(open(ROOT / "results/runs/design_cdblk2/points.csv", encoding="utf-8"))
               if (x["cd"], x["n_v"], x.get("disp"), x.get("blk")) == (d["cd"], d["n_v"], "finish", "150"))
    assert f"{r['port_h']}" == old["port_h"] and f"{r['lstar_lo']}" == old["lstar_lo"]
    K.install_spacing(115.0)
    k1 = KK.keys("s01")[5]
    r1 = KK.point("s01", k1)
    d1 = dict(f.split("=", 1) for f in k1.split("|"))
    src = "results/runs/design_cdblk/points.csv" if d1.get("blk") else "results/runs/design_codesign/points.csv"
    o1 = next(x for x in csv.DictReader(open(ROOT / src, encoding="utf-8")) if (x["cd"], x["n_v"]) == (d1["cd"], d1["n_v"]))
    assert f"{r1['port_h']}" == o1["port_h"]


def test_unmarked_configs_untouched_and_ban_reroutes():
    """Without buf / ban marks the derived map is byte-identical to that of the original function; with node_trace_016 banned the
    transfer routes no longer use that loaded turn."""
    import windport_design_lib as L
    import windport_revision_lib as K
    from windport import shipyard as SY
    from windport import sim4 as S4
    KK, plans = _env("c")
    c = L.transfer_cfg("okpo", 1, 10, {})
    D0 = L.build_map4(c["geo"])
    D1 = S4.build_map4(c["geo"])
    assert SY.sha(D0) == SY.sha(D1)
    cb = dict(c, geo=dict(c["geo"], ban=KK.BAN["okpo"]))
    D, net, p, *_ = S4.setup4(cb)
    W = D["windport"]
    for o in W["storage"]:
        for q in W["cradles"]:
            path = net.path(net.stops[o]["node"], net.stops[q]["node"])
            rs = [net.road[net.arc[a][3]]["orig"] if "orig" in net.road[net.arc[a][3]] else net.arc[a][3] for a in path]
            for a, b in zip(rs, rs[1:]):
                assert (a, b) != ("road_trace_039", "road_trace_619")


def test_buffer_plan_rules():
    """Near-yard layout: within each column the slot distances from the road centreline step by one row pitch (15.36 m); Okpo has
    9 slots, Yantai 10 (three yard zones); the column pick-up order of the tasks covers all slots."""
    import windport_revision_buffer as B
    KK, plans = _env("c")
    assert plans["okpo"]["slots"] == 9 and plans["yantai"]["slots"] == 10
    for s in ("okpo", "yantai"):
        p = plans[s]
        for c in p["columns"]:
            d = [b - a for a, b in zip(c["crabs"], c["crabs"][1:])]
            assert all(abs(x - B.PITCH) < 1e-6 for x in d), (s, c)
        assert sorted(p["order"]) == sorted(k for k, c in enumerate(p["columns"]) for _ in range(c["slots"]))
    # extra crab duration: one loaded leg, one empty leg, 4 mode switches
    ex = B.crab_extra(plans["okpo"], 2.5 / 3.6, 5.0 / 3.6, 300.0)
    m = max(c["crab_max_m"] for c in plans["okpo"]["columns"])
    assert abs(ex - (m / (2.5 / 3.6) + m / (5.0 / 3.6) + 1200.0)) < 1e-9


def test_staging_definition():
    """Staging criterion: at σ* all road-class window terms are ≥ I, at σ* − 1 one term is < I (core case, 1 km/h)."""
    from dataclasses import replace
    import windport_revision_analytic as KA
    import windport_design as X
    from windport import bound_all as BA
    X.setup_env()
    c = KA.core_cfg("pull_in", 8, dict(v_loaded=1.0 / 3.6))
    r = KA.staging(c, 10.0)
    assert r["sigma"] and r["sigma"] > 1
    w = BA.parts(c, lift=True)
    road = lambda s: min(v for k, v in BA.terms(dict(w, P=replace(w["P"], S=s)), 10 * 3600.0, empty=False).items()
                         if BA.CLASS.get(k) == "road" and k not in BA.PREP)
    assert road(r["sigma"]) >= r["I"] > road(r["sigma"] - 1)


@_released("results/runs/maingeom_runs_e4", "results/runs/maingeom_core")
def test_r1_default_spacing_reproduces_committed_lines():
    """Re-run pipeline of the 115 m spacing re-runs (windport_revision_r1) at the default 110 m: for each batch type, the rows
    written for one key with S ≥ 2 are byte-identical to that line in the directory the manuscript reads; at 115 m the
    core-case pull-in S = 3 becomes slower."""
    import windport_runs as T
    import windport_revision_lib as K
    import windport_revision_r1 as R1
    R1.install()
    K.install_spacing(110.0)
    BD = R1.base_dirs()
    cases = [("e1e3:e1", "A3|lane|pull_in|cradle|L12|K2|S3|G24|H0"), ("runs:e4", "kind=A2|scen=lane|mode=pull_in|lift=cradle|rule=fcfs|L=12|K=3|S=4|G=24"),
             ("unified:ablate", "what=port|step=s2|kind=A1|scen=lane|mode=pull_in|arr=S3|K=3|n_v=10"),
             ("maingeom:core", "first=170.0|scen=lane|lay=pull_in|arr=S3|K=4|hold=inf|extra=0.0")]
    for b, k in cases:
        assert k in R1.keys_of(b), (b, k)
        lines = (BD[b] / "points.csv").read_text(encoding="utf-8").splitlines()
        cols = next(__import__("csv").reader([lines[0]]))
        old = {R1.ident(b, r): line for line, r in zip(lines[1:], csv.DictReader(lines))}
        for row in R1.rows_of(b, k, R1.compute(b, k)):
            assert R1.row_line(cols, row) == old[R1.ident(b, row)], (b, k)
    K.install_spacing(115.0)
    r = R1.compute("maingeom:core", "first=170.0|scen=lane|lay=pull_in|arr=S3|K=4|hold=inf|extra=0.0")
    assert r["port_h"] > float(next(x for x in csv.DictReader(open(BD["maingeom:core"] / "points.csv", encoding="utf-8"))
                                     if x["key"] == "first=170.0|scen=lane|lay=pull_in|arr=S3|K=4|hold=inf|extra=0.0")["port_h"])


@_released("results/runs/revision_bnear", "results/runs/revision_btr")
def test_r1_rated_layout_matches_bnear():
    """Two-level row recomputed from the layout (windport_revision_r1_rated): L″*(10) of the near-yard window and of the transfer
    equal the L″* stored for the same configuration by the simulation batches bnear and btr (including the crab, switch and
    alternative-turn durations of level hi)."""
    import windport_revision_analytic as KA
    import windport_revision_lib as K
    import windport_revision_r1_rated as RR
    KK, plans = _env("c")
    K.install_all(plans)
    pts = {r["key"]: r for r in csv.DictReader(open(ROOT / "results/runs/revision_bnear/points.csv", encoding="utf-8"))}
    for s, sc, lv, v in (("okpo", "base", "feas", 2.5), ("okpo", "slow", "hi", 1.0), ("yantai", "slow", "hi", 1.0)):
        c = RR.near_cfg(s, "pull_in", 1, dict(v_loaded=v / 3.6, v_empty=5.0 / 3.6), lv, plans)
        old = float(pts[f"site={s}|scen={sc}|mode=pull_in|K=1|lv={lv}|G=24"]["lstar_lo"])
        assert abs(KA.lstar(c, 10) - old) < 1e-4, (s, sc, lv)
    tr = {r["key"]: r for r in csv.DictReader(open(ROOT / "results/runs/revision_btr/points.csv", encoding="utf-8"))}
    for s, sc, lv, v in (("okpo", "base", "hi", 2.5), ("okpo", "slow", "hi", 1.0), ("yantai", "base", "feas", 2.5)):
        c = RR.tr_cfg(s, 2, dict(v_loaded=v / 3.6, v_empty=5.0 / 3.6), lv, plans)
        assert abs(KA.lstar(c, 10) - float(tr[f"site={s}|scen={sc}|K=2|lv={lv}|ban=0"]["lstar_lo"])) < 1e-4, (s, sc, lv)


@_released("results/runs/maingeom_core", "results/tables/main2/recheck")
def test_r1rc_recheck_covers_core_rows():
    """cfg_of of the recheck: maingeom:core exactly as in windport_recheck_maingeom, the rest as in windport_recheck_main2; L″* of one
    core-case row equals the committed recheck (110 m)."""
    import windport_recheck_maingeom as FK
    import windport_revision_lib as K
    import windport_revision_r1rc as RC
    RC.init()
    K.install_spacing(110.0)
    key = "first=170.0|scen=lane|lay=pull_in|arr=S3|K=4|hold=0|extra=0.0"
    row = next(x for x in csv.DictReader(open(ROOT / "results/runs/maingeom_core/points.csv", encoding="utf-8")) if x["key"] == key)
    r = FK.one(("maingeom:core", "lift", row))
    old = next(x for x in csv.DictReader(open(ROOT / "results/tables/main2/recheck/rows.csv", encoding="utf-8"))
               if x["batch"] == "maingeom:core" and x["key"] == key)
    assert abs(r["lstar"] - float(old["lstar"])) < 1e-6 and r["over"] == 0
