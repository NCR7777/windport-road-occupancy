"""Main geometry of the parametric port archetypes (windport/archetypes.py GEOMETRIES["main"]: first cradle 170 m
from the gate, quay line 20 m from the apron road centre line, gate turning area radius 60 m). Reruns the manuscript
simulation batches that depend on the archetype geometry (conservative lifting rule windport/lift.py, t_u = 0.05 p;
unified bound W″_lift = bound_all.w2_lift, cradle mode including strings with dq < 0). Every worker calls
archetypes.use("main"); figures with real maps are not drawn, only data.

--part (comma separated; the sims-type parts of one call share one process pool):
  rerun     the committed batches of the conservative-lifting-rule rerun (keys, configs, single points and row format
            of experiments/windport_rerun_conservative.py; E6 uses the Okpo and Yantai shipyard maps, independent of the
            archetype geometry, not rerun), compared row by row with the run directories of the conservative lifting
            rule (40 m geometry) (diff.csv).
  e2        E2: 540 small instances and 17 hard instances (experiments/windport_e2_conservative.run: simulation + CP-SAT
            60 s / 600 s; at most 4 instances at a time, each taking 1-4 threads from the slots).
  spatial     the archetype batches of the spatial additions: hphd, reach, upsize, ablate
            (experiments/windport_rerun_spatial.run_point).
  core      core instances and the two Q_h columns: long single lane / long corridor 1 km/h × cradle layout (in-line
            roadside, in-line pull-in, side by side) × S0, S1, S1m, S3, S3m × K = 1-8 × Q_h = 0, 1, unlimited × first
            cradle 40 m (old geometry), 150 m, 170 m (main geometry); side by side is also run with the alternative
            turn into the cradle at 600 and 1,800 s.
  span      sensitivity to the span from below the lifted load to the gate (experiments/windport_span.one).
  xscan     fine grid of the release time x (experiments/windport_xscan.one).
  yards     Okpo and Yantai, three voyages, yard of 10 piles per vessel (keys of siteport in the spatial additions);
            the direction whose turn sector hits buildings or water uses the alternative turn at 600 and 1,800 s
            (turn_extra.json of the spatial additions). The shipyard maps are independent of the archetype geometry;
            the group with feasible turns is siteport of the unified bound.
  codesign  integer enumeration of the joint design (grid of experiments/windport_spatial_analytic.cd_configs), ranked
            once by W″_lift (bound_all, main measure) and once by W′ (bound4, comparison); the recheck set is as in
            the spatial additions (top 3 for each (scenario, n_v, day rate), top 3 without infrastructure, top 3 for
            each infrastructure combination), union over both rankings.
  cdv       simulates every configuration of the codesign recheck set (cdv of windport_rerun_spatial.run_point). Run codesign
            first.
  geom      geometry check (windport/geomcheck.py): three archetypes × scenario × cradle mode × first cradle
            40 / 150 / 170 m (150 m uses the quay line and turning area of the main geometry); E7 pile lengths under
            the main geometry.
  example   example table of the extra analyses (experiments/windport_analytic.example, plus W″_lift and the
            binding term) under the main geometry.
  critical  critical single-lane length of the extra analyses (windport_analytic.critical) under the main
            geometry (analytic, single process).
Output results/windport_maingeom_<part>_<config hash>/: config.json (code SHA-256, geometry), progress.json, points/
(per point, resume cache), points.csv etc.
Run: python experiments/windport_maingeom.py --part rerun --procs 12 --slots DIR
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap, write_json      # noqa: E402
import windport_runs as T                                        # noqa: E402

H = 3600.0
GEO = "main"
CODE = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "windport").glob("*.py") if p.name not in ("port_survey.py", "geomcheck.py")) + \
    ["occupancy/sim.py", "occupancy/network.py", "occupancy/params.py", "occupancy/tasks.py", "exact/check.py", "exact/model.py",
     "experiments/windport_sim.py", "experiments/windport_runs.py", "experiments/windport_sens_e7.py", "experiments/windport_extra.py",
     "experiments/windport_sens_e5.py", "experiments/windport_analytic.py", "experiments/windport_e2.py", "experiments/windport_spatial.py",
     "experiments/windport_spatial_analytic.py", "experiments/windport_rerun_conservative.py", "experiments/windport_e2_conservative.py", "experiments/windport_span.py",
     "experiments/windport_xscan.py", "experiments/windport_rerun_spatial.py", "experiments/windport_maingeom.py"]
SIMS = ["spatial", "core", "span", "xscan", "yards", "cdv"]
SPATIAL = ["hphd", "reach", "upsize", "ablate"]
CORE = dict(scen=["lane", "longslow"], lay=["on_road", "pull_in", "side"], arr=["S0", "S1", "S1m", "S3", "S3m"], K=list(range(1, 9)), hold=["0", "1", "inf"],
            first=[40.0, 150.0, 170.0], side_extra=[0.0, 600.0, 1800.0], n_v=10)
YARDS = dict(sites=["okpo", "yantai"], extra=[600.0, 1800.0], hold=["0", "1", "inf"])
XS2 = [0.28, 0.29, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39, 0.45]      # main geometry: threshold may leave the old grid


def code_hash():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}


def out_dir(name, extra=None):
    from windport import archetypes as A
    cfg = dict(task="maingeom", part=name, geometry=A.GEOMETRIES[GEO], code=code_hash(), **(extra or {}))
    return ROOT / "results" / f"windport_maingeom_{name.replace(':', '_')}_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}", cfg


def prepare(out, cfg):
    (out / "points").mkdir(parents=True, exist_ok=True)
    cf = out / "config.json"
    if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != json.loads(json.dumps(cfg)):
        raise SystemExit(f"{cf} does not match the current config; refusing to reuse it")
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


def conservative_dir(batch):
    """Run directory of the conservative lifting rule (40 m geometry, conservative rule): the unique one with the prefix
    (its config hash includes archetypes.py, so a directory name computed now would not match after the change)."""
    pre = "windport_conservative_e2_" if batch == "e1e3:e2" else f"windport_conservative_{batch.replace(':', '_')}_"
    ds = sorted(p for p in (ROOT / "results").glob(pre + "*") if p.is_dir() and len(p.name) == len(pre) + 12)
    assert len(ds) == 1, (batch, ds)
    return ds[0]


# ================================================================ rerun: committed batches of the conservative lifting rule
def rerun_batches():
    import windport_rerun_conservative as RR
    return [b for b in RR.SRC if b != "runs:e6"]


def init_rerun(outs):
    import windport_extra as X
    import windport_rerun_conservative as RR
    from windport import archetypes as A
    from windport import check as C
    from windport import check_lift as CL
    from windport import lift as LF
    pin(list(range(1, os.cpu_count())))
    LF.install()
    C.check = CL.check
    X.kassels_order = RR.kassels_lift
    A.use(GEO)
    _OUTS.update({k: Path(v) for k, v in outs.items()})


_OUTS = {}


def chunk_rerun(arg):
    import windport_rerun_conservative as RR
    batch, ks = arg
    for k in ks:
        f = _OUTS[batch] / "points" / RR.fname(batch, k)
        if not f.exists():
            write_json(f, RR.compute(batch, k))
    return batch, ks


def finish_rerun(batch, out):
    import windport_rerun_conservative as RR
    ks = RR.keys(batch)
    rs = [x for k in ks for x in RR.rows(batch, k, json.loads((out / "points" / RR.fname(batch, k)).read_text(encoding="utf-8")))]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, RR.cols(batch), extrasaction="raise")
        w.writeheader()
        w.writerows(rs)
    new = (out / "points.csv").read_text(encoding="utf-8").splitlines()
    old = (conservative_dir(batch) / "points.csv").read_text(encoding="utf-8").splitlines()
    assert new[0] == old[0], "columns differ"
    rd = lambda lines: {r["key"]: (line, r) for line, r in zip(lines[1:], csv.DictReader(lines))}
    N, O = rd(new), rd(old)
    assert set(N) == set(O), "row keys differ"
    diff = [dict(key=k, cls=RR.lift_class(r), same=int(line == O[k][0]), check_ok=r.get("check_ok", "")) for k, (line, r) in N.items()]
    wcsv(out / "diff.csv", diff, ["key", "cls", "same", "check_ok"])
    s = dict(batch=batch, conservative=conservative_dir(batch).name, rows=len(diff), same=sum(x["same"] for x in diff),
             check_fail=sum(1 for x in diff if x["check_ok"] in ("0", "False")))
    (out / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return s


def run_rerun(a):
    import windport_rerun_conservative as RR
    outs, progs, chunks = {}, {}, []
    for b in rerun_batches():
        out, cfg = out_dir(b, dict(src=RR.SRC[b], semantics="lift_tu0.05_head"))
        prepare(out, cfg)
        outs[b] = out
        ks = RR.keys(b)
        todo = [k for k in ks if not (out / "points" / RR.fname(b, k)).exists()]
        progs[b] = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, f"main geometry rerun {b}", "maingeom")
        n = RR.CHUNK.get(b, a.chunk)
        chunks += [(b, todo[i:i + n]) for i in range(0, len(todo), n)]
    chunks.sort(key=lambda x: x[0] not in ("extra:port", "e1e3:e3", "extra:fix", "runs:sens"))       # slow batches dispatched first
    try:
        for b, ds in slot_imap(chunk_rerun, chunks, a.procs, initializer=init_rerun, initargs=({k: str(v) for k, v in outs.items()},), slots_dir=a.slots,
                               tag="maingeom"):
            progs[b].write(done=progs[b].d["done"] + len(ds))
    except BaseException as e:
        for pg in progs.values():
            pg.write(state="failed", note=repr(e)[:300])
        raise
    from windport import archetypes as A
    A.use(GEO)
    for b, out in outs.items():
        s = finish_rerun(b, out)
        progs[b].write(state="done", note=json.dumps(s, ensure_ascii=False)[:300])
        print(out.name, json.dumps(s, ensure_ascii=False))


# ================================================================ e2
def init_e2():
    import windport_e2_conservative as E2D
    from windport import archetypes as A
    E2D.init()
    A.use(GEO)


def run_e2(a):
    import windport_e2 as E2
    import windport_e2_conservative as E2D
    src = (ROOT / E2D.SRC).read_bytes()
    rows = list(csv.DictReader(src.decode("utf-8").splitlines()))
    out, cfg = out_dir("e2", dict(src=E2D.SRC, long=E2D.LONG, grid=E2.GRID, max_threads=E2D.MAX_T))
    prepare(out, cfg)
    (out / "points_long").mkdir(exist_ok=True)
    fn = lambda k, lg=False: out / ("points_long" if lg else "points") / (k.replace("|", "_") + ".json")
    lrows = list(csv.DictReader((ROOT / E2D.LONG).read_text(encoding="utf-8").splitlines()))
    byk = {r["key"]: r for r in rows}
    jobs = [(r["key"], r, E2.GRID["time_s"], False) for r in rows] + [(k, byk[k], 600.0, True) for k in sorted(r["key"] for r in lrows)]
    todo = [j for j in jobs if not fn(j[0], j[3]).exists()]
    todo.sort(key=lambda j: not j[3])
    prog = Progress(out / "progress.json", len(jobs), len(jobs) - len(todo), E2D.PAR, "main geometry E2 (540 x 60 s + 17 x 600 s)", "maingeom")
    from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
    slots = None
    if a.slots:
        sys.path.insert(0, a.slots)
        from cpu_slots import Slots
        slots = Slots(f"maingeom-e2-{os.getpid()}")
    live = {}
    try:
        with ProcessPoolExecutor(E2D.PAR, initializer=init_e2) as ex:
            while todo or live:
                while todo and len(live) < E2D.PAR:
                    n = 1
                    if slots:
                        slots.want(E2D.MAX_T * min(E2D.PAR, len(todo) + len(live)))
                        while not slots.take():
                            time.sleep(0.5)
                        while n < E2D.MAX_T and slots.take():
                            n += 1
                    k, r, ts, lg = todo.pop(0)
                    live[ex.submit(E2D.run, (k, n, r, ts))] = (n, lg)
                done, _ = wait(live, timeout=1.0, return_when=FIRST_COMPLETED)
                for f in done:
                    n, lg = live.pop(f)
                    if slots:
                        for _ in range(n):
                            slots.give()
                    res = f.result()
                    write_json(fn(res["key"], lg), res)
                    prog.write(done=prog.d["done"] + 1)
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    finally:
        if slots:
            slots.close()
    (out / "e2long").mkdir(exist_ok=True)
    lr = []
    for r in lrows:
        a60, b6 = json.loads(fn(r["key"]).read_text(encoding="utf-8")), json.loads(fn(r["key"], True).read_text(encoding="utf-8"))
        lr.append(dict(key=r["key"], w1=b6["w1"], sim=b6["sim"], cp60_best=a60["cp_best"], cp60_bound=a60["cp_bound"], cp60_status=a60["cp_status"],
                       cp_best=b6["cp_best"], cp_bound=b6["cp_bound"], cp_status=b6["cp_status"], cp_check=b6["cp_check"], sim_check=b6["sim_check"]))
    wcsv(out / "e2long" / "points.csv", lr, E2D.LCOLS)
    res = [json.loads(fn(r["key"]).read_text(encoding="utf-8")) for r in rows]
    wcsv(out / "points.csv", res, E2.COLS)
    s = dict(rows=len(res), optimal=sum(r["cp_status"] == "OPTIMAL" for r in res), sim_over_cp=sum(int(r["sim"]) > int(r["cp_best"]) for r in res),
             check_fail=sum(str(r["sim_check"]) != "1" for r in res) + sum(str(r["cp_check"]) == "0" for r in res), long=len(lrows),
             long_optimal=sum(1 for r in lr if r["cp_status"] == "OPTIMAL"))
    (out / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(s, ensure_ascii=False))
    print(out.name, json.dumps(s, ensure_ascii=False))


# ================================================================ sims: spatial, core, span, xscan, yards, cdv
def core_keys():
    g, out = CORE, []
    for first, sc, lay, arr, K, h in itertools.product(g["first"], g["scen"], g["lay"], g["arr"], g["K"], g["hold"]):
        for x in (g["side_extra"] if lay == "side" else [0.0]):
            out.append(T.enc(dict(first=first, scen=sc, lay=lay, arr=arr, K=K, hold=h, extra=x)))
    return out


def core_cfg(d):
    """One core point: port-time config of the spatial additions (A1, 6 cradles, vessel crane open for 200 h from G = 24 h);
    first cradle and layout set from the key."""
    import windport_spatial as A
    mode = "on_road" if d["lay"] == "side" else d["lay"]
    c = A.cfg_of("core", dict(what="port", kind="A1", scen=d["scen"], mode=mode, arr=d["arr"], K=d["K"], n_v=CORE["n_v"], hold=d["hold"]))
    if d["lay"] == "side":
        c["geo"] = A.side_geo(d["scen"])
    c["geo"] = dict(c["geo"], gate_cradle_m=float(d["first"]))
    if float(d.get("extra") or 0):
        c["p"] = dict(c["p"], turn_extra={f"apron_{k}": float(d["extra"]) for k in range(int(c["geo"]["n_cradles"]))})
    return c


def yard_keys():
    import windport_spatial as A
    g, out = A.GRIDS["siteport"], []
    for site, m, x, h in itertools.product(YARDS["sites"], T.MODES, YARDS["extra"], YARDS["hold"]):
        for arr, K in itertools.product(g["arr"][site], g["K"]):
            out.append(T.enc(dict(what="port", kind="map:" + site, st="multi", scen="base", mode=m, arr=arr, K=K, n_v=g["n_v"], hold=h, extra=x)))
    return out


def yard_cfg(d):
    import windport_spatial as A
    c = A.cfg_of("siteport", {k: v for k, v in d.items() if k != "extra"})
    c["p"] = dict(c["p"], turn_extra=A.turn_extra(d["kind"][4:], "multi", float(d["extra"])))
    return c


def port_point(c):
    """One port-time point: conservative-rule simulation (sim4.simulate4), combined checker (check_all), L*(n_v) of W″_lift and
    W″_lift(port time)."""
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
    return dict(port_h=None if ph is None else round(ph, 6), lifts=len(ls), lstar_lo=round(lo / H, 6), lstar_hi=round(hi / H, 6),
                w_at_port=None if ph is None else f(ph * H + 0.5e-6 * H), check_ok=int(ck["ok"]), check_err=ck["errors"][:2], n_clear=ck["n_clear"],
                n_under=ck["n_under"], trips=len(sim.trips), map_sha256=net.map_sha256)


def sim_point(part, key):
    if part in SPATIAL or part == "cdv":
        import windport_rerun_spatial as E
        return E.run_point(part, key)
    if part == "core":
        d = T.dec(key)
        return dict(port_point(core_cfg(d)), **d)
    if part == "yards":
        d = T.dec(key)
        return dict(port_point(yard_cfg(d)), **d)
    if part == "span":
        import windport_span as SP
        a = json.loads(key)
        return SP.one(tuple(a))
    if part == "xscan":
        import windport_xscan as XS
        return XS.one(tuple(json.loads(key)))
    raise KeyError(part)


def sim_keys(part, chosen=None):
    import windport_spatial as A
    if part in SPATIAL:
        return A.keys(part)
    if part == "cdv":
        return A.keys("cdv", chosen)
    if part == "core":
        return core_keys()
    if part == "yards":
        return yard_keys()
    if part == "span":
        import windport_span as SP
        g = SP.GRID
        return [json.dumps(list(x)) for x in itertools.product(g["span"], g["scen"], g["mode"], g["arr"], g["hold"], g["K"])]
    if part == "xscan":
        import windport_xscan as XS
        xs = sorted(set(XS.XS) | set(XS2))
        return [json.dumps([m, arr, x, K]) for m in XS.GRID["mode"] for arr in ("S0", "S1") for x in (xs if arr == "S0" else [0.0]) for K in XS.GRID["K"]]
    raise KeyError(part)


def init_sims(outs):
    from windport import archetypes as A
    from windport import lift as LF
    pin(list(range(1, os.cpu_count())))
    LF.install()
    A.use(GEO)
    _OUTS.update({k: Path(v) for k, v in outs.items()})


def chunk_sims(arg):
    part, ks = arg
    for k in ks:
        f = _OUTS[part] / "points" / T.fname(k)
        if not f.exists():
            write_json(f, dict(sim_point(part, k), key=k))
    return part, ks


def sim_row(part, key, r):
    if part in SPATIAL or part == "cdv":
        import windport_rerun_spatial as E
        return E.row_of(key, r)
    out = {k: v for k, v in r.items() if k not in ("check_err", "map_sha256")}
    if isinstance(out.get("check_ok"), bool):
        out["check_ok"] = int(out["check_ok"])
    return out


def chosen_file():
    out, _ = codesign_dir()
    f = out / "chosen.json"
    assert f.exists(), "run --part codesign first"
    return f


def run_sims(parts, a):
    outs, progs, chunks, ks = {}, {}, [], {}
    for part in parts:
        extra = dict(chosen_sha256=hashlib.sha256(chosen_file().read_bytes()).hexdigest()) if part == "cdv" else {}
        if part == "core":
            extra = dict(grid=CORE)
        if part == "yards":
            extra = dict(grid=YARDS)
        if part == "spatial":
            for p_ in SPATIAL:
                out, cfg = out_dir(f"spatial_{p_}")
                outs[p_] = (out, cfg)
            continue
        outs[part] = out_dir(part, extra)
    chosen = json.loads(chosen_file().read_text(encoding="utf-8")) if "cdv" in outs else None
    for part, (out, cfg) in outs.items():
        prepare(out, cfg)
        ks[part] = sim_keys(part, chosen)
        todo = [k for k in ks[part] if not (out / "points" / T.fname(k)).exists()]
        progs[part] = Progress(out / "progress.json", len(ks[part]), len(ks[part]) - len(todo), a.procs, f"main geometry {part}", "maingeom")
        chunks += [(part, todo[i:i + a.chunk]) for i in range(0, len(todo), a.chunk)]
    chunks.sort(key=lambda x: x[0] != "yards")                     # shipyard map points are slow: dispatched first
    try:
        for part, ds in slot_imap(chunk_sims, chunks, a.procs, initializer=init_sims, initargs=({k: str(v[0]) for k, v in outs.items()},),
                                  slots_dir=a.slots, tag="maingeom"):
            progs[part].write(done=progs[part].d["done"] + len(ds))
    except BaseException as e:
        for pg in progs.values():
            pg.write(state="failed", note=repr(e)[:300])
        raise
    for part, (out, _) in outs.items():
        rows = [sim_row(part, k, json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8"))) for k in ks[part]]
        wcsv(out / "points.csv", rows)
        bad = sum(1 for r in rows if str(r.get("check_ok")) in ("0", "False"))
        note = f"{len(rows)} points; checker failures {bad}"
        progs[part].write(state="done", note=note)
        print(out.name, note)


# ================================================================ codesign
def cd_items():
    import windport_spatial_analytic as AA
    return [x for sc in AA.GRIDS["codesign"]["scen"] for x in AA.cd_configs(sc)]


def cd_cfg(x):
    import windport_spatial_analytic as AA
    g = AA.GRIDS["codesign"]
    return dict(geo=x["geo"], p=x["p"], S=x["S"], K=x["K"], lift=x["lift"], horizon_h=g["G"] + g["open_h"], cal=dict(crane=[[g["G"], g["G"] + g["open_h"]]]),
                n_load=max(g["n_v"]), hold=x["hold"], rule="fcfs")


def cd_point(i):
    import windport_spatial_analytic as AA
    from windport import bound3 as B3
    from windport import bound4 as B4
    from windport import bound_all as BA
    x = cd_items()[i]
    c = cd_cfg(x)
    f, f0 = BA.w2_lift(c, BA.parts(c, lift=True)), B4.wprime4_fn(c)
    return [dict(i=i, n_v=n, lstar_h=round(B3.lstar(f, n)[1] / H, 4), lstar_wprime_h=round(B3.lstar(f0, n)[1] / H, 4)) for n in AA.GRIDS["codesign"]["n_v"]]


def init_cd():
    from windport import archetypes as A
    pin(list(range(1, os.cpu_count())))
    A.use(GEO)


def cd_chunk(ix):
    return [r for i in ix for r in cd_point(i)]


def codesign_dir():
    import windport_spatial_analytic as AA
    return out_dir("codesign", dict(grid=AA.GRIDS["codesign"]))


def rank(rows, col, g):
    """Ranking of the spatial additions (windport_spatial_analytic.codesign): sort by cost, L*, number of infrastructure
    items and config; the recheck set takes the top 3 etc.; returns (best, chosen)."""
    for r in rows:
        Lh = r[col]
        for rate in g["rates"]:
            r[f"cost_{rate // 1000}k"] = round(Lh / 24 * rate + r["K"] * g["set_day"] * g["cycle"] + r["S"] * g["support"] / g["calls"])
    best, chosen = [], {}
    for sc in g["scen"]:
        for n in g["n_v"]:
            for rate in g["rates"]:
                ck = f"cost_{rate // 1000}k"
                rs = sorted((r for r in rows if r["scen"] == sc and r["n_v"] == n), key=lambda r: (r[ck], r[col], r["hold"] + r["pass_"] + r["widen"], r["cfg"]))
                plain = [r for r in rs if not (r["hold"] or r["pass_"] or r["widen"])]
                infra = [[r for r in rs if (r["hold"], r["pass_"], r["widen"]) == c] for c in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1))]
                top = rs[:g["top"]]
                best.append(dict(scen=sc, n_v=n, rate=rate, top=[r["cfg"] for r in top]))
                for r in top + plain[:g["top"]] + [x for lst in infra for x in lst[:g["top"]]]:
                    chosen[r["cfg"]] = json.loads(r["cfg"])
    return best, chosen


def run_codesign(a):
    import windport_spatial_analytic as AA
    g = AA.GRIDS["codesign"]
    out, cfg = codesign_dir()
    prepare(out, cfg)
    items = cd_items()
    done = {}
    for f in (out / "points").glob("*.json"):
        for r in json.loads(f.read_text(encoding="utf-8")):
            done.setdefault(r["i"], []).append(r)
    todo = [i for i in range(len(items)) if i not in done]
    prog = Progress(out / "progress.json", len(items), len(items) - len(todo), a.procs, "main geometry codesign (W″_lift, W′)", "maingeom")
    for rs in slot_imap(cd_chunk, [todo[k:k + 8] for k in range(0, len(todo), 8)], a.procs, initializer=init_cd, slots_dir=a.slots, tag="maingeom"):
        write_json(out / "points" / f"{rs[0]['i']}.json", rs)
        for r in rs:
            done.setdefault(r["i"], []).append(r)
        prog.write(done=len(done))
    rows = []
    for i, x in enumerate(items):
        for r in done[i]:
            n = r["n_v"]
            rows.append(dict({k: v for k, v in x.items() if k not in ("geo", "p")}, n_v=n, lstar_h=r["lstar_h"], lstar_wprime_h=r["lstar_wprime_h"],
                             cfg=json.dumps(dict(geo=x["geo"], p=x["p"], S=x["S"], K=x["K"], lift=x["lift"], hold=x["hold"], n_v=n), sort_keys=True)))
    rw = [dict(r) for r in rows]
    best, chosen = rank(rows, "lstar_h", g)
    best0, chosen0 = rank(rw, "lstar_wprime_h", g)
    for r, r0 in zip(rows, rw):
        r.update({f"{k}_wprime": r0[k] for k in r0 if k.startswith("cost_")})
    wcsv(out / "codesign.csv", rows)
    newtop = []
    for b, b0 in zip(best, best0):
        newtop += [dict(scen=b["scen"], n_v=b["n_v"], rate=b["rate"], rank=j + 1, cfg=c) for j, c in enumerate(b["top"]) if c not in b0["top"]]
    wcsv(out / "best.csv", [dict(scen=b["scen"], n_v=b["n_v"], rate=b["rate"], top_lift=" ; ".join(b["top"]), top_wprime=" ; ".join(b0["top"])) for b, b0 in zip(best, best0)])
    wcsv(out / "newtop.csv", newtop)
    allc = dict(chosen0, **chosen)
    (out / "chosen.json").write_text(json.dumps([allc[k] for k in sorted(allc)], ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    note = f"{len(items)} configs; recheck set W″_lift {len(chosen)}, W′ {len(chosen0)}, union {len(allc)}; {len(newtop)} new in W″_lift top 3"
    prog.write(state="done", note=note)
    print(out.name, note)


# ================================================================ geom, example, critical
def run_geom():
    import windport_extra as X
    from windport import archetypes as A
    from windport import geomcheck as GC
    out, cfg = out_dir("geom")
    cfg["geomcheck_sha256"] = hashlib.sha256((ROOT / "windport/geomcheck.py").read_bytes()).hexdigest()
    (out / "points").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    rows, sums = [], []
    for first in (40.0, 150.0, 170.0):
        geo = dict(A.GEOMETRIES[GEO] if first != 40.0 else A.GEOMETRIES["legacy40"], gate_cradle_m=first)
        for kind, sc, m, arr in itertools.product(A.KINDS, ("base", "lane"), T.MODES, ("S1", "S3")):
            c = X.port_cfg(sc, m, arr, 2, 10, 0)
            c["geo"] = dict(c["geo"], kind=kind, **geo)
            r = GC.check(c)
            tag = dict(first=first, kind=kind, scen=sc, mode=m, arr=arr)
            rows += [dict(tag, **x) for x in r["rows"]]
            sums.append(dict(tag, ok=r["ok"], piles_on_land=r["piles_on_land"], **{f"min_{k}": v for k, v in r["min_clear"].items()}))
    for lv in ("85", "100", "110", "120"):
        c = X.port_cfg("base", "on_road", "S1", 2, 10, 0)
        c["p"] = dict(c["p"], **{k: v for k, v in T.E7LEV[lv].items() if k != "t"})
        r = GC.check(c)
        sums.append(dict(first=170.0, kind="A1", scen=f"E7 Lv={lv}", mode="on_road", arr="S1", ok=r["ok"], piles_on_land=r["piles_on_land"],
                         **{f"min_{k}": v for k, v in r["min_clear"].items()}))
    c = X.port_cfg("longpile", "on_road", "S1", 2, 10, 0)
    r = GC.check(c)
    sums.append(dict(first=170.0, kind="A1", scen="longpile Lv=123.6", mode="on_road", arr="S1", ok=r["ok"], piles_on_land=r["piles_on_land"],
                     **{f"min_{k}": v for k, v in r["min_clear"].items()}))
    wcsv(out / "turns.csv", rows)
    wcsv(out / "summary.csv", sums)
    print(out.name)


def run_example():
    import windport_analytic as A6
    from windport import bound_all as BA
    out, cfg = out_dir("example", dict(grid=A6.GRIDS["example"]))
    prepare(out, cfg)
    rows = A6.example()
    g = A6.GRIDS["example"]
    for r in rows:
        c = A6.cfg_e4("A1", r["scen"], r["mode"], r["K"], g["S"], g["L"], g["G"])
        w = BA.parts(c, lift=True)
        v, keys, cls, sub, nat = BA.binding(BA.terms(w, g["L"] * H))
        r.update(w2_lift=v, binding_lift="+".join(keys), cls_lift=cls, eps_u=round(w.get("eps_u", 0.0), 1), dq_lift=round(w["P"].dq, 1),
                 tl_lift=round(w["P"].tl, 1), c_lift=round(w["P"].c, 1), hd_lift=round(w["P"].hd, 1))
    wcsv(out / "example.csv", rows)
    print(out.name)


def run_critical():
    import windport_analytic as A6
    out, cfg = out_dir("critical", dict(grid=A6.GRIDS["critical"]))
    prepare(out, cfg)
    wcsv(out / "critical.csv", A6.critical())
    print(out.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=6)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    from windport import archetypes as A
    from windport import lift as LF
    A.use(GEO)
    parts = a.part.split(",")
    if "rerun" in parts:
        run_rerun(a)
    if "codesign" in parts:
        run_codesign(a)
    sims = [p for p in parts if p in SIMS]
    if sims:
        LF.install()
        run_sims(sims, a)
    if "e2" in parts:
        run_e2(a)
    if "geom" in parts:
        run_geom()
    if "example" in parts:
        run_example()
    if "critical" in parts:
        run_critical()


if __name__ == "__main__":
    main()
