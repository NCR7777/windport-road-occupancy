"""Conservative lifting rule (windport/sim.py, sim2.py, sim3.py and the bound modules are not changed).

Semantics (p["lift_clear"] and p["lift_under"] both default to on; p["lift_tu"] defaults to TU):
  clear  for a lift from the vehicle (a direct lift, or the from-vehicle trip of a mixed scheme) the lift starts >= the vehicle body
         has left the road: loaded departure + the latest end of the no-wait windows of the loaded leg on all resources except the
         destination stop resource (road segments, junctions and the swept junction arms). In the road-occupancy model a stop is
         located at the vehicle front, and a segment window lasts until "vehicle rear leaves the next decision point + longitudinal
         clearance" (timed as if driving on); when the lifting position is less than one vehicle-plus-cargo length from the gate,
         this wait replaces the vehicle driving on until it has fully left the single lane (same convention as for when the
         single lane is released).
  under  during [s, s + d] after the lift starts, the resources below the load are held whole and exclusively (no other vehicle may
         occupy them): lift from the vehicle d = max(t_u, x·p), lift from a cradle d = t_u; t_u = lift_tu × p is the time from
         lift start until the load has cleared the quay front (scenario value), x = release_frac is the vehicle release time. For a
         lift from the vehicle the lifted vehicle itself does not count (it is below the load), but it leaves the quay no earlier
         than s + d; for a lift from a cradle no vehicle may be below (the vehicle that delivered it must leave first).
         Resources below the load (under_res): the quay-front road segment of the lifting position (the map segment of the stop;
         when split, every piece that intersects the load), the junction resources at the ends of that road that fall within the
         load extent, and for drive-in cradles also the bay of the lifting position. The load lies along the vehicle body and the
         stop is the vehicle front, so the extent is L_v backwards from the stop along the approach (open interval; the approach
         direction is that of the last arc of this loaded trip). The front road runs along the quay line and drive-in bays lie on
         its land side; a lift towards the ship also crosses the front road, so both cradle types use the same rule. Other
         segments reaching seawards (ramp segments) are not included.
         In the main geometry (first cradle 40 m from the gate, L_v = 110 m) the extent reaches about 70 m past the gate; by the
         road-occupancy convention (after clear the body counts as having left the single lane) that part is not counted;
         sensitivity p["lift_span"] = "gate" (span_res) goes back L_v along this loaded route, including the gate and the top
         segment of the single lane.
  Convoy dispatch (LiftConvoySim): a vehicle lifting from a cradle whose lift has not started may also be bumped - the lift is
         withdrawn, and after the bumped vehicle has left the area below the load it is rebooked in the next free crane window;
         the order already booked on the crane is unchanged (if it would have to pass another lift, the bump is cancelled).
  The fixed-duration representation (fixed) does not check road conflicts, so under is dropped together with the road; clear is
         still counted (the vehicle must stand still before lifting; that is an operation time, not a road conflict, and both
         representations use the same operation definition).
With lift_tu = 0 and x = 0, under has no effect and a cradle trip calls PortSim unchanged; with clear and under both off a direct
lift also calls PortSim unchanged (identical to PortSim trip by trip, tested).
installed(): replaces windport.sim.PortSim, windport.sim2.ConvoySim, windport.sim3.CutSim and sim2.build_map with the versions in
this module (context manager; install() is permanent, for worker processes), so the existing experiment scripts run under the new
semantics without changing a line. build_map also accepts geo["first_cradle_m"] (distance of the first cradle from the gate, for
sensitivity). The bound under the new semantics is in windport/bound_lift.py."""
import contextlib

from occupancy.network import EPS
from windport import sim as WS
from windport import sim2 as S2
from windport import sim3 as S3

BIG, CRANE, NOBODY = WS.BIG, WS.CRANE, WS.NOBODY
TU = 0.05                   # main rule t_u = 0.05 p (scenario value; sensitivity over 0.05-0.1 p)
_BUILD = S2.build_map


def arrive_fw(net, o_node, d_node):
    """Whether the last arc of the loaded leg to the lifting position runs in the forward direction of the segment (increasing s)."""
    return net.arc[net.path(o_node, d_node)[-1]][4]


