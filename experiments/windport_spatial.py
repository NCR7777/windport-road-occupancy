"""The spatial additions: simulation batches that strengthen the offshore-wind study (occupancy/, bounds/, exact/ and the modules of the
E1-E3 batches, the E4-E7 batches and the extra analyses are unchanged; the new semantics are in windport/sim4.py, bound4.py, check4.py).
Settings as in the E4-E7 batches and the extra analyses: gate holding places Q_h = 0, direct and mixed lifting release the vehicle when the
lift starts (x = 0), jacking and set-down 30 min each.
Window points record the simulated delivery sim, W″ (windport/bound4.py; equal to W′ without reach and reserved periods) and the five
regimes; port-time points record the port time to load n_v piles, L*(n_v) and W″(port time). All points are checked by windport/check4.py
(points with the cut as a single resource by check3).

--part sites    Relaxed storage area (holds three voyages, 30 piles; windport.sim4.SITES_MULTI: Okpo zone_trace_001 6.82 ha, Yantai
                zone_trace_030 5.04 ha): rerun the full E6 grid (Okpo, Yantai × cradle mode × base / 1 km/h / crane 0.5 h × L = 4, 6, 12,
                24 h × K = 1–8 × S = 0–min(4, cradle bays) × G = 3, 24 h × FCFS / convoy). Results for the one-voyage storage area are taken
                from the committed runs/e6.
--part siteport Two storage areas × cradle mode × base / 1 km/h × lifting arrangement (Okpo S0, S1, S1m, S3, S3m; Yantai S0, S1, S1m) ×
                K = 1–8: port time for one vessel of 10 piles and L*(10) (crane open for 200 h from G = 24 h).
                The relaxed storage area also gets gate holding places Q_h = 1 and unlimited (keys carry hold; keys with Q_h = 0 unchanged).
--part hphd     Jacking / set-down extended to 1.5 and 2 h (h_p = h_d), plus Kassels' Rønne handling (h_p = 2 h, h_d = 0.5 h), applied to
                the reduced grids (a) E1, (b) E4, (c) E3 of Appendix C (as windport_runs --part sens; the base row is taken from the committed
                runs/sens).
--part reach    Table 7 (exchange rate) and Fig. 7 under two cradle layouts. Tandem (A1, one cradle every 110 m along the apron) × base /
                long single lane 1 km/h × cradle mode × L = 12 h × G = 24 h × K = 1–10 × S = 1–6 × cradle / mixed lifting × crane reach
                (S_r, t_sh) = (1, 1 h), (2, 0.5 h), (2, 1 h), (2, 2 h); side-by-side (windport.sim4.build_side: one 40 m spur per cradle,
                pitch 20 m, all reachable) × same scenarios × K = 1–10 × S = 0–6 × cradle / mixed lifting.
                Tandem with unlimited reach is taken from the committed E4 points (cradle) and mix6 points of the extra analyses (mixed).
                Tandem with reach also gets two dispatch variants (keys carry disp): finish = choose the quay bay by lift-finish time,
                prestage = far cradles only pre-stage before the window (windport.sim4.ReachMixin); the same applies to tandem with reach
                in upsize.
--part upsize   Fig. 7 upsizing under both layouts: tandem (S_r = 2, t_sh = 1 h; S = 3) and side-by-side (S = 1, 3) × base / long single
                lane × four monopile levels × K = 1–6, otherwise as E7 (single lane 12 m wide, L = 12 h, G = 24 h).
--part turn     At the turns that windport_spatial_analytic --part turn found to sweep over buildings or water, the loaded turn uses an
                alternative manoeuvre with an extra stop of 600 s or 1,800 s; two storage areas × cradle mode × base × L = 12 h ×
                G = 24 h × K = 1–8 × S = 0–min(4, cradle bays) × FCFS.
--part reserve  Sharing with block transport: the shared road section (windport.sim4.reserve_road) reserves f = 10%, 25%, 50% of every
                2 h for block transport; two storage areas × cradle mode × base × L = 12 h × G = 24 h × K = 1–8 × S = 0, 1, 3
                (Yantai 0, 1) × FCFS.
--part ablate   Component ablation (cumulative): s1 switches off loaded steering stops and junction sweep (sweep_steer_s = None,
                turn_sweep_s = 0); s2 also makes the loaded length independent of the load (Lv = empty length 30 m); s3 also replaces the
                segment-level network by the cut as a single resource (windport/sim3.py). (a) Port time: A1 × five scenarios × cradle
                mode × S0, S1, S1m, S3 × K = 1–8 × n_v = 10; (b) window delivery: A1 × base / long single lane × cradle mode × L = 12 h ×
                G = 24 h × K = 1–10 × S = 0, 1, 3.
                The full model is taken from the committed port points of the extra analyses (FCFS, Q_h = 0, n_v = 10) and E4 points;
                step 4 (Q = K) changes only the bound and is computed in the report.
                Also cf = the cut as a single resource applied directly to the full model (without first switching off steering or
                changing L_v), which gives the attribution in another order.
--part cdv      Simulation check of the co-design: reads the configuration list given by --input (chosen.json written by
                windport_spatial_analytic --part codesign) and computes port time and L*(n_v) for each configuration.
Output results/windport_spatial_<part>_<config hash>/: config.json, progress.json, points/ (one JSON per point, resume cache),
points.csv (no wall-clock times).
Run: python experiments/windport_spatial.py --part sites --procs 11 --slots DIR
"""
import argparse
import csv
import hashlib
import itertools
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap, write_json      # noqa: E402
from windport import bound3 as B3                                # noqa: E402
from windport import bound4 as B4                                # noqa: E402
from windport import check4 as C4                                # noqa: E402
from windport import sim as S                                    # noqa: E402
from windport import sim2 as S2                                  # noqa: E402
from windport import sim3 as S3                                  # noqa: E402
from windport import sim4 as S4                                  # noqa: E402
import windport_runs as T                                        # noqa: E402

