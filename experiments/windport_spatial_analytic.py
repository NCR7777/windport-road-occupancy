"""The spatial additions: the parts that run no simulation (reads only the Okpo and Yantai maps, writes only text and data, draws no maps).

--part regime5   The A1 points of E1 (five scenarios × cradle mode × L = 2–24 h × K = 1–6 × S = 0, 1, 2, 3, 4, 6 × G = 3, 24 h, main
                 lifting rule and mixed lifting) are classified into five regimes by the W′ term that actually binds
                 (windport.bound4.classify: crane, cradle turnover, fleet, road, preparation time; preparation time also records its
                 sub-type); the simulated delivery is taken from the committed runs/e1. Output regime5.csv.
--part critical  New points for Fig. 12. (a) Okpo and Yantai with the relaxed storage areas (base / 1 km/h × cradle mode × p = 1, 0.5 h;
                 plus alternative turning manoeuvres of 600 and 1,800 s): τ/p (as tau in windport_analytic: τ_cut = t_ℓ + t_e,
                 τ_zone1, τ_W); (b) real ports that public figures can locate: Rønne (the 250 m route of Kassels Appendix D, 2.5 km/h; A1
                 aligned by route length, as in the pub part of the extra analyses) and the Rønne electric SPMT trial (815 m, speed not
                 published: 1 and 2.5 km/h); where the single-lane length is not published, the interval is given by the two ends, single
                 lane 0 and 100% of the route. Output critical_points.csv.
--part codesign  Integer enumeration for the co-design. A1 base / long single lane 1 km/h × one vessel n_v = 3, 5, 10 × K = 1–8 × S = 0–3
                 × cradle layout (tandem: S_r = 1, t_sh = 1 h; side-by-side: all reachable) × cradle mode (roadside / pull-in for tandem) ×
                 lifting (cradle / mixed) × Q_h = 0, 1 × passing place (with / without, tandem) × single lane widened to 16 m (with /
                 without); the port time of each configuration is L*(n_v) (W″, independent of dispatch); cost per voyage = vessel day rate
                 × L*/24 + K × 7,200 €/day × voyage cycle 6 days + S × 60,000 €/10 calls (as in the cost table of the extra analyses);
                 infrastructure (gate holding places, passing places, widening) has no public unit price, so the saving per voyage and the
                 break-even investment over a campaign of 10 voyages are reported.
                 Output codesign.csv (all configurations), best.csv, chosen.json (input to the simulation check windport_spatial.py --part
                 cdv; also contains the top 3 for each single infrastructure addition and for "passing place + widening"; savings are
                 reported for simulation-checked configurations, L* is used only for screening).
--part campaign  Campaign duration with one vessel and several voyages. One vessel carries n_v piles, 60 in total; each voyage = port time
                 + round-trip sailing 2 × 12 h + 24 h installation per pile (only in workable periods; weather in 6 h blocks, a two-state
                 Markov chain with workable probability q and persistence parameter ρ, seeds 1–200); port time in two representations:
                 occupancy model (FCFS port time of the port part of the extra analyses) and fixed time (value for K = 2 after calibrating
                 with K_ref = 1 in the same scenario, or the crane lower bound n_v·p). Output campaign.csv.
Output results/windport_spatial_<part>_<config hash>/.
Run: python experiments/windport_spatial_analytic.py --part regime5
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from windport import shipyard as SY                              # noqa: E402
from windport import sim as WS                                   # noqa: E402
from windport import sim4 as S4                                  # noqa: E402
import windport_runs as T                                        # noqa: E402

CODE = ["windport/sim.py", "windport/sim2.py", "windport/sim4.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py",
        "windport/bound4.py", "windport/archetypes.py", "windport/shipyard.py", "occupancy/network.py", "occupancy/params.py",
        "experiments/windport_runs.py", "experiments/windport_spatial_analytic.py"]
KMH = 1 / 3.6
E1_DIR = "results/runs/e1"
E3_DIR = "results/runs/e3"
EXTRA_PORT = "results/runs/port_time"
RATES = [140000, 250000]                     # €/day: Ursavas 2017 jack-up vessel; upper end of the Tjaberings 2022 heavy-lift range
SET_DAY = 24 * (180 + 120)                   # €/day: one SPMT set + two operators, busy rate (Kassels Appendix D)
SUPPORT, CALLS, CYCLE = 60000.0, 10, 6       # € per cradle, calls for amortisation, voyage cycle (days) (Kassels App. D; 10 voyages in 61 days)
GRIDS = dict(
    regime5=dict(scen=["base", "slow", "longslow", "lane", "fastcrane"], e1_dir=E1_DIR),
    critical=dict(sites=["okpo", "yantai"], scen=["base", "slow"], p=[1.0, 0.5], K=10, extra=[0.0, 600.0, 1800.0],
                  ports=[dict(name="Rønne (Kassels, Appendix D)", route_m=250.0, v=[2.5], src="Kassels 2023 Appendix D p.53: storage area → quayside location 250 m; SPMT 2,500 m/h"),
                         dict(name="Rønne electric SPMT trial (Baltica 2)", route_m=815.0, v=[1.0, 2.5],
                              src="Mammoet press release (oceannews.com): one 1,700 t monopile moved 815 m; not stated whether this is the full storage-to-quay route; speed not published")],
),
    codesign=dict(scen=["base", "lane"], n_v=[3, 5, 10], K=list(range(1, 9)), S=[0, 1, 2, 3], reach=(1, 3600.0), hold=[0, 1], pass_=dict(pp_m=150.0, pp_w=16.0),
                  widen=16.0, rates=RATES, set_day=SET_DAY, support=SUPPORT, calls=CALLS, cycle=CYCLE, G=24, open_h=200, top=3),
    campaign=dict(n_total=60, n_v=[3, 10], transit_h=12.0, install_h=24.0, block_h=6.0, q=[0.6, 0.8], spell_blocks=4.0, seeds=list(range(1, 201)),
                  scen=["base", "lane"], K=[1, 2], e3_dir=E3_DIR, extra_port=EXTRA_PORT),
)


# ---------------------------------------------------------------- five regimes
def regime5():
    import windport_sim as E1M
    from windport import bound4 as B4
    g = GRIDS["regime5"]
    sim = {r["key"]: r for r in csv.DictReader(open(ROOT / g["e1_dir"] / "points.csv", encoding="utf-8"))}
    rows = []
    for k in E1M.keys("e1"):
        f = k.split("|")
        if f[0] != "A1" or f[1] not in g["scen"]:
            continue
        c = E1M.cfg_of("e1", k)
        cl = B4.classify(c)
        r = sim[k]
        rows.append(dict(key=k, scen=f[1], mode=f[2], lift=f[3], L=int(f[4][1:]), K=int(f[5][1:]), S=int(f[6][1:]), G=int(f[7][1:]), sim=int(r["sim"]),
                         w1=int(r["w1"]), wprime=cl["wprime"], cls=cl["cls"], sub=cl["sub"], nature=cl["nature"], binding=cl["binding"], regime3=r["regime"],
                         **{f"t_{a}": b for a, b in cl["terms"].items()}))
        assert int(r["sim"]) <= cl["wprime"], k
    return rows


# ---------------------------------------------------------------- new points for the critical-length figure
def critical():
    import windport_analytic as A6
    g = GRIDS["critical"]
    import windport_spatial as E
    ex = json.loads(E.turn_file().read_text(encoding="utf-8"))
    rows = []
    rat = lambda t, pp: dict(ratio_cut=round(t["cut"] / (pp * 3600), 3), ratio_zone1=round(t["zone1"] / (pp * 3600), 3), ratio_w=round(t["w"] / (pp * 3600), 3))
    for site in g["sites"]:
        for st in ("runs", "multi"):
            for sc in g["scen"]:
                for m in T.MODES:
                    for pp in g["p"]:
                        for x in g["extra"]:
                            c = T.cfg_of("e6", T.enc(dict(kind="map:" + site, scen=sc, mode=m, lift="cradle", rule="fcfs", L=12, K=g["K"], S=1, G=24)))
                            c["p"] = dict(c["p"], lift_s=pp * 3600.0)
                            if st == "multi":
                                c["geo"] = dict(c["geo"], storage="multi")
                            if x:
                                c["p"]["turn_extra"] = {n: x for n in ex[f"{site}|{st}"]}
                            D, net, *_ = S4.setup4(c)
                            t = A6.tau(c)
                            route = min(sum(net.arc[a][2] for a in net.path(net.stops[o]["node"], net.stops[D["windport"]["cradles"][0]]["node"]))
                                        for o in D["windport"]["storage"])
                            rows.append(dict(kind="site", name=site, storage=st, scen=sc, mode=m, p=pp, turn_extra=x, route_m=round(route, 1),
                                             v=T.SCEN[sc].get("p", {}).get("v_loaded", WS.BASE["v_loaded"]) * 3.6,
                                             **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in t.items()}, **rat(t, pp)))
    for port in g["ports"]:
        for v in port["v"]:
            for frac in (0.0, 1.0):
                for m in T.MODES:
                    dist = port["route_m"] - 100.0           # as in the pub part: in A1 saddle row to cradle bay is dist_m + 100 m (yard offset 60 m + gate to cradle 40 m)
                    geo = dict(kind="A1", n_cradles=6, cradle_mode=m, dist_m=dist, corridor_m=max(10.0, frac * dist), n_junctions=0)
                    c = A6.cfg_e4("A1", "base", m, g["K"], 1, 12, 24, extra_p=dict(v_loaded=v * KMH), geo=geo)
                    D, net, *_ = S4.setup4(c)
                    route = min(sum(net.arc[a][2] for a in net.path(net.stops[o]["node"], net.stops[D["windport"]["cradles"][0]]["node"]))
                                for o in D["windport"]["storage"])
                    t = A6.tau(c)
                    rows.append(dict(kind="port", name=port["name"], storage="", scen="", mode=m, p=1.0, turn_extra=0.0, route_m=round(route, 1), v=v,
                                     lane_frac=frac, lane_m=geo["corridor_m"], src=port["src"],
                                     **{k: (round(x, 1) if isinstance(x, float) else x) for k, x in t.items()}, **rat(t, 1.0)))
    return rows


# ---------------------------------------------------------------- co-design
def cd_configs(sc):
    g = GRIDS["codesign"]
    s = T.SCEN[sc]
    out = []
    for K, Sn in itertools.product(g["K"], g["S"]):
        lays = ["tandem"] if Sn == 0 else ["tandem", "side"]
        for lay in lays:
            modes = T.MODES if lay == "tandem" else ["side"]
            lifts = ["direct"] if Sn == 0 else ["cradle", "mixed"]
            for m, lf, h, pa, wd in itertools.product(modes, lifts, g["hold"], [0, 1] if lay == "tandem" else [0], [0, 1]):
                geo = dict(kind="A1side" if lay == "side" else ("A1pass" if pa else "A1"), n_cradles=6, **s.get("geo", {}))
                if lay == "tandem":
                    geo["cradle_mode"] = m
                if pa:
                    geo.update(g["pass_"])
                if wd:
                    geo["corridor_w"] = g["widen"]
                p = dict(s.get("p", {}))
                if lay == "tandem" and Sn > g["reach"][0]:
                    p.update(reach=g["reach"][0], shift_s=g["reach"][1])
                out.append(dict(scen=sc, K=K, S=Sn, lay=lay, mode=m, lift=lf, hold=h, pass_=pa, widen=wd, geo=geo, p=p))
    return out


def codesign():
    from windport import bound3 as B3
    from windport import bound4 as B4
    g = GRIDS["codesign"]
    rows = []
    for sc in g["scen"]:
        for x in cd_configs(sc):
            c = dict(geo=x["geo"], p=x["p"], S=x["S"], K=x["K"], lift=x["lift"], horizon_h=g["G"] + g["open_h"], cal=dict(crane=[[g["G"], g["G"] + g["open_h"]]]),
                     n_load=max(g["n_v"]), hold=x["hold"], rule="fcfs")
            f = B4.wprime4_fn(c)
            for n in g["n_v"]:
                lo, hi = B3.lstar(f, n)
                Lh = hi / 3600.0
                r = dict({k: v for k, v in x.items() if k not in ("geo", "p")}, n_v=n, lstar_h=round(Lh, 4))
                for rate in g["rates"]:
                    r[f"cost_{rate // 1000}k"] = round(Lh / 24 * rate + x["K"] * g["set_day"] * g["cycle"] + x["S"] * g["support"] / g["calls"])
                r["cfg"] = json.dumps(dict(geo=x["geo"], p=x["p"], S=x["S"], K=x["K"], lift=x["lift"], hold=x["hold"], n_v=n), sort_keys=True)
                rows.append(r)
    best, chosen = [], {}
    for sc in g["scen"]:
        for n in g["n_v"]:
            for rate in g["rates"]:
                ck = f"cost_{rate // 1000}k"
                rs = sorted((r for r in rows if r["scen"] == sc and r["n_v"] == n), key=lambda r: (r[ck], r["lstar_h"], r["hold"] + r["pass_"] + r["widen"], r["cfg"]))
                plain = [r for r in rs if not (r["hold"] or r["pass_"] or r["widen"])]
                b0 = plain[0]
                line = dict(scen=sc, n_v=n, rate=rate, best=rs[0], plain=b0)
                for opt in ("hold", "pass_", "widen"):
                    w = [r for r in rs if r[opt] and all(not r[o] for o in ("hold", "pass_", "widen") if o != opt)]
                    line[f"save_{opt}"] = round(b0[ck] - w[0][ck]) if w else None
                    line[f"with_{opt}"] = w[0] if w else None
                best.append(line)
                # each single infrastructure addition (and passing place + widening) also sends its top `top` to the simulation check;
                # savings are reported from simulation
                infra = [[r for r in rs if (r["hold"], r["pass_"], r["widen"]) == c] for c in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1))]
                for r in rs[:g["top"]] + plain[:g["top"]] + [x for lst in infra for x in lst[:g["top"]]]:
                    chosen[r["cfg"]] = json.loads(r["cfg"])
    return rows, best, [chosen[k] for k in sorted(chosen)]


# ---------------------------------------------------------------- campaign duration
def weather(seed, q, spell, n):
    """Two-state Markov chain in 6 h blocks (1 = workable): workable spells last `spell` blocks on average, stationary probability q."""
    import random
    R = random.Random(seed)
    a = 1 - 1 / spell
    b = max(0.0, 1 - q * (1 - a) / (1 - q))
    s, out = int(R.random() < q), []
    for _ in range(n):
        out.append(s)
        s = int(R.random() < (a if s else 1 - b))
    return out


def campaign_len(Tp, g, n_v, wx):
    """Campaign duration (h): each voyage = Tp h in port, outbound transit, pile-by-pile installation (the clock runs only in workable
    blocks, install_h per pile), return transit; weather affects installation only."""
    t, left, B = 0.0, g["n_total"], g["block_h"]
    while left > 0:
        n = min(n_v, left)
        t += Tp + g["transit_h"]
        need = n * g["install_h"]
        while need > 1e-9:
            k = int(t // B)
            end = (k + 1) * B
            if wx[k]:
                d = min(need, end - t)
                need -= d
                t += d
            else:
                t = end
        t += g["transit_h"]
        left -= n
    return t


def campaign():
    g = GRIDS["campaign"]
    e3 = {r["key"]: r for r in csv.DictReader(open(ROOT / g["e3_dir"] / "points.csv", encoding="utf-8"))}
    rows = []
    for sc, n_v, K in itertools.product(g["scen"], g["n_v"], g["K"]):
        occ = float(e3[f"port|{sc}|pull_in|occ|n{n_v}|K{K}|S1|H0"]["port_h"])
        fix = float(e3[f"fix|{sc}|pull_in|S1|R1|port{n_v}|K{K}"]["port_h"])
        for q in g["q"]:
            d_occ, d_fix = [], []
            for s in g["seeds"]:
                wx = weather(s, q, g["spell_blocks"], 20000)
                d_occ.append(campaign_len(occ, g, n_v, wx) / 24)
                d_fix.append(campaign_len(fix, g, n_v, wx) / 24)
            dd = sorted(a - b for a, b in zip(d_occ, d_fix))
            mean = lambda x: sum(x) / len(x)
            rows.append(dict(scen=sc, n_v=n_v, K=K, q=q, port_occ_h=round(occ, 3), port_fix_h=round(fix, 3), voyages=-(-g["n_total"] // n_v),
                             days_occ=round(mean(d_occ), 3), days_fix=round(mean(d_fix), 3), diff_mean=round(mean(dd), 3),
                             diff_p10=round(dd[len(dd) // 10], 3), diff_p90=round(dd[(9 * len(dd)) // 10], 3),
                             naive=round(-(-g["n_total"] // n_v) * (occ - fix) / 24, 3)))
    return rows


def config(part):
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="spatial", part=part, grid=GRIDS[part], base=WS.BASE, code=code,
               code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest(),
               networks={s: SY.NETWORK[s] for s in ("okpo", "yantai")})
    return cfg


def wcsv(path, rows):
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=list(GRIDS))
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = config(a.part)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_spatial_{a.part}_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    if a.part == "regime5":
        wcsv(out / "regime5.csv", regime5())
    elif a.part == "critical":
        wcsv(out / "critical_points.csv", critical())
    elif a.part == "codesign":
        rows, best, chosen = codesign()
        wcsv(out / "codesign.csv", rows)
        flat = []
        for b in best:
            r = dict(scen=b["scen"], n_v=b["n_v"], rate=b["rate"])
            for tag in ("best", "plain"):
                x = b[tag]
                r.update({f"{tag}_{k}": x[k] for k in ("K", "S", "lay", "mode", "lift", "hold", "pass_", "widen", "lstar_h")}, **{f"{tag}_cost": x[f"cost_{b['rate'] // 1000}k"]})
            for opt in ("hold", "pass_", "widen"):
                r[f"save_{opt}"] = b[f"save_{opt}"]
                w = b[f"with_{opt}"]
                r[f"with_{opt}"] = "" if w is None else f"K={w['K']} S={w['S']} {w['lay']} {w['mode']} {w['lift']} L*={w['lstar_h']}"
            flat.append(r)
        wcsv(out / "best.csv", flat)
        (out / "chosen.json").write_text(json.dumps(chosen, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    elif a.part == "campaign":
        wcsv(out / "campaign.csv", campaign())
    print(out)


if __name__ == "__main__":
    main()
