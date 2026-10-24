"""Report of the spatial additions: tables, draft figures and the numbers quoted in the report, built from the run directories (no
simulation; the Q = K step of the Table 7 exchange rate and L* only call the bound code).

Inputs: the sites, siteport, turn, reserve, reach, upsize, ablate, hphd, cdv, random runs, the analytic regime5, critical, codesign,
campaign runs and the turn-check directory (found by prefix, exactly one each); the committed directories of the E4-E7 batches (e4, e6,
e7, sens, report), the extra analyses (port, mix6, report) and the E1-E3 batches (e1).
Output results/windport_spatial_report_<first 12 hex digits of the SHA-256 of the inputs and this script>/: table_*.md / .csv, fig_*.png
(drafts, no maps), numbers.json, inputs.json.
Run: python experiments/windport_report_spatial.py
"""
import collections
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import matplotlib                                                # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402

import windport_runs as T                                        # noqa: E402

plt.rcParams.update({"font.family": ["Microsoft YaHei", "SimHei", "DejaVu Sans"], "axes.unicode_minus": False, "font.size": 8})
FIXED = dict(e4="runs/e4", e6="runs/e6", e7="runs/e7",
             sens="runs/sens", rep134="tables/e4_e7", port="runs/port_time",
             mix6="runs/mixed_e4", rep136="tables/extra", crit136="runs/critical")
NEW = ["sites", "siteport", "turn", "turngeo", "reserve", "reach", "upsize", "ablate", "hphd", "cdv", "random", "regime5", "critical", "codesign", "campaign"]
SCEN_ZH = dict(base="base", slow="1 km/h", longslow="long corridor + 1 km/h", lane="long single lane + 1 km/h", fastcrane="crane 0.5 h")
MODE_ZH = dict(on_road="roadside", pull_in="pull-in", side="side-by-side")
AXLE = dict(A=[160, 240], w=[18.75, 21.5, 25.0, 33.0])
CLS_ZH = dict(crane="crane", turnover="cradle turnover", fleet="fleet", road="road", prep="preparation time")


def i(x):
    return int(round(float(x)))


def fl(x):
    return None if x in ("", None) else float(x)


def one(prefix):
    """Run directory of the spatial additions (exactly one). The geometric turn check (windport_turn_sweep.py, has turn_extra.json) and
    the simulation --part turn (has points/) share a prefix and are told apart by content: prefix = "turngeo" takes the former, "turn"
    the latter."""
    pre = "turn" if prefix == "turngeo" else prefix
    ds = sorted(p for p in (ROOT / "results").glob(f"windport_spatial_{pre}_*") if p.is_dir())
    if pre == "turn":
        ds = [p for p in ds if (p / "turn_extra.json").exists() == (prefix == "turngeo")]
    assert len(ds) == 1, (prefix, ds)
    return ds[0]


def rd(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def wcsv(p, rows):
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)


