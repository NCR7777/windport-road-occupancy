"""Main experiments E4-E7 and supplementary runs (simulator windport/sim2.py, independent checker windport/check.py).
Base case: no gate holding places (Q_h = 0); the yard side is treated as open (port archetypes; except the batches with an off-road
pocket and the shipyard maps); direct lifting releases the vehicle when the lift starts (x = 0); jack-up and set-down 30 min each.
Every point also gets W1′ (w1g: geometric quay-zone Q plus the chain-cut preparation term).

--part e4    Fig. 4: fleet plateau and cradle-vehicle rate. A1, A2, A3 (Layouts 1-3) × base / long single lane + 1 km/h
             (corridor-limited) × cradle type × L = 6, 12, 24 h × K = 1–10 × S = 0–6 (S = 0 direct lifting)
             × G = 3, 24 h × dispatch rule fcfs / convoy (loaded vehicles first through the bottleneck; upper end of the plateau).
--part e5    Fig. 5: unloading-loading overlap. A1 × base / long corridor + 1 km/h × cradle type × dedicated unloading vehicle
             (K_u = 1, loading K_t − 1) / shared fleet without priority (plain, ordinary first-come-first-served) / shared fleet
             (K_t, unloading dispatched first) / shared fleet with at most 1 vehicle unloading at a time (shared1,
             windport.sim2.CapMixin) × K_t = 2, 3, 4, 6
             × overlap x = 0, 0.25, 0.5, 0.75, 1 × tidal window 6 h / continuously open × S = 1, 3; crane window [G, G + L]
             (L = 24 h, G = 24 h), unloading period of length L starting at G + (1 − x)·L; RoRo on-board work 3 h; every point also
             gets the upper bound on both flows combined (Corollary 5).
--part e6    Fig. 6, Table 4: shipyards as wind marshalling ports. Maps derived from Okpo (6 cradle positions) and Yantai (1)
             (windport/shipyard.py) × cradle type × base / 1 km/h / crane 0.5 h × L = 4, 6, 12, 24 h × K = 1–8
             × S = 0–min(4, cradle positions) × G = 3, 24 h × fcfs / convoy; idle vehicles wait in the off-road pocket next to the
             storage area.
--part e7    Fig. 7: upscaling. A1 (single lane 12 m wide) × base / long single lane + 1 km/h × cradle type × monopile 85 m / 9.5 m,
             100 m / 9.5 m, 110 m / 11.5 m, 120 m / 12 m × K = 1–6 × S = 1, 3 × L = 12 h × G = 24 h; the summary converts the masses
             1,500 / 1,500 / 2,300 / 3,000 t into an upper limit on K with the axle-line pool.
--part pocket  Off-road pocket (30 m stub joined to the south end of the single lane): reruns the corridor-limited E1 scenarios
             (A1: seven, A2 / A3: two) on the E1 grid (cradle mode and direct lifting), compared with the committed
             runs/e1.
--part conv  Convoy dispatch × gate holding places Q_h = 0, 1, 2, unlimited; A1 × five scenarios on the E1h grid (one more column
             in the gate-holding-place table).
--part e2c   Reruns the simulation of the 540 small E2 instances with convoy dispatch (one more column in Table 2; the CP-SAT column
             is taken from the committed E2 results).
--part sens  Appendix C: jack-up / set-down 15–60 min, steering 2–10 min, direct-lift release time x, loaded speed 1–2.5 km/h,
             crane 0.5–1.5 h, varied one at a time (others at base), applied to (a) a reduced E1 grid, (b) a reduced E4 grid (plateau
             and cradle-vehicle rate), (c) E3 port time (road occupancy / fixed durations, K_ref = 1, i.e. conflict-free travel time);
             RoRo 3–5 h applied to (d) a reduced E5 grid.
Output results/windport_runs_<part>_<config hash>/: config.json (parameters, grid, SHA-256 of inputs and code; e6 also records the
paths, SHA-256 and commits of the two maps), progress.json, points/ (one JSON per point, resume cache), points.csv (no wall clock).

Run: .venv/Scripts/python.exe experiments/windport_runs.py --part e4 --procs 23 --slots DIR
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
from windport import check as C                                  # noqa: E402
from windport import shipyard as SY                              # noqa: E402
from windport import sim as S                                    # noqa: E402
from windport import sim2 as S2                                  # noqa: E402

KMH = 1 / 3.6
TIDE = 12.4206
CODE = ["windport/sim.py", "windport/sim2.py", "windport/bound.py", "windport/bound2.py", "windport/check.py", "windport/archetypes.py",
        "windport/shipyard.py", "occupancy/sim.py", "occupancy/network.py", "occupancy/params.py",
        "occupancy/tasks.py", "exact/check.py", "experiments/windport_runs.py"]
INPUTS = ["data/register/parameters.csv"]
LONG = dict(dist_m=1500.0, corridor_m=1200.0)
SCEN = dict(base={}, slow=dict(p=dict(v_loaded=1.0 * KMH)), long=dict(geo=LONG), longslow=dict(geo=LONG, p=dict(v_loaded=1.0 * KMH)),
            lane=dict(geo=dict(LONG, n_junctions=0), p=dict(v_loaded=1.0 * KMH)), longpile=dict(p=dict(Lv=123.6)),
            fastcrane=dict(p=dict(lift_s=1800.0)), joint=dict(p=dict(roro_s=3 * 3600.0), joint=dict(L_tide=6.0, per_tide=1, K_u=1)),
            jointshared=dict(p=dict(roro_s=3 * 3600.0, unload_first=True), joint=dict(L_tide=6.0, per_tide=1, K_u=0)))
MODES = ["on_road", "pull_in"]
NC = dict(okpo=6, yantai=1)
E7LEV = {"85": dict(Lv=85.0, B=9.5, t=1500), "100": dict(Lv=100.0, B=9.5, t=1500), "110": dict(Lv=110.0, B=11.5, t=2300),
         "120": dict(Lv=120.0, B=12.0, t=3000)}
SENS = dict(none=[0], hphd=[900.0, 2700.0, 3600.0], steer=[300.0, 600.0], v=[1.0, 1.5, 2.0, 2.5], lift=[1800.0, 2700.0, 4500.0, 5400.0],
            x=[0.25, 0.5, 1.0])
E1G = dict(L=[2, 3, 4, 6, 8, 12, 18, 24], K=[1, 2, 3, 4, 5, 6], S=[0, 1, 2, 3, 4, 6], G=[3, 24])
SC5 = ["base", "slow", "longslow", "lane", "fastcrane"]
GRIDS = dict(
    e4=dict(title="E4 fleet plateau and cradle-vehicle rate (Fig. 4)", kinds=["A1", "A2", "A3"], scen=["base", "lane"], L=[6, 12, 24], K=list(range(1, 11)),
            S=list(range(0, 7)), G=[3, 24], rule=["fcfs", "convoy"]),
    e5=dict(title="E5 unloading-loading overlap (Fig. 5)", scen=["base", "longslow"], fleet=["ded", "plain", "shared", "shared1"], Kt=[2, 3, 4, 6], x=[0.0, 0.25, 0.5, 0.75, 1.0],
            tide=["6", "cont"], S=[1, 3], L=24, G=24, rule=["fcfs", "convoy"], roro_h=3.0),
    e6=dict(title="E6 shipyards as wind marshalling ports (Fig. 6, Table 4)", sites=["okpo", "yantai"], scen=["base", "slow", "fastcrane"], L=[4, 6, 12, 24], K=list(range(1, 9)), G=[3, 24],
            rule=["fcfs", "convoy"]),
    e7=dict(title="E7 upscaling (Fig. 7)", scen=["base", "lane"], lev=list(E7LEV), K=list(range(1, 7)), S=[1, 3], L=[12], G=[24], corridor_w=12.0),
    pocket=dict(title="Off-road pocket: sensitivity of the corridor-limited E1 scenarios", sets=[dict(kinds=["A1"], scen=["slow", "long", "longslow", "lane", "fastcrane", "joint",
                                                                                "jointshared"]),
                                                               dict(kinds=["A2", "A3"], scen=["longslow", "lane"])], stub_m=30.0, **E1G),
    conv=dict(title="Convoy dispatch × gate holding places (one more column in the gate-holding-place table)", scen=SC5, hold=[0, 1, 2, "inf"], **E1G),
    e2c=dict(title="E2 small instances rerun in simulation with convoy dispatch (one more column in Table 2)"),
    sens=dict(title="Appendix C sensitivity", levels=SENS, e1=dict(scen=["base", "lane"], L=[4, 12], K=list(range(1, 7)), S=[0, 1, 3], G=[3, 24]),
              e4=dict(scen=["base", "lane"], L=[12], K=list(range(1, 11)), S=list(range(0, 7)), G=[24]),
              e3=dict(scen=["base", "lane"], K=list(range(1, 9)), S=1, n_v=10, G=24, open_h=200),
              e5=dict(scen=["base"], fleet=["ded", "plain", "shared", "shared1"], Kt=[2, 4], x=[0.0, 0.5, 1.0], tide=["6", "cont"], S=1, roro_h=[3.0, 4.0, 5.0])),
)


def enc(d):
    return "|".join(f"{k}={v}" for k, v in d.items())


def dec(key):
    out = {}
    for f in key.split("|"):
        k, v = f.split("=", 1)
        out[k] = v
    return out


def lift_of(S_):
    return "direct" if int(S_) == 0 else "cradle"


def keys(part):
    g, out = GRIDS[part], []
    if part == "e4":
        for kind, sc, m, L, K, Sn, G, r in itertools.product(g["kinds"], g["scen"], MODES, g["L"], g["K"], g["S"], g["G"], g["rule"]):
            out.append(dict(kind=kind, scen=sc, mode=m, lift=lift_of(Sn), rule=r, L=L, K=K, S=Sn, G=G))
    elif part == "e5":
        for sc, m, fl, Kt, x, td, Sn, r in itertools.product(g["scen"], MODES, g["fleet"], g["Kt"], g["x"], g["tide"], g["S"], g["rule"]):
            out.append(dict(kind="A1", scen=sc, mode=m, lift="cradle", rule=r, fleet=fl, Kt=Kt, x=x, tide=td, roro=g["roro_h"], L=g["L"], S=Sn, G=g["G"]))
    elif part == "e6":
        for site in g["sites"]:
            for m, sc, L, K, Sn, G, r in itertools.product(MODES, g["scen"], g["L"], g["K"], range(0, min(4, NC[site]) + 1), g["G"], g["rule"]):
                out.append(dict(kind="map:" + site, scen=sc, mode=m, lift=lift_of(Sn), rule=r, L=L, K=K, S=Sn, G=G))
    elif part == "e7":
        for sc, m, lev, K, Sn, L, G in itertools.product(g["scen"], MODES, g["lev"], g["K"], g["S"], g["L"], g["G"]):
            out.append(dict(kind="A1", scen=sc, mode=m, lift="cradle", rule="fcfs", lev=lev, L=L, K=K, S=Sn, G=G))
    elif part == "pocket":
        for st in g["sets"]:
            for kind, sc, m, L, K, Sn, G in itertools.product(st["kinds"], st["scen"], MODES, g["L"], g["K"], g["S"], g["G"]):
                out.append(dict(kind=kind, scen=sc, mode=m, lift=lift_of(Sn), rule="fcfs", pocket=1, hold=0, L=L, K=K, S=Sn, G=G))
    elif part == "conv":
        for sc, m, L, K, Sn, G, h in itertools.product(g["scen"], MODES, g["L"], g["K"], g["S"], g["G"], g["hold"]):
            out.append(dict(kind="A1", scen=sc, mode=m, lift=lift_of(Sn), rule="convoy", hold=h, L=L, K=K, S=Sn, G=G))
    elif part == "e2c":
        import windport_e2 as E2
        out = [dict(e2=k.replace("|", "/")) for k in E2.keys()]
    else:
        lv = g["levels"]
        for par, vals in lv.items():
            for val in vals:
                a = g["e1"]
                for sc, m, L, K, Sn, G in itertools.product(a["scen"], MODES, a["L"], a["K"], a["S"], a["G"]):
                    out.append(dict(sub="e1", par=par, val=val, kind="A1", scen=sc, mode=m, lift=lift_of(Sn), rule="fcfs", L=L, K=K, S=Sn, G=G))
                a = g["e4"]
                for sc, m, L, K, Sn, G in itertools.product(a["scen"], MODES, a["L"], a["K"], a["S"], a["G"]):
                    out.append(dict(sub="e4", par=par, val=val, kind="A1", scen=sc, mode=m, lift=lift_of(Sn), rule="fcfs", L=L, K=K, S=Sn, G=G))
                a = g["e3"]
                for sc, m, K, rep in itertools.product(a["scen"], MODES, a["K"], ["occ", "fix"]):
                    out.append(dict(sub="e3", par=par, val=val, kind="A1", scen=sc, mode=m, lift="cradle", rule="fcfs", rep=rep, n_v=a["n_v"], K=K,
                                    S=a["S"], G=a["G"]))
        a = g["e5"]
        for sc, m, fl, Kt, x, td, ro in itertools.product(a["scen"], ["pull_in"], a["fleet"], a["Kt"], a["x"], a["tide"], a["roro_h"]):
            out.append(dict(sub="e5", par="roro", val=ro, kind="A1", scen=sc, mode=m, lift="cradle", rule="fcfs", fleet=fl, Kt=Kt, x=x, tide=td,
                            roro=ro, L=24, S=a["S"], G=24))
    return [enc(d) for d in out]


def cfg_of(part, key):
    d = dec(key)
    if part == "e2c":
        import windport_e2 as E2
        c = E2.cfg_of(d["e2"].replace("/", "|"))
        c["rule"] = "convoy"
        return c
    sc = SCEN[d["scen"]]
    p = dict(sc.get("p", {}))
    par, val = d.get("par"), float(d["val"]) if "val" in d else None
    if par == "hphd":
        p.update(hp_s=val, hd_s=val)
    elif par == "steer":
        p["sweep_steer_s"] = val
    elif par == "v":
        p["v_loaded"] = val * KMH
    elif par == "lift":
        p["lift_s"] = val
    elif par == "x":
        p["release_frac"] = val
    kind, mode = d["kind"], d["mode"]
    if kind.startswith("map:"):
        geo = dict(kind="map", site=kind[4:], cradle_mode=mode, n_cradles=NC[kind[4:]])
    else:
        geo = dict(dict(kind=kind, n_cradles=6, cradle_mode=mode), **sc.get("geo", {}))
        if d.get("pocket") == "1":
            geo["pocket"] = GRIDS["pocket"]["stub_m"]
    if part == "e7":
        lv = E7LEV[d["lev"]]
        p.update(Lv=lv["Lv"], B=lv["B"])
        geo["corridor_w"] = GRIDS["e7"]["corridor_w"]
    lift_s = p.get("lift_s", S.BASE["lift_s"])
    Sn, G = int(d["S"]), float(d["G"])
    hold = d.get("hold", "0")
    hold = "inf" if hold == "inf" else int(hold)
    if d.get("rep"):                                   # E3 port time: crane open from G on, until n_v piles are loaded
        oh = GRIDS["sens"]["e3"]["open_h"]
        K = int(d["K"])
        return dict(geo=geo, p=p, S=Sn, K=K, lift="cradle", horizon_h=G + oh, cal=dict(crane=[[G, G + oh]]), n_load=int(d["n_v"]),
                    fixed=d["rep"] == "fix", hold=0, rule="fcfs")
    L = float(d["L"])
    if d.get("fleet"):
        Kt = int(d["Kt"])
        K, Ku = (Kt - 1, 1) if d["fleet"] == "ded" else (Kt, 0)
    else:
        K, Ku = int(d["K"]), 0
    c = dict(geo=geo, p=p, S=Sn, K=K, lift=d["lift"], horizon_h=G + L + 1, cal=dict(crane=[[G, G + L]]),
             n_load=int(L * 3600 // lift_s) + K + Sn + 2, hold=hold, rule=d["rule"])
    if d.get("fleet"):                                 # E5: unloading period [u0, u0 + L], u0 = G + (1 − x)·L
        x = float(d["x"])
        u0 = G + (1 - x) * L
        p["roro_s"] = float(d["roro"]) * 3600.0
        if Ku == 0 and d["fleet"] != "plain":
            p["unload_first"] = True
        if d["fleet"] == "shared1":
            p["unload_cap"] = 1
        if d["tide"] == "cont":
            ramp = [[u0, u0 + L]]
            n_u, rel = int(math.ceil(L / float(d["roro"]))) + 1, [u0] * (int(math.ceil(L / float(d["roro"]))) + 1)
        else:
            ramp = [[u0 + i * TIDE, u0 + i * TIDE + 6.0] for i in range(int(math.ceil(L / TIDE)))]
            n_u, rel = len(ramp), [a for a, _ in ramp]
        c["cal"]["ramp"] = ramp
        c.update(K_u=Ku, n_unload=n_u, unload_release_h=rel, joint_cut="corr_lane_0", horizon_h=max(G + L, u0 + L) + 1)
    jt = sc.get("joint")
    if jt and not d.get("fleet"):                       # simultaneous unloading and loading scenarios of E1 (pocket part)
        n = int(math.ceil((G + L + 1) / TIDE))
        c["cal"]["ramp"] = [[i * TIDE, i * TIDE + jt["L_tide"]] for i in range(n)]
        c.update(n_unload=n * jt["per_tide"], unload_release_h=[i * TIDE for i in range(n) for _ in range(jt["per_tide"])],
                 joint_cut="corr_lane_0", K_u=jt["K_u"])
    return c


def port_h(c, sim):
    n = c["n_load"]
    lifts = sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)
    return (lifts[n - 1] - c["cal"]["crane"][0][0] * 3600.0) / 3600.0 if len(lifts) >= n else None


def regime(binding):
    b = set(binding.split("+"))
    return "interface" if "interface" in b else ("flow" if b & {"prep", "serial"} else "staging")


def run_one(part, key):
    c = cfg_of(part, key)
    net, p, sim, r = S2.simulate2(c)
    D, _, _, _, starts, quay, cal = S2.setup2(c)
    g, y = S2.idle_nodes(D)
    chk = C.check(net, p, sim.trips, starts, quay, cal, c.get("fixed", False), S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
    out = dict(key=key, sim=sum(r["n_vessel"]), lifts=len(r["lifts"]), n_ramp=sum(r["n_ramp"]), trips=r["trips"], exits=r["exits"],
               check_ok=chk["ok"], check_err=chk["errors"][:2], bumps=getattr(sim, "bumps", 0), map_sha256=net.map_sha256)
    if c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0] > 150:
        out["port_h"] = port_h(c, sim)
    w, wg = r.get("w1"), r.get("w1g")
    if w:
        out["w1"] = dict(bound=w["bound"], any=w["any_hist"], binding=w["binding"], cut=w["cut"], tl=w["tl"], te=w["te"], c=w["c"], dq=w["dq"],
                         k_dagger=w["k_dagger"], rate_h=w["rate_h"])
    if wg:
        out["w1g"] = wg
    if "thm3" in r:
        out["thm3"] = sum(r["thm3"]["bound"])
        out["thm3_over"] = sum(max(0, a - b) for a, b in zip(r["n_ramp"], r["thm3"]["bound"]))
    if "joint_ub" in r:
        out["joint_ub"] = {k: v for k, v in r["joint_ub"].items() if k != "vt"}
    return out


def fname(key):
    return hashlib.sha256(key.encode()).hexdigest()[:20] + ".json"


_OUT = None


def init(out):
    global _OUT
    _OUT = Path(out)
    pin(list(range(1, os.cpu_count())))


def run_chunk(arg):
    part, ks = arg
    for k in ks:
        write_json(_OUT / "points" / fname(k), run_one(part, k))
    return ks


COLS = ["key", "part", "sub", "par", "val", "kind", "scen", "mode", "lift", "rule", "pocket", "hold", "fleet", "Kt", "x", "tide", "roro", "lev", "rep",
        "n_v", "L", "K", "S", "G", "sim", "lifts", "n_ramp", "port_h", "w1", "w1_any", "w1_binding", "w1g", "w1g_binding", "regime", "Q", "serial",
        "chain", "bmax", "phased", "interface", "turnover", "fleet_t", "cut", "zone", "prep", "cut_res", "tl", "te", "c", "dq", "k_dagger", "rate_h",
        "thm3", "thm3_over", "joint_ub", "exit_hold", "exit_yard", "bumps", "check_ok", "trips"]


def row_of(part, key, r):
    d = dec(key)
    if part == "e2c":
        import windport_e2 as E2
        m, sc, K, s, L, G, h = d["e2"].split("/")
        d = dict(kind="A1", scen=sc, mode=m, lift="direct" if s == "S0" else "cradle", rule="convoy", hold=h[1:], L=L[1:], K=K[1:], S=s[1:], G=G[1:])
    out = {k: v for k, v in d.items() if k in COLS}
    out.update(key=key, part=part, sim=r["sim"], lifts=r["lifts"], n_ramp=r["n_ramp"], trips=r["trips"], check_ok=int(r["check_ok"]), bumps=r["bumps"],
               exit_hold=r["exits"].get("hold", 0), exit_yard=r["exits"].get("yard", 0))
    if "port_h" in r:
        out["port_h"] = "" if r["port_h"] is None else round(r["port_h"], 6)
    if "w1" in r:
        w = r["w1"]
        out.update(w1=w["bound"], w1_any=w["any"], w1_binding=w["binding"], cut_res=w["cut"], tl=round(w["tl"], 3), te=round(w["te"], 3),
                   c=round(w["c"], 3), dq=round(w["dq"], 3), k_dagger=round(w["k_dagger"], 6), rate_h=round(w["rate_h"], 6))
    if "w1g" in r:
        g = r["w1g"]
        ch = g.get("chain") or {}
        t = g["terms"]
        out.update(w1g=g["bound"], w1g_binding=g["binding"], regime=regime(g["binding"]), Q=g["Q"], serial="" if g["serial"] is None else g["serial"],
                   chain=ch.get("res", ""), bmax="" if not ch else ("inf" if ch["bmax"] == math.inf else ch["bmax"]), phased=int(bool(ch.get("phased"))),
                   interface=t.get("interface"), turnover="inf" if t.get("turnover") is None else t["turnover"], fleet_t=t.get("fleet"), cut=t.get("cut"),
                   zone=t.get("zone", ""), prep=t.get("prep", ""))
    if "thm3" in r:
        out.update(thm3=r["thm3"], thm3_over=r["thm3_over"])
    if "joint_ub" in r:
        out["joint_ub"] = r["joint_ub"]["ub"]
    return out


def config(part):
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="runs", part=part, title=GRIDS[part]["title"], grid=GRIDS[part], scen=SCEN, base=S.BASE, tide_h=TIDE, e7=E7LEV, nc=NC,
               inputs={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in INPUTS}, code=code,
               code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest())
    if part in ("e6",):
        cfg["networks"] = {s: dict(network=SY.NETWORK[s], site=SY.SITES[s]) for s in GRIDS["e6"]["sites"]}
    if part == "e2c":
        cfg["e2_source"] = "results/runs/e2/points.csv"
        cfg["code"]["experiments/windport_e2.py"] = hashlib.sha256((ROOT / "experiments/windport_e2.py").read_bytes()).hexdigest()
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=list(GRIDS))
    ap.add_argument("--procs", type=int, default=23)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=20)
    ap.add_argument("--aggregate-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = config(a.part)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_runs_{a.part}_{h}"
    ks = keys(a.part)
    if not a.aggregate_only:
        (out / "points").mkdir(parents=True, exist_ok=True)
        cf = out / "config.json"
        if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != cfg:
            raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
        cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        todo = [k for k in ks if not (out / "points" / fname(k)).exists()]
        prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, cfg["title"], "runs")
        chunks = [(a.part, todo[i:i + a.chunk]) for i in range(0, len(todo), a.chunk)]
        try:
            for ds in slot_imap(run_chunk, chunks, a.procs, initializer=init, initargs=(str(out),),
                                slots_dir=a.slots, tag="runs"):
                prog.write(done=prog.d["done"] + len(ds))
        except Exception as e:
            prog.write(state="failed", failed=1, note=repr(e)[:300])
            raise
    rows = [row_of(a.part, k, json.loads((out / "points" / fname(k)).read_text(encoding="utf-8"))) for k in ks]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
    bad = sum(1 for r in rows if not r["check_ok"])
    over = sum(1 for r in rows if r.get("w1g") not in (None, "") and r.get("rep") != "fix" and r["sim"] > r["w1g"])
    over1 = sum(1 for r in rows if r.get("w1") not in (None, "") and r.get("rep") != "fix" and r["sim"] > r["w1"])
    jo = sum(1 for r in rows if r.get("joint_ub") not in (None, "") and r["sim"] + r["n_ramp"] > r["joint_ub"])
    note = f"checker failures: {bad} points; above W1: {over1} points; above W1′: {over} points; above the joint bound: {jo} points"
    if not a.aggregate_only:
        prog.write(state="done", note=note)
    print(out)
    print(note)


if __name__ == "__main__":
    main()
