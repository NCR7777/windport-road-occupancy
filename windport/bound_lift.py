"""Upper bound W″_lift under the conservative lifting semantics (windport/lift.py). Same set of corollaries as W″
(windport/bound_dead.py, Corollaries 6, 7); only the lower bound on handover follows the new semantics:
for one trip (saddle row o, lifting position d) handover ≥ arrival + off(o, d). Direct lifting: off = time from arrival
until the vehicle body leaves the road (lift.pair_times); mixed lifting: off = min(h_d, time until the vehicle body leaves
the road) (the earlier of placement complete and lift start). With direct lifting the vehicle leaves the quay no earlier
than lift start + max(x·p, t_u) (no passage under the suspended load, and the first leg of the departure is under the
load); this time is added to c. For all other terms, the no-passage rule under the load only removes feasible schedules
and is not modelled separately. Parameters follow windport.sim.w1_port and bound3.wprime_parts (geometric quay zone Q,
return-occupancy correction) and then go through bound_dead.parts4. Chain dq is the signed min (handover lower bound − end
of the chain-top block window): ≥ 0 for direct lifting (original form of Corollary 6); with mixed lifting it can be
negative when h_d is shorter than the time for the vehicle tail to leave the chain top, and parts4 uses the extension of
Corollary 6 (σ; see the manuscript). Cradle mode (or lift_clear off) is the same as W″, except that for t_u > 0 the
cradle-turnover term and h_d of Corollary 7 become h_d + t_u + τ_g, and the right end of the handover counting interval is
tightened by ε_U (time for the delivery vehicle to leave the area under the load, egress; see the manuscript)."""
import math
from dataclasses import replace

from windport import bound as WB
from windport import bound2 as W2
from windport import bound3 as B3
from windport import bound_dead as BD
from windport import sim as WS
from windport import sim2 as S2
from windport.lift import TU, pair_times


def lift_port(cfg, D, net, p):
    """As windport.sim.w1_port, with the handover lower bound off(o, d). Cut and return trip follow occupancy_times; the cut
    occupancy up to handover and dq are computed per lifting position with the minimum off and then minimised; c and the first
    handover are computed per combination. Returns (Port, occupancy_times, dict(pairs, off) or None (cradle mode))."""
    W = D["windport"]
    S, lift = cfg["S"], ("direct" if cfg["S"] == 0 else cfg.get("lift", "cradle"))
    if lift == "cradle" or not p.get("lift_clear", True):
        P, t = WS.w1_port(cfg, D, net, p)
        tu = p.get("lift_tu", TU) * p["lift_s"] if p.get("lift_under", True) else 0.0
        if lift == "cradle" and tu > 0:
            # Lifting from a cradle closes the area under the load for [s, s + t_u]: the next vehicle delivering to the same
            # cradle arrives no earlier than s (cradle free), and its window on the under-load resource runs from entry to
            # departure and must not intersect the closure, so it enters no earlier than s + t_u and arrives no earlier than
            # s + t_u + τ_g (τ_g = lower bound on the time from entering the under-load resource to arrival). Consecutive lift
            # starts at one cradle are ≥ t_u + τ_g + h_d apart, and with all cradles full each handover in the window is
            # ≥ a + t_u + τ_g + h_d: the cradle-turnover term and h_d of Corollary 7 become h_d + t_u + τ_g (Port.hd enters
            # only these two terms)
            W = D["windport"]
            P = replace(P, hd=P.hd + tu + approach(net, p, W["storage"], W["cradles"][:max(1, S)]))
        return P, t, None
    rows, quay = W["storage"], W["cradles"][:max(1, S)]
    pt_ = pair_times(net, p, rows, quay)
    hd = 0.0 if lift == "direct" else p["hd_s"]
    off = {k: (v["off"] if lift == "direct" else min(hd, v["off"])) for k, v in pt_.items()}
    q = lambda u: dict(p, load_s=p["hp_s"], unload_s=u)
    cut = WS.w1_port(cfg, D, net, p)[1]["res"]           # cut of w1_port: parameters only grow, W″_lift ≤ W″
    t0 = WB.occupancy_times(net, q(min(off.values())), rows, quay, p["Lv"], p["B"], cut=cut)
    td = [WB.occupancy_times(net, q(min(off[o, d] for o in rows)), rows, [d], p["Lv"], p["B"], cut=t0["res"]) for d in quay]
    first = p["hp_s"] + min(v["TL"] + off[k] for k, v in pt_.items())
    c = p["hp_s"] + min(min(pt_[o, d]["TE"] for d in quay) + min(pt_[o, d]["TL"] + off[o, d] for d in quay) for o in rows)
    t = dict(t0, tl=min(x["tl"] for x in td), dq=min(x["dq"] for x in td), c=c, ce=c - first)
    L = (cfg["cal"]["crane"][0][1] - cfg["cal"]["crane"][0][0]) * 3600.0
    tu = p.get("lift_tu", TU) * p["lift_s"] if p.get("lift_under", True) else 0.0
    xr = max(p.get("release_frac", 0.0) * p["lift_s"], tu) if lift == "direct" else 0.0     # direct: leave ≥ s + max(x·p, t_u)
    P = WB.Port(L=L, p=p["lift_s"], S=S, K=cfg["K"], hp=t["hp"], hd=hd, tl=t["tl"], te=t["te"], c=c + hd + xr, ce=t["ce"] + xr, dq=t["dq"],
                Q=cfg["K"], mixed=lift == "mixed", te_occ=t["te_occ"])
    return P, t, dict(pairs=pt_, off=off)


