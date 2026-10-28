"""Analytic part of the revision studies (no simulation; unified bound W″_lift = bound_all, main2 geometry, conservative lifting
rule). Reads only the Okpo and Yantai shipyard maps and only outputs numbers.

stage    Minimum pre-window staging needed to neutralise the road. In the window form of W″ (Theorem 1, any history) S is the
         number of monopiles already on the quay side (on cradles or on the ground after the cut) when the window opens, and
         β ≤ q = min(K, Q) is the number of loaded vehicles parked on the quay side at the same time (the cut term takes the
         maximum over k ≤ q and is already in W″). σ* = the smallest S for which all road-class window terms of W″ are
         ≥ I = ⌊L/p⌋ (σ is tried from 1; σ* = 1 is reported as "≤ 1"): with less staging than σ* no dispatching reaches the crane bound (necessary
         condition). Rate-form comparison: σ_rate = ⌈L/p − (L − p)/τ_cut⌉ − q, τ_cut = t_ℓ + t_e (the occupation of one cycle on
         the binding cut; the integer form of S + β < L/p − (L − p)/τ_cut).
         Cases: the long single-lane core case (L = 10 h), the public sites (A1 proxy map, L = 12 h; including Eemshaven Gode
         Wind 3 at 1 / 2.5 km/h), and the two shipyards without buffer (direct loading from the three-voyage storage zone)
         and with the two-level (near-yard) window (L = 10 h).
rated    Certified port-time lower bound L″*(n_v) at rated speeds: loaded v_l and empty v_e take the rated limits of a public
         datasheet (Scheuerle 6-axle-line 210.12.4 G4, 2015-10-13: 10 km/h at axle-line load ≤ 27 t, 5 km/h at ≤ 30 t, empty
         11.5 km/h; parameter register spmt_axle_load_vs_speed_scheuerle, spmt_speed_unloaded), side by side with 1 / 2.5 km/h;
         for two-level storage also T_rate and T_seq*. Also the critical speed v*: below loaded speed v* the certified bound
         L″*(n_v) exceeds the crane bound n_v·p (empty 5 km/h, bisection).
premise  Co-design (long single lane, block length 150 m), five corridor options: the terms that actually enter W″_lift, the
         binding terms, the binding cut and the number of chains, for the premise check in the manuscript.
Output: results/windport_revision_analytic_<config hash>/. Run: python experiments/windport_revision_analytic.py
"""
import csv
import hashlib
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                        # noqa: E402

H, KMH = 3600.0, 1 / 3.6
RATED = dict(r10=dict(v_loaded=10.0 * KMH, v_empty=11.5 * KMH), r5=dict(v_loaded=5.0 * KMH, v_empty=11.5 * KMH))
SPEEDS = dict(v1=dict(v_loaded=1.0 * KMH), v25=dict(v_loaded=2.5 * KMH), **RATED)
KMAX = 8
CODE = ["experiments/windport_revision_analytic.py", "experiments/windport_design_analytic.py", "experiments/windport_maingeom.py", "experiments/windport_spatial.py",
        "experiments/windport_design_lib.py", "experiments/windport_report_design.py", "experiments/windport_survey.py", "windport/bound_all.py",
        "windport/bound.py", "windport/bound_dead.py", "windport/bound_lift.py", "windport/sim4.py", "windport/main2.py"]


def wcsv(path, rows):
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- configurations
def core_cfg(mode, K, p=None):
    import windport_maingeom as F
    c = F.core_cfg(dict(first=170.0, scen="lane", lay=mode, arr="S1", K=K, hold="0", extra=0.0))
    if p:
        c["p"] = dict(c["p"], **p)
    return c


