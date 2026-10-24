"""Main geometry main2: two changes to main (the main geometry: first cradle position 170 m from the gate, shoreline 20 m from the
apron road centre line, gate turning area radius 60 m):

1. Side-by-side cradles rebuilt with a realistic placement (layout kind = "A1rows"; the map record keeps kind "A1" with
   layout = "rows"): monopiles lie in rows parallel to the shoreline on the cradles (Rønne-style side-by-side), one cradle
   position per row. A north-south spine road runs north from the gate inside the port, each row branches east from the
   spine; rows are dead-end segments, the delivery vehicle drives into a row and, after placement, reverses out.
     Row pitch pitch_m = B + w_e + c (monopile diameter + empty vehicle width + lateral margin, the same parameters as the
     15.36 m road-width criterion for an empty and a loaded vehicle passing);
     row start x0_m = L_v/2 + δ (sweep radius L_v/2 for a 90° turn on the spot at the spine node into the row, δ = longitudinal
     clearance; same rule as the gate turning area), piles lie in [x0, x0 + L_v], the delivery vehicle stops with its front at
     head_m = x0 + L_v (= first cradle position of the main geometry, 170 m), row end end_m = head_m + δ;
     cradle position k = 0 is the row closest to the shoreline (top of the spine); larger k is farther from the shore, and the
     farthest row (k = n − 1) is at the gate's level and branches directly from the gate.
     S cradles thus use the S rows closest to the shore, and crane reach S_r is given as "the number of rows within the effective
     working radius from the shoreline" (see the manuscript).
   Road width: the spine and all rows use the apron road width apron_w. rows_geo(geo, p) computes these dimensions from the point
   parameters (L_v, B, empty vehicle width, clearances), so they scale up with larger piles.
2. Unloading ramp in line with the apron road (ramp_axis = "along"): for A1 and A2 the ramp is at the east end of the apron
   (ramp_at = "end"), the RoRo vessel berths end-on at the east end of the apron and the ramp extends east from there (ramp top
   ramp_V at (ramp foot x + ramp_m, D)); after coming down the ramp the vehicle drives straight along the apron with no turn
   at the ramp foot. The position of the ramp foot on the apron, the ramp length and the road widths are unchanged; only the
   coordinates of the single node ramp_V change (loading routes do not use the ramp, so the loading road network is unchanged:
   tests/test_windport_main2.py).
   Also loop_open_m: radius of the open turning area where the A2 return loop joins the south end of the single lane (used only
   by the geometry check, windport/geomcheck.py).
3. Upper bound (the dead-end premises of Corollaries 6 and 7 extended to multiple dead-end rows; statement and proof: see the
   manuscript): when all quay positions lie on the rebuilt rows, premise (iii) of the chain, "beyond the chain top there is only
   one segment g", is replaced by "the quay side is a tree" (tree): every loaded leg, after the chain top block, first enters a
   junction resource and then passes only segments and junctions that are exclusive both for loaded / empty and for two loaded
   vehicles, ending at a roadside quay position; every departure leg from each quay position passes exactly these resources in
   reverse before entering the chain top block. Premises (i)(ii) (Q_h = 0, first return leg traversing the whole chain in reverse)
   are unchanged. bound2.quay_side_Q and zone_Q then treat the premises as satisfied (Q_s = number of vehicles that can stand at
   quay positions at the same time, i.e. the number of rows used). Applies only to road networks whose quay positions all lie on
   "row_" segments; all other networks give identical values.
install(): registers archetypes.GEOMETRIES["main2"], replaces archetypes.build with a version that knows "A1rows" and the in-line
ramp (byte-for-byte identical to the original function under legacy40 and main), and replaces bound2.chain_times, quay_side_Q and
zone_Q with versions that know item 3; the existing modules look these functions up by name, so they work without changing a line
(same approach as install in windport/lift.py). use() = install() + archetypes.use("main2")."""
import copy

