"""Simulation of an offshore wind marshalling port: the occupancy model (whole-path reservation of occupancy.Sim) with port
semantics; occupancy/, bounds/ and exact/ are unchanged, only subclasses are used.

PortNet (subclass of Net, overrides leg): turning of long loads. At every turn of angle >= turn_deg (junction resource or not) a
  loaded vehicle stops, switches steering programme and then turns, taking
  δ = sweep_steer_s + angle × (Lv/2)/v (the end of the load travels an arc of radius Lv/2): later decision times and the travel
  time are shifted by δ; while stopped the tail still covers the incoming section, whose release is also delayed by δ; if the
  turn is at a junction resource the junction is held for (D + Lv + longitudinal clearance)/v + δ, and during the same period the
  other arms of the junction (road sections not on the vehicle's route) are also held exclusively (sweep).
  Empty vehicles as before (a constant turn_sweep_s added at junctions, no stop). With sweep_steer_s = None it equals Net.
PortSim (subclass of Sim, whole-path reservation only: no stopping en route, waiting only at the origin, at a quay slot or at an
  idle location, so no deadlock):
  calendar  cal = dict(crane=[(a, b), ...], ramp=[(a, b), ...]): open periods (s); a missing key means always open. Closed
        periods are held at full capacity in the reservation table (negative vehicle ids, excluded from occupancy statistics).
        Both the ramp road and the on-board pick-up point are held, so a whole ramp operation (empty vehicle drives onto the ramp
        -> loaded vehicle's tail leaves the ramp) falls inside an open period; likewise the crane lifts only during the berthing
        period, each lift entirely inside an open period.
  resources  cradle ('c', 'cr', k): capacity 1, held from set-down (cradle mode) or from the vehicle's arrival (direct lift)
        until the lift starts; crane ('c', 'crane'): capacity 1, each lift holds it for lift_s;
        gate holding place HOLD: capacity hold (Q_h), see "idle locations".
  tasks  load: o = yard saddle row, d chosen among the quay slots quay at dispatch; durations hp_s (jack-up pick-up), hd_s
        (set-down into the cradle).
        unload: o = top of the ramp (on-board pick-up point), d = saddle row; durations roro_s (on-board part of the ramp
        operation), hy_s (set down on saddles).
  lifting  lift = "cradle": the crane lifts only from cradles (base case; the premise of W1 Theorem 1); "direct": S = 0, the
        vehicle waits at the quay slot for the crane and is released release_frac × lift_s after the lift starts (default 0:
        released as soon as the monopile leaves the vehicle); "mixed": in cradle mode the crane may also lift from the vehicle
        (Corollary 2); each trip takes the option with the earliest lift start, then the earliest release.
  dispatch  first come first served, nearest idle vehicle to the origin (Sim.dispatch; with flows, vehicles are assigned per
        flow); at dispatch the empty run, pick-up, loaded run, set-down (or waiting for the crane), crane slot and departure from
        the quay are all booked at once (as Sim.plan_full, including just-in-time departure); if they cannot be booked the whole
        trip is shifted later. Load-out picks, among the quay slots, the one with the earliest lift start, then earliest
        release, then lowest index.
  booking ownership: every leg (empty run, origin stop, loaded run, destination stop, departure, waiting) has its own booking
        id, and the conflict check exempts none of the vehicle's earlier legs - a vehicle body is in one place only, so a later
        leg cannot pass through a window of its own earlier leg that has not ended (e.g. with direct lift the loaded vehicle's
        tail still covers the incoming section, so departure waits until the tail has left).
  idle locations: after release at load-out the vehicle immediately drives empty away from the dead-end quay front and books
        one of two locations; all waiting between two trips is recorded as occupancy:
        gate holding place HOLD (if hold > 0, capacity hold; the vehicle waits there until the empty run of its next trip
        starts); if there is no holding place or it is full, the vehicle drives all the way out of the single lane to the yard
        side (yard, the two-lane junction at the south end of the single lane; the yard side is open ground where parked empty
        vehicles do not block traffic - this is the only idle location whose occupancy is not recorded). A vehicle waiting at
        the quay slot to leave holds the slot.
        After unloading the vehicle stays next to the saddle row (yard side).
  records  trips: one entry per trip (recorded when booked) - t1 empty-run start, a arrival at origin, t2 loaded departure, tc
        arrival at destination (start of set-down or waiting for the crane), s lift start, r0 release,
        exit = [target node, departure time, "hold" | "yard"], and completion events F_quay (set-down done), F_vessel (lift
        done), F_ramp (tail leaves the ramp road, including longitudinal clearance), F_yard (set down on saddles, vehicle
        released); rel is the time the vehicle reaches an idle location (available again).
  fixed = True: fixed-duration representation (E3) - roads and junctions are not checked for conflicts (each trip at its
        conflict-free travel time); ramp, cradles, crane, saddle rows, holding places and calendar as before.
simulate(cfg) builds layout, network and tasks from a point config and runs them, returning (net, p, sim, result);
run_point(cfg) returns only the result (JSON-serialisable).
"""
import collections
import json
import math

