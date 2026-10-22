"""Independent checker for the port simulation (does not call Net.leg, Net.demand, Sim or the planning code of windport.sim).

Following the process definitions and the header of windport.sim, occupation is rebuilt from each trip's
(t1, t2, tc, s, r0, exit) and the network facts (shortest paths, arc lengths, junction sizes, capacities, turning angles,
stops):
  road: from the decision point entering it to the next decision point + (vehicle length + longitudinal clearance)/speed;
        a roadside stop at the destination is the last road and is counted only as the stop;
  turn: a loaded vehicle stops at turning angles ≥ turn_deg for δ = sweep_steer_s + angle × (Lv/2)/v, later times shift by
        δ and the release of the incoming road is delayed by δ; when the turn is a junction resource the junction is held
        for (D + Lv + longitudinal clearance)/v + δ and the other arms are held exclusively; empty vehicles only add
        turn_sweep_s at junctions; an empty leg starting from a junction or entry node holds it for one tail time;
  origin stop: from the empty leg entering the last road (or from the empty departure if already at the origin) to the
        loaded departure + tail;
  destination stop: from the loaded leg entering the last road to leaving the quay (roadside quay stop) or leaving + empty
        clearance (pull-in quay stop, saddle row); for unloading, placement + empty clearance;
  cradle k: from arrival to lift start, and cradle k must be this trip's quay stop (quay[k] = d); crane: lift_s from lift
        start;
  leaving the quay: from the exit time, empty travel to the gate (gate holding place) or the yard side; in the holding
        place until this vehicle's next empty departure (or the simulation horizon H if none); the two idle positions
        are fixed independently by the archetype topology (idle_nodes), and an exit record whose destination does not
        match its node, or that goes to a holding place when there are none, is an error;
        the yard side is treated as open ground and not counted (assumption);
  closed periods of the calendar: the ramp road, the on-vessel pickup point and the crane are held at full capacity.
Widths as in exact.check.width (stop, holding place, cradle, crane: 1 each). Widths are merged by the per-instant maximum
**only within one leg** (leg = the empty part, origin stop, loaded part, destination stop, cradle, crane, exit and wait of a
trip); different legs and different trips are counted separately even for the same vehicle, since the vehicle body is only
in one place.
Timing: consecutive trips of a vehicle, empty + pickup, arrival time, lift no earlier than placement complete (direct lift:
no earlier than arrival), release time (direct lift: release_frac·p after lift start), exit no earlier than release, each
lift entirely inside a crane opening, each ramp operation entirely inside a ramp opening, F_ramp equal to the end of the
loaded window on the ramp, completion events matching their definitions, each task done at most once. fixed = True
(fixed-duration representation) only checks stops, holding places, cradles, crane and ramp."""
import collections
import math

from exact.check import runs, width

TOL = 1e-6
HOLD = ("b", "hold", 0)


def leg(net, cap, size, p, src, dst, v, Lv, b, loaded, start_node, end_res=None):
    """Occupation [(resource, width, relative start, relative end)] of one leg, its travel time (including steering stops)
    and the relative time of entering the last road. When end_res is a roadside stop the last road is not counted
    separately."""
    if src == dst:
        return [], 0.0, 0.0
    R, D = runs(net, net.path(src, dst))
    tail = (Lv + p["long_clear"]) / v
    steer = p.get("sweep_steer_s")
    dl = [0.0] * len(R)
    for i in range(1, len(R)):
        ang = net.turn(R[i - 1][4], R[i][3])
        if loaded and steer is not None and math.degrees(ang) >= p["turn_deg"]:
            dl[i] = steer + ang * Lv / 2 / v
    at = lambda i: R[i][2] / v + sum(dl[1:i])           # arrival at the start of section i (before stopping)
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


def inside(a, b, wins):
    return any(x - TOL <= a and b <= y + TOL for x, y in wins)


def idle_nodes(net):
    """The two legal idle positions of an archetype: the gate with the gate holding place (the last gate recorded by the
    archetype: for A1 and A2 the gate where the single lane meets the quay front, for A3 gate 2), and the yard side (on the
    corridor used to leave the quay, the two-lane node at the southern end of the single lane; the yard junction when the
    single lane runs all the way to the yard). Fixed by the archetype topology, not read from the simulation."""
    W = net.D["windport"]
    pre = "corr2" if W["kind"] == "A3" else "corr"
    return W["gates"][-1], (f"{pre}_C" if f"{pre}_C" in net.D["nodes"] else f"{pre}_S")


