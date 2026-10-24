"""Conservative lifting rule: conservative lifting semantics (windport/lift.py), independent checker (windport/check_lift.py), CP-SAT kept in
sync (windport/cpsat_lift.py), the two-block chain enumeration variant (windport/exact_chain_lift.py) and the bound W″_lift under the new
semantics."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_extra as X                       # noqa: E402
from windport import bound3 as B3                # noqa: E402
from windport import bound_lift as BL            # noqa: E402
from windport import bound_dead as BD            # noqa: E402
from windport import check as C                  # noqa: E402
from windport import check_lift as CL            # noqa: E402
from windport import exact_chain as XC           # noqa: E402
from windport import exact_chain_lift as XL      # noqa: E402
from windport import lift as LF                  # noqa: E402
from windport import sim as S                    # noqa: E402
from windport import sim2 as S2                  # noqa: E402

H = 3600.0


def run(c, new=True):
    if new:
        with LF.installed():
            return S2.simulate2(c)[:3]
    return S2.simulate2(c)[:3]


def checks(c, net, p, sim):
    D, _, _, _, starts, quay, cal = S2.setup2(c)
    g, y = S2.idle_nodes(D)
    a = (net, p, sim.trips, starts, quay, cal, c.get("fixed", False), S.ramp_res(D), S.hold_of(c), sim.H)
    return C.check(*a, gate=g, yard=y), CL.check(*a, gate=g, yard=y)


def port_h(c, sim):
    ls = sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)
    return (ls[c["n_load"] - 1] - c["cal"]["crane"][0][0] * H) / H


def test_switches_off_reproduce_portsim():
    """Both switches off: identical to PortSim trip by trip for direct lifting, mixed lifting, convoy dispatch and x > 0."""
    for sc, m, arr, K, x in [("lane", "on_road", "S0", 2, 0.0), ("base", "pull_in", "S3m", 3, 0.5), ("fastcrane", "pull_in", "S3m", 2, 1.0)]:
        for rule in ("fcfs", "convoy"):
            c = X.port_cfg(sc, m, arr, K, 10, 0, rule, p_extra=dict(release_frac=x))
            c2 = dict(c, p=dict(c["p"], lift_clear=False, lift_under=False))
            assert run(c, False)[2].trips == run(c2)[2].trips, (sc, m, arr, K, x, rule)


def test_cradle_mode_with_tu_zero_unaffected():
    """With t_u = 0, FCFS dispatch in cradle mode (lifting from the cradle) is unaffected by the new semantics and identical to PortSim trip
    by trip; with the default t_u = 0.05 p the on-road cradle case changes and passes the new checker.
    Convoy dispatch is also identical in these two cases, but this is not a general result: in cradle mode the convoy rule itself changed
    through the post-yield comparison (14 of the 60 cases with t_u = 0, x = 0 differ from the original semantics, all pull-in with S = 3);
    the t_u sensitivity and the x scan use FCFS only and are unaffected."""
    for sc, m, arr, K in [("lane", "pull_in", "S1", 2), ("base", "on_road", "S3", 4)]:
        for rule in ("fcfs", "convoy"):
            c = X.port_cfg(sc, m, arr, K, 10, 0, rule, p_extra=dict(release_frac=1.0, lift_tu=0.0))
            assert run(c, False)[2].trips == run(c)[2].trips
    c = X.port_cfg("lane", "on_road", "S1", 2, 10, 0)
    net, p, sim = run(c)
    assert sim.trips != run(c, False)[2].trips and checks(c, net, p, sim)[1]["ok"]
    assert LF.TU == CL.TU == 0.05


def test_core_direct_lift_and_bound():
    """Core instance (long single lane 1 km/h, on-road, direct lifting, K = 2, Q_h = 0, 10 piles): FCFS 16.6575 h with t_u = 0.05 p and
    16.2075 h with t_u = 0, both equal to the L″* given by W″_lift (rule-independent lower bound); the checker passes. The schedule under the
    original semantics is reported by the new checker (lift started before the vehicle body left the road) and still passes the original checker."""
    for tu, want in ((None, 16.6575), (0.0, 16.2075)):
        c = X.port_cfg("lane", "on_road", "S0", 2, 10, 0, p_extra=None if tu is None else dict(lift_tu=tu))
        net, p, sim = run(c)
        old, new = checks(c, net, p, sim)
        assert old["ok"] and new["ok"] and new["n_clear"] == 10
        ph = port_h(c, sim)
        assert abs(ph - want) < 1e-4
        lo, hi = B3.lstar(BL.wfn_lift(c, dict(BL.lift_parts(c), G=24 * H)), 10)
        assert lo / H <= ph + 1e-6 and ph - lo / H < 1e-3
    net0, p0, sim0 = run(c, False)
    old0, new0 = checks(c, net0, p0, sim0)
    assert old0["ok"] and not new0["ok"] and any("lift started before the vehicle body left the road" in e for e in new0["errors"])


def test_under_load_violation_reported():
    """A vehicle under the suspended load during a lift must be reported: with the under rule switched off, schedules lifting from the vehicle
    (pull-in S = 3 mixed lifting, x = 1) and from the cradle (on-road S = 1 cradle) are both reported; they pass under the default semantics."""
    for args in (("fastcrane", "pull_in", "S3m", 2, dict(release_frac=1.0)), ("lane", "on_road", "S1", 2, {})):
        sc, m, arr, K, px = args
        c = X.port_cfg(sc, m, arr, K, 10, 0, p_extra=px)
        _, new = checks(c, *run(c))
        assert new["ok"] and new["n_under"] > 0
        c2 = dict(c, p=dict(c["p"], lift_under=False))
        _, bad = checks(c2, *run(c2))
        assert not bad["ok"] and any("under the load" in e for e in bad["errors"]), args


def test_under_res_matches_checker():
    """The under-load resources set by the simulation and by the checker are the same (on-road, pull-in, sectioned apron; both approach
    directions)."""
    for m in ("on_road", "pull_in"):
        for sec in (None, "stops"):
            c = X.port_cfg("base", m, "S3m", 2, 3, 0, p_extra=dict(section=sec) if sec else None)
            D, net, p, *_ = S2.setup2(c)
            for sid in D["windport"]["cradles"]:
                for fw in (True, False):
                    assert sorted(LF.under_res(net, sid, p["Lv"], fw)) == sorted(CL.under(net, sid, p["Lv"], fw))
                o, d = net.stops[D["windport"]["storage"][0]]["node"], net.stops[sid]["node"]
                assert LF.arrive_fw(net, o, d) == CL.arrive_fw(net, o, d)


def test_bound_order_and_per_pile():
    """W″_lift ≤ W″_clear (bound_dead signed = "clear") ≤ W″ (not generalised), and W″_lift(T_j) ≥ j per pile."""
    for sc, m, arr, K in [("lane", "on_road", "S3m", 2), ("lane", "pull_in", "S1m", 3), ("base", "pull_in", "S0", 1), ("longslow", "on_road", "S0", 4)]:
        c = X.port_cfg(sc, m, arr, K, 10, 0)
        G = 24 * H
        fl_ = BL.wfn_lift(c, dict(BL.lift_parts(c), G=G))
        fc = BD.wfn4(c, dict(BD.parts4(c, signed="clear"), G=G))
        f0 = BD.wfn4(c, dict(BD.parts4(c), G=G))
        for L in (2 * H, 6 * H, 10 * H, 15 * H, 30 * H):
            assert fl_(L) <= fc(L) <= f0(L), (sc, m, arr, K, L)
        net, p, sim = run(c)
        T = sorted(x["F_vessel"] - G for x in sim.trips if x["F_vessel"] is not None)[:10]
        assert all(fl_(t) >= j for j, t in enumerate(T, 1))


def test_exact_chain_lift():
    """With t_u = 0 and direct lifting identical to exact_chain; for direct and mixed lifting with t_u = 0, 1 the exact values never exceed
    W″ under the new semantics (experiments/windport_exact_conservative.lift_bound)."""
    import windport_exact_conservative as E
    for args in [(2, 0, 1, 1, 1, 2, 2, 2, 1, 1, 0, 10, 1), (3, 0, 2, 1, 3, 2, 2, 2, 1, 2, 4, 12, 2)]:
        assert XL.max_delivery(*args) == XC.max_delivery(*args)
    for K, S_, Qs in [(2, 1, 1), (3, 2, 2), (2, 2, 1), (2, 0, 1), (3, 0, 2)]:
        for tu in (0, 1):
            x = dict(K=K, S=S_, Qs=Qs, hp=1, a1=1, a2=2, e=2, o=1, hd=2, p=1, G=4, L=12, tu=tu)
            n = XL.max_delivery(K, S_, Qs, 1, 1, 2, 2, 2, 2, 1, 4, 12, 1, mixed=S_ > 0, tu=tu)
            assert n <= E.lift_bound(x)[0], x


def test_cpsat_lift():
    """E2 small cases (direct lifting, on-road cradle): the CP-SAT solution under the new semantics passes the new checker; its optimum is not
    larger than that of the original-semantics model."""
    import windport_e2 as E2
    from windport import cpsat as CP
    from windport import cpsat_lift as CPL
    for key in ("on_road|lane|K2|S0|L5|G1|H0", "on_road|lane|K2|S1|L5|G1|H0"):
        c = E2.cfg_of(key)
        with LF.installed():
            inst = CPL.Inst(c)
            out = CPL.solve(inst, 30.0, 4, 0, 1.0)
        assert out["trips"], key
        D, net, p, _, starts, quay, cal = S.setup(c)
        ck = CL.check(net, p, out["trips"], starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), inst.H)
        assert ck["ok"], (key, ck["errors"])
        old = CP.solve(CP.Inst(c), 30.0, 4, 0, 1.0)
        assert out["best"] <= old["best"], key


def test_random_regressions_pass_checker():
    """Two kinds of cases from the dead segment of the random regression that once failed the new checker: A2 cradle with 60 s set-down (lift
    started before the window of the delivering vehicle's loaded leg on a junction under the load had ended), and A1 convoy dispatch with
    direct lifting (a yielded vehicle rebooked its departure before the under-load closure ended). After the fix they pass and stay within
    W″_lift per pile."""
    import windport_random_conservative as R
    with LF.installed():
        for i in (8650, 18518):
            r = R.work(("dead", i))
            assert r["why"] == "" and r["n"] > 0, (i, r)


def test_round3_cradle_bound_equals_fcfs():
    """In cradle mode ε_U (the delivering vehicle leaving the area under the load) tightens the handover counting interval; for the core
    instance with cradle S = 1, L″_lift* equals FCFS exactly, 18.6425 h."""
    c = X.port_cfg("lane", "on_road", "S1", 2, 10, 0)
    _, _, sim = run(c)
    G = c["cal"]["crane"][0][0] * H
    w = dict(BL.lift_parts(c), G=G)
    assert abs(w["eps_u"] - 54.0) < 1e-6
    ls = sorted(t["F_vessel"] for t in sim.trips if t["F_vessel"] is not None)
    assert abs((ls[9] - G) / H - 18.6425) < 1e-4
    assert abs(B3.lstar(BL.wfn_lift(c, w), 10)[0] / H - 18.6425) < 1e-3


def test_round3_convoy_relift_and_gate_span():
    """Convoy dispatch: a vehicle lifting from the cradle after yielding (lift withdrawn and rebooked) passes the new checker, and yielding
    does occur; with the gate span, a gate holding place still in use is reported by the checker as lying under the load."""
    c = X.port_cfg("longslow", "pull_in", "S3", 2, 10, 0, rule="convoy")
    net, p, sim = run(c)
    assert sim.bumps > 0
    D, _, _, _, starts, quay, cal = S2.setup2(c)
    g, y = S2.idle_nodes(D)
    assert CL.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)["ok"]
    c = X.port_cfg("longslow", "pull_in", "S1", 3, 10, 1, p_extra=dict(lift_span="gate"))
    net, p, sim = run(c)
    D, _, _, _, starts, quay, cal = S2.setup2(c)
    ck = CL.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
    assert not ck["ok"] and any("('b', 'hold', 0)" in e for e in ck["errors"])


def test_round4_cradle_dead_when_crane_full():
    """The cradle branch is judged dead when it is booked out in the crane gaps and the cradle is held by a pile that can never be lifted:
    the vehicle returns to idle at once and the shared fleet still serves unloading. E5 base port, pull-in, shared fleet without priority,
    K_t = 2, x = 0, continuous opening: 24 loaded, 6 unloaded (same as the original semantics; missing the dead state gives 0 unloaded)."""
    import windport_runs as T
    key = "kind=A1|scen=base|mode=pull_in|lift=cradle|rule=fcfs|fleet=plain|Kt=2|x=0.0|tide=cont|roro=3.0|L=24|S=1|G=24"
    with LF.installed():
        r = T.run_one("e5", key)
    assert (r["sim"], r["n_ramp"]) == (24, 6), r