from occupancy import params as PP
from occupancy.network import EPS, Net
from occupancy.sim import Sim, Vehicle
from windport import archetypes as A
from windport import bound as WB
from windport.mapcache import map_file

BIG = 1e9                       # closed "until later": no open period after the window
CRANE = ("c", "crane")
HOLD = ("b", "hold", 0)
NOBODY = -7                     # "own vehicle" in conflict checks: matches no booking id, so earlier own bookings count


def cradle(k):
    return ("c", "cr", k)


def closed(open_windows):
    """Open periods -> closed periods within [0, BIG)."""
    out, t = [], 0.0
    for a, b in sorted(open_windows):
        if a > t + EPS:
            out.append((t, a))
        t = max(t, b)
    out.append((t, BIG))
    return out


def turn_delays(net, path, Lv, v, p):
    """Stop-and-steer times δ_i of a loaded leg at the start of each run (decision points i >= 1); runs as in Net.leg.
    Returns (runs [road, direction, first arc, last arc], list of δ)."""
    runs = []
    for a in path:
        rid, fw = net.arc[a][3], net.arc[a][4]
        if runs and runs[-1][0] == rid and runs[-1][1] == fw:
            runs[-1][3] = a
        else:
            runs.append([rid, fw, a, a])
    dl = [0.0] * len(runs)
    for i in range(1, len(runs)):
        ang = net.turn(runs[i - 1][3], runs[i][2])
        if math.degrees(ang) >= p["turn_deg"]:
            dl[i] = p["sweep_steer_s"] + ang * Lv / 2 / v
    return runs, dl


# ---------------------------------------------------------------- network: turning of long loads
class PortNet(Net):
    def leg(self, src, dst, v, Lv, b, loaded, p, cap, size, end_res, end_d, start_node=False):
        T, st, uses, arr = super().leg(src, dst, v, Lv, b, loaded, p, cap, size, end_res, end_d, start_node)
        if not loaded or src == dst or p.get("sweep_steer_s") is None:
            return T, st, uses, arr
        runs, dl = turn_delays(self, self.path(src, dst), Lv, v, p)
        if not any(dl):
            return T, st, uses, arr
        m = len(runs)
        cum = [sum(dl[1:j]) for j in range(arr + 1)]        # stops before decision point j (excluding j); arrival = all
        st2 = [x + c for x, c in zip(st, cum)]
        out = []
        for res, d, a, r, x in uses:
            if res[0] == "n" and a == r and 0 < a < m and res[1] == self.arc[runs[a][2]][0] and dl[a]:
                x = (size[res[1]] + Lv + p["long_clear"]) / v + dl[a]              # junction: stop-and-steer + sweep
                out += [(("r", q), cap[("r", q)], a, a, x) for q in self.incident[res[1]] if q not in (runs[a - 1][0], runs[a][0])]
            elif res[0] == "r" and r is not None and 0 < r < m and dl[r]:
                x += dl[r]                                                       # incoming section: tail covers it while stopped
            out.append((res, d, a, r, x))
        return T + sum(dl), st2, out, arr


