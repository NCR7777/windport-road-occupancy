"""Two-level stacking row (certified L″*(10), critical speed v*, rule-free lower bound T_seq* of the voyage cycle, staging
criterion σ*) recomputed with the main rule of the near-yard layout (stacking places picked by column, picking adds the lateral
shift to the farthest place and 4 mode switches; transfer set-down adds the lateral shift too; windport_revision.plan_cfg). The
lateral shift enters the bound through h_p / h_d; the alternative-turn times (p["turn_extra"]) enter the route occupancy; at
level hi the near-yard and transfer routes take the alternative times of bturn as in the simulation batches bnear / btr
(windport_revision.with_alt: 1 km/h uses the slow set, 2.5 km/h and the rated speeds use the base set - turning, reversing and
crabbing are low-speed manoeuvres and do not get faster with the rated speed). Two levels: hi (switch 300 s, main rule) and
feas (all turns feasible, 30 s, no alternative times). Speeds: 1 / 2.5 km/h and rated 5 / 10 km/h (empty 11.5 km/h).
v* bisects the loaded speed (empty 5 km/h, minimum over K ≤ 8, lateral shift recomputed with the speed; alternative times exist
only for 1 / 2.5 km/h, so none are added in the bisection). T_seq* = L″*_transfer(10) + L″*_window⁰(10) + return leg (K = 2).
σ* as windport_revision_analytic.staging (K = 8).
Output results/windport_revision_r1_rated_<config hash>/rated2.csv.
Run: python experiments/windport_revision_r1_rated.py
"""
import copy
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                        # noqa: E402

H, KMH = 3600.0, 1 / 3.6
CODE = ["experiments/windport_revision_r1_rated.py", "experiments/windport_revision_analytic.py", "experiments/windport_revision.py", "experiments/windport_revision_lib.py",
        "experiments/windport_revision_buffer.py", "experiments/windport_design_lib.py", "experiments/windport_report_design.py", "experiments/windport_spatial.py",
        "windport/bound_all.py", "windport/bound.py", "windport/bound_dead.py", "windport/bound_lift.py", "windport/sim4.py", "windport/shipyard.py"]


def alt_scen(p):
    """bturn has alternative times only for 1 km/h (slow) and 2.5 km/h (base); rated speeds use base."""
    return "slow" if p["v_loaded"] < 2.0 * KMH else "base"


def near_cfg(site, mode, K, p, lv, plans, G=24.0, alt=True):
    import windport_revision as KK
    import windport_revision_analytic as KA
    c = KA.yard_cfg(site, "runs", mode, K, p, G=G)
    c, _ = KK.plan_cfg(c, site, plans[site], dict(p), lv, "pick")
    return KK.with_alt(c, site, "near", alt_scen(p), lv) if alt else c


def tr_cfg(site, K, p, lv, plans):
    import windport_design_lib as L
    import windport_revision as KK
    c = L.transfer_cfg(site, K, 10, dict(p))
    nc = len(plans[site]["columns"])
    c["geo"] = dict(c["geo"], n_cradles=nc)
    c["S"] = nc
    c, _ = KK.plan_cfg(c, site, plans[site], dict(p), lv, "set")
    return KK.with_alt(c, site, "transfer", alt_scen(p), lv)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_design as X
    import windport_report_design as IR
    import windport_revision as KK
    import windport_revision_analytic as KA
    import windport_revision_lib as K
    import windport_netcache as NC
    X.setup_env()
    NC.install()
    plans, pf = KK.load_plans(make=False)
    K.install_all(plans)
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="revision", round=1, part="rated2", code=code, plans_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(), speeds=KA.SPEEDS, kmax=KA.KMAX)
    out = ROOT / "results" / f"windport_revision_r1_rated_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    rows = []
    for s in ("okpo", "yantai"):
        d_ret, _ = IR.return_leg(s)
        for lv in ("hi", "feas"):
            for m in T.MODES:
                r = dict(site=s, level=lv, mode=m, n=10, crane_h=10.0)
                for sp, p in KA.SPEEDS.items():
                    pp = dict(v_loaded=p.get("v_loaded", 2.5 * KMH), v_empty=p.get("v_empty", 5.0 * KMH))
                    r[f"L_{sp}"] = round(min(KA.lstar(near_cfg(s, m, K_, pp, lv, plans), 10) for K_ in (1, 2, 3, KA.KMAX)), 3)
                    st = KA.staging(near_cfg(s, m, KA.KMAX, pp, lv, plans), 10.0)
                    r[f"sigma_{sp}"] = st["sigma"]
                r["v_crit"] = KA.vcrit(lambda p: near_cfg(s, m, KA.KMAX, dict(v_loaded=p["v_loaded"], v_empty=5.0 * KMH), lv, plans, alt=False), 10, 10.0)
                rows.append(r)
            # voyage cycle (K = 2): T_rate (Corollary 1, with c, t_ℓ, t_e on the transfer network) and T_seq*
            from windport import bound_all as BA
            r = dict(site=s, level=lv, mode="cycle", n=10)
            for sp, p in KA.SPEEDS.items():
                pp = dict(v_loaded=p.get("v_loaded", 2.5 * KMH), v_empty=p.get("v_empty", 5.0 * KMH))
                ct = tr_cfg(s, 2, pp, lv, plans)
                P = BA.parts(ct, lift=True)["P"]
                rate = min(2 / P.c, 1.0 / (P.tl + P.te)) * H
                w0 = min(KA.lstar(near_cfg(s, mm, 2, pp, lv, plans, G=0.0), 10) for mm in T.MODES)
                r[f"Trate_{sp}"] = round(10 / rate, 2)
                r[f"Tseq_lb_{sp}"] = round(KA.lstar(ct, 10) + w0 + d_ret / pp["v_empty"] / H, 2)
            rows.append(r)
            print(s, lv, "done", flush=True)
    KA.wcsv(out / "rated2.csv", rows)
    print(out)


if __name__ == "__main__":
    main()
