"""main2 geometry (windport/main2.py: side-by-side cradles rebuilt from their real placement as rows parallel to the quay line, unloading ramp
in line with the apron): rerun the affected results.
Conservative lifting rule windport/lift.py, t_u = 0.05 p; unified bound W″_lift = bound_all.w2_lift. Every worker calls lift.install() and
main2.use(); side-by-side configurations (kind = "A1side") are all replaced by the rebuilt rows (kind = "A1rows") via main2.rows_cfg. Figures
with real maps are not drawn; only data are written.

Reuse (no recomputation): main2 changes only (a) the map of the side-by-side cradles and (b) the coordinates of one node, the ramp top ramp_V at
the east end of A1 and A2. Hence the main-geometry points that are neither side-by-side nor have unloading tasks have the same network as in the
main geometry (the loading, return and departure legs do not pass the ramp; tests/test_windport_main2.py), and the code-file SHA-256 entries equal
those in the main-geometry config.json; these points are reused unchanged. --part sample also recomputes a sample of the reused points under main2
and compares them byte by byte with the main-geometry rows.

--part (comma-separated; the simulation parts of one call share one process pool):
  geom      geometry check (windport/geomcheck.py): A1, A2, A3 × base / long single lane × cradle mode × S = 1, 3 (loading, return, unloading,
            ramp foot); rebuilt side-by-side rows × scenario × Q_h = 0, 1 (S = 6, all rows); E7 monopile lengths for tandem (main-geometry
            dimensions unchanged) and side-by-side (row dimensions follow L_v, B); distance of each side-by-side row from the quay line, and S_r.
  splice    main-geometry points whose map or network changed: points with unloading tasks in the rerun batches (the E1-E3 batches to the extra
            analyses; the A1, A2 ramp changed; the A3 map differs only in the geometry record and is recomputed as a control), and the
            side-by-side points of the spatial-additions batches reach / upsize. They are recomputed under main2, the other rows are taken
            unchanged from the main-geometry points.csv and spliced into a new points.csv (columns and row order as in the main geometry);
            diff.csv compares row by row.
  core      side-by-side rows of the core case (long single lane / long corridor at 1 km/h × S0, S1, S1m, S3, S3m × K = 1-8 × Q_h = 0, 1,
            unlimited, FCFS; Q_h = 0 also with convoy dispatch). Tandem rows are taken from the main-geometry core (170 m).
  reachdist side-by-side with crane reach by distance: side-by-side keys of the reach batch × (S_r, t_sh) = (1, 1 h), (2, 1 h) (points with
            S > S_r; S ≤ S_r equals full reach).
  codesign  integer enumeration of the codesign (as in the main geometry): side-by-side configurations recompute L* under main2 (W″_lift and
            W′), other configurations take the main-geometry values; ranked by both orderings, union of the recheck sets.
  cdv       simulate each configuration of the codesign recheck set: non-side-by-side configurations that are also in the main-geometry recheck
            set take the main-geometry points, the rest are computed. Run codesign first.
  sample    sample check of the reused points: drawn with a seed from each reused main-geometry batch, recomputed under main2, compared byte by
            byte with the main-geometry rows.
Output results/windport_main2_<part>_<config hash>/: config.json (code SHA-256, geometry), progress.json, points/ (per point, resume cache),
points.csv etc.
Run: python experiments/windport_main2_runs.py --part splice,core,reachdist,sample --procs 20 --slots DIR
"""
import argparse
import csv
import hashlib
import itertools
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap, write_json      # noqa: E402
import windport_runs as T                                        # noqa: E402
import windport_maingeom as F                                       # noqa: E402

H = 3600.0
GEO = "main2"
CODE = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "windport").glob("*.py") if p.name not in ("port_survey.py", "geomcheck.py")) + \
    [x for x in F.CODE if not x.startswith("windport/")] + ["experiments/windport_main2_runs.py"]
RERUN = ["e1e3:e1", "runs:e5", "runs:pocket", "runs:sens", "extra:sens5", "extra:pub"]      # rerun batches with unloading tasks (all other batches: 0)
SPATIAL = ["reach", "upsize"]                                                                    # spatial-additions batches with side-by-side points
CORE = dict(scen=["lane", "longslow"], arr=["S0", "S1", "S1m", "S3", "S3m"], K=list(range(1, 9)), hold=["0", "1", "inf"], convoy_hold=["0"], n_v=10)
REACHD = {"1_3600": (1, 3600.0), "2_3600": (2, 3600.0)}
SAMPLE = dict(seed=137_008, per_batch=12)
SIMS = ["splice", "core", "reachdist", "cdv", "sample"]