def check(net, p, trips, starts, quay, cal, fixed=False, ramp=(), hold=0, H=None, gate=None, yard=None):
    """trips: windport.sim.PortSim.trips; starts: start node of each vehicle; quay: quay stops (cradle k = quay[k]); cal:
    opening periods (seconds); hold: number of gate holding places (math.inf = unlimited); H: simulation horizon
    (occupation truncated there); gate, yard: legal idle positions (from idle_nodes and the archetype topology if not given).
    Leaving the quay may only go to these two: to the holding place only at the gate and with hold > 0; to the yard side
    only at the yard-side node. Returns dict(ok, errors, max_ratio, holds)."""
    g0, y0 = idle_nodes(net)
    gate, yard = gate or g0, yard or y0
    cap, size = net.capacities(p)
    cap = {**cap, ("c", "crane"): 1.0, HOLD: float(hold) if hold != math.inf else 1e6, **{("c", "cr", k): 1.0 for k in range(len(quay))}}
    ramp = set(ramp)
    keep = (lambda r: r[0] in ("b", "c") or r in ramp) if fixed else (lambda r: True)
    errs, holds = [], collections.defaultdict(list)
    P, clr = p["lift_s"], (p["plat_len"] + p["long_clear"]) / p["v_empty"]
    frac = p.get("release_frac", 0.0)
    ids = collections.Counter(x["id"] for x in trips if x["t1"] < 1e8)
    errs += [f"task {j} done {n} times" for j, n in ids.items() if n > 1]
    by = collections.defaultdict(list)
    for x in trips:
        by[x["vid"]].append(x)
    for k, lst in sorted(by.items()):
        loc, prev, hold_from = starts[k], 0.0, None
        lst = sorted((x for x in lst if x["t1"] < 1e8), key=lambda x: x["t1"])      # trips booked "later" (after the window): not checked
        for x in lst:
            own = lambda leg_: (k, x["id"], leg_)
            if hold_from is not None:                    # previous trip ended in the gate holding place: wait until this departure
                holds[HOLD].append((hold_from, x["t1"], 1.0, own("H")))
                hold_from = None
            so, sd = net.stops[x["o"]], net.stops[x["d"]]
            load, unload = (p["hp_s"], p["hd_s"]) if x["flow"] == "load" else (p["roro_s"], p["hy_s"])
            direct = x["how"] == "direct"
            E, TE, accE = leg(net, cap, size, p, loc, so["node"], p["v_empty"], p["plat_len"], p["plat_w"], False, True, so["res"])
            L, TL, accL = leg(net, cap, size, p, so["node"], sd["node"], p["v_loaded"], p["Lv"], p["B"], True, False, sd["res"])
            tail = (p["Lv"] + p["long_clear"]) / p["v_loaded"]
            t1, t2, tc, s = x["t1"], x["t2"], x["tc"], x["s"]
            tag = f"vehicle {k} task {x['id']}"
            if t1 < prev - TOL:
                errs.append(f"{tag}: empty departure {t1:.1f} before previous release {prev:.1f}")
            if t2 < t1 + TE + load - TOL:
                errs.append(f"{tag}: loaded departure {t2:.1f} before arrival + pickup {t1 + TE + load:.1f}")
            if abs(tc - (t2 + TL)) > 1e-3:
                errs.append(f"{tag}: arrival {tc:.1f} ≠ loaded departure + travel {t2 + TL:.1f}")
            for r, w, a, b in E:
                holds[r].append((t1 + a, t1 + b, w, own("E")))
            for r, w, a, b in L:
                holds[r].append((t2 + a, t2 + b, w, own("L")))
            holds[so["res"]].append((t1 + accE, t2 + tail, width(cap, so["res"], p["B"], True, p), own("o")))
            live = s is not None
            if x["flow"] == "load":
                if quay[x["k"]] != x["d"]:
                    errs.append(f"{tag}: cradle {x['k']} is not this trip's quay stop {x['d']}")
                r0 = (s + frac * P if direct else tc + unload) if live else (1e9 if direct else tc + unload)
                if x.get("r0") is not None and abs(x["r0"] - r0) > 1e-6:
                    errs.append(f"{tag}: release {x['r0']:.1f} ≠ {r0:.1f}")
                if live:
                    if s < tc + (0.0 if direct else unload) - TOL:
                        errs.append(f"{tag}: lift start {s:.1f} before {'arrival' if direct else 'placement complete'}")
                    if not inside(s, s + P, cal.get("crane") or [(0.0, math.inf)]):
                        errs.append(f"{tag}: lift [{s:.1f}, {s + P:.1f}] outside the berthing period")
                    if abs(x["F_vessel"] - (s + P)) > 1e-6:
                        errs.append(f"{tag}: F_vessel does not match its definition")
                    holds[("c", "crane")].append((s, s + P, 1.0, own("C")))
                holds[("c", "cr", x["k"])].append((tc, s if live else 1e9, 1.0, own("K")))
                if not direct and abs(x["F_quay"] - (tc + unload)) > 1e-6:
                    errs.append(f"{tag}: F_quay does not match its definition")
                end, rel = r0 + clr, r0
            else:
                end, rel = tc + unload + clr, tc + unload
                if abs(x["F_yard"] - rel) > 1e-6:
                    errs.append(f"{tag}: F_yard does not match its definition")
                rw = [b for r, w, a, b in L if r in ramp and r[0] == "r"]
                if ramp:
                    if x["F_ramp"] is None or abs(x["F_ramp"] - (t2 + max(rw))) > 1e-6:
                        errs.append(f"{tag}: F_ramp {x['F_ramp']} ≠ end of the loaded window on the ramp {t2 + max(rw):.1f}")
                    if cal.get("ramp") is not None and not inside(t1 + accE, t2 + max(rw), cal["ramp"]):
                        errs.append(f"{tag}: ramp operation [{t1 + accE:.1f}, {t2 + max(rw):.1f}] outside the tidal window")
            loc = sd["node"]
            # After release the empty vehicle leaves the quay (no earlier than release; if later, it waits on the quay stop)
            if x.get("exit"):
                node, t, kind = x["exit"]
                if t < rel - TOL:
                    errs.append(f"{tag}: leaves the quay at {t:.1f} before release {rel:.1f}")
                if kind == "hold" and not (node == gate and hold > 0):
                    errs.append(f"{tag}: leaves to the gate holding place, but node {node} is not gate {gate} or the number of gate holding places is {hold}")
                elif kind == "yard" and node != yard:
                    errs.append(f"{tag}: leaves to the yard side, but node {node} is not the yard-side node {yard}")
                elif kind not in ("hold", "yard"):
                    errs.append(f"{tag}: invalid exit destination {kind}")
                X, TX, _ = leg(net, cap, size, p, loc, node, p["v_empty"], p["plat_len"], p["plat_w"], False, True)
                end = t if sd["res"] in {r for r, *_ in X} else t + clr
                for r, w, a, b in X:
                    holds[r].append((t + a, t + b, w, own("X")))
                rel, loc = t + TX, node
                if kind == "hold":
                    hold_from = rel
            holds[sd["res"]].append((t2 + accL, end, width(cap, sd["res"], p["B"], True, p), own("d")))
            if abs(x["rel"] - rel) > 1e-6 and rel < 1e8:
                errs.append(f"{tag}: release time {x['rel']:.1f} ≠ {rel:.1f}")
            prev = rel
        if hold_from is not None:
            holds[HOLD].append((hold_from, H if H is not None else 1e9, 1.0, (k, "end", "H")))
    n = 0
    for key, rs in (("crane", [("c", "crane")]), ("ramp", sorted(ramp))):
        if cal.get(key) is None:
            continue
        t = 0.0
        for a, b in sorted(cal[key]) + [(1e9, 1e9)]:
            for r in rs:
                if a > t:
                    holds[r].append((t, a, cap[r], ("cal", n)))
            n += 1
            t = max(t, b)
    ratio = 0.0
    for r, iv in holds.items():
        if not keep(r):
            continue
        if H is not None:
            iv = [(s, min(e, H), w, o) for s, e, w, o in iv if s < H]
        ts = sorted({y for s, e, _, _ in iv for y in (s, e)})
        for a, b in zip(ts, ts[1:]):
            if b - a <= 1e-9:
                continue
            own_ = collections.defaultdict(float)
            for s, e, w, o in iv:
                if s <= a + 1e-9 and e >= b - 1e-9:
                    own_[o] = max(own_[o], w)
            load = sum(own_.values())
            if cap[r] > 0:
                ratio = max(ratio, load / cap[r])
            if load > cap[r] + TOL:
                errs.append(f"{r} in [{a:.1f}, {b:.1f}] holds {load:.2f} > capacity {cap[r]}")
                break
    return dict(ok=not errs, errors=errs[:20], max_ratio=ratio, holds=sum(len(v) for v in holds.values()))
