"""E2 (Table 2): maximum in-window delivery of a small instance - optimal schedule with waiting only at the origin (CP-SAT),
reported alongside W1 and the simulation (windport.sim).

Same schedule class, same occupancy windows (PortSim.windows / exit_w -> PortNet.leg, including stop-and-steer and sweep) and
same semantics as the simulation:
  - each trip: empty run, pick-up, loaded run, set-down (direct lift: wait for the crane), release, leave the quay; a vehicle
    waits only at the origin (after loading it occupies the saddle row), at the quay slot (while waiting for release or
    departure it occupies the slot) or at an idle location;
  - on leaving the quay the vehicle goes either to the gate holding place (capacity hold; it stays there until the empty run of
    its next trip, or to the end of the window if there is none) or to the yard side (no occupancy recorded);
  - the occupancy of every leg counts against capacity separately; different legs and trips of the same vehicle are not merged
    (the vehicle body is in one place only); within one leg, windows on the same resource are united;
  - the ship crane lifts only from cradles (cradle mode); with S = 0 it lifts from the vehicle parked at the quay slot, and the
    vehicle is released release_frac*p after the lift starts.
Decisions: which monopiles are lifted on board within the window, assignment to vehicles and order, quay slot, exit target, all
times. Objective: maximise the number of pieces lifted on board in the window [G, G + L] (empty-system start: at time 0 all
vehicles are empty at the yard saddle rows and the cradles are empty). Default number of candidate monopiles W1 + 2: more than
the bound, so that CP-SAT can test W1.
Time is rounded to units of `unit` seconds: window start down, window end up, durations up, cradle occupancy from "arrival
rounded down". An integer solution is therefore feasible in continuous time (conservative); every solution is also checked in
continuous time by the independent checker (windport.check). The optimum does not exceed the continuous-time optimum of the same
schedule class."""
import collections
import math

from ortools.sat.python import cp_model

from exact.model import scale_of
from occupancy.network import EPS
from occupancy.sim import Vehicle
from windport import bound as WB
from windport import sim as WS


def merge(ws):
    """Windows on the same resource within one leg: overlapping ones are united, width takes the max (conservative; equal to or
    stricter than the simulation's merge by booking id)."""
    by = collections.defaultdict(list)
    for r, a, b, d in ws:
        by[r].append([a, b, d])
    out = []
    for r, iv in by.items():
        iv.sort()
        cur = iv[0]
        for a, b, d in iv[1:]:
            if a <= cur[1] + EPS:
                cur = [cur[0], max(cur[1], b), max(cur[2], d)]
            else:
                out.append((r, *cur))
                cur = [a, b, d]
        out.append((r, *cur))
    return out


class Inst:
    """A small instance: the same point config cfg as windport.sim (load-out only, a single crane window); n candidate monopiles
    (default W1 + 2)."""

    def __init__(self, cfg, n=None):
        D, net, p, tasks, starts, quay, cal = WS.setup(cfg)
        assert cfg.get("lift", "cradle") != "mixed" and not cfg.get("n_unload")
        self.cfg, self.D, self.net, self.p, self.quay, self.cal, self.starts = cfg, D, net, p, quay, cal, starts
        self.lift = "direct" if cfg["S"] == 0 else "cradle"
        self.exit, self.yard, self.hold = WS.exit_node(D), WS.yard_node(D), WS.hold_of(cfg)
        self.sim = WS.PortSim(net, p, 1, [], starts[:1], quay, None, self.lift, False, WS.ramp_res(D), exit=self.exit, yard=self.yard,
                              hold=self.hold)
        (self.G, b), = cal["crane"]
        self.L, self.H = b - self.G, b
        P, t = WS.w1_port(cfg, D, net, p)
        bnd, why = WB.bound(P, self.G)
        self.w1 = dict(bound=bnd, binding="+".join(why), terms=WB.terms(P, self.G), any_hist=WB.bound(P)[0], cut="|".join(map(str, t["res"])))
        rows = D["windport"]["storage"]                     # same tasks as the simulation: pile j at saddle row j mod #rows
        self.tasks = [dict(id=j, flow="load", o=rows[j % len(rows)], d=None, B=p["B"], Lv=p["Lv"], release=0.0)
                      for j in range((bnd + 2) if n is None else n)]
        self.targets = ([("hold", self.exit)] if self.hold > 0 else []) + [("yard", self.yard)]
        self._w = {}

    def win(self, loc, j, k):
        key = (loc, j, k)
        if key not in self._w:
            so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr = self.sim.windows(Vehicle(-1, loc), dict(self.tasks[j], d=self.quay[k]))
            self._w[key] = (so, sd, d_so, d_sd, TE, TL, merge(WE), merge(WL), ao, ad, tail_l, clr)
        return self._w[key]

    def exit_w(self, k, target):
        TX, W = self.sim.exit_w(self.net.stops[self.quay[k]]["node"], target)
        return TX, merge(W)


