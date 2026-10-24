"""Independent check of the conservative lifting rule (windport/lift.py). Does not call Net.leg, the planning code of
windport.sim / lift, or lift.under_res.

1. All checks of windport.check.check (with its conventions when fixed);
2. clear: for every lift from the vehicle (how = "direct"), lift start ≥ loaded departure + the latest window end of the
   loaded leg rebuilt by this checker from the road-network facts (windport.check.leg, excluding the terminal stop
   resource), i.e. the vehicle body has left the road;
3. under (non-fixed duration representation): during [s, s + d] after each lift starts (from the vehicle or from a cradle;
   from the vehicle d = max(t_u, x·p), from a cradle d = t_u, t_u = lift_tu × p), no other window may lie on the resources
   under the load: the map road segment of the lifting position (with sections, every section intersecting the load),
   junctions at either end of that road lying within the load extent, and for a drive-in position the stand of the lifting
   position itself; the load occupies the open interval extending L_v back from the stop along the incoming road (the
   incoming direction is determined by the checker from the last run of this trip's loaded route), fixed independently
   from the map geometry and the section table. For a lift from the vehicle the trip's own window at the lifting position
   is exempt (the vehicle is under the load); for a lift from a cradle nothing is exempt. The windows of each leg (empty,
   origin stop, loaded, terminal stop, departure) are rebuilt from (t1, t2, tc, s, exit) of each trip and the road-network
   facts, as in windport.check.
4. Sensitivity p["lift_span"] = "gate": the resources under the load are found by going back L_v along the route runs from
   the span (including the gate and the single-lane top section; when the gate is within range, the gate holding place
   too; its window runs from arrival at the holding place on departure until the next empty departure)."""
import collections
import math

from exact.check import runs
from occupancy.network import polyline
from windport import check as C

TOL = C.TOL
TU = 0.05                   # default t_u / p (same as TU in windport/lift.py, checked by tests)
BASE = C.check              # original checker at import time (no recursion when windport.check.check is replaced by this check)


def under(net, sid, Lp, fw):
    """Resources under the load at lifting position sid (from map geometry): fw means arrival runs forward along the segment and
    the load lies in (s − Lp, s), otherwise in (s, s + Lp)."""
    _, rid, s = net.stops[sid]["node"].split("|")
    s = float(s)
    lo, hi = (s - Lp, s) if fw else (s, s + Lp)
    r = net.D["roads"][rid]
    if "lengthM" in r:                    # derived graph of a shipyard: stored centre-line length
        L = r["lengthM"]
    else:
        poly = polyline(net.D, r)
        L = sum(math.dist(a, b) for a, b in zip(poly, poly[1:]))
    cuts = [0.0] + list(net.edges.get(rid, [])) + [L]
    names = net.sec.get(rid, [rid])
    out = [("r", q) for q, a, b in zip(names, cuts, cuts[1:]) if a < hi and b > lo]
    bay = [net.stops[sid]["res"]] if net.stops[sid]["res"][0] == "b" else []              # drive-in: the stand itself
    return out + [("n", n) for n, at in ((r["fromNodeId"], 0.0), (r["toNodeId"], L)) if lo < at < hi and n in net.node_res] + bay


def span(net, sid, Lp, o_node, d_node, gate):
    """Sensitivity p["lift_span"] = "gate": with the runs of exact.check.runs (rid, direction, start distance, first arc,
    last arc), route length D minus the start distance of a run is its distance to the stop; runs whose end distance < L_v
    are under the load, and so is the start junction of runs whose start distance < L_v; when the gate (where the holding
    place is) is closer than L_v, the holding place HOLD is added. Union with under."""
    R, D = runs(net, net.path(o_node, d_node))
    out = set(under(net, sid, Lp, R[-1][1]))
    ends = [r[2] for r in R[1:]] + [D]
    for (rid, _, d0, a0, _), d1 in zip(R, ends):
        if D - d1 < Lp - TOL:
            out.add(("r", rid))
        if D - d0 < Lp - TOL:
            n = net.arc[a0][0]
            if n in net.node_res:
                out.add(("n", n))
            if n == gate:
                out.add(C.HOLD)
    return sorted(out)


def arrive_fw(net, o_node, d_node):
    """Whether the last run of this trip's loaded route goes forward along the segment (runs of exact.check.runs)."""
    return runs(net, net.path(o_node, d_node))[0][-1][1]


