"""Simulation batch with the additional analyses for the offshore-wind marshalling-port paper. The occupancy/, bounds/ and exact/
modules are unchanged; the new semantics live in windport/sim3.py, check3.py and bound3.py. Base case: gate holding places Q_h = 0;
with direct lifting the vehicle is released when the lift starts (x = 0); jacking-up and set-down 30 min each.

--part port   Extra columns of Table 5 and the cost table: A1 (Layout 1) × the five scenarios (as in Table 5) × cradle mode ×
              lifting arrangement (S = 0 direct lift; S = 1, 3 cradles; S = 1, 3 mixed lifting) × K = 1–8 × vessel load
              n_v = 3, 5, 10 × gate holding places Q_h = 0, 1, unlimited × representation: road occupancy FCFS / road occupancy
              convoy dispatch / cut as a single resource (windport/sim3.py, Q_h = 0, unlimited). The vessel crane opens at
              G = 24 h for 200 h; port time to load n_v piles = completion of lift n_v − G. FCFS points also get the
              rule-independent port-time lower bound L*(n_v) (windport/bound3.py); every road-occupancy point checks
              W′(port time) ≥ n_v.
--part fix    Fixed-duration representation of the mixed-lifting rows (Table 5, columns K_ref = 1–4): same calibration as E3
              (both speeds multiplied by 1/f so that at K_ref the port time to load 10 piles equals the road-occupancy value),
              A1 × five scenarios × cradle mode × S = 1, 3 mixed lifting × K_ref = 1–4, each for K = 1–8.
--part mix6   Mixed-lifting rows of Table 6 and Fig. 6: the E4 grid (A1, A2, A3 × base / long single lane 1 km/h × cradle
              mode × L = 12 h × K = 1–10 × S = 1–6 × G = 24 h × FCFS / convoy) with lifting mode mixed
              (windport_runs.run_one, part = e4).
--part sens   Three extra rows of Appendix C: empty vehicle length 60 m, lateral clearance 2, 3 m, longitudinal clearance
              10, 20 m, each applied to the reduced (a) E1, (b) E4, (c) E3 grids of the sens part; the base row is taken from
              the submitted results/runs/sens (par = none).
--part pub    Reproduction of published project figures: (1) Rønne load-out: A1, storage–quay 250 m (Kassels Appendix D,
              storage area → quayside location), K = 1, 2, vessel load 3 piles, preparation before the crane opens G = 12 h
              (installation vessel released half a day early), S = 0 direct lift / S = 1, 2 mixed lifting (TO1, TO2) /
              S = 1, 2, 3 cradles; the same is also run on the base geometry (600 m). (2) Rønne unloading: A1, quay–storage
              400 m, K = 1, 2, unloading 3 piles, ramp always open, RoRo 3, 4, 5 h. (3) Eemshaven unloading per tide: A1 base
              geometry, K = 1, 2, tidal window 4, 5, 6 h (period 12.42 h, 4 tides), ramp operation ρ (RoRo work on board)
              1.5–4 h, 3 piles released per tide; records the piles unloaded per tide and the Theorem 3 upper bound.
              The Rønne geometry matches the route lengths of Kassels Appendix D (saddle rows → cradle position, shortest 250 m:
              corridor 150 m; ramp → saddle rows, shortest 405 m: corridor 250 m, 1 cradle position, ramp after the first
              cradle position); each row also records the route length route_m. (1) also runs "Rønne handling": pick and
              place per the mode of Kassels Fig. 19 (loading from the vehicle 2 h = jacking h_p, loading from a stand
              2.5 h = h_p + set-down h_d, hence h_p = 2 h, h_d = 0.5 h; driving counted separately by distance, as the
              process + transport of Kassels §4.3), and computes the port time under "Kassels' lifting order" (first lift the
              pile on the vehicle while the vehicle immediately fetches the third pile, then lift the pile on the stand).
              (2) unloading is split further: saddle set-down h_y = 30 min / 0 × steering stop yes / no.
--part mixx   Dependence of mixed lifting and direct lifting on the vehicle release time x. (a) Port time: A1 × base / long
              corridor / long single lane / crane 0.5 h × cradle mode × S = 0 direct lift, S = 1, 3 mixed lifting × K = 1–8
              × x = 0, 0.25, 0.5, 0.75, 1 (cradle lifting does not depend on x; taken from the port part); (b) window
              delivery: the A1 subgrid of E4 (base / long single lane × cradle mode × L = 12 h × G = 24 h × K = 1–10 × S = 0
              direct lift, S = 1, 3 mixed lifting) × x = 0.25–1 (x = 0 is E4 and mix6).
Output results/windport_extra_<part>_<config hash>/: config.json (parameters, grid, SHA-256 of inputs and code), progress.json,
points/ (one JSON per point, resume cache), points.csv (no wall-clock times).
Run: .venv/Scripts/python.exe experiments/windport_extra.py --part port --procs 22 --slots DIR
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap, write_json      # noqa: E402
from windport import bound3 as B3                                # noqa: E402
from windport import check as C                                  # noqa: E402
from windport import check3 as C3                                # noqa: E402
from windport import sim as S                                    # noqa: E402
from windport import sim2 as S2                                  # noqa: E402
from windport import sim3 as S3                                  # noqa: E402
import windport_runs as T                                        # noqa: E402

KMH = 1 / 3.6
TIDE = 12.4206
CODE = ["windport/sim.py", "windport/sim2.py", "windport/sim3.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py",
        "windport/check.py", "windport/check3.py", "windport/archetypes.py", "windport/shipyard.py", "occupancy/sim.py", "occupancy/network.py",
        "occupancy/params.py", "occupancy/tasks.py", "exact/check.py", "experiments/windport_runs.py", "experiments/windport_extra.py"]
INPUTS = ["data/register/parameters.csv"]
ARR = dict(S0=(0, "direct"), S1=(1, "cradle"), S1m=(1, "mixed"), S3=(3, "cradle"), S3m=(3, "mixed"))
SENS3 = dict(platlen=("plat_len", [60.0]), latc=("lat_clear", [2.0, 3.0]), longc=("long_clear", [10.0, 20.0]))
PUB = dict(out_geo=dict(ronne=dict(dist_m=150.0, corridor_m=100.0), base={}), in_geo=dict(ronne=dict(dist_m=250.0, corridor_m=200.0, n_cradles=1)),
           out_arr=["S0", "S1", "S1m", "S2", "S2m", "S3"], K=[1, 2], n_out=3, G_out=12, roro_in=[3.0, 4.0, 5.0], n_in=3,
           tide_L=[4.0, 5.0, 6.0], rho=[1.5, 2.0, 2.5, 3.0, 3.5, 4.0], tides=4, per_tide=3,
           hand=dict(base={}, ronne=dict(hp_s=7200.0, hd_s=1800.0)), in_var=dict(base={}, hy0=dict(hy_s=0.0), nosteer=dict(sweep_steer_s=None),
                                                                               both=dict(hy_s=0.0, sweep_steer_s=None)))
XS = [0.0, 0.25, 0.5, 0.75, 1.0]
GRIDS = dict(
    port=dict(title="Table 5 extra columns and cost table: port time (n_v = 3, 5, 10)", scen=T.SC5, arr=list(ARR), K=list(range(1, 9)), n_v=[3, 5, 10],
              hold=[0, 1, "inf"], rep=["fcfs", "convoy", "cut"], cut_hold=[0, "inf"], G=24, open_h=200),
    fix=dict(title="Table 5 mixed-lifting rows, fixed-duration representation (K_ref = 1–4)", scen=T.SC5, arr=["S1m", "S3m"], kref=[1, 2, 3, 4], K=list(range(1, 9)), n_v=10,
             G=24, open_h=200, bisect=40),
    mix6=dict(title="Table 6 / Fig. 6 mixed-lifting rows (E4 grid, mixed)", kinds=["A1", "A2", "A3"], scen=["base", "lane"], L=[12], K=list(range(1, 11)),
              S=list(range(1, 7)), G=[24], rule=["fcfs", "convoy"]),
    sens=dict(title="Appendix C extra rows: empty vehicle length, lateral and longitudinal clearance", levels=SENS3, sub=T.GRIDS["sens"], base_dir="results/runs/sens"),
    pub=dict(title="Published project figures (Rønne load-out and unloading, Eemshaven per tide)", **PUB),
    mixx=dict(title="Release time x: mixed vs direct lifting", x=XS, port=dict(scen=["base", "longslow", "lane", "fastcrane"], arr=["S0", "S1m", "S3m"],
                                                                         K=list(range(1, 9)), n_v=10),
              win=dict(scen=["base", "lane"], L=12, G=24, K=list(range(1, 11)), S=[0, 1, 3], x=XS[1:])),
)


def port_cfg(sc, mode, arr, K, n_v, hold, rule="fcfs", fixed=False, p_extra=None, geo_extra=None, G=24, open_h=200):
    """One port-time point (as e3_cfg of E3: A1, 6 cradle positions, vessel crane open from G for open_h, n_v piles released at
    time 0)."""
    s = T.SCEN[sc]
    Sn, lift = ARR[arr] if arr in ARR else (int(arr[1]), "mixed" if arr.endswith("m") else ("direct" if arr == "S0" else "cradle"))
    geo = dict(dict(kind="A1", n_cradles=6, cradle_mode=mode), **s.get("geo", {}), **(geo_extra or {}))
    p = dict(s.get("p", {}), **(p_extra or {}))
    return dict(geo=geo, p=p, S=Sn, K=K, lift=lift, horizon_h=G + open_h, cal=dict(crane=[[G, G + open_h]]), n_load=n_v, fixed=fixed,
                hold=hold, rule=rule)


def check_of(c, net, p, sim, cut=False):
    D, _, _, _, starts, quay, cal = S2.setup2(c)
    g, y = S2.idle_nodes(D)
    if cut:
        return C3.check(net, p, sim.trips, starts, quay, cal, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
    return C.check(net, p, sim.trips, starts, quay, cal, c.get("fixed", False), S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)


def lifts_of(sim):
    return sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)


def keys(part):
    g, out = GRIDS[part], []
    if part == "port":
        for sc, m, arr, K, n, h, rep in itertools.product(g["scen"], T.MODES, g["arr"], g["K"], g["n_v"], g["hold"], g["rep"]):
            if rep == "cut" and h not in g["cut_hold"]:
                continue
            out.append(dict(scen=sc, mode=m, arr=arr, K=K, n_v=n, hold=h, rep=rep))
    elif part == "fix":
        for sc, m, arr, r in itertools.product(g["scen"], T.MODES, g["arr"], g["kref"]):
            out.append(dict(scen=sc, mode=m, arr=arr, kref=r))
    elif part == "mix6":
        for kind, sc, m, L, K, Sn, G, r in itertools.product(g["kinds"], g["scen"], T.MODES, g["L"], g["K"], g["S"], g["G"], g["rule"]):
            out.append(dict(kind=kind, scen=sc, mode=m, lift="mixed", rule=r, L=L, K=K, S=Sn, G=G))
    elif part == "sens":
        sub = g["sub"]
        for par, (_, vals) in g["levels"].items():
            for val in vals:
                a = sub["e1"]
                for sc, m, L, K, Sn, G in itertools.product(a["scen"], T.MODES, a["L"], a["K"], a["S"], a["G"]):
                    out.append(dict(sub="e1", par=par, val=val, kind="A1", scen=sc, mode=m, lift=T.lift_of(Sn), rule="fcfs", L=L, K=K, S=Sn, G=G))
                a = sub["e4"]
                for sc, m, L, K, Sn, G in itertools.product(a["scen"], T.MODES, a["L"], a["K"], a["S"], a["G"]):
                    out.append(dict(sub="e4", par=par, val=val, kind="A1", scen=sc, mode=m, lift=T.lift_of(Sn), rule="fcfs", L=L, K=K, S=Sn, G=G))
                a = sub["e3"]
                for sc, m, K, rep in itertools.product(a["scen"], T.MODES, a["K"], ["occ", "fix"]):
                    out.append(dict(sub="e3", par=par, val=val, kind="A1", scen=sc, mode=m, lift="cradle", rule="fcfs", rep=rep, n_v=a["n_v"], K=K,
                                    S=a["S"], G=a["G"]))
    elif part == "mixx":
        a = g["port"]
        for sc, m, arr, K, x in itertools.product(a["scen"], T.MODES, a["arr"], a["K"], g["x"]):
            out.append(dict(what="port", scen=sc, mode=m, arr=arr, K=K, x=x))
        a = g["win"]
        for sc, m, K, Sn, x in itertools.product(a["scen"], T.MODES, a["K"], a["S"], a["x"]):
            out.append(dict(what="win", kind="A1", scen=sc, mode=m, lift=T.lift_of(Sn) if Sn == 0 else "mixed", rule="fcfs", L=a["L"], K=K, S=Sn,
                            G=a["G"], x=x))
    else:
        for geo, m, arr, K, hd in itertools.product(g["out_geo"], T.MODES, g["out_arr"], g["K"], g["hand"]):
            out.append(dict(pub="out", geo=geo, mode=m, arr=arr, K=K, hand=hd))
        for geo, K, ro, var in itertools.product(g["in_geo"], g["K"], g["roro_in"], g["in_var"]):
            out.append(dict(pub="in", geo=geo, mode="pull_in", K=K, roro=ro, var=var))
        for K, Lt, rho in itertools.product(g["K"], g["tide_L"], g["rho"]):
            out.append(dict(pub="tide", geo="base", mode="pull_in", K=K, Lt=Lt, rho=rho))
    return [T.enc(d) for d in out]


def hold_v(h):
    return "inf" if h == "inf" else int(h)


# ---------------------------------------------------------------- one point of each part
def run_port(d):
    rep = d["rep"]
    c = port_cfg(d["scen"], d["mode"], d["arr"], int(d["K"]), int(d["n_v"]), hold_v(d["hold"]), "convoy" if rep == "convoy" else "fcfs",
                 fixed=rep == "cut")
    net, p, sim, r = (S3.simulate3 if rep == "cut" else S2.simulate2)(c)
    ck = check_of(c, net, p, sim, cut=rep == "cut")
    ls = lifts_of(sim)
    n = c["n_load"]
    G = c["cal"]["crane"][0][0] * 3600.0
    ph = (ls[n - 1] - G) / 3600.0 if len(ls) >= n else None
    out = dict(port_h=ph, lifts=len(ls), check_ok=ck["ok"], check_err=ck["errors"][:2], trips=len(sim.trips), bumps=getattr(sim, "bumps", 0))
    if rep != "cut":                                   # road occupancy: W′(port time) ≥ n (definition); FCFS also gets L*(n)
        f = B3.wprime_fn(dict(c, fixed=False))
        out["w_at_port"] = None if ph is None else f(ph * 3600.0)
        if rep == "fcfs":
            lo, hi = B3.lstar(f, n)
            out.update(lstar_lo=lo / 3600.0, lstar_hi=hi / 3600.0)
    return out


def fix_group(d, g):
    """As windport_sim.fix_group (E3), with mixed lifting allowed: bisect the calibration factor f, then compute the port time to
    load n_v piles for K = 1–8."""
    sc, mode, arr, kref = d["scen"], d["mode"], d["arr"], int(d["kref"])
    vl = T.SCEN[sc].get("p", {}).get("v_loaded", S.BASE["v_loaded"])

    def run(K, fixed, fac):
        sp = dict(v_loaded=vl / fac, v_empty=S.BASE["v_empty"] / fac) if fixed else {}
        c = port_cfg(sc, mode, arr, K, g["n_v"], 0, fixed=fixed, p_extra=sp, G=g["G"], open_h=g["open_h"])
        net, p, sim, r = S2.simulate2(c)
        ls = lifts_of(sim)
        G = c["cal"]["crane"][0][0] * 3600.0
        return (ls[g["n_v"] - 1] - G) / 3600.0, check_of(c, net, p, sim)
    target = run(kref, False, 1.0)[0]
    fx = lambda f: run(kref, True, f)[0]
    lo, hi = 1.0, 1.0
    if fx(1.0) < target - 1e-6:
        hi = 2.0
        while fx(hi) < target - 1e-6:
            lo, hi = hi, hi * 2
        for _ in range(g["bisect"]):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if fx(mid) < target - 1e-6 else (lo, mid)
    rows, ok, err = [], True, []
    for K in g["K"]:
        ph, ck = run(K, True, hi)
        ok &= ck["ok"]
        err += ck["errors"][:1]
        rows.append(dict(K=K, port_h=ph))
    return dict(factor=hi, target_h=target, rows=rows, check_ok=ok, check_err=err[:2])


def run_sens(d, key):
    par, val = d["par"], float(d["val"])
    base = dict(d, par="none", val=0)
    c = T.cfg_of("sens", T.enc(base))
    c["p"] = dict(c["p"], **{SENS3[par][0]: val})
    net, p, sim, r = S2.simulate2(c)
    ck = check_of(c, net, p, sim)
    out = dict(key=key, sim=sum(r["n_vessel"]), lifts=len(r["lifts"]), n_ramp=sum(r["n_ramp"]), trips=r["trips"], exits=r["exits"], check_ok=ck["ok"],
               check_err=ck["errors"][:2], bumps=0, map_sha256=net.map_sha256)
    if c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0] > 150:
        out["port_h"] = T.port_h(c, sim)
    w, wg = r.get("w1"), r.get("w1g")
    if w:
        out["w1"] = dict(bound=w["bound"], any=w["any_hist"], binding=w["binding"], cut=w["cut"], tl=w["tl"], te=w["te"], c=w["c"], dq=w["dq"],
                         k_dagger=w["k_dagger"], rate_h=w["rate_h"])
    if wg:
        out["w1g"] = wg
    return out


def run_pub(d):
    g = GRIDS["pub"]
    K = int(d["K"])
    if d["pub"] == "out":
        c = port_cfg("base", d["mode"], d["arr"], K, g["n_out"], 0, p_extra=g["hand"][d["hand"]], geo_extra=g["out_geo"][d["geo"]], G=g["G_out"])
        net, p, sim, r = S2.simulate2(c)
        ck = check_of(c, net, p, sim)
        ls = lifts_of(sim)
        G = c["cal"]["crane"][0][0] * 3600.0
        f = B3.wprime_fn(c)
        lo, _ = B3.lstar(f, g["n_out"])
        D = S2.build_map(c["geo"])
        return dict(port_h=(ls[g["n_out"] - 1] - G) / 3600.0, lifts=len(ls), how=[x["how"] for x in sorted(sim.trips, key=lambda x: x["s"] or 0)],
                    lstar_lo=lo / 3600.0, kassels_h=kassels_order(c, net, p) / 3600.0, route_m=route_len(net, D, D["windport"]["cradles"][0]),
                    check_ok=ck["ok"], check_err=ck["errors"][:2], trips=len(sim.trips))
    if d["pub"] == "in":
        geo = dict(dict(kind="A1", n_cradles=6, cradle_mode=d["mode"]), **g["in_geo"][d["geo"]])
        ro = float(d["roro"])
        c = dict(geo=geo, p=dict(g["in_var"][d["var"]], roro_s=ro * 3600.0), S=1, K=K, lift="cradle", horizon_h=60, cal=dict(ramp=[[0.0, 60.0]]), n_load=0,
                 n_unload=g["n_in"], unload_release_h=[0.0] * g["n_in"], hold=0, rule="fcfs")
        net, p, sim, r = S2.simulate2(c)
        ck = check_of(c, net, p, sim)
        fr, fy = sorted(r["ramp"]), sorted(r["yard"])
        D = S2.build_map(c["geo"])
        return dict(route_m=route_len(net, D, D["windport"]["ramp"][0], node=True), ramp_h=fr[-1] / 3600.0 if len(fr) == g["n_in"] else None, yard_h=fy[-1] / 3600.0 if len(fy) == g["n_in"] else None,
                    check_ok=ck["ok"], check_err=ck["errors"][:2], trips=len(sim.trips))
    Lt, rho = float(d["Lt"]), float(d["rho"])
    geo = dict(kind="A1", n_cradles=6, cradle_mode=d["mode"])
    ramp = [[i * TIDE, i * TIDE + Lt] for i in range(g["tides"])]
    c = dict(geo=geo, p=dict(roro_s=rho * 3600.0), S=1, K=K, lift="cradle", horizon_h=g["tides"] * TIDE + 1, cal=dict(ramp=ramp), n_load=0,
             n_unload=g["tides"] * g["per_tide"], unload_release_h=[a for a, _ in ramp for _ in range(g["per_tide"])], hold=0, rule="fcfs")
    net, p, sim, r = S2.simulate2(c)
    ck = check_of(c, net, p, sim)
    return dict(n_ramp=r["n_ramp"], thm3=r["thm3"]["bound"], rho_s=r["thm3"]["rho"], c_u=r["thm3"]["c_u"], check_ok=ck["ok"], check_err=ck["errors"][:2],
                trips=len(sim.trips))


def route_len(net, D, stop, node=False):
    """Shortest route length (m, minimum over the saddle rows) from the saddle rows to stop (a quay stop, or a node if node = True)."""
    t = stop if node else net.stops[stop]["node"]
    return round(min(sum(net.arc[a][2] for a in net.path(net.stops[o]["node"], t)) for o in D["windport"]["storage"]), 1)


def kassels_order(c, net, p):
    """Lifting order of Kassels §4.3 for 3 piles per vessel, 1 vehicle set and 1 stand: one pile pre-placed on the stand, one waiting
    on the vehicle at the quay; when the vessel arrives (G) the pile on the vehicle is lifted first, the vehicle is released at the
    same time, drives empty to the storage area, picks up the third pile (jacking h_p), returns loaded to the quay (direct lift, no
    set-down), then the pile on the stand is lifted; the third pile is lifted from max(G + 2p, vehicle arrival). Uses the wait-free
    trip durations of this model (fastest saddle row). Returns the time (s) from vessel arrival to completion of the third lift."""
    D = S2.build_map(c["geo"])
    W = D["windport"]
    cap, size = net.capacities(p)
    q = net.stops[W["cradles"][0]]
    best = None
    for o in W["storage"]:
        so = net.stops[o]
        TE = net.leg(q["node"], so["node"], p["v_empty"], p["plat_len"], p["plat_w"], False, p, cap, size, so["res"], 1.0, True)[0]
        TL = net.leg(so["node"], q["node"], p["v_loaded"], p["Lv"], p["B"], True, p, cap, size, q["res"], 1.0)[0]
        best = TE + TL if best is None else min(best, TE + TL)
    P = p["lift_s"]
    return max(2 * P, best + p["hp_s"]) + P


def run_mixx(d, key):
    x = float(d["x"])
    if d["what"] == "port":
        c = port_cfg(d["scen"], d["mode"], d["arr"], int(d["K"]), GRIDS["mixx"]["port"]["n_v"], 0, p_extra=dict(release_frac=x))
        net, p, sim, r = S2.simulate2(c)
        ck = check_of(c, net, p, sim)
        ls = lifts_of(sim)
        n = c["n_load"]
        return dict(port_h=(ls[n - 1] - c["cal"]["crane"][0][0] * 3600.0) / 3600.0, check_ok=ck["ok"], check_err=ck["errors"][:2], trips=len(sim.trips))
    k = T.enc({a: b for a, b in d.items() if a not in ("what", "x")})
    orig = T.cfg_of

    def patched(part, kk):
        c = orig(part, kk)
        c["p"] = dict(c["p"], release_frac=x)
        return c
    T.cfg_of = patched
    try:
        r = T.run_one("e4", k)
    finally:
        T.cfg_of = orig
    return dict(sim=r["sim"], w1g=r["w1g"]["bound"], check_ok=r["check_ok"], check_err=r["check_err"], trips=r["trips"])


def run_one(part, key):
    d = T.dec(key)
    if part == "mixx":
        return dict(key=key, **run_mixx(d, key))
    if part == "port":
        return dict(key=key, **run_port(d))
    if part == "fix":
        return dict(key=key, **fix_group(d, GRIDS["fix"]))
    if part == "mix6":
        return T.run_one("e4", key)
    if part == "sens":
        return run_sens(d, key)
    return dict(key=key, **run_pub(d))


# ---------------------------------------------------------------- run and aggregate
_OUT = None


def init(out):
    global _OUT
    _OUT = Path(out)
    pin(list(range(1, os.cpu_count())))


def run_chunk(arg):
    part, ks = arg
    for k in ks:
        write_json(_OUT / "points" / T.fname(k), run_one(part, k))
    return ks


PCOLS = dict(
    port=["key", "scen", "mode", "arr", "K", "n_v", "hold", "rep", "port_h", "lifts", "w_at_port", "lstar_lo", "lstar_hi", "bumps", "check_ok", "trips"],
    fix=["key", "scen", "mode", "arr", "kref", "factor", "target_h", "K", "port_h", "check_ok"],
    pub=["key", "pub", "geo", "mode", "arr", "K", "hand", "roro", "var", "Lt", "rho", "route_m", "port_h", "lifts", "lstar_lo", "kassels_h", "how", "ramp_h", "yard_h",
         "n_ramp", "thm3", "rho_s", "c_u", "check_ok", "trips"],
    mixx=["key", "what", "kind", "scen", "mode", "arr", "lift", "rule", "L", "K", "S", "G", "x", "port_h", "sim", "w1g", "check_ok", "trips"],
)


def rows_of(part, key, r):
    d = T.dec(key)
    if part in ("mix6", "sens"):
        return [T.row_of("e4" if part == "mix6" else "sens", key, r)]
    if part == "fix":
        return [dict(key=f"{key}|K={x['K']}", **d, factor=round(r["factor"], 9), target_h=round(r["target_h"], 6), K=x["K"],
                     port_h=round(x["port_h"], 6), check_ok=int(r["check_ok"])) for x in r["rows"]]
    out = dict(d, key=key, check_ok=int(r["check_ok"]), trips=r["trips"])
    for k in ("port_h", "lstar_lo", "lstar_hi", "ramp_h", "yard_h", "kassels_h"):
        if k in r:
            out[k] = "" if r[k] is None else round(r[k], 6)
    for k in ("lifts", "w_at_port", "bumps", "rho_s", "c_u", "sim", "w1g", "route_m"):
        if k in r:
            out[k] = "" if r[k] is None else r[k]
    for k in ("how", "n_ramp", "thm3"):
        if k in r:
            out[k] = "/".join(map(str, r[k]))
    return [out]


def config(part):
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    return dict(task="extra", part=part, title=GRIDS[part]["title"], grid=GRIDS[part], arr=ARR, scen=T.SCEN, base=S.BASE, tide_h=TIDE,
                inputs={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in INPUTS}, code=code,
                code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=list(GRIDS))
    ap.add_argument("--procs", type=int, default=22)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=10)
    ap.add_argument("--aggregate-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = config(a.part)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_extra_{a.part}_{h}"
    ks = keys(a.part)
    if not a.aggregate_only:
        (out / "points").mkdir(parents=True, exist_ok=True)
        cf = out / "config.json"
        if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != json.loads(json.dumps(cfg)):     # config contains tuples: compare after a JSON round trip
            raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
        cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        todo = [k for k in ks if not (out / "points" / T.fname(k)).exists()]
        prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, cfg["title"], "extra")
        chunk = 1 if a.part == "fix" else a.chunk
        chunks = [(a.part, todo[i:i + chunk]) for i in range(0, len(todo), chunk)]
        try:
            for ds in slot_imap(run_chunk, chunks, a.procs, initializer=init, initargs=(str(out),), slots_dir=a.slots, tag="extra"):
                prog.write(done=prog.d["done"] + len(ds))
        except Exception as e:
            prog.write(state="failed", failed=1, note=repr(e)[:300])
            raise
    rows = [x for k in ks for x in rows_of(a.part, k, json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8")))]
    cols = T.COLS if a.part in ("mix6", "sens") else PCOLS[a.part]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
    bad = sum(1 for r in rows if not r["check_ok"])
    note = f"checker failed at {bad} points"
    if a.part == "port":
        wb = sum(1 for r in rows if r.get("w_at_port") not in (None, "") and r["w_at_port"] < int(r["n_v"]))
        lb = sum(1 for r in rows if r.get("lstar_lo") not in (None, "") and r["port_h"] not in (None, "") and r["port_h"] < r["lstar_lo"] - 1e-9)
        note += f"; W′(port time) < n_v at {wb} points; port time < L* at {lb} points"
    if a.part in ("mix6", "sens"):
        over = sum(1 for r in rows if r.get("w1g") not in (None, "") and r.get("rep") != "fix" and r["sim"] > r["w1g"])
        note += f"; above W1′ at {over} points"
    if not a.aggregate_only:
        prog.write(state="done", note=note)
    print(out)
    print(note)


if __name__ == "__main__":
    main()