def under_res(net, sid, Lp, fw):
    """Resources below the load while lifting at position sid: the load lies in (s − Lp, s) (forward arrival) or (s, s + Lp)
    (reverse arrival)."""
    _, rid, s = net.stops[sid]["node"].split("|")
    s = float(s)
    lo, hi = (s - Lp, s) if fw else (s, s + Lp)
    pieces = sorted((q, r) for q, r in net.road.items() if r["orig"] == rid)
    out = [("r", q) for q, r in pieces if r["s0"] < hi and r["s1"] > lo]
    L = max(r["s1"] for _, r in pieces)
    ends = [(r["a"], 0.0) for _, r in pieces if r["s0"] == 0.0] + [(r["b"], L) for _, r in pieces if r["s1"] == L]
    bay = [net.stops[sid]["res"]] if net.stops[sid]["res"][0] == "b" else []          # drive-in: the bay itself is also below the load
    return out + [("n", n) for n, at in ends if lo < at < hi and n in net.node_res] + bay


def span_res(net, sid, Lp, path):
    """Sensitivity (p["lift_span"] = "gate"): the load extent goes back L_v from the stop along this loaded route; every segment and
    junction passed counts as below the load (past the gate this includes the gate and the top segment of the single lane), united
    with under_res. Returns (resource list, set of nodes passed within the extent)."""
    out, nodes, dist = [], set(), 0.0
    for a in reversed(path):
        t, _, L, rid, _ = net.arc[a]
        if dist >= Lp - EPS:
            break
        out.append(("r", rid))
        dist += L
        if dist < Lp - EPS:
            nodes.add(t)
            if t in net.node_res:
                out.append(("n", t))
    fw = net.arc[path[-1]][4]
    return sorted(set(out) | set(under_res(net, sid, Lp, fw))), nodes


def clear_end(WL, TL):
    """Time (relative to departure) at which the vehicle body has left the road on the loaded leg: latest end of the WL windows,
    not earlier than arrival."""
    return max([TL] + [b for _, _, b, _ in WL])


