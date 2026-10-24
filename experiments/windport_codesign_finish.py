"""Design analyses, codesign supplement: for codesign configurations with side-by-side S ≥ 2 and reach by distance (S_r = 1, 2), dispatch picks
the quay position by lift-finish time (reach_key = "finish", the main rule of Table 14), with the lifting exclusion zone of windport_rows_exclusion.
Key = cd key of windport_rows_exclusion (reach = 1, 2) plus disp = finish.
Output results/windport_design_cdfin_<config hash>/. Run: python experiments/windport_codesign_finish.py --procs 20 --slots DIR
"""
import argparse
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
import windport_rows_exclusion as RX                                # noqa: E402

CODE = RX.CODE + ["experiments/windport_codesign_finish.py"]


def keys():
    return [k + "|disp=finish" for k in RX.cd_keys() if T.dec(k)["reach"] != "all"]


def compute(key):
    d = T.dec(key)
    c = X.cd_cfg(d)
    c["p"] = dict(c["p"], reach_key="finish")
    return dict(X.port_point(c, all_j=False), **d)


_OUT = None


def init(out):
    global _OUT
    pin(list(range(1, os.cpu_count())))
    RX.install(True)
    _OUT = Path(out)


def chunk(ks):
    for k in ks:
        f = _OUT / "points" / T.fname(k)
        if not f.exists():
            write_json(f, dict(compute(k), key=k))
    return ks


def main():
    import hashlib
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    RX.install(True)
    from windport import archetypes as A
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="design", part="cdfin", geometry=A.GEOMETRIES[X.GEO], code=code, rule="rows_exclusion", disp="finish", semantics="lift_tu0.05_head")
    out = ROOT / "results" / f"windport_design_cdfin_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    X.prepare(out, cfg)
    ks = keys()
    todo = [k for k in ks if not (out / "points" / T.fname(k)).exists()]
    prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, "design analyses cdfin", "design")
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
    note = f"{len(rs)} points; checker failures {sum(1 for r in rs if not r['check_ok'])}; port time < L″_lift* {lb}"
    prog.write(state="done", note=note)
    print(out.name, note)


if __name__ == "__main__":
    main()
