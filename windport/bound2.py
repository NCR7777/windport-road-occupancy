"""Three strengthenings of W1 (statements and proofs in the manuscript; windport/bound.py is unchanged).

1. Chain cut (Corollary 3): when a single-lane section is split by side-road junctions into several exclusive blocks with no
   passing places between them, then on fixed routes
   · two passages in opposite directions are mutually exclusive over the whole chain (their chain time intervals are disjoint);
   · passages in the same direction are first-in-first-out on every block: the later one enters block i no earlier than the
     earlier one leaves block i;
   so loaded up-trips queue in "phases": a phase of b trips occupies the whole chain for at least
   Φ_l(b) = max_i [F_i + R_i + (b − 1)·h_i] (F_i, R_i: lower bounds on the time from entering the chain to entering block i,
   and from entering block i to leaving the chain; h_i: lower bound on the occupation of block i), and between two phases
   there is at least one phase of empty down-trips (opposite directions exclude each other).
   Length of an up phase: b ≤ b_max = min(K, Q_s), Q_s = number of vehicles the quay stops can hold at once, under the
   conditions (_guard, exit_first) that (i) there is no gate holding place (Q_h = 0); (ii) in every return pattern, the
   leg leaving the quay passes the whole chain in reverse (idle vehicles wait on the yard side of the chain); (iii) there is
   a "threshold" beyond the chain top: after the top block each loaded leg passes only junctions and one road g, g is
   exclusive for a loaded and an empty vehicle, and the first road of the leg leaving the quay is also g. Then the last
   vehicle of an up phase still holds g when it leaves the chain top, a vehicle ahead must pass g before going down, and the
   b vehicles of the phase stand on the quay stops at the same time. Without the conditions b_max = K. Without a threshold
   the statement fails: in the discrete two-block chain model an arriving and a departing vehicle can swap places on the
   quay-side boundary at the same instant, so with Qs = 1 a phase can hold 2 vehicles (the QT state of
   windport/exact_chain.py is the vehicle tail added to model the threshold).
   Preparation term Π_S from an empty system: the largest m with hp + offset of the first chain entry + f(m) ≤ b − p − dq_c,
   f(m) = min_r [r up phases + (r − 1) down phases], with at least max(r − 1, m − K) down-trips in total (one vehicle needs
   a down-trip between two up-trips), split evenly over the phases (Φ is convex in b).
   When not all returns pass the chain (A2 loop, A3 two gates) there is no phase constraint and f(m) = Φ_l(m): only the
   same-direction block spacing remains.
2. Geometric quay-zone capacity Q (Corollary 4): when the cut is the road holding the quay stops (a single roadside quay
   front), Q = number of loaded vehicles that road can hold at once (usually 1); when the cut is a block of a chain and
   conditions (i)-(iii) of Corollary 3 hold, Q = number of vehicles the quay stops can hold at once + number of blocks
   from the cut to the chain top; not used when there is an unloading task (Q = K).
3. Vehicle-time conservation for loading and unloading sharing one fleet (Corollary 5): with all vehicles starting empty on
   the yard side, up to T_end (the later of the last loading handover b_o − p and the end of the last unloading ramp
   window) the busy time of each vehicle is at most T_end plus the part of its last unloading trip after the ramp
   operation:
     N_o·w_o + N_u·w_u + e_y·(N_o − N_u − K)⁺ + e_q·(N_u − N_o)⁺ ≤ K·T_end + min(K, N_u)·post_u.
   w_o = pickup + loaded + placement (to the handover; placement not counted for direct and mixed lifting), w_u = empty
   on the ramp + on-vessel operation + loaded to the saddle + placement, post_u = w_u − lower bound of (empty on the ramp +
   on-vessel operation + loaded leaving the ramp); e_y = empty from quay stop → yard, e_q = empty from yard → ramp road;
   between loading and unloading (quay → ramp) 0 is used (lower bound).
All parameters come from the wait-free windows of the road-occupancy model (Net.leg, PortNet including turning at stops),
minimised over all (origin, destination) pairs; looser values keep the bounds valid."""
import math