class LiftSim(WS.PortSim):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.clear, self.under = self.p.get("lift_clear", True), self.p.get("lift_under", True)
        self.tu = self.p.get("lift_tu", TU) * self.p["lift_s"] if self.under else 0.0
        self._u, self.ubid, self.ucradle = {}, {}, set()

    def under_of(self, k, o_node):
        key = (k, o_node)
        if key not in self._u:
            d = self.net.stops[self.quay[k]]["node"]
            if self.p.get("lift_span", "head") == "gate":
                self._u[key] = span_res(self.net, self.quay[k], self.p["Lv"], self.net.path(o_node, d))[0]
            else:
                self._u[key] = under_res(self.net, self.quay[k], self.p["Lv"], arrive_fw(self.net, o_node, d))
        return self._u[key]

    def trial(self, v, task, t0, sid, k, how):
        direct = how == "direct"
        if task["flow"] != "load" or not ((direct and (self.clear or self.under)) or (not direct and self.tu > EPS and not self.fixed)):
            return super().trial(v, task, t0, sid, k, how)
        # Same as the loading branch of PortSim.trial with three changes: a lift from the vehicle starts >= the body has left the road
        # (clear); the resources below the load are exclusive in [s, s + d] (under); for a lift from the vehicle the vehicle leaves no
        # earlier than s + d, for a lift from a cradle the lift starts no earlier than the delivering vehicle has left the area below
        # the load (book the departure first, then the lift)
        task["d"] = sid
        load, unload = self.dur(task)
        so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr = self.windows(v, task)
        off = clear_end(WL, TL) if (direct and self.clear) else TL
        WE, WL = self.kept(WE), self.kept(WL)
        ko, kd = bool(self.kept([(so["res"],)])), bool(self.kept([(sd["res"],)]))
        hold = 0.0 if direct else unload
        P, tmin, jumps, own = self.p["lift_s"], t0, [], NOBODY
        xP = self.p.get("release_frac", 0.0) * P if direct else 0.0
        dur = max(self.tu, xP) if self.under else 0.0
        ures = self.under_of(k, so["node"]) if dur > EPS else []
        U = self.kept([(u, 0.0, dur, self.cap[u]) for u in ures])
        while True:
            t1 = self.earliest(WE + ([(so["res"], ao, TE + load + tail_l, d_so)] if ko else []), tmin, own, False, jumps)
            a = t1 + TE
            t2 = self.earliest(WL + ([(sd["res"], ad, TL + hold + clr, d_sd)] if kd else []), a + load, own, False, jumps)
            o2 = self.conflict(so["res"], t1 + ao, t2 + tail_l, d_so, own) if ko else None
            if o2 is not None:
                tmin = o2 - ao
                continue
            tc = t2 + TL
            if direct:
                s = self.earliest([(CRANE, 0.0, P, 1.0)] + U, t2 + off, own, False, jumps)
                r0 = s + xP
                if r0 >= BIG / 2:
                    return dict(key=(BIG, BIG, k, True), dead=True, k=k, how=how, d=sid)
            else:
                r0 = tc + unload
                if r0 >= BIG / 2:                            # as in PortSim.trial: the cradle holds a pile that can never be lifted; this trip does not start (vehicle returns to idle at once)
                    return dict(key=(BIG, BIG, k, True), dead=True, k=k, how=how, d=sid)
                x = self.leave(v, sd, t2, WL, r0, clr)
                # the delivering vehicle first leaves the area below the load: its windows on these resources from the exit leg, the
                # stop window and the loaded leg (with a very short set-down the rear may still be on a junction below the load) have ended
                gone = ([x["xs"] + b for q, _, b, _ in x["W"] if q in ures] + ([x["dend"]] if sd["res"] in ures else [])
                        + [t2 + b for q, _, b, _ in WL if q in ures])
                s = self.earliest([(CRANE, 0.0, P, 1.0)] + U, max([tc + hold] + gone), own, False, jumps)
            o2 = self.conflict(WS.cradle(k), tc, s, 1.0, own)
            if o2 is not None:
                tmin = t1 + (o2 - tc)
                continue
            if direct:
                x = self.leave(v, sd, t2, WL, max(r0, s + dur) if U else r0, clr)
            dend = x["dend"]
            o2 = self.conflict(sd["res"], tc + hold + clr, dend, d_sd, own) if kd and dend > tc + hold + clr + EPS else None
            if o2 is not None:
                tmin = t1 + (o2 - (t2 + ad))
                continue
            break
        if self.p["reserve_jit"] and not self.fixed:
            tj = t2 - load - TE
            if tj > t1 + EPS and all(self.conflict(r, tj + s_, tj + e_, d, own) is None for r, s_, e_, d in WE):
                t1, a = tj, tj + TE
        # windows below the load: for a lift from the vehicle at a roadside lifting position the vehicle already occupies that road at
        # its loaded width; top up to the full segment capacity
        Uw = [(u, s, s + dur, w - (d_sd if direct and u == sd["res"] else 0.0)) for u, _, _, w in U] if s < BIG / 2 else []
        return dict(key=(s, x["rel"], k, direct), k=k, how=how, d=sid, t1=t1, a=a, t2=t2, tc=tc, s=s, r0=r0, rel=x["rel"], x=x, dend=dend,
                    w=(so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr), U=[w for w in Uw if w[3] > EPS])

    def book(self, v, task, t0, r):
        if r.get("U"):                     # the area below the load is booked as a separate leg. Its resource list gets an extra zero-width
            b = self.bid()                 # crane window so that it is never exactly [lifting position] (ConvoySim uses that to spot the destination stop leg)
            self.commit(b, t0, r["U"] + [(CRANE, r["s"], r["s"], 0.0)])
            self.account(r["U"])
            self.ubid[v.id] = b
            if r["how"] != "direct":
                self.ucradle.add(b)
        super().book(v, task, t0, r)


