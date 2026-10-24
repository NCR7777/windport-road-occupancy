"""Committed simulation batches of the E1-E3 batches, the E4-E7 batches and the extra analyses rerun under the conservative lifting rule
(windport/lift.py).

Each batch uses the unchanged keys, configurations, single-point functions and aggregation functions of the committed experiment
scripts (windport_sim.py, windport_runs.py, windport_extra.py); only inside the worker processes are windport.sim.PortSim,
sim2.ConvoySim and sim3.CutSim replaced by the subclasses of windport/lift.py (lift.install), and windport.check.check by the check of
windport/check_lift.py (all checks of the original checker + the two checks of the new rule). All rows are rerun (cradle-mode rows too,
to verify byte identity).
Also: the "Kassels sequence" of pub (windport_extra.kassels_order, analytic) lifts the third monopile from the vehicle; under the new
rule the time for the vehicle body to leave the road after arrival is added (kassels_lift).
Batches (--batch, comma separated or all): e1e3:e1, e1h, rel, e3; runs:e4, e5, e6, e7, pocket, conv, e2c, sens, sens7; extra:port, fix,
mix6, sens, pub, mixx, sens5.
The cradle mode also keeps the area under the load closed (lift.TU), so cradle rows change too and all rows of all batches are rerun;
sens7 (windport_sens_e7.py) and sens5 (windport_sens_e5.py) are included.
The CP-SAT columns of E2 are in experiments/windport_e2_conservative.py; the random regressions of the E4-E7 batches and the extra analyses
are redone under the new rule by windport_random_conservative.py.
Output results/windport_conservative_<batch>_<config hash>/: config.json, progress.json, points/ (per point, resume cache), points.csv (same
columns as the committed one), diff.csv (per row: byte-identical to the committed row with the same key, cradle / lift from vehicle),
summary.json.
Run: python experiments/windport_rerun_conservative.py --batch all --procs 12 --slots DIR
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

CODE = ["windport/lift.py", "windport/check_lift.py", "windport/sim.py", "windport/sim2.py", "windport/sim3.py", "windport/check.py",
        "windport/check3.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py", "windport/archetypes.py", "windport/shipyard.py",
        "occupancy/sim.py", "occupancy/network.py", "occupancy/params.py", "occupancy/tasks.py", "exact/check.py", "experiments/windport_sim.py",
        "experiments/windport_runs.py", "experiments/windport_extra.py", "experiments/windport_e2.py", "experiments/windport_sens_e7.py",
        "experiments/windport_sens_e5.py", "experiments/windport_rerun_conservative.py"]
SRC = {"e1e3:e1": "runs/e1", "e1e3:e1h": "runs/e1_hold", "e1e3:rel": "runs/release_time",
       "e1e3:e3": "runs/e3", "runs:e4": "runs/e4", "runs:e5": "runs/e5",
       "runs:e6": "runs/e6", "runs:e7": "runs/e7", "runs:pocket": "runs/pocket",
       "runs:conv": "runs/convoy_hold", "runs:e2c": "runs/e2_convoy", "runs:sens": "runs/sens",
       "extra:port": "runs/port_time", "extra:fix": "runs/fixed_time", "extra:mix6": "runs/mixed_e4",
       "extra:sens": "runs/sens_extra", "extra:pub": "runs/public_projects", "extra:mixx": "runs/mixed_release",
       "runs:sens7": "runs/sens_e7", "extra:sens5": "runs/sens_e5"}
CHUNK = {"e1e3:e3": 1, "extra:fix": 1}


def mod(batch):
    src = batch.split(":")[0]
    if batch == "runs:sens7":
        import windport_sens_e7 as M
    elif batch == "extra:sens5":
        import windport_sens_e5 as M
    elif src == "e1e3":
        import windport_sim as M
    elif src == "runs":
        import windport_runs as M
    else:
        import windport_extra as M
    return M


def keys(batch):
    return mod(batch).keys() if batch in ("runs:sens7", "extra:sens5") else mod(batch).keys(batch.split(":")[1])


def fname(batch, key):
    if batch.startswith("e1e3"):
        return mod(batch).fname(key)
    import windport_runs as T
    return T.fname(key)


def compute(batch, key):
    M, part = mod(batch), batch.split(":")[1]
    if batch == "runs:sens7":
        import windport_runs as T
        return T.run_one("e7", key)
    if batch == "extra:sens5":
        return M.run_one(key)
    if batch.startswith("e1e3"):
        if key.startswith("fix|"):
            return M.fix_group(key)
        c, sim, r = M.run_one(M.cfg_of(part, key))
        r["key"] = key
        if key.startswith("port"):
            r["port_h"] = M.port_h(c, sim)
        return r
    return M.run_one(part, key)


def rows(batch, key, r):
    M, part = mod(batch), batch.split(":")[1]
    if batch in ("runs:sens7", "extra:sens5"):
        import windport_runs as T
        if batch == "runs:sens7":
            return [T.row_of("e7", key, r)]
        k, lat = key.rsplit("|lat=", 1)
        return [dict(T.row_of("e5", k, r), key=key, par="latc", val=lat)]
    if batch.startswith("runs"):
        return [M.row_of(part, key, r)]
    return M.rows_of(part, key, r)


def cols(batch):
    M, part = mod(batch), batch.split(":")[1]
    if batch in ("runs:sens7", "extra:sens5"):
        import windport_runs as T
        return T.COLS
    if batch.startswith("e1e3"):
        return M.COLS
    if batch.startswith("runs"):
        return M.COLS
    import windport_runs as T
    return T.COLS if part in ("mix6", "sens") else M.PCOLS[part]


def lift_class(row):
    """"lift": direct-lift or mixed-lifting rows (may change under the new rule); "cradle": cradle-mode and unloading rows (should be
    byte-identical)."""
    arr = row.get("arr") or ""
    if arr:
        return "lift" if arr == "S0" or arr.endswith("m") else "cradle"
    return "lift" if row.get("lift") in ("direct", "mixed") else "cradle"


# ---------------------------------------------------------------- worker processes
_OUT = None


def kassels_lift(c, net, p):
    """windport_extra.kassels_order under the new rule: the third monopile is lifted from the vehicle, and the lift starts no earlier
    than the vehicle body leaving the road after arrival (round trip of the fastest saddle row + leaving time).
    This column is meaningful only for the TO1 row (S = 1 mixed lifting, 1 vehicle set); cradle-mode rows keep the original formula
    (byte-identical to the committed ones)."""
    from windport import lift as LF
    from windport import sim2 as S2
    D = S2.build_map(c["geo"])
    W = D["windport"]
    pr = LF.pair_times(net, p, W["storage"], W["cradles"][:1])
    on = p.get("lift_clear", True) and (c["S"] == 0 or c.get("lift") in ("direct", "mixed"))
    best = min(v["TE"] + v["TL"] + (v["off"] if on else 0.0) for v in pr.values())
    P = p["lift_s"]
    return max(2 * P, best + p["hp_s"]) + P


def init(out):
    global _OUT
    _OUT = Path(out)
    pin(list(range(1, os.cpu_count())))
    from windport import check as C
    from windport import check_lift as CL
    from windport import lift as LF
    import windport_extra as X
    LF.install()
    C.check = CL.check
    X.kassels_order = kassels_lift


def run_chunk(arg):
    batch, ks = arg
    for k in ks:
        f = _OUT / "points" / fname(batch, k)
        if not f.exists():
            write_json(f, compute(batch, k))
    return ks


def config(batch):
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    src = ROOT / "results" / SRC[batch] / "points.csv"
    from windport import lift as LF
    return dict(task="conservative", part="rerun", round=4, batch=batch, semantics=dict(lift_clear=True, lift_under=True, lift_tu=LF.TU, span="head"), src=SRC[batch],
                src_sha256=hashlib.sha256(src.read_bytes()).hexdigest(), code=code)


def compare(batch, out, ks):
    """Compare the new points.csv row by row (by key) with the committed one. Returns the summary dict."""
    new = (out / "points.csv").read_text(encoding="utf-8").splitlines()
    old = (ROOT / "results" / SRC[batch] / "points.csv").read_text(encoding="utf-8").splitlines()
    assert new[0] == old[0], "columns differ"
    rd = lambda lines: {r["key"]: (line, r) for line, r in zip(lines[1:], csv.DictReader(lines))}
    N, O = rd(new), rd(old)
    assert set(N) == set(O), "row keys differ"
    diff = []
    for k, (line, r) in N.items():
        diff.append(dict(key=k, cls=lift_class(r), same=int(line == O[k][0]), check_ok=r.get("check_ok", "")))
    with open(out / "diff.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["key", "cls", "same", "check_ok"])
        w.writeheader()
        w.writerows(diff)
    s = dict(batch=batch, src=SRC[batch], rows=len(diff))
    for c in ("cradle", "lift"):
        d = [x for x in diff if x["cls"] == c]
        s.update({f"{c}_rows": len(d), f"{c}_same": sum(x["same"] for x in d)})
    s["check_fail"] = sum(1 for x in diff if x["check_ok"] in ("0", "False"))
    (out / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return s


def run_batch(batch, a):
    cfg = config(batch)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_conservative_{batch.replace(':', '_')}_{h}"
    (out / "points").mkdir(parents=True, exist_ok=True)
    cf = out / "config.json"
    if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != cfg:
        raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
    cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    ks = keys(batch)
    if not a.aggregate_only:
        todo = [k for k in ks if not (out / "points" / fname(batch, k)).exists()]
        prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, f"rerun under the conservative lifting rule {batch}", "conservative")
        n = CHUNK.get(batch, a.chunk)
        chunks = [(batch, todo[i:i + n]) for i in range(0, len(todo), n)]
        try:
            for ds in slot_imap(run_chunk, chunks, a.procs, initializer=init, initargs=(str(out),), slots_dir=a.slots, tag="conservative"):
                prog.write(done=prog.d["done"] + len(ds))
        except BaseException as e:
            prog.write(state="failed", failed=1, note=repr(e)[:300])
            raise
    rs = [x for k in ks for x in rows(batch, k, json.loads((out / "points" / fname(batch, k)).read_text(encoding="utf-8")))]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols(batch), extrasaction="raise")
        w.writeheader()
        w.writerows(rs)
    s = compare(batch, out, ks)
    if not a.aggregate_only:
        prog.write(state="done", note=json.dumps(s, ensure_ascii=False)[:300])
    print(out)
    print(json.dumps(s, ensure_ascii=False))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=20)
    ap.add_argument("--aggregate-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    for b in (list(SRC) if a.batch == "all" else a.batch.split(",")):
        run_batch(b, a)


if __name__ == "__main__":
    main()
