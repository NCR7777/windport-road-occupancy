"""The spatial additions: four spatial and shared-use semantics (windport/sim.py, sim2.py, sim3.py, shipyard.py and archetypes.py
are not changed; the existing run directories remain reproducible).

1. Crane reach: with p["reach"] = S_r, quay positions k >= S_r (from the S_r-th counted from the gate onwards) are outside the reach
   of the crane at one ship position, and each pile lifted from there (cradle or vehicle) occupies the crane for p + t_sh
   (p["shift_s"], moving the ship position or re-handling); k < S_r keep p. Used only with first-come-first-served and release time
   x = 0 (asserted on entry).
   Key for choosing the quay position: p["reach_key"] = "start" (default, as PortSim: earliest lift start) or "finish" (earliest lift
   finish, far cradles count t_sh); with p["far_prestage"] = True the far cradles are only used for pre-staging before the window:
   when the dispatch time is not earlier than the start of the first crane opening, only near quay positions are chosen.
2. Cradle rows (Rønne-style): build_side attaches to the A1 quay front, every pitch_m, a dead-end spur bay_m long with one cradle at
   its end (roadside stop; the spur serves only this cradle), all within crane reach (S_r = S); a loaded vehicle enters the spur
   sideways from the front, with stops and sweeps counted by the turning rules of the road-occupancy model (sweeping both front
   arms).
   Passing place: build_pass replaces a stretch pp_m in the middle of the single lane by a two-lane stretch pp_w wide. Both are
   variants of A1 (the port-type record keeps kind "A1" and also records layout).
3. Alternative turning manoeuvres: p["turn_extra"] = {key: seconds} - on these turns (turn angle >= turn_deg, where the sweep hits an
   obstacle and the vehicle cannot turn on the spot) a loaded vehicle uses an alternative manoeuvre, and the given seconds are added
   to the stopping time δ. The key is "node|from_road|to_road" (only this direction of turn) or "node" (all turns at the node);
   junction occupation, release of the approach road and trip time are all shifted accordingly (written as in
   windport.sim.PortNet). TurnNet differs from PortNet only when turn_extra is given.
4. Shared road for block transport (the shared cut of Theorem 4): with cfg["reserve"] = dict(f, T_h), on one shared segment
   (reserve_road: of the segments that every loading route passes, that a loaded vehicle holds alone, and that are not on the quay
   front or a yard stop, the one with the longest loaded occupation) the first f·T of every period T is reserved for block
   transport ([iT, iT + f·T), held at full capacity, not counted in the occupation statistics).
5. Relaxed storage area: with geo = dict(kind="map", site, storage="multi") SITES_MULTI is used (chosen and checked by
   experiments/windport_sites_multi.py with the area threshold "holds three voyages of 30 piles"); otherwise as the shipyard-derived
   maps of the E4-E7 batches.
get_net4 also puts the built network into the network cache of windport.sim2 (same key), so the functions of windport.sim2, bound2
and bound3 work as usual; setup4 builds the network first and then calls windport.sim2.setup2. simulate4(cfg) returns
(net, p, sim, result); the result is that of windport.sim2.simulate2 plus w4 (windport/bound4.py).
Independent check in windport/check4.py."""
import copy
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from occupancy.network import EPS, Net
from windport import archetypes as A
from windport import shipyard as SY
from windport import sim as WS
from windport import sim2 as S2

SITES_MULTI = dict(
    okpo=dict(SY.SITES["okpo"], storage_zone="zone_trace_001", near="node_trace_055"),
    yantai=dict(SY.SITES["yantai"], storage_zone="zone_trace_030", near="node_trace_082"),
)


