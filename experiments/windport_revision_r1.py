"""The 115 m spacing re-runs: every parameterised port batch that supplies numbers to the manuscript is re-run with the in-line
cradle spacing 115 m (L_v + δ) and spliced back into the committed directory format (same splice method as windport_main2_runs), plus
the recheck and invariance checks. Main geometry main2, conservative lifting rule; workers use windport_main2_runs.install() (LF,
check_lift, Kassels order, main2, side-by-side via rows_cfg) + windport_revision_lib.install_spacing(115) + windport_netcache.
Committed modules and the modules of the revision studies are not changed.

Scope (the batches whose results the manuscript reads):
  RR      batches of windport_rerun_conservative: e1e3:e1, e1h, rel, e3; runs:e4, e5, e7, pocket, conv, e2c, sens, sens7;
          extra:port, fix, mix6, mixx, sens, sens5 - **all keys** of each batch (rows with S ≤ 1 are recomputed too: for A1 / A2
          loading the S ≤ 1 rows equal the 110 m rows field by field, which checks the reuse; in A3 the second lane joins the
          east end of the quay front and the ramp with unloading tasks lies after the last cradle position, so these two kinds
          of S ≤ 1 rows change with the spacing). extra:pub (Rønne reproduction, geometry of the public case model) and runs:e6 (shipyard map) are excluded.
  spatial all keys of ablate and hphd of the spatial additions; in-line keys of upsize and reach (side-by-side reused, see inv).
  core    in-line keys of the core cases of the main geometry (three first-cradle positions, Q_h, alternative turns 0);
          side-by-side reused.
  xscan   fine grid of release times of the main geometry (S0 / S1; as a check).
  sens    t_u sensitivity of the core cases of the main geometry (windport_sens_conservative.one handles the lifting rule itself;
          separate process pool that installs only main2 and the spacing).
  e2      the 180 E2 small cases with S = 2 and the hard ones among them at 600 s (CP-SAT, as windport_maingeom.run_e2); for the 360
          cases with S ≤ 1 the model data are checked to be identical item by item (inv).
  ex      example table and critical lengths of the main geometry (analytic, windport_analytic.example / critical, as
          windport_maingeom.run_example / run_critical).
  inv     invariance checks: CP-SAT model data of E2 S ≤ 1; side-by-side rows (side-by-side keys of reach / upsize of the spatial
          additions, side-by-side rows of the core cases) sampled and recomputed at 115 m.
  recheck unified-bound W″_lift recheck of all re-run rows (windport_recheck_maingeom.one, configurations as
          windport_recheck_main2.cfg_of); gives the recheck rows.csv read by the manuscript.
Output results/windport_revision_r1_<part>_<config hash>/: config.json (SHA-256 of code and maps, spacing), progress.json, points/
(per point, resumable); splice/<batch>/points.csv, diff.csv, summary.json (columns and row order as in the committed directories).
Run: python experiments/windport_revision_r1.py --part x --procs 20 --slots DIR
"""
import argparse
import csv
import hashlib
import io
import itertools
import json
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
SPACING = 115.0
RR_B = ["e1e3:e1", "e1e3:e1h", "e1e3:rel", "e1e3:e3", "runs:e4", "runs:e5", "runs:e7", "runs:pocket", "runs:conv", "runs:e2c", "runs:sens", "runs:sens7",
        "extra:port", "extra:fix", "extra:mix6", "extra:mixx", "extra:sens", "extra:sens5"]
SPATIAL_B = ["unified:ablate", "unified:hphd", "unified:upsize", "unified:reach"]
OTHER_B = ["maingeom:core", "conservative:xscan"]
X_B = RR_B + SPATIAL_B + OTHER_B
SENS_B = ["conservative:sens"]
CODE = ["experiments/windport_revision_r1.py", "experiments/windport_revision_lib.py", "experiments/windport_netcache.py", "experiments/windport_main2_runs.py",
        "experiments/windport_recheck_main2.py", "experiments/windport_maingeom.py", "experiments/windport_recheck_maingeom.py", "experiments/windport_recheck_unified.py",
        "experiments/windport_rerun_conservative.py", "experiments/windport_sens_conservative.py", "experiments/windport_xscan.py", "experiments/windport_e2_conservative.py",
        "experiments/windport_rerun_spatial.py", "experiments/windport_spatial.py", "experiments/windport_extra.py", "experiments/windport_analytic.py",
        "experiments/windport_runs.py", "experiments/windport_sim.py", "experiments/windport_e2.py", "occupancy/sim.py", "occupancy/network.py",
        "occupancy/params.py", "occupancy/tasks.py", "exact/check.py", "exact/model.py"] + \
    sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "windport").glob("*.py") if p.name not in ("port_survey.py",))


