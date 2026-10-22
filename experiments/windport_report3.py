"""Figures and summary tables for the supplementary analyses (draft figures). Reads only the committed points.csv, example.csv,
critical.csv, facts.json, summary.json and the parameter-register supplement, not points/, so it rebuilds from a clean checkout.
Draws no real maps.

Inputs (run directories listed in DIRS):
  port, fix, mix6, sens, pub   experiments/windport_extra.py --part ...
  example, critical            experiments/windport_analytic.py --part ...
  facts                        experiments/windport_facts.py
  random                       experiments/windport_random_lift.py
  references (committed): E3 (fixed-duration column of Table 5), E4 (Table 6 and the simulated deliveries of the worked
  example), sens (baseline row of Appendix C)
Output: results/windport_extra_report_<first 12 hex digits of the SHA-256 of the inputs and this script>/.
Run: .venv/Scripts/python.exe experiments/windport_report3.py
"""
import collections
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIRS = dict(port="runs/port_time", fix="runs/fixed_time", mix6="runs/mixed_e4",
            sens="runs/sens_extra", pub="runs/public_projects", example="runs/example",
            critical="runs/critical", facts="runs/facts", random="runs/random_lift_1",
            random2="runs/random_lift_2", random3="runs/random_lift_3", random4="runs/random_lift_4",
            sens5="runs/sens_e5", mixx="runs/mixed_release", recheck="runs/recheck",
            e3="runs/e3", e4="runs/e4",
            e5="runs/e5", sens0="runs/sens")
FILES = dict(example="example.csv", critical="critical.csv", facts="facts.json", random="summary.json", random2="summary.json", random3="summary.json",
             random4="summary.json", recheck="summary.md")
EXTRA = ["data/register/parameters.csv"]
META = {"Software": None}
SCEN_ZH = dict(base="baseline", slow="1 km/h", longslow="long corridor + 1 km/h", lane="long single lane + 1 km/h", fastcrane="vessel crane 0.5 h")
MODE_ZH = dict(on_road="roadside cradle", pull_in="pull-in cradle")
ARR_ZH = dict(S0="S = 0 direct lift", S1="S = 1 cradle", S1m="S = 1 mixed lifting", S3="S = 3 cradle", S3m="S = 3 mixed lifting", S2="S = 2 cradle", S2m="S = 2 mixed lifting")
SC5 = ["base", "slow", "longslow", "lane", "fastcrane"]
RATES = [140000, 150000, 250000]                      # €/day: Ursavas 2017 jack-up vessel; Tjaberings 2022 heavy-lift vessel range
SET_DAY = (24 * (160 + 120), 24 * (180 + 120))        # €/day: one vehicle set + two operators (Kassels Appendix D, idle / busy)
SET_DAY_SUP = (24 * (160 + 120 + 80), 24 * (180 + 120 + 80))     # plus a supervisor at 80 €/h (source has one SPMT; whether it doubles is unclear)
SUPPORT = 60000.0                                     # € per support (Kassels Appendix D)
plt.rcParams.update({"font.family": ["Microsoft YaHei", "SimHei", "DejaVu Sans"], "axes.unicode_minus": False, "font.size": 8})


def path(k):
    return ROOT / "results" / DIRS[k] / FILES.get(k, "points.csv")


def load(k):
    return list(csv.DictReader(open(path(k), encoding="utf-8")))


def i(x):
    return int(float(x)) if x not in ("", None) else None


def fl(x):
    return float(x) if x not in ("", None) else None


def save(fig, out, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, metadata=META)
    (out / name).write_bytes(buf.getvalue())
    plt.close(fig)


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


def plateau(d):
    mx = max(d.values())
    return min(k for k, v in d.items() if v >= mx), mx


def first_within(d, tol=0.02):
    """{K: port time} → (minimum, first K within 2% of the minimum)."""
    m = min(d.values())
    return m, min(k for k, v in d.items() if v <= m * (1 + tol) + 1e-9)


def f2(x):
    return "—" if x is None else f"{x:.2f}"


# ---------------------------------------------------------------- worked-example table
def example(rows, e4, out):
    sim = {(r["scen"], r["mode"], i(r["K"])): i(r["sim"]) for r in e4
           if r["kind"] == "A1" and i(r["L"]) == 12 and i(r["G"]) == 24 and i(r["S"]) == 1 and r["rule"] == "fcfs"}
    conv = {(r["scen"], r["mode"], i(r["K"])): i(r["sim"]) for r in e4
            if r["kind"] == "A1" and i(r["L"]) == 12 and i(r["G"]) == 24 and i(r["S"]) == 1 and r["rule"] == "convoy"}
    w4 = {(r["scen"], r["mode"], i(r["K"])): i(r["w1g"]) for r in e4
          if r["kind"] == "A1" and i(r["L"]) == 12 and i(r["G"]) == 24 and i(r["S"]) == 1 and r["rule"] == "fcfs"}
    tab = []
    for r in rows:
        k = (r["scen"], r["mode"], i(r["K"]))
        assert w4[k] == i(r["w1g"]), (k, w4[k], r["w1g"])       # the analytic script and E4 give the same W1′
        tab.append(dict(r, sim_fcfs=sim[k], sim_convoy=conv[k]))
    wcsv(out / "table_example.csv", tab)
    L = ["# Worked example: A1, L = 12 h, G = 24 h, S = 1, Q_h = 0\n",
         "t_ℓ = driving on the cut + vehicle tail (L_v + longitudinal clearance)/v + steering stop δ + set-down h_d (only when the cut is the road of "
         "the quay berth); t_e = occupancy of an empty pass over the cut (divided by the number of parallel lanes); "
         "c = minimum interval between two successive handovers of one vehicle; d_q = from leaving the cut to the handover; Q = geometric quay-zone "
         "capacity (Corollary 4); K† = c/(t_ℓ + t_e). "
         "Terms: I interface ⌊L/p⌋, U cradle turnover, F fleet, C cut, Z quay zone (omitted when not tighter than F), Π preparation term from an "
         "empty system, Π_S serial-cut preparation term; W′ is the minimum. Simulation: first-come-first-served (convoy).\n",
         "| Scenario | Cradle | K | Cut (length m) | t_ℓ = drive + tail + δ + h_d (s) | t_e (s) | c (s) | d_q (s) | Q | K† | I | U | F | C | Z | Π | Π_S | "
         "W′ (binding term) | Simulation |",
         "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for t in tab:
        L.append(f"| {SCEN_ZH[t['scen']]} | {MODE_ZH[t['mode']]} | {t['K']} | {t['cut'].split('|')[1]} ({t['cut_len_m']}) | {t['tl']} = {t['drive_s']} + {t['tail_s']} + "
                 f"{t['delta_s']} + {float(t['hd_on_cut']):.0f} | {t['te']} | {t['c']} | {t['dq']} | {t['Q']} | {t['k_dagger']} | {t['interface']} | {t['turnover'] or '∞'} | "
                 f"{t['fleet']} | {t['cut_term']} | {t['zone'] or '—'} | {t['prep']} | {t['serial'] or '—'} | {t['w1g']} ({t['binding']}) | {t['sim_fcfs']} ({t['sim_convoy']}) |")
    md(out, "table_example.md", L)
    return tab


# ---------------------------------------------------------------- port time
def port_index(rows):
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r["scen"], r["mode"], r["arr"], i(r["n_v"]), r["hold"], r["rep"])][i(r["K"])] = r
    return by


def e3_fixed(e3):
    """Fixed-duration column of the committed E3 run: {(scen, mode, S, kref): {K: port time}} (n_v = 10); also the
    road-occupancy column (for the cross-check)."""
    fx, occ = collections.defaultdict(dict), collections.defaultdict(dict)
    for r in e3:
        k = r["key"].split("|")
        if k[0] == "fix" and k[5] == "port10":
            fx[(k[1], k[2], "S" + r["S"], i(r["kref"]))][i(r["K"])] = fl(r["port_h"])
        if k[0] == "port":
            occ[(k[1], k[2], "S" + r["S"], i(r["n_v"]), r["hold"])][i(r["K"])] = fl(r["port_h"])
    return fx, occ


