"""Gode Wind 3 evaluation: function evaluation (unified bound W″_lift = bound_all, main2 geometry, conservative lifting rule; no
simulation).

gode  Eemshaven Gode Wind 3 (A1 proxy map: route 1,135 m, single lane 795 m, Layout 1 dead-end quay;
      windport_revision_analytic.site_cfg, 10 monopiles per vessel, S = 1, G = 24 h), set-down h_d = 30 / 15 min × two cradle modes:
        L     certified L″*(10) (loaded 1 / 2.5 km/h, empty 5 km/h; rated 5 / 10 km/h, empty 11.5 km/h; minimum over
              K ∈ {1, 2, 3, 8});
        v     critical speed v* (empty 5 km/h, K = 8, as in the revision studies) and the road terms below 10 at L = 10 h,
              0.01 km/h below v*;
        v:term  per-term decomposition: keep only term k of W″, L″*_k = inf{L : term_k(L) ≥ 10}, v*_k = supremum of the loaded
              speeds with L″*_k > 10 h (same basis);
        tau   τ criterion of the design analyses (windport_analytic.tau, W′ parameters): the speeds at which τ_cut = p and
              τ_zone1 = p (the threshold given by the single lane itself is v_cut).
okpo  Okpo without buffer (direct loading from the three-voyage stacking area, original route;
      windport_revision_analytic.yard_cfg(okpo, multi)) × two cradle modes × alternative-turn basis:
        none  no alternative times (the basis of the manuscript values \\OkpoMultiLStar = 14.37 h and
              \\VcritOkpo = 10.4 km/h, i.e. lstar_0 of yards.csv of the main geometry);
        lo    shortest feasible family per turn from turn_alt.json of the design analyses, mode switch t_sw = 30 s (lower end
              of the Table 3 range); hi reverse-crab, t_sw = 300 s.
        ban_lo / ban_hi  loaded-turn ban at node_trace_016 (windport_revision.BAN, overlay installed by
             windport_revision_lib.install_all; the network reroutes through node_trace_015), alternative times from
             okpo|multi_ban of the bturn turn_alt.json of the revision studies (lo: t_sw = 30 s; hi: 300 s), the same
             configuration as bmulti of the revision studies.
        Alternative times exist only for 1 / 2.5 km/h: loaded < 2 km/h uses the 1 km/h set, all others (rated included) use the
        2.5 km/h set.
        L as above; v5 / v115 = v* at empty 5 / 11.5 km/h (K = 8); ve / ve5 = empty-speed threshold v_e* at loaded 10 / 5 km/h
        (rated, axle-line load ≤ 27 t / 27-30 t) (L″*(10) > 10 h when the empty speed is lower; bisection on [5, 11.5] km/h).
Output results/windport_gode_<config hash>/: points/<key>.json (per point), rows.csv, numbers.json (keys used by the manuscript
macros).
Run: python experiments/windport_gode.py --procs 12 --slots DIR
"""
import argparse
import functools
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, slot_imap                       # noqa: E402

H, KMH = 3600.0, 1 / 3.6
MODES = ("on_road", "pull_in")
HD = (1800.0, 900.0)
LEVELS = ("none", "lo", "hi", "ban_lo", "ban_hi")
TERMS = ("cut", "zone", "chainzone")
SPEEDS = dict(v1=(1.0, 5.0), v25=(2.5, 5.0), r5=(5.0, 11.5), r10=(10.0, 11.5))     # (loaded, empty) km/h
KS, KMAX = (1, 2, 3, 8), 8
CODE = ["experiments/windport_gode.py", "experiments/windport_revision_analytic.py", "experiments/windport_design_analytic.py", "experiments/windport_design_lib.py",
        "experiments/windport_analytic.py", "experiments/windport_spatial.py", "experiments/windport_survey.py", "experiments/windport_netcache.py",
        "experiments/windport_revision.py", "experiments/windport_revision_lib.py",
        "windport/bound_all.py", "windport/bound.py", "windport/bound3.py", "windport/bound_dead.py", "windport/bound_lift.py", "windport/sim4.py",
        "windport/main2.py", "windport/shipyard.py"]


def items():
    out = [("gode", m, str(int(hd)), q) for m in MODES for hd in HD for q in ("L", "v", "tau") + tuple(f"v:{k}" for k in TERMS)]
    return out + [("okpo", m, lv, q) for m in MODES for lv in LEVELS for q in ("L", "v5", "v115", "ve", "ve5")]