def code_hash():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}


def out_dir(name, extra=None):
    from windport import main2 as M2
    cfg = dict(task="main2", part=name, geometry=M2.MAIN2, code=code_hash(), **(extra or {}))
    return ROOT / "results" / f"windport_main2_{name.replace(':', '_')}_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}", cfg


prepare, wcsv = F.prepare, F.wcsv


def f_dirs():
    """Run directories of the main geometry (batch → directory)."""
    import windport_recheck_maingeom as FK
    return FK.dirs()


# ================================================================ configuration and classification of one point
def rerun_cfgs(batch, key):
    """Configurations of one key of a rerun batch (a list; the fixed-time group of the E1-E3 batches and the non-pub parts of the extra
    analyses have no unloading tasks and return [])."""
    import windport_rerun_conservative as RR
    M, part = RR.mod(batch), batch.split(":")[1]
    if batch == "extra:sens5":
        return [T.cfg_of("e5", key.rsplit("|lat=", 1)[0])]
    if batch == "extra:pub":
        return [dict(n_unload=1)] if T.dec(key)["pub"] != "out" else []
    if batch.startswith("e1e3") and key.startswith("fix|"):
        return []
    c = M.cfg_of(part, key)
    return c if isinstance(c, list) else [c]


def changed(batch, key):
    """Whether the map or network of this key changes under main2: it has unloading tasks (ramp) or is side-by-side."""
    if batch.startswith("unified:"):
        return T.dec(key).get("lay") == "side"
    return any(x.get("n_unload") for x in rerun_cfgs(batch, key))


def core_keys():
    g, out = CORE, []
    for sc, arr, K, h in itertools.product(g["scen"], g["arr"], g["K"], g["hold"]):
        out.append(T.enc(dict(scen=sc, lay="side", arr=arr, K=K, hold=h, rule="fcfs")))
    for sc, arr, K, h in itertools.product(g["scen"], g["arr"], g["K"], g["convoy_hold"]):
        out.append(T.enc(dict(scen=sc, lay="side", arr=arr, K=K, hold=h, rule="convoy")))
    return out


def core_cfg(d):
    from windport import main2 as M2
    c = M2.rows_cfg(F.core_cfg(dict(d, first=170.0, extra=0.0)))
    c["rule"] = d.get("rule", "fcfs")
    return c


def reachdist_keys():
    import windport_spatial as TA
    g = TA.GRIDS["reach"]
    out = []
    for rc, (Sr, _) in REACHD.items():
        for sc, K, Sn, lf in itertools.product(g["scen"], g["K"], g["side"]["S"], g["lift"]):
            if Sn > Sr:
                out.append(T.enc(dict(lay="side", kind="A1side", scen=sc, mode="side", lift=lf, rule="fcfs", reach=rc, L=g["L"], K=K, S=Sn, G=g["G"])))
    return out


def sample_keys():
    """Sample of the reused batches: from every main-geometry batch (all rerun batches and the four spatial-additions batches, E2 excluded)
    draw per_batch unchanged keys with the seed."""
    import windport_rerun_conservative as RR
    import windport_spatial as TA
    R = random.Random(SAMPLE["seed"])
    out = []
    for b in F.rerun_batches():
        ks = [k for k in RR.keys(b) if b not in RERUN or not changed(b, k)]
        out += [json.dumps([b, k]) for k in R.sample(ks, min(SAMPLE["per_batch"], len(ks)))]
    for p in F.SPATIAL:
        ks = [k for k in TA.keys(p) if not changed(f"unified:{p}", k)]
        out += [json.dumps([f"unified:{p}", k]) for k in R.sample(ks, SAMPLE["per_batch"])]
    return out


# ================================================================ worker processes
_OUTS = {}


def install():
    """Shared by the workers and the main process: conservative lifting rule, main2, side-by-side replaced by the rebuilt rows, and the
    checker and Kassels order of the conservative lifting rule."""
    import windport_extra as X
    import windport_spatial as TA
    import windport_rerun_conservative as RR
    from windport import check as C
    from windport import check_lift as CL
    from windport import lift as LF
    from windport import main2 as M2
    LF.install()
    C.check = CL.check
    X.kassels_order = RR.kassels_lift
    M2.use()
    if not getattr(TA.cfg_of, "_main2", False):
        orig = TA.cfg_of

        def cfg_of(part, d):
            return M2.rows_cfg(orig(part, d))
        cfg_of._main2 = True
        TA.cfg_of = cfg_of