from windport import archetypes as A
from windport import bound2 as W2

MAIN2 = dict(A.GEOMETRIES["main"], ramp_axis="along", loop_open_m=60.0)
ROWS = dict(n_cradles=6, pitch_m=15.36, x0_m=60.0, head_m=170.0, end_m=175.0)     # BASE: L_v 110, B 9.5, w_e 4.86, c 1, δ 5
_BUILD = A.build


def rows_dims(p):
    """Row dimensions (m): pitch = B + w_e + c, x0 = L_v/2 + δ, head = x0 + L_v, end = head + δ."""
    x0 = p["Lv"] / 2 + p["long_clear"]
    return dict(pitch_m=round(p["B"] + p["plat_w"] + p["lat_clear"], 3), x0_m=x0, head_m=x0 + p["Lv"], end_m=x0 + p["Lv"] + p["long_clear"])


def rows_geo(geo, p):
    """geo of side-by-side cradles (kind = "A1side", the drive-in spur abstraction of the spatial additions) → geo rebuilt with a
    realistic placement (kind = "A1rows"): keeps the number of cradle positions and the layout parameters of the scenario, drops
    the spur parameters pitch_m and bay_m, and computes the row dimensions from the point parameters p. Other geo are returned
    unchanged."""
    if geo.get("kind") != "A1side":
        return geo
    rest = {k: v for k, v in geo.items() if k not in ("kind", "pitch_m", "bay_m")}
    return dict(rest, kind="A1rows", **rows_dims(p))


def rows_cfg(c):
    """Replace side-by-side cradles in a point configuration by the rebuilt rows (using the parameters merged by
    windport.sim.params)."""
    from windport import sim as WS
    if c["geo"].get("kind") != "A1side":
        return c
    return dict(c, geo=rows_geo(c["geo"], WS.params(c)))


def build_rows(n_cradles=6, pitch_m=15.36, x0_m=60.0, head_m=170.0, end_m=175.0, **kw):
    from windport import sim4 as S4
    D0 = _BUILD("A1", **dict(kw, n_cradles=1, cradle_mode="on_road", ramp_at=None))
    m = S4._remap(D0)
    q = D0["windport"]["params"]
    Dm, gate, n = q["dist_m"], D0["windport"]["gates"][0], int(n_cradles)
    assert n >= 1 and x0_m < head_m <= end_m - 1.0
    del m.roads["apron_0"], m.nodes["apron_E"]
    ys = [Dm + (n - 1 - k) * pitch_m for k in range(n)]                      # row of cradle position k (k = 0 nearest shore)
    att = [m.node(f"spine_{k}", 0.0, ys[k]) if k < n - 1 else gate for k in range(n)]
    spine = m.chain("spine", att[::-1], q["apron_w"]) if n > 1 else []
    rows = []
    for k in range(n):
        e = m.node(f"row_{k}_E", end_m, ys[k], "endpoint")
        rows.append(m.road(f"row_{k}", att[k], e, q["apron_w"]))
    m.zones["z_cradle"]["extensions"][A.RS]["frontage"] = [dict(roadId=r, sStartM=head_m - 5.0, sEndM=head_m + 5.0) for r in rows]
    meta = copy.deepcopy(D0["windport"])
    meta.update(layout="rows", params=dict(q, n_cradles=n, pitch_m=pitch_m, x0_m=x0_m, head_m=head_m, end_m=end_m), apron=spine + rows,
                cradles=[f"z_cradle#{k}" for k in range(n)], row_y=[y - Dm for y in ys])
    return m.finish(meta)


