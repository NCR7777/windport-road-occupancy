"""Lateral clearance c_lat = 2, 3 m applied to E5 (loading and unloading at the same time, two loaded streams passing head-on on the
20 m two-lane road).
Grid: part of the E5 grid: base / long corridor 1 km/h × pull-in × four fleets × K_t = 2, 4 × overlap x = 0, 0.5, 1 × tide 6 h /
continuous × S = 1 × FCFS; the c_lat = 1 m base values are taken from the submitted results/runs/e5 (same
key). Each point is run as in windport_runs.run_one (checker, W1′, joint upper bound).
Output results/windport_extra_sens5_<config hash>/: config.json, progress.json, points/, points.csv.
Run: .venv/Scripts/python.exe experiments/windport_sens_e5.py --procs 22 --slots DIR
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

CODE = T.CODE + ["experiments/windport_sens_e5.py"]
LAT = [2.0, 3.0]
SUB = dict(scen=["base", "longslow"], mode="pull_in", Kt=["2", "4"], x=["0.0", "0.5", "1.0"], S="1", rule="fcfs")


def keys():
    out = []
    for k in T.keys("e5"):
        d = T.dec(k)
        if d["scen"] in SUB["scen"] and d["mode"] == SUB["mode"] and d["Kt"] in SUB["Kt"] and d["x"] in SUB["x"] and d["S"] == SUB["S"] and d["rule"] == SUB["rule"]:
            out += [f"{k}|lat={v}" for v in LAT]
    return out


def run_one(key):
    k, lat = key.rsplit("|lat=", 1)
    orig = T.cfg_of

    def patched(part, kk):
        c = orig(part, kk)
        c["p"] = dict(c["p"], lat_clear=float(lat))
        return c
    T.cfg_of = patched
    try:
        return T.run_one("e5", k)
    finally:
        T.cfg_of = orig


_OUT = None


def init(out):
    global _OUT
    _OUT = Path(out)
    pin(list(range(1, os.cpu_count())))


def run_chunk(ks):
    for k in ks:
        write_json(_OUT / "points" / T.fname(k), run_one(k))
    return ks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=22)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="extra", part="sens5", lat=LAT, sub=SUB, base_dir="results/runs/e5", code=code)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_extra_sens5_{h}"
    (out / "points").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    ks = keys()
    todo = [k for k in ks if not (out / "points" / T.fname(k)).exists()]
    prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, "Lateral clearance × E5", "extra")
    for ds in slot_imap(run_chunk, [todo[i:i + 4] for i in range(0, len(todo), 4)], a.procs, initializer=init, initargs=(str(out),),
                        slots_dir=a.slots, tag="extra"):
        prog.write(done=prog.d["done"] + len(ds))
    rows = []
    for k in ks:
        r = T.row_of("e5", k.rsplit("|lat=", 1)[0], json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8")))
        rows.append(dict(r, key=k, par="latc", val=k.rsplit("|lat=", 1)[1]))
    with open(out / "points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, T.COLS, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
    bad = sum(1 for r in rows if not r["check_ok"])
    jo = sum(1 for r in rows if r.get("joint_ub") not in (None, "") and r["sim"] + r["n_ramp"] > r["joint_ub"])
    note = f"checker failed at {bad} points; above the joint upper bound at {jo} points"
    prog.write(state="done", note=note)
    print(out)
    print(note)


if __name__ == "__main__":
    main()
