"""Unified-bound W″_lift recheck of the rows of the 115 m spacing re-runs (windport_recheck_maingeom.one; configurations as
windport_recheck_main2.cfg_of, workers install the 115 m spacing).
Written like windport_revision_r1.run_recheck, run in two parts by batch (main: the spliced batches other than E2; e2: E2 small cases
with S = 2), each with its own result directory; windport_revision_r1.py is not changed (its hash is recorded in the completed re-run
directories). Not rechecked, as in the main geometry: the fixed-duration representation, the cut as a single resource, the
fixed-duration group of the E1-E3 batches, the s3 / cf steps of ablate.
Output results/windport_revision_r1rc_<part>_<config hash>/rows.csv.
Run: python experiments/windport_revision_r1rc.py --part main --procs 9 --slots DIR
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, slot_imap                      # noqa: E402
import windport_revision_r1 as R1                                # noqa: E402


_FK_CFG = None


def init():
    """windport_revision_r1.init_rc (cfg_of of ER / FK replaced by windport_recheck_main2.cfg_of), except that rows of the core
    cases of the main geometry keep windport_recheck_maingeom.cfg_of as is (the cfg_of of the main2 geometry does not know
    maingeom:core)."""
    import windport_recheck_unified as ER
    import windport_recheck_maingeom as FK
    import windport_recheck_main2 as HK
    f_cfg = FK.cfg_of
    R1.init_rc()

    def cfg_of(batch, row):
        if batch == "maingeom:core":
            return f_cfg(batch, row)
        return HK.cfg_of(batch, row)
    ER.cfg_of = FK.cfg_of = cfg_of


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=["main", "e2"])
    ap.add_argument("--procs", type=int, default=9)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_recheck_maingeom as FK
    R1.install()
    sd = {b: d for b, d in R1.splice_dirs().items() if (b == "e1e3:e2") == (a.part == "e2")}
    psha = {b: hashlib.sha256(b"".join((d / n).read_bytes() for n in ("points.csv", "diff.csv") if (d / n).exists())).hexdigest() for b, d in sd.items()}
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in R1.CODE + ["experiments/windport_revision_r1rc.py"]}
    cfg = dict(task="revision", round=1, part=f"recheck_{a.part}", spacing=R1.SPACING, code=code,
               splice={b: str(d.relative_to(ROOT / "results")).replace("\\", "/") for b, d in sd.items()}, points_sha256=psha)
    out = ROOT / "results" / f"windport_revision_r1rc_{a.part}_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    R1.prepare(out, cfg)
    its = [x for x in R1.recheck_items() if x[0] in sd]
    prog = Progress(out / "progress.json", len(its), 0, a.procs, f"115 m spacing re-runs: recheck {a.part} (W″_lift of the re-run rows)", "revision")
    res = []
    try:
        for rs in slot_imap(R1.rc_chunk, [its[k:k + 100] for k in range(0, len(its), 100)], a.procs, initializer=init, slots_dir=a.slots, tag="revision"):
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res.sort(key=lambda r: (r["batch"], str(r["key"])))
    R1.wcsv(out / "rows.csv", res, FK.COLS)
    over = sum(int(r.get("over") or 0) for r in res)
    lh = sum(int(r.get("lstar_hi") or 0) for r in res if r["form"] == "port")
    note = f"{len(res)} rows; sim / CP-SAT > W″_lift: {over}; L″* > time in port: {lh}"
    prog.write(state="done", note=note)
    print(out.name, note)


if __name__ == "__main__":
    main()