CODE = ["windport/sim.py", "windport/sim2.py", "windport/sim3.py", "windport/sim4.py", "windport/bound.py", "windport/bound2.py",
        "windport/bound3.py", "windport/bound4.py", "windport/check.py", "windport/check3.py", "windport/check4.py", "windport/archetypes.py",
        "windport/shipyard.py", "occupancy/sim.py", "occupancy/network.py", "occupancy/params.py", "occupancy/tasks.py", "exact/check.py",
        "experiments/windport_runs.py", "experiments/windport_spatial.py"]
INPUTS = ["data/register/parameters.csv"]
def turn_file():
    """turn_extra.json of windport_spatial_analytic --part turn (the result directory name changes with that script's hash; checked by
    content: config records its SHA-256)."""
    fs = sorted(ROOT.glob("results/runs/spatial_turn_sweep/turn_extra.json"))
    assert len(fs) == 1, f"need exactly one turn result directory: {fs}"
    return fs[0]
ARR = dict(S0=(0, "direct"), S1=(1, "cradle"), S1m=(1, "mixed"), S3=(3, "cradle"), S3m=(3, "mixed"))
REACH = {"1_3600": (1, 3600.0), "2_1800": (2, 1800.0), "2_3600": (2, 3600.0), "2_7200": (2, 7200.0)}
ABL = dict(s1=dict(sweep_steer_s=None, turn_sweep_s=0.0), s2=dict(sweep_steer_s=None, turn_sweep_s=0.0, Lv=30.0), cf={})
CUT = ("s3", "cf")                 # the two steps with the cut as a single resource: s3 after s2, cf applied directly to the full model
DISP = dict(finish=dict(reach_key="finish"), prestage=dict(far_prestage=True))    # dispatch variants for choosing the quay bay under reach
GRIDS = dict(
    sites=dict(title="Relaxed storage area: E6 grid", storage="multi", **{k: T.GRIDS["e6"][k] for k in ("sites", "scen", "L", "K", "G", "rule")}),
    siteport=dict(title="Port time with two storage areas", sites=["okpo", "yantai"], storage=["runs", "multi"], scen=["base", "slow"],
                  arr=dict(okpo=["S0", "S1", "S1m", "S3", "S3m"], yantai=["S0", "S1", "S1m"]), K=list(range(1, 9)), n_v=10, G=24, open_h=200, hold=["1", "inf"]),
    hphd=dict(title="Jacking / set-down up to 2 h and Rønne handling", levels={"5400": dict(hp_s=5400.0, hd_s=5400.0), "7200": dict(hp_s=7200.0, hd_s=7200.0),
                                                                  "kas": dict(hp_s=7200.0, hd_s=1800.0)},
              sub={k: T.GRIDS["sens"][k] for k in ("e1", "e4", "e3")}),
    reach=dict(title="Crane reach and side-by-side cradles: Table 7 exchange rate", scen=["base", "lane"], L=12, G=24, K=list(range(1, 11)), S=list(range(1, 7)),
               lift=["cradle", "mixed"], reach=list(REACH), side=dict(n_cradles=6, pitch_m=20.0, bay_m=40.0, S=list(range(0, 7))),
               disp=list(DISP)),
    upsize=dict(title="Upsizing under two layouts", scen=["base", "lane"], lev=list(T.E7LEV), K=list(range(1, 7)), tandem_S=[3], side_S=[1, 3],
                reach="2_3600", L=12, G=24, disp=list(DISP)),
    turn=dict(title="Alternative turning manoeuvres", sites=["okpo", "yantai"], storage=["runs", "multi"], extra=[600.0, 1800.0], K=list(range(1, 9)), L=12, G=24),
    reserve=dict(title="Road section shared with block transport", sites=["okpo", "yantai"], storage=["runs", "multi"], f=[0.1, 0.25, 0.5], T_h=2.0, K=list(range(1, 9)),
                 S=dict(okpo=[0, 1, 3], yantai=[0, 1]), L=12, G=24),
    ablate=dict(title="Component ablation", steps=["s1", "s2", "s3", "cf"], port=dict(scen=T.SC5, arr=["S0", "S1", "S1m", "S3"], K=list(range(1, 9)), n_v=10,
                                                                        G=24, open_h=200),
                win=dict(scen=["base", "lane"], K=list(range(1, 11)), S=[0, 1, 3], L=12, G=24)),
    cdv=dict(title="Simulation check of the co-design", G=24, open_h=200),
)


