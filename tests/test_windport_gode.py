"""Gode Wind 3 evaluation: the function-evaluation configurations reproduce the released runs/gode/numbers.json (Gode Wind 3
v* at h_d = 30 min, the speed at τ_cut = p; Okpo L″*(10) without buffer); the turn levels add alternative-turn durations only
at lo / hi."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import pytest  # noqa: E402

pytestmark = pytest.mark.usefixtures("restore")      # setup_env and the overlays patch modules globally


def test_gode_reproduces_released_values(tmp_path):
    import windport_gode as N
    N.init(str(tmp_path))
    ref = json.loads((ROOT / "results/runs/gode/numbers.json").read_text(encoding="utf-8"))
    # h_d = 30 min, empty 5 km/h, K = 8: v* (bisection tolerance 0.005 / 0.001)
    for m in N.MODES:
        r = N.compute(("gode", m, "1800", "v"))
        assert abs(r["v_crit"] - ref["gode"][f"{m}|30"]["v_crit"]) < 0.005, m
    t = N.compute(("gode", "pull_in", "1800", "tau"))
    tr = ref["gode"]["pull_in|30"]["tau"]
    assert abs(t["v_cut"] - tr["v_cut"]) < 0.002 and t["zone1_p_2.5"] == tr["zone1_p_2.5"]
    # Okpo without buffer, level none, L″*(10) at 2.5 km/h (minimum over K)
    L = min(N.lstar_k(N.cfg("okpo", "pull_in", "none", K, 2.5, 5.0)) for K in N.KS)
    assert abs(L - ref["okpo"]["pull_in|none"]["v25"]) < 1e-3
    assert "turn_extra" not in N.cfg("okpo", "pull_in", "none", 8, 2.5, 5.0)["p"]
    lo, hi = (N.cfg("okpo", "pull_in", lv, 8, 2.5, 5.0)["p"]["turn_extra"] for lv in ("lo", "hi"))
    assert lo.keys() == hi.keys() and all(lo[k] <= hi[k] for k in lo) and max(lo.values()) > 0
    # both levels with node_trace_016 banned equal the L″* stored for the same configuration by the bmulti batch of the revision
    # studies (2.5 km/h, K = 8, Q_h = 0); node_trace_016 is no longer in the turn list
    bm = {(r["mode"], r["K"], r["hold"], r["lv"]): r for r in csv.DictReader(open(ROOT / "results/runs/revision_bmulti/points.csv", encoding="utf-8"))}
    for lv in ("lo", "hi"):
        c = N.cfg("okpo", "pull_in", f"ban_{lv}", 8, 2.5, 5.0)
        assert not any(k.startswith("node_trace_016") for k in c["p"]["turn_extra"])
        assert abs(N.lstar_k(c) - float(bm[("pull_in", "8", "0", lv)]["lstar_lo"])) < 1e-3, lv