EPS = 1e-9
INF = math.inf


def width(cap, res, b, loaded, p):
    """As exact.check.width: road min(B + c, C), loaded vehicles exclusive at junctions, stop / cradle 1."""
    C = cap[res]
    if res[0] in ("b", "c"):
        return 1.0
    if loaded and res[0] == "n":
        return C
    return min(C, b + p["lat_clear"])


def windows(net, p, cap, size, src, dst, loaded, Lv, B, end_res=None, end_d=0.0, start_node=False):
    """(travel time, [(resource, relative start, relative end)] in order of entry) of one leg; only resources with a window
    (the destination stop resource is excluded)."""
    v = p["v_loaded"] if loaded else p["v_empty"]
    T, st, uses, _ = net.leg(src, dst, v, Lv, B, loaded, p, cap, size, end_res if end_res else ("x",), end_d, start_node)
    return T, sorted(((res, st[a], st[r] + dl) for res, d, a, r, dl in uses if r is not None), key=lambda w: (w[1], w[2]))


def excl(cap, res, p, B, b0, pair):
    """Two vehicles do not fit on resource res: pair = "le" (loaded and empty), "ll" (two loaded), "ee" (two empty)."""
    wl, we = width(cap, res, B, True, p), width(cap, res, b0, False, p)
    a, b = dict(le=(wl, we), ll=(wl, wl), ee=(we, we))[pair]
    return a + b > cap[res] + EPS


def span(b, st):
    """Lower bound on the time a same-direction phase of b trips occupies the whole chain,
    Φ(b) = max_i [F_i + R_i + (b − 1)·h_i] (st = (F, R, h))."""
    F, R, h = st
    return max(F[i] + R[i] + (b - 1) * h[i] for i in range(len(F))) if b > 0 else 0.0


def f_min(m, K, bmax, up, down):
    """Lower bound on the total chain occupation of m up-trips (from an empty system, at least one down phase between up
    phases). down = None: returns do not pass the chain, only same-direction spacing applies."""
    if m <= 0:
        return 0.0
    if down is None:
        return span(m, up)
    best = INF
    for r in range(max(1, math.ceil(m / bmax - EPS)), m + 1):
        q, e = divmod(m, r)
        t = e * span(q + 1, up) + (r - e) * span(q, up)
        if r > 1:
            Dn = max(r - 1, m - K)
            q2, e2 = divmod(Dn, r - 1)
            t += e2 * span(q2 + 1, down) + (r - 1 - e2) * span(q2, down)
        best = min(best, t)
    return best


def prep_chain(ch, K, bmax, b_end, p_lift, hp):
    """Corollary 3: upper bound Π_S on the units lifted aboard within the window up to b_end, from an empty system
    (ch = a result of chain_times)."""
    D = b_end - p_lift - ch["dq"] - hp - ch["start0"]
    m = 0
    while f_min(m + 1, K, bmax, ch["up"], ch["down"]) <= D + EPS:
        m += 1
        if m > 10 ** 4:
            raise AssertionError("chain-cut term is unbounded: zero occupation on the chain?")
    return m


def _runs(rows, cand):
    """Maximal runs of candidate roads that are adjacent in every row (road sequence of a loaded leg), in the order of the
    first row."""
    pos = [{w[0]: i for i, w in enumerate(r)} for r in rows]
    order = [w[0] for w in rows[0] if w[0] in cand]
    out = []
    for res in order:
        if out and all(P[res] == P[out[-1][-1]] + 1 for P in pos):
            out[-1].append(res)
        else:
            out.append([res])
    return out