# ---------------------------------------------------------------- simulation
class PortSim(Sim):
    def __init__(self, net, p, K, tasks, starts, quay, cal=None, lift="cradle", fixed=False, ramp=(), record=False, exit=None, yard=None,
                 hold=0, flows=None):
        assert lift in ("cradle", "direct", "mixed") and len(starts) == K and exit is not None and yard is not None
        # K = 0: skip vehicle_starts (layouts without a ramp have no start classes)
        super().__init__(net, p, "reserve", 0, 1, None, record=record, tasks=tasks)
        self.vs = [Vehicle(k, loc) for k, loc in enumerate(starts)]
        self.idle = list(range(K))
        self.quay, self.lift, self.fixed, self.ramp_res = list(quay), lift, fixed, set(ramp)
        self.exit, self.yard, self.hold, self.flows = exit, yard, hold, flows
        self._exit, self.nb, self.held = {}, 10 ** 7, {}
        self.cap[CRANE] = 1.0
        self.cap[HOLD] = float(hold) if hold != math.inf else 1e6
        for k in range(len(self.quay)):
            self.cap[cradle(k)] = 1.0
        self.cal, self.trips, n = cal or {}, [], 0
        for key, rs in (("crane", [CRANE]), ("ramp", sorted(self.ramp_res))):
            if self.cal.get(key) is None:
                continue
            for a, b in closed(self.cal[key]):
                for r in rs:
                    n += 1
                    self.table[r].append((a, b, self.cap[r], -10 ** 6 - n))

    def bid(self):
        self.nb += 1
        return self.nb

    def dispatch(self, t):
        """p["unload_first"]: unloading tasks in the queue are dispatched first (ramp operations in the tidal window have
        priority; used for simultaneous unloading and loading with a shared fleet); otherwise first come first served.
        flows (flow each vehicle may serve, None = both): with separate vehicles for unloading and loading, each task in queue
        order gets the idle vehicle nearest to its origin that may serve that flow."""
        if self.p.get("unload_first") and self.queue:
            self.queue = collections.deque(sorted(self.queue, key=lambda x: x["flow"] != "unload"))
        if self.flows is None:
            return super().dispatch(t)
        while self.idle and self.queue:
            pick = None
            for task in self.queue:
                ks = [k for k in self.idle if self.flows[k] in (None, task["flow"])]
                if ks:
                    o = self.net.stops[task["o"]]["node"]
                    pick = (task, min(ks, key=lambda k: (self.net.dist(self.vs[k].loc, o), k)))
                    break
            if pick is None:
                return
            task, k = pick
            self.queue.remove(task)
            self.idle.remove(k)
            task["dispatch"], task["start"] = t, self.vs[k].loc
            self.plan(self.vs[k], task, t)

    def kept(self, W):
        """The fixed-duration representation keeps only ramp, stops (including holding places), cradles and crane (no conflict
        check on roads and junctions)."""
        return W if not self.fixed else [w for w in W if w[0][0] in ("b", "c") or w[0] in self.ramp_res]

    def dur(self, task):
        p = self.p
        return (p["hp_s"], p["hd_s"]) if task["flow"] == "load" else (p["roro_s"], p["hy_s"])

    def plan(self, v, task, t0):
        if task["flow"] == "unload":
            best = self.trial(v, task, t0, task["d"], None, None)
        else:
            hows = dict(cradle=["cradle"], direct=["direct"], mixed=["cradle", "direct"])[self.lift]
            best = min((self.trial(v, task, t0, sid, k, how) for k, sid in enumerate(self.quay) for how in hows), key=lambda r: r["key"])
        self.book(v, task, t0, best)

    def exit_w(self, node, target):
        """(duration, relative windows) of the empty run from quay slot node to target (the gate with the holding place, or the
        yard side); in the fixed-duration representation only the stop windows remain."""
        key = (node, target)
        if key not in self._exit:
            p = self.p
            T, st, uses, _ = self.net.leg(node, target, p["v_empty"], p["plat_len"], p["plat_w"], False, p, self.cap, self.size, ("x",), 0.0, True)
            self._exit[key] = (T, self.kept([(r, st[a], st[b] + dl, d) for r, d, a, b, dl in uses if b is not None]))
        return self._exit[key]

    def trial(self, v, task, t0, sid, k, how):
        """Earliest feasible booking for one destination (quay slot k, lift mode how); does not change the reservation table."""
        task["d"] = sid
        load, unload = self.dur(task)
        so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr = self.windows(v, task)
        WE, WL = self.kept(WE), self.kept(WL)
        ko, kd = bool(self.kept([(so["res"],)])), bool(self.kept([(sd["res"],)]))
        hold = 0.0 if how == "direct" else unload            # minimum time the destination stop is held after arrival
        P, tmin, jumps, own = self.p["lift_s"], t0, [], NOBODY
        x = None
        while True:
            t1 = self.earliest(WE + ([(so["res"], ao, TE + load + tail_l, d_so)] if ko else []), tmin, own, False, jumps)
            a = t1 + TE
            t2 = self.earliest(WL + ([(sd["res"], ad, TL + hold + clr, d_sd)] if kd else []), a + load, own, False, jumps)
            o2 = self.conflict(so["res"], t1 + ao, t2 + tail_l, d_so, own) if ko else None
            if o2 is not None:                               # waiting after loading would hold the origin: shift everything later
                tmin = o2 - ao
                continue
            tc, s, x, dend = t2 + TL, None, None, t2 + TL + hold + clr
            if task["flow"] == "unload":
                break
            s = self.earliest([(CRANE, 0.0, P, 1.0)], tc + hold, own, False, jumps)
            o2 = self.conflict(cradle(k), tc, s, 1.0, own)
            if o2 is not None:                               # cradle held by the previous pile: arrive after it has been lifted
                tmin = t1 + (o2 - tc)
                continue
            r0 = s + self.p.get("release_frac", 0.0) * P if how == "direct" else tc + unload
            if r0 >= BIG / 2:                                # direct lift, no crane slot left: trip does not start
                return dict(key=(BIG, BIG, k, True), dead=True, k=k, how=how, d=sid)
            x = self.leave(v, sd, t2, WL, r0, clr)
            dend = x["dend"]
            o2 = self.conflict(sd["res"], tc + hold + clr, dend, d_sd, own) if kd and dend > tc + hold + clr + EPS else None
            if o2 is not None:                               # waiting at the slot holds it: on conflict shift all later
                tmin = t1 + (o2 - (t2 + ad))
                continue
            break
        # just-in-time departure (as Sim.plan_full): the origin window shrinks to a subset of the feasible one, only the empty
        # run is checked
        if self.p["reserve_jit"] and not self.fixed:
            tj = t2 - load - TE
            if tj > t1 + EPS and all(self.conflict(r, tj + s_, tj + e_, d, own) is None for r, s_, e_, d in WE):
                t1, a = tj, tj + TE
        r0 = None if s is None else (s + self.p.get("release_frac", 0.0) * P if how == "direct" else tc + unload)
        rel = x["rel"] if x else (tc + unload if task["flow"] == "unload" else BIG)
        return dict(key=(s if s is not None else 0.0, rel, k if k is not None else 0, how == "direct"), k=k, how=how, d=sid,
                    t1=t1, a=a, t2=t2, tc=tc, s=s, r0=r0, rel=rel, x=x, dend=dend, w=(so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr))

    def leave(self, v, sd, t2, WL, r0, clr):
        """Leave the quay after release (r0): try the gate holding place first (if a place is free), otherwise drive out of the
        single lane to the yard side; departure is not earlier than the end of the vehicle's own loaded-leg windows on these
        resources (the vehicle body is in one place only) and does not conflict with other bookings (while waiting the vehicle
        stays at the quay slot). Returns dict(kind, node, xs departure time, TX, W relative windows, rel arrival, dend)."""
        endL = collections.defaultdict(float)
        for r, a, b, d in WL:
            endL[r] = max(endL[r], t2 + b)
        for kind, node in ([("hold", self.exit)] if self.hold > 0 else []) + [("yard", self.yard)]:
            TX, Wx = self.exit_w(sd["node"], node)
            lo = max([r0] + [endL[r] - a for r, a, b, d in Wx if r in endL])
            xs = self.earliest(Wx, lo, NOBODY, False, [])
            if kind == "hold" and self.conflict(HOLD, xs + TX, BIG, 1.0, self.held.get(v.id, NOBODY)) is not None:
                continue
            # roadside quay slot: the departure starts on this road, so the slot is held until departure
            stop = sd["res"] in {r for r, *_ in Wx}
            return dict(kind=kind, node=node, xs=xs, TX=TX, W=Wx, rel=xs + TX, dend=xs if stop else xs + clr)
        raise AssertionError("the yard side is always reachable")

    def book(self, v, task, t0, r):
        # trip does not start: the vehicle stays where it is (idle location unchanged), the task is not dispatched again
        if r.get("dead"):
            self.trips.append(dict(id=task["id"], flow=task["flow"], vid=v.id, o=task["o"], d=r["d"], k=r["k"], how=r["how"], t0=t0,
                                   start=v.loc, t1=BIG, a=BIG, t2=BIG, tc=BIG, s=None, r0=None, F_quay=None, F_vessel=None, F_ramp=None,
                                   F_yard=None, rel=BIG, exit=None))
            self.push(t0, "done", (v.id, task, 0.0))         # idle again at once (may serve e.g. unloading)
            return
        so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr = r["w"]
        task["d"] = r["d"]
        t1, t2, tc, s, P, x = r["t1"], r["t2"], r["tc"], r["s"], self.p["lift_s"], r["x"]
        if v.id in self.held:                                # previous trip ended in the holding place: held until now
            hb = self.held.pop(v.id)
            self.table[HOLD] = [(a, (t1 if b >= BIG / 2 and k == hb else b), w, k) for a, b, w, k in self.table[HOLD]]
        dend = r["dend"] if x else (BIG + clr if r["how"] == "direct" and s is not None else r["dend"])
        legs = [[(q, t1 + a, t1 + b, d) for q, a, b, d in WE], [(so["res"], t1 + ao, t2 + tail_l, d_so)],
                [(q, t2 + a, t2 + b, d) for q, a, b, d in WL], [(sd["res"], t2 + ad, dend, d_sd)]]
        if s is not None:
            legs.append([(cradle(r["k"]), tc, s, 1.0)] + ([(CRANE, s, s + P, 1.0)] if s < BIG / 2 else []))
        if x:
            legs.append([(q, x["xs"] + a, x["xs"] + b, d) for q, a, b, d in x["W"]])
            if x["kind"] == "hold":
                hb = self.bid()
                self.held[v.id] = hb
                self.commit(hb, t0, [(HOLD, x["rel"], BIG, 1.0)])
        for W in legs:
            self.commit(self.bid(), t0, self.kept(W))
            self.account([w for w in W if w[2] < BIG / 2])
        load, unload = self.dur(task)
        ramp = [t2 + b for q, a, b, d in WL if q in self.ramp_res and q[0] == "r"]
        live = s is not None and s < BIG / 2
        self.trips.append(dict(id=task["id"], flow=task["flow"], vid=v.id, o=task["o"], d=r["d"], k=r["k"], how=r["how"], t0=t0,
                               start=v.loc, t1=t1, a=r["a"], t2=t2, tc=tc, s=s if live else None, r0=r["r0"] if live else None,
                               F_quay=tc + unload if (s is not None and r["how"] != "direct") else None,
                               F_vessel=s + P if live else None,
                               F_ramp=max(ramp) if task["flow"] == "unload" and ramp else None,
                               F_yard=tc + unload if task["flow"] == "unload" else None, rel=r["rel"],
                               exit=[x["node"], x["xs"], x["kind"]] if x else None))
        task["plan"] = dict(start=v.loc, t1=t1, a=r["a"], t2=t2, vid=v.id)
        v.loc = x["node"] if x else sd["node"]
        self.push(r["rel"], "done", (v.id, task, max(0.0, t2 - r["a"] - load)))