def table5x(port, fix, e3, out):
    import windport.bound3 as B3                     # noqa: E402
    by = port_index(port)
    fx, occ3 = e3_fixed(e3)
    for r in fix:
        fx[(r["scen"], r["mode"], r["arr"], i(r["kref"]))][i(r["K"])] = fl(r["port_h"])
    same, diff = 0, []
    for (sc, m, arr, n, h, rep), d in by.items():           # exact check against the committed E3 port times (S = 0, 1, 3; Q_h = 0, unlimited; n_v = 3, 10)
        k3 = (sc, m, arr, n, "0" if h == "0" else "inf")
        if rep == "fcfs" and h in ("0", "inf") and k3 in occ3:
            for K, r in d.items():
                if fl(r["port_h"]) == occ3[k3][K]:
                    same += 1
                else:
                    diff.append((k3, K, r["port_h"], occ3[k3][K]))
    tab = []
    for sc in SC5:
        p = 1800.0 if sc == "fastcrane" else 3600.0
        for m in ("on_road", "pull_in"):
            for arr in ("S0", "S1", "S1m", "S3", "S3m"):
                get = lambda h, rep, n=10: {K: fl(r["port_h"]) for K, r in by[(sc, m, arr, n, h, rep)].items()}
                o, ko = first_within(get("0", "fcfs"))
                cv, kc = first_within(get("0", "convoy"))
                cu, ku = first_within(get("0", "cut"))
                oi, _ = first_within(get("inf", "fcfs"))
                o1, _ = first_within(get("1", "fcfs"))
                ls0 = min(fl(r["lstar_lo"]) for r in by[(sc, m, arr, 10, "0", "fcfs")].values())
                lsi = min(fl(r["lstar_lo"]) for r in by[(sc, m, arr, 10, "inf", "fcfs")].values())
                fk = [first_within(fx[(sc, m, arr, kr)]) if fx.get((sc, m, arr, kr)) else (None, None) for kr in (1, 2, 3, 4)]
                Sn = int(arr[1])
                occ1 = get("0", "fcfs")[1]
                hm = B3.muhabie_h(10, Sn, p, 24 * 3600.0, occ1 * 3600.0)
                lit = B3.muhabie_port(10, Sn, 3600.0, p, 24 * 3600.0) / 3600.0
                tab.append(dict(scen=sc, mode=m, arr=arr, limit=10 * p / 3600, occ=round(o, 2), K_occ=ko, convoy=round(cv, 2), K_convoy=kc, cut=round(cu, 2),
                                K_cut=ku, hold1=round(o1, 2), hold_inf=round(oi, 2), lstar0=round(ls0, 2), lstar_inf=round(lsi, 2),
                                fixed=" / ".join(f2(x) for x, _ in fk), K_fixed="/".join(str(k) if k else "—" for _, k in fk),
                                muhabie_h_min=None if hm is None else round(hm / 60, 1), muhabie_K1=round(occ1, 2), muhabie_1h=round(lit, 2)))
    wcsv(out / "table5x.csv", tab)
    L = ["# Table 5 extra columns: A1, minimum port time to load 10 piles (K = 1–8; in brackets the first K within 2% of the minimum), "
         "G = 24 h\n",
         "Mixed-lifting rows use the direct-lift vehicle release time x = 0 (x scan in table_mixx.md). Road occupancy: first-come-first-served "
         "(main case Q_h = 0; Q_h = 1 and unlimited also listed) and convoy dispatch (Q_h = 0); cut as a single resource: the fixed-duration "
         "representation with the single lane added as one resource of capacity 1 "
         "(windport/sim3.py, Q_h = 0); fixed duration K_ref = 1–4 (S = 0, 1, 3 from E3; mixed lifting calibrated here in the same way); "
         "L*(10): port-time lower bound valid for every dispatch rule, min_K L*(10; K) (K = 1–8, Q_h = 0 / unlimited; corrected W′); "
         "Muhabie-type single server: port time independent of K, "
         "calibrated at K_ref = 1 it equals the road-occupancy value at K = 1, in brackets the corresponding handling time per pile (min); "
         "port time at 1 h per pile listed separately.\n",
         "| Scenario | Cradle | Lifting | Lower limit | Road occupancy fcfs | Convoy | Cut single resource | Q_h = 1 | Q_h = ∞ | L*(10): Q_h = 0 / ∞ | "
         "Fixed duration K_ref = 1/2/3/4 | Muhabie: calibrated (h per pile) / 1 h per pile |",
         "|---|---|---|---:|---|---|---|---:|---:|---|---|---|"]
    for t in tab:
        L.append(f"| {SCEN_ZH[t['scen']]} | {MODE_ZH[t['mode']]} | {ARR_ZH[t['arr']]} | {t['limit']:.1f} | {t['occ']:.2f} ({t['K_occ']}) | {t['convoy']:.2f} ({t['K_convoy']}) | "
                 f"{t['cut']:.2f} ({t['K_cut']}) | {t['hold1']:.2f} | {t['hold_inf']:.2f} | {t['lstar0']:.2f} / {t['lstar_inf']:.2f} | {t['fixed']} ({t['K_fixed']}) | "
                 f"{t['muhabie_K1']:.2f} ({t['muhabie_h_min'] if t['muhabie_h_min'] is not None else '—'}) / {t['muhabie_1h']:.2f} |")
    L.append(f"\nExact check against the committed E3 port times: {same} identical, {len(diff)} different" + (f" (e.g. {diff[:3]})" if diff else "") + ".")
    md(out, "table5x.md", L)
    # Fig. 5 extra lines: five scenarios × pull-in, S = 1
    fig, ax = plt.subplots(1, 5, figsize=(15, 3.4), sharey=True)
    data = []
    for x, sc in zip(ax, SC5):
        p = 1800.0 if sc == "fastcrane" else 3600.0
        Ks = list(range(1, 9))
        lines = [("occupancy fcfs", ("S1", "0", "fcfs"), "-o", "C0"), ("occupancy fcfs, Q_h = ∞", ("S1", "inf", "fcfs"), "-s", "C1"),
                 ("convoy", ("S1", "0", "convoy"), ":^", "C2"), ("cut as one resource", ("S1", "0", "cut"), "--v", "C3"), ("mixed lifting fcfs", ("S1m", "0", "fcfs"), "-.D", "C4")]
        for lab, (arr, h, rep), sty, col in lines:
            d = by[(sc, "pull_in", arr, 10, h, rep)]
            ys = [fl(d[K]["port_h"]) for K in Ks]
            x.plot(Ks, ys, sty, color=col, ms=3, lw=1, label=lab)
            data += [dict(scen=sc, line=lab, K=K, port_h=y) for K, y in zip(Ks, ys)]
        fxd = fx[(sc, "pull_in", "S1", 1)]
        x.plot(Ks, [fxd[K] for K in Ks], "-", color="grey", lw=1, label="fixed duration K_ref = 1")
        ls = min(fl(r["lstar_lo"]) for r in by[(sc, "pull_in", "S1", 10, "0", "fcfs")].values())
        x.axhline(ls, color="k", lw=0.8, ls="--", label="L*(10), any dispatch (Q_h = 0)")
        x.axhline(10 * p / 3600, color="k", lw=0.6, ls=":", label="vessel-crane lower limit")
        x.axhline(fl(by[(sc, "pull_in", "S1", 10, "0", "fcfs")][1]["port_h"]), color="C5", lw=0.8, ls="-.", label="Muhabie type (K_ref = 1)")
        x.set_title(f"{SCEN_ZH[sc]}, pull-in, S = 1", fontsize=7)
        x.set_xlabel("number of SPMT sets K")
    ax[0].set_ylabel("port time to load 10 piles (h)")
    ax[0].legend(fontsize=5)
    fig.suptitle("Fig. 5 extra lines (draft): road occupancy fcfs, Q_h = ∞, convoy, cut single resource, mixed lifting, fixed duration, "
                 "L*(10), Muhabie type", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, out, "fig5x.png")
    wcsv(out / "fig5x.csv", data)
    return tab, same, diff


