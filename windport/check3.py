"""Independent check of windport/sim3.py (the cut as a single resource). Does not call Net.leg, the planning code of
windport.sim or sim3.CutSim.

1. The fixed-duration part is checked as in windport.check.check(fixed=True) (stops, holding places, cradles, crane, ramp,
   timing, completion events);
2. Single lanes: from each trip's (t1, t2, exit) and the network facts, the checker's own windport.check.leg rebuilds the
   occupation of the empty, loaded and exit legs; on each single lane (the corridor roads and the junctions between them;
   for A3 the loop is a separate lane; fixed independently from the archetype record) the windows of each leg are merged
   into one interval [earliest, latest], and no two intervals (of any vehicle or leg) may overlap."""
from windport import check as C

TOL = 1e-6


def lane_groups(net):
    D = net.D
    W = D["windport"]
    out = []
    for roads in [list(W.get("corridor") or [])] + ([list(W.get("loop") or [])] if W["kind"] == "A3" else []):
        if not roads:
            continue
        s = {("r", r) for r in roads}
        nodes = [n for r in roads for n in (D["roads"][r]["fromNodeId"], D["roads"][r]["toNodeId"])]
        s |= {("n", n) for n in set(nodes) if nodes.count(n) >= 2 and n in net.node_res}
        out.append(s)
    return out


def check(net, p, trips, starts, quay, cal, ramp=(), hold=0, H=None, gate=None, yard=None):
    base = C.check(net, p, trips, starts, quay, cal, True, ramp, hold, H, gate=gate, yard=yard)
    errs = list(base["errors"])
    cap, size = net.capacities(p)
    groups = lane_groups(net)
    iv = [[] for _ in groups]
    loc = dict(enumerate(starts))
    for x in sorted((x for x in trips if x["t1"] < 1e8), key=lambda x: x["t1"]):
        k = x["vid"]
        so, sd = net.stops[x["o"]], net.stops[x["d"]]
        legs = [(loc[k], so["node"], x["t1"], p["v_empty"], p["plat_len"], p["plat_w"], False, True, so["res"]),
                (so["node"], sd["node"], x["t2"], p["v_loaded"], p["Lv"], p["B"], True, False, sd["res"])]
        loc[k] = sd["node"]
        if x.get("exit"):
            node, t, _ = x["exit"]
            legs.append((sd["node"], node, t, p["v_empty"], p["plat_len"], p["plat_w"], False, True, None))
            loc[k] = node
        for src, dst, t0, v, Lv, b, loaded, sn, er in legs:
            W, _, _ = C.leg(net, cap, size, p, src, dst, v, Lv, b, loaded, sn, er)
            for g, lane in enumerate(groups):
                w = [(a, e) for r, _, a, e in W if r in lane]
                if w:
                    iv[g].append((t0 + min(a for a, _ in w), t0 + max(e for _, e in w), k, x["id"]))
    for g, ivg in enumerate(iv):
        ivg.sort()
        end, who = -1e18, None
        for s, e, k, j in ivg:
            if H is not None and s >= H:
                continue
            if s < end - TOL:
                errs.append(f"single lane {g}: vehicle {k} task {j} [{s:.1f}, {e:.1f}] overlaps {who} (until {end:.1f})")
                break
            if e > end:
                end, who = e, (k, j)
    return dict(ok=not errs, errors=errs[:20], n_lane=sum(len(x) for x in iv))
