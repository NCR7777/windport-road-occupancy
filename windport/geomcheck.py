"""Geometry check of the parametric port layouts: clearances of the turn sweep circles to the berth water, the piles on
the cradles and the side constraints of the single lane (uses only the layout parameters and the routes of the
road-occupancy model).

Obstacles (obstacles, layout coordinates: x east, y north, gate 1 at (0, D), D = dist_m; geometry parameters in
GEOMETRIES of windport/archetypes.py):
  water   berth water: y ≥ D + e (e = quay_edge_m; if None, half the apron road width apron_w/2). If the gate turning
          area radius t > e, the shoreline steps back at the turning area and the berth starts √(t² − e²) east of the gate
          (for A3 it also ends √(t² − e²) west of gate 2); if t ≤ e the berth runs along the whole apron (including the
          gate).
          For side-by-side cradles (A1side) the shoreline uses e = max(e, bay_m + long_clear) (main setting 40 + 5 = 45 m:
          the end of each short spur keeps longitudinal clearance to the shoreline). This shoreline is used only for the
          geometry check and the figures; quay_edge_m does not enter the road network or the simulation (with 20 m and
          45 m the map road network, time in port and L* are identical), so GEOMETRIES is not changed.
  piles   piles on the cradles (in-line): cradle position k records the vehicle front x_k when the delivery vehicle stops;
          the pile extends L_v back along the incoming road (same convention as the area under the load in
          windport/lift.py), on the sea side of the apron road: x ∈ [x_k − L_v, x_k], y ∈ [D + w/2 + c, D + w/2 + c + B]
          (w apron road width, c lateral clearance lat_clear, B monopile diameter).
          Side-by-side cradles are modelled abstractly as "one drive-in spur per cradle" (the 40 m spur is shorter than
          L_v and does not represent the actual pile placement), so no piles are placed; instead the spur ends are
          checked to be on land (bays_on_land).
  flanks  constraints on both sides of the single-lane corridor (buildings or storage, the reason the lane is single):
          x = corridor centre line ± corridor_w/2, y from the south end of the single lane to t south of the gate (none
          inside the turning area; for A2 the return road joins at the south end of the single lane, which also leaves
          plat_len/2 + c for the empty vehicle to turn).
  The yard side is open (manuscript assumption A6); no obstacles there.
Turns (turns): decision points where the road-occupancy model stops to turn (windport.sim.turn_delays, turn angle
≥ turn_deg), classified by route:
  loading     (saddle row → cradle position used) loaded, sweep radius L_v/2;
  return      (cradle position → saddle row; with a gate holding place, cradle position → gate) empty, radius
              plat_len/2;
  unloading   (ramp top → saddle row) loaded, radius L_v/2, except the ramp foot (junction of the ramp segment with the
              apron);
  ramp foot   first turn after an unloading vehicle comes down the ramp. Treated by assumption: the SPMT completes it by
              crabbing or re-orientation after the ramp, not as a 90° swept turn; the clearance is recorded only and
              does not count towards pass/fail;
  bay entry   side-by-side cradles turning from the apron into a spur (abstract; adjacent spurs are only pitch_m apart);
              clearance recorded only, not counted towards pass/fail.
Clearance = distance from circle centre to the obstacle − radius (< 0 means overlap). ok of check considers only loading
and return (plus piles on land and spurs on land); ok_unload also considers unloading (except the ramp foot).
Main2 geometry (main2, windport/main2.py; the items below apply only when the geometry has ramp_axis, results of
legacy40 and main are byte-for-byte unchanged):
  rebuilt side-by-side cradles (layout = "rows"): piles are placed on the rows (x ∈ [head − L_v, head], y = row centre
          line ± B/2); the shoreline lies d0 = quay_edge_m − (w/2 + c + B/2) beyond the centre line of the row closest
          to the shore (the same distance as from the piles on in-line cradles to the shoreline), and the berth water
          starts at the west end of the piles x0_m; bay entry (turning from a branch node into a row) is a real turn,
          counted as loading, and ok is computed as usual.
  ramp in line with the apron (ramp_axis = "along"): the RoRo vessel berths end-on at the east end of the apron,
          another water area starts ramp_m/2 east of the ramp foot; a turn at the ramp foot, if any, counts as unloading
          (no longer an assumption).
  The A2 return loop has an open turning area of radius loop_open_m where it joins the south end of the single lane (the
  single-lane side constraints start loop_open_m north of the junction)."""
import math

from windport import sim as WS
from windport import sim4 as S4