# ---------------------------------------------------------------- one point: config -> layout, network, tasks, calendar -> result
KMH = 1 / 3.6
# Base parameters (base case: the Kassels 2023 Rønne case model; the others as listed in the parameter register)
BASE = dict(v_loaded=2.5 * KMH, v_empty=5.0 * KMH, plat_len=30.0, plat_w=4.86, Lv=110.0, B=9.5,
            hp_s=1800.0, hd_s=1800.0, roro_s=4 * 3600.0, hy_s=1800.0, lift_s=3600.0, sweep_steer_s=120.0, release_frac=0.0)
_NETS = {}


def params(cfg):
    """Parameter table of the occupancy model: occupancy defaults + base + the point's overrides (cfg["p"]). The working day is
    set to 1 h (day_s is used only to convert the simulation horizon)."""
    p = dict(PP.DEFAULTS, **BASE)
    p.update(cfg.get("p") or {})
    return dict(p, day_s=3600.0, days=int(math.ceil(cfg["horizon_h"])) + 1, warmup_days=0)


def get_net(geo, p):
    """Layout (geo = dict(kind, **archetypes parameters)) -> PortNet; cached per process by geometry and section mode."""
    key = json.dumps([geo, p.get("section")], sort_keys=True)
    if key not in _NETS:
        D = A.build(geo["kind"], **{k: v for k, v in geo.items() if k != "kind"})
        f, sha = map_file(A.dumps(D))
        net = PortNet(str(f), sha, p, roles=A.ROLES)
        net.map_sha256 = sha
        _NETS[key] = (D, net)
    return _NETS[key]