def cost(port, out):
    """Port time T (h) for a vessel load of n_v piles × vessel day rate → cost per voyage; the difference between neighbouring
    levels = saving per voyage of one more vehicle set / one more cradle."""
    by = port_index(port)
    tab, best = [], []
    for sc in ("base", "longslow", "lane", "fastcrane"):
        for m in ("pull_in", "on_road"):
            for n in (3, 5, 10):
                for h in ("0", "1"):
                    T_ = {(arr, K): fl(by[(sc, m, arr, n, h, "fcfs")][K]["port_h"]) for arr in ("S0", "S1", "S1m", "S3", "S3m") for K in (1, 2, 3)}
                    for arr in ("S0", "S1", "S1m", "S3", "S3m"):
                        for K in (1, 2, 3):
                            t = T_[(arr, K)]
                            row = dict(scen=sc, mode=m, n_v=n, hold=h, arr=arr, K=K, port_h=round(t, 3), per_pile_h=round(t / n, 3),
                                       **{f"cost_{r // 1000}k": round(t / 24 * r) for r in RATES})
                            if K < 3:
                                dT = t - T_[(arr, K + 1)]
                                row.update(save_set_h=round(dT, 3), **{f"save_set_{r // 1000}k": round(dT / 24 * r) for r in RATES})
                                for r in (RATES[0], RATES[2]):        # days of vehicle hire it pays for (busy rate): without / with supervisor
                                    row[f"days_{r // 1000}k"] = round(dT / 24 * r / SET_DAY[1], 1)
                                    row[f"days_sup_{r // 1000}k"] = round(dT / 24 * r / SET_DAY_SUP[1], 1)
                            tab.append(row)
                    for K in (1, 2, 3):
                        for a, b in (("S0", "S1"), ("S1", "S3")):
                            dT = T_[(a, K)] - T_[(b, K)]
                            tab.append(dict(scen=sc, mode=m, n_v=n, hold=h, arr=f"{a}→{b}", K=K, save_cradle_h=round(dT, 3),
                                            **{f"save_cradle_{r // 1000}k": round(dT / 24 * r) for r in RATES},
                                            calls_to_amortise=(None if dT <= 1e-9 else round((int(b[1]) - int(a[1])) * SUPPORT / (dT / 24 * RATES[0]), 1))))
                    # cheapest configuration: cost per voyage = vessel T·r_v/24 + hire of K sets over a voyage cycle of C days
                    # + cradle cost amortised over N port calls (C = 6 days, N = 10: Kassels, 10 voyages in 61 days)
                    for r in RATES:
                        for C_ in (3, 6, 10):
                            cand = []
                            for (arr, K), t in T_.items():
                                Sn = int(arr[1])
                                c_ = t / 24 * r + K * SET_DAY[1] * C_ + Sn * SUPPORT / 10
                                cand.append((round(c_), arr, K, round(t, 2)))
                            cand.sort()
                            best.append(dict(scen=sc, mode=m, n_v=n, hold=h, rate=r, cycle_days=C_, cost=cand[0][0], arr=cand[0][1], K=cand[0][2],
                                             port_h=cand[0][3], second=f"{cand[1][1]} K={cand[1][2]} ({cand[1][0]})"))
    wcsv(out / "table_cost.csv", tab)
    wcsv(out / "table_cost_best.csv", best)
    L = ["# Cost and configuration tables\n",
         "Definitions: **port time** T(n_v) for a vessel load of n_v piles = from vessel-crane opening (vessel arrival) to the end of the n_v-th "
         "lift; **vessel time per pile** = T(n_v)/n_v (h/pile). Vessel cost per voyage = T × day rate / 24; "
         "day rates 140,000 (Ursavas 2017 jack-up vessel), 150,000 and 250,000 €/day (Tjaberings 2022 heavy-lift vessel range). The saving per "
         "voyage of one more vehicle set = T(K) − T(K + 1) times the day rate; "
         "it is the **break-even hire**: a second set is worth hiring if its hire over one voyage cycle does not exceed it (for a cycle of C days, "
         "break-even day rate = saving / C; C is a sensitivity parameter only). "
         f"In vehicle-hire days: one set + two operators at the Kassels Appendix D busy rate {SET_DAY[1]:,} €/day, with a supervisor at 80 €/h "
         f"{SET_DAY_SUP[1]:,} €/day. "
         f"The saving of one more cradle is computed the same way; cradles are charged per project (Kassels: {SUPPORT:,.0f} € each), port calls "
         "needed to amortise = cradle cost ÷ saving per voyage (140,000 €/day). "
         "A1, first-come-first-served, G = 24 h; mixed-lifting rows use the direct-lift release time x = 0 (Section 6: no slower than the cradle "
         "only when x·p ≤ h_d).\n",
         "## Saving per voyage of one more vehicle set (K → K + 1) = break-even hire (pull-in cradle, Q_h = 0)\n",
         "| Scenario | n_v | Lifting | T(K = 1 / 2 / 3) h | Vessel time per pile K = 1 / 2 / 3 h | K = 1→2 saving: h; € 140k / 250k | "
         "Hire days 140k: without / with supervisor | 250k: without / with supervisor | K = 2→3 saving h |",
         "|---|---:|---|---|---|---|---|---|---|"]
    get = {(t["scen"], t["mode"], t["n_v"], t["hold"], t["arr"], t["K"]): t for t in tab}
    for sc in ("base", "longslow", "lane", "fastcrane"):
        for n in (3, 5, 10):
            for arr in ("S0", "S1", "S1m", "S3"):
                a = [get[(sc, "pull_in", n, "0", arr, K)] for K in (1, 2, 3)]
                L.append(f"| {SCEN_ZH[sc]} | {n} | {ARR_ZH[arr]} | {' / '.join(f'{x['port_h']:.2f}' for x in a)} | {' / '.join(f'{x['per_pile_h']:.2f}' for x in a)} | "
                         f"{a[0]['save_set_h']:.2f}; {a[0]['save_set_140k']:,} / {a[0]['save_set_250k']:,} | {a[0]['days_140k']} / {a[0]['days_sup_140k']} | "
                         f"{a[0]['days_250k']} / {a[0]['days_sup_250k']} | {a[1]['save_set_h']:.2f} |")
    L += ["\nBreak-even day rate (€/day) = saving per voyage ÷ voyage cycle C (sensitivity; pull-in, S = 1, K = 1→2, Q_h = 0, 140,000 €/day):\n",
          "| Scenario | n_v | C = 3 days | C = 6 days | C = 10 days |", "|---|---:|---:|---:|---:|"]
    for sc in ("base", "longslow", "lane", "fastcrane"):
        for n in (3, 5, 10):
            v = get[(sc, "pull_in", n, "0", "S1", 1)]["save_set_140k"]
            L.append(f"| {SCEN_ZH[sc]} | {n} | {v / 3:,.0f} | {v / 6:,.0f} | {v / 10:,.0f} |")
    L += ["\n## Effect of a gate holding place Q_h = 1 (pull-in, S = 1, T for K = 1 / 2 / 3, h)\n", "| Scenario | n_v | Q_h = 0 | Q_h = 1 |", "|---|---:|---|---|"]
    for sc in ("base", "longslow", "lane", "fastcrane"):
        for n in (3, 5, 10):
            L.append(f"| {SCEN_ZH[sc]} | {n} | {' / '.join(f'{get[(sc, 'pull_in', n, '0', 'S1', K)]['port_h']:.2f}' for K in (1, 2, 3))} | "
                     f"{' / '.join(f'{get[(sc, 'pull_in', n, '1', 'S1', K)]['port_h']:.2f}' for K in (1, 2, 3))} |")
    L += ["\n## Saving per voyage of one more cradle (S = 0→1, 1→3) and port calls to amortise it (pull-in, Q_h = 0, 140k €/day)\n",
          "| Scenario | n_v | K | S 0→1: h (port calls) | S 1→3: h (port calls) |",
          "|---|---:|---:|---|---|"]
    for sc in ("base", "longslow", "lane", "fastcrane"):
        for n in (3, 5, 10):
            for K in (1, 2):
                a, b = get[(sc, "pull_in", n, "0", "S0→S1", K)], get[(sc, "pull_in", n, "0", "S1→S3", K)]
                L.append(f"| {SCEN_ZH[sc]} | {n} | {K} | {a['save_cradle_h']:.2f} ({a['calls_to_amortise'] or '—'}) | {b['save_cradle_h']:.2f} ({b['calls_to_amortise'] or '—'}) |")
    L += ["\n## Cheapest configuration (sensitivity: cost per voyage = vessel time cost + hire of K sets over a voyage cycle of C days (busy rate, "
          "no supervisor) + cradle cost per project amortised over 10 port calls; K ≤ 3, S ∈ {0, 1, 3}, "
          "including mixed lifting (x = 0); pull-in, Q_h = 0)\n",
          "| Scenario | n_v | Day rate €/day | C = 3 days | C = 6 days | C = 10 days |", "|---|---:|---:|---|---|---|"]
    gb = {(b["scen"], b["mode"], b["n_v"], b["hold"], b["rate"], b["cycle_days"]): b for b in best}
    for sc in ("base", "longslow", "lane", "fastcrane"):
        for n in (3, 5, 10):
            for r in RATES:
                cells = [gb[(sc, "pull_in", n, "0", r, C_)] for C_ in (3, 6, 10)]
                L.append(f"| {SCEN_ZH[sc]} | {n} | {r:,} | " + " | ".join(f"{ARR_ZH[c['arr']]}, K = {c['K']} (T = {c['port_h']} h, {c['cost']:,} €)" for c in cells) + " |")
    md(out, "table_cost.md", L)
    # figure: cheapest configuration (C = 6 days, 140k) by n_v and scenario
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
    for x, r in zip(ax, (140000, 250000)):
        for j, sc in enumerate(("base", "longslow", "lane", "fastcrane")):
            for n in (3, 5, 10):
                b = gb[(sc, "pull_in", n, "0", r, 6)]
                x.scatter(n, j, s=60 + 40 * b["K"], marker={"S0": "o", "S1": "s", "S1m": "D", "S3": "^", "S3m": "v"}[b["arr"]], color=f"C{b['K']}")
                x.text(n + 0.3, j, f"{b['arr']}, K={b['K']}\n{b['port_h']} h", fontsize=6, va="center")
        x.set_yticks(range(4))
        x.set_yticklabels([SCEN_ZH[s] for s in ("base", "longslow", "lane", "fastcrane")])
        x.set_xticks([3, 5, 10])
        x.set_xlim(2, 13)
        x.set_xlabel("vessel load n_v (piles)")
        x.set_title(f"vessel day rate {r:,} €/day, voyage cycle 6 days", fontsize=7)
    fig.suptitle("Fig. 12 (optional draft): cheapest configuration per voyage (pull-in, Q_h = 0; marker size and colour = K)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, out, "fig12_cheapest.png")
    return tab, best


# ---------------------------------------------------------------- critical single-lane length
def critical(rows, port, e3, sens0, e4, out):
    lr = [r for r in rows if r["part"] == "longrun"]
    win = [r for r in rows if r["part"] == "window"]
    nm = [r for r in rows if r["part"] == "named"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    x = ax[0]
    for pp, col in zip(("0.5", "1.0", "1.5"), ("C3", "C0", "C2")):
        for m, sty in (("pull_in", "-"), ("on_road", "--")):
            rs = sorted((r for r in lr if r["p"] == pp and r["mode"] == m), key=lambda r: float(r["v"]))
            vs = [float(r["v"]) for r in rs]
            x.plot(vs, [fl(r["ell_cut"]) if r["ell_cut"] != "" else None for r in rs], sty, color=col, lw=1.2,
                   label=f"p = {pp} h, {MODE_ZH[m]}: t_ℓ + t_e = p")
            x.plot(vs, [fl(r["ell_zone1"]) if r["ell_zone1"] != "" else None for r in rs], sty, color=col, lw=0.6, alpha=0.6,
                   label=f"p = {pp} h, {MODE_ZH[m]}: t_ℓ + d_q + t_e^occ = p" if m == "pull_in" else None)
    marks = [("A1 baseline (single-lane block 200 m)", 2.5, 200), ("A1 long corridor (block 600 m)", 1.0, 600), ("A1 long single lane 1,200 m", 1.0, 1200),
             ("Okpo route 282.7 m", 2.5, 282.7), ("Yantai route 102.8 m", 2.5, 102.8), ("Okpo 1 km/h", 1.0, 282.7), ("Yantai 1 km/h", 1.0, 102.8)]
    for lab, v, ell in marks:
        x.plot(v, ell, "k*", ms=6)
        x.annotate(lab, (v, ell), fontsize=5, xytext=(3, 3), textcoords="offset points")
    x.fill_between([2.4, 2.6], 250, 400, color="orange", alpha=0.4, label="Kassels distance 250–400 m (2.5 km/h)")
    x.set_xlabel("loaded speed (km/h)")
    x.set_ylabel("critical single-lane length ℓ* (m)")
    x.set_ylim(0, 4000)
    x.legend(fontsize=5, loc="upper left")
    x.set_title("(a) long run: the road takes at least τ per pile; for τ > p the vessel crane cannot lift continuously (S = 1, Q_h = 0)", fontsize=7)
    x = ax[1]
    for Sn, col in zip(("0", "1", "3"), ("C0", "C1", "C2")):
        for v, sty in (("1.0", "-o"), ("2.5", "--s")):
            rs = sorted((r for r in win if r["S"] == Sn and r["v"] == v), key=lambda r: int(r["Lp"]))
            x.plot([int(r["Lp"]) for r in rs], [fl(r["ell_window"]) for r in rs], sty, color=col, ms=3, lw=1, label=f"S = {Sn}, {v} km/h")
    x.set_xlabel("window length L / p (p = 1 h)")
    x.set_ylabel("shortest single lane at which a road term of W′ binds (m)")
    x.set_ylim(0, 6000)
    x.legend(fontsize=6)
    x.set_title("(b) window: W′ without the interface term < ⌊L/p⌋ (K = 10, G = 24 h, pull-in)", fontsize=7)
    fig.suptitle("Fig. 13 (draft) when the road matters: critical single-lane length", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, out, "fig13_critical.png")
    wcsv(out / "fig13_critical.csv", lr + win)
    # cross-check: Table 5 (five A1 scenarios), Appendix C3 (loaded speed on the long single lane), Table 6 (plateau deliveries at L = 12 h)
    by = port_index(port)
    chk = []
    for r in nm:
        if r["kind"] != "A1":
            continue
        sc = dict(base="base", slow="slow", longslow="longslow", lane="lane")[r["scen"]]
        if r["p"] == "0.5":
            if sc != "base":
                continue
            sc = "fastcrane"
        p = float(r["p"]) * 3600
        d = by[(sc, r["mode"], "S1", 10, "0", "fcfs")]
        tmin = min(fl(x["port_h"]) for x in d.values())
        chk.append(dict(src="Table 5", scen=sc, mode=r["mode"], ratio_cut=fl(r["ratio_cut"]), ratio_zone1=fl(r["ratio_zone1"]), observed_h=round(tmin, 2),
                        limit_h=10 * p / 3600, road_observed=int(tmin > 10 * p / 3600 * 1.02),
                        agree_cut=int((fl(r["ratio_cut"]) > 1) <= (tmin > 10 * p / 3600 * 1.02)),
                        agree_zone1=int((fl(r["ratio_zone1"]) > 1) == (tmin > 10 * p / 3600 * 1.02))))
    for r in [r for r in lr if r["p"] == "1.0"]:
        v = float(r["v"])
        rs = [x for x in sens0 if x["sub"] == "e3" and x["par"] == "v" and abs(float(x["val"]) - v) < 1e-9 and x["scen"] == "lane" and x["mode"] == r["mode"]
              and x["rep"] == "occ" and x["port_h"]]
        if not rs:
            continue
        tmin = min(float(x["port_h"]) for x in rs)
        pc, pz = fl(r["ell_cut"]), fl(r["ell_zone1"])
        chk.append(dict(src="Appendix C3 (long single lane 1,200 m)", scen=f"v = {v:g} km/h", mode=r["mode"], ell_cut=pc, ell_zone1=pz, observed_h=round(tmin, 2), limit_h=10.0,
                        road_observed=int(tmin > 10.2), agree_cut=int((pc is not None and 1200 > pc) <= (tmin > 10.2)),
                        agree_zone1=int((pz is not None and 1200 > pz) == (tmin > 10.2))))
    wcsv(out / "table_critical_check.csv", chk)
    L = ["# Critical single-lane length\n",
         "Minimum time one monopile occupies the single lane: τ_cut = t_ℓ + t_e (round trip over the cut; holds for any dispatch rule and any "
         "quay-zone capacity: the cut term of W1); when the quay zone holds only one vehicle set at a time (as first-come-first-served with Q_h = 0 "
         "does in practice) τ_zone1 = t_ℓ + d_q + t_e^occ (in cradle mode d_q includes the 30 min set-down, direct lift does not). For τ > p no "
         "fleet lets the vessel crane lift continuously; the critical length ℓ* is the single-lane length at which τ = p.\n",
         "## Critical length ℓ* (m): loaded speed × p (S = 1)\n", "| Cradle | p (h) | " + " | ".join(f"{v} km/h" for v in sorted({float(r['v']) for r in lr})) + " |",
         "|---|---:|" + "---:|" * len({r['v'] for r in lr})]
    for m in ("pull_in", "on_road"):
        for pp in ("0.5", "1.0", "1.5"):
            rs = sorted((r for r in lr if r["p"] == pp and r["mode"] == m), key=lambda r: float(r["v"]))
            L.append(f"| {MODE_ZH[m]} | {pp} | " + " | ".join(f"{r['ell_cut'] or '>6000'} / {r['ell_zone1'] or '>6000'}" for r in rs) + " |")
    L.append("\n(Each cell: critical length for τ_cut / for τ_zone1; 0 means the road limits at any length: the quay-front cut of the roadside "
             "cradle already includes the 30 min set-down, which exceeds p = 0.5 h.)\n")
    L += ["## τ/p of named cases (S = 1)\n", "| Port type / shipyard | Scenario | Cradle | p (h) | Cut | t_ℓ | t_e | d_q | Q | τ_cut/p | τ_zone1/p | τ_W/p |",
          "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in nm:
        L.append(f"| {r['kind']} | {r['scen']} | {MODE_ZH[r['mode']]} | {r['p']} | {r['res']} | {r['tl']} | {r['te']} | {r['dq']} | {r['Q']} | {r['ratio_cut']} | "
                 f"{r['ratio_zone1']} | {r['ratio_w']} |")
    L += ["\n## Cross-check against Table 5 and Appendix C3\n",
          "Road-limited (observed) = minimum port time more than 2% above the vessel-crane lower limit. agree_cut: τ_cut > p implies an observed "
          "road limit (sufficient condition); agree_zone1: τ_zone1 > p agrees with the observation.\n",
          "| Source | Scenario | Cradle | Criterion | Minimum port time h | Road-limited | Agrees with τ_cut | Agrees with τ_zone1 |", "|---|---|---|---|---:|---:|---:|---:|"]
    for c in chk:
        crit = f"{c.get('ratio_cut')} / {c.get('ratio_zone1')}" if "ratio_cut" in c else f"ℓ* {c.get('ell_cut')} / {c.get('ell_zone1')}"
        L.append(f"| {c['src']} | {SCEN_ZH.get(c['scen'], c['scen'])} | {MODE_ZH[c['mode']]} | {crit} | {c['observed_h']} | {c['road_observed']} | {c['agree_cut']} | {c['agree_zone1']} |")
    L.append(f"\nAll {len(chk)} rows: agree with τ_cut {sum(c['agree_cut'] for c in chk)}, agree with τ_zone1 {sum(c['agree_zone1'] for c in chk)}.")
    # Table 6: are the plateau deliveries at L = 12 h, G = 24 h, pull-in, S = 1 below 12 (window criterion)
    t6 = []
    for r in win:
        if r["S"] == "1" and r["Lp"] == "12":
            t6.append((r["v"], fl(r["ell_window"])))
    L.append("\nTable 6 check: critical length of the window criterion (L = 12 h, S = 1) "
             + "; ".join(f"{v} km/h: {e} m" for v, e in t6) + ". The long single lane of 1,200 m (1 km/h) exceeds it, Table 6 plateau deliveries "
             "6–11 < 12; the 200 m baseline block (2.5 km/h) is far below it, Table 6 plateau deliveries 12.")
    md(out, "table_critical.md", L)
    return chk


# ---------------------------------------------------------------- mixed-lifting rows of Table 6
def table6x(mix6, e4, out):
    def summarise(rows, lift):
        by = collections.defaultdict(dict)
        for r in rows:
            by[(r["kind"], r["scen"], r["mode"], i(r["L"]), i(r["G"]), i(r["S"]), r["rule"])][i(r["K"])] = r
        tab = []
        for kind in ("A1", "A2", "A3"):
            for sc in ("base", "lane"):
                for m in ("pull_in", "on_road"):
                    g = lambda S, ru: by[(kind, sc, m, 12, 24, S, ru)]
                    if not g(1, "fcfs"):
                        continue
                    N = {(S, K): i(g(S, "fcfs")[K]["sim"]) for S in range(1, 7) for K in range(1, 11)}
                    pl = {(S, ru): plateau({K: i(r["sim"]) for K, r in g(S, ru).items()}) for S in (1, 3, 6) for ru in ("fcfs", "convoy")}
                    k1 = [N[(S + 1, 1)] - N[(S, 1)] for S in range(1, 6)]
                    top = [N[(S + 1, 10)] - N[(S, 10)] for S in range(1, 6)]
                    eq = next((S for S in range(1, 7) if N[(S, 1)] >= N[(1, 2)]), None)
                    tab.append(dict(lift=lift, kind=kind, scen=sc, mode=m, k_dagger=round(float(g(1, "fcfs")[10]["k_dagger"]), 2),
                                    **{f"S{S}_{ru}": f"{pl[(S, ru)][0]} ({pl[(S, ru)][1]})" for S in (1, 3, 6) for ru in ("fcfs", "convoy")},
                                    per_cradle=round(sum(k1) / 5, 1), extra_cradles=(eq - 1) if eq else ">5", at_plateau=round(sum(top) / 5, 1),
                                    n_S1_K1=N[(1, 1)], n_S1_K2=N[(1, 2)], over=sum(i(r["sim"]) > i(r["w1g"]) for d in by.values() for r in d.values())))
        return tab
    base = summarise([r for r in e4 if r["lift"] == "cradle" or i(r["S"]) >= 1], "cradle")
    mix = summarise(mix6, "mixed")
    wcsv(out / "table6x.csv", base + mix)
    L = ["# Table 6 extra rows: mixed lifting (in cradle mode the vessel crane may also lift from the vehicle), L = 12 h, G = 24 h\n",
         "Plateau K (deliveries): first-come-first-served / convoy; piles per cradle (K = 1, mean over S = 1→6); cradles substituted by the second "
         "vehicle set (cradles needed at K = 1 to reach K = 2, S = 1, minus 1); piles per cradle on the plateau (K = 10). "
         "Cradle rows from E4 (same source as Table 6 of the manuscript).\n",
         "| Lifting | Port type | Scenario | Cradle | K† | S = 1 | S = 3 | S = 6 | Piles / cradle | Second set ≈ cradles | Piles / cradle on plateau | "
         "K = 1 / 2 (S = 1) |",
         "|---|---|---|---|---:|---|---|---|---:|---|---:|---|"]
    for t in base + mix:
        if t["mode"] != "pull_in":
            continue
        L.append(f"| {'cradle' if t['lift'] == 'cradle' else 'mixed lifting'} | {t['kind']} | {SCEN_ZH[t['scen']]} | {MODE_ZH[t['mode']]} | {t['k_dagger']} | "
                 f"{t['S1_fcfs']} / {t['S1_convoy']} | {t['S3_fcfs']} / {t['S3_convoy']} | {t['S6_fcfs']} / {t['S6_convoy']} | {t['per_cradle']} | {t['extra_cradles']} | "
                 f"{t['at_plateau']} | {t['n_S1_K1']} / {t['n_S1_K2']} |")
    L.append(f"\nMixed-lifting grid, {len(mix6)} points: above W1′ {sum(i(r['sim']) > i(r['w1g']) for r in mix6)}, checker failures "
             f"{sum(r['check_ok'] != '1' for r in mix6)}.")
    # mixed lifting vs cradle: difference in piles at the same point
    cr = {(r["kind"], r["scen"], r["mode"], r["rule"], i(r["K"]), i(r["S"])): i(r["sim"]) for r in e4
          if r["lift"] == "cradle" and i(r["L"]) == 12 and i(r["G"]) == 24}
    dd = collections.Counter()
    for r in mix6:
        k = (r["kind"], r["scen"], r["mode"], r["rule"], i(r["K"]), i(r["S"]))
        d = i(r["sim"]) - cr[k]
        dd[(r["scen"], r["mode"], "+" if d > 0 else ("0" if d == 0 else "−"))] += 1
    L.append("\nPiles at the same point, mixed lifting − cradle: " + "; ".join(f"{SCEN_ZH[s]}, {MODE_ZH[m]}: more {dd[(s, m, '+')]}, same {dd[(s, m, '0')]}, fewer {dd[(s, m, '−')]}"
                                                for s in ("base", "lane") for m in ("pull_in", "on_road")) + ".")
    md(out, "table6x.md", L)
    return base, mix, dd


# ---------------------------------------------------------------- dependence of mixed lifting and direct lift on the release time x
def mixx(rows, port, e4, mix6, out):
    by = port_index(port)
    pr = [r for r in rows if r["what"] == "port"]
    tab = []
    for sc in ("base", "longslow", "lane", "fastcrane"):
        p = 1800.0 if sc == "fastcrane" else 3600.0
        for m in ("pull_in", "on_road"):
            for Ks in ("1", "best"):
                pick = (lambda K: True) if Ks == "best" else (lambda K: K == 1)
                cr = {a: min(fl(r["port_h"]) for K, r in by[(sc, m, a, 10, "0", "fcfs")].items() if pick(K)) for a in ("S1", "S3")}
                for arr in ("S0", "S1m", "S3m"):
                    xs = {}
                    for x in ("0.0", "0.25", "0.5", "0.75", "1.0"):
                        xs[x] = min(fl(r["port_h"]) for r in pr if r["scen"] == sc and r["mode"] == m and r["arr"] == arr and r["x"] == x and pick(i(r["K"])))
                    ref = cr["S1"] if arr in ("S0", "S1m") else cr["S3"]
                    tab.append(dict(scen=sc, mode=m, K="1" if Ks == "1" else "1–8 shortest", arr=arr, cradle=round(ref, 2), **{f"x{x}": round(v, 2) for x, v in xs.items()},
                                    worse_from=next((x for x, v in xs.items() if v > ref + 1e-6), ""), xp_hd=f"x = {1800.0 / p:g}"))
    wcsv(out / "table_mixx.csv", tab)
    ref4 = {(r["scen"], r["mode"], i(r["K"]), i(r["S"])): i(r["sim"]) for r in e4
            if r["kind"] == "A1" and r["lift"] == "cradle" and i(r["L"]) == 12 and i(r["G"]) == 24 and r["rule"] == "fcfs"}
    x0 ={(r["scen"], r["mode"], i(r["K"]), i(r["S"])): i(r["sim"]) for r in mix6 if r["kind"] == "A1" and r["rule"] == "fcfs"}
    e4d = {(r["scen"], r["mode"], i(r["K"])): i(r["sim"]) for r in e4
           if r["kind"] == "A1" and i(r["S"]) == 0 and i(r["L"]) == 12 and i(r["G"]) == 24 and r["rule"] == "fcfs"}
    win = [r for r in rows if r["what"] == "win"]
    cnt = []
    for x in ("0.0", "0.25", "0.5", "0.75", "1.0"):
        for Sn in (1, 3):
            pts = [(k, v) for k, v in x0.items() if k[3] == Sn and k[0] in ("base", "lane")] if x == "0.0" else \
                [((r["scen"], r["mode"], i(r["K"]), i(r["S"])), i(r["sim"])) for r in win if i(r["S"]) == Sn and r["x"] == x]
            cnt.append(dict(x=x, what=f"S = {Sn} mixed lifting − cradle", more=sum(v > ref4[k] for k, v in pts), same=sum(v == ref4[k] for k, v in pts),
                            fewer=sum(v < ref4[k] for k, v in pts)))
        pts = [(k, e4d[k]) for k in e4d if k[0] in ("base", "lane")] if x == "0.0" else \
            [((r["scen"], r["mode"], i(r["K"])), i(r["sim"])) for r in win if i(r["S"]) == 0 and r["x"] == x]
        cnt.append(dict(x=x, what="S = 0 direct lift − S = 1 cradle", more=sum(v > ref4[(k[0], k[1], k[2], 1)] for k, v in pts),
                        same=sum(v == ref4[(k[0], k[1], k[2], 1)] for k, v in pts), fewer=sum(v < ref4[(k[0], k[1], k[2], 1)] for k, v in pts)))
    wcsv(out / "table_mixx_win.csv", cnt)
    L = ["# Dependence of mixed lifting and direct lift on the vehicle release time x\n",
         "x is the fraction of the lift cycle that a direct lift (including the piles lifted from the vehicle under mixed lifting) additionally waits "
         "at the quay berth before the vehicle is released: release time = lift start + x·p. Cradle mode does not depend on x.\n",
         "## Port time to load 10 piles (K = 1, and the minimum over K = 1–8; Q_h = 0, first-come-first-served, h)\n",
         "| Scenario | Cradle | K | Lifting | Cradle mode (same S) | x = 0 | 0.25 | 0.5 | 0.75 | 1 | Slower than cradle from x | x·p = h_d at |",
         "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for t in tab:
        L.append(f"| {SCEN_ZH[t['scen']]} | {MODE_ZH[t['mode']]} | {t['K']} | {ARR_ZH[t['arr']]} | {t['cradle']} | {t['x0.0']} | {t['x0.25']} | {t['x0.5']} | {t['x0.75']} | "
                 f"{t['x1.0']} | {t['worse_from'] or '—'} | {t['xp_hd']} |")
    L += ["\n## Window deliveries (A1 subgrid of E4: baseline / long single lane × cradle type × K = 1–10, L = 12 h, G = 24 h): number of points "
          "compared with cradle mode at the same point\n",
          "| x | Comparison | More | Same | Fewer |", "|---|---|---:|---:|---:|"]
    L += [f"| {c['x']} | {c['what']} | {c['more']} | {c['same']} | {c['fewer']} |" for c in cnt]
    md(out, "table_mixx.md", L)
    return tab, cnt


def recheck(out):
    d = ROOT / "results" / DIRS["recheck"]
    (out / "table_recheck.md").write_text((d / "summary.md").read_text(encoding="utf-8"), encoding="utf-8")


# ---------------------------------------------------------------- figures of published projects
def pub(rows, out):
    o = [r for r in rows if r["pub"] == "out"]
    n = [r for r in rows if r["pub"] == "in"]
    t = [r for r in rows if r["pub"] == "tide"]
    HZ = dict(base="this paper 30 + 30 min", ronne="Rønne handling (h_p 2 h, h_d 0.5 h)")
    L = ["# Reproduction of figures from published projects\n",
         "## Rønne load-out: 3 piles per vessel, released 12 h before the installation vessel arrives (G = 12 h), vessel crane 1 h "
         "(mode of Kassels Fig. 19)\n",
         "Kassels model (Appendix F, zero-overlap schedule): TO1 (1 support; lift the pile on the vehicle first, the vehicle immediately fetches the "
         "third pile, then lift the pile on the support) 3.311 h, TO2 (2 supports) 2.994 h; validation run 3.316 h (Appendix E). "
         "Rønne geometry: shortest distance from the saddle rows to the cradle berth 250 m (Appendix D, storage area → quayside location). "
         "Rønne handling: pick-up and placing at the Fig. 19 modes (load-out from the vehicle 2 h = h_p, "
         "from the support 2.5 h = h_p + h_d), driving counted separately by distance (§4.3: process module + transport module). "
         "\"Kassels order\" applies the lift order of §4.3 (one pile pre-placed on 1 support and one on the vehicle; lift the pile on the vehicle "
         "first, the vehicle immediately fetches the third pile, then lift the pile on the support) with the trip durations of this model; "
         "it is meaningful only for the TO1 configuration (S = 1 mixed lifting, 1 vehicle set), other rows are blank; L*(3) is the lower bound for "
         "any dispatch rule. Simulation: first-come-first-served (the pile booked first is lifted first).\n",
         "| Geometry | Route m | Handling | Cradle | Lifting | K | Simulated port h | Kassels order h (TO1 only) | L*(3) h | Lift mode per pile |",
         "|---|---:|---|---|---|---:|---:|---:|---:|---|"]
    for r in o:
        ko = f"{float(r['kassels_h']):.2f}" if (r["arr"], r["K"]) == ("S1m", "1") else ""
        L.append(f"| {'Rønne' if r['geo'] == 'ronne' else 'A1 baseline'} | {r['route_m']} | {HZ[r['hand']]} | {MODE_ZH[r['mode']]} | {ARR_ZH[r['arr']]} | {r['K']} | "
                 f"{float(r['port_h']):.2f} | {ko} | {float(r['lstar_lo']):.2f} | {r['how']} |")
    VZ = dict(base="this model (30 min saddle set-down, steering stop)", hy0="no saddle set-down (h_y = 0)", nosteer="no steering stop", both="both removed")
    L += ["\n## Rønne load-in (barge): 3 piles, ramp always open, shortest ramp-to-saddle-row distance about 400 m\n",
          "Kassels model TI0 (no temporary supports): mean barge port time 12.940 h (Appendix F); unloading duration triangular 3/4/5 h (Fig. 19, "
          "mean 4 h; includes ramp installation, ballasting, jacking onto the saddles, removing the grillage), "
          "vehicle released on reaching the yard (§4.3). This paper records the tail of the 3rd pile's vehicle leaving the ramp (F_ramp) and the "
          "3rd pile set down on the saddles (F_yard); with the 4 h mean the sources of the difference are separated.\n",
          "| K | RoRo h | Variant | Route m | 3rd pile leaves ramp h | 3rd pile on saddles h |", "|---:|---:|---|---:|---:|---:|"]
    for r in n:
        L.append(f"| {r['K']} | {r['roro']} | {VZ[r['var']]} | {r['route_m']} | {float(r['ramp_h']):.2f} | {float(r['yard_h']):.2f} |")
    L += ["\n## Eemshaven, unloading 1 → 2 piles per tide (Theorem 3): A1 baseline geometry, 3 piles released per tide, 4 tides\n",
          "Each cell: piles unloaded in each tide in simulation (separated by /); in brackets the Theorem 3 upper bound per tide. ρ is the ramp "
          "operation (on-board work + empty and loaded driving on the ramp), c_u the minimum interval between two successive ramp operations of "
          "one vehicle set.\n",
          "| K | Tide window h | " + " | ".join(f"on-board work {x} h" for x in sorted({r['rho'] for r in t}, key=float)) + " |", "|---:|---:|" + "---|" * len({r['rho'] for r in t})]
    for K in ("1", "2"):
        for Lt in sorted({r["Lt"] for r in t}, key=float):
            rs = sorted((r for r in t if r["K"] == K and r["Lt"] == Lt), key=lambda r: float(r["rho"]))
            L.append(f"| {K} | {Lt} | " + " | ".join(f"{r['n_ramp']} ({r['thm3']})" for r in rs) + " |")
    rr = sorted({(r["rho"], round(float(r["rho_s"]) / 3600, 2), round(float(r["c_u"]) / 3600, 2)) for r in t}, key=lambda x: float(x[0]))
    L.append("\nρ, c_u (h): " + "; ".join(f"on board {a} h → ρ = {b}, c_u = {c}" for a, b, c in rr) + ".")
    L.append("Shortening the on-board work shortens both ρ and c_u: with one vehicle set, 2 piles per tide need ρ + c_u ≤ L (fleet term); with two "
             "sets only ρ ≤ L/2 is needed (ramp term).")
    md(out, "table_pub.md", L)
    return o, n, t


# ---------------------------------------------------------------- three extra rows for Appendix C
PAR = dict(none="baseline", platlen="empty vehicle length", latc="lateral clearance", longc="longitudinal clearance")
UNIT = dict(none=lambda v: "—", platlen=lambda v: f"{float(v):g} m", latc=lambda v: f"{float(v):g} m", longc=lambda v: f"{float(v):g} m")


def sens(rows, base, out):
    rows = [r for r in base if r["par"] == "none" and r["sub"] in ("e1", "e4", "e3")] + rows
    lv = list(dict.fromkeys((r["par"], r["val"]) for r in rows))
    A, B, Cc = [], [], []
    for par, val in lv:
        e1 = [r for r in rows if r["sub"] == "e1" and r["par"] == par and r["val"] == val]
        for sc in ("base", "lane"):
            rs = [r for r in e1 if r["scen"] == sc]
            reg = collections.Counter(r["regime"] for r in rs)
            A.append(dict(par=par, val=val, scen=sc, n=len(rs), sim=sum(i(r["sim"]) for r in rs), tie=f"{sum(r['sim'] == r['w1g'] for r in rs) / len(rs):.1%}",
                          over=sum(i(r["sim"]) > i(r["w1g"]) for r in rs), reg=f"{reg['interface']} / {reg['staging']} / {reg['flow']}"))
        e4r = [r for r in rows if r["sub"] == "e4" and r["par"] == par and r["val"] == val]
        for sc in ("base", "lane"):
            for m in ("on_road", "pull_in"):
                g = collections.defaultdict(dict)
                for r in e4r:
                    if r["scen"] == sc and r["mode"] == m:
                        g[i(r["S"])][i(r["K"])] = r
                pl = {S: plateau({k: i(r["sim"]) for k, r in d.items()}) for S, d in g.items()}
                kd = float(g[1][10]["k_dagger"])
                gain = [pl[S + 1][1] - pl[S][1] for S in range(1, 6)]
                B.append(dict(par=par, val=val, scen=sc, mode=m, k_dagger=round(kd, 2), plat_S1=f"{pl[1][0]} ({pl[1][1]})", plat_S3=f"{pl[3][0]} ({pl[3][1]})",
                              eq_ceil=int(pl[1][0] == math.ceil(kd - 1e-9)), per_cradle=round(sum(gain) / 5, 2)))
        e3 = [r for r in rows if r["sub"] == "e3" and r["par"] == par and r["val"] == val]
        for sc in ("base", "lane"):
            for m in ("on_road", "pull_in"):
                po = [float(r["port_h"]) for r in e3 if r["scen"] == sc and r["mode"] == m and r["rep"] == "occ" and r["port_h"]]
                pf = [float(r["port_h"]) for r in e3 if r["scen"] == sc and r["mode"] == m and r["rep"] == "fix" and r["port_h"]]
                Cc.append(dict(par=par, val=val, scen=sc, mode=m, occ=round(min(po), 2), fix=round(min(pf), 2), ratio=round(min(po) / min(pf), 3)))
    wcsv(out / "tableC3x.csv", [dict(t="e1", **a) for a in A] + [dict(t="e4", **b) for b in B] + [dict(t="e3", **c) for c in Cc])
    L = ["# Appendix C, three extra rows: empty vehicle length, lateral clearance, longitudinal clearance (others at baseline; the baseline row "
         "from the committed sens run)\n",
         "## C1 type: reduced E1 grid (L = 4, 12 h; K = 1–6; S = 0, 1, 3; G = 3, 24 h; both cradle types)\n",
         "| Parameter | Value | Scenario | Points | Total piles | Equal to W1′ | Above W1′ | Regime interface / staging / flow |",
         "|---|---|---|---:|---:|---:|---:|---|"]
    L += [f"| {PAR[a['par']]} | {UNIT[a['par']](a['val'])} | {SCEN_ZH[a['scen']]} | {a['n']} | {a['sim']} | {a['tie']} | {a['over']} | {a['reg']} |" for a in A]
    L += ["\n## C2 type: E4 (L = 12 h, G = 24 h, fcfs): K†, plateau K (piles) at S = 1 and S = 3, plateau = ⌈K†⌉, piles per cradle on the "
          "plateau\n",
          "| Parameter | Value | Scenario | Cradle | K† | Plateau S = 1 | Plateau S = 3 | = ⌈K†⌉ | Piles / cradle |", "|---|---|---|---|---:|---|---|---:|---:|"]
    L += [f"| {PAR[b['par']]} | {UNIT[b['par']](b['val'])} | {SCEN_ZH[b['scen']]} | {MODE_ZH[b['mode']]} | {b['k_dagger']} | {b['plat_S1']} | {b['plat_S3']} | "
          f"{'yes' if b['eq_ceil'] else 'no'} | {b['per_cradle']} |" for b in B]
    L += ["\n## C3 type: minimum port time to load 10 piles (K = 1–8, S = 1; fixed duration uses conflict-free driving times)\n",
          "| Parameter | Value | Scenario | Cradle | Road occupancy h | Fixed duration h | Ratio |",
          "|---|---|---|---|---:|---:|---:|"]
    L += [f"| {PAR[c['par']]} | {UNIT[c['par']](c['val'])} | {SCEN_ZH[c['scen']]} | {MODE_ZH[c['mode']]} | {c['occ']} | {c['fix']} | {c['ratio']} |" for c in Cc]
    md(out, "tableC3x.md", L)
    return A, B, Cc


def sens5(rows, e5, out):
    """Lateral clearance applied to E5 (two loaded streams meeting head-on on a 20 m two-lane road): total of both streams and
    unloaded piles; c_lat = 1 m takes the same key from the committed E5 run."""
    base = {r["key"]: r for r in e5}
    tab = []
    for lat in ("1", "2.0", "3.0"):
        rs = [base[r["key"].rsplit("|lat=", 1)[0]] for r in rows if r["val"] == "2.0"] if lat == "1" else [r for r in rows if r["val"] == lat]
        for sc in ("base", "longslow"):
            for fleet in ("ded", "plain", "shared", "shared1"):
                for Kt in ("2", "4"):
                    g = [r for r in rs if r["scen"] == sc and r["fleet"] == fleet and r["Kt"] == Kt]
                    tab.append(dict(lat=lat, scen=sc, fleet=fleet, Kt=Kt, n=len(g), total=sum(i(r["sim"]) + i(r["n_ramp"]) for r in g),
                                    n_u=sum(i(r["n_ramp"]) for r in g), over=sum(i(r["sim"]) + i(r["n_ramp"]) > i(r["joint_ub"]) for r in g)))
    wcsv(out / "tableC4x.csv", tab)
    get = {(t["lat"], t["scen"], t["fleet"], t["Kt"]): t for t in tab}
    L = ["# Appendix C supplement: lateral clearance × E5 (simultaneous unloading and loading, pull-in, S = 1, fcfs; total over x = 0, 0.5, 1 "
         "× tidal 6 h / continuous)\n",
         "With c_lat = 1 m the 20 m two-lane road has capacity 21 m and two loaded vehicles, 2 × 10.5 = 21 m, can just pass each other; with 2 m, "
         "2 × 11.5 = 23 > 22, and with 3 m, 2 × 12.5 = 25 > 23: two opposing loaded vehicles cannot pass.\n",
         "| Scenario | Fleet | K_t | Both streams total (of which unloading): c_lat = 1 / 2 / 3 m | Above joint upper bound |", "|---|---|---:|---|---:|"]
    FZ = dict(ded="dedicated unloading vehicles", plain="shared (no priority)", shared="shared (unloading dispatched first)", shared1="shared (at most 1 unloading)")
    for sc in ("base", "longslow"):
        for fleet in ("ded", "plain", "shared", "shared1"):
            for Kt in ("2", "4"):
                a = [get[(lat, sc, fleet, Kt)] for lat in ("1", "2.0", "3.0")]
                L.append(f"| {SCEN_ZH[sc]} | {FZ[fleet]} | {Kt} | {' / '.join(f'{x['total']} ({x['n_u']})' for x in a)} | {sum(x['over'] for x in a)} |")
    md(out, "tableC4x.md", L)
    return tab


def table7_diam(facts, out):
    w = facts["width"]
    L = ["# Table 7 with a diameter column\n",
         "| Monopile | Length m | Diameter m | Passes 10 m single lane (D ≤ w) | Passes 12 m single lane | Road width for empty and loaded to pass ≥ | "
         "Road width for two loaded to pass ≥ |",
         "|---|---:|---:|---|---|---:|---:|"]
    for x in w["e7"]:
        L.append(f"| {x['lev']} m class | {x['Lv']:g} | {x['D']:g} | {'yes' if x['fits_10m'] else 'no'} | {'yes' if x['fits_12m'] else 'no'} | {x['loaded_empty_threshold']:.2f} | "
                 f"{x['two_loaded_threshold']:.2f} |")
    L.append("\nWidth rule of the model: resource capacity = road width + c_lat, a loaded vehicle occupies min(capacity, D + c_lat); when the "
             "diameter exceeds the road width the loaded vehicle counts as exclusive and the model does not judge feasibility; "
             "E7 uses a 12 m single lane, and all four classes satisfy D ≤ 12 m.")
    md(out, "table7_diam.md", L)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(ROOT))
    h = hashlib.sha256(Path(__file__).read_bytes())
    for k in sorted(DIRS):
        h.update(path(k).read_bytes())
    for f in EXTRA:
        h.update((ROOT / f).read_bytes())
    out = ROOT / "results" / f"windport_extra_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    port, fix, e3, e4 = load("port"), load("fix"), load("e3"), load("e4")
    ex = example(load("example"), e4, out)
    t5, same, diff = table5x(port, fix, e3, out)
    cst, best = cost(port, out)
    chk = critical(load("critical"), port, e3, load("sens0"), e4, out)
    b6, m6, dd = table6x(load("mix6"), e4, out)
    pub(load("pub"), out)
    mixx(load("mixx"), port, e4, load("mix6"), out)
    recheck(out)
    sens(load("sens"), load("sens0"), out)
    s5 = sens5(load("sens5"), load("e5"), out)
    facts = json.loads(path("facts").read_text(encoding="utf-8"))
    table7_diam(facts, out)
    rr = [json.loads(path(k).read_text(encoding="utf-8")) for k in ("random", "random2", "random3", "random4")]
    rnd = {k: (sum(r[k] for r in rr) if k != "gen" else "+".join(r["gen"] for r in rr)) for k in rr[0]}     # two main parts + port + hold, summed
    L = ["# Summary (generated by windport_report3.py)\n"]
    L.append(f"- sens5 (lateral clearance × E5): {len(load('sens5'))} points; checker failures {sum(r['check_ok'] != '1' for r in load('sens5'))}; "
             f"above joint upper bound {sum(t['over'] for t in s5 if t['lat'] != '1')}.")
    for k in ("port", "fix", "mix6", "sens", "pub", "mixx"):
        rs = load(k)
        L.append(f"- {k}: {len(rs)} rows; checker failures {sum(r['check_ok'] != '1' for r in rs)}" +
                 (f"; above W1′ {sum(1 for r in rs if r.get('w1g') and r.get('rep') != 'fix' and i(r['sim']) > i(r['w1g']))}" if k in ("mix6", "sens") else "") +
                 (f"; W′(port time) < n_v {sum(1 for r in rs if r['w_at_port'] not in ('', None) and i(r['w_at_port']) < i(r['n_v']))}; port time < L* "
                  f"{sum(1 for r in rs if r['lstar_lo'] and fl(r['port_h']) < fl(r['lstar_lo']) - 1e-9)}" if k == "port" else ""))
    L.append(f"- Table 5 extra columns: identical to the committed E3 port times at {same} points, different at {len(diff)} points.")
    L.append(f"- Critical-length cross-check: {len(chk)} rows, agree with τ_cut {sum(c['agree_cut'] for c in chk)}, agree with τ_zone1 {sum(c['agree_zone1'] for c in chk)}.")
    L.append(f"- Random port-layout regression ({DIRS['random']}, {DIRS['random2']}, {DIRS['random3']}, {DIRS['random4']}, total): " + json.dumps(rnd, ensure_ascii=False))
    for k in ("random", "random2", "random3", "random4"):
        L.append(f"  - {DIRS[k]}: " + path(k).read_text(encoding="utf-8").replace("\n", " "))
    md(out, "summary.md", L)
    (out / "inputs.json").write_text(json.dumps(dict({k: f"results/{DIRS[k]}/{FILES.get(k, 'points.csv')}" for k in sorted(DIRS)}, extra=EXTRA),
                                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