def solve(inst, time_s=60.0, workers=8, seed=0, unit=1.0, hint=None):
    """Return dict(status, best (pieces), bound, trips (continuous time, windport.check format), limit, threads, seed, unit,
    hint, inst). hint: simulation trips (used as a solution hint)."""
    p, T, K, Q = inst.p, inst.tasks, inst.cfg["K"], len(inst.quay)
    N, P = len(T), p["lift_s"]
    ce = lambda x: math.ceil(x / unit - 1e-7)
    fl = lambda x: math.floor(x / unit + 1e-7)
    H = ce(inst.H)
    BIGH = 4 * H
    hp, hd = p["hp_s"], (0.0 if inst.lift == "direct" else p["hd_s"])
    xr = ce(p.get("release_frac", 0.0) * P) if inst.lift == "direct" else 0
    O = inst.targets
    m = cp_model.CpModel()
    nv = lambda name: m.new_int_var(0, BIGH, name)
    pres = [m.new_bool_var(f"p{j}") for j in range(N)]
    t1, t2, tc, rel, xs, relx, harr = ([nv(f"{n}{j}") for j in range(N)] for n in ("t1_", "t2_", "tc_", "r0_", "xs_", "rx_", "ha_"))
    s = [m.new_int_var(ce(inst.G), max(ce(inst.G), fl(inst.H) - ce(P)), f"s_{j}") for j in range(N)]
    z = [[m.new_bool_var(f"z{j}_{k}") for k in range(Q)] for j in range(N)]
    e = [[m.new_bool_var(f"e{j}_{o}") for o in range(len(O))] for j in range(N)]
    by = collections.defaultdict(list)                     # resource -> [(interval, width)]
    crane, cr = [], collections.defaultdict(list)
    for j in range(N):
        m.add(sum(z[j]) == pres[j])
        m.add(sum(e[j]) == pres[j])
        crane.append(m.new_optional_fixed_size_interval_var(s[j], ce(P), pres[j], f"lift{j}"))
        if inst.lift == "direct":
            m.add(s[j] >= tc[j]).only_enforce_if(pres[j])
            m.add(rel[j] == s[j] + xr).only_enforce_if(pres[j])
        else:
            m.add(s[j] >= tc[j] + ce(hd)).only_enforce_if(pres[j])
            m.add(rel[j] == tc[j] + ce(hd)).only_enforce_if(pres[j])
        m.add(xs[j] >= rel[j]).only_enforce_if(pres[j])     # after release the vehicle may wait at the quay slot before leaving
        o_node = inst.net.stops[T[j]["o"]]["node"]
        tx = []
        for k in range(Q):
            so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr = inst.win(o_node, j, k)
            m.add(tc[j] == t2[j] + ce(TL)).only_enforce_if(z[j][k])
            for r, a, b, d in WL:
                by[r].append((m.new_optional_fixed_size_interval_var(t2[j] + fl(a), ce(b) - fl(a), z[j][k], ""), d))
            a0 = nv("")                                     # cradle (direct: quay slot) held from arrival (down) to lift start
            m.add(a0 == t2[j] + fl(TL)).only_enforce_if(z[j][k])
            cr[k].append(m.new_optional_interval_var(a0, nv(""), s[j], z[j][k], ""))
            for o, (kind, node) in enumerate(O):
                TX, WX = inst.exit_w(k, node)
                zo = m.new_bool_var("")
                m.add_bool_and([z[j][k], e[j][o]]).only_enforce_if(zo)
                m.add_bool_or([~z[j][k], ~e[j][o]]).only_enforce_if(~zo)
                for r, a, b, d in WX:
                    by[r].append((m.new_optional_fixed_size_interval_var(xs[j] + fl(a), ce(b) - fl(a), zo, ""), d))
                stop = sd["res"] in {r for r, *_ in WX}
                dend = nv("")                                # slot held to departure (roadside) or departure + clr (pull-in)
                m.add(dend == (xs[j] if stop else xs[j] + ce(clr))).only_enforce_if(zo)
                by[sd["res"]].append((m.new_optional_interval_var(t2[j] + fl(ad), nv(""), dend, zo, ""), d_sd))
                tx.append((zo, ce(TX), fl(TX)))
        m.add(relx[j] == xs[j] + sum(c * v for v, c, _ in tx)).only_enforce_if(pres[j])          # available again: rounded up
        m.add(harr[j] == xs[j] + sum(f * v for v, _, f in tx)).only_enforce_if(pres[j])          # enters hold: rounded down
    m.add_no_overlap(crane)
    for k, iv in cr.items():
        m.add_no_overlap(iv)
    # assignment and order: x[i, j] = the same vehicle does j right after i; st[v, j] = j is the first trip of vehicle v;
    # ns[j] = j is the last trip of its vehicle
    x = {(i, j): m.new_bool_var(f"x{i}_{j}") for i in range(N) for j in range(N) if i != j}
    st = {(v, j): m.new_bool_var(f"st{v}_{j}") for v in range(K) for j in range(N)}
    ns = [m.new_bool_var(f"ns{j}") for j in range(N)]
    for j in range(N):
        m.add(sum(x[i, j] for i in range(N) if i != j) + sum(st[v, j] for v in range(K)) == pres[j])
        m.add(sum(x[j, i] for i in range(N) if i != j) + ns[j] == pres[j])
        for i in range(N):
            if i != j:
                m.add(t1[j] >= relx[i]).only_enforce_if(x[i, j])
    for v in range(K):
        m.add(sum(st[v, j] for j in range(N)) <= 1)
    for v in range(K):                                       # vehicles with the same start are interchangeable: lower id first
        for v2 in range(v + 1, K):
            if inst.starts[v] == inst.starts[v2]:
                m.add(sum(st[v, j] for j in range(N)) >= sum(st[v2, j] for j in range(N)))
    for j in range(N):                                       # piles in the same saddle row are interchangeable: lower id first
        for j2 in range(j + 1, N):
            if T[j]["o"] == T[j2]["o"]:
                m.add(pres[j] >= pres[j2])
                m.add(s[j] <= s[j2]).only_enforce_if(pres[j2])
    hold_iv = []
    oh = next((o for o, (kind, _) in enumerate(O) if kind == "hold"), None)
    for j in range(N):
        # gate holding place: from arrival until the vehicle's next empty run starts (end of window if none)
        if oh is not None:
            he = nv("")
            for i in range(N):
                if i != j:
                    m.add(he == t1[i]).only_enforce_if(x[j, i])
            m.add(he == H).only_enforce_if(ns[j])
            hold_iv.append(m.new_optional_interval_var(harr[j], nv(""), he, e[j][oh], ""))
        o_node = inst.net.stops[T[j]["o"]]["node"]
        src = collections.defaultdict(list)                  # start location of the empty run -> indicators
        for i in range(N):
            if i == j:
                continue
            for o, (kind, node) in enumerate(O):
                w = m.new_bool_var("")
                m.add_bool_and([x[i, j], e[i][o]]).only_enforce_if(w)
                m.add_bool_or([~x[i, j], ~e[i][o]]).only_enforce_if(~w)
                src[node].append(w)
        for v in range(K):
            src[inst.starts[v]].append(st[v, j])
        os_, so_res, d_so0, tail0 = nv(f"os{j}"), None, None, None
        for loc, lits in sorted(src.items()):
            y = m.new_bool_var("")
            m.add(y == sum(lits))
            so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr = inst.win(loc, j, 0)
            so_res, d_so0, tail0 = so["res"], d_so, tail_l
            m.add(t2[j] >= t1[j] + ce(TE + hp)).only_enforce_if(y)
            m.add(os_ == t1[j] + fl(ao)).only_enforce_if(y)
            for r, a, b, d in WE:
                by[r].append((m.new_optional_fixed_size_interval_var(t1[j] + fl(a), ce(b) - fl(a), y, ""), d))
        oend = nv("")
        m.add(oend == t2[j] + ce(tail0))
        by[so_res].append((m.new_optional_interval_var(os_, nv(""), oend, pres[j], f"o{j}"), d_so0))
    if hold_iv and inst.hold != math.inf:
        m.add_cumulative(hold_iv, [1] * len(hold_iv), int(inst.hold))
    cap = inst.sim.cap
    S_ = scale_of([cap[r] for r in by] + [d for iv in by.values() for _, d in iv])
    for r, iv in by.items():
        if sum(d for _, d in iv) <= cap[r] + EPS:
            continue
        m.add_cumulative([a for a, _ in iv], [round(d * S_) for _, d in iv], round(cap[r] * S_))
    m.maximize(sum(pres))
    if hint:
        _hint(m, inst, hint, pres, t1, t2, s, z, e, x, st, xs, unit)
    sol = cp_model.CpSolver()
    sol.parameters.max_time_in_seconds = time_s
    sol.parameters.num_workers = workers
    sol.parameters.random_seed = seed
    status = sol.solve(m)
    out = dict(status=sol.status_name(status), bound=sol.best_objective_bound, best=0, trips=[], limit=time_s, threads=workers, seed=seed,
               unit=unit, hint=bool(hint), inst=inst, wall=sol.wall_time)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return out
    out["best"] = int(round(sol.objective_value))
    for v in range(K):
        j, loc = next((j for j in range(N) if sol.value(st[v, j])), None), inst.starts[v]
        while j is not None:
            k = next(k for k in range(Q) if sol.value(z[j][k]))
            o = next(o for o in range(len(O)) if sol.value(e[j][o]))
            so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr = inst.win(loc, j, k)
            a1, a2, sj, xj = (sol.value(q[j]) * unit for q in (t1, t2, s, xs))
            tcj = a2 + TL
            r0 = sj + p.get("release_frac", 0.0) * P if inst.lift == "direct" else tcj + hd
            TX = inst.exit_w(k, O[o][1])[0]
            out["trips"].append(dict(id=T[j]["id"], flow="load", vid=v, o=T[j]["o"], d=inst.quay[k], k=k, how=inst.lift, t1=a1, a=a1 + TE,
                                     t2=a2, tc=tcj, s=sj, r0=r0, F_quay=None if inst.lift == "direct" else tcj + hd, F_vessel=sj + P,
                                     F_ramp=None, F_yard=None, rel=xj + TX, exit=[O[o][1], xj, O[o][0]]))
            loc = O[o][1]
            j = next((i for i in range(N) if i != j and sol.value(x[j, i])), None)
    return out