def chain_times(net, p, stops_o, quay, Lv, B, unload_s, routes):
    """Chain-cut parameters from the road-occupancy model: returns [dict(res, up, down, dq, start0, top)] for each candidate
    chain (every maximal run and all its contiguous sub-runs); the Π_S of any chain is valid, the minimum is taken.
    stops_o: saddle-row stops; quay: quay stops; unload_s: placement time before the handover (0 for direct and mixed
    lifting); routes: the return patterns between two up-trips, each a list of empty legs [(start node, end node), ...]
    (after release, leave to the yard side; or leave to the gate holding place, then from the gate to a saddle row). If in
    every pattern exactly one leg passes the whole chain in reverse order and the other legs do not touch it, down is the
    (F, R, h) of the down direction; otherwise None (only same-direction spacing is used).
    Only roads that can hold neither a loaded plus an empty vehicle nor two loaded vehicles are used; h = 0 on blocks where
    same-direction empty vehicles fit side by side. Each row's window on the top block must end before the handover
    (dq ≥ 0)."""
    cap, size = net.capacities(p)
    rows, hands, full = [], [], []
    for o in stops_o:
        for d in quay:
            so, sd = net.stops[o], net.stops[d]
            dsd = net.demand(sd["res"], B, True, p, cap)
            TL, st, uses, _ = net.leg(so["node"], sd["node"], p["v_loaded"], Lv, B, True, p, cap, size, sd["res"], dsd)
            W = sorted(((res, st[a], st[r] + dl) for res, d, a, r, dl in uses if r is not None), key=lambda w: (w[1], w[2]))
            ad = next(st[a] for res, d, a, r, dl in uses if r is None)          # destination quay-stop reservation starts here (as in Sim.windows)
            rows.append([w for w in W if w[0][0] == "r"])
            full.append(([w[0] for w in W], sd["res"], {w[0]: (w[1], w[2]) for w in W}, ad))
            hands.append(TL + unload_s)
    exits = [[w for w in windows(net, p, cap, size, s, d, False, p["plat_len"], p["plat_w"], start_node=True)[1] if w[0][0] == "r"]
             for s, d in {route[0] for route in routes} if s != d]
    b0 = p["plat_w"]
    cand = {w[0] for w in rows[0]}
    for r in rows[1:]:
        cand &= {w[0] for w in r}
    cand = {res for res in cand if excl(cap, res, p, B, b0, "le") and excl(cap, res, p, B, b0, "ll")}
    rws = [[[w for w in windows(net, p, cap, size, s, d, False, p["plat_len"], b0, start_node=True)[1] if w[0][0] == "r"] if s != d else []
            for s, d in route] for route in routes]
    out = []
    for big in _runs(rows, cand):
        for i in range(len(big)):
            for j in range(i + 1, len(big) + 1):
                run = big[i:j]
                ws = [[next(w for w in r if w[0] == res) for res in run] for r in rows]
                dq = min(h - w[-1][2] for h, w in zip(hands, ws))
                n = len(run)
                mono = all(w[k + 1][1] < w[k][2] - EPS and w[k][2] <= w[k + 1][2] + EPS for w in ws for k in range(n - 1))
                if dq < -EPS or not mono:
                    continue
                up = ([min(w[k][1] - w[0][1] for w in ws) for k in range(n)], [min(w[-1][2] - w[k][1] for w in ws) for k in range(n)],
                      [min(w[k][2] - w[k][1] for w in ws) for k in range(n)])
                down, dws, first = None, [], True
                for legs in rws:
                    hit = [q for q, leg in enumerate(legs) if any(w[0] in run for w in leg)]
                    if len(hit) != 1 or not _has_rev(legs[hit[0]], run):
                        dws = None
                        break
                    first &= hit[0] == 0
                    dws.append([next(w for w in legs[hit[0]] if w[0] == res) for res in run[::-1]])
                if dws and not all(w[k + 1][1] < w[k][2] - EPS and w[k][2] <= w[k + 1][2] + EPS for w in dws for k in range(n - 1)):
                    dws = None                          # down windows must also satisfy (W)
                if dws:
                    hd = [min(w[k][2] - w[k][1] for w in dws) if excl(cap, run[n - 1 - k], p, B, b0, "ee") else 0.0 for k in range(n)]
                    down = ([min(w[k][1] - w[0][1] for w in dws) for k in range(n)], [min(w[-1][2] - w[k][1] for w in dws) for k in range(n)], hd)
                out.append(dict(res=run, up=up, down=down, dq=max(0.0, dq), start0=min(w[0][1] for w in ws), top=run[-1],
                                exit_first=bool(dws) and first, guard=_guard(cap, p, B, run[-1], full, exits)))
    return out


