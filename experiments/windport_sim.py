"""Simulation batches for the offshore wind marshalling port (simulator windport/sim.py, independent checker windport/check.py).
Modelling choices: idle space is modelled explicitly (gate holding places Q_h; base case Q_h = 0, i.e. after release the vehicle
leaves through the single lane to the yard side); stop-and-turn delays count as travel time; a route reservation does not exempt
the reserving vehicle; the cut window is clipped at the hand-over; release time of direct lifts; E3 calibrates the fixed-time
representation at K_ref. points.csv has no wall-clock columns.

--part e1 (Fig. 2, regime map): layout × scenario × cradle placement × lift mode × window length L × SPMT groups K × cradles S
    × preparation time G, Q_h = 0. Empty-system start (at time 0 all vehicles are empty at the yard saddle row, cradles empty);
    crane window [G, G + L]; ⌊L/p⌋ + K + S + 2 monopiles to load (all available at time 0).
    Per point: piles lifted onto the vessel in the simulation, the terms of W1 (empty start, preparation G: Theorem 2 ∧ Theorem 1)
    and the binding term, W1 for an arbitrary history, the independent checker; for simultaneous unloading and loading (scenarios
    joint, jointshared) also the piles unloaded per tidal window, the Theorem 3 bound and the Theorem 4 slack.
    Scenarios (base = the Kassels 2023 Rønne case model: loaded 2.5 km/h, crane 1 h, RoRo unloading 3–5 h per pile, 4 h used;
    see windport/sim.BASE):
      base; slow loaded 1 km/h; long yard-quay 1,500 m, single lane 1,200 m; longslow both; lane as longslow but the single lane has
      no side branches (one exclusive segment); longpile vehicle plus load 123.6 m long (longest monopile delivered at Lindø);
      fastcrane crane 0.5 h; joint simultaneous unloading and loading on shared roads, unloading by 1 dedicated SPMT group
      (ramp window 6 h, period 12.42 h, RoRo on-board work 3 h, one unloading task released per tidal window); jointshared as
      joint but the same K groups also unload (unloading tasks dispatched first).
--part e1h (one dimension of the regime map: gate holding places): A1 × base, slow, longslow, lane, fastcrane × cradle placement
    × lift mode (S = 0 is direct lift) × L × K × S × G × Q_h = 1, 2, unlimited ("unlimited": the gate occupies no space).
--part rel (release time of direct lifts): A1 base × cradle placement × K = 1–3 × S = 0 (direct lift, release_frac = 0, 0.25,
    0.5, 1) and S = 1 (cradle, reference) × L = 4, 12 h × G = 3, 24 h.
--part e3 (Table 3, Fig. 3): the same input under the fixed-time representation (fixed in windport.sim: no conflicts on roads
    and at junctions; ramp, cradles, crane, saddle row, holding places and calendar as before) and the occupancy representation:
    (a) vessel port time: cradles ready within G = 24 h, crane open from G on; time from G until the last of n_v piles is lifted
    (3 = Kassels' installation vessel; 10 = Mammoet per voyage); (b) piles lifted within window L. K = 1–8. Occupancy
    representation with Q_h = 0 (base case) and unlimited.
    Fixed-time calibration with the same mean durations: both speeds are multiplied by 1/f, where f makes the fixed-time port time
    for 10 piles at K = K_ref equal to the occupancy (Q_h = 0) port time at the same K_ref (bisection, smallest f that satisfies
    it); one set for each K_ref = 1, 2, 3, 4. K_ref = 1 is close to the conflict-free travel time.
Output results/windport_<part>_<config hash>/: config.json (parameters, grid, SHA-256 of inputs and code), progress.json,
points/ (per-point JSON, resume cache), points.csv (per-point summary, tracked in git).
CPU slots: --slots DIR or environment variable CPU_SLOTS (tools/cpu_slots.py); one slot per dispatched batch of points.

Run: .venv/Scripts/python.exe experiments/windport_sim.py --part e1 --procs 23 --slots DIR
     .venv/Scripts/python.exe experiments/windport_sim.py --part e1 --aggregate-only     # only rewrite points.csv from points/
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, slot_imap, write_json           # noqa: E402
from windport import check as C                                 # noqa: E402
from windport import sim as S                                   # noqa: E402

KMH = 1 / 3.6
CODE = ["windport/sim.py", "windport/bound.py", "windport/check.py", "windport/archetypes.py", "occupancy/sim.py", "occupancy/network.py",
        "occupancy/params.py", "occupancy/tasks.py", "occupancy/bound.py", "exact/check.py", "experiments/windport_sim.py"]
INPUTS = ["data/register/parameters.csv"]
LONG = dict(dist_m=1500.0, corridor_m=1200.0)
TIDE = 12.4206                       # semidiurnal M2 tide period (h, parameter register tide_m2_period)
SCEN = dict(base={}, slow=dict(p=dict(v_loaded=1.0 * KMH)), long=dict(geo=LONG), longslow=dict(geo=LONG, p=dict(v_loaded=1.0 * KMH)),
            lane=dict(geo=dict(LONG, n_junctions=0), p=dict(v_loaded=1.0 * KMH)), longpile=dict(p=dict(Lv=123.6)),
            fastcrane=dict(p=dict(lift_s=1800.0)), joint=dict(p=dict(roro_s=3 * 3600.0), joint=dict(L_tide=6.0, per_tide=1, K_u=1)),
            jointshared=dict(p=dict(roro_s=3 * 3600.0, unload_first=True), joint=dict(L_tide=6.0, per_tide=1, K_u=0)))
GRID = dict(modes=["on_road", "pull_in"], L=[2, 3, 4, 6, 8, 12, 18, 24], K=[1, 2, 3, 4, 5, 6], S=[0, 1, 2, 3, 4, 6], G=[3, 24], n_cradles=6)
SC5 = ["base", "slow", "longslow", "lane", "fastcrane"]
PARTS = dict(
    e1=dict(GRID, title="E1 window bound and simulation (Fig. 2, regime map)", sets=[dict(kinds=["A1"], scen=list(SCEN)), dict(kinds=["A2", "A3"], scen=["base", "longslow", "lane"])],
            lifts=["cradle", "mixed"], hold=[0]),
    e1h=dict(GRID, title="E1 gate holding places Q_h (one dimension of the regime map)", sets=[dict(kinds=["A1"], scen=SC5)], lifts=["cradle"], hold=[1, 2, "inf"]),
    rel=dict(title="Release time of direct lifts (sensitivity)", modes=GRID["modes"], K=[1, 2, 3], L=[4, 12], G=[3, 24], frac=[0.0, 0.25, 0.5, 1.0], n_cradles=6),
    e3=dict(title="E3 representation gap: fixed-time / occupancy (Table 3, Fig. 3)", scen=SC5, modes=GRID["modes"], K=[1, 2, 3, 4, 5, 6, 7, 8], S=[0, 1, 3], n_v=[3, 10],
            L=[6, 12], G=24, open_h=200, n_cradles=6, hold=[0, "inf"], kref=[1, 2, 3, 4], calib_n=10, bisect=40))


def code_sha():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}


def config(part):
    code = code_sha()
    return dict(task="e1e3", part=part, title=PARTS[part]["title"], grid=PARTS[part], scen=SCEN, base=S.BASE, tide_h=TIDE,
                inputs={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in INPUTS}, code=code,
                code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest())


def point_cfg(sc, kind, mode, **kw):
    """Simulation config of one point (format of windport.sim.setup)."""
    s = SCEN[sc]
    geo = dict(dict(kind=kind, n_cradles=kw.pop("n_cradles"), cradle_mode=mode), **s.get("geo", {}))
    return dict(geo=geo, p=dict(s.get("p", {}), **kw.pop("p", {})), **kw)


def lift_s(sc):
    return SCEN[sc].get("p", {}).get("lift_s", S.BASE["lift_s"])


def keys(part):
    g = PARTS[part]
    out = []
    if part in ("e1", "e1h"):
        for st in g["sets"]:
            for kind, sc, mode, L, K, Sn, G, h in itertools.product(st["kinds"], st["scen"], g["modes"], g["L"], g["K"], g["S"], g["G"], g["hold"]):
                for lift in (["direct"] if Sn == 0 else g["lifts"]):
                    out.append(f"{kind}|{sc}|{mode}|{lift}|L{L}|K{K}|S{Sn}|G{G}|H{h}")
    elif part == "rel":
        for mode, K, L, G in itertools.product(g["modes"], g["K"], g["L"], g["G"]):
            out += [f"A1|base|{mode}|direct|L{L}|K{K}|S0|G{G}|H0|X{x}" for x in g["frac"]]
            out.append(f"A1|base|{mode}|cradle|L{L}|K{K}|S1|G{G}|H0|X0.0")
    else:
        for sc, mode, K, Sn, h in itertools.product(g["scen"], g["modes"], g["K"], g["S"], g["hold"]):
            out += [f"port|{sc}|{mode}|occ|n{n}|K{K}|S{Sn}|H{h}" for n in g["n_v"]]
            out += [f"win|{sc}|{mode}|occ|L{L}|K{K}|S{Sn}|H{h}" for L in g["L"]]
        out += [f"fix|{sc}|{mode}|S{Sn}|R{r}" for sc, mode, Sn, r in itertools.product(g["scen"], g["modes"], g["S"], g["kref"])]
    return out


def hold_val(s):
    return "inf" if s == "inf" else int(s)


def cfg_of(part, key):
    g = PARTS[part]
    f = key.split("|")
    if part in ("e1", "e1h", "rel"):
        kind, sc, mode, lift = f[:4]
        L, K, Sn, G = (int(x[1:]) for x in f[4:8])
        c = point_cfg(sc, kind, mode, n_cradles=g["n_cradles"], S=Sn, K=K, lift=lift if Sn else "cradle", horizon_h=G + L + 1,
                      cal=dict(crane=[[G, G + L]]), n_load=int(L * 3600 // lift_s(sc)) + K + Sn + 2, hold=hold_val(f[8][1:]),
                      p=dict(release_frac=float(f[9][1:])) if len(f) > 9 else {})
        jt = SCEN[sc].get("joint")
        if jt:
            n = int(math.ceil((G + L + 1) / TIDE))
            c["cal"]["ramp"] = [[i * TIDE, i * TIDE + jt["L_tide"]] for i in range(n)]
            c.update(n_unload=n * jt["per_tide"], unload_release_h=[i * TIDE for i in range(n) for _ in range(jt["per_tide"])],
                     joint_cut="corr_lane_0", K_u=jt["K_u"])
        return c
    what, sc, mode = f[:3]
    if what == "fix":
        return None
    K, Sn, h = int(f[5][1:]), int(f[6][1:]), hold_val(f[7][1:])
    return e3_cfg(what, sc, mode, int(f[4][1:]), K, Sn, h, False, 1.0)


def e3_cfg(what, sc, mode, nL, K, Sn, h, fixed, fac):
    """One E3 point: what = port (port time to load n piles) or win (piles within window L); if fixed, both speeds times 1/fac."""
    g = PARTS["e3"]
    sp = {} if not fixed else dict(v_loaded=SCEN[sc].get("p", {}).get("v_loaded", S.BASE["v_loaded"]) / fac,
                                   v_empty=S.BASE["v_empty"] / fac)
    G = g["G"]
    if what == "port":
        return point_cfg(sc, "A1", mode, n_cradles=g["n_cradles"], S=Sn, K=K, horizon_h=G + g["open_h"], cal=dict(crane=[[G, G + g["open_h"]]]),
                         n_load=nL, fixed=fixed, hold=h, p=sp)
    return point_cfg(sc, "A1", mode, n_cradles=g["n_cradles"], S=Sn, K=K, horizon_h=G + nL + 1, cal=dict(crane=[[G, G + nL]]),
                     n_load=int(nL * 3600 // lift_s(sc)) + K + Sn + 2, fixed=fixed, hold=h, p=sp)


def port_h(c, sim):
    n = c["n_load"]
    lifts = sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)
    return (lifts[n - 1] - c["cal"]["crane"][0][0] * 3600.0) / 3600.0 if len(lifts) >= n else None


def run_one(c):
    net, p, sim, r = S.simulate(c)
    D, _, _, _, starts, quay, cal = S.setup(c)
    chk = C.check(net, p, sim.trips, starts, quay, cal, c.get("fixed", False), S.ramp_res(D), S.hold_of(c), sim.H)
    r.update(check_ok=chk["ok"], check_err=chk["errors"][:3], check_ratio=chk["max_ratio"], map_sha256=net.map_sha256)
    return c, sim, r


def fix_group(key):
    """One fixed-time group of E3: calibrate f by bisection, then compute port time and window piles for every K."""
    g = PARTS["e3"]
    _, sc, mode, Sn, R = key.split("|")
    Sn, kref = int(Sn[1:]), int(R[1:])
    occ = [port_h(c, sim) for c, sim, _ in (run_one(e3_cfg("port", sc, mode, g["calib_n"], K, Sn, 0, False, 1.0)) for K in [kref])]
    target = occ[0]
    fx = lambda f: port_h(*run_one(e3_cfg("port", sc, mode, g["calib_n"], kref, Sn, 0, True, f))[:2])
    lo, hi = 1.0, 1.0
    if fx(1.0) < target - 1e-6:
        hi = 2.0
        while fx(hi) < target - 1e-6:
            lo, hi = hi, hi * 2
        for _ in range(g["bisect"]):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if fx(mid) < target - 1e-6 else (lo, mid)
    out = dict(key=key, factor=hi, target_h=target, rows=[], check_ok=True, check_err=[])
    for what, nL, K in [("port", n, K) for n in g["n_v"] for K in g["K"]] + [("win", L, K) for L in g["L"] for K in g["K"]]:
        c, sim, r = run_one(e3_cfg(what, sc, mode, nL, K, Sn, 0, True, hi))
        out["check_ok"] &= r["check_ok"]
        out["check_err"] += r["check_err"][:1]
        out["rows"].append(dict(what=what, nL=nL, K=K, sim=sum(r["n_vessel"]) if what == "win" else len(r["lifts"]),
                                port_h=port_h(c, sim) if what == "port" else None, trips=r["trips"]))
    return out


def fname(key):
    return key.replace("|", "_") + ".json"


# ---------------------------------------------------------------- worker processes
_OUT = None


def init(out):
    global _OUT
    _OUT = Path(out)


def run_chunk(arg):
    part, ks = arg
    for k in ks:
        if k.startswith("fix|"):
            r = fix_group(k)
        else:
            c, sim, r = run_one(cfg_of(part, k))
            r["key"] = k
            if k.startswith("port"):
                r["port_h"] = port_h(c, sim)
        write_json(_OUT / "points" / fname(k), r)
    return ks


# ---------------------------------------------------------------- aggregation
COLS = ["key", "kind", "scen", "mode", "lift", "repr", "hold", "frac", "kref", "factor", "L", "K", "S", "G", "n_v", "sim", "w1", "w1_any", "gap",
        "binding", "regime", "interface", "turnover", "fleet", "cut", "zone", "prep", "cut_res", "tl", "te", "c", "dq", "k_dagger", "rate_h",
        "port_h", "n_ramp", "thm3", "thm3_over", "thm4_gap", "exit_hold", "exit_yard", "check_ok", "check_ratio", "trips"]


def regime(binding):
    """Regime: interface-limited (crane) / staging-limited (cradles + in-window transport: fleet, cut, quay zone, cradle turnover) /
    flow-limited (transport before the window: preparation term); if several terms bind, one is recorded in the order
    interface → flow → staging."""
    b = set(binding.split("+"))
    return "interface" if "interface" in b else ("flow" if "prep" in b else "staging")


def rows_of(part, key, r):
    f = key.split("|")
    if f[0] == "fix":
        g = PARTS["e3"]
        return [dict(key=f"{key}|{x['what']}{x['nL']}|K{x['K']}", kind="A1", scen=f[1], mode=f[2], lift="direct" if f[3] == "S0" else "cradle",
                     repr="fixed", hold=0, kref=int(f[4][1:]), factor=round(r["factor"], 9), K=x["K"], S=int(f[3][1:]), G=g["G"],
                     **({"n_v": x["nL"]} if x["what"] == "port" else {"L": x["nL"]}), sim=x["sim"],
                     port_h="" if x["port_h"] is None else round(x["port_h"], 6), check_ok=int(r["check_ok"]), trips=x["trips"])
                for x in r["rows"]]
    out = dict(key=key, trips=r["trips"], check_ok=int(r["check_ok"]), check_ratio=round(r["check_ratio"], 6),
               exit_hold=r["exits"].get("hold", 0), exit_yard=r["exits"].get("yard", 0))
    if part != "e3":
        out.update(kind=f[0], scen=f[1], mode=f[2], lift=f[3], repr="occ", L=int(f[4][1:]), K=int(f[5][1:]), S=int(f[6][1:]), G=int(f[7][1:]),
                   hold=f[8][1:], frac=float(f[9][1:]) if len(f) > 9 else 0.0)
    else:
        out.update(kind="A1", scen=f[1], mode=f[2], lift="direct" if f[6] == "S0" else "cradle", repr="occ", K=int(f[5][1:]), S=int(f[6][1:]),
                   G=PARTS["e3"]["G"], hold=f[7][1:], **({"n_v": int(f[4][1:])} if f[0] == "port" else {"L": int(f[4][1:])}))
        out["port_h"] = "" if r.get("port_h") is None else round(r["port_h"], 6)
    out["sim"] = sum(r["n_vessel"]) if f[0] != "port" else len(r["lifts"])
    w = r.get("w1")
    if w:
        out.update(cut_res=w["cut"], tl=round(w["tl"], 3), te=round(w["te"], 3), c=round(w["c"], 3), dq=round(w["dq"], 3),
                   k_dagger=round(w["k_dagger"], 6), rate_h=round(w["rate_h"], 6))
        if f[0] != "port":
            out.update(w1=w["bound"], w1_any=w["any_hist"], gap=w["bound"] - out["sim"], binding=w["binding"], regime=regime(w["binding"]),
                       **{k: ("inf" if w["terms"].get(k, "") is None else w["terms"].get(k, "")) for k in ("interface", "turnover", "fleet", "cut", "zone", "prep")})
    if "thm3" in r:
        out.update(n_ramp=sum(r["n_ramp"]), thm3=sum(r["thm3"]["bound"]),
                   thm3_over=sum(max(0, a - b) for a, b in zip(r["n_ramp"], r["thm3"]["bound"])))
    if "thm4_gap" in r:
        out["thm4_gap"] = round(r["thm4_gap"], 3)
    return [out]


def aggregate(part, out, ks):
    rows = [x for k in ks for x in rows_of(part, k, json.loads((out / "points" / fname(k)).read_text(encoding="utf-8")))]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=list(PARTS))
    ap.add_argument("--procs", type=int, default=23)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=40)
    ap.add_argument("--aggregate-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = config(a.part)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_{a.part}_{h}"
    ks = keys(a.part)
    if a.aggregate_only:
        aggregate(a.part, out, ks)
        print(out)
        return
    (out / "points").mkdir(parents=True, exist_ok=True)
    cf = out / "config.json"
    if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != cfg:
        raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
    cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    todo = [k for k in ks if not (out / "points" / fname(k)).exists()]
    prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, cfg["title"], "e1e3")
    chunk = 1 if a.part == "e3" else a.chunk
    chunks = [(a.part, todo[i:i + chunk]) for i in range(0, len(todo), chunk)]
    failed = 0
    try:
        for ds in slot_imap(run_chunk, chunks, a.procs, initializer=init, initargs=(str(out),),
                            slots_dir=a.slots, tag="e1e3"):
            prog.write(done=prog.d["done"] + len(ds))
    except Exception as e:
        failed = 1
        prog.write(state="failed", note=repr(e)[:300])
        raise
    rows = aggregate(a.part, out, ks)
    bad = sum(1 for r in rows if not r["check_ok"])
    over = sum(1 for r in rows if r["repr"] == "occ" and isinstance(r.get("gap"), int) and r["gap"] < 0)
    prog.write(state="failed" if failed else "done", note=f"checker failed at {bad} points; occupancy simulation above W1 at {over} points")
    print(out)


if __name__ == "__main__":
    main()