def side_geo(sc):
    g = GRIDS["reach"]["side"]
    return dict(dict(kind="A1side", n_cradles=g["n_cradles"], pitch_m=g["pitch_m"], bay_m=g["bay_m"]), **T.SCEN[sc].get("geo", {}))


def turn_extra(site, st, x):
    ex = json.loads(turn_file().read_text(encoding="utf-8"))
    return {n: x for n in ex[f"{site}|{st}"]}


def keys(part, cd=None):
    g, out = GRIDS[part], []
    if part == "sites":
        for site in g["sites"]:
            for m, sc, L, K, Sn, G, r in itertools.product(T.MODES, g["scen"], g["L"], g["K"], range(0, min(4, T.NC[site]) + 1), g["G"], g["rule"]):
                out.append(dict(kind="map:" + site, st="multi", scen=sc, mode=m, lift=T.lift_of(Sn), rule=r, L=L, K=K, S=Sn, G=G))
    elif part == "siteport":
        for site, st, m, sc in itertools.product(g["sites"], g["storage"], T.MODES, g["scen"]):
            for arr, K in itertools.product(g["arr"][site], g["K"]):
                out.append(dict(what="port", kind="map:" + site, st=st, scen=sc, mode=m, arr=arr, K=K, n_v=g["n_v"]))
        for site, m, sc, h in itertools.product(g["sites"], T.MODES, g["scen"], g["hold"]):
            for arr, K in itertools.product(g["arr"][site], g["K"]):
                out.append(dict(what="port", kind="map:" + site, st="multi", scen=sc, mode=m, arr=arr, K=K, n_v=g["n_v"], hold=h))
    elif part == "hphd":
        for lv in g["levels"]:
            a = g["sub"]["e1"]
            for sc, m, L, K, Sn, G in itertools.product(a["scen"], T.MODES, a["L"], a["K"], a["S"], a["G"]):
                out.append(dict(sub="e1", lv=lv, kind="A1", scen=sc, mode=m, lift=T.lift_of(Sn), rule="fcfs", L=L, K=K, S=Sn, G=G))
            a = g["sub"]["e4"]
            for sc, m, L, K, Sn, G in itertools.product(a["scen"], T.MODES, a["L"], a["K"], a["S"], a["G"]):
                out.append(dict(sub="e4", lv=lv, kind="A1", scen=sc, mode=m, lift=T.lift_of(Sn), rule="fcfs", L=L, K=K, S=Sn, G=G))
            a = g["sub"]["e3"]
            for sc, m, K, rep in itertools.product(a["scen"], T.MODES, a["K"], ["occ", "fix"]):
                out.append(dict(sub="e3", lv=lv, kind="A1", scen=sc, mode=m, lift="cradle", rule="fcfs", rep=rep, n_v=a["n_v"], K=K, S=a["S"], G=a["G"]))
    elif part == "reach":
        for sc, m, K, Sn, lf, rc in itertools.product(g["scen"], T.MODES, g["K"], g["S"], g["lift"], g["reach"]):
            out.append(dict(lay="tandem", kind="A1", scen=sc, mode=m, lift=lf, rule="fcfs", reach=rc, L=g["L"], K=K, S=Sn, G=g["G"]))
        for sc, K, Sn in itertools.product(g["scen"], g["K"], g["side"]["S"]):
            for lf in (["direct"] if Sn == 0 else g["lift"]):
                out.append(dict(lay="side", kind="A1side", scen=sc, mode="side", lift=lf, rule="fcfs", reach="all", L=g["L"], K=K, S=Sn, G=g["G"]))
        for sc, m, K, Sn, lf, rc, ds in itertools.product(g["scen"], T.MODES, g["K"], g["S"], g["lift"], g["reach"], g["disp"]):
            out.append(dict(lay="tandem", kind="A1", scen=sc, mode=m, lift=lf, rule="fcfs", reach=rc, L=g["L"], K=K, S=Sn, G=g["G"], disp=ds))
    elif part == "upsize":
        for sc, m, lv, K, Sn in itertools.product(g["scen"], T.MODES, g["lev"], g["K"], g["tandem_S"]):
            out.append(dict(lay="tandem", kind="A1", scen=sc, mode=m, lift="cradle", rule="fcfs", reach=g["reach"], lev=lv, L=g["L"], K=K, S=Sn, G=g["G"]))
        for sc, lv, K, Sn in itertools.product(g["scen"], g["lev"], g["K"], g["side_S"]):
            out.append(dict(lay="side", kind="A1side", scen=sc, mode="side", lift="cradle", rule="fcfs", reach="all", lev=lv, L=g["L"], K=K, S=Sn, G=g["G"]))
        for sc, m, lv, K, Sn, ds in itertools.product(g["scen"], T.MODES, g["lev"], g["K"], g["tandem_S"], g["disp"]):
            out.append(dict(lay="tandem", kind="A1", scen=sc, mode=m, lift="cradle", rule="fcfs", reach=g["reach"], lev=lv, L=g["L"], K=K, S=Sn, G=g["G"],
                            disp=ds))
    elif part in ("turn", "reserve"):
        var = g["extra"] if part == "turn" else g["f"]
        for site, st, m, x in itertools.product(g["sites"], g["storage"], T.MODES, var):
            Ss = range(0, min(4, T.NC[site]) + 1) if part == "turn" else g["S"][site]
            for K, Sn in itertools.product(g["K"], Ss):
                d = dict(kind="map:" + site, st=st, scen="base", mode=m, lift=T.lift_of(Sn), rule="fcfs", L=g["L"], K=K, S=Sn, G=g["G"])
                d["extra" if part == "turn" else "f"] = x
                out.append(d)
    elif part == "ablate":
        a = g["port"]
        for st, sc, m, arr, K in itertools.product(g["steps"], a["scen"], T.MODES, a["arr"], a["K"]):
            out.append(dict(what="port", step=st, kind="A1", scen=sc, mode=m, arr=arr, K=K, n_v=a["n_v"]))
        a = g["win"]
        for st, sc, m, K, Sn in itertools.product(g["steps"], a["scen"], T.MODES, a["K"], a["S"]):
            out.append(dict(what="win", step=st, kind="A1", scen=sc, mode=m, lift=T.lift_of(Sn), rule="fcfs", L=a["L"], K=K, S=Sn, G=a["G"]))
    elif part == "cdv":
        out = [dict(what="port", cd=json.dumps(x, sort_keys=True)) for x in cd]
    return [T.enc(d) for d in out]