def setup(cfg):
    """cfg: geo (layout and geometry; n_cradles is the number of quay slots, all S share the same geometry and only the first S
    are used as cradles), S (number of cradles; 0 = direct lift at the first quay slot), K (number of SPMT units for load-out),
    K_u (units for unloading only, default 0 = unloading also done by the K units), hold (gate holding places Q_h, default 0;
    "inf" = unlimited), lift, fixed, horizon_h, cal ({crane: [[a, b] h...], ramp: [[a, b] h...]}), n_load (number of load-out
    tasks, all released at time 0), n_unload and unload_release_h (number of unloading tasks and their release times), p
    (parameter overrides).
    Returns (D, net, p, tasks, starts, quay slots, calendar (s)); starts cover all K + K_u units, all at the yard saddle rows."""
    p = params(cfg)
    D, net = get_net(cfg["geo"], p)
    W = D["windport"]
    assert cfg["S"] <= len(W["cradles"]), (cfg["S"], len(W["cradles"]))
    assert not cfg.get("n_unload") or W["ramp"], "unloading tasks need a ramp (ramp_at must not be None)"
    rows = W["storage"]
    tasks = [dict(id=j, flow="load", o=rows[j % len(rows)], d=None, B=p["B"], Lv=p["Lv"], release=0.0) for j in range(cfg["n_load"])]
    rel = cfg.get("unload_release_h") or []
    tasks += [dict(id=cfg["n_load"] + j, flow="unload", o=W["ramp"][0], d=rows[-1 - j % len(rows)], B=p["B"], Lv=p["Lv"],
                   release=rel[j] * 3600.0 if j < len(rel) else 0.0) for j in range(cfg.get("n_unload", 0))]
    starts = [net.stops[rows[k % len(rows)]]["node"] for k in range(cfg["K"] + cfg.get("K_u", 0))]
    cal = {k: [(a * 3600.0, b * 3600.0) for a, b in v] for k, v in (cfg.get("cal") or {}).items() if v is not None}
    return D, net, p, tasks, starts, W["cradles"][:max(1, cfg["S"])], cal


