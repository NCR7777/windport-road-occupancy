"""Rerun of the simulation batches of the spatial additions under the conservative lifting rule (direct lifts, mixed lift-and-carry
and cradle mode all use it; windport/lift.py, t_u = 0.05 p, main rule for the area under the load).

Keys, configurations and grids follow experiments/windport_spatial.py (keys and cfg_of are called unchanged); in each worker process
lift.install() replaces windport.sim.PortSim, sim2.ConvoySim and sim3.CutSim by the conservative versions, and the crane reach,
reserved periods and alternative turns of sim4 stay layered on top. Checking uses windport/check_all.py (check4 + check_lift);
the bound is W″_lift from the unified entry windport/bound_all.py (window-type points also record the five case classes; port-time
points record L″_lift*(n_v) and W″_lift(port time)).
All rows are rerun (cradle-mode rows too); the row-by-row comparison with the committed points.csv of windport_spatial is done in the
summary (experiments/windport_report_unified.py).
--part takes the windport_spatial parts sites, siteport, hphd, reach, upsize, turn, reserve, ablate, cdv, or all (all parts share one
process pool).
Output results/windport_unified_<part>_<config hash>/: config.json, progress.json, points/ (one JSON per point, resume cache),
points.csv (no wall-clock times).
Run: python experiments/windport_rerun_spatial.py --part all --procs 23 --slots DIR
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap, write_json      # noqa: E402
import windport_runs as T                                        # noqa: E402
import windport_spatial as A                                       # noqa: E402

PARTS = ["sites", "siteport", "hphd", "reach", "upsize", "turn", "reserve", "ablate", "cdv"]
CODE = A.CODE + ["windport/lift.py", "windport/check_lift.py", "windport/check_all.py", "windport/bound_dead.py", "windport/bound_lift.py",
                 "windport/bound_all.py", "experiments/windport_rerun_spatial.py"]


def cdv_input():
    """Recheck list of the co-design of the spatial additions (chosen.json of windport_spatial_analytic --part codesign; the directory
    name follows that script's hash, so the file is recorded by its SHA-256)."""
    fs = sorted(ROOT.glob("results/windport_spatial_codesign_*/chosen.json"))
    assert len(fs) == 1, fs
    return fs[0]


def run_point(part, key):
    from windport import bound3 as B3
    from windport import bound_all as BA
    from windport import check_all as CA
    from windport import sim as S
    from windport import sim2 as S2
    from windport import sim3 as S3
    from windport import sim4 as S4
    d = T.dec(key)
    c = dict(A.cfg_of(part, d), w4=False)
    cut = c.get("fixed") and d.get("step") in A.CUT
    if cut:
        S4.setup4(c)
        net, p, sim, r = S3.simulate3(c)
    else:
        net, p, sim, r = S4.simulate4(c)
    rv = None
    if r.get("reserve"):
        rv = dict(res=tuple(r["reserve"]["res"].split("|")), f=r["reserve"]["f"], T=r["reserve"]["T"], H_end=(c["horizon_h"] + 1) * 3600.0)
    D, _, _, _, starts, quay, cal = S4.setup4(c)
    g, y = S2.idle_nodes(D)
    ck = CA.check(net, p, sim.trips, starts, quay, cal, c.get("fixed", False) and not cut, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y,
                  cut=cut, reserve=rv)
    out = dict(key=key, trips=len(sim.trips), check_ok=ck["ok"], check_err=ck["errors"][:2], n_far=ck["n_far"], n_res=ck["n_res"], n_clear=ck["n_clear"],
               n_under=ck["n_under"], map_sha256=net.map_sha256, exits=r.get("exits"))
    if r.get("reserve"):
        out["reserve"] = r["reserve"]
    cb = dict(c, fixed=False)
    w = BA.parts(cb, lift=True)
    f = BA.w2_lift(cb, w)
    G = c["cal"]["crane"][0][0] * 3600.0
    if d.get("what") == "port" or d.get("rep"):
        n = c["n_load"]
        ls = sorted(x["F_vessel"] for x in sim.trips if x["F_vessel"] is not None)
        ph = (ls[n - 1] - G) / 3600.0 if len(ls) >= n else None
        lo, hi = B3.lstar(f, n)
        out.update(port_h=ph, lifts=len(ls), lstar_lo=lo / 3600.0, lstar_hi=hi / 3600.0, w_at_port=None if ph is None else f(ph * 3600.0))
    else:
        L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * 3600.0
        v, keys_, cls, sub, nat = BA.binding(BA.terms(w, L))
        out.update(sim=sum(r["n_vessel"]), w4=v, cls=cls, sub=sub, nature=nat, binding="+".join(keys_))
    return out


_OUT = {}


def init(outs):
    pin(list(range(1, os.cpu_count())))
    from windport import lift as LF
    LF.install()
    _OUT.update({k: Path(v) for k, v in outs.items()})


def run_chunk(arg):
    part, ks = arg
    for k in ks:
        f = _OUT[part] / "points" / T.fname(k)
        if not f.exists():
            write_json(f, run_point(part, k))
    return part, ks


COLS = ["key", "sim", "w4", "cls", "prep_sub", "nature", "binding", "port_h", "lifts", "lstar_lo", "lstar_hi", "w_at_port", "check_ok", "n_far", "n_res",
        "n_clear", "n_under", "reserve_res", "reserve_tl", "trips"]


def row_of(key, r):
    out = A.row_of(key, r)
    for k in ("n_clear", "n_under"):
        out[k] = r[k]
    return out


def config(part):
    from windport import lift as LF
    cfg = dict(A.config(part, cdv_input() if part == "cdv" else None), task="unified", semantics=dict(lift_clear=True, lift_under=True, lift_tu=LF.TU, span="head"))
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg.update(code=code, code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest())
    return cfg


def out_dir(part):
    cfg = config(part)
    return ROOT / "results" / f"windport_unified_{part}_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}", cfg


def all_keys(part):
    cd = json.loads(cdv_input().read_text(encoding="utf-8")) if part == "cdv" else None
    return A.keys(part, cd)


def finish(part, out, ks):
    rows = [row_of(k, json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8"))) for k in ks]
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
    bad = sum(1 for r in rows if not r["check_ok"])
    occ = lambda r: r.get("step") not in A.CUT and r.get("rep") != "fix"
    over = sum(1 for r in rows if r.get("w4") not in (None, "") and occ(r) and r["sim"] > r["w4"])
    nv = lambda r: int(r["n_v"]) if "n_v" in r else json.loads(r["cd"])["n_v"]
    wp = sum(1 for r in rows if r.get("w_at_port") not in (None, "") and occ(r) and r["w_at_port"] < nv(r))
    lb = sum(1 for r in rows if r.get("port_h") not in (None, "") and occ(r) and r["port_h"] < r["lstar_lo"] - 1e-9)
    return f"checker failed {bad} points; above W″_lift {over} points; W″_lift(port time) < n_v {wp} points; port time < L″_lift* {lb} points"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, help="part names of the spatial additions, comma separated, or all")
    ap.add_argument("--procs", type=int, default=23)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    ap.add_argument("--aggregate-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    parts = PARTS if a.part == "all" else a.part.split(",")
    outs, ks, progs, chunks = {}, {}, {}, []
    for part in parts:
        out, cfg = out_dir(part)
        outs[part], ks[part] = out, all_keys(part)
        if a.aggregate_only:
            continue
        (out / "points").mkdir(parents=True, exist_ok=True)
        cf = out / "config.json"
        if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != json.loads(json.dumps(cfg)):
            raise SystemExit(f"{cf} does not match the current configuration, refusing to reuse it")
        cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        todo = [k for k in ks[part] if not (out / "points" / T.fname(k)).exists()]
        progs[part] = Progress(out / "progress.json", len(ks[part]), len(ks[part]) - len(todo), a.procs, f"unified bound: spatial additions {part} rerun under the conservative lifting rule", "unified")
        # shipyard-map points are slow: dispatch them first so cores do not sit idle at the end of the batch
        todo.sort(key=lambda k: (not k.startswith("kind=map") and "map:" not in k, k))
        chunks += [(part, todo[i:i + a.chunk]) for i in range(0, len(todo), a.chunk)]
    chunks.sort(key=lambda x: (not any("map:" in k for k in x[1]),))
    if chunks:
        try:
            for part, ds in slot_imap(run_chunk, chunks, a.procs, initializer=init, initargs=({k: str(v) for k, v in outs.items()},), slots_dir=a.slots,
                                      tag="unified"):
                progs[part].write(done=progs[part].d["done"] + len(ds))
        except BaseException as e:
            for pg in progs.values():
                pg.write(state="failed", failed=1, note=repr(e)[:300])
            raise
    for part in parts:
        note = finish(part, outs[part], ks[part])
        if part in progs:
            progs[part].write(state="done", note=note)
        print(outs[part])
        print(note)


if __name__ == "__main__":
    main()