def code_hash():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}


def out_dir(name, extra=None):
    from windport import main2 as M2
    cfg = dict(task="revision", round=1, part=name, geometry=M2.MAIN2, spacing=SPACING, code=code_hash(), semantics="lift_tu0.05_head", **(extra or {}))
    return ROOT / "results" / f"windport_revision_r1_{name}_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}", cfg


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


def base_dirs():
    """Batch → directory the manuscript currently reads (dirs() of windport_report_main2: the run directories of the main
    geometry, replaced by splice subdirectories where the main2 geometry spliced them)."""
    import windport_report_main2 as HR
    return HR.dirs()["run"]


# ================================================================ keys, single points, rows
def keys_of(b):
    import windport_rerun_conservative as RR
    import windport_spatial as TA
    import windport_maingeom as F
    if b in RR_B:
        return RR.keys(b)
    if b.startswith("unified:"):
        p = b.split(":")[1]
        ks = TA.keys(p)
        return ks if p in ("ablate", "hphd") else [k for k in ks if T.dec(k).get("lay") != "side"]
    if b == "maingeom:core":
        return [k for k in F.core_keys() if T.dec(k)["lay"] != "side"]
    if b == "conservative:xscan":
        return F.sim_keys("xscan")
    if b == "conservative:sens":
        import windport_sens_conservative as M
        import windport_sens_maingeom as FS
        g = M.GRID
        return [json.dumps(list(x)) for x in itertools.product(FS.VARS, g["scen"], g["mode"], g["arr"], g["K"])]
    raise KeyError(b)


def compute(b, k):
    import windport_rerun_conservative as RR
    import windport_maingeom as F
    if b in RR_B:
        return RR.compute(b, k)
    if b.startswith("unified:"):
        import windport_rerun_spatial as E
        return E.run_point(b.split(":")[1], k)
    if b == "maingeom:core":
        return F.sim_point("core", k)
    if b == "conservative:xscan":
        return dict(F.sim_point("xscan", k), key=k)
    if b == "conservative:sens":
        import windport_sens_conservative as M
        return M.one(tuple(json.loads(k)))
    raise KeyError(b)


def rows_of(b, k, r):
    import windport_rerun_conservative as RR
    import windport_maingeom as F
    if b in RR_B:
        return RR.rows(b, k, r)
    if b.startswith("unified:"):
        import windport_rerun_spatial as E
        return [E.row_of(k, r)]
    if b == "maingeom:core":
        return [F.sim_row("core", k, dict(r, key=k))]
    if b == "conservative:xscan":
        return [F.sim_row("xscan", k, r)]
    if b == "conservative:sens":
        return [r]
    raise KeyError(b)


def ident(b, row):
    if b == "conservative:sens":
        return "|".join(str(row[c]) for c in ("var", "scen", "mode", "arr", "K"))
    return row["key"]


def fname(b, k):
    return hashlib.sha256(json.dumps([b, k]).encode()).hexdigest()[:24] + ".json"


# ================================================================ worker processes
_OUT = {}


def install(sens_only=False):
    import windport_revision_lib as K
    import windport_netcache as NC
    if sens_only:
        from windport import main2 as M2
        M2.use()
    else:
        import windport_main2_runs as HX
        HX.install()
    K.install_spacing(SPACING)
    NC.install()


def init(out, sens_only):
    pin(list(range(1, os.cpu_count())))
    install(sens_only)
    _OUT["d"] = Path(out)


def chunk(items):
    for b, k in items:
        f = _OUT["d"] / "points" / fname(b, k)
        if not f.exists():
            write_json(f, compute(b, k))
    return items


def row_line(cols, row):
    s = io.StringIO()
    w = csv.DictWriter(s, cols, extrasaction="ignore")
    w.writerow(row)
    return s.getvalue().rstrip("\r\n")