BIG = 1e5
ASSUMED = ("ramp foot", "bay entry")               # clearance recorded only, not counted towards pass/fail


def _rect_dist(x, y, r):
    x0, x1, y0, y1 = r
    return math.hypot(max(x0 - x, 0.0, x - x1), max(y0 - y, 0.0, y - y1))


def quay_edge(D, p):
    """Distance of the shoreline from the apron road centre line (m): quay_edge_m (None means apron_w/2); for side-by-side
    cradles max(·, bay_m + long_clear)."""
    from windport import archetypes as A
    W = D["windport"]
    q, g = W["params"], W.get("geometry", A.GEOMETRIES["legacy40"])
    e = q["apron_w"] / 2 if g["quay_edge_m"] is None else float(g["quay_edge_m"])
    if W.get("layout") == "side":
        e = max(e, q["bay_m"] + p["long_clear"])
    if W.get("layout") == "rows":
        e = W["row_y"][0] + row_d0(D, p)
    return e


def row_d0(D, p):
    """Rebuilt side-by-side rows: distance (m) from the pile centre line of the row closest to the shore to the shoreline,
    equal to the pile centre line to shoreline distance of in-line cradles = quay_edge_m − (w/2 + c + B/2)."""
    q, g = D["windport"]["params"], D["windport"]["geometry"]
    return float(g["quay_edge_m"]) - (q["apron_w"] / 2 + p["lat_clear"] + p["B"] / 2)


def obstacles(D, p):
    """{class: [(x0, x1, y0, y1)]}, see the module docstring."""
    from windport import archetypes as A
    W = D["windport"]
    q, g = W["params"], W.get("geometry", A.GEOMETRIES["legacy40"])
    Dm, w = q["dist_m"], q["apron_w"]
    e = quay_edge(D, p)
    t = float(g["turn_open_m"])
    pos = lambda n: D["nodes"][n]["position"][:2]
    gx = [pos(n)[0] for n in W["gates"]]
    back = math.sqrt(t * t - e * e) if t > e else -BIG
    x0 = gx[0] + back
    x1 = gx[1] - back if W["kind"] == "A3" else BIG
    if W.get("layout") == "rows":
        x0 = q["x0_m"]
    out = dict(water=[(x0, x1, Dm + e, BIG)], piles=[], flanks=[])
    c, B = p["lat_clear"], p["B"]
    if g.get("ramp_axis") == "along" and W["kind"] in ("A1", "A2") and q["ramp_at"] == "end":     # RoRo vessel at the east end
        xj = D["nodes"]["ramp_J"]["position"][0]
        out["water"].append((xj + q["ramp_m"] / 2, BIG, Dm - w / 2 - q["ramp_m"] / 2, BIG))
    if W.get("layout") == "rows":
        for y in W["row_y"]:
            out["piles"].append((q["head_m"] - p["Lv"], q["head_m"], Dm + y - B / 2, Dm + y + B / 2))
    elif W.get("layout") != "side":
        for f in D["zones"]["z_cradle"]["extensions"][A.RS]["frontage"]:
            a = pos(D["roads"][f["roadId"]]["fromNodeId"])
            xk = a[0] + (f["sStartM"] + f["sEndM"]) / 2
            out["piles"].append((xk - p["Lv"], xk, Dm + w / 2 + c, Dm + w / 2 + c + B))
    lanes = [W["corridor"]] + ([W["loop"]] if W["kind"] == "A3" else [])
    for lane in lanes:
        pts = [pos(D["roads"][r][e_]) for r in lane for e_ in ("fromNodeId", "toNodeId")]
        xc, ylo = pts[0][0], min(y for _, y in pts)
        if W["kind"] == "A2":                   # return road joins here: open area for the empty turn (plat_len/2 + c)
            ylo += float(g["loop_open_m"]) if "loop_open_m" in g else p["plat_len"] / 2 + c
        yhi = max(y for _, y in pts) - t
        if yhi > ylo:
            hw = q["corridor_w"] / 2
            out["flanks"] += [(xc - hw, xc - hw, ylo, yhi), (xc + hw, xc + hw, ylo, yhi)]
    return out


