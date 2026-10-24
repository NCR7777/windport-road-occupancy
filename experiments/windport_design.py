"""Simulation and geometry batches of the design analyses (main2 geometry; conservative lifting semantics windport/lift.py,
t_u = 0.05 p; unified bound W″_lift).
Uses only the two shipyard maps (Okpo, Yantai); outputs only identifiers and numbers, no maps. The new semantics are in
experiments/windport_design_lib.py (transfer network) and windport_turn_alt.py (alternative turns).

--part (comma-separated; the sim parts share one process pool):
  turn      Okpo, Yantai × single-tier (runs) / three-tier (multi) / far → near transfer (transfer) loaded routes: turns where the
            sector of an in-place rotation centred on the junction hits buildings or water (spatial-additions criterion). For each,
            search alternative manoeuvres (early steering, reversing, crabbing; windport_turn_alt) and give class and duration
            (two speeds × two ends: lo = shortest over all feasible families, steering-mode switch 30 s; hi = reverse-crab
            (lateral family) only, switch 300 s; if none is feasible, the generic formula). Writes turn_alt.csv (per turn),
            turn_alt.json (for the simulation: {site|st: {turn key: dict(cls, t={speed|lo/hi: seconds})}}), turn_check.csv
            (comparison with the turn list in turn_extra.json of the spatial additions).
  e6:lo, e6:hi   Table tab_yards (single-tier E6 grid; keys, configuration, single point and row format of the E4-E7 batches,
            as in the runs:e6 rerun of the conservative lifting rule) with alternative manoeuvres as the main rule: turns that
            fail the sector check get the alternative-manoeuvre duration (lo / hi ends). Also records W″_lift (unified entry)
            for the recheck.
  yards     Table tab_yards3 (three-tier storage, port time of one vessel with 10 piles; keys of the main-geometry yards part)
            with alternative manoeuvres as the main rule (alt = lo / hi).
  near      Near yard (single-tier storage) loading-window port time (single-tier keys of siteport in the spatial additions)
            × turning (feas = all feasible / lo / hi) × pre-window preparation G = 24 h (compared with single-stage storage)
            and G = 0 (from an empty system, for the voyage-cycle accounting).
  transfer  Far yard → near yard transfer of 30 piles (K = 1–8 × base / 1 km/h × turning feas / lo / hi), from an empty
            system; records the placement time of each pile and W″_lift.
  codesign  Joint design enumeration space (experiments/windport_spatial_analytic.cd_configs, 2,176 configurations) × n_v = 3, 5,
            10, all simulated; side-by-side cradles as rebuilt in the main2 geometry (main2.rows_cfg), plus one group each with
            distance-based ship-crane reach S_r = 1 (main rule) and 2 (for S > S_r each far pile gets t_sh = 1 h); "all
            reachable" is the optimistic upper limit.
Output results/windport_design_<part>_<config hash>/: config.json (SHA-256 of code and inputs, geometry), progress.json,
points/ (per point, resumable), points.csv, etc.
Run: python experiments/windport_design.py --part turn --procs 6 --slots DIR
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
GEO = "main2"
CODE = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "windport").glob("*.py") if p.name not in ("port_survey.py", "geomcheck.py")) + \
    ["occupancy/sim.py", "occupancy/network.py", "occupancy/params.py", "occupancy/tasks.py", "exact/check.py", "exact/model.py",
     "experiments/windport_runs.py", "experiments/windport_spatial.py", "experiments/windport_spatial_analytic.py", "experiments/windport_turn_sweep.py",
     "experiments/windport_design.py", "experiments/windport_design_lib.py", "experiments/windport_turn_alt.py"]
SIMS = ["e6:lo", "e6:hi", "yards", "near", "transfer", "codesign"]
LEVELS = ["feas", "lo", "hi"]
TRANSFER = dict(sites=["okpo", "yantai"], scen=["base", "slow"], K=list(range(1, 9)), n=30, level=LEVELS)
NEAR = dict(G=[24, 0], level=LEVELS)
YARDS = dict(sites=["okpo", "yantai"], hold=["0", "1", "inf"], level=["lo", "hi"])
CD = dict(n_v=[3, 5, 10], shift_s=3600.0, side_reach=["all", "1", "2"])
SPEEDS = dict(base=2.5 / 3.6, slow=1.0 / 3.6)


def code_hash():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}


def maps():
    from windport import shipyard as SY
    return {s: SY.NETWORK[s] for s in ("okpo", "yantai")}


def out_dir(name, extra=None):
    from windport import archetypes as A
    cfg = dict(task="design", part=name, geometry=A.GEOMETRIES[GEO], code=code_hash(), maps=maps(), **(extra or {}))
    return ROOT / "results" / f"windport_design_{name.replace(':', '_')}_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}", cfg


def prepare(out, cfg):
    (out / "points").mkdir(parents=True, exist_ok=True)
    cf = out / "config.json"
    if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != json.loads(json.dumps(cfg)):
        raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
    cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def wcsv(path, rows, cols=None):
    if cols is None:
        cols = []
        for r in rows:
            cols += [k for k in r if k not in cols]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def setup_env():
    """Shared by worker and main processes: main2 geometry, conservative lifting semantics, transfer network."""
    from windport import lift as LF
    from windport import main2
    import windport_design_lib as L
    main2.use()
    LF.install()
    L.install()


# ================================================================ turn
def turn_configs():
    import windport_turn_sweep as TA
    import windport_design_lib as L
    out = []
    for site in ("okpo", "yantai"):
        for st in ("runs", "multi"):
            out += [(site, st, m, TA.turn_cfg(site, st, m)) for m in T.MODES]
        out.append((site, "transfer", "pull_in", L.transfer_cfg(site, 1, 10, {})))
    return out


def turn_items():
    """[(site, st, turn key, turn dict)]: turns whose sector hits buildings or water (union over cradle modes)."""
    import windport_turn_sweep as TA
    import windport_turn_alt as TI
    from windport import shipyard as SY
    from windport import sim4 as S4
    seen, bad = {}, []
    for site, st, m, c in turn_configs():
        D, net, p, *_ = S4.setup4(c)
        for k, x in TI.route_turns(D, net, p).items():
            x0 = seen.setdefault((site, st, k), dict(x, modes=[], routes=0))
            x0["modes"].append(m)
            x0["routes"] += x["routes"]
    for (site, st, k), x in sorted(seen.items()):
        zs = [S4.SITES_MULTI[site]["storage_zone"], SY.SITES[site]["storage_zone"]] if st == "transfer" else \
            [(S4.SITES_MULTI[site] if st == "multi" else SY.SITES[site])["storage_zone"]]
        obs = TI.layers_of(site, zs)
        b, h = TI.sector_bad(obs, x, T.S.BASE["Lv"], T.S.BASE["B"])
        x.update(sector_building=h["building"], sector_water=h["water"], sector_other=h["other"], bad=int(b), zones=zs)
        bad.append((site, st, k, x))
    return bad


def turn_one(arg):
    import windport_turn_alt as TI
    site, st, k, x = arg
    if not x["bad"]:
        return site, st, k, x, None
    obs = TI.layers_of(site, x["zones"])
    G = TI.Grid(x["xy"], obs, TI.road_polys(site))
    return site, st, k, x, TI.analyse(G, x["xy"], x["hin"], x["th"], T.S.BASE["Lv"], T.S.BASE["B"], SPEEDS)


def init_turn():
    pin(list(range(1, os.cpu_count())))
    setup_env()


def run_turn(a):
    import windport_turn_alt as TI
    out, cfg = out_dir("turn", dict(grid=TI.GRID, res=TI.RES, half=TI.HALF, tsw=TI.TSW, speeds=SPEEDS, step=[TI.STEP_TIP, TI.NT]))
    prepare(out, cfg)
    items = turn_items()
    prog = Progress(out / "progress.json", len(items), 0, a.procs, "design analyses: feasibility and duration of alternative turns", "design")
    res = []
    for r in slot_imap(turn_one, items, a.procs, initializer=init_turn, slots_dir=a.slots, tag="design"):
        res.append(r)
        prog.write(done=len(res))
    res.sort(key=lambda r: (r[0], r[1], r[2]))
    rows, alt = [], {}
    Lv, B = T.S.BASE["Lv"], T.S.BASE["B"]
    for site, st, k, x, r in res:
        row = dict(site=site, storage=st, turn=k, node=x["node"], turn_deg=round(math.degrees(abs(x["th"])), 1), routes=x["routes"], modes="+".join(x["modes"]),
                   w_in=x["w_in"], w_out=x["w_out"], sector_building=x["sector_building"], sector_water=x["sector_water"], sector_other=x["sector_other"],
                   bad=x["bad"])
        if r is not None:
            cls = TI.classify(r)
            row.update(cls=cls, base_block=r["base_block"], n_cand=r["n_cand"], n_feas=r["n_feas"], n_clean=r["n_clean"])
            t = {}
            for vn, v in SPEEDS.items():
                # lo: shortest over all feasible families (incl. early steering), steering-mode switch at the low end of TSW;
                # hi: reverse-crab only (lateral family C±), high end of TSW;
                # if none is feasible, use the generic formula (t_sw of the same end) and write the generic label in the fam column
                for lv, j, fams in (("lo", 0, None), ("hi", 1, ("C+", "C-"))):
                    tsw = TI.TSW[j]
                    b = TI.best_alt(r, vn, j, fams)
                    if cls.startswith("in place"):
                        t[f"{vn}|{lv}"], fam = 0.0, "in place"
                    elif b is None:
                        t[f"{vn}|{lv}"], fam = round(TI.generic_s(Lv, B, v, tsw, x["w_in"], x["w_out"]), 1), "generic formula"
                    else:
                        t[f"{vn}|{lv}"], fam = b[1]["t"], b[0]
                        row.update({f"{lv}_{vn}_{a}": b[1][a] for a in ("s", "lam", "u", "f", "crab_m", "straight_m", "rmax_m", "clean", "other")})
                    row[f"fam_{vn}_{lv}"], row[f"t_{vn}_{lv}"] = fam, t[f"{vn}|{lv}"]
                    row[f"generic_{vn}_{lv}"] = round(TI.generic_s(Lv, B, v, tsw, x["w_in"], x["w_out"]), 1)
            row["fams_feasible"] = "+".join(sorted({f.split("|")[0] for f in r["fams"]}))
            row["fams_clean"] = "+".join(sorted({f.split("|")[0] for f, y in r["fams"].items() if y["clean"]}))
            alt.setdefault(f"{site}|{st}", {})[k] = dict(cls=cls, t=t)
        rows.append(row)
    for site in ("okpo", "yantai"):
        for st in ("runs", "multi", "transfer"):
            alt.setdefault(f"{site}|{st}", {})
    wcsv(out / "turn_alt.csv", rows)
    (out / "turn_alt.json").write_text(json.dumps(alt, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    # compare with the turn list of the spatial additions
    import windport_spatial as A
    old = json.loads(A.turn_file().read_text(encoding="utf-8"))
    chk = []
    for key, lst in sorted(old.items()):
        new = sorted(alt.get(key, {}))
        chk.append(dict(key=key, spatial=len(lst), design=len(new), same=int(sorted(lst) == new), only_spatial=";".join(sorted(set(lst) - set(new))),
                        only_design=";".join(sorted(set(new) - set(lst)))))
    wcsv(out / "turn_check.csv", chk)
    note = f"{len(rows)} turns, {sum(r['bad'] for r in rows)} fail the sector check; {sum(c['same'] for c in chk)} / {len(chk)} match the spatial-additions list"
    prog.write(state="done", note=note)
    print(out.name, note)


# ================================================================ sims
def port_point(c, all_j=True):
    """One port-time point: conservative-semantics simulation (sim4.simulate4), joint checker (check_all), L*(n) of W″_lift
    and the per-pile check W″_lift(T_j) ≥ j."""
    from windport import bound_all as BA
    from windport import check_all as CA
    from windport import sim as S
    from windport import sim2 as S2
    from windport import sim4 as S4
    net, p, sim, r = S4.simulate4(dict(c, w4=False))
    D, _, _, _, starts, quay, cal = S4.setup4(c)
    g, y = S2.idle_nodes(D)
    ck = CA.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
    G = c["cal"]["crane"][0][0] * H
    n = c["n_load"]
    ls = sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)
    ph = (ls[n - 1] - G) / H if len(ls) >= n else None
    f = BA.w2_lift(c, BA.parts(c, lift=True))
    lo, hi = BA.lstar(f, n)
    viol = sum(1 for j in range(1, len(ls) + 1) if f(ls[j - 1] - G + 1e-6) < j) if all_j else None
    return dict(port_h=None if ph is None else round(ph, 6), lifts=len(ls), lstar_lo=round(lo / H, 6), lstar_hi=round(hi / H, 6),
                w_at_port=None if ph is None else f(ph * H + 0.5e-6 * H), viol=viol, T_j=[round((t - G) / H, 6) for t in ls[:n]],
                check_ok=int(ck["ok"]), check_err=ck["errors"][:2], n_clear=ck["n_clear"], n_under=ck["n_under"], trips=len(sim.trips),
                map_sha256=net.map_sha256)


def yard_keys():
    import windport_spatial as A
    g, out = A.GRIDS["siteport"], []
    for site, m, lv, h in itertools.product(YARDS["sites"], T.MODES, YARDS["level"], YARDS["hold"]):
        for arr, K in itertools.product(g["arr"][site], g["K"]):
            out.append(T.enc(dict(what="port", kind="map:" + site, st="multi", scen="base", mode=m, arr=arr, K=K, n_v=g["n_v"], hold=h, alt=lv)))
    return out


def near_keys():
    import windport_spatial as A
    g, out = A.GRIDS["siteport"], []
    for G, lv, site, m, sc in itertools.product(NEAR["G"], NEAR["level"], g["sites"], T.MODES, g["scen"]):
        for arr, K in itertools.product(g["arr"][site], g["K"]):
            out.append(T.enc(dict(what="port", kind="map:" + site, st="runs", scen=sc, mode=m, arr=arr, K=K, n_v=g["n_v"], alt=lv, G=G)))
    return out


def transfer_keys():
    g = TRANSFER
    return [T.enc(dict(site=s, scen=sc, K=K, n=g["n"], alt=lv)) for s, sc, K, lv in itertools.product(g["sites"], g["scen"], g["K"], g["level"])]


def cd_items():
    import windport_spatial_analytic as AA
    return [x for sc in AA.GRIDS["codesign"]["scen"] for x in AA.cd_configs(sc)]


def cd_keys():
    out = []
    for i, x in enumerate(cd_items()):
        reach = ["grid"] if x["lay"] != "side" else [r for r in CD["side_reach"] if r == "all" or x["S"] > int(r)]
        for n, r in itertools.product(CD["n_v"], reach):
            out.append(T.enc(dict(cd=i, n_v=n, reach=r)))
    return out


def sim_keys(part):
    if part.startswith("e6:"):
        return T.keys("e6")
    return dict(yards=yard_keys, near=near_keys, transfer=transfer_keys, codesign=cd_keys)[part]()


def site_cfg(d):
    """Points of yards / near: siteport configuration of the spatial additions (pre-window preparation G can be changed);
    turns get alternative manoeuvres according to alt."""
    import windport_spatial as A
    import windport_design_lib as L
    c = A.cfg_of("siteport", {k: v for k, v in d.items() if k not in ("alt", "G")})
    if "G" in d and float(d["G"]) != A.GRIDS["siteport"]["G"]:
        G, oh = float(d["G"]), A.GRIDS["siteport"]["open_h"]
        c.update(horizon_h=G + oh, cal=dict(crane=[[G, G + oh]]))
    return L.with_turns(c, d["kind"][4:], d["st"], d["scen"], d["alt"])


def transfer_cfg(d):
    import windport_design_lib as L
    c = L.transfer_cfg(d["site"], int(d["K"]), int(d["n"]), dict(T.SCEN[d["scen"]].get("p", {})))
    return L.with_turns(c, d["site"], "transfer", d["scen"], d["alt"])


def cd_cfg(d):
    import windport_spatial as A
    from windport import main2
    x = cd_items()[int(d["cd"])]
    c = A.port_cfg(x["geo"], x["p"], x["S"], x["lift"], x["K"], int(d["n_v"]), A.GRIDS["cdv"]["G"], A.GRIDS["cdv"]["open_h"], x["hold"])
    if x["lay"] == "side":
        c = main2.rows_cfg(c)
        if d["reach"] != "all":
            c["p"] = dict(c["p"], reach=int(d["reach"]), shift_s=CD["shift_s"])
    return c


def e6_point(level, key):
    """One E6 point of the E4-E7 batches (written as in the conservative-lifting-rule rerun); turns of the single-tier storage
    that fail the sector check get alternative manoeuvres; also records W″_lift(L)."""
    import windport_design_lib as L
    from windport import bound_all as BA
    d = T.dec(key)
    c = L.with_turns(T.cfg_of("e6", key), d["kind"][4:], "runs", d["scen"], level)
    old = T.cfg_of
    T.cfg_of = lambda part, k: c if k == key else old(part, k)
    try:
        r = T.run_one("e6", key)
    finally:
        T.cfg_of = old
    w = BA.parts(c, lift=True)
    L_ = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * H
    v, keys_, cls, sub, nat = BA.binding(BA.terms(w, L_))
    r.update(w2_lift=v, w2_binding="+".join(keys_), w2_cls=cls, w2_nature=nat)
    return r


def sim_point(part, key):
    d = T.dec(key)
    if part.startswith("e6:"):
        return e6_point(part[3:], key)
    if part in ("yards", "near"):
        return dict(port_point(site_cfg(d)), **d)
    if part == "transfer":
        return dict(port_point(transfer_cfg(d)), **d)
    if part == "codesign":
        return dict(port_point(cd_cfg(d), all_j=False), **d)
    raise KeyError(part)


_OUTS = {}


def init_sims(outs):
    pin(list(range(1, os.cpu_count())))
    setup_env()
    from windport import check as C
    from windport import check_all as CA
    from windport import sim2 as S2
    from windport import sim4 as S4
    C.check = CA.check                      # the E6 single point (windport_runs.run_one) looks up windport.check.check by name: swap in the joint checker (knows alternative manoeuvres)
    S2.get_net = S4.get_net4                # windport.sim2.setup2 builds the network with TurnNet (identical to PortNet value by value when there are no alternative manoeuvres)
    _OUTS.update({k: Path(v) for k, v in outs.items()})


def chunk_sims(arg):
    part, ks = arg
    for k in ks:
        f = _OUTS[part] / "points" / T.fname(k)
        if not f.exists():
            write_json(f, dict(sim_point(part, k), key=k))
    return part, ks


def sim_row(part, key, r):
    if part.startswith("e6:"):
        return T.row_of("e6", key, r)
    out = {k: v for k, v in r.items() if k not in ("check_err", "map_sha256", "T_j")}
    if part == "transfer":
        out["T_j"] = " ".join(f"{t:.4f}" for t in r["T_j"])
    return out


def turn_input():
    import windport_design_lib as L
    f = L.turn_file()
    return dict(turn_alt=str(f.relative_to(ROOT)).replace("\\", "/"), turn_alt_sha256=hashlib.sha256(f.read_bytes()).hexdigest())


def run_sims(parts, a):
    outs, progs, chunks, ks = {}, {}, [], {}
    for part in parts:
        extra = dict(turn_input(), semantics="lift_tu0.05_head")
        extra["grid"] = dict(yards=YARDS, near=NEAR, transfer=TRANSFER, codesign=CD).get(part, part)
        outs[part] = out_dir(part, extra)
    for part, (out, cfg) in outs.items():
        prepare(out, cfg)
        ks[part] = sim_keys(part)
        todo = [k for k in ks[part] if not (out / "points" / T.fname(k)).exists()]
        progs[part] = Progress(out / "progress.json", len(ks[part]), len(ks[part]) - len(todo), a.procs, f"design {part}", "design")
        n = 1 if part in ("yards", "transfer") else a.chunk
        chunks += [(part, todo[i:i + n]) for i in range(0, len(todo), n)]
    slow = ("yards", "transfer", "near")
    chunks.sort(key=lambda x: x[0] not in slow)                    # shipyard-map points are slow: dispatch them first
    try:
        for part, ds in slot_imap(chunk_sims, chunks, a.procs, initializer=init_sims, initargs=({k: str(v[0]) for k, v in outs.items()},),
                                  slots_dir=a.slots, tag="design"):
            progs[part].write(done=progs[part].d["done"] + len(ds))
    except BaseException as e:
        for pg in progs.values():
            pg.write(state="failed", note=repr(e)[:300])
        raise
    for part, (out, _) in outs.items():
        rs = [json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8")) for k in ks[part]]
        rows = [sim_row(part, k, r) for k, r in zip(ks[part], rs)]
        if part.startswith("e6:"):
            wcsv(out / "points.csv", rows, T.COLS)
            wcsv(out / "recheck.csv", [dict(key=k, sim=r["sim"], w2_lift=r["w2_lift"], w2_binding=r["w2_binding"], w2_cls=r["w2_cls"], w2_nature=r["w2_nature"],
                                            over=int(r["sim"] > r["w2_lift"])) for k, r in zip(ks[part], rs)])
            bad = sum(1 for r in rs if not r["check_ok"])
            over = sum(1 for r in rs if r["sim"] > r["w2_lift"])
            note = f"{len(rows)} points; checker failures {bad}; above W″_lift {over}"
        else:
            wcsv(out / "points.csv", rows)
            bad = sum(1 for r in rs if not r["check_ok"])
            lb = sum(1 for r in rs if r["port_h"] is not None and r["port_h"] < r["lstar_lo"] - 1e-9)
            vi = sum(int(r["viol"] or 0) for r in rs)
            note = f"{len(rows)} points; checker failures {bad}; port time < L″_lift* {lb}; W″_lift(T_j) < j for {vi} piles in total"
        progs[part].write(state="done", note=note)
        print(out.name, note)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    setup_env()
    parts = a.part.split(",")
    if "turn" in parts:
        run_turn(a)
    sims = [p for p in parts if p in SIMS]
    if sims:
        run_sims(sims, a)


if __name__ == "__main__":
    main()
