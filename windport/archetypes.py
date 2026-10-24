"""Parametric offshore wind marshalling port archetypes: A1 (Layout 1) single-lane quay corridor, A2 (Layout 2) loop,
A3 (Layout 3) two gates plus bypass.

Outputs a map dict in the same format as the shipyard maps (nodes, roads, junctions, movements, accessPoints, facilities,
zones), read directly by occupancy.network.Net; D["windport"] additionally records the archetype, its parameters, the stops of
each role and the corridor roads. Net only knows the roles in occupancy.params.FLOW, so the wind classes are mapped through
ROLES (the roles argument of Net), without changing occupancy/:
  wf_storage    storage saddle row: pull-in stop, one per row (as yard)
  wf_cradle     quay cradle: roadside stop that occupies the quay-front road section while placing (as buffer); with
                cradle_mode = "pull_in" it is a pull-in cradle bay (wf_cradle_bay, as assembly_yard)
  wf_ramp       on-vessel pickup point at the top of the RoRo ramp: entry node (as assembly_workshop); the ramp road itself
                is a road resource
to_net(D, p, path) writes the JSON, computes its SHA-256 and returns a Net. The same parameters give byte-identical files.

Geometry (m): x east, y north. The yard road runs east-west along y = 0 with the saddle rows on it (x >= 0); the quay front
runs east-west along y = dist_m with the cradles on it; the corridor runs north-south, its northern corridor_m is single-lane
(corridor_w) and the rest two-lane (yard_w); n_junctions junctions on the single-lane section each connect a side stub
(dead end).
  A1  one two-way corridor; the quay front is a dead end (a single gate).
  A2  loop: loaded trips use the corridor (one-way north), empty trips use the western return road (one-way, from the quay
      gate back to the southern end of the corridor); the quay front is still a dead end.
  A3  two gates: corridor 1 at x = 0 runs one-way north into gate 1, the quay front runs one-way east, out through gate 2,
      and corridor 2 runs one-way south back to the yard; the ramp lies between the cradles and gate 2. With
      bypass = True, loaded vehicles coming down the ramp must take the bypass (one-way south) straight back to the yard.
Ramp (ramp_at): for A1 and A2 "end" (east end of the quay front, unloading flow passes the cradles), "gate" (inside the
gate, before the cradles) or None; for A3 it is fixed between the cradles and gate 2.
Main geometry parameters (GEOMETRIES): gate_cradle_m, distance of the first cradle slot from the gate (a cradle slot is
where the front of the delivering vehicle stops); quay_edge_m, distance of the quay edge from the centre line of the
quay-front road (None: the road edge, apron_w/2); turn_open_m, radius of the turning zone at the gate (no water, no
monopile on a cradle and no corridor-side constraint inside it). The last two enter only the geometry check
(windport/geomcheck.py) and do not change the road network. The default geometry is GEOMETRY (legacy40, the geometry of
the earlier batches, maps unchanged byte for byte); use("main") switches to the main geometry; keyword arguments of build
take precedence.
"""
import hashlib
import json
from pathlib import Path

SC = "org.shipyard.spatial_classification"
RS = "org.shipyard.research_semantics"
ROLES = {"yard": "wf_storage", "buffer": "wf_cradle", "assembly_yard": "wf_cradle_bay", "assembly_workshop": "wf_ramp"}
KINDS = ("A1", "A2", "A3")
# Geometry and road widths are scenario settings; lengths in m
DEFAULTS = dict(dist_m=600.0, corridor_m=400.0, n_cradles=3, ramp_at="end", n_junctions=1,
                corridor_w=10.0, yard_w=20.0, apron_w=12.0, ramp_m=40.0, ramp_w=12.0,
                n_rows=8, row_spacing=15.0, yard_off=60.0, cradle_spacing=110.0, cradle_mode="on_road",
                loop_off=60.0, stub_m=30.0, bypass=True)
GEOMETRIES = dict(legacy40=dict(gate_cradle_m=40.0, quay_edge_m=None, turn_open_m=0.0),
                  main=dict(gate_cradle_m=170.0, quay_edge_m=20.0, turn_open_m=60.0))