# ---------------------------------------------------------------- configuration of one point
def port_cfg(geo, p, Sn, lift, K, n_v, G=24, open_h=200, hold=0):
    return dict(geo=geo, p=p, S=Sn, K=K, lift=lift, horizon_h=G + open_h, cal=dict(crane=[[G, G + open_h]]), n_load=n_v, fixed=False, hold=hold,
                rule="fcfs")


def cfg_of(part, d):
    if part == "cdv":
        x = json.loads(d["cd"])
        return port_cfg(x["geo"], x["p"], x["S"], x["lift"], x["K"], x["n_v"], GRIDS["cdv"]["G"], GRIDS["cdv"]["open_h"], x.get("hold", 0))
    if part == "hphd":
        lv = GRIDS["hphd"]["levels"][d["lv"]]
        base = {k: v for k, v in d.items() if k != "lv"}
        c = T.cfg_of("sens", T.enc(dict(base, par="none", val=0)))
        c["p"] = dict(c["p"], **lv)
        return c
    if d.get("what") == "port":
        site = d["kind"][4:] if d["kind"].startswith("map:") else None
        Sn, lift = ARR[d["arr"]]
        sc = T.SCEN[d["scen"]]
        p = dict(sc.get("p", {}))
        if site:
            geo = dict(kind="map", site=site, cradle_mode=d["mode"], n_cradles=T.NC[site])
            if d["st"] == "multi":
                geo["storage"] = "multi"
        else:
            geo = dict(dict(kind="A1", n_cradles=6, cradle_mode=d["mode"]), **sc.get("geo", {}))
        if d.get("step"):
            p.update(ABL.get(d["step"], ABL["s2"]))
        g = GRIDS["ablate"]["port"] if d.get("step") else GRIDS["siteport"]
        hold = d.get("hold", "0")
        c = port_cfg(geo, p, Sn, lift, int(d["K"]), int(d["n_v"]), g["G"], g["open_h"])
        c["fixed"] = d.get("step") in CUT
        c["hold"] = "inf" if hold == "inf" else int(hold)
        return c
    if d["kind"].startswith("map:"):
        base = {k: v for k, v in d.items() if k not in ("st", "extra", "f")}
        c = T.cfg_of("e6", T.enc(base))
        if d["st"] == "multi":
            c["geo"] = dict(c["geo"], storage="multi")
        if "extra" in d:
            c["p"] = dict(c["p"], turn_extra=turn_extra(d["kind"][4:], d["st"], float(d["extra"])))
        if "f" in d:
            c["reserve"] = dict(f=float(d["f"]), T_h=GRIDS["reserve"]["T_h"])
        return c
    if part == "upsize":
        base = dict(kind="A1", scen=d["scen"], mode="on_road" if d["mode"] == "side" else d["mode"], lift="cradle", rule="fcfs", lev=d["lev"],
                    L=d["L"], K=d["K"], S=d["S"], G=d["G"])
        c = T.cfg_of("e7", T.enc(base))
    else:
        base = dict(kind="A1", scen=d["scen"], mode="on_road" if d["mode"] == "side" else d["mode"], lift=T.lift_of(d["S"]), rule="fcfs",
                    L=d["L"], K=d["K"], S=d["S"], G=d["G"])
        c = T.cfg_of("e4", T.enc(base))
        c["lift"] = d["lift"]
    if d.get("lay") == "side":
        c["geo"] = dict(side_geo(d["scen"]), **({"corridor_w": c["geo"]["corridor_w"]} if "corridor_w" in c["geo"] else {}))
    if d.get("reach") in REACH:
        Sr, sh = REACH[d["reach"]]
        c["p"] = dict(c["p"], reach=Sr, shift_s=sh, **DISP.get(d.get("disp"), {}))
    if d.get("step"):
        c["p"] = dict(c["p"], **ABL.get(d["step"], ABL["s2"]))
        c["fixed"] = d["step"] in CUT
    return c