def turns(cfg):
    """(D, p, [(node, turn angle in degrees, route class, centre (x, y), radius)]): the turns on all routes, each node
    recorded once per route class (largest angle)."""
    D, net, p, *_ = S4.setup4(cfg)
    W = D["windport"]
    if W["kind"] not in ("A1", "A2", "A3"):
        return D, p, []
    quay, rows = W["cradles"][:max(1, cfg["S"])], W["storage"]
    legs = [(o, d, "load-out") for o in rows for d in quay] + [(d, o, "return") for o in rows for d in quay]
    if WS.hold_of(cfg):
        legs += [(d, W["gates"][-1], "return") for d in quay]
    legs += [(v, o, "unloading") for v in W.get("ramp") or [] for o in rows]
    foot = {D["roads"][W["ramp_road"]]["fromNodeId"]} if W.get("ramp_road") else set()
    seen = {}
    for a, b, route in legs:
        na = net.stops[a]["node"] if a in net.stops else a
        nb = net.stops[b]["node"] if b in net.stops else b
        loaded = route != "return"
        L = p["Lv"] if loaded else p["plat_len"]
        runs, dl = WS.turn_delays(net, net.path(na, nb), L, p["v_loaded"] if loaded else p["v_empty"], p)
        for i in range(1, len(runs)):
            if dl[i]:
                n = net.arc[runs[i][2]][0]
                r = route
                if route == "unloading" and n in foot:
                    r = "ramp foot"
                elif route == "load-out" and str(runs[i][0]).startswith("bay_"):
                    r = "bay entry"
                elif route == "load-out" and W.get("layout") == "rows" and str(runs[i][0]).startswith("row_"):
                    r = "bay entry"
                deg = math.degrees(net.turn(runs[i - 1][3], runs[i][2]))
                k = (n, r)
                if k not in seen or deg > seen[k][1]:
                    seen[k] = (n, round(deg, 1), r, tuple(D["nodes"][n]["position"][:2]), L / 2)
    order = ("load-out", "return", "unloading", "ramp foot", "bay entry")
    return D, p, sorted(seen.values(), key=lambda x: (order.index(x[2]), x[0]))


def check(cfg):
    """Clearance of each turn, and whether the piles and side-by-side spurs are on land: dict(rows=[...], ok, ok_unload,
    piles_on_land, bays_on_land, min_clear, min_unload, assumed). ok considers only loading and return (plus piles and spurs on
    land); ok_unload considers unloading (except the ramp foot; None when there is no unloading route); assumed holds the minimum
    clearances of ramp foot and bay entry (recorded only)."""
    D, p, ts = turns(cfg)
    if not ts:
        return dict(rows=[], ok=None, ok_unload=None, piles_on_land=None, bays_on_land=None, min_clear=None, min_unload=None, assumed={})
    allob = obstacles(D, p)
    ob = {k: v for k, v in allob.items() if v}             # absent obstacle classes (no piles side-by-side) are not listed
    rows = []
    for n, deg, route, (x, y), R in ts:
        r = dict(node=n, deg=deg, route=route, R=R)
        for k, rs in ob.items():
            r[k] = round(min((_rect_dist(x, y, q) for q in rs), default=BIG) - R, 2)
        r["ok"] = int(all(r[k] >= 0 for k in ob))
        rows.append(r)
    W = D["windport"]
    edge = ob["water"][0][2]
    land = all(q[3] <= edge + 1e-9 for q in allob["piles"])
    bays = None
    if W.get("layout") == "side":
        bays = int(all(D["nodes"][D["roads"][b]["toNodeId"]]["position"][1] <= edge + 1e-9 for b in W["apron"] if str(b).startswith("bay_")))
    # main2 geometry: bay entry in rebuilt side-by-side rows is a real turn (counted as loading); with the ramp in line with the
    # apron the ramp-foot turn counts as unloading (no longer recorded only by assumption)
    assumed = tuple(a for a in ASSUMED if not ((a == "bay entry" and W.get("layout") == "rows") or
                                               (a == "ramp foot" and W.get("geometry", {}).get("ramp_axis") == "along")))
    main = [r for r in rows if r["route"] in ("load-out", "return") or (r["route"] == "bay entry" and "bay entry" not in assumed)]
    unl = [r for r in rows if r["route"] == "unloading" or (r["route"] == "ramp foot" and "ramp foot" not in assumed)]
    mn = lambda rs: {k: min(r[k] for r in rs) for k in ob} if rs else None
    return dict(rows=rows, ok=int(all(r["ok"] for r in main) and land and bays in (None, 1)), ok_unload=int(all(r["ok"] for r in unl)) if unl else None,
                piles_on_land=int(land), bays_on_land=bays, min_clear=mn(main), min_unload=mn(unl),
                assumed={a: mn([r for r in rows if r["route"] == a]) for a in assumed if any(r["route"] == a for r in rows)})