GEOMETRY = GEOMETRIES["legacy40"]


def use(name):
    """Make GEOMETRIES[name] the default geometry (process-wide; called in the initializer of the worker processes). The
    network caches have no geometry in their keys and are cleared."""
    global GEOMETRY
    from windport import sim, sim2
    GEOMETRY = GEOMETRIES[name]
    sim._NETS.clear()
    sim2._NETS.clear()


class _Map:
    def __init__(self):
        self.nodes, self.roads, self.oneway, self.ban = {}, {}, set(), set()

    def node(self, nid, x, y, kind="junction"):
        self.nodes[nid] = dict(kind=kind, name=nid, position=[float(x), float(y), 0.0])
        return nid

    def road(self, rid, a, b, w, anchors=(), oneway=False):
        self.roads[rid] = dict(fromNodeId=a, toNodeId=b, name=rid, direction="forward" if oneway else "both",
                               geometry=dict(kind="path", anchors=[[float(x), float(y), 0.0] for x, y in anchors],
                                             spans=[dict(kind="line") for _ in range(len(anchors) + 1)]),
                               widthM=dict(state="known", value=float(w)))
        if oneway:
            self.oneway.add(rid)
        return rid

    def chain(self, rid, pts, w, oneway=False, stubs=(), stub_dir=(-1, 0), stub_m=30.0, stub_w=20.0):
        """Connect the nodes pts in order into roads rid_0, rid_1, ...; each node in stubs gets a dead-end stub.
        Returns the list of road ids."""
        out = []
        for k, (a, b) in enumerate(zip(pts, pts[1:])):
            out.append(self.road(f"{rid}_{k}", a, b, w, oneway=oneway))
        for n in stubs:
            x, y, _ = self.nodes[n]["position"]
            e = self.node(f"{n}_stub", x + stub_dir[0] * stub_m, y + stub_dir[1] * stub_m, "endpoint")
            self.road(f"{n}_stub", n, e, stub_w)
        return out

    def s_on(self, rid, x, y):
        """Distance of point (x, y) from the start of the straight road rid."""
        r = self.roads[rid]
        x0, y0, _ = self.nodes[r["fromNodeId"]]["position"]
        assert not r["geometry"]["anchors"]
        return abs(x - x0) + abs(y - y0)

    def finish(self, meta):
        deg = {}
        for rid, r in self.roads.items():
            for e in ("fromNodeId", "toNodeId"):
                deg.setdefault(r[e], []).append(rid)
        junctions, movements = {}, {}
        for n, rids in sorted(deg.items()):
            if len(rids) < 2:
                continue
            jid = f"j_{n}"
            junctions[jid] = dict(model="explicit_movements", name=jid, nodeIds=[n])
            for ri in rids:
                din = "forward" if self.roads[ri]["toNodeId"] == n else "backward"
                for ro in rids:
                    if ro == ri:
                        continue
                    dout = "forward" if self.roads[ro]["fromNodeId"] == n else "backward"
                    ok = not ((ri in self.oneway and din != "forward") or (ro in self.oneway and dout != "forward")
                              or (n, ri, ro) in self.ban)
                    movements[f"m_{n}_{ri}_{ro}"] = dict(allowed=ok, junctionId=jid, name=f"{ri}→{ro}",
                                                         incomingArc=dict(roadId=ri, direction=din),
                                                         outgoingArc=dict(roadId=ro, direction=dout))
        return dict(schemaVersion="windport-archetype-1", mapId=f"windport_{meta['kind']}", nodes=self.nodes, roads=self.roads,
                    junctions=junctions, movements=movements, accessPoints=self.access, facilities=self.facilities,
                    zones=self.zones, windport=meta)