def check_of(c, net, p, sim, cut=False, rv=None):
    D, _, _, _, starts, quay, cal = S4.setup4(c)
    g, y = S2.idle_nodes(D)
    return C4.check(net, p, sim.trips, starts, quay, cal, c.get("fixed", False) and not cut, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y,
                    cut=cut, reserve=rv)


def run_point(part, key):
    d = T.dec(key)
    c = dict(cfg_of(part, d), w4=False)
    cut = c.get("fixed") and d.get("step") in CUT
    if cut:
        S4.setup4(c)
        net, p, sim, r = S3.simulate3(c)
    else:
        net, p, sim, r = S4.simulate4(c)
    rv = None
    if r.get("reserve"):
        rv = dict(res=tuple(r["reserve"]["res"].split("|")), f=r["reserve"]["f"], T=r["reserve"]["T"], H_end=(c["horizon_h"] + 1) * 3600.0)
    ck = check_of(c, net, p, sim, cut=cut, rv=rv)
    out = dict(key=key, trips=len(sim.trips), check_ok=ck["ok"], check_err=ck["errors"][:2], n_far=ck["n_far"], n_res=ck["n_res"],
               map_sha256=net.map_sha256, exits=r.get("exits"))
    if r.get("reserve"):
        out["reserve"] = r["reserve"]
    cb = dict(c, fixed=False)
    w = B4.parts4(cb)
    f = B4.wprime4_fn(cb, w)
    G = c["cal"]["crane"][0][0] * 3600.0
    if d.get("what") == "port" or d.get("rep"):
        n = c["n_load"]
        ls = sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)
        ph = (ls[n - 1] - G) / 3600.0 if len(ls) >= n else None
        lo, hi = B3.lstar(f, n)
        out.update(port_h=ph, lifts=len(ls), lstar_lo=lo / 3600.0, lstar_hi=hi / 3600.0, w_at_port=None if ph is None else f(ph * 3600.0))
    else:
        L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * 3600.0
        cl = B4.classify(cb, w)
        out.update(sim=sum(r["n_vessel"]), w4=f(L), wprime=B4.wprime_fast(cb, w)(L), cls=cl["cls"], sub=cl["sub"], nature=cl["nature"],
                   binding=cl["binding"], terms=cl["terms"])
    return out