def build(kind, **kw):
    """Replacement for archetypes.build: kind = "A1rows" gives the rebuilt side-by-side cradles; when the current geometry has
    ramp_axis = "along", the east-end ramp of A1 and A2 is in line with the apron. Otherwise as the original function."""
    if kind == "A1rows":
        return build_rows(**kw)
    D = _BUILD(kind, **kw)
    W = D["windport"]
    if W.get("geometry", {}).get("ramp_axis") == "along" and kind in ("A1", "A2") and W["params"]["ramp_at"] == "end":
        x, y, z = D["nodes"]["ramp_J"]["position"]
        D["nodes"]["ramp_V"]["position"] = [x + float(W["params"]["ramp_m"]), y, z]
    return D


_CHAIN, _QS, _ZQ = W2.chain_times, W2.quay_side_Q, W2.zone_Q


def on_rows(net, quay):
    """All quay positions lie on the rebuilt rows ("row_" segments, roadside stops)."""
    return bool(quay) and all(net.stops[d]["res"][0] == "r" and str(net.stops[d]["res"][1]).startswith("row_") for d in quay)


def route_res(net, s, t):
    """Resources passed in order by the route s → t: segments ("r", segment) and the junction resources ("n", node)
    between them."""
    out, prev = [], None
    for a in net.path(s, t):
        n, r = net.arc[a][0], ("r", net.arc[a][3])
        if r != prev:
            if prev is not None and n in net.node_res:
                out.append(("n", n))
            out.append(r)
            prev = r
    return out


def tree_ok(net, p, B, top, stops_o, quay, legs):
    """Premise tree of item 3 (chain top block top; legs are the first legs (start node, end node) of all return routes):
    after top, every loaded leg passes one junction resource and then exclusive segments and junctions, the last being the
    segment of the roadside quay position; every departure leg from that quay position passes exactly the same resources in
    reverse order before entering top."""
    cap, _ = net.capacities(p)
    b0 = p["plat_w"]
    ok_res = lambda r: r[0] == "n" or (r[0] == "r" and W2.excl(cap, r, p, B, b0, "le") and W2.excl(cap, r, p, B, b0, "ll"))
    after = {}
    for d in quay:
        sd = net.stops[d]
        for o in stops_o:
            names = route_res(net, net.stops[o]["node"], sd["node"])
            if names.count(top) != 1:
                return False
            a = names[names.index(top) + 1:]
            if len(a) < 2 or a[0][0] != "n" or a[-1] != sd["res"] or not all(ok_res(r) for r in a) or after.setdefault(d, a) != a:
                return False
    for d in quay:
        sd = net.stops[d]
        mine = [(s, t) for s, t in legs if s == sd["node"]]
        if not mine:
            return False
        for s, t in mine:
            names = route_res(net, s, t)
            if top not in names or names[:names.index(top)] != after[d][::-1]:
                return False
    return True


def chain_times(net, p, stops_o, quay, Lv, B, unload_s, routes):
    """bound2.chain_times; when all quay positions lie on the rebuilt rows, chains failing _guard also record tree (item 3)."""
    out = _CHAIN(net, p, stops_o, quay, Lv, B, unload_s, routes)
    if out and on_rows(net, quay):
        legs = sorted({r[0] for r in routes if r and r[0][0] != r[0][1]})
        for ch in out:
            if not ch["guard"] and ch.get("exit_first"):
                ch["tree"] = tree_ok(net, p, B, ch["top"], stops_o, quay, legs)
    return out


def quay_side_Q(net, p, stops_o, quay, Lv, B, ch, hold):
    return _QS(net, p, stops_o, quay, Lv, B, dict(ch, guard=True) if ch.get("tree") else ch, hold)


def zone_Q(net, p, stops_o, quay, Lv, B, cut, hold, chains, K):
    return _ZQ(net, p, stops_o, quay, Lv, B, cut, hold, [dict(ch, guard=True) if ch.get("tree") else ch for ch in chains], K)


def install():
    A.GEOMETRIES["main2"] = MAIN2
    A.build = build
    W2.chain_times, W2.quay_side_Q, W2.zone_Q = chain_times, quay_side_Q, zone_Q


def use():
    install()
    A.use("main2")