def approach(net, p, rows, quay):
    """τ_g: time from a loaded leg entering its last road segment (the apron segment of the lifting position, inside the
    under-load resource; occupied from entry until after arrival, and for a roadside lifting position it is the terminal stop
    resource) to arrival, minimised over all (saddle row, lifting position) pairs (decision-point times of PortNet.leg,
    including the stop-and-turn on entry). 0 when the last segment is not in the under-load resource."""
    from windport.lift import arrive_fw, under_res
    cap, size = net.capacities(p)
    best = None
    for o in rows:
        so = net.stops[o]
        for d in quay:
            sd = net.stops[d]
            TL, st, uses, arr = net.leg(so["node"], sd["node"], p["v_loaded"], p["Lv"], p["B"], True, p, cap, size, sd["res"],
                                        net.demand(sd["res"], p["B"], True, p, cap))
            U = set(under_res(net, d, p["Lv"], arrive_fw(net, so["node"], sd["node"])))
            last = ("r", net.arc[net.path(so["node"], sd["node"])[-1]][3])
            tg = TL - st[arr - 1] if last in U else 0.0
            best = tg if best is None else min(best, tg)
    return max(0.0, best or 0.0)


def egress(net, p, rows, quay, targets):
    """ε_U: no-wait time after release (placement complete) for the delivery vehicle to leave the lifting position with its tail
    clear of the under-load resource, minimised over (saddle row, lifting position, departure target) (departure-leg windows as
    windport.sim.PortSim.exit_w; for a drive-in lifting position whose stand is under the load, the clearance clr for the tail to
    leave the stand is added, as dend in PortSim.leave)."""
    from windport.lift import arrive_fw, under_res
    cap, size = net.capacities(p)
    clr = (p["plat_len"] + p["long_clear"]) / p["v_empty"]
    best = None
    for d in quay:
        sd = net.stops[d]
        for o in rows:
            U = set(under_res(net, d, p["Lv"], arrive_fw(net, net.stops[o]["node"], sd["node"])))
            for tg in targets:
                _, st, uses, _ = net.leg(sd["node"], tg, p["v_empty"], p["plat_len"], p["plat_w"], False, p, cap, size, ("x",), 0.0, True)
                W = [(r, st[b] + dl) for r, _, a, b, dl in uses if b is not None]
                g = max([0.0] + [e for r, e in W if r in U] + ([0.0 if sd["res"] in {r for r, _ in W} else clr] if sd["res"] in U else []))
                best = g if best is None else min(best, g)
    return best or 0.0


def first_ends(net, p, rows, quay):
    """Per (saddle row, lifting position): (TL, {segment: end of the window of the first pass of the loaded leg}), windows as in
    bound2.windows (no-wait windows of PortNet.leg)."""
    cap, size = net.capacities(p)
    out = {}
    for o in rows:
        for d in quay:
            sd = net.stops[d]
            TL, ws = W2.windows(net, p, cap, size, net.stops[o]["node"], sd["node"], True, p["Lv"], p["B"], sd["res"],
                                net.demand(sd["res"], p["B"], True, p, cap))
            e = {}
            for r, a, b in ws:
                e.setdefault(r, b)
            out[o, d] = (TL, e)
    return out