# ---------------------------------------------------------------- port-type variants
def _remap(D):
    """Built A1 map dict -> archetypes._Map (after changing the network, finish regenerates junctions and turns)."""
    assert D["windport"]["kind"] == "A1", "only A1 can be rewritten"
    m = A._Map()
    m.nodes, m.roads = copy.deepcopy(D["nodes"]), copy.deepcopy(D["roads"])
    m.oneway = {r for r, x in D["roads"].items() if x["direction"] == "forward"}
    m.access, m.facilities, m.zones = copy.deepcopy(D["accessPoints"]), copy.deepcopy(D["facilities"]), copy.deepcopy(D["zones"])
    return m


def build_side(n_cradles=6, pitch_m=20.0, bay_m=40.0, **kw):
    """Cradle rows: the front of A1 (no ramp) becomes a chain of segments gate -> front nodes 0 ... n−1 (from gate_cradle_m east of
    the gate, every pitch_m); each front node gets a dead-end spur bay_m long to the north, and cradle k is at the end of spur k
    (roadside stop, 10 m long)."""
    D0 = A.build("A1", **dict(kw, n_cradles=1, cradle_mode="on_road", ramp_at=None))
    m = _remap(D0)
    q = D0["windport"]["params"]
    Dm, gate = q["dist_m"], D0["windport"]["gates"][0]
    del m.roads["apron_0"], m.nodes["apron_E"]
    x0 = D0["windport"].get("geometry", A.GEOMETRIES["legacy40"])["gate_cradle_m"]      # distance of the first cradle position from the gate (a parameter)
    xs = [x0 + k * pitch_m for k in range(int(n_cradles))]
    nodes = [gate] + [m.node(f"apron_{k}", x, Dm) for k, x in enumerate(xs)]
    apron = m.chain("apron", nodes, q["apron_w"])
    bays = []
    for k, x in enumerate(xs):
        e = m.node(f"bay_{k}_E", x, Dm + bay_m, "endpoint")
        bays.append(m.road(f"bay_{k}", nodes[k + 1], e, q["apron_w"]))
    m.zones["z_cradle"]["extensions"][A.RS]["frontage"] = [dict(roadId=b, sStartM=bay_m - 10.0, sEndM=bay_m) for b in bays]
    meta = copy.deepcopy(D0["windport"])
    meta.update(layout="side", params=dict(q, n_cradles=int(n_cradles), pitch_m=pitch_m, bay_m=bay_m), apron=apron + bays,
                cradles=[f"z_cradle#{k}" for k in range(int(n_cradles))])
    return m.finish(meta)


def build_pass(pp_m=150.0, pp_w=16.0, **kw):
    """Passing place: a stretch pp_m in the middle of the A1 single lane (around the midpoint of its full length) becomes pp_w wide;
    if the midpoint falls on a junction, the passing place starts from the junction northwards."""
    D0 = A.build("A1", **kw)
    m = _remap(D0)
    W = D0["windport"]
    y0 = W["params"]["dist_m"] - W["params"]["corridor_m"]
    mid = y0 + W["params"]["corridor_m"] / 2
    ys = lambda r: sorted(m.nodes[m.roads[r][e]]["position"][1] for e in ("fromNodeId", "toNodeId"))
    rid = next(r for r in W["corridor"] if ys(r)[0] <= mid < ys(r)[1])
    lo, hi = ys(rid)
    a, b = max(lo, mid - pp_m / 2), min(hi, max(lo, mid - pp_m / 2) + pp_m)
    r = m.roads.pop(rid)
    w = r["widthM"]["value"]
    pts = [r["fromNodeId"]]
    if a > lo + EPS:
        pts.append(m.node(f"{rid}_pa", 0.0, a))
    if b < hi - EPS:
        pts.append(m.node(f"{rid}_pb", 0.0, b))
    pts.append(r["toNodeId"])
    new, lane = [], []
    for k, (u, v) in enumerate(zip(pts, pts[1:])):
        yu, yv = m.nodes[u]["position"][1], m.nodes[v]["position"][1]
        wide = abs(min(yu, yv) - a) < EPS and abs(max(yu, yv) - b) < EPS
        new.append(m.road(f"{rid}_p{k}", u, v, pp_w if wide else w))
        if not wide:
            lane.append(new[-1])
    meta = copy.deepcopy(W)
    i = meta["corridor"].index(rid)
    meta["corridor"] = meta["corridor"][:i] + lane + meta["corridor"][i + 1:]
    meta.update(layout="pass", params=dict(W["params"], pp_m=pp_m, pp_w=pp_w), passing=[x for x in new if x not in lane])
    return m.finish(meta)