def _hint(m, inst, trips, pres, t1, t2, s, z, e, x, st, xs, unit):
    """Simulation trips (those lifted on board within the window) as a solution hint."""
    O = [kind for kind, _ in inst.targets]
    by_v = collections.defaultdict(list)
    for tr in trips:
        if tr["F_vessel"] is not None and tr["exit"] and tr["id"] < len(inst.tasks):   # same id = same saddle row
            by_v[tr["vid"]].append(tr)
    idx = {(v, tr["id"]): tr["id"] for v, lst in by_v.items() for tr in lst}
    on = set(idx.values())
    for q in range(len(inst.tasks)):
        m.add_hint(pres[q], q in on)
    prev = {}
    for v, lst in sorted(by_v.items()):
        seq = [idx[(v, tr["id"])] for tr in sorted(lst, key=lambda q: q["t1"]) if (v, tr["id"]) in idx]
        for n, q in enumerate(seq):
            prev[q] = ("s", v) if n == 0 else ("x", seq[n - 1])
        for tr in lst:
            q = idx.get((v, tr["id"]))
            if q is None:
                continue
            for var, val in ((t1[q], tr["t1"]), (t2[q], tr["t2"]), (s[q], tr["s"]), (xs[q], tr["exit"][1])):
                m.add_hint(var, round(val / unit))
            for kk in range(len(inst.quay)):
                m.add_hint(z[q][kk], kk == tr["k"])
            for o, kind in enumerate(O):
                m.add_hint(e[q][o], kind == tr["exit"][2])
    for (i, q), var in x.items():
        m.add_hint(var, prev.get(q) == ("x", i))
    for (v, q), var in st.items():
        m.add_hint(var, prev.get(q) == ("s", v))