def ramp_res(D):
    W = D["windport"]
    return [("r", W["ramp_road"]), ("n", W["ramp"][0])] if W.get("ramp") else []


def exit_node(D):
    """The gate passed when leaving the quay after release (in A1 and A2 the junction of the single lane and the dead-end quay
    front; in A3 gate 2). The gate holding place is attached here."""
    return D["windport"]["gates"][-1]


def yard_node(D):
    """Yard-side idle location: the first two-lane junction after driving out of the single lane from the quay (in A1 and A2 the
    south end of the corridor's single lane, in A3 the south end of corridor 2; the yard junction if the single lane runs all the
    way to the yard)."""
    pre = "corr2" if D["windport"]["kind"] == "A3" else "corr"
    return f"{pre}_C" if f"{pre}_C" in D["nodes"] else f"{pre}_S"


def hold_of(cfg):
    h = cfg.get("hold", 0)
    return math.inf if h == "inf" else int(h)


def simulate(cfg):
    D, net, p, tasks, starts, quay, cal = setup(cfg)
    lift = "direct" if cfg["S"] == 0 else cfg.get("lift", "cradle")
    Ku = cfg.get("K_u", 0)
    sim = PortSim(net, p, cfg["K"] + Ku, tasks, starts, quay, cal, lift, cfg.get("fixed", False), ramp_res(D), record=cfg.get("record", False),
                  exit=exit_node(D), yard=yard_node(D), hold=hold_of(cfg), flows=["load"] * cfg["K"] + ["unload"] * Ku if Ku else None)
    sim.run()
    return net, p, sim, result(cfg, D, net, p, sim, cal)