# ---------------------------------------------------------------- run and aggregate
_OUT, _PART = None, None


def init(out, part):
    global _OUT, _PART
    _OUT, _PART = Path(out), part
    pin(list(range(1, os.cpu_count())))


def run_chunk(ks):
    for k in ks:
        write_json(_OUT / "points" / T.fname(k), run_point(_PART, k))
    return ks


COLS = ["key", "sim", "w4", "wprime", "cls", "prep_sub", "nature", "binding", "port_h", "lifts", "lstar_lo", "lstar_hi", "w_at_port", "check_ok", "n_far",
        "n_res", "reserve_res", "reserve_tl", "trips"]


def row_of(key, r):
    d = T.dec(key)
    out = dict(d, key=key)
    for k in ("sim", "w4", "wprime", "cls", "sub", "nature", "binding", "lifts", "check_ok", "n_far", "n_res", "trips"):
        if k in r:
            out["prep_sub" if k == "sub" else k] = int(r[k]) if isinstance(r[k], bool) else r[k]
    for k in ("port_h", "lstar_lo", "lstar_hi", "w_at_port"):
        if k in r:
            out[k] = "" if r[k] is None else round(r[k], 6)
    if r.get("reserve"):
        out["reserve_res"], out["reserve_tl"] = r["reserve"]["res"], round(r["reserve"]["tl"], 3)
    return out