def md(out, name, lines):
    (out / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def save(fig, out, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, metadata={"Software": None})
    (out / name).write_bytes(buf.getvalue())
    plt.close(fig)


def plateau(d):
    mx = max(d.values())
    return min(k for k, v in d.items() if v >= mx), mx


def pct(a, b):
    return f"{a / b:.1%}" if b else "-"


# ---------------------------------------------------------------- relaxed storage area
def sites(new, old, siteport, out, N):
    """new: sites of the spatial additions (relaxed, W″); old: E6 of the E4-E7 batches (one voyage, W1′)."""
    key = lambda r: (r["kind"], r["scen"], r["mode"], r["rule"], i(r["L"]), i(r["G"]), i(r["S"]), i(r["K"]))
    A, B = {key(r): r for r in old}, {key(r): r for r in new}
    assert set(A) == set(B)
    tab = []
    for site in ("okpo", "yantai"):
        for sc in ("base", "slow", "fastcrane"):
            for rule in ("fcfs", "convoy"):
                ks = [k for k in A if k[0] == f"map:{site}" and k[1] == sc and k[3] == rule]
                sa, sb = sum(i(A[k]["sim"]) for k in ks), sum(i(B[k]["sim"]) for k in ks)
                tab.append(dict(site=site, scen=sc, rule=rule, n=len(ks), sim_runs=sa, sim_multi=sb, change=pct(sb - sa, sa),
                                lower=sum(i(B[k]["sim"]) < i(A[k]["sim"]) for k in ks), higher=sum(i(B[k]["sim"]) > i(A[k]["sim"]) for k in ks),
                                tie_multi=pct(sum(i(B[k]["sim"]) == i(B[k]["w4"]) for k in ks), len(ks)),
                                road_multi=sum(B[k]["cls"] == "road" for k in ks), prep_multi=sum(B[k]["cls"] == "prep" for k in ks)))
    wcsv(out / "table_sites.csv", tab)
    L = ["# Relaxed storage area: one-voyage storage area (E6) vs a storage area holding three voyages (Okpo zone_trace_001 6.82 ha, Yantai zone_trace_030 5.04 ha)\n",
         "Total delivery over the same grid (cradle mode × L = 4, 6, 12, 24 h × K = 1–8 × S × G = 3, 24 h); the share at W″ and the W″ regimes are for the relaxed points.\n",
         "| Shipyard | Scenario | Dispatch | Points | Delivery: one voyage | Relaxed | Change | Points lower / higher | Relaxed at W″ | Relaxed road / preparation-time regime points |", "|---|---|---|---:|---:|---:|---:|---|---:|---|"]
    L += [f"| {t['site']} | {SCEN_ZH[t['scen']]} | {t['rule']} | {t['n']} | {t['sim_runs']} | {t['sim_multi']} | {t['change']} | {t['lower']} / {t['higher']} | "
          f"{t['tie_multi']} | {t['road_multi']} / {t['prep_multi']} |" for t in tab]
    # pull-in, L = 12, G = 24, FCFS: delivery vs K
    L += ["\n## L = 12 h, G = 24 h, FCFS, pull-in cradles: delivery vs K (one voyage → relaxed; W″ of the relaxed case in parentheses)\n"]
    rows = []
    for site in ("okpo", "yantai"):
        for sc in ("base", "slow", "fastcrane"):
            for Sn in range(0, min(4, T.NC[site]) + 1):
                ks = [(f"map:{site}", sc, "pull_in", "fcfs", 12, 24, Sn, K) for K in range(1, 9)]
                a, b = [i(A[k]["sim"]) for k in ks], [i(B[k]["sim"]) for k in ks]
                pa, pb = plateau(dict(zip(range(1, 9), a))), plateau(dict(zip(range(1, 9), b)))
                rows.append(dict(site=site, scen=sc, S=Sn, runs=a, multi=b, w4=[i(B[k]["w4"]) for k in ks], plat_runs=pa, plat_multi=pb))
    L += ["| Shipyard | Scenario | S | K = 1 … 8 | Plateau (K, piles) |", "|---|---|---:|---|---|"]
    L += [f"| {r['site']} | {SCEN_ZH[r['scen']]} | {r['S']} | " + " ".join(f"{x}→{y}({w})" for x, y, w in zip(r["runs"], r["multi"], r["w4"])) +
          f" | {r['plat_runs'][0]} ({r['plat_runs'][1]}) → {r['plat_multi'][0]} ({r['plat_multi'][1]}) |" for r in rows]
    # port time
    sp = {(r["kind"], r["st"], r["scen"], r["mode"], r["arr"], i(r["K"])): r for r in siteport if not r.get("hold")}
    sph = {(r["kind"], r["scen"], r["mode"], r["arr"], i(r["K"]), r["hold"]): r for r in siteport if r.get("hold")}
    L += ["\n## Port time for one vessel of 10 piles (h; FCFS / L*(10), crane open from G = 24 h)\n", "| Shipyard | Storage area | Scenario | Cradle | Lifting | K = 1 | 2 | 3 | 4 | 6 | 8 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    spt = []
    for site in ("okpo", "yantai"):
        for st in ("runs", "multi"):
            for sc in ("base", "slow"):
                for m in ("pull_in", "on_road"):
                    for arr in (["S0", "S1", "S1m", "S3", "S3m"] if site == "okpo" else ["S0", "S1", "S1m"]):
                        rs = [sp[(f"map:{site}", st, sc, m, arr, K)] for K in range(1, 9)]
                        spt += [dict(site=site, st=st, scen=sc, mode=m, arr=arr, K=K, hold="0", port_h=r["port_h"], lstar=r["lstar_lo"])
                                for K, r in zip(range(1, 9), rs)]
                        L.append(f"| {site} | {'one voyage' if st == 'runs' else 'three voyages'} | {SCEN_ZH[sc]} | {MODE_ZH[m]} | {arr} | " +
                                 " | ".join(f"{fl(rs[K - 1]['port_h']):.2f} / {fl(rs[K - 1]['lstar_lo']):.2f}" for K in (1, 2, 3, 4, 6, 8)) + " |")
    # relaxed storage area: sensitivity to gate holding places
    L += ["\n## Relaxed storage area: port time for one vessel of 10 piles with gate holding places Q_h = 0 / 1 / unlimited (h, FCFS; L*(10) as in the Q_h = 0 column)\n",
          "| Shipyard | Scenario | Cradle | Lifting | Q_h | K = 1 | 2 | 3 | 4 | 6 | 8 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for site in ("okpo", "yantai"):
        for sc in ("base", "slow"):
            for m in ("pull_in", "on_road"):
                for arr in (["S1", "S1m", "S3"] if site == "okpo" else ["S0", "S1", "S1m"]):
                    for h in ("0", "1", "inf"):
                        rs = [sp[(f"map:{site}", "multi", sc, m, arr, K)] if h == "0" else sph[(f"map:{site}", sc, m, arr, K, h)] for K in range(1, 9)]
                        spt += [dict(site=site, st="multi", scen=sc, mode=m, arr=arr, K=K, hold=h, port_h=r["port_h"], lstar=r["lstar_lo"])
                                for K, r in zip(range(1, 9), rs) if h != "0"]
                        L.append(f"| {site} | {SCEN_ZH[sc]} | {MODE_ZH[m]} | {arr} | {dict(inf='unlimited').get(h, h)} | " +
                                 " | ".join(f"{fl(rs[K - 1]['port_h']):.2f}" for K in (1, 2, 3, 4, 6, 8)) + " |")
    wcsv(out / "table_siteport.csv", spt)
    md(out, "table_sites.md", L)
    hk = lambda h, K, m="pull_in", arr="S1": fl((sp[("map:okpo", "multi", "base", m, arr, K)] if h == "0" else sph[("map:okpo", "base", m, arr, K, h)])["port_h"])
    N["okpo_hold"] = {f"{m}|{arr}|{h}|{K}": hk(h, K, m, arr) for m in ("pull_in", "on_road") for arr in ("S1", "S3") for h in ("0", "1", "inf")
                      for K in (1, 2, 4, 8)}
    okm = [r for r in rows if r["site"] == "okpo" and r["scen"] == "base" and r["S"] == 1][0]
    ytm = [r for r in rows if r["site"] == "yantai" and r["scen"] == "base" and r["S"] == 1][0]
    N["sites"] = dict(okpo_base_S1=dict(runs=okm["runs"], multi=okm["multi"], w4=okm["w4"]), yantai_base_S1=dict(runs=ytm["runs"], multi=ytm["multi"], w4=ytm["w4"]),
                      totals=tab, over=sum(1 for r in new if i(r["sim"]) > i(r["w4"])), check_bad=sum(1 for r in new if not i(r["check_ok"])),
                      tie=pct(sum(i(r["sim"]) == i(r["w4"]) for r in new), len(new)), n=len(new))
    return A, B


# ---------------------------------------------------------------- turning
def turn(tdir, rows, A, B, out, N):
    nodes, routes = rd(tdir / "turn.csv"), rd(tdir / "turn_routes.csv")
    L = ["# Turning: steering stops on the loading routes in Okpo and Yantai, swept-path check and alternative manoeuvres\n",
         "Sweep: the monopile turns about the junction from the incoming to the outgoing heading (sector), and a full circle (radius Lv/2 = 55 m); sample points within 8 m of the junction are ignored. Obstacles: buildings; water (dry docks, floating docks); other occupied areas "
         "(yards, assembly yards, buffers, steel stockyards, offshore fabrication yards, gantry-crane spans; the storage area of this site excepted).\n",
         "| Shipyard | Storage area | Turn nodes (incl. different turn directions) | Sector feasible: clear of buildings | + clear of water | + clear of other occupied areas | Full circle feasible (all three layers clear) | Routes (row × cradle × cradle mode) | Whole route sector clear of buildings | + water | + other occupied areas |",
         "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    tt = []
    for site in ("okpo", "yantai"):
        for st in ("runs", "multi"):
            ns = [n for n in nodes if n["site"] == site and n["storage"] == st]
            rs = [r for r in routes if r["site"] == site and r["storage"] == st]
            sb = lambda n, lay: all(i(n[f"sweep_{x}"]) == 0 for x in lay)
            row = dict(site=site, st=st, nodes=len(ns), ok_b=sum(sb(n, ["building"]) for n in ns), ok_bw=sum(sb(n, ["building", "water"]) for n in ns),
                       ok_all=sum(sb(n, ["building", "water", "other"]) for n in ns),
                       circ=sum(all(i(n[f"circle_{x}"]) == 0 for x in ("building", "water", "other")) for n in ns), routes=len(rs),
                       r_b=sum(i(r["ok_building"]) for r in rs), r_bw=sum(i(r["ok_water"]) for r in rs), r_all=sum(i(r["ok_other"]) for r in rs))
            tt.append(row)
            L.append(f"| {site} | {'one voyage' if st == 'runs' else 'three voyages'} | {row['nodes']} | {row['ok_b']} | {row['ok_bw']} | {row['ok_all']} | {row['circ']} | "
                     f"{row['routes']} | {row['r_b']} ({pct(row['r_b'], row['routes'])}) | {row['r_bw']} | {row['r_all']} |")
    # simulation with alternative manoeuvres
    by = {(r["kind"], r["st"], r["mode"], i(r["K"]), i(r["S"]), float(r["extra"])): r for r in rows}
    L += ["\n## Infeasible turns use an alternative manoeuvre (extra stop 600 s, 1,800 s): delivery (L = 12 h, G = 24 h, base, FCFS)\n",
          "| Shipyard | Storage area | Cradle | S | K = 1 … 8: original → +600 s → +1,800 s | Total |", "|---|---|---|---:|---|---|"]
    tot = collections.Counter()
    for site in ("okpo", "yantai"):
        for st in ("runs", "multi"):
            ref = A if st == "runs" else B
            for m in ("pull_in", "on_road"):
                for Sn in range(0, min(4, T.NC[site]) + 1):
                    k0 = [ref[(f"map:{site}", "base", m, "fcfs", 12, 24, Sn, K)] for K in range(1, 9)]
                    a = [i(x["sim"]) for x in k0]
                    b = [i(by[(f"map:{site}", st, m, K, Sn, 600.0)]["sim"]) for K in range(1, 9)]
                    c = [i(by[(f"map:{site}", st, m, K, Sn, 1800.0)]["sim"]) for K in range(1, 9)]
                    tot[(site, st, 0)] += sum(a)
                    tot[(site, st, 600)] += sum(b)
                    tot[(site, st, 1800)] += sum(c)
                    if m == "pull_in" and Sn in (0, 1):
                        L.append(f"| {site} | {'one voyage' if st == 'runs' else 'three voyages'} | {MODE_ZH[m]} | {Sn} | " + " ".join(f"{x}/{y}/{z}" for x, y, z in zip(a, b, c)) +
                                 f" | {sum(a)} → {sum(b)} → {sum(c)} |")
    L.append("\nTotal (both cradle modes, all S, K): " + "; ".join(f"{s} {'one voyage' if st == 'runs' else 'three voyages'} {tot[(s, st, 0)]} → {tot[(s, st, 600)]} ({pct(tot[(s, st, 600)] - tot[(s, st, 0)], tot[(s, st, 0)])})"
                                                    f" → {tot[(s, st, 1800)]} ({pct(tot[(s, st, 1800)] - tot[(s, st, 0)], tot[(s, st, 0)])})"
                                                    for s in ("okpo", "yantai") for st in ("runs", "multi")))
    md(out, "table_turn.md", L)
    wcsv(out / "table_turn.csv", tt)
    N["turn"] = dict(geometry=tt, totals={f"{a}|{b}|{c}": v for (a, b, c), v in tot.items()}, over=sum(1 for r in rows if i(r["sim"]) > i(r["w4"])),
                     check_bad=sum(1 for r in rows if not i(r["check_ok"])))


# ---------------------------------------------------------------- sharing with block transport
def reserve(rows, A, B, out, N):
    by = {(r["kind"], r["st"], r["mode"], i(r["K"]), i(r["S"]), float(r["f"])): r for r in rows}
    L = ["# Road section shared with block transport: the shared section reserves f of every 2 h for block transport (L = 12 h, G = 24 h, base, FCFS)\n",
         "Shared section = among the sections that every loading route passes, that loaded vehicles hold exclusively and that are not on the quay apron or at stops, the one with the longest loaded occupancy (windport.sim4.reserve_road).\n",
         "| Shipyard | Storage area | Shared section (t_ℓ s) | f = 0 | 10% | 25% | 50% | Points where W″ tightens (f > 0) |", "|---|---|---|---:|---:|---:|---:|---:|"]
    tab = []
    for site in ("okpo", "yantai"):
        for st in ("runs", "multi"):
            ref = A if st == "runs" else B
            rs = [r for r in rows if r["kind"] == f"map:{site}" and r["st"] == st]
            road = sorted({(r["reserve_res"], r["reserve_tl"]) for r in rs})
            s0 = sum(i(ref[(f"map:{site}", "base", r["mode"], "fcfs", 12, 24, i(r["S"]), i(r["K"]))]["sim"]) for r in rs if float(r["f"]) == 0.1)
            sf = {f: sum(i(r["sim"]) for r in rs if float(r["f"]) == f) for f in (0.1, 0.25, 0.5)}
            tight = sum(1 for r in rs if i(r["w4"]) < i(r["wprime"]))
            tab.append(dict(site=site, st=st, road=road, f0=s0, **{f"f{f}": v for f, v in sf.items()}, tight=tight, n=len(rs)))
            L.append(f"| {site} | {'one voyage' if st == 'runs' else 'three voyages'} | {'; '.join(a.split('|')[-1] + f' ({b})' for a, b in road)} | {s0} | "
                     + " | ".join(f"{sf[f]} ({pct(sf[f] - s0, s0)})" for f in (0.1, 0.25, 0.5)) + f" | {tight} / {len(rs)} |")
    md(out, "table_reserve.md", L)
    wcsv(out / "table_reserve.csv", tab)
    N["reserve"] = dict(tab=tab, over=sum(1 for r in rows if i(r["sim"]) > i(r["w4"])), check_bad=sum(1 for r in rows if not i(r["check_ok"])))


# ---------------------------------------------------------------- Table 7 exchange rate under two layouts and the best lifting mode
def rates(N_):
    k1 = [N_[(S + 1, 1)] - N_[(S, 1)] for S in range(1, 6)]
    top = [N_[(S + 1, 10)] - N_[(S, 10)] for S in range(1, 6)]
    eq = next((S for S in range(1, 7) if N_[(S, 1)] >= N_[(1, 2)]), None)
    return dict(per_cradle_K1=round(sum(k1) / 5, 2), second_set=eq if eq is not None else ">6", n11=N_[(1, 1)], n12=N_[(1, 2)],
                per_cradle_plat=round(sum(top) / 5, 2), n1_10=N_[(1, 10)], n6_10=N_[(6, 10)])


def reach(rows, e4, mix6, out, N):
    grid = collections.defaultdict(dict)                 # (layout, scenario, cradle mode, lifting) → {(S, K): piles}
    for r in e4:
        if r["kind"] == "A1" and i(r["L"]) == 12 and i(r["G"]) == 24 and r["rule"] == "fcfs" and r["scen"] in ("base", "lane"):
            grid[("tandem_all", r["scen"], r["mode"], "cradle" if i(r["S"]) else "direct")][(i(r["S"]), i(r["K"]))] = i(r["sim"])
    for r in mix6:
        if r["kind"] == "A1" and i(r["L"]) == 12 and i(r["G"]) == 24 and r["rule"] == "fcfs":
            grid[("tandem_all", r["scen"], r["mode"], "mixed")][(i(r["S"]), i(r["K"]))] = i(r["sim"])
    for r in rows:
        lay = "side" if r["lay"] == "side" else f"tandem_{r['reach']}" + (f"|{r['disp']}" if r.get("disp") else "")
        grid[(lay, r["scen"], r["mode"], r["lift"])][(i(r["S"]), i(r["K"]))] = i(r["sim"])
    for rc in ("1_3600", "2_1800", "2_3600", "2_7200"):                # max over the three dispatch variants
        for sc in ("base", "lane"):
            for m in ("pull_in", "on_road"):
                for lf in ("cradle", "mixed"):
                    gs = [grid[(f"tandem_{rc}" + d, sc, m, lf)] for d in ("", "|finish", "|prestage")]
                    grid[(f"tandem_{rc}|best", sc, m, lf)] = {k: max(g_[k] for g_ in gs) for k in gs[0]}
    tab, iso = [], []
    rcs = ["1_3600", "2_1800", "2_3600", "2_7200"]
    lays = ["side", "tandem_all"] + [f"tandem_{rc}{d}" for rc in rcs for d in ("", "|finish", "|prestage", "|best")]
    RZ = {"1_3600": "S_r = 1, t_sh = 1 h", "2_1800": "S_r = 2, t_sh = 0.5 h", "2_3600": "S_r = 2, t_sh = 1 h", "2_7200": "S_r = 2, t_sh = 2 h"}
    DZ = {"": "earliest lift start", "|finish": "earliest lift finish", "|prestage": "far cradles pre-stage only", "|best": "max of three dispatch variants"}
    LAY_ZH = dict(tandem_all="tandem, all reachable (E4 / mix6)", side="side-by-side (all reachable; main case)",
                  **{f"tandem_{rc}{d}": f"tandem {RZ[rc]}, {DZ[d]}" for rc in rcs for d in DZ})
    for lay in lays:
        for sc in ("base", "lane"):
            for m in (["side"] if lay == "side" else ["pull_in", "on_road"]):
                c, x = grid[(lay, sc, m, "cradle")], grid[(lay, sc, m, "mixed")]
                best = {k: max(c[k], x[k]) for k in c}
                for lift, G_ in (("cradle", c), ("mixed", x), ("best", best)):
                    tab.append(dict(layout=lay, scen=sc, mode=m, lift=lift, **rates(G_)))
                for (S_, K), v in sorted(best.items()):
                    iso.append(dict(layout=lay, scen=sc, mode=m, S=S_, K=K, best=v, cradle=c[(S_, K)], mixed=x[(S_, K)],
                                    best_mode="mixed" if x[(S_, K)] > c[(S_, K)] else ("cradle" if c[(S_, K)] > x[(S_, K)] else "tie")))
    wcsv(out / "table7_rate.csv", tab)
    wcsv(out / "fig7_iso.csv", iso)
    L = ["# Table 7 exchange rate: two cradle layouts × crane reach × lifting mode × quay-bay dispatch (L = 12 h, G = 24 h, FCFS; with dispatch variants)\n",
         "Main case: side-by-side cradles (all reachable); tandem with reach as a sensitivity. Dispatch for tandem with reach: earliest lift start (original rule), earliest lift finish (far cradles count t_sh), far cradles only pre-stage before the window; "
         "\"max of three dispatch variants\" takes the largest count of the three for each (S, K).\n",
         "Piles / cradle (K = 1) = average gain per extra cradle over S = 1→6; second set ≈ cradles = number of cradles at which K = 1 catches up with K = 2, S = 1; piles / cradle (plateau) = the same average at K = 10. "
         "\"Best\" = for each (S, K) the larger of cradle and mixed lifting (x = 0), i.e. relative to the best lifting mode at each K.\n",
         "| Layout | Scenario | Cradle mode | Lifting | Piles / cradle (K = 1) | Second set ≈ cradles | K = 1 / K = 2 (S = 1) | Piles / cradle (plateau) | Plateau S = 1 → 6 |", "|---|---|---|---|---:|---|---|---:|---|"]
    L += [f"| {LAY_ZH[t['layout']]} | {SCEN_ZH[t['scen']]} | {MODE_ZH[t['mode']]} | {dict(cradle='cradle', mixed='mixed', best='best')[t['lift']]} | {t['per_cradle_K1']} | "
          f"{t['second_set']} | {t['n11']} / {t['n12']} | {t['per_cradle_plat']} | {t['n1_10']} → {t['n6_10']} |" for t in tab]
    md(out, "table7_rate.md", L)
    # Fig. 7 draft: pull-in (side-by-side as itself), best lifting, piles vs K (S = 1, 3, 6)
    fig, ax = plt.subplots(2, 3, figsize=(12, 6), sharey="row")
    for a, sc in enumerate(("base", "lane")):
        for b, lay in enumerate(("side", "tandem_2_3600", "tandem_2_3600|best")):
            x = ax[a][b]
            m = "side" if lay == "side" else "pull_in"
            for S_, col in zip((1, 3, 6), ("C0", "C1", "C2")):
                c, mx = grid[(lay, sc, m, "cradle")], grid[(lay, sc, m, "mixed")]
                x.plot(range(1, 11), [max(c[(S_, K)], mx[(S_, K)]) for K in range(1, 11)], "-o", color=col, ms=3, label=f"S = {S_} (best)")
                x.plot(range(1, 11), [c[(S_, K)] for K in range(1, 11)], ":", color=col, lw=0.8)
            x.set_title(f"{LAY_ZH[lay]}, {SCEN_ZH[sc]}", fontsize=7)
            x.set_xlabel("K")
    ax[0][0].legend(fontsize=6)
    fig.suptitle("Fig. 7 (draft) two cradle layouts: solid = max of cradle and mixed lifting, dotted = cradle", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, out, "fig7_layouts.png")
    pick = lambda lay, sc, m, lf: next(t for t in tab if (t["layout"], t["scen"], t["mode"], t["lift"]) == (lay, sc, m, lf))
    N["rate"] = {f"{lay}|{sc}|{lf}": pick(lay, sc, "side" if lay == "side" else "pull_in", lf) for lay in lays for sc in ("base", "lane") for lf in ("cradle", "best")}
    N["reach_disp_tight"] = {d: sum(1 for r in rows if r.get("disp", "") == d and i(r["w4"]) < i(r["wprime"])) for d in ("", "finish", "prestage")}
    N["reach_over"] = sum(1 for r in rows if i(r["sim"]) > i(r["w4"]))
    N["reach_tight"] = sum(1 for r in rows if i(r["w4"]) < i(r["wprime"]))
    N["reach_check_bad"] = sum(1 for r in rows if not i(r["check_ok"]))
    return grid


# ---------------------------------------------------------------- upsizing staircase
def upsize(rows, e7, out, N):
    lev = T.E7LEV
    old = {(r["scen"], r["mode"], r["lev"], i(r["S"]), i(r["K"])): i(r["sim"]) for r in e7}
    new = {}
    for r in rows:
        if r["mode"] in ("pull_in", "side"):
            k = (r["lay"], r["scen"], r["lev"], i(r["S"]), i(r["K"]))
            new[k] = max(new.get(k, 0), i(r["sim"]))            # tandem with reach: max over the three dispatch variants
    tab = []
    for A_ in AXLE["A"]:
        for w in AXLE["w"]:
            for lv, x in lev.items():
                a = math.ceil(x["t"] / w - 1e-9)
                K = min(6, A_ // a)
                r = dict(A=A_, w=w, lev=lv, Lv=x["Lv"], B=x["B"], t=x["t"], axles=a, K=K)
                for sc in ("base", "lane"):
                    g = lambda d, k: d.get(k, 0) if K >= 1 else 0
                    r.update({f"{sc}_tandem_S1": g(old, (sc, "pull_in", lv, 1, K)), f"{sc}_tandem_S3": g(old, (sc, "pull_in", lv, 3, K)),
                              f"{sc}_reach_S3": g(new, ("tandem", sc, lv, 3, K)), f"{sc}_side_S1": g(new, ("side", sc, lv, 1, K)),
                              f"{sc}_side_S3": g(new, ("side", sc, lv, 3, K))})
                tab.append(r)
    wcsv(out / "table_upsize.csv", tab)
    L = ["# Upsizing: fleet staircase over (A, w, m) and two cradle layouts\n",
         "Road-specific finding first: monopile diameters of 11.5 and 12 m exceed the 10 m base single lane, so the single lane must be at least as wide as the diameter (engineering check; in the occupancy model the loaded width is min(road width + clearance, B + clearance), "
         "so a diameter above the road width only shows as exclusive use of that section and is not flagged as infeasible, which is why this batch and E7 both use a 12 m single lane). The remaining steps come from fleet arithmetic: a set needs ⌈m/w⌉ axle lines, an axle pool A forms K = ⌊A/⌈m/w⌉⌋ sets (at most 6), "
         "the fixed-time representation gives the same steps; the road only decides the piles at the same K when the monopile gets longer (E7: at most 1 pile difference). w = 18.75, 25 t (E7) and 21.5 t (Baltic Power), 33 t (Moray West).\n",
         "| Axle pool A | w (t/axle line) | Monopile (length / diameter / mass) | Axle lines per set | K | Base: tandem S = 1 / S = 3 / tandem with reach S = 3 (max of three dispatch variants) / side-by-side S = 1 / side-by-side S = 3 | Long single lane: as left |",
         "|---:|---:|---|---:|---:|---|---|"]
    for r in tab:
        L.append(f"| {r['A']} | {r['w']} | {r['Lv']:.0f} m / {r['B']} m / {r['t']} t | {r['axles']} | {r['K']} | "
                 f"{r['base_tandem_S1']} / {r['base_tandem_S3']} / {r['base_reach_S3']} / {r['base_side_S1']} / {r['base_side_S3']} | "
                 f"{r['lane_tandem_S1']} / {r['lane_tandem_S3']} / {r['lane_reach_S3']} / {r['lane_side_S1']} / {r['lane_side_S3']} |")
    md(out, "table_upsize.md", L)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for b, A_ in enumerate(AXLE["A"]):
        x = ax[b]
        for w, col in zip(AXLE["w"], ("C0", "C1", "C2", "C3")):
            ts = [t for t in tab if t["A"] == A_ and t["w"] == w]
            x.step([t["t"] for t in ts], [t["K"] for t in ts], where="post", color=col, label=f"w = {w} t")
        x.set_title(f"Axle pool A = {A_}", fontsize=8)
        x.set_xlabel("Monopile mass m (t)")
        x.set_ylabel("SPMT sets K = min(6, ⌊A/⌈m/w⌉⌋)")
        x.legend(fontsize=6)
    fig.suptitle("Fleet staircase (draft): the steps come only from axle arithmetic", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, out, "fig_upsize_staircase.png")
    N["upsize"] = dict(K={f"{t['A']}|{t['w']}|{t['lev']}": t["K"] for t in tab}, over=sum(1 for r in rows if i(r["sim"]) > i(r["w4"])))


# ---------------------------------------------------------------- component ablation
def ablate(rows, port, e4, out, N):
    from windport import bound3 as B3
    from dataclasses import replace
    full_p = {(r["scen"], r["mode"], r["arr"], i(r["K"])): fl(r["port_h"]) for r in port
              if r["rep"] == "fcfs" and r["hold"] == "0" and i(r["n_v"]) == 10}
    full_w = {(r["scen"], r["mode"], i(r["S"]), i(r["K"])): i(r["sim"]) for r in e4
              if r["kind"] == "A1" and i(r["L"]) == 12 and i(r["G"]) == 24 and r["rule"] == "fcfs"}
    ab_p = {(r["step"], r["scen"], r["mode"], r["arr"], i(r["K"])): fl(r["port_h"]) for r in rows if r["what"] == "port"}
    ab_w = {(r["step"], r["scen"], r["mode"], i(r["S"]), i(r["K"])): i(r["sim"]) for r in rows if r["what"] == "win"}
    tab = []
    for sc in T.SC5:
        ks = [(sc, m, a, K) for m in T.MODES for a in ("S0", "S1", "S1m", "S3") for K in range(1, 9)]
        prev = {k: full_p[k] for k in ks}
        row = dict(scen=sc, what="Port time n_v = 10 (h)", full_mean=round(sum(prev.values()) / len(ks), 3))
        for st in ("s1", "s2", "s3", "cf"):
            cur = {k: ab_p[(st,) + k] for k in ks}
            d = [cur[k] - full_p[k] for k in ks]
            row.update({f"{st}_mean": round(sum(cur.values()) / len(ks), 3), f"{st}_maxdiff": round(min(d), 3), f"{st}_changed": sum(abs(x) > 1e-6 for x in d)})
        tab.append(row)
    for sc in ("base", "lane"):
        ks = [(sc, m, S_, K) for m in T.MODES for S_ in (0, 1, 3) for K in range(1, 11)]
        row = dict(scen=sc, what="Window delivery L = 12 h (piles, total)", full_mean=sum(full_w[k] for k in ks))
        for st in ("s1", "s2", "s3", "cf"):
            d = [ab_w[(st,) + k] - full_w[k] for k in ks]
            row.update({f"{st}_mean": sum(ab_w[(st,) + k] for k in ks), f"{st}_maxdiff": max(d), f"{st}_changed": sum(x != 0 for x in d)})
        tab.append(row)
    # step 4: the bound takes Q = K (instead of the geometric quay-zone Q)
    q4 = []
    for sc in ("base", "lane"):
        for m in T.MODES:
            for S_ in (0, 1, 3):
                for K in range(1, 11):
                    c = T.cfg_of("e4", T.enc(dict(kind="A1", scen=sc, mode=m, lift=T.lift_of(S_), rule="fcfs", L=12, K=K, S=S_, G=24)))
                    w = B3.wprime_parts(c)
                    f = B3.wprime_fn(c, w)
                    wq = dict(w, P=replace(w["P"], Q=K), bm=[K] * len(w["bm"]))
                    fq = B3.wprime_fn(c, wq)
                    L_ = 12 * 3600.0
                    q4.append(dict(scen=sc, mode=m, S=S_, K=K, sim=full_w[(sc, m, S_, K)], wprime=f(L_), wprime_QK=fq(L_)))
    for sc in ("base", "lane"):
        rs = [r for r in q4 if r["scen"] == sc]
        tab.append(dict(scen=sc, what="Step 4 Q = K: W′ total → with Q = K (points at bound → )", full_mean=sum(r["wprime"] for r in rs),
                        s4_mean=sum(r["wprime_QK"] for r in rs), s4_changed=sum(r["wprime_QK"] != r["wprime"] for r in rs),
                        tie_full=sum(r["sim"] == r["wprime"] for r in rs), tie_QK=sum(r["sim"] == r["wprime_QK"] for r in rs)))
    lq = []
    for sc in ("base", "lane"):
        c = dict(geo=dict(kind="A1", n_cradles=6, cradle_mode="pull_in", **T.SCEN[sc].get("geo", {})), p=dict(T.SCEN[sc].get("p", {})), S=1, K=2,
                 lift="cradle", horizon_h=224, cal=dict(crane=[[24, 224]]), n_load=10, hold=0, rule="fcfs")
        w = B3.wprime_parts(c)
        lo = B3.lstar(B3.wprime_fn(c, w), 10)[0] / 3600
        lo_q = B3.lstar(B3.wprime_fn(c, dict(w, P=replace(w["P"], Q=8), bm=[8] * len(w["bm"]))), 10)[0] / 3600
        lq.append(dict(scen=sc, lstar=round(lo, 3), lstar_QK=round(lo_q, 3)))
    wcsv(out / "table_ablate.csv", tab)
    wcsv(out / "table_ablate_q.csv", q4)
    L = ["# Component ablation: switch off cumulatively (s1) loaded steering stops and junction sweep, (s2) load-dependent loaded length, (s3) the segment-level network (replaced by the cut as a single resource), (step 4) Q = K in the bound\n",
         "Full model: port time from the port points of the extra analyses (FCFS, Q_h = 0), delivery from E4. Port time: mean over the 64 cells five scenarios × cradle mode × S0, S1, S1m, S3 × K = 1–8, "
         "the minimum difference to the full model (negative = faster) and the number of changed cells; delivery: total over the 60 cells base / long single lane × cradle mode × S = 0, 1, 3 × K = 1–10, the largest increase and the number of changed cells.\n",
         "Long corridor + 1 km/h and long single lane + 1 km/h are identical cell by cell in the full model and in every step (straight passage through junctions has no effect), so the two rows have the same values. cf = the cut as a single resource applied directly to the full model (without first switching off steering "
         "or changing L_v): the attribution of a sequential ablation depends on the order, and cf gives another order.\n",
         "| Scenario | Quantity | Full | s1: value / max diff / changed | s2 | s3 | cf |", "|---|---|---:|---|---|---|---|"]
    for t in tab:
        if "s1_mean" in t:
            L.append(f"| {SCEN_ZH[t['scen']]} | {t['what']} | {t['full_mean']} | " + " | ".join(f"{t[f'{s}_mean']} / {t[f'{s}_maxdiff']} / {t[f'{s}_changed']}" for s in ("s1", "s2", "s3", "cf")) + " |")
    L += ["\nStep 4 (bound only): Q = K instead of the geometric quay-zone Q.\n", "| Scenario | W′ total (60 cells) | With Q = K | Changed cells | Cells at bound: geometric Q → Q = K | L*(10) (S = 1, K = 2, h): geometric Q → Q = K |",
          "|---|---:|---:|---:|---|---|"]
    for t, l_ in zip([t for t in tab if "s4_mean" in t], lq):
        L.append(f"| {SCEN_ZH[t['scen']]} | {t['full_mean']} | {t['s4_mean']} | {t['s4_changed']} | {t['tie_full']} → {t['tie_QK']} | {l_['lstar']} → {l_['lstar_QK']} |")
    md(out, "table_ablate.md", L)
    N["ablate"] = dict(tab=tab, lstar_q=lq, check_bad=sum(1 for r in rows if not i(r["check_ok"])))


# ---------------------------------------------------------------- jacking / set-down up to 2 h
def hphd(rows, sens, out, N):
    assert all(r["sub"] == T.dec(r["key"])["sub"] for r in rows)    # the regime sub-type is named prep_sub, so the sub column is the sub-grid
    base = {}
    for r in sens:
        if r["par"] == "none":
            k = (r["sub"], r["scen"], r["mode"], r["L"], r["K"], r["S"], r["G"], r.get("rep", ""))
            base[k] = r
    tab = []
    for lv in ("5400", "7200", "kas"):
        for sub in ("e1", "e4", "e3"):
            for sc in ("base", "lane"):
                rs = [r for r in rows if r["lv"] == lv and r["sub"] == sub and r["scen"] == sc]
                if sub == "e3":
                    for rep in ("occ", "fix"):
                        q = [r for r in rs if r["rep"] == rep]
                        b = [fl(base[(sub, r["scen"], r["mode"], "", r["K"], r["S"], r["G"], rep)]["port_h"]) for r in q]
                        tab.append(dict(lv=lv, sub=f"e3 {rep}", scen=sc, n=len(q), base=round(sum(b) / len(b), 3), val=round(sum(fl(r["port_h"]) for r in q) / len(q), 3)))
                else:
                    b = [i(base[(sub, r["scen"], r["mode"], r["L"], r["K"], r["S"], r["G"], "")]["sim"]) for r in rs]
                    tab.append(dict(lv=lv, sub=sub, scen=sc, n=len(rs), base=sum(b), val=sum(i(r["sim"]) for r in rs),
                                    tie=pct(sum(i(r["sim"]) == i(r["w4"]) for r in rs), len(rs))))
    wcsv(out / "table_hphd.csv", tab)
    LV = {"5400": "h_p = h_d = 1.5 h", "7200": "h_p = h_d = 2 h", "kas": "Rønne handling h_p = 2 h, h_d = 0.5 h"}
    L = ["# Jacking / set-down extended to 2 h (extra rows for Appendix C)\n", "Base = par = none of Appendix C (h_p = h_d = 0.5 h). E1, E4: total delivery; E3: mean port time for one vessel of 10 piles (h, S = 1, K = 1–8).\n",
          "| Level | Sub-grid | Scenario | Points | Base | This level | This level at W″ |", "|---|---|---|---:|---:|---:|---:|"]
    L += [f"| {LV[t['lv']]} | {t['sub']} | {SCEN_ZH[t['scen']]} | {t['n']} | {t['base']} | {t['val']} | {t.get('tie', '')} |" for t in tab]
    md(out, "table_hphd.md", L)
    N["hphd"] = dict(tab=tab, over=sum(1 for r in rows if r.get("w4") not in ("", None) and i(r["sim"]) > i(r["w4"])),
                     check_bad=sum(1 for r in rows if not i(r["check_ok"])))


# ---------------------------------------------------------------- five regimes
def regime5(rows, out, N):
    c = collections.Counter()
    tie = collections.defaultdict(lambda: [0, 0])
    sub = collections.Counter()
    nat = collections.Counter()
    for r in rows:
        main = r["lift"] != "mixed"
        if main:
            c[(r["scen"], r["cls"])] += 1
            nat[(r["scen"], r["nature"])] += 1
            if r["cls"] == "prep":
                sub[(r["scen"], r["sub"])] += 1
        tie[(r["cls"], main)][0] += 1
        tie[(r["cls"], main)][1] += i(r["sim"]) == i(r["wprime"])
    L = ["# Five regimes: the A1 points of E1 classified by the W′ term that actually binds (windport.bound4.classify)\n",
         "Crane = interface term; cradle turnover; fleet = F; road = C, Z, Π_S (within the window); preparation time = the preparation term binds strictly (W′ below all window terms), sub-types Π_F (fleet), Π_C (cut), Π_Z (quay zone), Π_S (chain cut). "
         "Ties are assigned in the order crane, cradle turnover, fleet, road (road counts only when it binds strictly or ties with terms other than fleet). Also given is the classification \"by nature\": Π_F in preparation time goes to fleet, the rest to road.\n",
         "## Main lifting rule (cradle; direct lifting for S = 0): points per scenario (1,152 points / scenario)\n", "| Scenario | Crane | Cradle turnover | Fleet | Road | Preparation time (sub-types) | By nature: fleet / road |", "|---|---:|---:|---:|---:|---|---|"]
    for sc in ("base", "slow", "longslow", "lane", "fastcrane"):
        subs = "; ".join(f"{k[1]} {v}" for k, v in sorted(sub.items()) if k[0] == sc)
        L.append(f"| {SCEN_ZH[sc]} | {c[(sc, 'crane')]} | {c[(sc, 'turnover')]} | {c[(sc, 'fleet')]} | {c[(sc, 'road')]} | {c[(sc, 'prep')]} ({subs}) | "
                 f"{nat[(sc, 'fleet')]} / {nat[(sc, 'road')]} |")
    L += ["\n## Share at the bound by regime (points with simulation = W′)\n", "| Regime | Main rule: points / at bound | Mixed lifting: points / at bound |", "|---|---|---|"]
    for k in ("crane", "turnover", "fleet", "road", "prep"):
        a, b = tie[(k, True)], tie[(k, False)]
        L.append(f"| {CLS_ZH[k]} | {a[0]} / {pct(a[1], a[0])} | {b[0]} / {pct(b[1], b[0])} |")
    md(out, "table_regime5.md", L)
    fig_rows = [r for r in rows if r["mode"] == "pull_in" and i(r["G"]) == 3 and i(r["L"]) in (4, 12) and r["lift"] != "mixed"]
    wcsv(out / "fig_regime5.csv", [dict(scen=r["scen"], L=r["L"], K=r["K"], S=r["S"], cls=r["cls"], sub=r["sub"], nature=r["nature"], binding=r["binding"],
                                        sim=r["sim"], wprime=r["wprime"]) for r in fig_rows])
    col = dict(crane="#C9DCEF", turnover="#BBBBBB", fleet="#F6DDB0", road="#D9928D", prep="#B7D7A8")
    Ss = [0, 1, 2, 3, 4, 6]
    fig, axs = plt.subplots(2, 5, figsize=(13, 5.5), sharex=True, sharey=True)
    for a, L_ in enumerate((4, 12)):
        for b, sc in enumerate(("base", "slow", "longslow", "lane", "fastcrane")):
            ax = axs[a][b]
            for r in fig_rows:
                if r["scen"] == sc and i(r["L"]) == L_:
                    K, S_ = i(r["K"]), Ss.index(i(r["S"]))
                    ax.add_patch(plt.Rectangle((K - 0.5, S_ - 0.5), 1, 1, facecolor=col[r["nature"]], lw=0,
                                               hatch="///" if r["cls"] == "prep" else None, edgecolor="#555555"))
                    ax.text(K, S_, r["sim"], ha="center", va="center", fontsize=6)
            ax.set_xlim(0.5, 6.5)
            ax.set_ylim(-0.5, 5.5)
            ax.set_yticks(range(6), [str(s) for s in Ss])
            ax.set_title(f"{SCEN_ZH[sc]}, L = {L_} h", fontsize=7)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=col[k], label=CLS_ZH[k]) for k in ("crane", "turnover", "fleet", "road")]
               + [Patch(facecolor="white", edgecolor="#555555", hatch="///", label="preparation term binds strictly")], loc="lower center", ncol=5)
    fig.suptitle("Regime map (draft): coloured by nature (Π_F to fleet; Π_C, Π_Z, Π_S to road), hatched where the preparation term binds strictly; A1, pull-in, G = 3 h; cell value = simulated delivery", fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    save(fig, out, "fig_regime5.png")
    N["regime5"] = {f"{k[0]}|{k[1]}": v for k, v in c.items()}
    N["regime5_tie"] = {f"{k[0]}|{'main' if k[1] else 'mixed'}": v for k, v in tie.items()}


# ---------------------------------------------------------------- new points for Fig. 12
def critical(rows, out, N):
    L = ["# New points for Fig. 12: Okpo and Yantai with relaxed storage areas, and real ports located by public figures\n",
         "τ_cut = t_ℓ + t_e (round trip over the cut), τ_zone1 = t_ℓ + d_q + t_e^occ (one set at a time in the quay zone), τ_W (the quay-zone term of W′ itself); τ/p > 1 means the road-limited side (criterion 8 of the extra analyses). "
         "For real ports whose single-lane length is not published, the interval is given by the two ends, single lane 0 and 100% of the route.\n",
         "| Object | Storage area | Scenario | Cradle | p (h) | Alternative turn (s) | Route m | Speed km/h | Cut | τ_cut/p | τ_zone1/p | τ_W/p |", "|---|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|"]
    for r in rows:
        if r["kind"] == "site" and float(r["turn_extra"]) in (0.0, 1800.0):
            L.append(f"| {r['name']} | {'one voyage' if r['storage'] == 'runs' else 'three voyages'} | {SCEN_ZH[r['scen']]} | {MODE_ZH[r['mode']]} | {r['p']} | {r['turn_extra']} | {r['route_m']} | "
                     f"{float(r['v']):.1f} | {r['res'].split('|')[-1]} | {r['ratio_cut']} | {r['ratio_zone1']} | {r['ratio_w']} |")
    L += ["\n| Real port (source) | Route m | Speed km/h | Single-lane share of route | Cradle | τ_cut/p | τ_zone1/p | τ_W/p |", "|---|---:|---:|---:|---|---:|---:|---:|"]
    for r in rows:
        if r["kind"] == "port":
            L.append(f"| {r['name']} | {r['route_m']} | {r['v']} | {float(r['lane_frac']):.0%} | {MODE_ZH[r['mode']]} | {r['ratio_cut']} | {r['ratio_zone1']} | {r['ratio_w']} |")
    L += ["\nThe other ports (Eemshaven, Esbjerg, Vlissingen, the port on the Elbe estuary, Lindø, Taranto, Rostock, Ostend, Nigg, Ferrol) have **no published** storage-to-quay distance or single-lane length "
          "(port list and citations: see the manuscript); Fig. 12 lists them as \"not published\" without points."]
    md(out, "table_critical_points.md", L)
    wcsv(out / "fig12_points.csv", rows)
    # Fig. 12 draft: critical single-lane length ℓ*(v) of the extra analyses (p = 1 h) and the ports located by public figures;
    # where the single-lane length is not published, a vertical line from 0 to the route length
    cr = [r for r in rd(ROOT / "results" / FIXED["crit136"] / "critical.csv") if r["part"] == "longrun" and r["p"] == "1.0"]
    fig, ax = plt.subplots(figsize=(6, 4))
    for m, ls in (("pull_in", "-"), ("on_road", "--")):
        q = sorted((float(r["v"]), r) for r in cr if r["mode"] == m)
        for k, col, lab in (("ell_cut", "C0", "τ_cut = p"), ("ell_zone1", "C3", "τ_zone1 = p")):
            ax.plot([v for v, r in q if r[k]], [float(r[k]) for v, r in q if r[k]], ls, color=col, lw=1, label=f"{lab} ({MODE_ZH[m]})")
    for name, mk, dx in (("Rønne (Kassels, Appendix D)", "o", -0.06), ("Rønne electric SPMT trial (Baltica 2)", "s", 0.06)):
        for r in rows:
            if r["kind"] == "port" and r["name"] == name and r["mode"] == "pull_in" and float(r["lane_frac"]) == 1.0:
                v = float(r["v"]) + dx
                ax.plot([v, v], [0, float(r["route_m"])], color="k", lw=1.2)
                ax.plot([v], [float(r["route_m"])], mk, color="k", ms=5, label=None)
    ax.set_xlabel("Loaded speed (km/h)")
    ax.set_ylabel("Single-lane length (m)")
    ax.set_ylim(0, 3000)
    ax.legend(fontsize=6)
    ax.set_title("Fig. 12 (draft): lines = critical single-lane length (p = 1 h); vertical lines = ports located by public figures, 0 to route length where the single-lane length is not published\n"
                 "○ Rønne Kassels model 250 m; □ Baltica 2 trial 815 m (the source does not say whether this is the full storage-to-quay route)", fontsize=7)
    fig.tight_layout()
    save(fig, out, "fig12_critical.png")
    N["critical"] = [dict(name=r["name"], storage=r["storage"], scen=r["scen"], mode=r["mode"], p=r["p"], extra=r["turn_extra"], v=r["v"],
                          frac=r.get("lane_frac", ""), ratio_w=r["ratio_w"], ratio_zone1=r["ratio_zone1"]) for r in rows]


# ---------------------------------------------------------------- co-design
def codesign(best, allrows, cdv, out, N):
    """Infrastructure savings are reported for simulation-checked configurations (for each single infrastructure addition and for
    "passing place + widening" the top 3 by L* go to the check); the L* values are listed alongside as screening values only."""
    sim = {json.dumps(json.loads(T.dec(r["key"])["cd"]), sort_keys=True): r for r in cdv}
    ZH = lambda r: (f"K={r['K']} S={r['S']} {dict(tandem='tandem', side='side-by-side')[r['lay']]}"
                    f"{'' if r['lay'] == 'side' else '·' + MODE_ZH[r['mode']]} {dict(cradle='cradle', mixed='mixed', direct='direct')[r['lift']]}")
    GROUPS = [("none", (0, 0, 0)), ("gate holding place", (1, 0, 0)), ("passing place", (0, 1, 0)), ("widening", (0, 0, 1)), ("passing place + widening", (0, 1, 1))]
    L = ["# Co-design: screening by closed-form integer enumeration of W″, checked by simulation\n",
         "Variables: K = 1–8, S = 0–3, cradle layout (tandem S_r = 1, t_sh = 1 h / side-by-side all reachable), cradle mode, lifting (cradle / mixed x = 0), Q_h = 0, 1, passing place (tandem), single lane widened to 16 m. "
         "Screening uses L*(n_v) (a lower bound independent of dispatch); the check uses the FCFS port time T_sim. Cost per voyage = vessel day rate × T/24 + K × 7,200 €/day × 6 days + S × 60,000 €/10 calls. "
         "Infrastructure has no published unit price: given is the change in the cheapest cost among checked configurations after adding one item (and passing place + widening) (positive = saving); times 10 voyages it is the break-even investment for one campaign. "
         "The checked set is, for each (scenario, n_v, day rate), the top 3 by L*, the top 3 without infrastructure and the top 3 of each infrastructure combination, so the table shows the cheapest \"among checked configurations\".\n",
         "| Scenario | n_v | Day rate | Infrastructure | Cheapest checked configuration | L* / T_sim h | Simulated cost € | Saving vs none € (simulation) | Saving vs none € (L* screening) |",
         "|---|---:|---:|---|---|---|---:|---:|---:|"]
    out_rows, slower = [], []
    for sc in ("base", "lane"):
        for n in ("3", "5", "10"):
            for rate in ("140k", "250k"):
                rv = int(rate[:-1]) * 1000
                csim = lambda r: fl(sim[r["cfg"]]["port_h"]) / 24 * rv + i(r["K"]) * 7200 * 6 + i(r["S"]) * 6000
                best_g = {}
                for name, combo in GROUPS:
                    rs = [r for r in allrows if r["scen"] == sc and str(r["n_v"]) == n and (i(r["hold"]), i(r["pass_"]), i(r["widen"])) == combo]
                    ver = [r for r in rs if r["cfg"] in sim]
                    best_g[name] = (min(ver, key=lambda r: (csim(r), i(r["hold"]) + i(r["pass_"]) + i(r["widen"]), r["cfg"])) if ver else None,
                                    min(rs, key=lambda r: (float(r[f"cost_{rate}"]), i(r["hold"]) + i(r["pass_"]) + i(r["widen"]), r["cfg"])) if rs else None)
                p_s, p_l = best_g["none"]
                for name, _ in GROUPS:
                    s_, l_ = best_g[name]
                    if s_ is None:
                        continue
                    row = dict(scen=sc, n_v=n, rate=rate, infra=name, cfg=ZH(s_), lstar_h=float(s_["lstar_h"]), tsim_h=round(fl(sim[s_["cfg"]]["port_h"]), 3),
                               cost_sim=round(csim(s_)), save_sim=round(csim(p_s) - csim(s_)), save_lstar=round(float(p_l[f"cost_{rate}"]) - float(l_[f"cost_{rate}"])))
                    out_rows.append(row)
                    L.append(f"| {SCEN_ZH[sc]} | {n} | {rate} | {name} | {row['cfg']} | {row['lstar_h']:.2f} / {row['tsim_h']:.2f} | {row['cost_sim']:,} | "
                             f"{row['save_sim']:,} | {row['save_lstar']:,} |")
                    if name == "gate holding place" and row["save_sim"] < 0 and fl(sim[s_["cfg"]]["port_h"]) > fl(sim[p_s["cfg"]]["port_h"]):
                        slower.append(f"{SCEN_ZH[sc]}, one vessel of {n} piles, {rate}: \"gate holding place alone {row['save_sim']:,} €\" means that under FCFS the added gate holding place makes it slower"
                                      f" ({row['tsim_h']:.2f} vs {fl(sim[p_s['cfg']]['port_h']):.2f} h)")
    agree = []
    for sc in ("base", "lane"):
        for n in ("3", "5", "10"):
            rs = [r for r in allrows if r["scen"] == sc and str(r["n_v"]) == n and r["cfg"] in sim]
            for rate in ("140k", "250k"):
                rv = int(rate[:-1]) * 1000
                csim = lambda r: fl(sim[r["cfg"]]["port_h"]) / 24 * rv + i(r["K"]) * 7200 * 6 + i(r["S"]) * 6000
                a_ = min(rs, key=lambda r: (float(r[f"cost_{rate}"]), i(r["hold"]) + i(r["pass_"]) + i(r["widen"]), r["cfg"]))
                s_ = min(rs, key=lambda r: (csim(r), i(r["hold"]) + i(r["pass_"]) + i(r["widen"]), r["cfg"]))
                agree.append(dict(scen=sc, n_v=n, rate=rate, n_verified=len(rs), lstar_pick=a_["cfg"] == s_["cfg"], sim_cost_gap=round(csim(a_) - csim(s_)),
                                  sim_best=ZH(s_) + ("·gate holding place" if i(s_["hold"]) else "") + ("·passing place" if i(s_["pass_"]) else "") + ("·widening" if i(s_["widen"]) else "")))
    L += ["\nTable note: passing places are only enumerated for the tandem layout; the negative value of \"passing place alone\" comes from the change of layout (when the cheapest configuration without infrastructure is side-by-side, adding a passing place forces tandem), "
          "not from the passing place itself" + ("; " + "; ".join(slower) if slower else "") + ".\n"]
    L += ["\nScreening vs check: among checked configurations, whether the cheapest by L* is also the cheapest by simulated port time; if not, the difference in €/voyage.\n",
          "| Scenario | n_v | Day rate | Configurations checked | Same | Simulated cost of the L* pick − simulated cheapest € | Simulated cheapest configuration |", "|---|---:|---|---:|---|---:|---|"]
    L += [f"| {SCEN_ZH[a_['scen']]} | {a_['n_v']} | {a_['rate']} | {a_['n_verified']} | {'yes' if a_['lstar_pick'] else 'no'} | {a_['sim_cost_gap']:,} | {a_['sim_best']} |"
          for a_ in agree]
    lb = sum(1 for r in cdv if fl(r["port_h"]) is not None and fl(r["port_h"]) < fl(r["lstar_lo"]) - 1e-9)
    L.append(f"\nOf the {len(cdv)} checked configurations, {lb} have a simulated port time below L*; checker failures: {sum(1 for r in cdv if not i(r['check_ok']))}.")
    md(out, "table_codesign.md", L)
    wcsv(out / "table_codesign.csv", out_rows)
    N["codesign"] = dict(rows=out_rows, agree=agree, below_lstar=lb, n_verified=len(cdv))


# ---------------------------------------------------------------- campaign duration
def campaign(rows, out, N):
    L = ["# Campaign duration: one vessel, 60 piles, weather windows; port time in two representations\n",
         "Each voyage = port time + 2 × 12 h sailing + 24 h installation per pile (the clock runs only in workable 6 h blocks); weather is a two-state Markov chain (workable probability q, workable spells of 24 h on average), seeds 1–200. "
         "Port time: occupancy model (FCFS from E3, pull-in S = 1, Q_h = 0) vs fixed-time representation (calibrated with K_ref = 1 in the same scenario).\n",
         "| Scenario | n_v | K | q | Port h: occupancy / fixed time | Voyages | Campaign (days): occupancy / fixed time | Difference: mean (10%–90%) | Sum of port-time differences only |", "|---|---:|---:|---:|---|---:|---|---|---:|"]
    L += [f"| {SCEN_ZH[r['scen']]} | {r['n_v']} | {r['K']} | {r['q']} | {r['port_occ_h']} / {r['port_fix_h']} | {r['voyages']} | {r['days_occ']} / {r['days_fix']} | "
          f"{r['diff_mean']} ({r['diff_p10']}–{r['diff_p90']}) | {r['naive']} |" for r in rows]
    md(out, "table_campaign.md", L)
    N["campaign"] = rows


# ---------------------------------------------------------------- assorted numbers
def p15(e4, mix6, rep134, siteport, rep136, out, N):
    pl = rd(rep134 / "table_e4_plateau.csv")
    L = ["# Assorted numbers\n", "## Three plateaus (A1, L = 12 h, G = 24 h, pull-in): rate-bound plateau ⌈K†⌉, rule-independent plateau within the window (smallest K at which W1′ reaches its maximum), FCFS / convoy plateaus\n",
         "| Scenario | S | K† | ⌈K†⌉ | W1′ plateau (piles) | FCFS plateau (piles) | Convoy plateau (piles) |", "|---|---:|---:|---:|---|---|---|"]
    three = []
    for t in pl:
        if t["kind"] == "A1" and t["mode"] == "pull_in" and t["L"] == "12" and t["G"] == "24" and t["S"] in ("0", "1", "3", "6"):
            three.append(t)
            L.append(f"| {SCEN_ZH[t['scen']]} | {t['S']} | {t['k_dagger']} | {t['ceil_kd']} | K={t['plat_w1g']} ({t['n_w1g']}) | K={t['plat_fcfs']} ({t['n_fcfs']}) | "
                     f"K={t['plat_convoy']} ({t['n_convoy']}) |")
    # cradle and mixed lifting side by side
    c = {(r["scen"], r["mode"], i(r["S"]), i(r["K"])): i(r["sim"]) for r in e4 if r["kind"] == "A1" and r["L"] == "12" and r["G"] == "24" and r["rule"] == "fcfs"}
    x = {(r["scen"], r["mode"], i(r["S"]), i(r["K"])): i(r["sim"]) for r in mix6 if r["kind"] == "A1" and r["L"] == "12" and r["G"] == "24" and r["rule"] == "fcfs"}
    L += ["\n## Cradle and mixed lifting (x = 0) side by side: A1, pull-in, L = 12 h, G = 24 h, FCFS (piles; cradle / mixed)\n", "| Scenario | S | K = 1 | 2 | 3 | 4 | 6 | 10 |",
          "|---|---:|---|---|---|---|---|---|"]
    for sc in ("base", "lane"):
        for S_ in (1, 3, 6):
            L.append(f"| {SCEN_ZH[sc]} | {S_} | " + " | ".join(f"{c[(sc, 'pull_in', S_, K)]} / {x[(sc, 'pull_in', S_, K)]}" for K in (1, 2, 3, 4, 6, 10)) + " |")
    # the h_d condition of rule 6 at Okpo
    sp = {(r["site"], r["st"], r["scen"], r["mode"], r["arr"], i(r["K"])): fl(r["port_h"]) for r in siteport if r["hold"] == "0"}
    L += ["\n## Rule 6 (lift from the vehicle when x·p ≤ h_d) at Okpo: port time for one vessel of 10 piles (h), cradle / mixed lifting (x = 0, so x·p = 0 ≤ h_d = 0.5 h)\n",
          "| Storage area | Scenario | Cradle mode | S | K = 1 | 2 | 4 | 8 |", "|---|---|---|---:|---|---|---|---|"]
    okp = []
    for st in ("runs", "multi"):
        for sc in ("base", "slow"):
            for m in ("pull_in", "on_road"):
                for S_ in (1, 3):
                    a = [sp[("okpo", st, sc, m, f"S{S_}", K)] for K in (1, 2, 4, 8)]
                    b = [sp[("okpo", st, sc, m, f"S{S_}m", K)] for K in (1, 2, 4, 8)]
                    okp.append(dict(st=st, scen=sc, mode=m, S=S_, cradle=a, mixed=b))
                    L.append(f"| {'one voyage' if st == 'runs' else 'three voyages'} | {SCEN_ZH[sc]} | {MODE_ZH[m]} | {S_} | " + " | ".join(f"{u:.2f} / {v:.2f}" for u, v in zip(a, b)) + " |")
    worse = sum(1 for r in okp for u, v in zip(r["cradle"], r["mixed"]) if v > u + 1e-6)
    L.append(f"\nCells where mixed lifting is slower than cradle: {worse} / {len(okp) * 4} (x = 0 satisfies x·p ≤ h_d; for x·p > h_d mixed lifting is slower than cradle, Section 6 of the extra analyses).")
    # cost footnote
    cost = rd(rep136 / "table_cost.csv")
    sv = [fl(r["save_set_h"]) for r in cost if r["arr"] == "S1" and r["mode"] == "pull_in" and r["hold"] == "0" and r["n_v"] == "10" and r["K"] == "1"
          and r.get("save_set_h") not in ("", None)]
    L += ["\n## Numbers for the cost footnote of Table 10\n",
          f"One vessel of 10 piles, pull-in S = 1, K = 1→2: saving per voyage {min(sv):.2f}–{max(sv):.2f} h (four scenarios), at 140,000 €/day {min(sv) / 24 * 140000:,.0f}–{max(sv) / 24 * 140000:,.0f} €. "
          f"The break-even in Table 10 assumes continuous hire (the second set is hired for the whole voyage cycle of C days, {6 * 7200:,} €/voyage for C = 6 days); if only days in port are charged, minimum 1 day, the second set costs 7,200 € per voyage."]
    md(out, "table_p15.md", L)
    N["p15"] = dict(three=three, okpo_mixed_worse=worse, okpo=okp, save_set_h=[min(sv), max(sv)])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    dirs = {k: one(k) for k in NEW if k != "random"}
    rnd = sorted(p for p in (ROOT / "results").glob("windport_spatial_random_*") if p.is_dir())
    assert len(rnd) == 2, rnd                                    # random regression in two parts (start 0 and 12,000, 12,000 cases each)
    fixed = {k: ROOT / "results" / v for k, v in FIXED.items()}
    files = dict(sites="points.csv", siteport="points.csv", turn="points.csv", turngeo="turn.csv", reserve="points.csv", reach="points.csv", upsize="points.csv", ablate="points.csv",
                 hphd="points.csv", cdv="points.csv", regime5="regime5.csv", critical="critical_points.csv", codesign="best.csv",
                 campaign="campaign.csv")
    inputs = {f"{k}": str((dirs[k] / f).relative_to(ROOT)).replace("\\", "/") for k, f in files.items()}
    inputs.update({f"random{j}": str((d / "summary.json").relative_to(ROOT)).replace("\\", "/") for j, d in enumerate(rnd)})
    h = hashlib.sha256(Path(__file__).read_bytes())
    for k in sorted(inputs):
        h.update((ROOT / inputs[k]).read_bytes())
    h.update(json.dumps(FIXED, sort_keys=True).encode())
    out = ROOT / "results" / f"windport_spatial_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    N = {}
    sites_rows = rd(dirs["sites"] / "points.csv")
    e6 = rd(fixed["e6"] / "points.csv")
    sp = rd(dirs["siteport"] / "points.csv")
    A, B = sites(sites_rows, e6, sp, out, N)
    turn(dirs["turngeo"], rd(dirs["turn"] / "points.csv"), A, B, out, N)
    reserve(rd(dirs["reserve"] / "points.csv"), A, B, out, N)
    e4 = rd(fixed["e4"] / "points.csv")
    mix6 = rd(fixed["mix6"] / "points.csv")
    reach(rd(dirs["reach"] / "points.csv"), e4, mix6, out, N)
    upsize(rd(dirs["upsize"] / "points.csv"), rd(fixed["e7"] / "points.csv"), out, N)
    ablate(rd(dirs["ablate"] / "points.csv"), rd(fixed["port"] / "points.csv"), e4, out, N)
    hphd(rd(dirs["hphd"] / "points.csv"), rd(fixed["sens"] / "points.csv"), out, N)
    regime5(rd(dirs["regime5"] / "regime5.csv"), out, N)
    critical(rd(dirs["critical"] / "critical_points.csv"), out, N)
    codesign(rd(dirs["codesign"] / "best.csv"), rd(dirs["codesign"] / "codesign.csv"), rd(dirs["cdv"] / "points.csv"), out, N)
    campaign(rd(dirs["campaign"] / "campaign.csv"), out, N)
    p15(e4, mix6, fixed["rep134"], rd(out / "table_siteport.csv"), fixed["rep136"], out, N)
    parts = [json.loads((d / "summary.json").read_text(encoding="utf-8")) for d in rnd]
    N["random"] = {k: sum(p[k] for p in parts) for k in parts[0]}
    N["random_chunks"] = [d.name for d in rnd]
    (out / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out / "inputs.json").write_text(json.dumps(dict(new=inputs, fixed=FIXED), ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