def run_point(cfg):
    return simulate(cfg)[3]


def w1_port(cfg, D, net, p):
    """Parameters of W1 (from the occupancy model, windport.bound.occupancy_times): cradle mode uses set-down hd_s; direct lift
    counts set-down as 0 and adds release_frac*p before release to the cycle. Returns (Port, occupancy_times). Mixed lifting
    (Corollary 2): occupancy of the cut and the time from leaving the cut to hand-over are taken without set-down (lift from the
    vehicle) - with roadside cradles the quay front is the cut and set-down holds the front, a trip lifted from the vehicle does
    no set-down and occupies less, so tl taken with set-down is no longer a lower bound; c is the cycle without set-down + hd
    (Corollary 2 subtracts hd in its conversion)."""
    W = D["windport"]
    S, lift = cfg["S"], ("direct" if cfg["S"] == 0 else cfg.get("lift", "cradle"))
    hd = 0.0 if lift == "direct" else p["hd_s"]
    pt = dict(p, load_s=p["hp_s"], unload_s=0.0 if lift == "mixed" else hd)
    quay = W["cradles"][:max(1, S)]
    t = WB.occupancy_times(net, pt, W["storage"], quay, p["Lv"], p["B"])
    L = (cfg["cal"]["crane"][0][1] - cfg["cal"]["crane"][0][0]) * 3600.0
    # extra waiting at the quay slot before release, counted on the return side after hand-over
    xr = p.get("release_frac", 0.0) * p["lift_s"] if lift == "direct" else 0.0
    c = t["c"] + (hd if lift == "mixed" else 0.0) + xr
    P = WB.Port(L=L, p=p["lift_s"], S=S, K=cfg["K"], hp=t["hp"], hd=hd, tl=t["tl"], te=t["te"], c=c, ce=t["ce"] + xr, dq=t["dq"],
                Q=cfg["K"], mixed=lift == "mixed", te_occ=t["te_occ"])
    return P, t