def init(outs):
    pin(list(range(1, os.cpu_count())))
    install()
    _OUTS.update({k: Path(v) for k, v in outs.items()})


def compute(part, key):
    import windport_rerun_conservative as RR
    import windport_rerun_spatial as E
    if part == "core":
        d = T.dec(key)
        return dict(F.port_point(core_cfg(d)), **d)
    if part == "reachdist":
        return E.run_point("reach", key)
    if part == "cdv":
        return E.run_point("cdv", key)
    b, k = json.loads(key)
    if b.startswith("unified:"):
        return E.run_point(b.split(":")[1], k)
    return RR.compute(b, k)


def fname(key):
    return hashlib.sha256(key.encode()).hexdigest()[:24] + ".json"


def chunk(arg):
    part, ks = arg
    for k in ks:
        f = _OUTS[part] / "points" / fname(k)
        if not f.exists():
            write_json(f, compute(part, k))
    return part, ks


def rows_of(batch, key, r):
    import windport_rerun_conservative as RR
    import windport_rerun_spatial as E
    if batch.startswith("unified:"):
        return [E.row_of(key, r)]
    return RR.rows(batch, key, r)


def row_line(cols, row):
    """One row as csv text (as csv.DictWriter writes it), for byte-by-byte comparison with the main-geometry rows."""
    import io
    s = io.StringIO()
    w = csv.DictWriter(s, cols, extrasaction="ignore")
    w.writerow(row)
    return s.getvalue().rstrip("\r\n")


# ================================================================ keys and finishing of each part
def part_keys(part, chosen=None):
    import windport_rerun_conservative as RR
    import windport_spatial as TA
    if part == "splice":
        out = []
        for b in RERUN:
            out += [json.dumps([b, k]) for k in RR.keys(b) if changed(b, k)]
        for p in SPATIAL:
            out += [json.dumps([f"unified:{p}", k]) for k in TA.keys(p) if changed(f"unified:{p}", k)]
        return out
    if part == "core":
        return core_keys()
    if part == "reachdist":
        return reachdist_keys()
    if part == "sample":
        return sample_keys()
    if part == "cdv":
        return cdv_todo(chosen)[0]
    raise KeyError(part)