class LiftConvoySim(S2.ConvoySim, LiftSim):
    """Convoy dispatch (ConvoySim) under the conservative lifting rule. Lift from the vehicle: a bumped vehicle rebooks its departure
    no earlier than the end of the closure below the load. Lift from a cradle: on a bump the lift that has not started is withdrawn -
    first the leg below the load is removed (the new vehicle may pass through), the crane and cradle bookings are kept as
    placeholders; after the new vehicle is booked and the bumped vehicle has rebooked its departure, the lift is rebooked in the next
    free crane window after that vehicle has left the area below the load. If the rebooking would pass another lift already booked on
    the crane (the crane order would change) or the cradle is taken by someone else, the whole bump is cancelled (state is restored
    to before the bump and booked without bumping). A bumping plan is only adopted if it finishes this group of lifts earlier than
    the plan without bumping (plan)."""

    def book(self, v, task, t0, r):
        """As ConvoySim.book; for a lift from the vehicle a bumped vehicle also rebooks its departure no earlier than the end of the
        closure below the load (r0 of pend becomes max(r0, s + d))."""
        super().book(v, task, t0, r)
        if r.get("U") and r["how"] == "direct" and v.id in self.pend:
            y = self.pend[v.id]
            y["r0"] = max(y["r0"], max(w[2] for w in r["U"]))

    def _cradle_pending(self, y, t0):
        tr = y["trip"]
        return tr["how"] != "direct" and tr["s"] is not None and tr["s"] > t0 + EPS and self.ubid.get(tr["vid"]) in self.ucradle

    def _free_after(self, y):
        """As ConvoySim._free_after; the vehicle's own leg below the load also counts as its own."""
        a = y["t2"] + y["ad"]
        mine = set(y["bids"]) | {self.ubid.get(y["trip"]["vid"])}
        return not any(e[1] > a + EPS and e[3] not in mine for e in self.table[y["sd"]["res"]] if e[0] >= a - EPS)

    def _bump(self, cand, t0):
        out = super()._bump(cand, t0)
        out["under"] = []
        for k in cand:
            if self._cradle_pending(self.pend[k], t0):
                b = self.ubid[k]
                for res in list(self.table):
                    keep = []
                    for e in self.table[res]:
                        (out["under"].append((res, e)) if e[3] == b else keep.append(e))
                    self.table[res] = keep
        return out

    def _restore(self, saved):
        super()._restore(saved)
        for res, e in saved["under"]:
            self.table[res].append(e)

    def _snap(self):
        trips = {id(y["trip"]): (y["trip"], dict(y["trip"])) for y in self.pend.values()}
        return dict(table={r: list(l) for r, l in self.table.items()}, ev=list(self.ev), seq=self.seq, nb=self.nb, n_trips=len(self.trips),
                    held=dict(self.held), pend={k: dict(y) for k, y in self.pend.items()}, trips=trips, vdone=dict(self.vdone), ubid=dict(self.ubid),
                    ucradle=set(self.ucradle), bumps=self.bumps, loc=[v.loc for v in self.vs], occ=dict(self.occ), ivs={r: list(l) for r, l in self.ivs.items()})

    def _back(self, z):
        self.table.clear()
        self.table.update(z["table"])
        self.ev[:], self.seq, self.nb = z["ev"], z["seq"], z["nb"]
        del self.trips[z["n_trips"]:]
        self.held, self.pend, self.vdone, self.ubid, self.ucradle, self.bumps = z["held"], z["pend"], z["vdone"], z["ubid"], z["ucradle"], z["bumps"]
        for tr, old in z["trips"].values():
            tr.clear()
            tr.update(old)
        for v, loc in zip(self.vs, z["loc"]):
            v.loc = loc
        self.occ.clear()
        self.occ.update(z["occ"])
        self.ivs.clear()
        self.ivs.update(z["ivs"])

    def _relift(self, k, t0):
        """After the bumped vehicle k has rebooked its departure, rebook its lift from the cradle (the withdrawn leg below the load is
        not put back); returns False if that is not possible."""
        y = self.pend[k]
        tr, sd = y["trip"], y["sd"]
        s0, tc, kq, P = tr["s"], tr["tc"], tr["k"], self.p["lift_s"]
        cr = WS.cradle(kq)
        bid = next(e[3] for e in self.table[cr] if abs(e[0] - tc) < EPS and abs(e[1] - s0) < EPS)
        for res in (cr, CRANE):
            self.table[res] = [e for e in self.table[res] if e[3] != bid]
        ures = self.under_of(kq, self.net.stops[tr["o"]]["node"])
        node, xs, _ = tr["exit"]
        _, Wx = self.exit_w(sd["node"], node)
        stop = sd["res"] in {r for r, *_ in Wx}
        gone = ([xs + b for q, _, b, _ in Wx if q in ures] + ([xs if stop else xs + y["clr"]] if sd["res"] in ures else [])
                + [y["t2"] + b for q, _, b, _ in y["WL"] if q in ures])
        U = self.kept([(u, 0.0, self.tu, self.cap[u]) for u in ures])
        s1 = self.earliest([(CRANE, 0.0, P, 1.0)] + U, max([s0] + gone), NOBODY, False, [])
        if s1 >= BIG / 2 or any(s0 - EPS <= e[0] < s1 - EPS for e in self.table[CRANE]) or self.conflict(cr, tc, s1, 1.0, NOBODY) is not None:
            return False
        W = [(cr, tc, s1, 1.0), (CRANE, s1, s1 + P, 1.0)]
        self.commit(self.bid(), t0, W)
        self.account(W)
        ub = self.bid()
        Uw = [(u, s1, s1 + self.tu, w) for u, _, _, w in U if w > EPS]
        self.commit(ub, t0, Uw + [(CRANE, s1, s1, 0.0)])
        self.account(Uw)
        self.ubid[k] = ub
        self.ucradle.add(ub)
        tr["s"], tr["F_vessel"] = s1, s1 + P
        return True

    def plan(self, v, task, t0):
        """As ConvoySim.plan (bumping is considered when the new vehicle would arrive earlier by bumping), with two additions: if a
        bumped vehicle lifts from a cradle and its lift has not started, its lift is rebooked after the new vehicle and the rebooked
        departure, otherwise the bump is cancelled; the plans with and without bumping are compared on the finishing times of this
        group of lifts (the new vehicle and the one of each bumped vehicle), and the one with the earlier (latest, sum) is taken -
        without bumping each bumped vehicle keeps its planned lift and the new vehicle takes its best choice without bumping. With both
        switches off this is ConvoySim."""
        if task["flow"] == "unload" or not (self.clear or self.under):
            return super().plan(v, task, t0)
        best0 = self._best(v, task, t0)
        cand = sorted((k for k, y in self.pend.items() if y["xs"] > t0 + EPS and k != v.id and self._free_after(y)),
                      key=lambda k: (self.pend[k]["r0"], k))
        if not cand or best0.get("dead"):
            return self.book(v, task, t0, best0)
        lifted = [k for k in cand if self._cradle_pending(self.pend[k], t0)]
        P = self.p["lift_s"]
        done = lambda s: BIG if s is None or s >= BIG / 2 else s + P
        m0 = [done(best0["s"])] + [done(self.pend[k]["trip"]["s"]) for k in cand]
        saved = self._bump(cand, t0)
        best1 = self._best(v, task, t0)
        if not best1.get("dead") and best1["tc"] < best0["tc"] - EPS:
            z = self._snap()
            self.bumps += 1
            self.book(v, task, t0, best1)
            for k in cand:
                self._rebook(k, t0, saved["tmp"][k])
            if all(self._relift(k, t0) for k in lifted):
                m1 = [done(best1["s"])] + [done(self.pend[k]["trip"]["s"]) for k in cand]
                a1, a0 = (max(m1), sum(m1)), (max(m0), sum(m0))
                if a1[0] < a0[0] - EPS or (abs(a1[0] - a0[0]) <= EPS and a1[1] < a0[1] - EPS):
                    return
                self.rejected = getattr(self, "rejected", 0) + 1
            self._back(z)
        self._restore(saved)
        self.book(v, task, t0, best0)


