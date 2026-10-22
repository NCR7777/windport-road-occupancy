"""Wind-port archetype generator (windport/archetypes.py). Archetypes are written in the shipyard-map format and read directly by
occupancy.network.Net; on A1 (Layout 1), load-out and unloading tasks run under full-path reservation (exact.model.FPR) and the
independent checker exact.check verifies occupancy resource by resource."""
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from exact.check import check                      # noqa: E402
from exact.model import FPR                         # noqa: E402
from occupancy import params as PP                  # noqa: E402
from windport import archetypes as A                # noqa: E402

# SPMT case: loaded 1 km/h, empty 5 km/h, empty vehicle 30 m long and 4.86 m wide, pick-up and set-down 30 min each
# (values used for structural checks only)
P = dict(PP.DEFAULTS, v_loaded=1 / 3.6, v_empty=5 / 3.6, plat_len=30.0, plat_w=4.86, load_s=1800.0, unload_s=1800.0)
LV, B = 100.0, 10.0


@pytest.fixture
def tmp():
    with tempfile.TemporaryDirectory() as d:     # pytest's tmp_path is not writable on some machines (see tests/test_slots.py)
        yield Path(d)


def roads(net, a, b):
    return {net.arc[i][3] for i in net.path(a, b)}


def node(net, sid):
    return net.stops[sid]["node"]


@pytest.mark.parametrize("kind", A.KINDS)
def test_builds_and_net_reads(kind, tmp):
    D = A.build(kind)
    net = A.to_net(D, P, tmp / f"{kind}.json")
    W = D["windport"]
    q = A.DEFAULTS
    assert len(W["storage"]) == q["n_rows"] and all(net.stops[s]["mode"] == "pull_in" for s in W["storage"])
    assert len(W["cradles"]) == q["n_cradles"] and all(net.stops[s]["mode"] == "on_road" for s in W["cradles"])
    assert [net.stops[s]["mode"] for s in W["ramp"]] == ["node"]
    cap, _ = net.capacities(P)
    for rid in W["corridor"]:                       # single lane: neither two loaded vehicles nor loaded + empty fit
        C = cap[("r", rid)]
        d_l, d_e = net.demand(("r", rid), B, True, P, cap), net.demand(("r", rid), P["plat_w"], False, P, cap)
        assert 2 * d_l > C and d_l + d_e > C
    for o in W["storage"]:                          # every row reaches every cradle and back; the ramp reaches every row
        for d in W["cradles"]:
            assert net.dist(node(net, o), node(net, d)) < float("inf") > net.dist(node(net, d), node(net, o))
        for v in W["ramp"]:
            assert net.dist(v, node(net, o)) < float("inf") > net.dist(node(net, o), v)


def test_routes_by_kind(tmp):
    out = {}
    for kind, kw in (("A1", {}), ("A2", {}), ("A3", {}), ("A3", dict(bypass=False))):
        D = A.build(kind, **kw)
        net = A.to_net(D, P, tmp / f"{kind}{len(kw)}.json")
        W = D["windport"]
        o, d, v = node(net, W["storage"][0]), node(net, W["cradles"][0]), W["ramp"][0]
        out[kind, len(kw)] = (W, roads(net, o, d), roads(net, d, o), roads(net, v, o))
    W, load, empty, unload = out["A1", 0]
    # A1: the single-lane corridor is shared by all three flows
    assert set(W["corridor"]) <= load and set(W["corridor"]) <= empty and set(W["corridor"]) <= unload
    W, load, empty, unload = out["A2", 0]
    # A2 loop: the return avoids the corridor; loaded unloading also uses the return road
    assert set(W["corridor"]) <= load and not set(W["corridor"]) & empty and W["loop"][0] in empty
    assert W["loop"][0] in unload and not set(W["corridor"]) & unload
    W, load, empty, unload = out["A3", 0]
    # A3: in through gate 1, out through gate 2; unloading uses the bypass
    assert set(W["corridor"]) <= load and set(W["loop"]) <= empty and not set(W["corridor"]) & empty
    assert W["bypass"] in unload and not (set(W["corridor"]) | set(W["loop"])) & unload
    W, load, empty, unload = out["A3", 1]
    assert "bypass" not in W and set(W["loop"]) <= unload                                                    # no bypass: gate 2


def test_ramp_position_and_pull_in(tmp):
    D = A.build("A1", ramp_at="gate", cradle_mode="pull_in")
    net = A.to_net(D, P, tmp / "g.json")
    W = D["windport"]
    assert all(net.stops[s]["mode"] == "pull_in" for s in W["cradles"])
    assert "apron_1" not in roads(net, W["ramp"][0], node(net, W["storage"][0]))      # ramp at gate: skips cradle section
    D = A.build("A1", ramp_at=None)
    assert D["windport"]["ramp"] == [] and "ramp" not in {r for r in D["roads"]}


def test_deterministic_bytes():
    assert A.dumps(A.build("A2", n_cradles=4)) == A.dumps(A.build("A2", n_cradles=4))
    assert A.dumps(A.build("A2", n_cradles=4)) != A.dumps(A.build("A2", n_cradles=5))
    with pytest.raises(AssertionError):
        A.build("A1", corridor_m=700.0)                 # single-lane section cannot be longer than the yard-to-quay distance


def test_corridor_occupancy_matches_formula(tmp):
    """Single-lane section occupancy in the road-occupancy model = (length + vehicle length + longitudinal clearance) / speed
    (the road rule of Net.leg)."""
    D = A.build("A1", n_junctions=0, corridor_m=300.0, dist_m=500.0)
    net = A.to_net(D, P, tmp / "a1.json")
    W = D["windport"]
    cap, size = net.capacities(P)
    so, sd = net.stops[W["storage"][0]], net.stops[W["cradles"][0]]
    _, st, uses, _ = net.leg(so["node"], sd["node"], P["v_loaded"], LV, B, True, P, cap, size, sd["res"],
                             net.demand(sd["res"], B, True, P, cap))
    (a, r, dl), = [(a, r, dl) for res, _, a, r, dl in uses if res == ("r", W["corridor"][0])]
    assert st[r] + dl - st[a] == pytest.approx((300.0 + LV + P["long_clear"]) / P["v_loaded"])


def test_reserve_on_archetype_passes_independent_check(tmp):
    """On A1, 2 SPMT sets do 3 load-outs + 2 unloadings (full-path reservation); the independent checker verifies capacity per
    resource and timing per vehicle."""
    D = A.build("A1", n_cradles=2, n_rows=3)
    net = A.to_net(D, P, tmp / "a1.json")
    W = D["windport"]
    tasks = [dict(id=j, flow="load", o=W["storage"][j % 3], d=W["cradles"][j % 2], B=B, Lv=LV, release=0.0) for j in range(3)]
    tasks += [dict(id=3 + j, flow="unload", o=W["ramp"][0], d=W["storage"][j], B=B, Lv=LV, release=0.0) for j in range(2)]
    p = dict(P, days=30)
    sim = FPR(net, p, "reserve", 2, 1, None, record=True, tasks=[dict(t) for t in tasks])
    starts = [node(net, W["storage"][0]), node(net, W["storage"][1])]
    for v, loc in zip(sim.vs, starts):
        v.loc = loc
    sim.run()
    assert len(sim.done) == 5
    seq = {}
    for r in sorted(sim.done, key=lambda r: r["plan"]["t1"]):
        seq.setdefault(r["plan"]["vid"], []).append((r["id"], r["plan"]["t1"], r["plan"]["t2"]))
    res = check(net, p, tasks, starts, seq, clr=True)
    assert res["ok"], res["errors"]