def sites():
    import windport_survey as TS
    if TS.HAUL.exists():
        return TS.haul_survey(json.loads(TS.HAUL.read_text(encoding="utf-8")))
    # release: the haul paths are not released; path and single-lane lengths from the coordinate-free segment table
    out = {k: dict(len_m=None, lane_m=0.0) for k in TS.HAUL_PORTS}
    key = {hp["name"]: k for k, hp in TS.HAUL_PORTS.items()}
    with open(ROOT / "results/runs/survey/segments_public.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            h = out[key[r["site"]]]
            h["len_m"] = float(r["path_m"])
            h["lane_m"] += float(r["seg_m"]) if r["seg_width_class"] == "A" else 0.0
    return {k: dict(h, lane_m=round(h["lane_m"], 1)) for k, h in out.items()}


def site_cfg(h, mode, K, p):
    import windport_design_analytic as IA
    c = IA.eem_cfg(h["len_m"], h["lane_m"], mode, 2.5)
    c.update(K=K, n_load=12 + K + 3)
    c["p"] = dict({k: v for k, v in c["p"].items() if k != "v_loaded"}, **(p or {}))
    if "v_loaded" not in c["p"]:
        c["p"]["v_loaded"] = 2.5 * KMH
    return c


def yard_cfg(site, st, mode, K, p, G=24.0):
    import windport_spatial as A
    c = A.cfg_of("siteport", dict(what="port", kind="map:" + site, st=st, scen="base", mode=mode, arr="S1", K=K, n_v=10))
    if p:
        c["p"] = dict(c["p"], **p)
    if G != A.GRIDS["siteport"]["G"]:
        oh = A.GRIDS["siteport"]["open_h"]
        c.update(horizon_h=G + oh, cal=dict(crane=[[G, G + oh]]))
    return c


def lstar(c, n):
    from windport import bound_all as BA
    lo, hi = BA.lstar(BA.w2_lift(c, BA.parts(c, lift=True)), n)
    return lo / H


# ---------------------------------------------------------------- staging criterion
def staging(c, L_h):
    """(σ*, I, q, τ_cut/p, σ_rate, binding road term @ σ*−1, binding cut): σ is raised from 1 until all road-class window terms
    are ≥ I."""
    from windport import bound_all as BA
    w = BA.parts(c, lift=True)
    P = w["P"]
    L = L_h * H
    I = math.floor(L / P.p + 1e-9)
    road = lambda t: {k: v for k, v in t.items() if BA.CLASS.get(k) == "road" and k not in BA.PREP}
    sig, last = None, None
    for s in range(1, I + 1):
        t = road(BA.terms(dict(w, P=replace(w["P"], S=s)), L, empty=False))
        if not t or min(t.values()) >= I:
            sig = s
            break
        last = min(t, key=t.get)
    q = min(P.K, P.Q)
    tau = P.tl + P.te
    rate = math.ceil(L / P.p - (L - P.p) / tau - 1e-9) - q if tau > 0 else None
    return dict(sigma=sig, I=I, q=q, tau_cut_p=round(tau / P.p, 3), tl_s=round(P.tl, 1), te_s=round(P.te, 1), sigma_rate=rate,
                rate_raw=round(L / P.p - (L - P.p) / tau, 2) if tau > 0 else None, binding_below=last, cut=str(w["t"].get("res")))


def stage_rows():
    import windport_survey as TS
    rows = []
    for m in T.MODES:
        for sp in ("v1", "r10"):
            rows.append(dict(case="core case (long single lane 1.2 km)", obj="core", mode=m, speed=sp, L_h=10, **staging(core_cfg(m, KMAX, SPEEDS[sp]), 10.0)))
    for k, h in sites().items():
        for m in T.MODES:
            for sp in ("v1", "v25", "r10"):
                rows.append(dict(case=TS.HAUL_PORTS[k]["name"], obj=k, mode=m, speed=sp, L_h=12, **staging(site_cfg(h, m, KMAX, SPEEDS[sp]), 12.0)))
    for s in ("okpo", "yantai"):
        for st, nm in (("multi", "no buffer (direct loading from the three-voyage storage zone)"), ("runs", "two-level (near yard)")):
            for m in T.MODES:
                for sp in ("v25", "v1", "r10"):
                    rows.append(dict(case=f"{s} {nm}", obj=f"{s}|{st}", mode=m, speed=sp, L_h=10,
                                     **staging(yard_cfg(s, st, m, KMAX, SPEEDS[sp]), 10.0)))
    return rows


# ---------------------------------------------------------------- rated and critical speeds
def lmin(fn, n, Ks=(KMAX,)):
    return min(lstar(fn(K), n) for K in Ks)


def vcrit(fn, n, crane_h, lo=0.2, hi=12.0, tol=0.005):
    """Loaded speed v (km/h, empty 5 km/h) below which L″*(n) > crane_h, by bisection (L″* does not increase with speed); returns
    "> hi" if still > crane_h at hi, "< lo" if already ≤ at lo."""
    f = lambda v: lstar(fn(dict(v_loaded=v * KMH)), n) - crane_h > 1e-6
    if f(hi):
        return f"> {hi:g}"
    if not f(lo):
        return f"< {lo:g}"
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) else (lo, mid)
    return round((lo + hi) / 2, 3)