def build_map4(geo):
    """geo -> map dict: kind = "map" with storage = "multi" uses SITES_MULTI; "A1side" / "A1pass" are the two variants above;
    otherwise as windport.sim2.build_map."""
    k = geo["kind"]
    rest = {x: v for x, v in geo.items() if x not in ("kind", "pocket", "storage")}
    if k == "map":
        S = SITES_MULTI[geo["site"]] if geo.get("storage") == "multi" else None
        return SY.build(geo["site"], geo.get("cradle_mode", "on_road"), geo.get("n_cradles"), S=S)
    if k == "A1side":
        D = build_side(**rest)
    elif k == "A1pass":
        D = build_pass(**rest)
    else:
        return S2.build_map(geo)
    if geo.get("pocket"):
        D, pid = S2.add_pocket(D, WS.yard_node(D), float(geo["pocket"]))
        D["windport"]["pocket"] = pid
    return D


# ---------------------------------------------------------------- network: alternative turning manoeuvres
def turn_delays4(net, path, Lv, v, p):
    """As windport.sim.turn_delays, and on the turns in p["turn_extra"] (only at decision points where the vehicle already stops to
    turn) adds the seconds of the alternative manoeuvre."""
    runs, dl = WS.turn_delays(net, path, Lv, v, p)
    ex = p.get("turn_extra") or {}
    for i in range(1, len(runs)):
        if dl[i]:
            n = net.arc[runs[i][2]][0]
            dl[i] += float(ex.get(f"{n}|{runs[i - 1][0]}|{runs[i][0]}", ex.get(n, 0.0)))
    return runs, dl


class TurnNet(WS.PortNet):
    def leg(self, src, dst, v, Lv, b, loaded, p, cap, size, end_res, end_d, start_node=False):
        if not p.get("turn_extra"):
            return super().leg(src, dst, v, Lv, b, loaded, p, cap, size, end_res, end_d, start_node)
        T, st, uses, arr = Net.leg(self, src, dst, v, Lv, b, loaded, p, cap, size, end_res, end_d, start_node)
        if not loaded or src == dst or p.get("sweep_steer_s") is None:
            return T, st, uses, arr
        runs, dl = turn_delays4(self, self.path(src, dst), Lv, v, p)
        if not any(dl):
            return T, st, uses, arr
        m = len(runs)
        cum = [sum(dl[1:j]) for j in range(arr + 1)]
        st2 = [x + c for x, c in zip(st, cum)]
        out = []
        for res, d, a, r, x in uses:
            if res[0] == "n" and a == r and 0 < a < m and res[1] == self.arc[runs[a][2]][0] and dl[a]:
                x = (size[res[1]] + Lv + p["long_clear"]) / v + dl[a]
                out += [(("r", q), cap[("r", q)], a, a, x) for q in self.incident[res[1]] if q not in (runs[a - 1][0], runs[a][0])]
            elif res[0] == "r" and r is not None and 0 < r < m and dl[r]:
                x += dl[r]
            out.append((res, d, a, r, x))
        return T + sum(dl), st2, out, arr


