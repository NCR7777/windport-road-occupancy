"""CP-SAT model of the E2 small cases under the conservative lifting rule (header of windport/lift.py). windport/cpsat.py
is unchanged; Inst, merge and _hint are reused as they are, solve is copied, and two constraints are added for each
quay-position choice: for a direct lift, lift start ≥ loaded departure + vehicle body clear of the road (clear); during
[s, s + d] after the lift starts, the resources under the load (lift.under_res, following the incoming direction of this
pile's saddle row) are exclusive (under; direct lifting d = max(t_u, x·p), with the share of the vehicle standing at the
lifting position topped up to the full segment capacity; cradle mode d = t_u). The departure of the delivering vehicle and
the occupancy of the next arriving vehicle on segments intersecting the area under the load are excluded by the same
cumulative constraints. With clear = under = False this is the same model as windport.cpsat.solve (under also applies in
cradle mode)."""
import collections
import math

from ortools.sat.python import cp_model

from exact.model import scale_of
from occupancy.network import EPS
from windport import cpsat as CP
from windport import lift as LF

Inst = CP.Inst


def solve(inst, time_s=60.0, workers=8, seed=0, unit=1.0, hint=None, clear=True, under=True):
    """Returns dict(status, best (piles), bound, trips (continuous time, windport.check format), limit, threads, seed, unit, hint,
    inst). hint: simulation trips (used as an initial solution hint)."""
    p, T, K, Q = inst.p, inst.tasks, inst.cfg["K"], len(inst.quay)
    N, P = len(T), p["lift_s"]
    ce = lambda x: math.ceil(x / unit - 1e-7)
    fl = lambda x: math.floor(x / unit + 1e-7)
    H = ce(inst.H)
    BIGH = 4 * H
    hp, hd = p["hp_s"], (0.0 if inst.lift == "direct" else p["hd_s"])
    xr = ce(p.get("release_frac", 0.0) * P) if inst.lift == "direct" else 0
    tu = ce(p.get("lift_tu", LF.TU) * P) if under else 0
    dur = max(tu, xr) if inst.lift == "direct" else tu
    O = inst.targets
    m = cp_model.CpModel()
    nv = lambda name: m.new_int_var(0, BIGH, name)
    pres = [m.new_bool_var(f"p{j}") for j in range(N)]
    t1, t2, tc, rel, xs, relx, harr = ([nv(f"{n}{j}") for j in range(N)] for n in ("t1_", "t2_", "tc_", "r0_", "xs_", "rx_", "ha_"))
    s = [m.new_int_var(ce(inst.G), max(ce(inst.G), fl(inst.H) - ce(P)), f"s_{j}") for j in range(N)]
    z = [[m.new_bool_var(f"z{j}_{k}") for k in range(Q)] for j in range(N)]
    e = [[m.new_bool_var(f"e{j}_{o}") for o in range(len(O))] for j in range(N)]
    by = collections.defaultdict(list)                     # resource → [(interval, width)]
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
        m.add(xs[j] >= rel[j]).only_enforce_if(pres[j])     # may wait at the quay position after release
        if inst.lift == "direct" and under and dur > 0:      # under the load: leave ≥ s + d (as simulated)
            m.add(xs[j] >= s[j] + dur).only_enforce_if(pres[j])
        o_node = inst.net.stops[T[j]["o"]]["node"]
        tx = []
        for k in range(Q):
            so, sd, d_so, d_sd, TE, TL, WE, WL, ao, ad, tail_l, clr = inst.win(o_node, j, k)
            m.add(tc[j] == t2[j] + ce(TL)).only_enforce_if(z[j][k])
            if inst.lift == "direct" and clear:          # lift once the body is clear of the road
                m.add(s[j] >= t2[j] + ce(LF.clear_end(WL, TL))).only_enforce_if(z[j][k])
            if under and dur > 0:                         # under-load resources exclusive in [s, s + d]
                for u in LF.under_res(inst.net, inst.quay[k], p["Lv"], LF.arrive_fw(inst.net, o_node, sd["node"])):
                    w = inst.sim.cap[u] - (d_sd if inst.lift == "direct" and u == sd["res"] else 0.0)
                    if w > EPS:
                        by[u].append((m.new_optional_fixed_size_interval_var(s[j], dur, z[j][k], ""), w))
            for r, a, b, d in WL:
                by[r].append((m.new_optional_fixed_size_interval_var(t2[j] + fl(a), ce(b) - fl(a), z[j][k], ""), d))
            a0 = nv("")                                     # cradle / quay position held from arrival (floor) to lift start
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
                dend = nv("")                                # quay position held until departure (+ clr if drive-in)
                m.add(dend == (xs[j] if stop else xs[j] + ce(clr))).only_enforce_if(zo)
                by[sd["res"]].append((m.new_optional_interval_var(t2[j] + fl(ad), nv(""), dend, zo, ""), d_sd))
                tx.append((zo, ce(TX), fl(TX)))
        m.add(relx[j] == xs[j] + sum(c * v for v, c, _ in tx)).only_enforce_if(pres[j])          # free again: ceil
        m.add(harr[j] == xs[j] + sum(f * v for v, _, f in tx)).only_enforce_if(pres[j])          # holding place: floor
    m.add_no_overlap(crane)
    for k, iv in cr.items():
        m.add_no_overlap(iv)
    # dispatch and precedence: x[i, j] = the same vehicle does j right after i; st[v, j] = j is the first trip of vehicle v;
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
    for v in range(K):                                       # same-start vehicles interchangeable: lower index first
        for v2 in range(v + 1, K):
            if inst.starts[v] == inst.starts[v2]:
                m.add(sum(st[v, j] for j in range(N)) >= sum(st[v2, j] for j in range(N)))
    for j in range(N):                                       # same-row piles interchangeable: lower index first
        for j2 in range(j + 1, N):
            if T[j]["o"] == T[j2]["o"]:
                m.add(pres[j] >= pres[j2])
                m.add(s[j] <= s[j2]).only_enforce_if(pres[j2])
    hold_iv = []
    oh = next((o for o, (kind, _) in enumerate(O) if kind == "hold"), None)
    for j in range(N):
        if oh is not None:                                   # gate holding place: until next empty departure (or H)
            he = nv("")
            for i in range(N):
                if i != j:
                    m.add(he == t1[i]).only_enforce_if(x[j, i])
            m.add(he == H).only_enforce_if(ns[j])
            hold_iv.append(m.new_optional_interval_var(harr[j], nv(""), he, e[j][oh], ""))
        o_node = inst.net.stops[T[j]["o"]]["node"]
        src = collections.defaultdict(list)                  # empty-departure location → indicators
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
        CP._hint(m, inst, hint, pres, t1, t2, s, z, e, x, st, xs, unit)
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
