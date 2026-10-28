"""Whether the occupancy windows of the CP-SAT model are identical item by item at 110 / 115 m for the 360 E2 small cases with
S ≤ 1 (replaces the e2 item of windport_revision_r1 inv, whose digest used object repr including memory addresses and is void).
Compared are the data the model actually uses: Inst.win(...) for every (start or cradle row, task, quay position) and
Inst.exit_w(...) for every (quay position, destination) (resource names and durations); also whether W1 (which sets the number of
candidate monopiles) is the same.
If the windows are identical, the CP-SAT models at the two spacings differ only in the number of candidate monopiles (≥ W1 + 2 >
optimum), so the optimum is the same and no re-solve is needed.
Output results/windport_revision_r1inv2_<config hash>/inv2.csv, summary.json.
Run: python experiments/windport_revision_r1inv2.py --procs 2 --slots DIR
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

from batch import Progress, pin, slot_imap                 # noqa: E402
import windport_revision_r1 as R1                                # noqa: E402


def norm(x):
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, dict):
        return {str(k): norm(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    if isinstance(x, (list, tuple)):
        return [norm(v) for v in x]
    return x if isinstance(x, (int, str, bool, type(None))) else str(x)


def digest(key):
    import windport_e2 as E2
    from windport import cpsat_lift as CPL
    inst = CPL.Inst(E2.cfg_of(key))
    locs = sorted(set(inst.starts) | {inst.net.stops[t["o"]]["node"] for t in inst.tasks})
    data = []
    for loc in locs:
        for j in range(len(inst.tasks)):
            for k in range(len(inst.quay)):
                data.append(norm(inst.win(loc, j, k)))
    for k in range(len(inst.quay)):
        for _, node in inst.targets:
            data.append(norm(inst.exit_w(k, node)))
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(), inst.w1["bound"], len(inst.tasks)


def one(key):
    import windport_revision_lib as K
    out = {}
    for sp in (110.0, R1.SPACING):
        K.install_spacing(sp)
        out[sp] = digest(key)
    K.install_spacing(R1.SPACING)
    a, b = out[110.0], out[R1.SPACING]
    return dict(key=key, same_windows=int(a[0] == b[0]), w1_110=a[1], w1_115=b[1], n_cand_110=a[2], n_cand_115=b[2])


def init():
    pin(list(range(1, os.cpu_count())))
    import windport_e2_conservative as E2D
    E2D.init()
    R1.install()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rows, _ = R1.e2_rows()
    keys = [r["key"] for r in rows if int(r["S"]) <= 1]
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in R1.CODE + ["experiments/windport_revision_r1inv2.py"]}
    cfg = dict(task="revision", round=1, part="inv2", spacing=R1.SPACING, code=code, n=len(keys))
    out = ROOT / "results" / f"windport_revision_r1inv2_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    R1.prepare(out, cfg)
    prog = Progress(out / "progress.json", len(keys), 0, a.procs, "115 m spacing re-runs: CP-SAT model windows of E2 S ≤ 1 (110 / 115 m)", "revision")
    res = []
    for r in slot_imap(one, keys, a.procs, initializer=init, slots_dir=a.slots, tag="revision"):
        res.append(r)
        prog.write(done=len(res))
    res.sort(key=lambda r: r["key"])
    R1.wcsv(out / "inv2.csv", res)
    s = dict(n=len(res), same_windows=sum(r["same_windows"] for r in res), w1_same=sum(1 for r in res if r["w1_110"] == r["w1_115"]))
    (out / "summary.json").write_text(json.dumps(s, ensure_ascii=False) + "\n", encoding="utf-8")
    prog.write(state="done", note=json.dumps(s, ensure_ascii=False))
    print(out.name, s)


if __name__ == "__main__":
    main()