def get_net4(geo, p):
    """geo -> (D, TurnNet); stored in the windport.sim2 cache (same key as windport.sim2.get_net); rebuilt if the cached entry
    under that key is not a TurnNet."""
    key = json.dumps([geo, p.get("section")], sort_keys=True)
    hit = S2._NETS.get(key)
    if hit is None or not isinstance(hit[1], TurnNet):
        D = build_map4(geo)
        raw = A.dumps(D)
        d = Path(tempfile.gettempdir()) / "windport_maps"
        d.mkdir(exist_ok=True)
        sha = hashlib.sha256(raw).hexdigest()
        f = d / f"{sha[:16]}_{os.getpid()}.json"
        f.write_bytes(raw)
        net = TurnNet(str(f), sha, p, roles=A.ROLES)
        net.map_sha256 = sha
        S2._NETS[key] = (D, net)
    return S2._NETS[key]


def setup4(cfg):
    get_net4(cfg["geo"], WS.params(cfg))
    out = S2.setup2(cfg)
    assert isinstance(out[1], TurnNet)
    return out


# ---------------------------------------------------------------- shared segment
def reserve_road(D, net, p, cfg):
    """Segment shared with block transport: of the segments that every (cradle row, cradle) loading route passes, that cannot hold
    two loaded vehicles, and that are not on the quay front (apron in the port-type record) or a stop, the one with the longest
    loaded occupation (t_ℓ from windport.bound.occupancy_times with cut set to that segment). Returns (resource, t_ℓ)."""
    from windport import bound as WB
    W = D["windport"]
    rows, quay = W["storage"], W["cradles"][:max(1, cfg["S"])]
    cap, size = net.capacities(p)
    common = None
    for o in rows:
        for d in quay:
            so, sd = net.stops[o], net.stops[d]
            rs = {("r", net.arc[a][3]) for a in net.path(so["node"], sd["node"])}
            common = rs if common is None else common & rs
    skip = {("r", r) for r in W.get("apron") or []} | {net.stops[s]["res"] for s in rows + quay}
    lift = "direct" if cfg["S"] == 0 else cfg.get("lift", "cradle")
    pt = dict(p, load_s=p["hp_s"], unload_s=0.0 if lift in ("direct", "mixed") else p["hd_s"])
    best = None
    for c in sorted(common - skip, key=str):
        try:
            t = WB.occupancy_times(net, pt, rows, quay, p["Lv"], p["B"], cut=c)
        except AssertionError:
            continue
        if best is None or t["tl"] > best[1] + EPS:
            best = (c, t["tl"])
    assert best, "no segment can be shared"
    return best


def closures(T, f, H):
    """[iT, iT + fT), i = 0, 1, ..., until H is covered."""
    out, i = [], 0
    while i * T < H + T:
        out.append((i * T, i * T + f * T))
        i += 1
    return out


# ---------------------------------------------------------------- simulation
class ReachMixin:
    """Lifts at quay positions k >= p["reach"] occupy the crane for lift_s + shift_s per pile: p["lift_s"] is changed temporarily
    during trial and book of this trip (and restored afterwards)."""

    def _lift(self, k):
        r = self.p.get("reach")
        return self._p0 + (self.p["shift_s"] if r is not None and k is not None and k >= r else 0.0)

    def trial(self, v, task, t0, sid, k, how):
        if task["flow"] != "load":
            return super().trial(v, task, t0, sid, k, how)
        self.p["lift_s"] = self._lift(k)
        try:
            return super().trial(v, task, t0, sid, k, how)
        finally:
            self.p["lift_s"] = self._p0

    def plan(self, v, task, t0):
        """Quay position for loading: reach_key = "finish" chooses by lift finish time (s + lift duration at that position); with
        far_prestage only near positions are chosen once the crane is open. Otherwise as PortSim."""
        key, pre = self.p.get("reach_key", "start"), self.p.get("far_prestage", False)
        if task["flow"] != "load" or (key == "start" and not pre):
            return super().plan(v, task, t0)
        G = min((a for a, _ in self.cal.get("crane") or []), default=0.0)
        hows = dict(cradle=["cradle"], direct=["direct"], mixed=["cradle", "direct"])[self.lift]
        ks = [k for k in range(len(self.quay)) if not (pre and t0 >= G - EPS and k >= self.p["reach"])]
        cand = [self.trial(v, task, t0, self.quay[k], k, how) for k in ks for how in hows]
        fin = lambda r: r["key"] if r.get("dead") else ((r["s"] + self._lift(r["k"]),) + r["key"][1:] if key == "finish" else r["key"])
        self.book(v, task, t0, min(cand, key=fin))

    def book(self, v, task, t0, r):
        if task["flow"] != "load" or r.get("dead"):
            return super().book(v, task, t0, r)
        self.p["lift_s"] = self._lift(r["k"])
        try:
            return super().book(v, task, t0, r)
        finally:
            self.p["lift_s"] = self._p0