def key(it):
    return "|".join(it)


# ---------------------------------------------------------------- configuration
@functools.cache
def gw3():
    import windport_revision_analytic as KA
    return KA.sites()["eemshaven_gw3"]


def cfg(obj, mode, var, K, vl, ve):
    import windport_revision_analytic as KA
    p = dict(v_loaded=vl * KMH, v_empty=ve * KMH)
    if obj == "gode":
        return dict(KA.site_cfg(gw3(), mode, K, dict(p, hd_s=float(var))), n_load=10)
    c = KA.yard_cfg("okpo", "multi", mode, K, p)
    vn = "slow" if vl < 2.0 else "base"
    if var == "none":
        return c
    if var.startswith("ban_"):
        import windport_revision as KK
        alt = KK.turn_alt()[0]["okpo|multi_ban"]
        return dict(c, geo=dict(c["geo"], ban=KK.BAN["okpo"]), p=dict(c["p"], turn_extra={k: x["t"][f"{vn}|{var[4:]}"] for k, x in alt.items()}))
    import windport_design_lib as IL
    return IL.with_turns(c, "okpo", "multi", vn, var)


def lstar_k(c, k=None, n=10):
    """L″*(n) (h): k = None uses all terms of W″_lift, otherwise only term k (None if that term is absent)."""
    from windport import bound_all as BA
    w = BA.parts(c, lift=True)
    if k is None:
        f = BA.w2_lift(c, w)
    else:
        if k not in BA.terms(w, 10 * H):
            return None
        f = lambda L: BA.terms(w, L).get(k, math.inf)
    return BA.lstar(f, n)[0] / H


def bisect(f, lo, hi, tol=0.001):
    """f goes from true to false on [lo, hi] (monotone in speed): returns the supremum; "> hi" if still true at hi, "< lo" if
    already false at lo."""
    if f(hi):
        return f"> {hi:g}"
    if not f(lo):
        return f"< {lo:g}"
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) else (lo, mid)
    return round((lo + hi) / 2, 3)


def road_below(obj, mode, var, v, ve):
    """Terms of W″_lift below 10 at speed v, L = 10 h, K = 8 (tightest first)."""
    from windport import bound_all as BA
    t = {k: x for k, x in BA.terms(BA.parts(cfg(obj, mode, var, KMAX, v, ve), lift=True), 10 * H).items() if k != "prep"}
    return "+".join(f"{k}={x}" for k, x in sorted(t.items(), key=lambda kv: kv[1]) if x < 10)


def compute(it):
    obj, mode, var, q = it
    r = dict(obj=obj, mode=mode, var=var, q=q)
    if q == "L":
        for s, (vl, ve) in SPEEDS.items():
            r[f"L_{s}"] = round(min(lstar_k(cfg(obj, mode, var, K, vl, ve)) for K in KS), 4)
    elif q in ("v", "v5", "v115") or q.startswith("v:"):
        ve = 11.5 if q == "v115" else 5.0
        k = q[2:] if q.startswith("v:") else None
        if k is not None and lstar_k(cfg(obj, mode, var, KMAX, 2.5, ve), k) is None:
            r["v_crit"] = "—"
        else:
            r["v_crit"] = bisect(lambda v: lstar_k(cfg(obj, mode, var, KMAX, v, ve), k) > 10.0 + 1e-6, 0.2, 12.0)
            if k is None and not isinstance(r["v_crit"], str):
                r["below"] = road_below(obj, mode, var, r["v_crit"] - 0.01, ve)
    elif q in ("ve", "ve5"):
        vl = 10.0 if q == "ve" else 5.0
        r["ve_crit"] = bisect(lambda e: lstar_k(cfg(obj, mode, var, KMAX, vl, e)) > 10.0 + 1e-6, 5.0, 11.5)
    elif q == "tau":
        import windport_analytic as A6
        tau = lambda v: A6.tau(cfg(obj, mode, var, KMAX, v, 5.0))
        for v in (1.0, 2.5):
            t = tau(v)
            r[f"cut_p_{v}"], r[f"zone1_p_{v}"] = round(t["cut"] / 3600, 3), round(t["zone1"] / 3600, 3)
        r["res"] = tau(2.5)["res"]
        for k in ("cut", "zone1"):
            r[f"v_{k}"] = bisect(lambda v: tau(v)[k] / 3600.0 > 1.0, 0.3, 8.0)
    return r