def finish(out, batches, its):
    """Per batch: take points.csv of the directory the manuscript currently reads, replace the re-run keys by the 115 m rows (same
    columns, same order), and write splice/<batch>/points.csv, diff.csv, summary.json."""
    BD = base_dirs()
    pts = {}
    for b, k in its:
        pts.setdefault(b, {})[k] = json.loads((out / "points" / fname(b, k)).read_text(encoding="utf-8"))
    summ = {}
    for b in batches:
        src = BD[b] / "points.csv"
        lines = src.read_text(encoding="utf-8").splitlines()
        cols = next(csv.reader([lines[0]]))
        old = list(csv.DictReader(lines))
        new_rows = {}
        for k, r in pts.get(b, {}).items():
            for row in rows_of(b, k, r):
                new_rows[ident(b, row)] = row
        d = out / "splice" / b.replace(":", "_")
        d.mkdir(parents=True, exist_ok=True)
        for f in BD[b].iterdir():
            if f.is_file() and f.suffix in (".md", ".json") and f.name not in ("progress.json", "config.json", "summary.json"):
                (d / f.name).write_bytes(f.read_bytes())
        res, diff = [], []
        for line, r in zip(lines[1:], old):
            i = ident(b, r)
            if i in new_rows:
                nl = row_line(cols, new_rows[i])
                res.append(nl)
                diff.append(dict(key=i, same=int(nl == line), check_ok=new_rows[i].get("check_ok", "")))
            else:
                res.append(line)
        assert len(diff) == len(new_rows), (b, len(diff), len(new_rows))
        (d / "points.csv").write_bytes(("\r\n".join([lines[0]] + res) + "\r\n").encode("utf-8"))
        wcsv(d / "diff.csv", diff, ["key", "same", "check_ok"])
        s = dict(batch=b, src=str(BD[b].relative_to(ROOT / "results")).replace("\\", "/"), rows=len(old), recomputed=len(diff), same=sum(x["same"] for x in diff),
                 check_fail=sum(1 for x in diff if str(x["check_ok"]) in ("0", "False")))
        (d / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        summ[b] = s
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return summ


def run_pool(name, batches, a, sens_only=False):
    out, cfg = out_dir(name, dict(batches=batches, src={b: str(base_dirs()[b].relative_to(ROOT / "results")).replace("\\", "/") for b in batches}))
    prepare(out, cfg)
    its = [(b, k) for b in batches for k in keys_of(b)]
    todo = [x for x in its if not (out / "points" / fname(*x)).exists()]
    prog = Progress(out / "progress.json", len(its), len(its) - len(todo), a.procs, f"115 m spacing re-runs: {name}", "revision")
    slow = {"e1e3:e3", "extra:fix"}
    todo.sort(key=lambda x: x[0] not in slow)
    n = lambda b: 1 if b in slow else a.chunk
    chunks, cur = [], []
    for x in todo:
        if x[0] in slow:
            chunks.append([x])
        else:
            cur.append(x)
            if len(cur) >= a.chunk:
                chunks.append(cur)
                cur = []
    if cur:
        chunks.append(cur)
    try:
        for ds in slot_imap(chunk, chunks, a.procs, initializer=init, initargs=(str(out), sens_only), slots_dir=a.slots, tag="revision"):
            prog.write(done=prog.d["done"] + len(ds))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    s = finish(out, batches, its)
    note = "; ".join(f"{b} {v['recomputed']} rows ({v['same']} same, {v['check_fail']} checker failures)" for b, v in s.items())
    prog.write(state="done", note=note[:900])
    print(out.name)
    print(json.dumps(s, ensure_ascii=False, indent=1))


# ================================================================ E2 (CP-SAT)
def e2_rows():
    BD = base_dirs()
    rows = list(csv.DictReader(open(BD["e1e3:e2"] / "points.csv", encoding="utf-8")))
    lrows = list(csv.DictReader(open(BD["e1e3:e2"] / "e2long" / "points.csv", encoding="utf-8")))
    return rows, lrows


def init_e2():
    import windport_e2_conservative as E2D
    E2D.init()
    install()


def run_e2(a):
    import windport_e2 as E2
    import windport_e2_conservative as E2D
    rows, lrows = e2_rows()
    s2 = [r for r in rows if int(r["S"]) == 2]
    l2 = [r for r in lrows if r["key"].split("|")[3] == "S2"]
    out, cfg = out_dir("e2", dict(grid=E2.GRID, max_threads=E2D.MAX_T, keys=sorted(r["key"] for r in s2), long=sorted(r["key"] for r in l2)))
    prepare(out, cfg)
    (out / "points_long").mkdir(exist_ok=True)
    fn = lambda k, lg=False: out / ("points_long" if lg else "points") / (k.replace("|", "_") + ".json")
    jobs = [(r["key"], r, E2.GRID["time_s"], False) for r in s2] + [(r["key"], next(x for x in s2 if x["key"] == r["key"]), 600.0, True) for r in l2]
    todo = [j for j in jobs if not fn(j[0], j[3]).exists()]
    todo.sort(key=lambda j: not j[3])
    prog = Progress(out / "progress.json", len(jobs), len(jobs) - len(todo), E2D.PAR, "115 m spacing re-runs: E2 S = 2 (CP-SAT 60 s / 600 s)", "revision")
    from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
    slots = None
    if a.slots:
        sys.path.insert(0, a.slots)
        from cpu_slots import Slots
        slots = Slots(f"revision-e2-{os.getpid()}")
    live = {}
    par = min(E2D.PAR, a.procs)
    try:
        with ProcessPoolExecutor(par, initializer=init_e2) as ex:
            while todo or live:
                while todo and len(live) < par:
                    n = 1
                    if slots:
                        slots.want(E2D.MAX_T * min(par, len(todo) + len(live)))
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
    # splice back: the S = 2 rows and the 600 s rows are replaced by the 115 m ones (columns as committed)
    new = {r["key"]: json.loads(fn(r["key"]).read_text(encoding="utf-8")) for r in s2}
    newl = {r["key"]: json.loads(fn(r["key"], True).read_text(encoding="utf-8")) for r in l2}
    d = out / "splice" / "e1e3_e2"
    (d / "e2long").mkdir(parents=True, exist_ok=True)
    res = [dict(r, **{c: new[r["key"]][c] for c in E2.COLS if c in new[r["key"]]}) if r["key"] in new else r for r in rows]
    wcsv(d / "points.csv", res, E2.COLS)
    lr = []
    for r in lrows:
        if r["key"] in newl:
            a60, b6 = new[r["key"]], newl[r["key"]]
            r = dict(key=r["key"], w1=b6["w1"], sim=b6["sim"], cp60_best=a60["cp_best"], cp60_bound=a60["cp_bound"], cp60_status=a60["cp_status"],
                     cp_best=b6["cp_best"], cp_bound=b6["cp_bound"], cp_status=b6["cp_status"], cp_check=b6["cp_check"], sim_check=b6["sim_check"])
        lr.append(r)
    wcsv(d / "e2long" / "points.csv", lr, E2D.LCOLS)
    old = {r["key"]: r for r in rows}
    diff = [dict(key=k, same=int(all(str(v[c]) == str(old[k][c]) for c in ("sim", "w1", "cp_best", "cp_status"))), sim_old=old[k]["sim"], sim_new=v["sim"],
                 cp_old=old[k]["cp_best"], cp_new=v["cp_best"], st_old=old[k]["cp_status"], st_new=v["cp_status"]) for k, v in new.items()]
    wcsv(d / "diff.csv", diff)
    s = dict(rows=len(res), recomputed=len(new), long=len(newl), same=sum(x["same"] for x in diff), optimal=sum(v["cp_status"] == "OPTIMAL" for v in new.values()),
             check_fail=sum(str(v["sim_check"]) != "1" for v in new.values()) + sum(str(v["cp_check"]) == "0" for v in new.values()))
    (out / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(s, ensure_ascii=False))
    print(out.name, json.dumps(s, ensure_ascii=False))


# ================================================================ example table and critical lengths (analytic)
def run_ex(a):
    import windport_analytic as A6
    from windport import bound_all as BA
    install()
    out, cfg = out_dir("ex", dict(grid=dict(example=A6.GRIDS["example"], critical=A6.GRIDS["critical"])))
    prepare(out, cfg)
    rows = A6.example()
    g = A6.GRIDS["example"]
    for r in rows:
        c = A6.cfg_e4("A1", r["scen"], r["mode"], r["K"], g["S"], g["L"], g["G"])
        w = BA.parts(c, lift=True)
        v, keys, cls, sub, nat = BA.binding(BA.terms(w, g["L"] * H))
        r.update(w2_lift=v, binding_lift="+".join(keys), cls_lift=cls, eps_u=round(w.get("eps_u", 0.0), 1), dq_lift=round(w["P"].dq, 1),
                 tl_lift=round(w["P"].tl, 1), c_lift=round(w["P"].c, 1), hd_lift=round(w["P"].hd, 1))
    (out / "example").mkdir(exist_ok=True)
    wcsv(out / "example" / "example.csv", rows)
    (out / "critical").mkdir(exist_ok=True)
    wcsv(out / "critical" / "critical.csv", A6.critical())
    BD = base_dirs()
    import windport_report_maingeom as FR
    Df = FR.dirs()
    same = {}
    for name, dd in (("example", Df["example"]), ("critical", Df["critical"])):
        same[name] = (out / name / f"{name}.csv").read_bytes() == (dd / f"{name}.csv").read_bytes()
    (out / "summary.json").write_text(json.dumps(same, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out.name, same)


# ================================================================ invariance checks
def inv_items():
    """All E2 cases with S ≤ 1 (model data); 40 side-by-side keys each of reach / upsize of the spatial additions and 40
    side-by-side rows of the core cases (fixed seed)."""
    import random
    import windport_spatial as TA
    import windport_main2_runs as HX
    R = random.Random(137_115)
    rows, _ = e2_rows()
    out = [("e2", r["key"]) for r in rows if int(r["S"]) <= 1]
    for p in ("reach", "upsize"):
        ks = [k for k in TA.keys(p) if T.dec(k).get("lay") == "side"]
        out += [(f"side:{p}", k) for k in R.sample(ks, min(40, len(ks)))]
    out += [("side:core", k) for k in R.sample(HX.core_keys(), 40)]
    return out


def inv_one(arg):
    """(kind, key) → dict(same=...): for E2, whether the CP-SAT model data (tasks, candidate windows of each trip, W1) are the
    same at 110 / 115 m; for side-by-side, whether the row recomputed at 115 m equals the committed row field by field."""
    import windport_revision_lib as K
    kind, k = arg
    if kind == "e2":
        import pickle
        import windport_e2 as E2
        from windport import cpsat_lift as CPL
        dig = []
        for sp in (110.0, SPACING):
            K.install_spacing(sp)
            inst = CPL.Inst(E2.cfg_of(k))
            st = {x: getattr(inst, x) for x in sorted(vars(inst)) if x not in ("net", "D", "cfg", "p")}
            dig.append(hashlib.sha256(pickle.dumps(repr(st))).hexdigest())
        K.install_spacing(SPACING)
        return dict(kind=kind, key=k, same=int(dig[0] == dig[1]))
    import windport_rerun_spatial as E
    import windport_main2_runs as HX
    import windport_maingeom as F
    if kind == "side:core":
        r = dict(F.port_point(HX.core_cfg(T.dec(k))), **T.dec(k))
        row = F.sim_row("core", k, r)
        base = {T.enc({c: x[c] for c in ("scen", "lay", "arr", "K", "hold", "rule")}): x for x in csv.DictReader(open(_core_dir() / "points.csv", encoding="utf-8"))}
        o = base[k]
    else:
        p = kind.split(":")[1]
        row = E.row_of(k, E.run_point(p, k))
        o = {x["key"]: x for x in csv.DictReader(open(base_dirs()[f"unified:{p}"] / "points.csv", encoding="utf-8"))}[k]
    same = all(str(row.get(c, "")) == str(o[c]) for c in o if c in row and c not in ("map_sha256",))
    return dict(kind=kind, key=k, same=int(same))


def _core_dir():
    import windport_report_main2 as HR
    return HR.h_dirs()["core"]


def init_inv():
    pin(list(range(1, os.cpu_count())))
    install()


def run_inv(a):
    out, cfg = out_dir("inv")
    prepare(out, cfg)
    its = inv_items()
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "115 m spacing re-runs: invariance checks (E2 S ≤ 1, side-by-side sample)", "revision")
    res = []
    for r in slot_imap(inv_one, its, a.procs, initializer=init_inv, slots_dir=a.slots, tag="revision"):
        res.append(r)
        prog.write(done=len(res))
    wcsv(out / "inv.csv", res)
    s = {}
    for r in res:
        x = s.setdefault(r["kind"], dict(n=0, same=0))
        x["n"] += 1
        x["same"] += r["same"]
    (out / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(s, ensure_ascii=False))
    print(out.name, s)


# ================================================================ recheck
def splice_dirs():
    """Completed re-runs: batch → splice directory."""
    out = {}
    for p in sorted((ROOT / "results").glob("windport_revision_r1_*")):
        for d in (p / "splice").glob("*") if (p / "splice").exists() else []:
            b = d.name.replace("_", ":", 1)
            out[b] = d
    return out


def recheck_items():
    """Re-run rows (keys of diff.csv), selected by the rules of windport_recheck_maingeom.items: skip the fixed-duration
    representation, the cut as a single resource, the fixed-duration group of the E1-E3 batches, and the s3 / cf steps of ablate."""
    import windport_recheck_maingeom as FK
    out = []
    for b, d in sorted(splice_dirs().items()):
        if b == "e1e3:e2":
            lng = {r["key"]: r for r in FK.load(d, "e2long/points.csv")}
            keys = {r["key"] for r in FK.load(d, "diff.csv")}
            for r in FK.load(d):
                if r["key"] in keys:
                    out.append((b, "lift", dict(r, **{k: v for k, v in lng.get(r["key"], {}).items() if k.startswith("cp_")})))
            continue
        keys = {r["key"] for r in FK.load(d, "diff.csv")}
        for r in FK.load(d):
            if ident(b, r) not in keys:
                continue
            if b == "extra:fix" or r.get("repr") == "fixed" or r.get("rep") in ("fix", "cut") or r.get("key", "").startswith("fix|"):
                continue
            if b.startswith("unified:") and (r.get("step") in ("s3", "cf") or r.get("rep") == "fix"):
                continue
            out.append((b, "plain" if b == "conservative:sens" and r["var"] == "orig" else "lift", r))
    return out


def rc_chunk(its):
    import windport_recheck_maingeom as FK
    return [FK.one(x) for x in its]


def init_rc():
    import windport_recheck_unified as ER
    import windport_recheck_maingeom as FK
    import windport_recheck_main2 as HK
    pin(list(range(1, os.cpu_count())))
    install()
    ER.cfg_of = HK.cfg_of
    FK.cfg_of = HK.cfg_of


def run_recheck(a):
    import windport_recheck_maingeom as FK
    sd = splice_dirs()
    psha = {b: hashlib.sha256(b"".join((d / n).read_bytes() for n in ("points.csv", "diff.csv") if (d / n).exists())).hexdigest() for b, d in sd.items()}
    out, cfg = out_dir("recheck", dict(splice={b: str(d.relative_to(ROOT / "results")).replace("\\", "/") for b, d in sd.items()}, points_sha256=psha))
    prepare(out, cfg)
    its = recheck_items()
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "115 m spacing re-runs: recheck (W″_lift of the re-run rows)", "revision")
    res = []
    try:
        for rs in slot_imap(rc_chunk, [its[k:k + 100] for k in range(0, len(its), 100)], a.procs, initializer=init_rc, slots_dir=a.slots, tag="revision"):
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res.sort(key=lambda r: (r["batch"], str(r["key"])))
    wcsv(out / "rows.csv", res, FK.COLS)
    over = sum(int(r.get("over") or 0) for r in res)
    lh = sum(int(r.get("lstar_hi") or 0) for r in res if r["form"] == "port")
    note = f"{len(res)} rows; sim / CP-SAT > W″_lift: {over}; L″* > time in port: {lh}"
    prog.write(state="done", note=note)
    print(out.name, note)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, help="x (RR + spatial additions + core + xscan), sens, e2, ex, inv, recheck; comma-separated")
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=6)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    for part in a.part.split(","):
        if part == "x":
            install()
            run_pool("x", X_B, a)
        elif part == "sens":
            install(True)
            run_pool("sens", SENS_B, a, sens_only=True)
        elif part == "e2":
            install()
            run_e2(a)
        elif part == "ex":
            run_ex(a)
        elif part == "inv":
            install()
            run_inv(a)
        elif part == "recheck":
            install()
            run_recheck(a)
        else:
            raise SystemExit(part)


if __name__ == "__main__":
    main()