def build(kind, **kw):
    """Map dict of archetype kind (A1, A2, A3); parameters as in DEFAULTS and GEOMETRIES."""
    assert kind in KINDS, kind
    g = dict(GEOMETRY, **{k: kw.pop(k) for k in list(kw) if k in GEOMETRY})
    q = dict(DEFAULTS, **kw)
    unknown = set(kw) - set(DEFAULTS)
    assert not unknown, f"unknown parameters: {unknown}"
    D, Lc, S = q["dist_m"], q["corridor_m"], int(q["n_cradles"])
    assert 0 < Lc <= D and S >= 1
    m = _Map()
    m.access, m.facilities, m.zones = {}, {}, {}
    meta = dict(kind=kind, params=q, corridor=[], loop=[], gates=[])
    if g != GEOMETRIES["legacy40"]:
        meta["geometry"] = g
    yc = D - Lc                                  # southern end of the single-lane section

    def access_road(rid, x, north, oneway, stub_dir):
        """North-south corridor at x, from the southern end (x, 0) to the northern end (x, D); returns (southern node,
        northern node, southern end of the single-lane section, single-lane roads, two-lane roads).
        north: roads point north; oneway: the single-lane section is one-way (A2 corridor), "all" also makes the
        two-lane section one-way (the two A3 corridors)."""
        s0 = m.node(f"{rid}_S", x, 0.0)
        n1 = m.node(f"{rid}_N", x, D)
        mids = [m.node(f"{rid}_j{k + 1}", x, yc + Lc * (k + 1) / (q["n_junctions"] + 1)) for k in range(q["n_junctions"])]
        wide = []
        c0 = s0
        if yc > 0:
            c0 = m.node(f"{rid}_C", x, yc)
            wide = m.chain(f"{rid}_wide", [s0, c0] if north else [c0, s0], q["yard_w"], oneway=oneway == "all")
        pts = [c0] + mids + [n1]
        lane = m.chain(f"{rid}_lane", pts if north else pts[::-1], q["corridor_w"], oneway=bool(oneway), stubs=mids,
                       stub_dir=stub_dir, stub_m=q["stub_m"], stub_w=q["yard_w"])
        return s0, n1, c0, lane, wide

    # ---- quay front, cradles and ramp
    x_cr = [float(g["gate_cradle_m"]) + k * q["cradle_spacing"] for k in range(S)]      # cradle slots (distance from the gate)
    if kind == "A3":
        ramp_x = x_cr[-1] + q["cradle_spacing"] / 2
        apron_end = ramp_x + 60.0
    elif q["ramp_at"] == "gate":
        ramp_x = 20.0
        x_cr = [ramp_x + x for x in x_cr]
        apron_end = x_cr[-1] + q["cradle_spacing"] / 2
    else:
        ramp_x = x_cr[-1] + q["cradle_spacing"] / 2 if q["ramp_at"] == "end" else None
        apron_end = ramp_x if ramp_x is not None else x_cr[-1] + q["cradle_spacing"] / 2

    # ---- corridor
    if kind in ("A1", "A2"):
        ys, gate, c0, lane, wide = access_road("corr", 0.0, True, kind == "A2", (-1, 0) if kind == "A1" else (1, 0))
        meta["corridor"], meta["gates"] = lane, [gate]
        if kind == "A2":
            ret = m.road("loop", gate, c0, q["corridor_w"], anchors=[(-q["loop_off"], D), (-q["loop_off"], yc)], oneway=True)
            meta["loop"] = [ret]
        g1 = gate
    else:
        ys, g1, _, lane1, _ = access_road("corr1", 0.0, True, "all", (-1, 0))
        ye2, g2, _, lane2, _ = access_road("corr2", apron_end, False, "all", (1, 0))
        meta["corridor"], meta["loop"], meta["gates"] = lane1, lane2, [g1, g2]

    # quay front: gate → cradle section → (ramp junction) → east end
    if ramp_x is not None:
        rj = m.node("ramp_J", ramp_x, D)
        v = m.node("ramp_V", ramp_x, D + q["ramp_m"], "access")
        ramp = m.road("ramp", rj, v, q["ramp_w"])
        meta["ramp_road"] = ramp
    if kind == "A3":
        apron = [m.road("apron_0", g1, rj, q["apron_w"], oneway=True), m.road("apron_1", rj, g2, q["apron_w"], oneway=True)]
        cr_road = "apron_0"
    elif q["ramp_at"] == "gate":
        qe = m.node("apron_E", apron_end, D, "endpoint")
        apron = [m.road("apron_0", g1, rj, q["apron_w"]), m.road("apron_1", rj, qe, q["apron_w"])]
        cr_road = "apron_1"
    elif q["ramp_at"] == "end":
        apron = [m.road("apron_0", g1, rj, q["apron_w"])]
        cr_road = "apron_0"
    else:
        qe = m.node("apron_E", apron_end, D, "endpoint")
        apron = [m.road("apron_0", g1, qe, q["apron_w"])]
        cr_road = "apron_0"
    meta["apron"] = apron

    # ---- yard road and saddle rows; A3 bypass
    x_rows = [q["yard_off"] + k * q["row_spacing"] for k in range(int(q["n_rows"]))]
    xs = sorted({0.0, x_rows[-1] + q["row_spacing"]} | ({apron_end} if kind == "A3" else set())
                | ({ramp_x} if kind == "A3" and q["bypass"] else set()))
    xs[-1] = max(xs[-1], x_rows[-1] + q["row_spacing"])
    ynodes = []
    for x in xs:
        if x == 0.0:
            ynodes.append(ys)
        elif kind == "A3" and x == apron_end:
            ynodes.append(ye2)
        else:
            ynodes.append(m.node(f"yard_{int(x)}", x, 0.0, "junction" if x != xs[-1] else "endpoint"))
    yard = m.chain("yard", ynodes, q["yard_w"])
    if kind == "A3" and q["bypass"]:
        yb = ynodes[xs.index(ramp_x)]
        byp = m.road("bypass", rj, yb, q["corridor_w"], oneway=True)
        meta["bypass"] = byp
        m.ban.add((rj, "apron_0", byp))          # only vehicles coming down the ramp use the bypass
        m.ban.add((rj, ramp, "apron_1"))         # loaded vehicles from the ramp take the bypass, not the eastern quay front
    seg_of = lambda x: next(r for r, a, b in zip(yard, xs, xs[1:]) if a <= x <= b)

    # ---- facilities and zones
    def zone(zid, cls, runs, name, mode=None):
        ext = {SC: dict(classId=cls), RS: dict(classId=cls, frontage=[dict(roadId=r, sStartM=s0, sEndM=s1) for r, s0, s1 in runs])}
        if mode:
            ext[RS]["defaultStopMode"] = mode
        m.zones[zid] = dict(name=name, kind="zone", extensions=ext, boundary=dict(holes=[], outer=[]))

    zone("z_storage", ROLES["yard"],
         [(seg_of(x), m.s_on(seg_of(x), x, 0.0) - 2.0, m.s_on(seg_of(x), x, 0.0) + 2.0) for x in x_rows], "Monopile storage saddle rows", "pull_in")
    ccls = ROLES["buffer"] if q["cradle_mode"] == "on_road" else ROLES["assembly_yard"]
    zone("z_cradle", ccls, [(cr_road, m.s_on(cr_road, x, D) - 5.0, m.s_on(cr_road, x, D) + 5.0) for x in x_cr], "Quay cradles",
         q["cradle_mode"])
    meta["storage"] = [f"z_storage#{k}" for k in range(len(x_rows))]
    meta["cradles"] = [f"z_cradle#{k}" for k in range(S)]
    meta["ramp"] = []
    if ramp_x is not None:
        m.access["ap_ramp"] = dict(nodeId=v, facilityId="f_ramp", name="Ramp top")
        m.facilities["f_ramp"] = dict(name="RoRo ramp (on-vessel pickup point)", kind="ramp", accessPointIds=["ap_ramp"],
                                      extensions={SC: dict(classId=ROLES["assembly_workshop"])}, boundary=dict(holes=[], outer=[]))
        meta["ramp"] = [v]
    return m.finish(meta)


def dumps(D):
    """Canonical JSON bytes (sorted keys, UTF-8): the same parameters give identical bytes."""
    return json.dumps(D, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")


def write(D, path):
    """Write the map JSON and return its SHA-256."""
    raw = dumps(D)
    Path(path).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def to_net(D, p, path):
    """Write the map and build a Net the way occupancy reads it (SHA-256 check, classes mapped by ROLES)."""
    from occupancy.network import Net
    return Net(str(path), write(D, path), p, roles=ROLES)
