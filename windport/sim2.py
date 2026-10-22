"""Three extensions of the port simulation (windport/sim.py, check.py and bound.py are unchanged; earlier run directories remain
reproducible).

1. Off-road waiting area: add_pocket attaches a short stub (default 30 m long, 20 m wide) to a junction; the end of the stub is
   where idle vehicles park - unlimited capacity, off the road; entering and leaving count as road occupancy (the stub section
   and the junction). With geo["pocket"] = stub length (m) the stub is attached to the south end of the single lane
   (windport.sim.yard_node); after release the vehicle drives all the way out of the single lane and stops in the waiting area.
   Shipyard maps (windport.shipyard) always have a waiting area, attached to a junction next to the storage area.
2. Dispatch rule rule:
   fcfs    first come first served (windport.sim.PortSim): at dispatch the empty run, pick-up, loaded run, set-down, crane slot
           and departure from the quay are all booked at once.
   convoy  loaded vehicles cross the bottleneck first (in convoy): dispatch and booking as in fcfs; when a load-out trip is
           dispatched, empty departures that are booked but not yet started may be postponed (the vehicle waits longer at its
           quay slot) if this lets the loaded run reach a quay slot earlier. When the quay side has room for two or more
           vehicles, upbound vehicles can thus follow closely and enter another quay slot (same-direction convoy), and the empty
           vehicles then go down in convoy. The schedule class remains that of CP-SAT (windport/cpsat.py): vehicles wait only at
           the origin, at quay slots and at idle locations.
3. Strengthened W1 (windport/bound2.py): every point also gets w1g = min{W1 (geometric quay-zone Q), empty-system preparation
   term (geometric Q), serial-cut preparation term Π_S}; points with simultaneous unloading and loading also get the combined
   upper bound of both flows joint_ub (dedicated vehicles: W1 + Theorem 3 + Theorem 4; shared fleet: plus vehicle-time
   conservation).
With geo["kind"] = "map" the derived graph is built by windport.shipyard (geo = dict(kind="map", site, cradle_mode, n_cradles)).
simulate2(cfg) returns (net, p, sim, result); the result is as windport.sim.result plus w1g, joint_ub, the rule and the idle
locations."""
import copy
import hashlib
import json
import math
import os
import tempfile
from dataclasses import replace
from pathlib import Path

from occupancy.network import EPS
from windport import archetypes as A
from windport import bound as WB
from windport import bound2 as W2
from windport import sim as WS

BIG = WS.BIG
_NETS = {}


# ---------------------------------------------------------------- off-road waiting area
def add_pocket(D, node, stub_m=30.0, w=20.0, pid="pocket"):
    """Attach a short stub from junction node to the waiting-area node pid (an endpoint, not a resource, unlimited capacity).
    The stub points in the direction farthest from the existing roads; the junction's turning permissions are extended with all
    movements between the stub and the other roads (only the permitted direction for one-way roads). Returns (new map dict,
    pid)."""
    import math as m_
    D = copy.deepcopy(D)
    x0, y0 = D["nodes"][node]["position"][:2]
    inc = [rid for rid, r in D["roads"].items() if node in (r["fromNodeId"], r["toNodeId"])]

    def heading(rid):
        r = D["roads"][rid]
        anc = r["geometry"].get("anchors") or []
        if r["fromNodeId"] == node:
            x1, y1 = (anc[0] if anc else D["nodes"][r["toNodeId"]]["position"])[:2]
        else:
            x1, y1 = (anc[-1] if anc else D["nodes"][r["fromNodeId"]]["position"])[:2]
        return m_.atan2(y1 - y0, x1 - x0)
    hs = [heading(r) for r in inc]
    best = max((k * m_.pi / 8 for k in range(16)),
               key=lambda a: (min((abs((a - h + m_.pi) % (2 * m_.pi) - m_.pi) for h in hs), default=m_.pi), -a))
    D["nodes"][pid] = dict(kind="endpoint", name=pid, position=[x0 + stub_m * m_.cos(best), y0 + stub_m * m_.sin(best), 0.0])
    rid = f"{pid}_stub"
    D["roads"][rid] = dict(fromNodeId=node, toNodeId=pid, name=rid, direction="both",
                           geometry=dict(kind="path", anchors=[], spans=[dict(kind="line")]), widthM=dict(state="known", value=float(w)))
    jid = next((j for j, J in D["junctions"].items() if J["nodeIds"] == [node]), None)
    if jid is None:
        jid = f"j_{node}"
        D["junctions"][jid] = dict(model="explicit_movements", name=jid, nodeIds=[node])

    def dir_at(r_id, incoming):
        r = D["roads"][r_id]
        d = "forward" if (r["toNodeId"] == node) == incoming else "backward"
        ok = r.get("direction", "both") in ("both", d)
        return d, ok
    for ro in inc:
        for a, b in ((ro, rid), (rid, ro)):
            din, ok1 = dir_at(a, True)
            dout, ok2 = dir_at(b, False)
            D["movements"][f"m_{node}_{a}_{b}"] = dict(allowed=ok1 and ok2, junctionId=jid, name=f"{a}→{b}",
                                                      incomingArc=dict(roadId=a, direction=din), outgoingArc=dict(roadId=b, direction=dout))
    if len(inc) == 1:                                   # node was an endpoint: only straight-on and U-turn needed
        pass
    return D, pid


