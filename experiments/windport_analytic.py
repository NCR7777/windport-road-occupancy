"""Analytic part (no simulation; uses only the bound code and the wait-free windows of the road-occupancy model: windport/bound.py,
bound2.py, bound3.py).

--part example  Worked-example table: A1 base and long single lane 1 km/h × cradle mode × K = 1, 2, S = 1, L = 12 h, G = 24 h:
                cut, cut length, t_ℓ (split into driving, vehicle tail, steering stop, set-down), t_e, t_e^occ, c, d_q, geometric
                quay-zone Q, K†, the terms I, U, F, C, Z, Π, Π_S, W′ and the binding term. Simulated deliveries are taken from the
                E4 points.csv by the summary script.
--part critical Critical single-lane length: A1 with one single-lane section (n_junctions = 0) of length ℓ and a 200 m two-lane
                road on the storage side, S = 1, Q_h = 0:
                (a) long run: the minimum time one monopile must occupy the road, τ_cut = t_ℓ + t_e (round trip over the cut) and
                    τ_zone1 = t_ℓ + d_q + t_e^occ (quay zone holds one vehicle set), and the quay-zone term of W′ itself,
                    τ_W = max(τ_cut, (t_ℓ + d_q)/Q or τ_zone1); for τ > p no fleet can keep the vessel crane lifting
                    continuously. Critical length ℓ* = inf{ℓ : τ(ℓ) > p} for loaded speed 0.5–5 km/h, p = 0.5, 1, 1.5 h,
                    on-road / pull-in cradles;
                (b) window: the shortest ℓ at which the smallest W′ term other than the interface term is < ⌊L/p⌋ (K = 10,
                    G = 24 h), for L/p = 3–24, S = 0, 1, 3, loaded speed 1 and 2.5 km/h, p = 1 h;
                (c) τ/p for named cases: three layouts × base / long corridor 1 km/h / long single lane 1 km/h, Okpo and Yantai
                    × base / 1 km/h (both cradle modes, S = 1, p = 1, 0.5 h).
Output results/windport_extra_<part>_<config hash>/: config.json, <part>.csv, <part>.json.
Run: .venv/Scripts/python.exe experiments/windport_analytic.py --part example
"""
import argparse
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

from windport import bound as WB                                 # noqa: E402
from windport import bound2 as W2                                # noqa: E402
from windport import bound3 as B3                                # noqa: E402
from windport import sim as S                                    # noqa: E402
from windport import sim2 as S2                                  # noqa: E402
import windport_runs as T                                        # noqa: E402

KMH = 1 / 3.6
CODE = ["windport/sim.py", "windport/sim2.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py", "windport/archetypes.py",
        "windport/shipyard.py", "occupancy/network.py", "occupancy/params.py", "experiments/windport_runs.py", "experiments/windport_analytic.py"]
GRIDS = dict(
    example=dict(scen=["base", "lane"], modes=T.MODES, K=[1, 2], S=1, L=12, G=24),
    critical=dict(v=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0], p=[0.5, 1.0, 1.5], modes=T.MODES, wide_m=200.0, ell_max=6000.0,
                  win=dict(Lp=[3, 4, 6, 8, 12, 16, 24], S=[0, 1, 3], v=[1.0, 2.5], p=1.0, K=10, G=24),
                  named=dict(kinds=["A1", "A2", "A3"], scen=["base", "slow", "longslow", "lane"], sites=["okpo", "yantai"], site_scen=["base", "slow"],
                             p=[1.0, 0.5], K=10)),
)


def cfg_e4(kind, sc, mode, K, Sn, L, G, extra_p=None, geo=None):
    c = T.cfg_of("e4", T.enc(dict(kind=kind, scen=sc, mode=mode, lift=T.lift_of(Sn), rule="fcfs", L=L, K=K, S=Sn, G=G)))
    if extra_p:
        c["p"] = dict(c["p"], **extra_p)
    if geo is not None:
        c["geo"] = geo
    return c