def result(cfg, D, net, p, sim, cal):
    """Readings of one point: pieces lifted on board in each crane window (F_vessel inside the window), pieces unloaded in each
    ramp window (F_ramp), F_quay and F_vessel of load-out, W1 (first crane window; empty-system start, preparation time = window
    start) with its terms and the binding term."""
    tr = sim.trips
    out = dict(trips=len(tr), n_vessel=[], n_ramp=[], lifts=[], quay=[], ramp=[])
    for a, b in cal.get("crane") or []:
        out["n_vessel"].append(sum(1 for x in tr if x["F_vessel"] is not None and a - EPS <= x["s"] and x["F_vessel"] <= b + EPS))
    for a, b in cal.get("ramp") or []:
        out["n_ramp"].append(sum(1 for x in tr if x["F_ramp"] is not None and a - EPS <= x["F_ramp"] <= b + EPS))
    out["lifts"] = sorted(round(x["s"], 3) for x in tr if x["F_vessel"] is not None)
    out["quay"] = sorted(round(x["F_quay"], 3) for x in tr if x["F_quay"] is not None and x["s"] is not None)
    out["ramp"] = sorted(round(x["F_ramp"], 3) for x in tr if x["F_ramp"] is not None)
    out["yard"] = sorted(round(x["F_yard"], 3) for x in tr if x["F_yard"] is not None)
    out["exits"] = dict(collections.Counter(x["exit"][2] for x in tr if x["exit"]))
    if cfg["n_load"] and cal.get("crane"):
        P, t = w1_port(cfg, D, net, p)
        G = cal["crane"][0][0]
        tm = WB.terms(P, G)
        b, why = WB.bound(P, G)
        out["w1"] = dict(bound=b, binding="+".join(why), terms={k: (None if v == math.inf else v) for k, v in tm.items()},
                         any_hist=WB.bound(P)[0], cut="|".join(map(str, t["res"])), tl=t["tl"], te=t["te"], c=P.c, dq=t["dq"],
                         k_dagger=WB.k_dagger(P), rate_h=WB.rate(P) * 3600.0)
    # Theorem 3: pieces unloaded per ramp window (S_u = 0, Q = number of unloading vehicles)
    if cfg.get("n_unload") and cal.get("ramp"):
        pu = dict(p, load_s=p["roro_s"], unload_s=p["hy_s"])
        W = D["windport"]
        Ku = cfg.get("K_u") or cfg["K"]
        Kt = cfg["K"] + cfg.get("K_u", 0)
        u = WB.unload_times(net, pu, W["ramp"][0], W["storage"], p["Lv"], p["B"])
        out["thm3"] = dict(bound=[min(WB.unload_terms(b - a, u["rho"], Ku, u["c_u"], u["tl"], u["te"]).values()) for a, b in cal["ramp"]],
                           rho=u["rho"], c_u=u["c_u"], tl=u["tl"], te=u["te"], cut="|".join(map(str, u["res"])))
        # Theorem 4: both flows share one cut (the single lane of A1), K = all vehicles
        if cfg["n_load"] and cal.get("crane") and cfg.get("joint_cut"):
            c = ("r", cfg["joint_cut"])
            P, _ = w1_port(cfg, D, net, p)
            lo = WB.occupancy_times(net, dict(p, load_s=p["hp_s"], unload_s=P.hd), W["storage"], quay_of(D, cfg), p["Lv"], p["B"], cut=c)
            uu = WB.unload_times(net, pu, W["ramp"][0], W["storage"], p["Lv"], p["B"], cut=c)
            g = [WB.joint_gap(no, nu, cfg["S"], 0, Kt, Kt, lo["tl"], uu["tl"], uu["te"], lo["te"], (ao, bo - p["lift_s"] - lo["dq"]),
                              (au + uu["rho"], bu))
                 for (ao, bo), no in zip(cal["crane"], out["n_vessel"]) for (au, bu), nu in zip(cal["ramp"], out["n_ramp"])]
            out["thm4_gap"] = min(g)
    return out


def quay_of(D, cfg):
    return D["windport"]["cradles"][:max(1, cfg["S"])]
