"""Recheck of the submitted results and of the windport_extra batches with the corrected W′ (return-trip occupancy correction in
windport/bound3.py): only the bound columns are recomputed; simulated counts are taken from the points.csv / cases.csv of each run
directory (no re-simulation).

For each row: rebuild the configuration from the key, compute W′ before the correction (original return-trip occupancy; must equal
the recorded w1g, otherwise counted as mismatch) and after it; record whether the simulated count exceeds or equals the corrected
W′. Port-time batches (port, pub) also get L*(n_v) before and after the correction.
Batches: e4, e5, e6, e7, pocket, conv, e2c, sens, sens7, random (cases.csv) of the earlier runs; mix6, sens, sens5, port, pub of the
windport_extra batches.
Output results/windport_extra_recheck_<config hash>/: config.json, progress.json, summary.csv (per batch), changed.csv (rows where
W′ or L* changed), e2.csv (Table 2: cases with proven optimum = W′, before / after), e6.csv (Table 4: share of points attaining W′,
before / after), summary.md.
Run: .venv/Scripts/python.exe experiments/windport_recheck.py --procs 22 --slots DIR
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402

CODE = ["windport/sim.py", "windport/sim2.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py", "windport/archetypes.py",
        "windport/shipyard.py", "occupancy/network.py", "occupancy/params.py", "experiments/windport_runs.py", "experiments/windport_random.py",
        "experiments/windport_e2.py", "experiments/windport_extra.py", "experiments/windport_recheck.py"]
RUNS = dict(e4="runs/e4", e5="runs/e5", e6="runs/e6",
            e7="runs/e7", pocket="runs/pocket", conv="runs/convoy_hold",
            e2c="runs/e2_convoy", sens="runs/sens", sens7="runs/sens_e7",
            random="runs/random_bound")
EXTRA = dict(mix6="runs/mixed_e4", sens="runs/sens_extra", sens5="runs/sens_e5",
            port="runs/port_time", pub="runs/public_projects")
E2 = dict(e2="runs/e2", e2long="runs/e2_long")
_CACHE = {}


def cfg_of(batch, row):
    import windport_runs as T
    import windport_extra as X
    src, part = batch.split(":")
    k = row.get("key")
    if src == "runs":
        if part == "random":
            import windport_random as R
            return R.make(int(row["i"]))
        return T.cfg_of("e7" if part == "sens7" else part, k)
    if part == "mix6":
        return T.cfg_of("e4", k)
    if part == "sens":
        d = T.dec(k)
        c = T.cfg_of("sens", T.enc(dict(d, par="none", val=0)))
        c["p"] = dict(c["p"], **{X.SENS3[d["par"]][0]: float(d["val"])})
        return c
    if part == "sens5":
        kk, lat = k.rsplit("|lat=", 1)
        c = T.cfg_of("e5", kk)
        c["p"] = dict(c["p"], lat_clear=float(lat))
        return c
    d = T.dec(k)
    if part == "port":
        return X.port_cfg(d["scen"], d["mode"], d["arr"], int(d["K"]), int(d["n_v"]), X.hold_v(d["hold"]), "convoy" if d["rep"] == "convoy" else "fcfs")
    g = X.GRIDS["pub"]
    return X.port_cfg("base", d["mode"], d["arr"], int(d["K"]), g["n_out"], 0, geo_extra=g["out_geo"][d["geo"]], G=g["G_out"])


def parts(c):
    """windport.bound3.wprime_parts cached by (geometry, parameters, S, K, lifting, Q_h, unloading or not); G is taken per row."""
    from windport import bound3 as B3
    key = json.dumps({k: v for k, v in c.items() if k not in ("cal", "horizon_h", "n_load", "rule", "record", "unload_release_h")}, sort_keys=True,
                     default=str)
    if key not in _CACHE:
        _CACHE[key] = B3.wprime_parts(c)
    return dict(_CACHE[key], G=c["cal"]["crane"][0][0] * 3600.0)


def one(arg):
    batch, row = arg
    from windport import bound3 as B3
    c = cfg_of(batch, row)
    w = parts(c)
    w0 = dict(w, P=replace(w["P"], te=w["te0"], te_occ=w["te_occ0"]))
    f, f0 = B3.wprime_fn(c, w), B3.wprime_fn(c, w0)
    out = dict(batch=batch, key=row.get("key") or row.get("i"), corr=int(w["P"].te_occ < w["te_occ0"] - 1e-9 or w["P"].te < w["te0"] - 1e-9))
    if batch.endswith(("port", "pub")):
        n = int(row.get("n_v") or 3)
        ph = float(row["port_h"]) * 3600.0
        lo0, _ = B3.lstar(f0, n)
        lo1, _ = B3.lstar(f, n)
        out.update(sim=n, old=f0(ph), new=f(ph), stored=None, lstar0=round(lo0 / 3600.0, 6), lstar1=round(lo1 / 3600.0, 6),
                   stored_lstar=row.get("lstar_lo"), port_h=row["port_h"])
        return out
    L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * 3600.0
    sim = int(row["n"] if batch == "runs:random" else row["sim"])
    out.update(sim=sim, old=f0(L), new=f(L), stored=int(float(row["w1g"])) if row.get("w1g") not in (None, "") else None)
    return out


def chunk(items):
    return [one(x) for x in items]


def init():
    pin(list(range(1, os.cpu_count())))


def load(d, name="points.csv"):
    return list(csv.DictReader(open(ROOT / "results" / d / name, encoding="utf-8")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=22)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--extra-dirs", default=None, help="run directories of the windport_extra batches: mix6=…,sens=…,sens5=…,port=…,pub=…")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    dirs = dict(EXTRA, **dict(x.split("=") for x in a.extra_dirs.split(","))) if a.extra_dirs else EXTRA
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="extra", part="recheck", runs=RUNS, extra=dirs, e2=E2, code=code)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_extra_recheck_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    items = []
    for part, d in RUNS.items():
        rows = load(d, "cases.csv") if part == "random" else load(d)
        items += [(f"runs:{part}", r) for r in rows if (part != "random" or r.get("w1g")) and r.get("rep") != "fix"]     # W′ does not apply to the fixed-duration representation
    for part, d in dirs.items():
        rows = load(d)
        if part == "port":
            rows = [r for r in rows if r["rep"] in ("fcfs", "convoy")]
        if part == "pub":
            rows = [r for r in rows if r["pub"] == "out"]
        items += [(f"extra:{part}", r) for r in rows]
    items.sort(key=lambda x: json.dumps(cfg_key(x), sort_keys=True))        # keep rows of the same configuration together (cache hits)
    chunks = [items[k:k + 200] for k in range(0, len(items), 200)]
    prog = Progress(out / "progress.json", len(items), 0, a.procs, "Recheck of submitted results with the corrected W′", "extra")
    res = []
    for rs in slot_imap(chunk, chunks, a.procs, initializer=init, slots_dir=a.slots, tag="extra"):
        res += rs
        prog.write(done=len(res))
    res.sort(key=lambda r: (r["batch"], str(r["key"])))
    by = collections.defaultdict(list)
    for r in res:
        by[r["batch"]].append(r)
    summ = []
    for b, rs in sorted(by.items()):
        port = b.endswith(("port", "pub"))
        summ.append(dict(batch=b, rows=len(rs), corrected=sum(r["corr"] for r in rs), changed=sum(r["new"] != r["old"] for r in rs),
                         sum_old=sum(r["old"] for r in rs), sum_new=sum(r["new"] for r in rs),
                         mismatch=0 if port else sum(1 for r in rs if r["stored"] is not None and r["stored"] != r["old"]),
                         over_old=sum(1 for r in rs if r["sim"] > r["old"]), over_new=sum(1 for r in rs if r["sim"] > r["new"]),
                         tie_old=sum(1 for r in rs if r["sim"] == r["old"]), tie_new=sum(1 for r in rs if r["sim"] == r["new"]),
                         lstar_changed=sum(1 for r in rs if port and r["lstar0"] != r["lstar1"]) if port else ""))
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(summ[0]))
        w.writeheader()
        w.writerows(summ)
    ch = [r for r in res if r["new"] != r["old"] or r.get("lstar0") != r.get("lstar1")]
    cols = ["batch", "key", "sim", "stored", "old", "new", "corr", "lstar0", "lstar1", "stored_lstar", "port_h"]
    with open(out / "changed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(ch)
    # Table 2 (the 540 small E2 cases): cases whose proven optimum equals W′
    e2, lng = load(E2["e2"]), {r["key"]: r for r in load(E2["e2long"])}
    new2 = {r["key"].split("=", 1)[1].replace("/", "|"): r for r in by["runs:e2c"]}
    e2rows = []
    for r in e2:
        if r["key"] in lng:
            r = dict(r, cp_best=lng[r["key"]]["cp_best"], cp_status=lng[r["key"]]["cp_status"])
        x = new2[r["key"]]
        e2rows.append(dict(key=r["key"], status=r["cp_status"], cp=int(r["cp_best"]), old=x["old"], new=x["new"]))
    opt = [r for r in e2rows if r["status"] == "OPTIMAL"]
    with open(out / "e2.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["proven", "eq_old", "eq_new", "cp_over_new", "sum_gap_old", "sum_gap_new"])
        w.writeheader()
        e2s = dict(proven=len(opt), eq_old=sum(r["cp"] == r["old"] for r in opt), eq_new=sum(r["cp"] == r["new"] for r in opt),
                   cp_over_new=sum(r["cp"] > r["new"] for r in e2rows), sum_gap_old=sum(r["old"] - r["cp"] for r in opt),
                   sum_gap_new=sum(r["new"] - r["cp"] for r in opt))
        w.writerow(e2s)
    # Table 4 (E6): share of points attaining W′ (FCFS)
    e6 = {r["key"]: r for r in load(RUNS["e6"])}
    g6 = collections.defaultdict(list)
    for r in by["runs:e6"]:
        x = e6[r["key"]]
        if x["rule"] == "fcfs":
            g6[(x["kind"][4:], x["scen"], x["mode"])].append(r)
    e6rows = [dict(site=s, scen=sc, mode=m, n=len(rs), tie_old=sum(r["sim"] == r["old"] for r in rs), tie_new=sum(r["sim"] == r["new"] for r in rs),
                   over_new=sum(r["sim"] > r["new"] for r in rs), changed=sum(r["new"] != r["old"] for r in rs)) for (s, sc, m), rs in sorted(g6.items())]
    with open(out / "e6.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(e6rows[0]))
        w.writeheader()
        w.writerows(e6rows)
    L = ["# Recheck with the corrected W′ (return-trip occupancy = minimum over the return-trip routes)\n", "| Batch | Rows | Rows with smaller return occupancy | Rows with changed W′ | ΣW′ before → after | Recorded ≠ recomputed before | Sim > W′ before / after | Ties before → after | Rows with changed L* |",
         "|---|---:|---:|---:|---|---:|---|---|---:|"]
    L += [f"| {s['batch']} | {s['rows']} | {s['corrected']} | {s['changed']} | {s['sum_old']} → {s['sum_new']} | {s['mismatch']} | {s['over_old']} / {s['over_new']} | "
          f"{s['tie_old']} → {s['tie_new']} | {s['lstar_changed']} |" for s in summ]
    L += ["", f"Table 2 (E2): of {e2s['proven']} proven optima, = W′ in {e2s['eq_old']} → {e2s['eq_new']} cases; Σ(W′ − optimum) {e2s['sum_gap_old']} → {e2s['sum_gap_new']}; "
          f"CP-SAT best solution > corrected W′ in {e2s['cp_over_new']} cases.", "", "Table 4 (E6, FCFS):", "| Shipyard | Scenario | Cradle | Points | Ties before → after | W′ changed | Above corrected W′ |",
          "|---|---|---|---:|---|---:|---:|"]
    L += [f"| {r['site']} | {r['scen']} | {r['mode']} | {r['n']} | {r['tie_old']} → {r['tie_new']} | {r['changed']} | {r['over_new']} |" for r in e6rows]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=f"{len(res)} rows; W′ changed in {sum(s['changed'] for s in summ)} rows; sim > corrected W′ in {sum(s['over_new'] for s in summ)} rows")
    print(out)
    print((out / "summary.md").read_text(encoding="utf-8"))


def cfg_key(x):
    batch, row = x
    return [batch.split(":")[1], {k: v for k, v in row.items() if k in ("kind", "scen", "mode", "S", "K", "lift", "hold", "lev", "par", "val", "arr", "geo")}]


if __name__ == "__main__":
    main()