def decompose(c):
    """Split t_ℓ: steering stop δ (stops at turns ≥ 60° entering and leaving the cut, on the trip to the nearest cradle position),
    vehicle tail (Lv + longitudinal clearance)/v (when the cut is not the road of the quay stop), set-down h_d (on-road cradles, when
    the cut is the road of the quay stop); the rest is driving on the cut."""
    D, net, p, *_ = S2.setup2(c)
    w = B3.wprime_parts(c)
    t, P = w["t"], w["P"]
    cut = t["res"]
    v = p["v_loaded"]
    W = D["windport"]
    sd = net.stops[W["cradles"][0]]
    stop_cut = sd["res"] == cut
    best = None
    for o in W["storage"]:
        runs, dl = S.turn_delays(net, net.path(net.stops[o]["node"], sd["node"]), p["Lv"], v, p)
        idx = [i for i, r in enumerate(runs) if ("r", r[0]) == cut]
        if idx:
            i = idx[0]
            d = dl[i] + (dl[i + 1] if i + 1 < len(dl) else 0.0)
            best = d if best is None else min(best, d)
    delta = best or 0.0
    tail = 0.0 if stop_cut else (p["Lv"] + p["long_clear"]) / v
    hd = P.hd if stop_cut else 0.0
    length = net.road[cut[1]]["L"] if cut[0] == "r" else None
    return dict(cut="|".join(map(str, cut)), cut_len_m=round(length, 1) if length else None, delta_s=round(delta, 1), tail_s=round(tail, 1),
                hd_on_cut=hd, drive_s=round(t["tl"] - delta - tail - hd, 1), tl=round(t["tl"], 1), te=round(t["te"], 1), te_occ=round(t["te_occ"], 1),
                c=round(P.c, 1), dq=round(P.dq, 1), Q=P.Q, k_dagger=round(WB.k_dagger(P), 3))


def example():
    g = GRIDS["example"]
    out = []
    for sc in g["scen"]:
        for m in g["modes"]:
            for K in g["K"]:
                c = cfg_e4("A1", sc, m, K, g["S"], g["L"], g["G"])
                D, net, p, *_ = S2.setup2(c)
                w = B3.wprime_parts(c)
                P, G = w["P"], w["G"]
                tm = WB.terms(P, G)
                ser = min((W2.prep_chain(ch, K, b, G + P.L, P.p, w["hp"]) for ch, b in zip(w["chains"], w["bm"])), default=math.inf)
                wp = B3.wprime_fn(c)(P.L)
                r = S2.bounds2(c, D, net, p)
                assert wp == r["bound"], (wp, r)
                row = dict(scen=sc, mode=m, K=K, S=g["S"], L=g["L"], G=g["G"], **decompose(c))
                row.update(hp=p["hp_s"], hd=P.hd, interface=tm["interface"], turnover=None if tm["turnover"] == math.inf else tm["turnover"],
                           fleet=tm["fleet"], cut_term=tm["cut"], zone=tm.get("zone"), prep=tm["prep"], serial=None if ser == math.inf else ser,
                           w1g=r["bound"], binding=r["binding"], rate_h=round(WB.rate(P) * 3600, 4))
                out.append(row)
    return out


# ---------------------------------------------------------------- critical single-lane length
def lane_geo(ell, mode, wide):
    return dict(kind="A1", n_cradles=6, cradle_mode=mode, dist_m=ell + wide, corridor_m=ell, n_junctions=0)


def tau(c):
    """Minimum time one monopile must occupy the road: τ_cut = t_ℓ + t_e, τ_zone1 = t_ℓ + d_q + t_e^occ, τ_W (quay-zone term of W′,
    geometric Q)."""
    w = B3.wprime_parts(c)
    P, t = w["P"], w["t"]
    cut = P.tl + P.te
    z1 = P.tl + P.dq + t["te_occ"]
    zw = z1 if P.Q == 1 else (P.tl + P.dq) / P.Q
    return dict(cut=cut, zone1=z1, w=max(cut, zw), Q=P.Q, tl=P.tl, te=P.te, te_occ=t["te_occ"], dq=P.dq, c=P.c, res="|".join(map(str, t["res"])))


def crit_len(fn, lo=10.0, hi=6000.0, tol=0.5):
    """inf{ℓ : fn(ℓ)} (fn turns from false to true as ℓ grows); returns 0 if already true at lo, None if still false at hi."""
    if fn(lo):
        return 0.0
    if not fn(hi):
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if fn(mid) else (mid, hi)
    return round(hi, 1)


