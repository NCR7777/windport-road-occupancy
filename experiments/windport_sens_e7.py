"""Appendix C, E7 part (base case: the sensitivity analysis also covers the main E7 result): does upscaling still reduce delivery
in steps under every sensitivity level?
Grid: A1 (single lane 12 m) × base / long single lane + 1 km/h × pull-in cradle × monopile 85 / 100 / 110 / 120 m × K = 1–4 × S = 1
× L = 12 h × G = 24 h, with the sensitivity levels of the sens part of windport_runs.py (jack-up / set-down, steering, loaded speed,
crane cycle, direct-lift release time; the release time has no effect in cradle mode but is listed anyway).
Point configurations and summary rows reuse cfg_of / run_one / row_of of windport_runs.py (part = "e7", keys also carry par, val),
so they are produced exactly like E7 and sens.
Output results/windport_runs_sens7_<config hash>/: config.json, progress.json, points/, points.csv.

Run: .venv/Scripts/python.exe experiments/windport_sens_e7.py --procs 23 --slots DIR
"""
import argparse
import csv
import hashlib
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                      # noqa: E402
from batch import Progress, slot_imap                      # noqa: E402

GRID = dict(scen=["base", "lane"], mode=["pull_in"], lev=list(T.E7LEV), K=[1, 2, 3, 4], S=[1], L=[12], G=[24], levels=T.SENS)


def keys():
    out = []
    for par, vals in GRID["levels"].items():
        for val in vals:
            for sc, m, lev, K, S, L, G in itertools.product(GRID["scen"], GRID["mode"], GRID["lev"], GRID["K"], GRID["S"], GRID["L"], GRID["G"]):
                out.append(T.enc(dict(sub="e7", par=par, val=val, kind="A1", scen=sc, mode=m, lift="cradle", rule="fcfs", lev=lev, L=L, K=K, S=S, G=G)))
    return out


def run_chunk(arg):
    _, ks = arg
    for k in ks:
        T.write_json(T._OUT / "points" / T.fname(k), T.run_one("e7", k))
    return ks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=23)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    base = T.config("e7")
    code = dict(base["code"], **{"experiments/windport_sens_e7.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    cfg = dict(base, part="sens7", title="Appendix C: sensitivity of E7 upscaling", grid=dict(GRID, e7=T.GRIDS["e7"]), code=code,
               code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest())
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_runs_sens7_{h}"
    (out / "points").mkdir(parents=True, exist_ok=True)
    cf = out / "config.json"
    if cf.exists() and json.loads(cf.read_text(encoding="utf-8")) != cfg:
        raise SystemExit(f"{cf} does not match the current configuration; refusing to reuse it")
    cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    ks = keys()
    todo = [k for k in ks if not (out / "points" / T.fname(k)).exists()]
    prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, cfg["title"], "runs")
    chunks = [("e7", todo[i:i + 10]) for i in range(0, len(todo), 10)]
    for ds in slot_imap(run_chunk, chunks, a.procs, initializer=T.init, initargs=(str(out),), slots_dir=a.slots, tag="runs"):
        prog.write(done=prog.d["done"] + len(ds))
    rows = [T.row_of("e7", k, json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8"))) for k in ks]
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, T.COLS, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
    bad = sum(1 for r in rows if not r["check_ok"])
    over = sum(1 for r in rows if r["sim"] > r["w1g"])
    note = f"checker failures: {bad} points; above W1′: {over} points"
    prog.write(state="done", note=note)
    print(out)
    print(note)


if __name__ == "__main__":
    main()
