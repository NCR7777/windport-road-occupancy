"""Design analyses, supplement to the side-by-side reach analysis: with crane reach by distance for side-by-side cradles (S_r = 1, 2, t_sh = 1 h
per far pile), dispatch picks the quay position by lift-finish time (reach_key = "finish" of windport.sim4.ReachMixin, the rule the spatial
additions give for tandem reach), with the lifting exclusion zone of windport_rows_exclusion. Key = t7 reach-by-distance key of windport_rows_exclusion
plus disp = finish.
Output results/windport_design_rowsfin_<config hash>/. Run: python experiments/windport_rows_finish.py --procs 20 --slots DIR
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                        # noqa: E402
import windport_rows_exclusion as RX                                # noqa: E402

RX.CODE.append("experiments/windport_rows_finish.py")
_T7 = RX.t7_keys


def keys():
    return [k + "|disp=finish" for k in _T7() if T.dec(k)["reach"] != "all"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    RX.install(True)
    old, od = RX.t7_keys, RX.out_dir
    RX.t7_keys = keys                                   # single point and summary as in rowsx:t7 (windport_rerun_spatial.run_point("reach", key))
    RX.out_dir = lambda name, extra: od("rowsfin", dict(extra, disp="finish"))
    try:
        RX.run(["rowsx:t7"], a, True)
    finally:
        RX.t7_keys, RX.out_dir = old, od


if __name__ == "__main__":
    main()
