"""Independent check of windport/sim4.py. Does not call Net.leg or the planning code of windport.sim / sim4.

1. Alternative turns: the checker's own leg4 (windport.check.leg plus the turn stop of p["turn_extra"]; key
   "node|from-road|to-road" or "node") replaces windport.check.leg during the check, so windport.check.check (and check3)
   verify travel times, release of the incoming road, junction occupancy and sweep item by item with the lengthened legs;
2. Crane reach: lifts at quay position k ≥ p["reach"] are checked as [s, s + p + t_sh]: lifts do not overlap, lie entirely
   within the crane open periods, F_vessel = s + p + t_sh; in the trip table handed to windport.check.check, t_sh is first
   subtracted from F_vessel of these trips (all other items are checked by it as usual);
3. Reserved periods: from (t1, t2, exit) of each trip, leg4 rebuilds the windows of the empty, loaded and departure legs on the
   reserved segment; they must not intersect the reserved periods (recomputed independently from cfg with the definition
   [iT, iT + fT) of windport.sim4.closures)."""
from windport import check as C
from windport import check3 as C3
from exact.check import runs, width
import math

TOL = 1e-6


def leg4(net, cap, size, p, src, dst, v, Lv, b, loaded, start_node, end_res=None):
    """As windport.check.leg, plus the seconds of the alternative turn at the nodes of p["turn_extra"] (only where the vehicle
    already has to stop and turn)."""
    if src == dst:
        return [], 0.0, 0.0
    R, D = runs(net, net.path(src, dst))
    tail = (Lv + p["long_clear"]) / v
    steer = p.get("sweep_steer_s")
    ex = p.get("turn_extra") or {}
    dl = [0.0] * len(R)
    for i in range(1, len(R)):
        ang = net.turn(R[i - 1][4], R[i][3])
        if loaded and steer is not None and math.degrees(ang) >= p["turn_deg"]:
            n = net.arc[R[i][3]][0]
            dl[i] = steer + ang * Lv / 2 / v + float(ex.get(f"{n}|{R[i - 1][0]}|{R[i][0]}", ex.get(n, 0.0)))
    at = lambda i: R[i][2] / v + sum(dl[1:i])
    out = []
    if start_node and ("n", src) in cap:
        out.append((("n", src), width(cap, ("n", src), b, loaded, p), 0.0, tail))
    for i, (rid, fw, d0, a0, a1) in enumerate(R):
        th = at(i)
        nxt = at(i + 1) + dl[i + 1] if i + 1 < len(R) else D / v + sum(dl)
        n = net.arc[a0][0]
        if i > 0 and n in net.node_res:
            ang = net.turn(R[i - 1][4], a0)
            occ = (size[n] + Lv + p["long_clear"]) / v
            if math.degrees(ang) >= p["turn_deg"]:
                if loaded and steer is not None:
                    occ += dl[i]
                    out += [(("r", r), cap[("r", r)], th, th + occ) for r in net.incident[n] if r not in (R[i - 1][0], rid)]
                else:
                    occ += p["turn_sweep_s"]
            out.append((("n", n), width(cap, ("n", n), b, loaded, p), th, th + occ))
        if not (i == len(R) - 1 and end_res == ("r", rid)):
            out.append((("r", rid), width(cap, ("r", rid), b, loaded, p), th, nxt + tail))
    return out, D / v + sum(dl), at(len(R) - 1)


def closures(T, f, H):
    out, i = [], 0
    while i * T < H + T:
        out.append((i * T, i * T + f * T))
        i += 1
    return out


def check(net, p, trips, starts, quay, cal, fixed=False, ramp=(), hold=0, H=None, gate=None, yard=None, cut=False, reserve=None):
    """Arguments as windport.check.check; with cut = True the base part uses windport.check3.check; reserve = dict(res=resource,
    f, T (s), H_end (s)). Returns dict(ok, errors, max_ratio, n_far, n_res)."""
    Sr, sh, P0 = p.get("reach"), float(p.get("shift_s") or 0.0), p["lift_s"]
    far = lambda x: Sr is not None and x["flow"] == "load" and x.get("k") is not None and x["k"] >= Sr and x.get("s") is not None
    tr = [dict(x, F_vessel=x["F_vessel"] - sh) if far(x) and x.get("F_vessel") is not None else x for x in trips]
    old = C.leg
    C.leg = leg4
    try:
        if cut:
            base = C3.check(net, p, tr, starts, quay, cal, ramp, hold, H, gate=gate, yard=yard)
        else:
            base = C.check(net, p, tr, starts, quay, cal, fixed, ramp, hold, H, gate=gate, yard=yard)
    finally:
        C.leg = old
    errs = list(base["errors"])
    # crane: each lift with its true duration
    lifts = []
    for x in trips:
        if x["t1"] >= 1e8 or x.get("s") is None:
            continue
        P = P0 + (sh if far(x) else 0.0)
        lifts.append((x["s"], x["s"] + P, x["id"]))
        if abs(x["F_vessel"] - (x["s"] + P)) > 1e-6:
            errs.append(f"task {x['id']}: F_vessel {x['F_vessel']:.1f} ≠ s + {P:.0f}")
        if cal.get("crane") and not C.inside(x["s"], x["s"] + P, cal["crane"]):
            errs.append(f"task {x['id']}: lift [{x['s']:.1f}, {x['s'] + P:.1f}] outside the berthing period")
    lifts.sort()
    for (s0, e0, j0), (s1, e1, j1) in zip(lifts, lifts[1:]):
        if s1 < e0 - TOL:
            errs.append(f"crane: task {j0} [{s0:.1f}, {e0:.1f}] overlaps task {j1} [{s1:.1f}, {e1:.1f}]")
    n_res = 0
    if reserve:
        res = tuple(reserve["res"])
        wins = closures(reserve["T"], reserve["f"], reserve["H_end"])
        cap, size = net.capacities(p)
        loc = dict(enumerate(starts))
        for x in sorted((x for x in trips if x["t1"] < 1e8), key=lambda x: x["t1"]):
            k = x["vid"]
            so, sd = net.stops[x["o"]], net.stops[x["d"]]
            legs = [(loc[k], so["node"], x["t1"], p["v_empty"], p["plat_len"], p["plat_w"], False, True, so["res"]),
                    (so["node"], sd["node"], x["t2"], p["v_loaded"], p["Lv"], p["B"], True, False, sd["res"])]
            loc[k] = sd["node"]
            if x.get("exit"):
                legs.append((sd["node"], x["exit"][0], x["exit"][1], p["v_empty"], p["plat_len"], p["plat_w"], False, True, None))
                loc[k] = x["exit"][0]
            for src, dst, t0, v, Lv, b, loaded, sn, er in legs:
                W, _, _ = leg4(net, cap, size, p, src, dst, v, Lv, b, loaded, sn, er)
                for r, _, a, e in W:
                    if r != res:
                        continue
                    n_res += 1
                    s_, e_ = t0 + a, t0 + e
                    for ca, cb in wins:
                        if s_ < cb - TOL and ca < e_ - TOL:
                            errs.append(f"vehicle {k} task {x['id']}: on reserved road {res} [{s_:.1f}, {e_:.1f}] intersects reserved period [{ca:.1f}, {cb:.1f}]")
                            break
    return dict(ok=not errs, errors=errs[:20], max_ratio=base.get("max_ratio"), n_far=sum(1 for x in trips if far(x)), n_res=n_res)