# ---------------------------------------------------------------- convoy dispatch
class ConvoySim(WS.PortSim):
    """rule = convoy: loaded vehicles cross the bottleneck first (see module docstring). Dispatch and booking as in fcfs; when a
    load-out trip is dispatched, if postponing empty departures that are booked but not yet started lets this loaded run reach a
    quay slot earlier (earlier arrival tc), they are postponed: those departures are withdrawn (the vehicles stay at their quay
    slots and hold them), this loaded run is booked, and then they get the earliest departure again (not before now) in order of
    release. When every quay slot is held by a vehicle waiting to leave, postponing does not help and fcfs applies. Unloading
    tasks follow fcfs."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._cap = None
        # vehicle -> booked, not yet started departure:
        # {trip, task, sd, t2, WL, r0, clr, ad, d_sd, wait, xs, bids: {bid: [resources]}}
        self.pend = {}
        self.vdone = {}           # vehicle -> valid "available again" time (for postponed vehicles the old done event is void)
        self.bumps = 0

    def commit(self, vid, now, W):
        if self._cap is not None:
            self._cap.append((vid, [w[0] for w in W]))
        return super().commit(vid, now, W)

    def book(self, v, task, t0, r):
        self._cap = []
        super().book(v, task, t0, r)
        cap, self._cap = self._cap, None
        x = r.get("x")
        self.vdone[v.id] = t0 if r.get("dead") else r["rel"]
        if r.get("dead") or task["flow"] != "load" or not x:
            return
        so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr = r["w"]
        load = self.dur(task)[0]
        bids = {cap[-1][0]: cap[-1][1]}                                    # departure (last leg)
        bids.update({vid: rs for vid, rs in cap if rs == [sd["res"]] and vid != cap[-1][0]})    # destination quay slot
        if x["kind"] == "hold":
            bids[self.held[v.id]] = [WS.HOLD]
        self.pend[v.id] = dict(trip=self.trips[-1], task=task, sd=sd, t2=r["t2"], WL=WL, r0=r["r0"], clr=clr, ad=ad, d_sd=d_sd,
                               wait=max(0.0, r["t2"] - r["a"] - load), xs=x["xs"], bids=bids, hold=x["kind"] == "hold")

    def on_done(self, t, x):
        k = x[0]
        if self.vdone.get(k) is None or abs(t - self.vdone[k]) > 1e-6:
            return                                                          # postponed vehicle: the old done event is void
        self.vdone[k] = None
        self.pend.pop(k, None)
        super().on_done(t, x)

    def _best(self, v, task, t0):
        hows = dict(cradle=["cradle"], direct=["direct"], mixed=["cradle", "direct"])[self.lift]
        return min((self.trial(v, task, t0, sid, k, how) for k, sid in enumerate(self.quay) for how in hows), key=lambda r: r["key"])

    def plan(self, v, task, t0):
        if task["flow"] == "unload":
            return super().plan(v, task, t0)
        best0 = self._best(v, task, t0)
        cand = sorted((k for k, y in self.pend.items() if y["xs"] > t0 + EPS and k != v.id and self._free_after(y)),
                      key=lambda k: (self.pend[k]["r0"], k))
        if not cand or best0.get("dead"):
            return self.book(v, task, t0, best0)
        saved = self._bump(cand, t0)
        best1 = self._best(v, task, t0)
        if not best1.get("dead") and best1["tc"] < best0["tc"] - EPS:
            self.bumps += 1
            self.book(v, task, t0, best1)
            for k in cand:
                self._rebook(k, t0, saved["tmp"][k])
        else:
            self._restore(saved)
            self.book(v, task, t0, best0)

    def _free_after(self, y):
        """No one else has booked this vehicle's quay slot after it (otherwise postponing would overlap periods already booked by
        others)."""
        a = y["t2"] + y["ad"]
        return not any(e[1] > a + EPS and e[3] not in y["bids"] for e in self.table[y["sd"]["res"]] if e[0] >= a - EPS)

    def _bump(self, cand, t0):
        """Withdraw the departures (and holding places) of the vehicles in cand; their quay slots are held indefinitely instead
        (temporary bookings). Returns the record needed to restore."""
        out = dict(removed=[], tmp={}, held={})
        for k in cand:
            y = self.pend[k]
            for bid, rs in y["bids"].items():
                for res in set(rs):
                    keep = []
                    for e in self.table[res]:
                        (out["removed"].append((res, e)) if e[3] == bid else keep.append(e))
                    self.table[res] = keep
            if k in self.held and self.held[k] in y["bids"]:
                out["held"][k] = self.held.pop(k)
            tb = self.bid()
            self.table[y["sd"]["res"]].append((y["t2"] + y["ad"], BIG, y["d_sd"], tb))
            out["tmp"][k] = tb
        return out

    def _restore(self, saved):
        for k, tb in saved["tmp"].items():
            res = self.pend[k]["sd"]["res"]
            self.table[res] = [e for e in self.table[res] if e[3] != tb]
        for res, e in saved["removed"]:
            self.table[res].append(e)
        self.held.update(saved["held"])

    def _rebook(self, k, t0, tb):
        """Postponed vehicle k: remove the temporary booking, book the earliest departure not before t0, update the trip record
        and the "available again" time."""
        y, v = self.pend[k], self.vs[k]
        sd = y["sd"]
        self.table[sd["res"]] = [e for e in self.table[sd["res"]] if e[3] != tb]
        x = WS.PortSim.leave(self, v, sd, y["t2"], y["WL"], max(y["r0"], t0), y["clr"])
        bids = {}
        b = self.bid()
        self.commit(b, t0, [(sd["res"], y["t2"] + y["ad"], x["dend"], y["d_sd"])])
        bids[b] = [sd["res"]]
        if x["kind"] == "hold":
            hb = self.bid()
            self.held[k] = hb
            self.commit(hb, t0, [(WS.HOLD, x["rel"], BIG, 1.0)])
            bids[hb] = [WS.HOLD]
        W = self.kept([(q, x["xs"] + a, x["xs"] + b_, d) for q, a, b_, d in x["W"]])
        b = self.bid()
        self.commit(b, t0, W)
        bids[b] = [w[0] for w in W]
        self.account(W)
        y["trip"]["exit"], y["trip"]["rel"] = [x["node"], x["xs"], x["kind"]], x["rel"]
        y.update(xs=x["xs"], bids=bids, hold=x["kind"] == "hold")
        v.loc = x["node"]
        self.vdone[k] = x["rel"]
        self.push(x["rel"], "done", (k, y["task"], y["wait"]))


class CapMixin:
    """p["unload_cap"] = n: in a shared fleet at most n vehicles unload at the same time (no unloading task is dispatched to an
    (n + 1)-th vehicle; otherwise as the rule it is mixed into). Without this cap, unloading-first dispatch books the vehicles
    one by one into slots after the ramp (one vehicle at a time on the ramp, 3 h per trip), all vehicles queue before the ramp,
    and load-out supply stops."""

    def dispatch(self, t):
        cap = self.p.get("unload_cap")
        if cap is None:
            return super().dispatch(t)
        if not hasattr(self, "_unl"):
            self._unl = set()
        if self.p.get("unload_first") and self.queue:
            self.queue = __import__("collections").deque(sorted(self.queue, key=lambda x: x["flow"] != "unload"))
        while self.idle and self.queue:
            task = next((x for x in self.queue if x["flow"] != "unload" or len(self._unl) < cap), None)
            if task is None:
                return
            o = self.net.stops[task["o"]]["node"]
            k = min(self.idle, key=lambda k: (self.net.dist(self.vs[k].loc, o), k))
            self.queue.remove(task)
            self.idle.remove(k)
            task["dispatch"], task["start"] = t, self.vs[k].loc
            if task["flow"] == "unload":
                self._unl.add(task["id"])
            self._defer = None
            self.plan(self.vs[k], task, t)

    def on_done(self, t, x):
        if hasattr(self, "_unl"):
            self._unl.discard(x[1]["id"])
        super().on_done(t, x)


# ---------------------------------------------------------------- one point
def build_map(geo):
    """geo -> map dict (layout or shipyard derived graph); with a waiting area, D["windport"]["pocket"] is set."""
    if geo["kind"] == "map":
        from windport import shipyard as SY
        return SY.build(geo["site"], geo.get("cradle_mode", "on_road"), geo.get("n_cradles"))
    D = A.build(geo["kind"], **{k: v for k, v in geo.items() if k not in ("kind", "pocket")})
    if geo.get("pocket"):
        D, pid = add_pocket(D, WS.yard_node(D), float(geo["pocket"]))
        D["windport"]["pocket"] = pid
    return D


def get_net(geo, p):
    key = json.dumps([geo, p.get("section")], sort_keys=True)
    if key not in _NETS:
        D = build_map(geo)
        raw = A.dumps(D)
        d = Path(tempfile.gettempdir()) / "windport_maps"
        d.mkdir(exist_ok=True)
        sha = hashlib.sha256(raw).hexdigest()
        f = d / f"{sha[:16]}_{os.getpid()}.json"
        f.write_bytes(raw)
        net = WS.PortNet(str(f), sha, p, roles=A.ROLES)
        net.map_sha256 = sha
        _NETS[key] = (D, net)
    return _NETS[key]


def setup2(cfg):
    """As windport.sim.setup; the layout may have a waiting area or be a shipyard derived graph."""
    old = WS.get_net
    WS.get_net = get_net
    try:
        return WS.setup(cfg)
    finally:
        WS.get_net = old


def idle_nodes(D):
    """(gate, yard-side idle location): with a waiting area the idle location is the waiting-area node."""
    W = D["windport"]
    return W["gates"][-1], W.get("pocket") or WS.yard_node(D)


def simulate2(cfg):
    D, net, p, tasks, starts, quay, cal = setup2(cfg)
    lift = "direct" if cfg["S"] == 0 else cfg.get("lift", "cradle")
    Ku = cfg.get("K_u", 0)
    gate, yard = idle_nodes(D)
    cls = ConvoySim if cfg.get("rule", "fcfs") == "convoy" else WS.PortSim
    if cfg.get("p", {}).get("unload_cap") is not None:
        cls = type(cls.__name__ + "Cap", (CapMixin, cls), {})
    sim = cls(net, p, cfg["K"] + Ku, tasks, starts, quay, cal, lift, cfg.get("fixed", False), WS.ramp_res(D), record=cfg.get("record", False),
              exit=gate, yard=yard, hold=WS.hold_of(cfg), flows=["load"] * cfg["K"] + ["unload"] * Ku if Ku else None)
    sim.run()
    res = WS.result(cfg, D, net, p, sim, cal)
    res["rule"], res["idle"] = cfg.get("rule", "fcfs"), [gate, yard]
    if cfg["n_load"] and cal.get("crane"):
        res["w1g"] = bounds2(cfg, D, net, p)
    if cfg.get("n_unload") and cal.get("ramp") and cal.get("crane"):
        res["joint_ub"] = joint_bound(cfg, D, net, p, cal)
    return net, p, sim, res


def run_point2(cfg):
    return simulate2(cfg)[3]


def routes_of(D, cfg, net):
    """Return routes between two upbound trips: after release leave to the yard side (the only one when Q_h = 0), or leave to
    the gate holding place and then go from the gate to each saddle row."""
    W = D["windport"]
    gate, yard = idle_nodes(D)
    qn = [net.stops[d]["node"] for d in W["cradles"][:max(1, cfg["S"])]]
    rows = [net.stops[o]["node"] for o in W["storage"]]
    out = [[(q, yard), (yard, r)] for q in qn for r in rows]
    if WS.hold_of(cfg) != 0:
        out += [[(q, gate), (gate, r)] for q in qn for r in rows]
    return out


def bounds2(cfg, D, net, p):
    """w1g: W1 and the empty-system preparation term recomputed with the geometric quay-zone Q (Corollary 4), then the minimum
    with the serial-cut preparation term Π_S (Corollary 3)."""
    W = D["windport"]
    S, K = cfg["S"], cfg["K"]
    lift = "direct" if S == 0 else cfg.get("lift", "cradle")
    P, t = WS.w1_port(cfg, D, net, p)
    G, L = cfg["cal"]["crane"][0][0] * 3600.0, P.L
    rows, quay = W["storage"], W["cradles"][:max(1, S)]
    hold = WS.hold_of(cfg)
    unload = bool(cfg.get("n_unload"))
    chains = W2.chain_times(net, p, rows, quay, p["Lv"], p["B"], 0.0 if lift in ("direct", "mixed") else p["hd_s"], routes_of(D, cfg, net))
    Q = K if unload else W2.zone_Q(net, p, rows, quay, p["Lv"], p["B"], t["res"], hold, chains, K)
    P2 = replace(P, Q=Q)
    b2, why = WB.bound(P2, G)
    tm = WB.terms(P2, G)
    best, bch = math.inf, None
    for ch in chains:
        Qs = math.inf if unload else W2.quay_side_Q(net, p, rows, quay, p["Lv"], p["B"], ch, hold)
        pi = W2.prep_chain(ch, K, min(K, Qs), G + L, P.p, p["hp_s"])
        if pi < best:
            best, bch = pi, dict(res="|".join(r[1] for r in ch["res"]), phased=ch["down"] is not None, bmax=min(K, Qs), pi=pi)
    bound = min(b2, best)
    binding = why + (["serial"] if best <= b2 else []) if best >= b2 else ["serial"]
    return dict(bound=bound, binding="+".join(binding), Q=Q, w1q=b2, serial=None if best == math.inf else best, chain=bch,
                terms={k: (None if v == math.inf else v) for k, v in tm.items()})


def joint_bound(cfg, D, net, p, cal):
    """Combined upper bound of both flows with simultaneous unloading and loading, max(N_o + N_u): N_o <= W1 (Q = K),
    N_u <= Theorem 3 in each ramp window, every (crane window, ramp window) pair satisfies Theorem 4 (the shared cut of A1,
    cfg["joint_cut"]), and a shared fleet (K_u = 0) also obeys vehicle-time conservation (Corollary 5). Returns dict(ub,
    parts)."""
    W = D["windport"]
    S, K, Ku = cfg["S"], cfg["K"], cfg.get("K_u", 0)
    P, _ = WS.w1_port(cfg, D, net, p)
    (ao, bo), = cal["crane"]
    w1 = WB.bound(P, ao)[0]
    pu = dict(p, load_s=p["roro_s"], unload_s=p["hy_s"])
    u = WB.unload_times(net, pu, W["ramp"][0], W["storage"], p["Lv"], p["B"])
    Kun = Ku or K
    t3 = [min(WB.unload_terms(b - a, u["rho"], Kun, u["c_u"], u["tl"], u["te"]).values()) for a, b in cal["ramp"]]
    j = None
    if cfg.get("joint_cut"):
        c = ("r", cfg["joint_cut"])
        lo = WB.occupancy_times(net, dict(p, load_s=p["hp_s"], unload_s=P.hd), W["storage"], W["cradles"][:max(1, S)], p["Lv"], p["B"], cut=c)
        uu = WB.unload_times(net, pu, W["ramp"][0], W["storage"], p["Lv"], p["B"], cut=c)
        Kt = K + Ku
        j = lambda no, nu, a, b: WB.joint_gap(no, nu, S, 0, Kt, Kt, lo["tl"], uu["tl"], uu["te"], lo["te"], (ao, bo - p["lift_s"] - lo["dq"]),
                                              (a + uu["rho"], b)) >= -1e-6
    vt = None
    if Ku == 0:
        lift = "direct" if S == 0 else cfg.get("lift", "cradle")
        vt = W2.vehicle_times(net, p, W["storage"], W["cradles"][:max(1, S)], W["ramp"][0], p["Lv"], p["B"],
                              p["hd_s"] if lift == "cradle" else 0.0)
        T_end = max(bo - p["lift_s"], max(b for _, b in cal["ramp"]))
    best = (-1, 0, 0)
    for no in range(w1 + 1):
        if j is not None and not all(j(no, 0, a, b) for a, b in cal["ramp"]):
            continue
        nus = []
        for (a, b), cap3 in zip(cal["ramp"], t3):
            nu = cap3
            while nu > 0 and j is not None and not j(no, nu, a, b):
                nu -= 1
            nus.append(nu)
        nu = sum(nus)
        if vt is not None:
            while nu > 0 and not W2.vehicle_time_ok(no, nu, K, vt, T_end):
                nu -= 1
            if not W2.vehicle_time_ok(no, nu, K, vt, T_end):
                continue
        if no + nu > best[0]:
            best = (no + nu, no, nu)
    return dict(ub=best[0], no=best[1], nu=best[2], w1=w1, thm3=sum(t3), vt=vt)