def rated_rows():
    import windport_survey as TS
    import windport_report_design as IR
    import windport_design_lib as L
    rows = []
    for m in T.MODES:
        r = dict(case="core case (long single lane 1.2 km)", obj="core", mode=m, n=10, crane_h=10.0)
        for sp, p in SPEEDS.items():
            r[f"L_{sp}"] = round(lmin(lambda K: core_cfg(m, K, p), 10, (1, 2, 4, KMAX)), 3)
        r["v_crit"] = vcrit(lambda p: core_cfg(m, KMAX, p), 10, 10.0)
        rows.append(r)
    for k, h in sites().items():
        for m in T.MODES:
            r = dict(case=TS.HAUL_PORTS[k]["name"], obj=k, mode=m, n=10, crane_h=10.0)
            for sp, p in SPEEDS.items():
                r[f"L_{sp}"] = round(lmin(lambda K: dict(site_cfg(h, m, K, p), n_load=10), 10, (1, 2, 3, KMAX)), 3)
            r["v_crit"] = vcrit(lambda p: dict(site_cfg(h, m, KMAX, p), n_load=10), 10, 10.0)
            rows.append(r)
    for s in ("okpo", "yantai"):
        for st, nm in (("multi", "no buffer"), ("runs", "two-level: near-yard window")):
            for m in T.MODES:
                r = dict(case=f"{s} {nm}", obj=f"{s}|{st}", mode=m, n=10, crane_h=10.0)
                for sp, p in SPEEDS.items():
                    r[f"L_{sp}"] = round(lmin(lambda K: yard_cfg(s, st, m, K, p), 10, (1, 2, 3, KMAX)), 3)
                r["v_crit"] = vcrit(lambda p: yard_cfg(s, st, m, KMAX, p), 10, 10.0)
                rows.append(r)
        # voyage cycle of two-level storage, K = 2: T_rate (Corollary 1) and T_seq* (transfer + lower bound of window⁰ + return)
        r = dict(case=f"{s} two-level: voyage cycle (K = 2)", obj=f"{s}|cycle", mode="pull_in", n=10)
        for sp, p in SPEEDS.items():
            ct = L.transfer_cfg(s, 2, 10, dict(p))
            from windport import bound_all as BA
            P = BA.parts(ct, lift=True)["P"]
            rate = min(2 / P.c, 1.0 / (P.tl + P.te)) * H
            d, _ = IR.return_leg(s)
            ve = p.get("v_empty", 5.0 * KMH)
            tseq = lstar(ct, 10) + min(lstar(yard_cfg(s, "runs", mm, 2, p, G=0.0), 10) for mm in T.MODES) + d / ve / H
            r[f"Trate_{sp}"], r[f"Tseq_lb_{sp}"] = round(10 / rate, 2), round(tseq, 2)
        rows.append(r)
    return rows


# ---------------------------------------------------------------- term list for the premise check
def premise_rows():
    import windport_design as X
    import windport_codesign_blocks as BK
    from windport import bound_all as BA
    items = X.cd_items()
    rows = []
    for i, x in enumerate(items):
        if x["scen"] != "lane" or x["K"] not in (1, 2) or x["S"] not in (0, 1) or x["mode"] != "pull_in" or x["lay"] != "tandem":
            continue
        if x["S"] == 1 and x["lift"] != "cradle":
            continue
        d = dict(cd=i, n_v=10, reach="grid")
        c = X.cd_cfg(d)
        roads = sorted(set(BK.corridor_roads(c)))
        c["p"] = dict(c["p"], retrofit=[dict(kind="blocks", road=r, len=150.0) for r in roads])
        w = BA.parts(c, lift=True)
        t = BA.terms(w, 10 * H, empty=True)
        v, keys, cls, sub, nat = BA.binding(t)
        rows.append(dict(K=x["K"], S=x["S"], lift=x["lift"], hold=x["hold"], pass_=x["pass_"], widen=x["widen"], cut=str(w["t"].get("res")),
                         chains=len(w["chains"]), zc=len(w.get("zc") or []), ll=len(w.get("ll") or []), Q=w["P"].Q, terms="+".join(sorted(k for k in t if k != "prep")),
                         W=v, binding="+".join(keys), cls=cls, tl_s=round(w["P"].tl, 1), te_s=round(w["P"].te, 1)))
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_design as X
    import windport_codesign_blocks as BK
    import windport_netcache as NC
    X.setup_env()
    NC.install()
    parts = sys.argv[1].split(",") if len(sys.argv) > 1 else ["stage", "rated", "premise"]
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="revision", part="analytic", code=code, rated=RATED, kmax=KMAX, maps=X.maps())
    out = ROOT / "results" / f"windport_revision_analytic_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    if "stage" in parts:
        wcsv(out / "stage.csv", stage_rows())
        print("stage done")
    if "rated" in parts:
        wcsv(out / "rated.csv", rated_rows())
        print("rated done")
    if "premise" in parts:
        BK.install_ll()
        wcsv(out / "premise.csv", premise_rows())
        print("premise done")
    print(out)


if __name__ == "__main__":
    main()