def _guard(cap, p, B, top, full, exits):
    """The "threshold" beyond the chain top (condition of Corollaries 3 and 4): after the top block each loaded leg passes
    only junctions and one road g (for roadside quay stops g is the road holding the stop), g is exclusive for a loaded and
    an empty vehicle, and the first road of every leg leaving the quay is g. Then the last vehicle of an up phase still
    holds g when it leaves the chain top, and a vehicle ahead must pass g before going down, so it can only stand on a quay
    stop or a gate holding place; there is no empty vehicle on the road on the quay side. Two model facts used by the proof
    are also checked: the quay-stop reservation starts no later than entering g, and g is still held when the vehicle leaves
    the chain top (the window of g covers the end of the top window). For roadside quay stops g is the stop itself, and both
    hold automatically because the reservation runs from entering g until after the handover (dq ≥ 0 is checked)."""
    gs = set()
    for names, sres, wd, ad in full:
        if top not in names:
            return False
        after = names[names.index(top) + 1:]
        roads = {r for r in after if r[0] == "r"} | ({sres} if sres[0] == "r" else set())
        if len(roads) != 1:
            return False
        gs |= roads
    if len(gs) != 1:
        return False
    g = next(iter(gs))
    for names, sres, wd, ad in full:
        if g != sres:
            sg, eg = wd[g]
            et = wd[top][1]
            if not (ad <= sg + EPS and sg < et - EPS and et <= eg + EPS):
                return False
    return excl(cap, g, p, B, p["plat_w"], "le") and bool(exits) and all(e and e[0][0] == g for e in exits)


def _has_rev(r, run):
    names = [w[0] for w in r]
    idx = [names.index(res) if res in names else -1 for res in run[::-1]]
    return all(i >= 0 for i in idx) and all(b == a + 1 for a, b in zip(idx, idx[1:]))