def lift_parts(cfg):
    """Parts of W″_lift independent of the window length (format of bound_dead.terms4 / wfn4)."""
    D, net, p, *_ = S2.setup2(cfg)
    W = D["windport"]
    S, K = cfg["S"], cfg["K"]
    lift = "direct" if S == 0 else cfg.get("lift", "cradle")
    P, t, hx = lift_port(cfg, D, net, p)
    G = cfg["cal"]["crane"][0][0] * 3600.0
    rows, quay = W["storage"], W["cradles"][:max(1, S)]
    hold, unload = WS.hold_of(cfg), bool(cfg.get("n_unload"))
    routes = S2.routes_of(D, cfg, net)
    if hx is None:
        chains = W2.chain_times(net, p, rows, quay, p["Lv"], p["B"], p["hd_s"] if lift == "cradle" else 0.0, routes)
    else:                                # shift by 1e7 to pass the dq ≥ 0 filter, then signed dq (as parts4(signed=True))
        off = hx["off"]
        top = first_ends(net, p, rows, quay)       # chain-top window: first pass of the loaded leg (as chain_times)
        chains = [dict(ch, dq=min(TL + off[k] - e[ch["top"]] for k, (TL, e) in top.items()))
                  for ch in W2.chain_times(net, p, rows, quay, p["Lv"], p["B"], 1e7, routes)]
    Q = K if unload else W2.zone_Q(net, p, rows, quay, p["Lv"], p["B"], t["res"], hold, chains, K)
    bm = [min(K, math.inf if unload else W2.quay_side_Q(net, p, rows, quay, p["Lv"], p["B"], ch, hold)) for ch in chains]
    occ0 = WB.te_full(P)
    low = lambda x: x if x < occ0 - 1e-6 else occ0
    occ = low(B3.return_occ(net, p, routes, t["res"], first=True))
    tot = low(B3.return_occ(net, p, routes, t["res"]))
    te = P.te if P.te <= 0 or occ0 <= 0 else P.te * tot / occ0
    o = None if hx is None else min(v["off"] for v in hx["pairs"].values())
    w = dict(P=replace(P, Q=Q, te=te, te_occ=occ), t=t, G=G, chains=chains, bm=bm, hp=p["hp_s"], te_occ0=occ0, te0=P.te, o=o)
    w = BD.parts4(cfg, w)
    if lift == "direct" and hx is not None:        # Corollary 6(b): down trip waits + max(x·p, t_u); add to c_z, σ
        dl = max(p.get("release_frac", 0.0) * p["lift_s"], p.get("lift_tu", TU) * p["lift_s"] if p.get("lift_under", True) else 0.0)
        w["zc"] = [(cz + dl, f1, sg + dl) for cz, f1, sg in w["zc"]]
    tu = p.get("lift_tu", TU) * p["lift_s"] if p.get("lift_under", True) else 0.0
    if lift == "cradle" and tu > 0 and not cfg.get("fixed"):     # lift waits for the vehicle to clear: tighten by ε_U
        g, y = S2.idle_nodes(D)
        w["eps_u"] = egress(net, p, rows, quay, ([g] if hold else []) + [y])
    return w


def wfn_lift(cfg, w=None):
    """Closure of W″_lift(L) (L in seconds; window [G, G + L], G = crane window start of cfg). Cradle mode with t_u > 0: for every
    pile handed over and lifted aboard within the window, handover ≤ b − p − ε_U (the lift waits for the delivery vehicle to leave
    the area under the load); the interface term (counting lifts) uses L, all other terms (counting piles on cradles at the window
    start and handovers within the window) use L − ε_U."""
    w = w or lift_parts(cfg)
    e, P = w.get("eps_u", 0.0), w["P"].p
    f0 = BD.wfn4(cfg, w)
    if e <= 0:
        return f0

    def f(L):
        # L < p: no pile can be fully lifted in the window, same as W″. Other terms use max(L − ε_U, p): when L − ε_U < p there
        # is no countable handover in the window, only the piles on cradles at the window start, and every term is at least S at
        # D = 0 (bound.terms gives 0 for D < 0, so it cannot be substituted directly). serial (Π_S of Corollary 3) is truncated
        # at ⌊L/p⌋ + 1 and uses L.
        if L < P - 1e-9:
            return f0(L)
        t, r = BD.terms4(w, L), BD.terms4(w, max(L - e, P))
        return min([t["interface"], t.get("serial", math.inf)] + [v for k, v in r.items() if k not in ("prep", "interface", "serial")])
    return f