def windows(net, p, trips, starts, H=None):
    """Occupancy windows of every leg of every trip: {resource: [(start, end, (vehicle, task, leg))]} (leg: E empty,
    o origin stop, L loaded, d terminal stop, X departure, H gate holding place: from arrival at the holding place on
    departure until the next empty departure)."""
    cap, size = net.capacities(p)
    P, frac = p["lift_s"], p.get("release_frac", 0.0)
    tail, clr = (p["Lv"] + p["long_clear"]) / p["v_loaded"], (p["plat_len"] + p["long_clear"]) / p["v_empty"]
    out = collections.defaultdict(list)
    by = collections.defaultdict(list)
    for x in trips:
        if x["t1"] < 1e8:
            by[x["vid"]].append(x)
    for k, lst in by.items():
        loc, held = starts[k], None
        for x in sorted(lst, key=lambda x: x["t1"]):
            own = lambda g: (k, x["id"], g)
            if held is not None:
                out[C.HOLD].append((held[0], x["t1"], held[1]))
                held = None
            so, sd = net.stops[x["o"]], net.stops[x["d"]]
            load, unload = (p["hp_s"], p["hd_s"]) if x["flow"] == "load" else (p["roro_s"], p["hy_s"])
            E, _, accE = C.leg(net, cap, size, p, loc, so["node"], p["v_empty"], p["plat_len"], p["plat_w"], False, True, so["res"])
            L, _, accL = C.leg(net, cap, size, p, so["node"], sd["node"], p["v_loaded"], p["Lv"], p["B"], True, False, sd["res"])
            out[so["res"]].append((x["t1"] + accE, x["t2"] + tail, own("o")))
            for g, t0, W in (("E", x["t1"], E), ("L", x["t2"], L)):
                for r, _, a, b in W:
                    out[r].append((t0 + a, t0 + b, own(g)))
            if x["flow"] == "load":
                s = x["s"]
                direct = x["how"] == "direct"
                r0 = (s + frac * P if direct else x["tc"] + unload) if s is not None else (1e9 if direct else x["tc"] + unload)
                end = r0 + clr
            else:
                end = x["tc"] + unload + clr
            loc = sd["node"]
            if x.get("exit"):
                node, t, _ = x["exit"]
                X, _, _ = C.leg(net, cap, size, p, loc, node, p["v_empty"], p["plat_len"], p["plat_w"], False, True)
                end = t if sd["res"] in {r for r, *_ in X} else t + clr
                for r, _, a, b in X:
                    out[r].append((t + a, t + b, own("X")))
                loc = node
                if x["exit"][2] == "hold":
                    held = (x["rel"], own("H"))
            out[sd["res"]].append((x["t2"] + accL, end, own("d")))
        if held is not None:
            out[C.HOLD].append((held[0], H if H is not None else 1e9, held[1]))
    return out


def check(net, p, trips, starts, quay, cal, fixed=False, ramp=(), hold=0, H=None, gate=None, yard=None):
    """Arguments as windport.check.check. Returns dict(ok, errors, max_ratio, holds, n_clear (trips checked for clear),
    n_under (trips checked for under))."""
    base = BASE(net, p, trips, starts, quay, cal, fixed, ramp, hold, H, gate=gate, yard=yard)
    errs = list(base["errors"])
    cap, size = net.capacities(p)
    xP = p.get("release_frac", 0.0) * p["lift_s"]
    tu = p.get("lift_tu", TU) * p["lift_s"]
    lifts = [x for x in trips if x["t1"] < 1e8 and x["flow"] == "load" and x["s"] is not None and (H is None or x["s"] < H)]
    live = [x for x in lifts if x["how"] == "direct"]
    for x in live:
        so, sd = net.stops[x["o"]], net.stops[x["d"]]
        L, TL, _ = C.leg(net, cap, size, p, so["node"], sd["node"], p["v_loaded"], p["Lv"], p["B"], True, False, sd["res"])
        end = x["t2"] + max([TL] + [b for *_, b in L])
        if x["s"] < end - TOL:
            errs.append(f"vehicle {x['vid']} task {x['id']}: lift started before the vehicle body left the road (lift start {x['s']:.1f} earlier than {end:.1f})")
    nu = 0
    chk = [x for x in lifts if (max(tu, xP) if x["how"] == "direct" else tu) > TOL] if not fixed else []
    if chk:
        W = windows(net, p, trips, starts, H)
        wide = p.get("lift_span", "head") == "gate"
        g0 = gate if gate is not None else C.idle_nodes(net)[0]
        for x in chk:
            direct = x["how"] == "direct"
            a, b = x["s"], x["s"] + (max(tu, xP) if direct else tu)
            nu += 1
            on, dn = net.stops[x["o"]]["node"], net.stops[x["d"]]["node"]
            for u in (span(net, x["d"], p["Lv"], on, dn, g0) if wide else under(net, x["d"], p["Lv"], arrive_fw(net, on, dn))):
                for s, e, own in W.get(u, []):
                    if not (direct and own == (x["vid"], x["id"], "d")) and s < b - TOL and e > a + TOL:
                        errs.append(f"vehicle {x['vid']} task {x['id']} ({x['how']}): during the lift [{a:.1f}, {b:.1f}] a vehicle ({own}) is on {u} under the load [{s:.1f}, {e:.1f}]")
                        break
    return dict(ok=not errs, errors=errs[:20], max_ratio=base["max_ratio"], holds=base["holds"], n_clear=len(live), n_under=nu)
