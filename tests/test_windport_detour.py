"""Okpo detour evaluation: T_rate of the Okpo transfer network. Both routes reproduce the released runs/detour/numbers.json
(three decimals); with the detour (node_trace_016 banned) T_rate ≤ T_seq* ≤ T_seq (revision-studies report, K = 2)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import pytest  # noqa: E402

pytestmark = pytest.mark.usefixtures("restore")      # setup_env and the overlays patch modules globally
KMH = 1 / 3.6


def test_detour_trate_ban():
    import windport_detour as P
    plans, _ = P.init()
    ref = json.loads((ROOT / "results/runs/detour/numbers.json").read_text(encoding="utf-8"))["trate"]
    tseq = json.loads((ROOT / "results/tables/revision/numbers.json").read_text(encoding="utf-8"))["buffer"]["tseq"]
    for lv in ("hi", "feas"):
        for sp, sc, vl in (("v1", "slow", 1.0), ("v25", "base", 2.5)):
            p = dict(v_loaded=vl * KMH, v_empty=5.0 * KMH)
            for ban in (0, 1):
                t, _ = P.trate_h(P.tr_cfg_ban("okpo", 2, p, lv, plans, ban))
                assert round(t, 3) == ref[f"okpo|{sp}|{lv}|{ban}"]["T_rate"], (lv, sp, ban)
            s = tseq[f"okpo|{sc}|{lv}|1|2"]
            assert t <= s["T_seq_lb"] <= s["T_seq"], (lv, sp, t, s)                  # detour ordering
