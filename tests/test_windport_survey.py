"""Public-site survey: distance computations of the public road-network survey (windport/port_survey.py) on a few synthetic roads,
answers worked out by hand."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from windport import port_survey as PS                           # noqa: E402


def synth():
    """Working area 200 × 300 m, the south side y = 0 is the shoreline; roads: A(100,10)-B(100,110)-C(100,210) one service road,
    C-E(10,210) (lanes=1, width=6), C-G(100,290), B-D(180,110) (oneway), B-(0,110) is a footway (not a road)."""
    D = PS.Data.__new__(PS.Data)
    pts = dict(q0=(0, 0), q1=(200, 0), r2=(200, 300), r3=(0, 300), A=(100, 10), B=(100, 110), C=(100, 210), E=(10, 210), G=(100, 290),
               D=(180, 110), F=(0, 110))
    ids = {k: i + 1 for i, k in enumerate(pts)}
    D.xy = {ids[k]: v for k, v in pts.items()}
    way = lambda ns, **t: dict(type="way", nodes=[ids[n] for n in ns], tags=t)
    D.ways = {1: way(["q0", "q1"], natural="coastline"), 2: way(["q0", "q1", "r2", "r3", "q0"], landuse="industrial"),
              10: way(["A", "B", "C"], highway="service"), 12: way(["C", "E"], highway="service", lanes="1", width="6"),
              14: way(["C", "G"], highway="service"), 11: way(["B", "D"], highway="service", oneway="yes"),
              13: way(["B", "F"], highway="footway")}
    D.ways[5] = way(["q1", "q0"], natural="water")                  # the same shoreline also drawn as a water boundary: length not counted twice
    D.rels, D.node_tags, D.water_members = {}, {}, set()
    return D


def test_survey_synthetic():
    r = PS.survey(synth(), dict(area=[("way", 2)]))
    assert r["status"] == "ok"
    assert r["quay_len_m"] == pytest.approx(200.0)
    assert r["n_front"] == 1                                        # only A is within 30 m of the shoreline
    assert r["route_min_m"] == pytest.approx(100.0)                 # B
    assert r["route_max_m"] == pytest.approx(290.0)                 # E: 90 + 100 + 100
    f = r["far"]
    assert f["length_m"] == pytest.approx(290.0)
    assert f["n_junctions"] == 2 and f["n_turns"] == 1              # right turn of 90° at C, straight on at B (the footway does not count in the degree)
    assert sorted(f["junction_angles"]) == [pytest.approx(0.0), pytest.approx(90.0)]
    assert f["len_no_width_m"] == pytest.approx(200.0)              # only C-E has a width
    narrow = [w for w in f["ways"] if w["lanes"] == "1"]
    assert len(narrow) == 1 and narrow[0]["width"] == "6" and narrow[0]["length_m"] == pytest.approx(90.0)
    assert r["straight_max_m"] == pytest.approx(300.0)


def test_relation_ring_stitch():
    D = synth()
    D.ways[3] = dict(type="way", nodes=[D.ways[2]["nodes"][i] for i in (0, 1, 2)], tags={})
    D.ways[4] = dict(type="way", nodes=[D.ways[2]["nodes"][i] for i in (4, 3, 2)], tags={})     # a reversed piece
    D.rels = {9: dict(type="relation", members=[dict(type="way", ref=3, role="outer"), dict(type="way", ref=4, role="outer")], tags={})}
    assert abs(PS.area(D.ring(("rel", 9)))) == pytest.approx(200 * 300)


@pytest.mark.skipif(not (ROOT / "results/runs/survey/haulpaths.json").exists(), reason="haul paths measured on imagery: not part of the release")
def test_haulpaths_survey():
    """Imagery path length (local-plane algorithm of port_survey) differs from the haversine of the checking page by < 1%; width
    classes and single-lane stretches."""
    import json
    sys.path.insert(0, str(ROOT / "experiments"))
    import windport_survey as S
    h = S.haul_survey(json.loads(S.HAUL.read_text(encoding="utf-8")))
    assert set(h) == set(S.HAUL_PORTS)
    for k, r in h.items():
        assert r["rel_diff"] < 0.01, k
    assert {k: r["width_class"] for k, r in h.items() if r["width_class"] != "C"} == {"eemshaven_gw3": "A"}
    assert h["nordenham"]["min_fixed_w_m"] == pytest.approx(23.2)                  # the only fixed narrow point, >= 20 m
    assert h["eemshaven_gw3"]["lane_m"] == pytest.approx(795, abs=1)               # measured as about 795 m
    assert h["eemshaven_gw3"]["len_m"] == pytest.approx(1135, abs=1)
    assert 129 < min(r["len_m"] for k, r in h.items() if k != "eemshaven_gw3") < max(r["len_m"] for k, r in h.items() if k != "eemshaven_gw3") < 690
    # segment table: sum of segment lengths = path length; Gode Wind 3 segments 2-4 are class A (11.3 m), the 23.2 m measurement of Nordenham falls in segment 3
    for k, r in h.items():
        assert sum(g["len_m"] for g in r["segments"]) == pytest.approx(r["len_m"], abs=0.2), k
    assert [g["width_class"] for g in h["eemshaven_gw3"]["segments"]] == ["C", "A", "A", "A", "C"]
    assert [(g["seg"], g["width_m"]) for g in h["nordenham"]["segments"] if g["measured"]] == [(3, 23.2)]
    assert all("[to be checked]" not in r["note"] for r in h.values())
    # synthetic piece: longitude difference 0.01° on the equator ≈ 1,111.95 m (R = 6,371,000); class limits
    assert S.hav((0, 0), (0, 0.01)) == pytest.approx(1111.95, abs=0.01)
    w = lambda *xs: dict(widths=[dict(w=x, fixed=f) for x, f in xs])
    assert S.width_class(w((15.3, True), (8.0, False))) == (15.3, "A")             # storage aisles (fixed = false) are not counted
    assert S.width_class(w((15.4, True))) == (15.4, "B")
    assert S.width_class(w((20.0, True))) == (20.0, "C") and S.width_class(w()) == (None, "C")


def test_segments_public_no_coordinates():
    """The public segment table has no coordinates: no latitude/longitude columns and no decimal pairs that look like them."""
    import csv
    import re
    rows = list(csv.DictReader(open(ROOT / "results" / "runs/survey" / "segments_public.csv", encoding="utf-8")))
    assert rows and not any(c in rows[0] for c in ("lat", "lon", "path", "a", "b"))
    assert not any(re.search(r"\d{1,3}\.\d{4,}", v) for r in rows for v in r.values())


def test_port_rows_matches_spatial():
    """port_rows and the real-port branch of windport_spatial_analytic.critical agree row by row at the single-lane ends 0 and 100%."""
    sys.path.insert(0, str(ROOT / "experiments"))
    import windport_spatial_analytic as A7
    import windport_survey as S
    g0 = A7.GRIDS["critical"]
    try:
        A7.GRIDS["critical"] = dict(g0, sites=[], ports=[dict(name="x", route_m=500.0, v=S.V, src="s")])
        ref = A7.critical()
    finally:
        A7.GRIDS["critical"] = g0
    mine = S.port_rows("x", 500.0, 0.0, "s") + S.port_rows("x", 500.0, 400.0, "s")
    key = lambda r: (r["lane_frac"], r["v"], r["mode"])
    for a, b in zip(sorted(ref, key=key), sorted(mine, key=key)):
        assert a == b