def quay_stops_cap(net, p, quay, B):
    """Number of vehicles the quay stops can hold at once: sum over the quay stop resources (bay for pull-in, whole road for
    roadside) of the loaded vehicles each can hold (a resource shared by several quay stops counts once)."""
    cap, _ = net.capacities(p)
    res = {net.stops[d]["res"] for d in quay}
    return sum(1 if r[0] == "b" else int(cap[r] // net.demand(r, B, True, p, cap) + EPS) for r in res)


def quay_side_Q(net, p, stops_o, quay, Lv, B, ch, hold):
    """Q_s of Corollary 3: number of vehicles that can stand beyond the top block of chain ch (quay side) at once = number
    of vehicles the quay stops can hold. Given only when there is no gate holding place (Q_h = 0) and the resources from the
    chain top to the quay stops are exclusive for a loaded and an empty vehicle (at the end of an up phase there is no empty
    vehicle on the road on the quay side); otherwise INF (b_max = K)."""
    if hold != 0 or not ch.get("exit_first") or not ch.get("guard"):
        return INF
    return quay_stops_cap(net, p, quay, B)


def zone_Q(net, p, stops_o, quay, Lv, B, cut, hold, chains, K):
    """Corollary 4: at most Q vehicles in the quay zone beyond cut at once (returns K if the conditions fail).
    cut is the quay stop resource (a single roadside quay front): every vehicle in the quay zone occupies this road at
    loaded width, so Q = number of loaded vehicles it can hold; a gate holding place lies on the yard side of the cut and
    does not count. cut is a block of a chain and there is no gate holding place: Q = number of vehicles the quay stops can
    hold + number of blocks from cut to the chain top (the resources from the chain top to the quay stops are exclusive for
    a loaded and an empty vehicle)."""
    qres = {net.stops[d]["res"] for d in quay}
    if cut in qres:
        return min(K, quay_stops_cap(net, p, quay, B)) if len(qres) == 1 and cut[0] == "r" else K
    if hold != 0:
        return K
    for ch in chains:
        if cut in ch["res"] and ch.get("exit_first") and ch.get("guard"):
            return min(K, quay_stops_cap(net, p, quay, B) + len(ch["res"]) - ch["res"].index(cut))
    return K


def vehicle_time_lhs(No, Nu, K, vt):
    """Part of left − right of Corollary 5 that does not depend on T_end: returns (left side, deductible tail of the last
    unloading trip). vt = dict(w_o, w_u, post_u, e_y, e_q)."""
    lhs = No * vt["w_o"] + Nu * vt["w_u"] + vt["e_y"] * max(0, No - Nu - K) + vt["e_q"] * max(0, Nu - No)
    return lhs, min(K, Nu) * vt["post_u"]


def vehicle_time_ok(No, Nu, K, vt, T_end):
    lhs, post = vehicle_time_lhs(No, Nu, K, vt)
    return lhs <= K * T_end + post + 1e-6


def vehicle_times(net, p, stops_o, quay, ramp_stop, Lv, B, hd):
    """Parameters of Corollary 5 (each minimised): w_o, w_u, post_u (part of unloading after the ramp operation), e_y (empty
    from quay stop → saddle row), e_q (empty from saddle row → entering the ramp road).
    hd: placement time before the handover (hd_s in cradle mode; 0 for direct and mixed lifting, which hand over on
    arrival)."""
    cap, size = net.capacities(p)
    b0 = p["plat_w"]
    w_o, e_y = INF, INF
    for o in stops_o:
        so = net.stops[o]
        for d in quay:
            sd = net.stops[d]
            TL = net.leg(so["node"], sd["node"], p["v_loaded"], Lv, B, True, p, cap, size, sd["res"], net.demand(sd["res"], B, True, p, cap))[0]
            TE = net.leg(sd["node"], so["node"], p["v_empty"], p["plat_len"], b0, False, p, cap, size, so["res"], 0.0, True)[0]
            w_o, e_y = min(w_o, p["hp_s"] + TL + hd), min(e_y, TE)
    sr = net.stops[ramp_stop]
    w_u = pre_u = e_q = INF
    for o in stops_o:
        so = net.stops[o]
        TL, stL, uL, _ = net.leg(sr["node"], so["node"], p["v_loaded"], Lv, B, True, p, cap, size, so["res"], net.demand(so["res"], B, True, p, cap))
        TE, stE, uE, arr = net.leg(so["node"], sr["node"], p["v_empty"], p["plat_len"], b0, False, p, cap, size, sr["res"], 0.0, True)
        ramp_road = next(r for r, d, a, rr, dl in uL if a == 0 and r[0] == "r")
        off = next(stL[rr] + dl for r, d, a, rr, dl in uL if r == ramp_road)          # loaded tail leaves the ramp road (F_ramp)
        up = TE - stE[arr - 1]                                                          # empty travel on the ramp road
        w_u = min(w_u, up + p["roro_s"] + TL + p["hy_s"])
        pre_u = min(pre_u, up + p["roro_s"] + off)
        e_q = min(e_q, stE[arr - 1])
    # If a vehicle's last trip is unloading, the left side counts w_u, but until completion (F_ramp) it used at least only
    # pre_u; the difference w_u − pre_u is added to the right side
    return dict(w_o=w_o, w_u=w_u, post_u=max(0.0, w_u - pre_u), e_y=e_y, e_q=e_q)