def finish_splice(out, ks):
    """Per batch: the main-geometry points.csv with the changed keys replaced by the main2 rows; writes <batch>/points.csv, diff.csv,
    summary.json."""
    FD = f_dirs()
    pts = {}
    for k in ks:
        b, kk = json.loads(k)
        pts.setdefault(b, {})[kk] = json.loads((out / "points" / fname(k)).read_text(encoding="utf-8"))
    summ = {}
    for b in RERUN + [f"unified:{p}" for p in SPATIAL]:
        src = FD[b] / "points.csv"
        lines = src.read_text(encoding="utf-8").splitlines()
        cols = lines[0].split(",")
        old = list(csv.DictReader(lines))
        new_rows = {}
        for kk, r in pts.get(b, {}).items():
            for row in rows_of(b, kk, r):
                new_rows[row["key"]] = row
        d = out / b.replace(":", "_")
        d.mkdir(exist_ok=True)
        res, diff = [], []
        for line, r in zip(lines[1:], old):
            if r["key"] in new_rows:
                nl = row_line(cols, new_rows[r["key"]])
                res.append(nl)
                diff.append(dict(key=r["key"], same=int(nl == line), check_ok=new_rows[r["key"]].get("check_ok", "")))
            else:
                res.append(line)
        assert len(diff) == len(new_rows), (b, len(diff), len(new_rows))
        (d / "points.csv").write_bytes(("\r\n".join([lines[0]] + res) + "\r\n").encode("utf-8"))     # line endings as csv.DictWriter
        wcsv(d / "diff.csv", diff, ["key", "same", "check_ok"])
        s = dict(batch=b, maingeom=FD[b].name, rows=len(old), recomputed=len(diff), same=sum(x["same"] for x in diff),
                 check_fail=sum(1 for x in diff if str(x["check_ok"]) in ("0", "False")))
        (d / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        summ[b] = s
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return summ


def finish_sample(out, ks):
    FD = f_dirs()
    res = []
    for k in ks:
        b, kk = json.loads(k)
        r = json.loads((out / "points" / fname(k)).read_text(encoding="utf-8"))
        lines = (FD[b] / "points.csv").read_text(encoding="utf-8").splitlines()
        cols = lines[0].split(",")
        old = {row["key"]: line for line, row in zip(lines[1:], csv.DictReader(lines))}
        for row in rows_of(b, kk, r):
            res.append(dict(batch=b, key=row["key"], same=int(row_line(cols, row) == old[row["key"]])))
    wcsv(out / "sample.csv", res, ["batch", "key", "same"])
    s = dict(rows=len(res), same=sum(x["same"] for x in res), batches=len({x["batch"] for x in res}))
    (out / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return s


def finish_plain(part, out, ks):
    import windport_rerun_spatial as E
    rows = []
    for k in ks:
        r = json.loads((out / "points" / fname(k)).read_text(encoding="utf-8"))
        if part == "core":
            rows.append(F.sim_row("core", k, r))
        else:
            rows.append(E.row_of(k, r))
    wcsv(out / "points.csv", rows)
    bad = sum(1 for r in rows if str(r.get("check_ok")) in ("0", "False"))
    return dict(rows=len(rows), check_fail=bad)


def run_sims(parts, a):
    outs, progs, chunks, ks = {}, {}, [], {}
    chosen = None
    for part in parts:
        extra = {}
        if part == "core":
            extra = dict(grid=CORE)
        elif part == "reachdist":
            extra = dict(reach=REACHD)
        elif part == "sample":
            extra = dict(sample=SAMPLE)
        elif part == "splice":
            extra = dict(rerun=RERUN, spatial=SPATIAL)
        elif part == "cdv":
            chosen = json.loads(chosen_file().read_text(encoding="utf-8"))
            extra = dict(chosen_sha256=hashlib.sha256(chosen_file().read_bytes()).hexdigest())
        outs[part] = out_dir(part, extra)
    for part, (out, cfg) in outs.items():
        prepare(out, cfg)
        ks[part] = part_keys(part, chosen)
        todo = [k for k in ks[part] if not (out / "points" / fname(k)).exists()]
        progs[part] = Progress(out / "progress.json", len(ks[part]), len(ks[part]) - len(todo), a.procs, f"main2 geometry {part}", "main2")
        chunks += [(part, todo[i:i + a.chunk]) for i in range(0, len(todo), a.chunk)]
    chunks.sort(key=lambda x: x[0] != "splice")
    try:
        for part, ds in slot_imap(chunk, chunks, a.procs, initializer=init, initargs=({k: str(v[0]) for k, v in outs.items()},), slots_dir=a.slots,
                                  tag="main2"):
            progs[part].write(done=progs[part].d["done"] + len(ds))
    except BaseException as e:
        for pg in progs.values():
            pg.write(state="failed", note=repr(e)[:300])
        raise
    install()
    for part, (out, _) in outs.items():
        if part == "splice":
            s = finish_splice(out, ks[part])
        elif part == "sample":
            s = finish_sample(out, ks[part])
        elif part == "cdv":
            s = finish_cdv(out, chosen)
        else:
            s = finish_plain(part, out, ks[part])
        progs[part].write(state="done", note=json.dumps(s, ensure_ascii=False)[:300])
        print(out.name, json.dumps(s, ensure_ascii=False)[:600])


# ================================================================ codesign, cdv
def codesign_dir():
    import windport_spatial_analytic as AA
    return out_dir("codesign", dict(grid=AA.GRIDS["codesign"]))


def chosen_file():
    out, _ = codesign_dir()
    f = out / "chosen.json"
    assert f.exists(), "run --part codesign first"
    return f


def cd_point(i):
    import windport_spatial_analytic as AA
    from windport import bound3 as B3
    from windport import bound4 as B4
    from windport import bound_all as BA
    from windport import main2 as M2
    c = M2.rows_cfg(F.cd_cfg(F.cd_items()[i]))
    f, f0 = BA.w2_lift(c, BA.parts(c, lift=True)), B4.wprime4_fn(c)
    return [dict(i=i, n_v=n, lstar_h=round(B3.lstar(f, n)[1] / H, 4), lstar_wprime_h=round(B3.lstar(f0, n)[1] / H, 4)) for n in AA.GRIDS["codesign"]["n_v"]]


def cd_chunk(ix):
    return [r for i in ix for r in cd_point(i)]


def init_cd():
    pin(list(range(1, os.cpu_count())))
    install()


def run_codesign(a):
    """Side-by-side configurations are computed; the others take the per-point values of the main-geometry codesign (same configurations,
    same index); ordering and recheck set as in the main geometry (windport_maingeom.rank)."""
    import windport_spatial_analytic as AA
    g = AA.GRIDS["codesign"]
    out, cfg = codesign_dir()
    prepare(out, cfg)
    items = F.cd_items()
    side = [i for i, x in enumerate(items) if x["geo"]["kind"] == "A1side"]
    cfg_s = lambda x, n: json.dumps(dict(geo=x["geo"], p=x["p"], S=x["S"], K=x["K"], lift=x["lift"], hold=x["hold"], n_v=n), sort_keys=True)
    fr = {r["cfg"]: r for r in csv.DictReader(open(ROOT / "results" / one_codesign_f() / "codesign.csv", encoding="utf-8"))}
    old = {i: [dict(i=i, n_v=n, lstar_h=float(fr[cfg_s(x, n)]["lstar_h"]), lstar_wprime_h=float(fr[cfg_s(x, n)]["lstar_wprime_h"])) for n in g["n_v"]]
           for i, x in enumerate(items) if x["geo"]["kind"] != "A1side"}
    done = {}
    for f in (out / "points").glob("*.json"):
        for r in json.loads(f.read_text(encoding="utf-8")):
            done.setdefault(r["i"], []).append(r)
    todo = [i for i in side if i not in done]
    prog = Progress(out / "progress.json", len(side), len(side) - len(todo), a.procs, "codesign enumeration: side-by-side configurations (W″_lift and W′)", "main2")
    for rs in slot_imap(cd_chunk, [todo[k:k + 4] for k in range(0, len(todo), 4)], a.procs, initializer=init_cd, slots_dir=a.slots, tag="main2"):
        write_json(out / "points" / f"{rs[0]['i']}.json", rs)
        for r in rs:
            done.setdefault(r["i"], []).append(r)
        prog.write(done=sum(1 for i in side if i in done))
    rows = []
    for i, x in enumerate(items):
        src = done if i in done else old
        for r in src[i]:
            n = r["n_v"]
            rows.append(dict({k: v for k, v in x.items() if k not in ("geo", "p")}, n_v=n, lstar_h=r["lstar_h"], lstar_wprime_h=r["lstar_wprime_h"],
                             cfg=cfg_s(x, n), recomputed=int(i in done)))
    rw = [dict(r) for r in rows]
    best, chosen = F.rank(rows, "lstar_h", g)
    best0, chosen0 = F.rank(rw, "lstar_wprime_h", g)
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
    note = f"{len(items)} configurations ({len(side)} side-by-side recomputed); recheck set W″_lift {len(chosen)}, W′ {len(chosen0)}, union {len(allc)}; {len(newtop)} new entries in the W″_lift top 3"
    prog.write(state="done", note=note)
    print(out.name, note)


def one_codesign_f():
    import windport_recheck_maingeom as FK
    return FK.one_dir("windport_maingeom_codesign_").name


def cdv_todo(chosen):
    """Keys of the recheck set to compute (side-by-side configurations, or not in the main-geometry recheck set) and keys that take the
    main-geometry points."""
    import windport_spatial as TA
    ks = TA.keys("cdv", chosen)
    fk = {r["key"] for r in csv.DictReader(open(f_dirs()["unified:cdv"] / "points.csv", encoding="utf-8"))}
    new = [k for k in ks if k not in fk or json.loads(T.dec(k)["cd"])["geo"]["kind"] == "A1side"]
    return new, [k for k in ks if k not in new]


def finish_cdv(out, chosen):
    import windport_spatial as TA
    import windport_rerun_spatial as E
    ks = TA.keys("cdv", chosen)
    new, old = cdv_todo(chosen)
    fr = {r["key"]: r for r in csv.DictReader(open(f_dirs()["unified:cdv"] / "points.csv", encoding="utf-8"))}
    rows = [E.row_of(k, json.loads((out / "points" / fname(k)).read_text(encoding="utf-8"))) if k in new else dict(fr[k]) for k in ks]
    wcsv(out / "points.csv", rows, list(csv.DictReader(open(f_dirs()["unified:cdv"] / "points.csv", encoding="utf-8")).fieldnames))
    return dict(rows=len(rows), recomputed=len(new), reused=len(old), check_fail=sum(1 for r in rows if str(r.get("check_ok")) in ("0", "False")))


# ================================================================ geom
def run_geom():
    import windport_extra as X
    import windport_spatial as TA
    from windport import archetypes as A
    from windport import geomcheck as GC
    from windport import main2 as M2
    from windport import sim4 as S4
    out, cfg = out_dir("geom")
    cfg["geomcheck_sha256"] = hashlib.sha256((ROOT / "windport/geomcheck.py").read_bytes()).hexdigest()
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    rows, sums = [], []

    def put(tag, c):
        r = GC.check(c)
        rows.extend(dict(tag, **x) for x in r["rows"])
        sums.append(dict(tag, ok=r["ok"], ok_unload=r["ok_unload"], piles_on_land=r["piles_on_land"],
                         **{f"min_{k}": v for k, v in (r["min_clear"] or {}).items()}, **{f"unl_{k}": v for k, v in (r["min_unload"] or {}).items()},
                         assumed=json.dumps(r["assumed"], ensure_ascii=False)))
    for kind, sc, m, arr in itertools.product(A.KINDS, ("base", "lane"), T.MODES, ("S1", "S3")):
        c = X.port_cfg(sc, m, arr, 2, 10, 0)
        c["geo"] = dict(c["geo"], kind=kind)
        put(dict(layout="tandem", kind=kind, scen=sc, mode=m, arr=arr, hold="0", lv="110"), c)
    for sc, h in itertools.product(("base", "lane"), ("0", "1")):
        c = X.port_cfg(sc, "on_road", "S1", 2, 10, int(h))
        c["geo"], c["S"] = TA.side_geo(sc), 6
        put(dict(layout="rows", kind="A1rows", scen=sc, mode="side", arr="S6", hold=h, lv="110"), M2.rows_cfg(c))
    for lv in T.E7LEV:
        pv = {k: v for k, v in T.E7LEV[lv].items() if k != "t"}
        c = X.port_cfg("base", "on_road", "S1", 2, 10, 0)
        c["p"] = dict(c["p"], **pv)
        put(dict(layout="tandem", kind="A1", scen="base", mode="on_road", arr="S1", hold="0", lv=lv), c)
        c = X.port_cfg("base", "on_road", "S1", 2, 10, 0)
        c["p"], c["geo"], c["S"] = dict(c["p"], **pv), TA.side_geo("base"), 6
        put(dict(layout="rows", kind="A1rows", scen="base", mode="side", arr="S6", hold="0", lv=lv), M2.rows_cfg(c))
    wcsv(out / "turns.csv", rows)
    wcsv(out / "summary.csv", sums)
    # distance of each side-by-side row from the quay line (pile centre line to quay line); S_r(R_q) = number of rows within R_q of the quay line
    reach = []
    for lv in ["base"] + list(T.E7LEV):                    # base: base parameters (L_v 110 m, B 9.5 m); the others are the E7 monopile levels
        c = X.port_cfg("base", "on_road", "S1", 2, 10, 0)
        c["p"] = dict(c["p"], **{k: v for k, v in T.E7LEV.get(lv, {}).items() if k != "t"})
        c["geo"], c["S"] = TA.side_geo("base"), 6
        c = M2.rows_cfg(c)
        D, _, p, *_ = S4.setup4(c)
        W = D["windport"]
        d0 = GC.row_d0(D, p)
        for k, y in enumerate(W["row_y"]):
            reach.append(dict(lv=lv, Lv=p["Lv"], B=p["B"], k=k, row_y=round(y, 2), dist_m=round(W["row_y"][0] - y + d0, 2), pitch_m=W["params"]["pitch_m"],
                              x0_m=W["params"]["x0_m"], head_m=W["params"]["head_m"], quay_edge_m=round(GC.quay_edge(D, p), 2)))
    wcsv(out / "rows_reach.csv", reach)
    print(out.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True)
    ap.add_argument("--procs", type=int, default=20)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    install()
    parts = a.part.split(",")
    if "geom" in parts:
        run_geom()
    if "codesign" in parts:
        run_codesign(a)
    sims = [p for p in parts if p in SIMS]
    if sims:
        run_sims(sims, a)


if __name__ == "__main__":
    main()