def critical():
    g = GRIDS["critical"]
    rows = []
    for m in g["modes"]:
        for v in g["v"]:
            for pp in g["p"]:
                ps = pp * 3600.0
                mk = lambda ell: cfg_e4("A1", "base", m, 10, 1, 12, 24, extra_p=dict(v_loaded=v * KMH, lift_s=ps), geo=lane_geo(ell, m, g["wide_m"]))
                row = dict(part="longrun", mode=m, v=v, p=pp)
                for k in ("cut", "zone1", "w"):
                    row[f"ell_{k}"] = crit_len(lambda ell: tau(mk(ell))[k] > ps, hi=g["ell_max"])
                t0 = tau(mk(10.0))
                row.update(tau_cut_at10=round(t0["cut"], 1), tau_zone1_at10=round(t0["zone1"], 1), res_at10=t0["res"])
                rows.append(row)
                S2._NETS.clear()
    a = g["win"]
    for Sn in a["S"]:
        for v in a["v"]:
            for Lp in a["Lp"]:
                L = Lp * a["p"]
                mk = lambda ell: cfg_e4("A1", "base", "pull_in", a["K"], Sn, L, a["G"], extra_p=dict(v_loaded=v * KMH, lift_s=a["p"] * 3600.0),
                                        geo=lane_geo(ell, "pull_in", g["wide_m"]))

                def road(ell):
                    c = mk(ell)
                    w = B3.wprime_parts(c)
                    P = w["P"]
                    tm = WB.terms(P, w["G"])
                    ser = min((W2.prep_chain(ch, c["K"], b, w["G"] + P.L, P.p, w["hp"]) for ch, b in zip(w["chains"], w["bm"])), default=math.inf)
                    return min([x for k, x in tm.items() if k != "interface"] + [ser]) < tm["interface"]
                rows.append(dict(part="window", mode="pull_in", v=v, p=a["p"], S=Sn, Lp=Lp, ell_window=crit_len(road, hi=g["ell_max"])))
                S2._NETS.clear()
    n = g["named"]
    for kind in n["kinds"]:
        for sc in n["scen"]:
            for m in T.MODES:
                for pp in n["p"]:
                    c = cfg_e4(kind, sc, m, n["K"], 1, 12, 24, extra_p=dict(lift_s=pp * 3600.0))
                    t = tau(c)
                    rows.append(dict(part="named", kind=kind, scen=sc, mode=m, p=pp, **{k: (round(x, 1) if isinstance(x, float) else x) for k, x in t.items()},
                                     ratio_cut=round(t["cut"] / (pp * 3600), 3), ratio_zone1=round(t["zone1"] / (pp * 3600), 3), ratio_w=round(t["w"] / (pp * 3600), 3)))
    for site in n["sites"]:
        for sc in n["site_scen"]:
            for m in T.MODES:
                for pp in n["p"]:
                    c = T.cfg_of("e6", T.enc(dict(kind="map:" + site, scen=sc, mode=m, lift="cradle", rule="fcfs", L=12, K=n["K"], S=1, G=24)))
                    c["p"] = dict(c["p"], lift_s=pp * 3600.0)
                    t = tau(c)
                    rows.append(dict(part="named", kind=site, scen=sc, mode=m, p=pp, **{k: (round(x, 1) if isinstance(x, float) else x) for k, x in t.items()},
                                     ratio_cut=round(t["cut"] / (pp * 3600), 3), ratio_zone1=round(t["zone1"] / (pp * 3600), 3), ratio_w=round(t["w"] / (pp * 3600), 3)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=list(GRIDS))
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="extra", part=a.part, grid=GRIDS[a.part], base=S.BASE, scen=T.SCEN, code=code,
               code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest())
    if a.part == "critical":
        cfg["networks"] = {s: T.SY.NETWORK[s] for s in ("okpo", "yantai")}
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_extra_{a.part}_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    rows = example() if a.part == "example" else critical()
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with open(out / f"{a.part}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    print(out)


if __name__ == "__main__":
    main()
