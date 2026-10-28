"""Revision studies: simulation batches (main2 geometry; conservative lifting rule t_u = 0.05 p; unified bound W″_lift).
Only the Okpo and Yantai shipyard maps are used; the output is IDs and numbers only, no maps are drawn. The new semantics are
in experiments/windport_revision_lib.py (cradle spacing, near-yard storage slots, turn bans) and windport_revision_buffer.py
(near-yard layout).

--group a  Tables 8 and 10, tandem S ≥ 2: cradle spacing L_v + δ = 115 m (install_spacing); keys, configurations, single points
           and rows otherwise as in the committed batches:
             t8:port   S3 and S3m keys of the extra analyses' port batch (n_v = 10, three representations, Q_h = 0 / 1 /
                       unlimited; windport_rerun_conservative.compute); first-come-first-served also records L*(10) of W″_lift;
             t8:e3     S = 3 keys of E3 in the E1-E3 batches (port time n_v = 10, Q_h = 0 / unlimited; fixed-duration calibration
                       set K_ref = 1-4);
             t8:fix    S3m calibration set of the extra analyses' fix batch (K_ref = 1-4);
             rate:e4   E4 of the E4-E7 batches: A1, base / long single lane, L = 12 h, G = 24 h, first-come-first-served, S = 2-6
                       (the tandem rows of Table 10 "all reachable");
             rate:mix6 the same sub-grid of the extra analyses' mix6 (mixed lifting);
             rate:reach tandem S = 2-6 keys of the spatial additions' reach batch (S_r = 1, 2, t_sh = 0.5 / 1 / 2 h, three
                       berth-picking dispatch rules; windport_rerun_spatial.run_point).
--group b  Table 12: tandem S ≥ 2 in the co-design enumeration space (2 × 512 configurations × n_v = 3, 5, 10), cradle
           spacing 115 m:
             cd        main rule S_r = 1, t_sh = 1 h (as in cd_configs), two quay-berth picking rules (earliest lift start /
                       by lift completion time); all reachable (optimistic, independent of the rule); the long single-lane corridor uses
                       uniform block sections of 150 m (75 / 300 m as main-rule sensitivity), the bound adds the pure loaded cut
                       terms (windport_codesign_blocks), the network cache is keyed by the network parameters (windport_netcache);
             s01       invariance spot check: tandem S ≤ 1 at 115 m (all S ≤ 1 tandem configurations of the base port n_v = 10 and
                       of the long single lane 150 m n_v = 10), compared field by field with the committed points.
--group c  window and transfer under the near-yard storage-slot layout (cradle spacing unchanged):
             bturn     turn sweeps and alternative manoeuvres (1 m clearance, as in windport_turn_alt_clear) on the loaded routes
                       after the layout (near-yard columns → quay; far yard → near-yard columns; at Okpo also with the loaded turn
                       at node_trace_016 banned); writes turn_alt.json;
             bnear     near-yard window (one-voyage keys of the spatial additions' siteport, S = 1) under the layout: slots are
                       picked by column, each pick-up adds a crabbing time (farthest slot); turning feas + switch 30 s / hi +
                       switch 300 s; G = 24 h and 0;
             btr       far → near transfer of 10 piles to the layout columns (each set-down adds a crabbing time); at Okpo also
                       with node_trace_016 banned;
             bmulti    Okpo three-voyage single-level direct loading (siteport multi keys of the spatial additions, S = 1,
                       Q_h = 0 / 1) with node_trace_016 banned.
Output results/windport_revision_<part>_<config hash>/: config.json (SHA-256 of code and inputs, geometry, spacing), progress.json,
points/ (one file per point, resumable), points.csv.
Run: python experiments/windport_revision.py --group a --procs 22 --slots DIR
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
import windport_runs as T                                        # noqa: E402

H = 3600.0
SPACING = 115.0
GROUPS = dict(a=["t8:port", "t8:e3", "t8:fix", "rate:e4", "rate:mix6", "rate:reach"], b=["cd", "s01"], c=["bturn", "bnear", "btr", "bmulti"])
EXTRA = dict(okpo=(), yantai=("zone_trace_022", "zone_trace_024"))     # extra near-yard zones for one voyage (windport_revision_buffer)
BAN = dict(okpo=[["node_trace_016", "road_trace_039", "road_trace_619"]])
LEVELS = dict(feas=("feas", 30.0), hi=("hi", 300.0))                  # turning level + mode switch t_sw for crabbing
CDB = dict(n_v=[3, 5, 10], rc=["main", "all"], disp=["start", "finish"], blk_main=150.0, blk_sens=[75.0, 300.0])
CODE_BASE = ["experiments/windport_revision.py", "experiments/windport_revision_lib.py", "experiments/windport_revision_buffer.py",
             "experiments/windport_turn_alt_clear.py", "experiments/windport_codesign_blocks.py", "experiments/windport_codesign_blocks2.py",
             "experiments/windport_netcache.py", "experiments/windport_rerun_conservative.py", "experiments/windport_sim.py", "experiments/windport_extra.py",
             "experiments/windport_rerun_spatial.py", "experiments/windport_spatial.py", "experiments/windport_turn_sweep.py", "experiments/windport_sites.py"]


def code_files():
    import windport_design as X
    return sorted(set(X.CODE + CODE_BASE))


def code_hash():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in code_files()}


def out_dir(name, extra):
    import windport_design as X
    from windport import archetypes as A
    cfg = dict(task="revision", part=name, geometry=A.GEOMETRIES[X.GEO], code=code_hash(), maps=X.maps(), semantics="lift_tu0.05_head", **extra)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    return ROOT / "results" / f"windport_revision_{name.replace(':', '_')}_{h}", cfg


def wcsv(path, rows, cols=None):
    if cols is None:
        cols = []
        for r in rows:
            cols += [k for k in r if k not in cols]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ================================================================ layouts (main process computes and writes them; workers read)
def plans_dir():
    from windport import shipyard as SY
    import windport_revision_buffer as B
    src = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in ("experiments/windport_revision_buffer.py",)}
    cfg = dict(task="revision", part="plans", extra=EXTRA, code=src, networks={s: SY.NETWORK[s] for s in ("okpo", "yantai")},
               params=dict(res=B.RES, clear=B.CLEAR_M, verge=B.VERGE_M, Lv=B.LV, dm=B.DM, pitch=B.PITCH, delta=B.DELTA))
    out = ROOT / "results" / f"windport_revision_plans_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    return out, cfg


def load_plans(make=True):
    out, cfg = plans_dir()
    f = out / "plans.json"
    if not f.exists() and (ROOT / "results/runs/revision_plans/plans.json").exists():
        f = ROOT / "results/runs/revision_plans/plans.json"      # layouts of the release (computing them needs the yard maps)
    if not f.exists():
        assert make, f"compute the layouts first: {f}"
        import windport_revision_buffer as B
        out.mkdir(parents=True, exist_ok=True)
        (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        plans = {s: B.make_plan(s, EXTRA[s]) for s in ("okpo", "yantai")}
        write_json(f, plans)
    return json.loads(f.read_text(encoding="utf-8")), f


# ================================================================ keys and configurations
def keys(part):
    import windport_sim as WSM
    import windport_extra as X6
    import windport_spatial as TA
    if part == "t8:port":
        return [k for k in X6.keys("port") if T.dec(k)["arr"] in ("S3", "S3m") and T.dec(k)["n_v"] == "10"]
    if part == "t8:e3":
        return [k for k in WSM.keys("e3") if (k.startswith("port|") and k.split("|")[6] == "S3" and k.split("|")[4] == "n10")
                or (k.startswith("fix|") and k.split("|")[3] == "S3")]
    if part == "t8:fix":
        return [k for k in X6.keys("fix") if T.dec(k)["arr"] == "S3m"]
    if part == "rate:e4":
        return [k for k in T.keys("e4") if (lambda d: d["kind"] == "A1" and d["L"] == "12" and d["G"] == "24" and d["rule"] == "fcfs" and int(d["S"]) >= 2)(T.dec(k))]
    if part == "rate:mix6":
        return [k for k in X6.keys("mix6") if (lambda d: d["kind"] == "A1" and d["rule"] == "fcfs" and int(d["S"]) >= 2)(T.dec(k))]
    if part == "rate:reach":
        return [k for k in TA.keys("reach") if (lambda d: d["lay"] == "tandem" and int(d["S"]) >= 2)(T.dec(k))]
    if part == "cd":
        return cd_keys()
    if part == "s01":
        return s01_keys()
    if part == "bnear":
        return bnear_keys()
    if part == "btr":
        return btr_keys()
    if part == "bmulti":
        return bmulti_keys()
    raise KeyError(part)


def fname(part, k):
    import windport_rerun_conservative as RR
    return RR.fname("e1e3:e3", k) if part == "t8:e3" else T.fname(k)


def cd_keys():
    import windport_design as X
    items = X.cd_items()
    out = []
    for i, x in enumerate(items):
        if x["lay"] != "tandem" or x["S"] < 2:
            continue
        for n in CDB["n_v"]:
            base = f"cd={i}|n_v={n}|reach=grid"
            blks = [""] if x["scen"] == "base" else [f"{CDB['blk_main']:g}"] + [f"{b:g}" for b in CDB["blk_sens"]]
            for b in blks:
                tail = f"|blk={b}" if b else ""
                for ds in CDB["disp"]:
                    out.append(base + "|rc=main" + ("|disp=finish" if ds == "finish" else "") + tail)
                if b in ("", f"{CDB['blk_main']:g}"):
                    out.append(base + "|rc=all" + tail)
    return out


def cd_cfg(d):
    import windport_design as X
    import windport_codesign_blocks as BK
    c = X.cd_cfg(dict(cd=d["cd"], n_v=d["n_v"], reach="grid"))
    if d.get("rc") == "all":
        c["p"] = {k: v for k, v in c["p"].items() if k not in ("reach", "shift_s")}
    if d.get("disp") == "finish":
        c["p"] = dict(c["p"], reach_key="finish")
    if d.get("blk"):
        roads = sorted(set(BK.corridor_roads(c)))
        c["p"] = dict(c["p"], retrofit=[dict(kind="blocks", road=r, len=float(d["blk"])) for r in roads])
    return c


def s01_keys():
    import windport_design as X
    items = X.cd_items()
    out = []
    for i, x in enumerate(items):
        if x["lay"] == "tandem" and x["S"] <= 1:
            out.append(f"cd={i}|n_v=10|reach=grid" + ("|blk=150" if x["scen"] == "lane" else ""))
    return out


# ---------------------------------------------------------------- configurations of the near-yard parts
def plan_cfg(c, site, plan, scen_p, level, which):
    """Configuration of the near-yard window (which = "pick") or the transfer ("set") plus the layout: geo marker buf, extra
    crabbing time per pick-up / set-down (farthest slot), turn alternatives."""
    import copy
    import windport_revision_buffer as B
    from windport import sim as WS
    c = copy.deepcopy(c)
    c["geo"] = dict(c["geo"], buf=site)
    p0 = dict(WS.BASE, **scen_p)
    ex = B.crab_extra(plan, p0["v_loaded"], p0["v_empty"], LEVELS[level][1])
    key = "hp_s" if which == "pick" else "hd_s"
    c["p"] = dict(c["p"], **{key: p0[key] + ex})
    if which == "pick":
        c["revision_origins"] = list(plan["order"])
    return c, ex


def turn_alt():
    fs = sorted(ROOT.glob("results/windport_revision_bturn_*/turn_alt.json")) or [ROOT / "results/runs/revision_bturn/turn_alt.json"]
    assert len(fs) == 1, fs
    return json.loads(fs[0].read_text(encoding="utf-8")), fs[0]


_ALT = {}


def with_alt(c, site, var, scen, level):
    if level == "feas":
        return c
    if not _ALT:
        _ALT.update(turn_alt()[0])
    vn = "slow" if scen == "slow" else "base"
    ex = {k: x["t"][f"{vn}|hi"] for k, x in _ALT[f"{site}|{var}"].items()}
    if ex:
        c["p"] = dict(c["p"], turn_extra=ex)
    return c


def bnear_keys():
    import windport_spatial as A
    g = A.GRIDS["siteport"]
    return [T.enc(dict(site=s, scen=sc, mode=m, K=K, lv=lv, G=G)) for G, lv, s, m, sc, K in
            itertools.product([24, 0], list(LEVELS), ["okpo", "yantai"], T.MODES, g["scen"], g["K"])]


def bnear_cfg(d, plans):
    import windport_spatial as A
    s = d["site"]
    c = A.cfg_of("siteport", dict(what="port", kind="map:" + s, st="runs", scen=d["scen"], mode=d["mode"], arr="S1", K=d["K"], n_v=10))
    if int(d["G"]) != A.GRIDS["siteport"]["G"]:
        G, oh = float(d["G"]), A.GRIDS["siteport"]["open_h"]
        c.update(horizon_h=G + oh, cal=dict(crane=[[G, G + oh]]))
    c, ex = plan_cfg(c, s, plans[s], dict(T.SCEN[d["scen"]].get("p", {})), d["lv"], "pick")
    return with_alt(c, s, "near", d["scen"], d["lv"])


def btr_keys():
    out = []
    for s, sc, K, lv in itertools.product(["okpo", "yantai"], ["base", "slow"], range(1, 9), list(LEVELS)):
        out.append(T.enc(dict(site=s, scen=sc, K=K, lv=lv, ban=0)))
        if s in BAN:
            out.append(T.enc(dict(site=s, scen=sc, K=K, lv=lv, ban=1)))
    return out


def btr_cfg(d, plans):
    import windport_design_lib as L
    s = d["site"]
    sp = dict(T.SCEN[d["scen"]].get("p", {}))
    c = L.transfer_cfg(s, int(d["K"]), 10, sp)
    nc = len(plans[s]["columns"])
    c["geo"] = dict(c["geo"], n_cradles=nc)
    c["S"] = nc
    if d.get("ban") == "1":
        c["geo"] = dict(c["geo"], ban=BAN[s])
    c, ex = plan_cfg(c, s, plans[s], sp, d["lv"], "set")
    return with_alt(c, s, "transfer_ban" if d.get("ban") == "1" else "transfer", d["scen"], d["lv"])


def bmulti_keys():
    return [T.enc(dict(site="okpo", scen="base", mode=m, K=K, hold=h, lv=lv)) for m, K, h, lv in itertools.product(T.MODES, range(1, 9), ["0", "1"], ["lo", "hi"])]


def bmulti_cfg(d):
    """Okpo three-voyage single-level direct loading: same keys as windport_design yards (alternatives lo / hi), loaded turn at
    node_trace_016 banned; alternatives along the routes after the ban (bturn okpo|multi_ban)."""
    import copy
    import windport_spatial as A
    c = A.cfg_of("siteport", dict(what="port", kind="map:okpo", st="multi", scen="base", mode=d["mode"], arr="S1", K=d["K"], n_v=10, hold=d["hold"]))
    c = copy.deepcopy(c)
    c["geo"] = dict(c["geo"], ban=BAN["okpo"])
    if not _ALT:
        _ALT.update(turn_alt()[0])
    ex = {k: x["t"][f"base|{d['lv']}"] for k, x in _ALT["okpo|multi_ban"].items()}
    if ex:
        c["p"] = dict(c["p"], turn_extra=ex)
    return c


# ================================================================ single point
def point(part, key, plans=None):
    import windport_rerun_conservative as RR
    import windport_design as X
    d = T.dec(key) if "=" in key else None
    if part == "t8:port":
        r = RR.compute("extra:port", key)
        if d["rep"] == "fcfs":
            import windport_extra as X6
            from windport import bound_all as BA
            c = X6.port_cfg(d["scen"], d["mode"], d["arr"], int(d["K"]), int(d["n_v"]), X6.hold_v(d["hold"]), "fcfs")
            lo, hi = BA.lstar(BA.w2_lift(c, BA.parts(c, lift=True)), int(d["n_v"]))
            r.update(lstar_w2=lo / H, lstar_w2_hi=hi / H)
        return r
    if part == "t8:e3":
        return RR.compute("e1e3:e3", key)
    if part == "t8:fix":
        return RR.compute("extra:fix", key)
    if part == "rate:e4":
        return RR.compute("runs:e4", key)
    if part == "rate:mix6":
        return RR.compute("extra:mix6", key)
    if part == "rate:reach":
        import windport_rerun_spatial as E
        return E.run_point("reach", key)
    if part == "cd":
        return dict(X.port_point(cd_cfg(d), all_j=True), **d)
    if part == "s01":
        return dict(X.port_point(cd_cfg(d), all_j=True), **d)
    if part == "bnear":
        return dict(X.port_point(bnear_cfg(d, plans)), **d)
    if part == "btr":
        return dict(X.port_point(btr_cfg(d, plans)), **d)
    if part == "bmulti":
        return dict(X.port_point(bmulti_cfg(d)), **d)
    raise KeyError(part)


def rows_of(part, key, r):
    import windport_rerun_conservative as RR
    import windport_design as X
    if part == "t8:port":
        out = RR.rows("extra:port", key, r)
        for o in out:
            o.update(lstar_w2=r.get("lstar_w2", ""), lstar_w2_hi=r.get("lstar_w2_hi", ""))
        return out
    if part in ("t8:e3", "t8:fix", "rate:e4", "rate:mix6"):
        return RR.rows({"t8:e3": "e1e3:e3", "t8:fix": "extra:fix", "rate:e4": "runs:e4", "rate:mix6": "extra:mix6"}[part], key, r)
    if part == "rate:reach":
        import windport_rerun_spatial as E
        return [E.row_of(key, r)]
    return [X.sim_row("transfer" if part == "btr" else "codesign", key, r)]


# ================================================================ worker processes
_OUTS, _PLANS = {}, {}


def init(group, outs, plans):
    pin(list(range(1, os.cpu_count())))
    import windport_design as X
    import windport_revision_lib as K
    import windport_netcache as NC
    X.setup_env()
    K.install_all(plans)
    if group in ("a", "b"):
        K.install_spacing(SPACING)
    if group == "a":
        import windport_extra as X6
        import windport_rerun_conservative as RR
        from windport import check as C
        from windport import check_lift as CL
        C.check = CL.check
        X6.kassels_order = RR.kassels_lift
    if group == "b":
        import windport_codesign_blocks as BK
        BK.RX.install(True)
        BK.install_ll()
    NC.install()
    _OUTS.update({k: Path(v) for k, v in outs.items()})
    _PLANS.update(plans or {})


def chunk(arg):
    part, ks = arg
    for k in ks:
        f = _OUTS[part] / "points" / fname(part, k)
        if not f.exists():
            r = point(part, k, _PLANS)
            write_json(f, r if part.startswith(("t8", "rate")) else dict(r, key=k))
    return part, ks


# ================================================================ turns after the layout
def bturn_cfgs(plans):
    """(site, variant, cfg, zones not counted as "other occupation"): near = near-yard columns → quay; transfer = far yard →
    near-yard columns; transfer_ban / multi_ban = node_trace_016 banned."""
    import windport_spatial as A
    import windport_design_lib as L
    from windport import shipyard as SY
    from windport import sim4 as S4
    out = []
    for s in ("okpo", "yantai"):
        zs = [z["zone"] for z in plans[s]["zones"]]
        for m in T.MODES:
            c = A.cfg_of("siteport", dict(what="port", kind="map:" + s, st="runs", scen="base", mode=m, arr="S1", K=1, n_v=10))
            c["geo"] = dict(c["geo"], buf=s)
            out.append((s, "near", c, zs))
        c = L.transfer_cfg(s, 1, 10, {})
        nc = len(plans[s]["columns"])
        c["geo"] = dict(c["geo"], n_cradles=nc, buf=s)
        c["S"] = nc
        out.append((s, "transfer", c, [S4.SITES_MULTI[s]["storage_zone"]] + zs))
        if s in BAN:
            out.append((s, "transfer_ban", dict(c, geo=dict(c["geo"], ban=BAN[s])), [S4.SITES_MULTI[s]["storage_zone"]] + zs))
            for m in T.MODES:
                cm = A.cfg_of("siteport", dict(what="port", kind="map:" + s, st="multi", scen="base", mode=m, arr="S1", K=1, n_v=10))
                cm["geo"] = dict(cm["geo"], ban=BAN[s])
                out.append((s, "multi_ban", cm, [S4.SITES_MULTI[s]["storage_zone"]]))
    return out


def bturn_items(plans):
    import windport_turn_alt as TI
    from windport import shipyard as SY
    from windport import sim4 as S4
    seen = {}
    for s, var, c, zs in bturn_cfgs(plans):
        D, net, p, *_ = S4.setup4(c)
        for k, x in TI.route_turns(D, net, p).items():
            x0 = seen.setdefault((s, var, k), dict(x, routes=0, zones=zs))
            x0["routes"] += x["routes"]
    items = []
    for (s, var, k), x in sorted(seen.items()):
        obs = TI.layers_of(s, x["zones"])
        b, h = TI.sector_bad(obs, x, T.S.BASE["Lv"], T.S.BASE["B"])
        x.update(sector_building=h["building"], sector_water=h["water"], sector_other=h["other"], bad=int(b))
        items.append((s, var, k, x))
    return items


def bturn_one(arg):
    import windport_turn_alt_clear  # noqa: F401  (importing it installs the 1 m clearance Grid / analyse)
    import windport_design as X
    s, var, k, x = arg
    return X.turn_one((s, var, k, x))


def init_turn(plans):
    pin(list(range(1, os.cpu_count())))
    import windport_design as X
    import windport_revision_lib as K
    X.setup_env()
    K.install_all(plans)


def run_bturn(a, plans, pf):
    import windport_design as X
    import windport_turn_alt as TI
    import windport_turn_alt_clear as T1
    out, cfg = out_dir("bturn", dict(plans_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(), ban=BAN, clear_m=T1.CLEAR_M, tsw=TI.TSW))
    (out / "points").mkdir(parents=True, exist_ok=True)
    X.prepare(out, cfg)
    items = bturn_items(plans)
    prog = Progress(out / "progress.json", len(items), 0, a.procs, "revision turns after the layout", "revision")
    res = []
    for r in slot_imap(bturn_one, items, a.procs, initializer=init_turn, initargs=(plans,), slots_dir=a.slots, tag="revision"):
        res.append(r)
        prog.write(done=len(res))
    res.sort(key=lambda r: (r[0], r[1], r[2]))
    rows, alt = [], {}
    Lv, B = T.S.BASE["Lv"], T.S.BASE["B"]
    for s, var, k, x, r in res:
        row = dict(site=s, var=var, turn=k, node=x["node"], turn_deg=round(math.degrees(abs(x["th"])), 1), routes=x["routes"], w_in=x["w_in"], w_out=x["w_out"],
                   sector_building=x["sector_building"], sector_water=x["sector_water"], sector_other=x["sector_other"], bad=x["bad"])
        if r is not None:
            cls = TI.classify(r)
            t = {}
            for vn, v in X.SPEEDS.items():
                for lv, j, fams in (("lo", 0, None), ("hi", 1, ("C+", "C-"))):
                    b = TI.best_alt(r, vn, j, fams)
                    if cls.startswith("in place"):
                        t[f"{vn}|{lv}"], fam = 0.0, "in place"
                    elif b is None:
                        t[f"{vn}|{lv}"], fam = round(TI.generic_s(Lv, B, v, TI.TSW[j], x["w_in"], x["w_out"]), 1), "generic formula"
                    else:
                        t[f"{vn}|{lv}"], fam = b[1]["t"], b[0]
                    row[f"fam_{vn}_{lv}"], row[f"t_{vn}_{lv}"] = fam, t[f"{vn}|{lv}"]
            row.update(cls=cls, fams_feasible="+".join(sorted({f.split("|")[0] for f in r["fams"]})))
            alt.setdefault(f"{s}|{var}", {})[k] = dict(cls=cls, t=t)
        rows.append(row)
    for s, var, *_ in bturn_cfgs(plans):
        alt.setdefault(f"{s}|{var}", {})
    wcsv(out / "turn_alt.csv", rows)
    (out / "turn_alt.json").write_text(json.dumps(alt, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    note = f"{len(rows)} turns, sector failures {sum(r['bad'] for r in rows)}"
    prog.write(state="done", note=note)
    print(out.name, note)


# ================================================================ batches
def part_extra(part, plans, pf):
    ex = dict(spacing=SPACING if part in GROUPS["a"] + GROUPS["b"] else None)
    if part == "cd":
        ex["grid"] = CDB
    if part in ("bnear", "btr", "bmulti"):
        _, tf = turn_alt()
        ex.update(plans_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(), turn_alt_sha256=hashlib.sha256(tf.read_bytes()).hexdigest(), levels=LEVELS, ban=BAN)
    return ex


def run(group, parts, a, plans, pf):
    import windport_design as X
    outs, progs, chunks, ks = {}, {}, [], {}
    for part in parts:
        out, cfg = out_dir(part, part_extra(part, plans, pf))
        X.prepare(out, cfg)
        outs[part] = out
        ks[part] = keys(part)
        todo = [k for k in ks[part] if not (out / "points" / fname(part, k)).exists()]
        progs[part] = Progress(out / "progress.json", len(ks[part]), len(ks[part]) - len(todo), a.procs, f"revision {part}", "revision")
        n = 1 if part in ("t8:e3", "t8:fix", "bnear", "btr", "bmulti") else a.chunk
        chunks += [(part, todo[i:i + n]) for i in range(0, len(todo), n)]
    slow = ("t8:e3", "t8:fix", "btr", "bmulti", "bnear")
    chunks.sort(key=lambda x: x[0] not in slow)
    try:
        for part, ds in slot_imap(chunk, chunks, a.procs, initializer=init, initargs=(group, {k: str(v) for k, v in outs.items()}, plans),
                                  slots_dir=a.slots, tag="revision"):
            progs[part].write(done=progs[part].d["done"] + len(ds))
    except BaseException as e:
        for pg in progs.values():
            pg.write(state="failed", note=repr(e)[:300])
        raise
    for part, out in outs.items():
        rs = [json.loads((out / "points" / fname(part, k)).read_text(encoding="utf-8")) for k in ks[part]]
        rows = [x for k, r in zip(ks[part], rs) for x in rows_of(part, k, r)]
        wcsv(out / "points.csv", rows)
        bad = sum(1 for x in rows if str(x.get("check_ok")) in ("0", "False"))
        note = f"{len(rows)} rows; checker failures {bad}"
        if part in ("cd", "s01", "bnear", "btr", "bmulti"):
            lb = sum(1 for r in rs if r["port_h"] is not None and r["port_h"] < r["lstar_lo"] - 1e-9)
            vi = sum(int(r.get("viol") or 0) for r in rs)
            note += f"; port time < L″_lift* {lb}; W″_lift(T_j) < j {vi} piles"
        progs[part].write(state="done", note=note)
        print(out.name, note)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, choices=list(GROUPS))
    ap.add_argument("--part", default=None, help="parts within the group (comma-separated); default: whole group (group c runs bturn first)")
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_design as X
    import windport_revision_lib as K
    X.setup_env()
    plans, pf = load_plans()
    K.install_all(plans)
    parts = a.part.split(",") if a.part else GROUPS[a.group]
    assert set(parts) <= set(GROUPS[a.group]), parts
    if "bturn" in parts:
        run_bturn(a, plans, pf)
        parts = [p for p in parts if p != "bturn"]
    if parts:
        if a.group in ("a", "b"):
            K.install_spacing(SPACING)
        run(a.group, parts, a, plans, pf)


if __name__ == "__main__":
    main()
