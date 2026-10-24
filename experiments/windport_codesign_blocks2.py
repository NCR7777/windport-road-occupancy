"""Design analyses, dispatch and block-length additions:
  1. codesign tandem S ≥ 2 (far cradles, t_sh = 1 h per pile) picks the quay position by lift-finish time (reach_key = "finish", the main rule
     of Table 14): both the base port (corridor not split into blocks, as before) and the long single lane (corridor uniformly split into blocks of
     150 m, as in windport_codesign_blocks) are recomputed;
  2. block-length sensitivity: all long-single-lane configurations recomputed with block lengths 75 m and 300 m (the four corridor options use the
     same block length; dispatch as in the main rule: tandem S ≥ 2 and side-by-side S ≥ 2 with reach by distance pick the quay position by
     lift-finish time).
  3. The rule for picking the quay position is a design variable (each configuration takes the faster of the two rules): on the long single lane
     the dispatch-dependent configurations (tandem S ≥ 2, side-by-side S ≥ 2 with reach by distance) also get the "earliest lift start" version
     (key without disp): tandem at 75 / 300 m, side-by-side at 75 / 150 / 300 m (tandem at 150 m is already in windport_codesign_blocks).
Single point, bound (including the pure-loaded cut term), checker and per-pile check as in windport_codesign_blocks. Keys with different block lengths
are interleaved in one process, so the network cache is keyed by the build parameters (windport_netcache.install; without it a geo would reuse the
block length of the network built first in the process). Key = codesign key + disp = finish (where needed) + blk = block length (long single lane).
Output results/windport_design_cdblk2_<config hash>/. Run: python experiments/windport_codesign_blocks2.py --procs 22 --slots DIR
"""
import argparse
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
import windport_design as X                                       # noqa: E402
import windport_codesign_blocks as BK                               # noqa: E402
import windport_netcache as NC                                   # noqa: E402

CODE = BK.CODE + ["experiments/windport_codesign_blocks2.py", "experiments/windport_netcache.py"]
BLOCKS = dict(main=150.0, sens=[75.0, 300.0])


def keys():
    items = X.cd_items()
    out = []
    for k in X.cd_keys():
        d = T.dec(k)
        x = items[int(d["cd"])]
        tandem2 = x["lay"] == "tandem" and x["S"] >= 2
        side_far = x["lay"] == "side" and x["S"] >= 2 and d["reach"] in ("1", "2")
        kk = k + "|disp=finish" if (tandem2 or side_far) else k
        if x["scen"] == "base":
            if tandem2:
                out.append(kk)
            continue
        if tandem2:
            out.append(kk + f"|blk={BLOCKS['main']:g}")
        out += [kk + f"|blk={b:g}" for b in BLOCKS["sens"]]
        if tandem2 or side_far:                                  # earliest-lift-start version
            out += [k + f"|blk={b:g}" for b in BLOCKS["sens"] + ([BLOCKS["main"]] if side_far else [])]
    return out


def cfg(d):
    c = X.cd_cfg(d)
    if d.get("disp") == "finish":
        c["p"] = dict(c["p"], reach_key="finish")
    if d.get("blk"):
        roads = sorted(set(BK.corridor_roads(c)))
        c["p"] = dict(c["p"], retrofit=[dict(kind="blocks", road=r, len=float(d["blk"])) for r in roads])
    return c


def compute(key):
    d = T.dec(key)
    return dict(X.port_point(cfg(d), all_j=True), **d)


_OUT = None


def init(out):
    global _OUT
    pin(list(range(1, os.cpu_count())))
    BK.RX.install(True)
    BK.install_ll()
    NC.install()
    _OUT = Path(out)


def chunk(ks):
    for k in ks:
        f = _OUT / "points" / T.fname(k)
        if not f.exists():
            write_json(f, dict(compute(k), key=k))
    return ks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    BK.RX.install(True)
    BK.install_ll()
    NC.install()
    from windport import archetypes as A
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cf = dict(task="design", part="cdblk2", geometry=A.GEOMETRIES[X.GEO], code=code, blocks=BLOCKS, rule="rows_exclusion", semantics="lift_tu0.05_head")
    out = ROOT / "results" / f"windport_design_cdblk2_{hashlib.sha256(json.dumps(cf, sort_keys=True).encode()).hexdigest()[:12]}"
    X.prepare(out, cf)
    ks = keys()
    todo = [k for k in ks if not (out / "points" / T.fname(k)).exists()]
    prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, "design analyses cdblk2 (tandem by lift-finish time, block-length sensitivity)", "design")
    try:
        for ds in slot_imap(chunk, [todo[i:i + a.chunk] for i in range(0, len(todo), a.chunk)], a.procs, initializer=init, initargs=(str(out),),
                            slots_dir=a.slots, tag="design"):
            prog.write(done=prog.d["done"] + len(ds))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    rs = [json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8")) for k in ks]
    X.wcsv(out / "points.csv", [X.sim_row("codesign", k, r) for k, r in zip(ks, rs)])
    lb = sum(1 for r in rs if r["port_h"] is not None and r["port_h"] < r["lstar_lo"] - 1e-9)
    vi = sum(int(r["viol"] or 0) for r in rs)
    note = f"{len(rs)} points; checker failures {sum(1 for r in rs if not r['check_ok'])}; port time < L″_lift* {lb}; W″_lift(T_j) < j for {vi} piles (of {sum(r['lifts'] for r in rs)})"
    prog.write(state="done", note=note)
    print(out.name, note)


if __name__ == "__main__":
    main()