_OUT = None


def init(out):
    global _OUT
    import windport_design as X
    import windport_revision_lib as K
    import windport_netcache as NC
    X.setup_env()
    K.install_all()                        # ban overlay; configs without ban / buf are unchanged (tests/test_windport_revision.py)
    NC.install()
    _OUT = Path(out)


def one(it):
    r = compute(it)
    (_OUT / "points" / f"{key(it).replace('|', '__')}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    return r


# ---------------------------------------------------------------- summary: numbers entries used by the manuscript macros
def numbers(rows):
    R = {(r["obj"], r["mode"], r["var"], r["q"]): r for r in rows}
    g = {}
    for m in MODES:
        for hd in HD:
            v = str(int(hd))
            L, V, tau = R[("gode", m, v, "L")], R[("gode", m, v, "v")], R[("gode", m, v, "tau")]
            g[f"{m}|{int(hd) // 60}"] = dict({s: L[f"L_{s}"] for s in SPEEDS}, v_crit=V["v_crit"], below=V.get("below", ""),
                                             v_term={k: R[("gode", m, v, f"v:{k}")]["v_crit"] for k in TERMS},
                                             tau={k: tau[k] for k in ("v_cut", "v_zone1", "cut_p_1.0", "zone1_p_1.0", "cut_p_2.5", "zone1_p_2.5", "res")})
    o = {}
    for m in MODES:
        for lv in LEVELS:
            L = R[("okpo", m, lv, "L")]
            o[f"{m}|{lv}"] = dict({s: L[f"L_{s}"] for s in SPEEDS}, v_crit_e5=R[("okpo", m, lv, "v5")]["v_crit"],
                                  below_e5=R[("okpo", m, lv, "v5")].get("below", ""), v_crit_e115=R[("okpo", m, lv, "v115")]["v_crit"],
                                  ve_crit_l10=R[("okpo", m, lv, "ve")]["ve_crit"], ve_crit_l5=R[("okpo", m, lv, "ve5")]["ve_crit"])
    return dict(gode=g, okpo=o, units=dict(L="h (L″*(10), minimum over K ∈ {1, 2, 3, 8})", v="km/h (K = 8)", hd="min"), speeds=SPEEDS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_design as X
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    import windport_design_lib as IL
    import windport_revision as KK
    bt = KK.turn_alt()[1]
    cf = dict(task="gode", code=code, maps=X.maps(), turn_alt=str(IL.turn_file().relative_to(ROOT)).replace("\\", "/"),
              turn_alt_sha256=hashlib.sha256(IL.turn_file().read_bytes()).hexdigest(), bturn=str(bt.relative_to(ROOT)).replace("\\", "/"),
              bturn_sha256=hashlib.sha256(bt.read_bytes()).hexdigest(), ban=KK.BAN, hd=HD, levels=LEVELS, speeds=SPEEDS, ks=KS, kmax=KMAX, terms=TERMS)
    out = ROOT / "results" / f"windport_gode_{hashlib.sha256(json.dumps(cf, sort_keys=True).encode()).hexdigest()[:12]}"
    (out / "points").mkdir(parents=True, exist_ok=True)
    cfp = out / "config.json"
    if cfp.exists() and json.loads(cfp.read_text(encoding="utf-8")) != json.loads(json.dumps(cf)):
        raise SystemExit(f"{cfp} does not match the current configuration; refusing to reuse it")
    cfp.write_text(json.dumps(cf, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = items()
    pt = lambda it: out / "points" / f"{key(it).replace('|', '__')}.json"
    todo = [it for it in its if not pt(it).exists()]
    prog = Progress(out / "progress.json", len(its), len(its) - len(todo), a.procs, "Gode Wind 3 evaluation (Gode Wind 3 h_d, Okpo turn switching)", "gode")
    try:
        for _ in slot_imap(one, todo, a.procs, initializer=init, initargs=(str(out),), slots_dir=a.slots, tag="gode"):
            prog.write(done=prog.d["done"] + 1)
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    rows = [json.loads(pt(it).read_text(encoding="utf-8")) for it in its]
    import windport_revision_analytic as KA
    KA.wcsv(out / "rows.csv", rows)
    N = numbers(rows)
    (out / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    prog.write(state="done", note=f"{len(rows)} items")
    print(out)
    print(json.dumps(N, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
