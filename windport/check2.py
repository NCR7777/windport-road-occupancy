"""Independent check of the assumptions used by the W1 strengthenings (windport/bound2.py), using only windport.check.leg
(windows rebuilt from network facts, without Net.leg or the planning code of the simulation).

From the simulation trip table (PortSim.trips: t1 empty departure, t2 loaded departure, exit = [destination node, exit
time, kind]) the passages of each vehicle over a chain of blocks are rebuilt:
  up    a loaded leg passes the whole chain (in order), interval = [enter first block, leave last block];
  down  the exit from the quay or the next empty leg passes the whole chain in reverse;
Checks:
  opp    number of pairs of opposite-direction passages whose intervals intersect (chain-cut lemma: should be 0);
  phase  after sorting by start time, the longest run of consecutive up passages (Corollary 3: should be ≤ b_max);
  zone   on the cut: a vehicle is in the quay zone from its loaded leg entering the cut until its next return entering
         the cut; the maximum number of vehicles in the quay zone at once (Corollary 4: should be ≤ Q).
Only loading trips are checked (callers do not use Corollaries 3 and 4 when there is an unloading task)."""
import collections

from windport import check as C


def _passes(net, cap, size, p, trips, starts, chain, cut):
    """Returns (passages [(start, end, direction, vehicle)], quay-zone intervals [(enter, leave, vehicle)])."""
    out, zone = [], []
    by = collections.defaultdict(list)
    for x in trips:
        if x["t1"] < 1e8:
            by[x["vid"]].append(x)
    for k, lst in by.items():
        lst.sort(key=lambda x: x["t1"])
        loc, zin = starts[k], None
        for x in lst:
            so, sd = net.stops[x["o"]], net.stops[x["d"]]
            legs = [(loc, so["node"], x["t1"], False), (so["node"], sd["node"], x["t2"], True)]
            if x.get("exit"):
                legs.append((sd["node"], x["exit"][0], x["exit"][1], False))
            for a, b, t0, loaded in legs:
                if a == b:
                    continue
                v, Lv, B = (p["v_loaded"], p["Lv"], p["B"]) if loaded else (p["v_empty"], p["plat_len"], p["plat_w"])
                W, _, _ = C.leg(net, cap, size, p, a, b, v, Lv, B, loaded, not loaded)
                ws = {r: (t0 + s, t0 + e) for r, _, s, e in W}
                if chain and all(("r", c) in ws for c in chain):
                    st = [ws[("r", c)][0] for c in chain]
                    up = st == sorted(st) and (len(chain) == 1 or st[0] < st[-1])
                    out.append((min(s for s, _ in (ws[("r", c)] for c in chain)), max(e for _, e in (ws[("r", c)] for c in chain)),
                                "up" if loaded else "down", k))
                if cut in ws:
                    if loaded and x["flow"] == "load":
                        zin = ws[cut][0]
                    elif not loaded and zin is not None:
                        zone.append((zin, ws[cut][0], k))
                        zin = None
            loc = x["exit"][0] if x.get("exit") else sd["node"]
        if zin is not None:
            zone.append((zin, 1e18, k))
    return out, zone


def hyp(net, p, trips, starts, chain, cut):
    """chain: road ids of the chain (in up order); cut: cut resource. Returns dict(opp, phase, zone)."""
    cap, size = net.capacities(p)
    ps, zone = _passes(net, cap, size, p, trips, starts, chain or [], cut)
    ups = [x for x in ps if x[2] == "up"]
    dns = [x for x in ps if x[2] == "down"]
    opp = sum(1 for a in ups for b in dns if a[0] < b[1] - 1e-6 and b[0] < a[1] - 1e-6)
    phase, run = 0, 0
    for s, e, d, k in sorted(ps):
        run = run + 1 if d == "up" else 0
        phase = max(phase, run)
    # At equal times leave before enter (half-open intervals; tolerance as in the checker)
    ev = sorted([(a + C.TOL, 1) for a, b, k in zone] + [(b, -1) for a, b, k in zone])
    cur = mz = 0
    for t, d in sorted(ev, key=lambda x: (x[0], x[1])):
        cur += d
        mz = max(mz, cur)
    return dict(opp=opp, phase=phase if chain else 0, zone=mz)