def config(part, inp=None):
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="spatial", part=part, title=GRIDS[part]["title"], grid=GRIDS[part], arr=ARR, reach=REACH, ablate=ABL, scen=T.SCEN, base=S.BASE,
               inputs={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in INPUTS}, code=code,
               code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest())
    if part in ("sites", "siteport", "turn", "reserve"):
        cfg["networks"] = {s: T.SY.NETWORK[s] for s in ("okpo", "yantai")}
        cfg["sites_multi"] = S4.SITES_MULTI
    if part == "turn":
        cfg["turn_extra"] = hashlib.sha256(turn_file().read_bytes()).hexdigest()
    if inp:
        cfg["input"] = dict(path=str(Path(inp).relative_to(ROOT)).replace("\\", "/"), sha256=hashlib.sha256(Path(inp).read_bytes()).hexdigest())
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=list(GRIDS))
    ap.add_argument("--procs", type=int, default=11)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=8)
    ap.add_argument("--input", default=None)
    ap.add_argument("--aggregate-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    inp = (ROOT / a.input).resolve() if a.input else None
    cfg = config(a.part, inp)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_spatial_{a.part}_{h}"
    cd = json.loads(inp.read_text(encoding="utf-8")) if inp else None
    ks = keys(a.part, cd)
    if not a.aggregate_only:
        (out / "points").mkdir(parents=True, exist_ok=True)
        cf = out / "config.json"
        if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != json.loads(json.dumps(cfg)):
            raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
        cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        todo = [k for k in ks if not (out / "points" / T.fname(k)).exists()]
        prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, cfg["title"], "spatial")
        chunks = [todo[i:i + a.chunk] for i in range(0, len(todo), a.chunk)]
        try:
            for ds in slot_imap(run_chunk, chunks, a.procs, initializer=init, initargs=(str(out), a.part), slots_dir=a.slots, tag="spatial"):
                prog.write(done=prog.d["done"] + len(ds))
        except Exception as e:
            prog.write(state="failed", failed=1, note=repr(e)[:300])
            raise
    rows = [row_of(k, json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8"))) for k in ks]
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
    bad = sum(1 for r in rows if not r["check_ok"])
    occ = lambda r: r.get("step") not in CUT and r.get("rep") != "fix"       # bound applies to the occupancy model only (cut / fixed-time skip roads)
    over = sum(1 for r in rows if r.get("w4") not in (None, "") and occ(r) and r["sim"] > r["w4"])
    nv = lambda r: int(r["n_v"]) if "n_v" in r else json.loads(r["cd"])["n_v"]
    wp = sum(1 for r in rows if r.get("w_at_port") not in (None, "") and occ(r) and r["w_at_port"] < nv(r))
    lb = sum(1 for r in rows if r.get("port_h") not in (None, "") and occ(r) and r["port_h"] < r["lstar_lo"] - 1e-9)
    note = f"checker failed at {bad} points; above W″ at {over} points; W″(port time) < n_v at {wp} points; port time < L* at {lb} points"
    if not a.aggregate_only:
        prog.write(state="done", note=note)
    print(out)
    print(note)


if __name__ == "__main__":
    main()