class ReserveMixin:
    """Periodic reserved periods on the shared segment: held at full capacity (negative vehicle id, not in the occupation
    statistics)."""

    def _reserve(self, res, wins):
        for n, (a, b) in enumerate(wins):
            for r in res:
                self.table[r].append((a, b, self.cap[r], -2 * 10 ** 6 - n))


def sim_class(base, reach, reserve):
    mix = ([ReachMixin] if reach else []) + ([ReserveMixin] if reserve else [])
    return type(base.__name__ + "4", tuple(mix) + (base,), {}) if mix else base


def reserve_of(cfg, D, net, p):
    """cfg["reserve"] = dict(f, T_h) -> dict(res, wins, tl, f, T); None when f = 0."""
    rv = cfg.get("reserve")
    if not rv or not rv.get("f"):
        return None
    c, tl = reserve_road(D, net, p, cfg)
    T = float(rv["T_h"]) * 3600.0
    return dict(res=[c], wins=closures(T, float(rv["f"]), (cfg["horizon_h"] + 1) * 3600.0), tl=tl, f=float(rv["f"]), T=T)


def simulate4(cfg):
    from windport import bound4 as B4
    D, net, p, tasks, starts, quay, cal = setup4(cfg)
    lift = "direct" if cfg["S"] == 0 else cfg.get("lift", "cradle")
    Ku = cfg.get("K_u", 0)
    gate, yard = S2.idle_nodes(D)
    rule = cfg.get("rule", "fcfs")
    reach = p.get("reach") is not None
    if reach:
        assert rule == "fcfs" and not p.get("release_frac") and not cfg.get("n_unload"), "crane reach only with first-come-first-served, x = 0, loading only"
    rv = reserve_of(cfg, D, net, p)
    base = S2.ConvoySim if rule == "convoy" else WS.PortSim
    if p.get("unload_cap") is not None:
        base = type(base.__name__ + "Cap", (S2.CapMixin, base), {})
    cls = sim_class(base, reach, rv is not None)
    sim = cls(net, p, cfg["K"] + Ku, tasks, starts, quay, cal, lift, cfg.get("fixed", False), WS.ramp_res(D), record=cfg.get("record", False),
              exit=gate, yard=yard, hold=WS.hold_of(cfg), flows=["load"] * cfg["K"] + ["unload"] * Ku if Ku else None)
    if reach:
        sim._p0 = p["lift_s"]
    if rv is not None:
        assert not cfg.get("fixed"), "the fixed-duration representation does not check road conflicts, so reserved periods have no effect"
        sim._reserve(rv["res"], rv["wins"])
    sim.run()
    res = WS.result(cfg, D, net, p, sim, cal)
    res["rule"], res["idle"] = rule, [gate, yard]
    if rv is not None:
        res["reserve"] = dict(res="|".join(map(str, rv["res"][0])), tl=rv["tl"], f=rv["f"], T=rv["T"])
    if cfg["n_load"] and cal.get("crane"):
        if cfg.get("w1g"):                        # the serial-cut terms of windport.sim2.bounds2 are uncapped and take tens of seconds per point on a large yard; computed only on request
            res["w1g"] = S2.bounds2(cfg, D, net, p)
        if cfg.get("w4", True):
            res["w4"] = B4.bound4(cfg)
    return net, p, sim, res