class LiftCutSim(S3.CutSim, LiftSim):
    pass


def build_map(geo):
    """sim2.build_map that also accepts geo["first_cradle_m"]: shifts all cradle positions so the first cradle lies this far from
    the gate (the port type has its first cradle 40 m from the gate; for sensitivity)."""
    g = {k: v for k, v in geo.items() if k != "first_cradle_m"}
    D = _BUILD(g)
    if "first_cradle_m" in geo:
        dx = float(geo["first_cradle_m"]) - 40.0
        for x in D["zones"]["z_cradle"]["extensions"]["org.shipyard.research_semantics"]["frontage"]:
            x["sStartM"] += dx
            x["sEndM"] += dx
    return D


def install():
    """Permanent replacement (for worker processes): wherever the existing modules look up a class by name, this module's version
    is used."""
    WS.PortSim, S2.ConvoySim, S3.CutSim, S2.build_map = LiftSim, LiftConvoySim, LiftCutSim, build_map


@contextlib.contextmanager
def installed():
    old = WS.PortSim, S2.ConvoySim, S3.CutSim, S2.build_map
    install()
    try:
        yield
    finally:
        WS.PortSim, S2.ConvoySim, S3.CutSim, S2.build_map = old


# ---------------------------------------------------------------- geometry (shared by simulation and bound)
def pair_times(net, p, rows, quay):
    """For each (cradle row, lifting position) pair: loaded travel TL, ends of the loaded windows ends, time from arrival until the
    body has left the road off, and empty return TE (lifting position -> cradle row). Uses the no-wait windows of PortNet.leg
    (including stopping to turn), the same windows as the simulation."""
    cap, size = net.capacities(p)
    out = {}
    for o in rows:
        so = net.stops[o]
        for d in quay:
            sd = net.stops[d]
            TL, st, uses, _ = net.leg(so["node"], sd["node"], p["v_loaded"], p["Lv"], p["B"], True, p, cap, size, sd["res"],
                                      net.demand(sd["res"], p["B"], True, p, cap))
            ends = {r: st[rr] + dl for r, d_, a, rr, dl in uses if rr is not None}
            TE = net.leg(sd["node"], so["node"], p["v_empty"], p["plat_len"], p["plat_w"], False, p, cap, size, so["res"],
                         net.demand(so["res"], p["plat_w"], False, p, cap), True)[0]
            out[o, d] = dict(TL=TL, TE=TE, ends=ends, off=max([TL] + list(ends.values())) - TL)
    return out
