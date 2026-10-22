"""Figures 4–7, Table 2 (with W1′ and convoy columns), Table 4, the gate-holding-place table (with a convoy column), the off-road
pocket table, the Appendix C sensitivity tables and a summary (draft figures).
Reads only the committed points.csv, summary.md / summary.json and sites.md, not points/, so it can be rebuilt from a clean
checkout. Figures containing the real maps are not drawn (E6 is shown as curves only).

Inputs (run directories registered in DIRS):
  e4, e5, e6, e7, pocket, conv, e2c, sens  experiments/windport_runs.py --part …
  sens7    experiments/windport_sens_e7.py (Appendix C, E7 part)
  random   experiments/windport_random.py (random port-archetype regression, 20,000 cases)
  chain    experiments/windport_chain_check.py (exhaustive check of two-block chains for the chain cut)
  sites    experiments/windport_sites.py (E6 site selection)
  E1, E1h, E2, E2long runs (e1, e1h, e2, e2long entries; baselines for the pocket, convoy and Table 2 comparisons)
Output results/windport_runs_report_<first 12 hex digits of the SHA-256 of the inputs and this script>/.

Run: .venv/Scripts/python.exe experiments/windport_report2.py
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
DIRS = dict(e4="runs/e4", e5="runs/e5", e6="runs/e6",
            e7="runs/e7", pocket="runs/pocket", conv="runs/convoy_hold",
            e2c="runs/e2_convoy", sens="runs/sens", sens7="runs/sens_e7",
            random="runs/random_bound", chain="runs/chain", sites="tables/sites",
            e1="runs/e1", e1h="runs/e1_hold", e2="runs/e2",
            e2long="runs/e2_long")
FILES = dict(random="summary.json", chain="summary.md", sites="sites.md")
META = {"Software": None}
SCEN_ZH = dict(base="Base", slow="1 km/h", long="Long corridor", longslow="Long corridor + 1 km/h", lane="Long single lane + 1 km/h",
               fastcrane="Crane 0.5 h", joint="Simultaneous unloading/loading (dedicated unloading vehicle)",
               jointshared="Simultaneous unloading/loading (shared fleet)")
MODE_ZH = dict(on_road="Roadside cradle", pull_in="Pull-in cradle")
SC5 = ["base", "slow", "longslow", "lane", "fastcrane"]
plt.rcParams.update({"font.family": ["Microsoft YaHei", "SimHei", "DejaVu Sans"], "axes.unicode_minus": False, "font.size": 8})


def path(k):
    return ROOT / "results" / DIRS[k] / FILES.get(k, "points.csv")


def load(k):
    return list(csv.DictReader(open(path(k), encoding="utf-8")))


def i(x):
    return int(float(x)) if x not in ("", None) else None


def save(fig, out, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, metadata=META)
    (out / name).write_bytes(buf.getvalue())
    plt.close(fig)


def wcsv(p, rows):
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def md(out, name, lines):
    (out / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def pct(a, b):
    return f"{a / b:.1%}" if b else "—"


def plateau(d):
    """{K: pile count} -> (smallest K reaching the maximum, maximum)."""
    mx = max(d.values())
    return min(k for k, v in d.items() if v >= mx), mx


def ceil_kd(x):
    return math.ceil(float(x) - 1e-9)


# ---------------------------------------------------------------- Fig. 4: fleet plateau and cradle-vehicle rate
def e4(rows, out):
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r["kind"], r["scen"], r["mode"], i(r["L"]), i(r["G"]), i(r["S"]), r["rule"])][i(r["K"])] = r
    tab, cmp_ = [], collections.Counter()
    for (kind, sc, m, L, G, S, rule), d in sorted(by.items()):
        if rule != "fcfs":
            continue
        dc = by[(kind, sc, m, L, G, S, "convoy")]
        kf, nf = plateau({k: i(r["sim"]) for k, r in d.items()})
        kc, nc = plateau({k: i(r["sim"]) for k, r in dc.items()})
        kw, nw = plateau({k: i(r["w1g"]) for k, r in d.items()})
        kd = float(d[max(d)]["k_dagger"])
        reg = d[kf]["regime"]
        ck = min(ceil_kd(kd), 10)
        w_ck, w_top = i(d[ck]["w1g"]), max(i(r["w1g"]) for r in d.values())
        tab.append(dict(kind=kind, scen=sc, mode=m, L=L, G=G, S=S, k_dagger=round(kd, 3), ceil_kd=ceil_kd(kd), plat_fcfs=kf, n_fcfs=nf, plat_convoy=kc,
                        n_convoy=nc, plat_w1g=kw, n_w1g=nw, regime_at_plateau=reg, n_fcfs_ceil=i(d[ck]["sim"]), n_convoy_ceil=i(dc[ck]["sim"]),
                        w1g_gain_after_ceil=w_top - w_ck, convoy_gain_after_ceil=max(i(r["sim"]) for r in dc.values()) - i(d[ck]["sim"]),
                        gain_dispatch=i(dc[ck]["sim"]) - i(d[ck]["sim"]), gain_vehicles=max(i(r["sim"]) for r in dc.values()) - i(dc[ck]["sim"]),
                        bound_gain=w_top - i(d[ck]["sim"]),
                        convoy_monotone=int(all(i(dc[k]["sim"]) <= i(dc[k + 1]["sim"]) for k in range(1, 10)))))
        cmp_[(sc, "S=0" if S == 0 else "S≥1", reg, "eq" if kf == ceil_kd(kd) else ("lt" if kf < ceil_kd(kd) else "gt"))] += 1
        cmp_[("convoy", sc, "S=0" if S == 0 else "S≥1", "eq" if kc == ceil_kd(kd) else ("lt" if kc < ceil_kd(kd) else "gt"))] += 1
    wcsv(out / "table_e4_plateau.csv", tab)
    # Cradle-vehicle rate: piles gained per extra cradle at K = 1 (fleet-limited side); how many cradles the second vehicle group is
    # worth (cradles needed at K = 1 to reach the count of K = 2, S = 1; cradle mode S ≥ 1); piles gained per extra cradle on the
    # plateau (K = 10): with a limited corridor, adding vehicles cannot replace these piles
    rate = []
    for kind in ("A1", "A2", "A3"):
        for sc in ("base", "lane"):
            for m in ("on_road", "pull_in"):
                for L in (6, 12, 24):
                    for G in (3, 24):
                        N = {(S, K): i(r["sim"]) for (k_, s_, m_, L_, G_, S, ru), d in by.items() if (k_, s_, m_, L_, G_, ru) == (kind, sc, m, L, G, "fcfs")
                             for K, r in d.items()}
                        k1 = [N[(S + 1, 1)] - N[(S, 1)] for S in range(1, 6)]
                        top = [N[(S + 1, 10)] - N[(S, 10)] for S in range(1, 6)]
                        eq = next((S for S in range(1, 7) if N[(S, 1)] >= N[(1, 2)]), None)
                        rate.append(dict(kind=kind, scen=sc, mode=m, L=L, G=G, piles_per_cradle_K1=round(sum(k1) / len(k1), 2),
                                         second_group_cradles=eq if eq is not None else ">6", n_S1_K1=N[(1, 1)], n_S1_K2=N[(1, 2)],
                                         piles_per_cradle_plateau=round(sum(top) / len(top), 2), n_S1_K10=N[(1, 10)], n_S6_K10=N[(6, 10)]))
    wcsv(out / "table_e4_rate.csv", rate)
    L_ = ["# Fig. 4 / E4 (draft): fleet plateau and cradle-vehicle rate\n",
          "Plateau = smallest K in 1–10 at which the pile count reaches its maximum (first-come-first-served fcfs; convoy dispatch gives the upper end); "
          "K† = c/(tl + te) (occupancy_times at K = 10). Regime = the W1′ term that binds at the plateau (interface / staging / flow).\n",
          "## fcfs plateau versus ⌈K†⌉ (counts over L × G × S × cradle type × archetype)\n",
          "| Scenario | Lifting | Regime at plateau | Plateau = ⌈K†⌉ | Plateau < ⌈K†⌉ | Plateau > ⌈K†⌉ |",
          "|---|---|---|---:|---:|---:|"]
    for sc in ("base", "lane"):
        for sg in ("S≥1", "S=0"):
            for reg in ("interface", "staging", "flow"):
                if any(cmp_[(sc, sg, reg, x)] for x in ("eq", "lt", "gt")):
                    L_.append(f"| {SCEN_ZH[sc]} | {sg} | {reg} | {cmp_[(sc, sg, reg, 'eq')]} | {cmp_[(sc, sg, reg, 'lt')]} | {cmp_[(sc, sg, reg, 'gt')]} |")
    L_ += ["\n## Convoy-dispatch plateau versus ⌈K†⌉\n", "| Scenario | Lifting | Plateau = ⌈K†⌉ | Plateau < ⌈K†⌉ | Plateau > ⌈K†⌉ |", "|---|---|---:|---:|---:|"]
    for sc in ("base", "lane"):
        for sg in ("S≥1", "S=0"):
            L_.append(f"| {SCEN_ZH[sc]} | {sg} | {cmp_[('convoy', sc, sg, 'eq')]} | {cmp_[('convoy', sc, sg, 'lt')]} | {cmp_[('convoy', sc, sg, 'gt')]} |")
    late = [t for t in tab if t["scen"] == "lane" and t["S"] >= 1 and t["plat_convoy"] > t["ceil_kd"]]
    L_ += ["\nConfigurations whose convoy plateau lies beyond ⌈K†⌉ (long single lane, S ≥ 1). Convoy gain = largest convoy count over "
           "K = 1–10 − fcfs count at ⌈K†⌉, split into the gain from changing the dispatch at the same ⌈K†⌉ (convoy − fcfs, both at ⌈K†⌉) "
           "and the gain from adding vehicles under convoy dispatch. Computable limit = W1′(K = 10) − fcfs count at ⌈K†⌉ (W1′ holds for "
           "any schedule, so no dispatch rule and no K ≤ 10 exceeds the fcfs plateau by more). The increase of W1′ itself beyond ⌈K†⌉, "
           "W1′(10) − W1′(⌈K†⌉), is listed separately: it is not a limit on the convoy gain (fcfs at ⌈K†⌉ stays below W1′).\n",
           "| Archetype | Cradle | L | G | S | ⌈K†⌉ | fcfs: plateau (piles) | Convoy: plateau (piles) | Convoy gain = dispatch + vehicles | "
           "Computable limit W1′(10) − fcfs(⌈K†⌉) | W1′ increase | Convoy monotone in K |",
           "|---|---|---:|---:|---:|---:|---|---|---|---:|---:|---|"]
    L_ += [f"| {t['kind']} | {MODE_ZH[t['mode']]} | {t['L']} | {t['G']} | {t['S']} | {t['ceil_kd']} | K={t['plat_fcfs']} ({t['n_fcfs']}) | "
           f"K={t['plat_convoy']} ({t['n_convoy']}) | {t['convoy_gain_after_ceil']} = {t['gain_dispatch']} + {t['gain_vehicles']} | {t['bound_gain']} | "
           f"{t['w1g_gain_after_ceil']} | {'yes' if t['convoy_monotone'] else 'no'} |" for t in late]
    L_.append(f"\nIn these {len(late)} configurations the convoy gain never exceeds the computable limit: {all(t['convoy_gain_after_ceil'] <= t['bound_gain'] for t in late)}"
              f" (all 216: {all(t['convoy_gain_after_ceil'] <= t['bound_gain'] for t in tab if t['scen'] == 'lane' and t['S'] >= 1)}); "
              f"configurations whose convoy gain exceeds the W1′ increase: {sum(1 for t in late if t['convoy_gain_after_ceil'] > t['w1g_gain_after_ceil'])}. "
              f"Configurations (of 216) where convoy is not monotone in K: {sum(1 for t in tab if t['scen'] == 'lane' and t['S'] >= 1 and not t['convoy_monotone'])}.")
    L_ += ["\n## Plateaus at L = 12 h, G = 24 h (fcfs / convoy / W1′; piles)\n", "| Archetype | Scenario | Cradle | S | K† | Plateau fcfs | convoy | W1′ |", "|---|---|---|---:|---:|---|---|---|"]
    for t in tab:
        if t["L"] == 12 and t["G"] == 24:
            L_.append(f"| {t['kind']} | {SCEN_ZH[t['scen']]} | {MODE_ZH[t['mode']]} | {t['S']} | {t['k_dagger']:.2f} | K={t['plat_fcfs']} ({t['n_fcfs']}) | "
                      f"K={t['plat_convoy']} ({t['n_convoy']}) | K={t['plat_w1g']} ({t['n_w1g']}) |")
    L_ += ["\n## Cradle-vehicle rate (fcfs, pull-in cradle)\n", "Piles gained per extra cradle at K = 1 (mean over S = 1→6); cradles the second "
           "vehicle group is worth (cradles needed at K = 1 to reach the count of K = 2, S = 1); piles gained per extra cradle on the plateau "
           "(K = 10, mean over S = 1→6).\n",
           "| Archetype | Scenario | L | G | Piles / cradle (K = 1) | Second group ≈ cradles | K = 1 / K = 2 (S = 1) | Piles / cradle (plateau) | "
           "Plateau S = 1 → S = 6 |", "|---|---|---:|---:|---:|---|---|---:|---|"]
    for r in rate:
        if r["mode"] == "pull_in":
            L_.append(f"| {r['kind']} | {SCEN_ZH[r['scen']]} | {r['L']} | {r['G']} | {r['piles_per_cradle_K1']} | {r['second_group_cradles']} | {r['n_S1_K1']} / {r['n_S1_K2']} | "
                      f"{r['piles_per_cradle_plateau']} | {r['n_S1_K10']} → {r['n_S6_K10']} |")
    md(out, "table_e4.md", L_)
    # Figure: one panel per archetype × scenario, pull-in, L = 12, G = 24: piles versus K (S = 0, 1, 3, 6), fcfs solid, convoy dotted,
    # W1′ dashed, vertical line at K†
    fig, ax = plt.subplots(2, 3, figsize=(12, 6.5), sharey="row")
    data = []
    for b, kind in enumerate(("A1", "A2", "A3")):
        for a, sc in enumerate(("base", "lane")):
            x = ax[a][b]
            for S, col in zip((0, 1, 3, 6), ("C0", "C1", "C2", "C3")):
                d, dc = by[(kind, sc, "pull_in", 12, 24, S, "fcfs")], by[(kind, sc, "pull_in", 12, 24, S, "convoy")]
                Ks = sorted(d)
                x.plot(Ks, [i(d[K]["sim"]) for K in Ks], "-o", color=col, ms=3, lw=1, label=f"S = {S}")
                x.plot(Ks, [i(dc[K]["sim"]) for K in Ks], ":", color=col, lw=1)
                ck = ceil_kd(d[10]["k_dagger"])
                top = max(i(d[K]["sim"]) for K in Ks)
                x.plot([K for K in Ks if K > ck and i(dc[K]["sim"]) > top], [i(dc[K]["sim"]) for K in Ks if K > ck and i(dc[K]["sim"]) > top], "x",
                       color=col, ms=5)
                x.plot(Ks, [i(d[K]["w1g"]) for K in Ks], "--", color=col, lw=0.8)
                data += [dict(kind=kind, scen=sc, S=S, K=K, fcfs=i(d[K]["sim"]), convoy=i(dc[K]["sim"]), w1g=i(d[K]["w1g"])) for K in Ks]
            kd = float(by[(kind, sc, "pull_in", 12, 24, 1, "fcfs")][10]["k_dagger"])
            x.axvline(kd, color="grey", lw=0.8, ls=":")
            x.text(kd, 0.03, f" K†={kd:.2f}", fontsize=6, transform=x.get_xaxis_transform())
            x.set_title(f"{kind}, {SCEN_ZH[sc]}, pull-in cradle, L = 12 h", fontsize=7)
            x.set_xlabel("SPMT groups K")
            if b == 0:
                x.set_ylabel("Lifted on board in the window (piles)")
    ax[0][0].legend(fontsize=6)
    fig.suptitle("Fig. 4 (draft) fleet plateau: solid fcfs, dotted convoy (loaded first), dashed W1′; vertical line K† = c/(tl + te) (S ≥ 1); "
                 "× marks convoy points beyond ⌈K†⌉ above the fcfs plateau", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, out, "fig4.png")
    wcsv(out / "fig4.csv", data)
    # Equal-delivery contours: A1, A2, A3 × scenario, pull-in, L = 12, G = 24, pile count over the (K, S) plane
    fig, ax = plt.subplots(2, 3, figsize=(12, 6.5))
    for b, kind in enumerate(("A1", "A2", "A3")):
        for a, sc in enumerate(("base", "lane")):
            M = [[i(by[(kind, sc, "pull_in", 12, 24, S, "fcfs")][K]["sim"]) for K in range(1, 11)] for S in range(7)]
            x = ax[a][b]
            im = x.imshow(M, origin="lower", aspect="auto", cmap="viridis", extent=(0.5, 10.5, -0.5, 6.5))
            cs = x.contour(range(1, 11), range(7), M, levels=sorted({v for row in M for v in row}), colors="w", linewidths=0.6)
            x.clabel(cs, fontsize=5, fmt="%d")
            x.set_title(f"{kind}, {SCEN_ZH[sc]}: equal-delivery contours", fontsize=7)
            x.set_xlabel("K")
            x.set_ylabel("Cradles S (0 = direct lifting)")
            fig.colorbar(im, ax=x, shrink=0.8)
    fig.suptitle("Fig. 4b (draft) (K, S) equal-delivery contours: pull-in cradle, L = 12 h, G = 24 h, fcfs", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, out, "fig4b.png")
    return cmp_


# ---------------------------------------------------------------- Fig. 5: unloading-loading overlap
FLEET_ZH = dict(ded="Dedicated unloading vehicle", plain="Shared fleet (no priority)", shared="Shared fleet (unloading first)",
                shared1="Shared fleet (at most 1 unloading)")
FLEETS = ("ded", "plain", "shared", "shared1")


def e5(rows, out):
    """Includes "shared fleet, no priority"; reports (N_o, N_u) in two dimensions, since the total rewards starving one flow;
    conclusions are stratified by corridor."""
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r["scen"], r["mode"], r["tide"], r["fleet"], i(r["Kt"]), i(r["S"]), r["rule"])][float(r["x"])] = r
    tab = []
    for (sc, m, td, fl, Kt, S, rule), d in sorted(by.items()):
        for x, r in sorted(d.items()):
            dd = by[(sc, m, td, "ded", Kt, S, rule)][x]
            tab.append(dict(scen=sc, mode=m, tide=td, fleet=fl, Kt=Kt, S=S, rule=rule, x=x, n_o=i(r["sim"]), n_u=i(r["n_ramp"]),
                            total=i(r["sim"]) + i(r["n_ramp"]), joint_ub=i(r["joint_ub"]), w1=i(r["w1"]), thm3=i(r["thm3"]),
                            nu_below_ded=int(i(r["n_ramp"]) < i(dd["n_ramp"]))))
    wcsv(out / "table_e5.csv", tab)
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    mk = dict(ded="o", plain="s", shared="v", shared1="^")
    for a, sc in enumerate(("base", "longslow")):
        for b, td in enumerate(("6", "cont")):
            x = ax[a][b]
            for fl in FLEETS:
                for Kt, col in ((2, "C0"), (4, "C1")):
                    d = by[(sc, "pull_in", td, fl, Kt, 1, "fcfs")]
                    xs = sorted(d)
                    x.plot([i(d[v]["n_ramp"]) for v in xs], [i(d[v]["sim"]) for v in xs], "-", marker=mk[fl], color=col, ms=4, lw=0.8, alpha=0.8,
                           label=f"{FLEET_ZH[fl]}, K_t = {Kt}" if (a, b) == (0, 0) else None)
                    x.annotate("x=1", (i(d[1.0]["n_ramp"]), i(d[1.0]["sim"])), fontsize=5)
            x.set_title(f"{SCEN_ZH[sc]}, {'tidal window 6 h' if td == '6' else 'ramp continuously open'}, pull-in, S = 1 (points: overlap x = 0–1)", fontsize=7)
            x.set_xlabel("Unloading completed N_u (piles)")
            x.set_ylabel("Loaded on board N_o (piles)")
    fig.legend(loc="lower center", ncol=4, fontsize=6)
    fig.suptitle("Fig. 5 (draft) unloading-loading overlap: (N_u, N_o) in two dimensions, four fleet arrangements, K_t = 2, 4", fontsize=9)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    save(fig, out, "fig5.png")
    L = ["# Fig. 5 / E5 unloading-loading overlap (fcfs, pull-in, S = 1; cells: N_o + N_u / joint upper bound; * marks less unloading than "
         "the dedicated unloading vehicle in the same cell)\n",
         "| Scenario | Ramp | Fleet | K_t | x = 0 | 0.25 | 0.5 | 0.75 | 1 |", "|---|---|---|---:|---|---|---|---|---|"]
    for sc in ("base", "longslow"):
        for td in ("6", "cont"):
            for fl in FLEETS:
                for Kt in (2, 3, 4, 6):
                    d, dd = by[(sc, "pull_in", td, fl, Kt, 1, "fcfs")], by[(sc, "pull_in", td, "ded", Kt, 1, "fcfs")]
                    L.append(f"| {SCEN_ZH[sc]} | {'6 h' if td == '6' else 'continuous'} | {FLEET_ZH[fl]} | {Kt} | " + " | ".join(
                        f"{d[v]['sim']}+{d[v]['n_ramp']}{'*' if i(d[v]['n_ramp']) < i(dd[v]['n_ramp']) else ''} / {d[v]['joint_ub']}" for v in sorted(d)) + " |")
    over = sum(1 for t in tab if t["total"] > t["joint_ub"])
    L.append(f"\nBoth flows combined above the joint upper bound: {over} / {len(tab)} points; loading above W1: {sum(1 for t in tab if t['n_o'] > t['w1'])} points; "
             f"unloading above Theorem 3: {sum(1 for t in tab if t['n_u'] > t['thm3'])} points.")
    # Does the "at most one" versus dedicated-unloading-vehicle comparison in each sub-grid (cradle type × S × dispatch rule) have the
    # same sign as in the tabulated sub-grid?
    agree, n = 0, 0
    ref = {(t["scen"], t["tide"], t["Kt"], t["x"]): t for t in tab if t["mode"] == "pull_in" and t["S"] == 1 and t["rule"] == "fcfs"}
    sign = lambda a, b: (a > b) - (a < b)
    for t in tab:
        if t["fleet"] != "shared1" or (t["mode"], t["S"], t["rule"]) == ("pull_in", 1, "fcfs"):
            continue
        dd = next(u for u in tab if (u["scen"], u["mode"], u["tide"], u["fleet"], u["Kt"], u["S"], u["rule"], u["x"]) ==
                  (t["scen"], t["mode"], t["tide"], "ded", t["Kt"], t["S"], t["rule"], t["x"]))
        r1 = ref[(t["scen"], t["tide"], t["Kt"], t["x"])]
        rd = next(u for u in tab if (u["scen"], u["mode"], u["tide"], u["fleet"], u["Kt"], u["S"], u["rule"], u["x"]) ==
                  (t["scen"], "pull_in", t["tide"], "ded", t["Kt"], 1, "fcfs", t["x"]))
        n += 1
        agree += sign(t["total"], dd["total"]) == sign(r1["total"], rd["total"])
    L.append(f"\nIn the other sub-grids (roadside cradle, S = 3, convoy dispatch) the combined total of \"at most one\" versus the dedicated "
             f"unloading vehicle has the same sign as in the tabulated sub-grid: {agree} / {n} cells.")
    md(out, "table_e5.md", L)
    return over, len(tab), agree, n


# ---------------------------------------------------------------- Fig. 6, Table 4: shipyards
def e6(rows, out, sites_md):
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r["kind"], r["scen"], r["mode"], i(r["L"]), i(r["G"]), i(r["S"]), r["rule"])][i(r["K"])] = r
    t4 = []
    for site in ("map:okpo", "map:yantai"):
        for sc in ("base", "slow", "fastcrane"):
            for m in ("on_road", "pull_in"):
                rs = [r for r in rows if r["kind"] == site and r["scen"] == sc and r["mode"] == m and r["rule"] == "fcfs"]
                rc = [r for r in rows if r["kind"] == site and r["scen"] == sc and r["mode"] == m and r["rule"] == "convoy"]
                reg = collections.Counter(r["regime"] for r in rs)
                one = next(r for r in rs if i(r["S"]) == 1 and i(r["K"]) == 8)
                cuts = collections.defaultdict(set)
                for r in rs:
                    cuts[r["cut_res"].split("|")[-1].replace("road_trace_", "")].add(i(r["S"]))
                cut_by_S = "; ".join(f"S = {','.join(map(str, sorted(v)))}: {k}" for k, v in sorted(cuts.items(), key=lambda kv: min(kv[1])))
                d = by[(site, sc, m, 12, 24, 1, "fcfs")]
                kf, nf = plateau({k: i(r["sim"]) for k, r in d.items()})
                t4.append(dict(site=site[4:], scen=sc, mode=m, n=len(rs), tie_w1=pct(sum(r["sim"] == r["w1"] for r in rs), len(rs)),
                               tie_w1g=pct(sum(r["sim"] == r["w1g"] for r in rs), len(rs)), over=sum(i(r["sim"]) > i(r["w1g"]) for r in rs),
                               interface=reg["interface"], staging=reg["staging"], flow=reg["flow"], cut=cut_by_S, tl_s=one["tl"], te_s=one["te"],
                               c_s=one["c"], k_dagger=one["k_dagger"], chain=one["chain"], plat_L12_S1=f"K={kf} ({nf})",
                               sum_fcfs=sum(i(r["sim"]) for r in rs), sum_convoy=sum(i(r["sim"]) for r in rc), checks=sum(r["check_ok"] == "1" for r in rs + rc)))
    wcsv(out / "table4.csv", t4)
    L = ["# Table 4 (draft) shipyards as wind marshalling ports: Okpo, Yantai (site selection in sites.md; idle vehicles wait in the off-road "
         "pocket next to the storage area)\n",
         "The cut changes with the number of cradles S (road_trace_ ids); tl / te / c, K† and the chain are the values at S = 1, K = 8.\n",
         "| Shipyard | Scenario | Cradle | Points | Tie W1 / W1′ | Above W1′ | Regime interface / staging / flow | Cut (by S) | tl / te / c (s) (S = 1) | "
         "K† (S = 1) | Chain (S = 1) | Plateau at L = 12 h, S = 1 | Total piles fcfs / convoy | Checker passed |",
         "|---|---|---|---:|---|---:|---|---|---|---:|---|---|---|---:|"]
    for t in t4:
        L.append(f"| {t['site']} | {SCEN_ZH[t['scen']]} | {MODE_ZH[t['mode']]} | {t['n']} | {t['tie_w1']} / {t['tie_w1g']} | {t['over']} | "
                 f"{t['interface']} / {t['staging']} / {t['flow']} | {t['cut']} | {t['tl_s']} / {t['te_s']} / {t['c_s']} | {float(t['k_dagger']):.2f} | "
                 f"{t['chain']} | {t['plat_L12_S1']} | {t['sum_fcfs']} / {t['sum_convoy']} | {t['checks']} / {2 * t['n']} |")
    L += ["", "## Site selection (windport_sites.py)\n", sites_md]
    md(out, "table4.md", L)
    fig, ax = plt.subplots(3, 2, figsize=(11, 10), sharey=True)
    data = []
    for b, site in enumerate(("map:okpo", "map:yantai")):
        for a, sc in enumerate(("base", "slow", "fastcrane")):
            x = ax[a][b]
            for S, col in zip((0, 1, 2, 4), ("C0", "C1", "C2", "C3")):
                d = by.get((site, sc, "pull_in", 12, 24, S, "fcfs"))
                if not d:
                    continue
                Ks = sorted(d)
                x.plot(Ks, [i(d[K]["sim"]) for K in Ks], "-o", color=col, ms=3, lw=1, label=f"S = {S}")
                x.plot(Ks, [i(d[K]["w1g"]) for K in Ks], "--", color=col, lw=0.8)
                data += [dict(site=site[4:], scen=sc, S=S, K=K, sim=i(d[K]["sim"]), w1g=i(d[K]["w1g"])) for K in Ks]
            x.set_title(f"{'Okpo' if site == 'map:okpo' else 'Yantai'}, {SCEN_ZH[sc]}, pull-in cradle, L = 12 h, G = 24 h", fontsize=7)
            x.set_xlabel("K")
            x.set_ylabel("Lifted on board in the window (piles)")
            x.legend(fontsize=6)
    fig.suptitle("Fig. 6 (draft) shipyards as wind marshalling ports: simulation (solid) and W1′ (dashed)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, out, "fig6.png")
    wcsv(out / "fig6.csv", data)
    return t4


# ---------------------------------------------------------------- Fig. 7: upscaling
AXLE = dict(A=[160, 240], w=[18.75, 25.0])


def e7(rows, out, lev):
    by = {(r["scen"], r["mode"], r["lev"], i(r["S"]), i(r["K"])): r for r in rows}
    tab = []
    for A in AXLE["A"]:
        for w in AXLE["w"]:
            for lv, x in lev.items():
                a = math.ceil(x["t"] / w - 1e-9)
                K = min(6, A // a)
                for sc in ("base", "lane"):
                    for m in ("on_road", "pull_in"):
                        for S in (1, 3):
                            r = by.get((sc, m, lv, S, K)) if K >= 1 else None
                            tab.append(dict(A=A, w=w, lev=lv, Lv=x["Lv"], B=x["B"], t=x["t"], a=a, K=K, scen=sc, mode=m, S=S,
                                            sim=i(r["sim"]) if r else 0, w1g=i(r["w1g"]) if r else 0, k_dagger=r["k_dagger"] if r else ""))
    wcsv(out / "table_e7.csv", tab)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for b, sc in enumerate(("base", "lane")):
        x = ax[b]
        for (A, w), col in zip([(A, w) for A in AXLE["A"] for w in AXLE["w"]], ("C0", "C1", "C2", "C3")):
            ts = [t for t in tab if t["A"] == A and t["w"] == w and t["scen"] == sc and t["mode"] == "pull_in" and t["S"] == 1]
            x.plot([t["Lv"] for t in ts], [t["sim"] for t in ts], "-o", color=col, ms=3, label=f"Axle-line pool {A}, {w} t/axle line")
            for t in ts:
                x.text(t["Lv"], t["sim"] + 0.15, f"K={t['K']}", fontsize=5, color=col)
        x.set_title(f"{SCEN_ZH[sc]}, pull-in cradle, S = 1, L = 12 h, G = 24 h", fontsize=7)
        x.set_xlabel("Monopile length Lv (m) (85/1,500 t, 100/1,500 t, 110/2,300 t, 120/3,000 t)")
        x.set_ylabel("Lifted on board in the window (piles)")
        x.legend(fontsize=6)
    fig.suptitle("Fig. 7 (draft) upscaling: with a fixed axle-line pool, K = ⌊A / ⌈m/w⌉⌋ falls in steps", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, out, "fig7.png")
    L = ["# Fig. 7 / E7 (draft) upscaling (pull-in, S = 1; piles / K)\n",
         "| Axle-line pool A | Per axle line w (t) | Scenario | 85 m / 1,500 t | 100 m / 1,500 t | 110 m / 2,300 t | 120 m / 3,000 t |",
         "|---:|---:|---|---|---|---|---|"]
    for A in AXLE["A"]:
        for w in AXLE["w"]:
            for sc in ("base", "lane"):
                ts = [t for t in tab if t["A"] == A and t["w"] == w and t["scen"] == sc and t["mode"] == "pull_in" and t["S"] == 1]
                L.append(f"| {A} | {w} | {SCEN_ZH[sc]} | " + " | ".join(f"{t['sim']} (K = {t['K']})" for t in ts) + " |")
    # Effect of a longer monopile at the same K
    L += ["\nPile count versus monopile size at the same K (pull-in, S = 1):\n", "| Scenario | K | 85 | 100 | 110 | 120 |", "|---|---:|---:|---:|---:|---:|"]
    for sc in ("base", "lane"):
        for K in (1, 2, 4):
            L.append(f"| {SCEN_ZH[sc]} | {K} | " + " | ".join(str(i(by[(sc, 'pull_in', lv, 1, K)]['sim'])) for lv in lev) + " |")
    md(out, "table_e7.md", L)


# ---------------------------------------------------------------- Off-road pocket
def pocket(rows, base, out):
    ref = {}
    for r in base:
        if r["lift"] in ("cradle", "direct") and r["hold"] == "0":
            ref[(r["kind"], r["scen"], r["mode"], r["lift"], i(r["L"]), i(r["K"]), i(r["S"]), i(r["G"]))] = r
    tab, ch = [], 0
    for kind in ("A1", "A2", "A3"):
        for sc in ("slow", "long", "longslow", "lane", "fastcrane", "joint", "jointshared"):
            for m in ("on_road", "pull_in"):
                rs = [r for r in rows if r["kind"] == kind and r["scen"] == sc and r["mode"] == m]
                if not rs:
                    continue
                pr = [(r, ref[(kind, sc, m, r["lift"], i(r["L"]), i(r["K"]), i(r["S"]), i(r["G"]))]) for r in rs]
                d = [i(a["sim"]) - i(b["sim"]) for a, b in pr]
                ch += sum(x != 0 for x in d)
                reg_a = collections.Counter(a["regime"] for a, _ in pr)
                tab.append(dict(kind=kind, scen=sc, mode=m, n=len(pr), sim_e1=sum(i(b["sim"]) for _, b in pr), sim_pocket=sum(i(a["sim"]) for a, _ in pr),
                                up=sum(x > 0 for x in d), down=sum(x < 0 for x in d), tie_e1=pct(sum(b["gap"] == "0" for _, b in pr), len(pr)),
                                tie_pocket_w1=pct(sum(a["sim"] == a["w1"] for a, _ in pr), len(pr)), tie_pocket_w1g=pct(sum(a["sim"] == a["w1g"] for a, _ in pr), len(pr)),
                                regime=f"{reg_a['interface']} / {reg_a['staging']} / {reg_a['flow']}", over=sum(i(a["sim"]) > i(a["w1g"]) for a, _ in pr)))
    wcsv(out / "table_pocket.csv", tab)
    L = ["# Off-road pocket: corridor-limited E1 scenarios; idle vehicles on the yard side park in the pocket at the end of a 30 m stub "
         "(entering and leaving occupy the road)\n",
         "Compared with the committed E1 (Q_h = 0, idle vehicles wait at the junction at the south end of the single lane without "
         "occupying it); same (L, K, S, G), cradle mode and direct lifting.\n",
         "| Archetype | Scenario | Cradle | Points | Piles E1 → pocket | Up / down points | Tie E1 (W1) | Tie pocket (W1 / W1′) | "
         "Regime (W1′) interface / staging / flow | Above W1′ |",
         "|---|---|---|---:|---|---|---|---|---|---:|"]
    for t in tab:
        L.append(f"| {t['kind']} | {SCEN_ZH[t['scen']]} | {MODE_ZH[t['mode']]} | {t['n']} | {t['sim_e1']} → {t['sim_pocket']} | {t['up']} / {t['down']} | "
                 f"{t['tie_e1']} | {t['tie_pocket_w1']} / {t['tie_pocket_w1g']} | {t['regime']} | {t['over']} |")
    md(out, "table_pocket.md", L)
    return tab


# ---------------------------------------------------------------- Gate holding places × convoy dispatch
def hold(conv, e1, e1h, out):
    rows = []
    for sc in SC5:
        for m in ("on_road", "pull_in"):
            for h in ("0", "1", "2", "inf"):
                f = [r for r in (e1 if h == "0" else e1h) if r["kind"] == "A1" and r["scen"] == sc and r["mode"] == m and r["hold"] == h
                     and r["lift"] in ("cradle", "direct")]
                c = [r for r in conv if r["scen"] == sc and r["mode"] == m and r["hold"] == h]
                rows.append(dict(scen=sc, mode=m, hold=h, n=len(f), fcfs=sum(i(r["sim"]) for r in f), convoy=sum(i(r["sim"]) for r in c),
                                 w1=sum(i(r["w1"]) for r in f), w1g=sum(i(r["w1g"]) for r in c), tie_fcfs=pct(sum(r["gap"] == "0" for r in f), len(f)),
                                 tie_convoy_w1g=pct(sum(r["sim"] == r["w1g"] for r in c), len(c)), better=0))
    wcsv(out / "table_hold2.csv", rows)
    L = ["# Gate holding places Q_h × dispatch rule (A1, cradle mode and direct lifting, 576 points per cell): fcfs from the committed "
         "E1 and E1h, convoy (loaded first through the bottleneck) from this run\n",
         "| Scenario | Cradle | Q_h | Piles fcfs | Piles convoy | W1 total | W1′ total | Tie fcfs (W1) | Tie convoy (W1′) |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    mono = collections.Counter()
    for r in rows:
        L.append(f"| {SCEN_ZH[r['scen']]} | {MODE_ZH[r['mode']]} | {r['hold']} | {r['fcfs']} | {r['convoy']} | {r['w1']} | {r['w1g']} | {r['tie_fcfs']} | {r['tie_convoy_w1g']} |")
    for sc in SC5:
        for m in ("on_road", "pull_in"):
            for rule in ("fcfs", "convoy"):
                v = [next(r for r in rows if r["scen"] == sc and r["mode"] == m and r["hold"] == h)[rule] for h in ("0", "1", "2", "inf")]
                mono[(rule, all(a <= b for a, b in zip(v, v[1:])))] += 1
    L.append(f"\nCells where the pile count does not decrease with Q_h (scenario × cradle, 10 cells): fcfs {mono[('fcfs', True)]}, convoy {mono[('convoy', True)]}.")
    md(out, "table_hold2.md", L)
    return mono


# ---------------------------------------------------------------- Table 2: W1′ and convoy columns added
def table2(e2, e2l, e2c, out):
    lng = {r["key"]: r for r in e2l}
    cv = {r["key"].split("=", 1)[1].replace("/", "|"): r for r in e2c}
    by = collections.defaultdict(list)
    for r in e2:
        if r["key"] in lng:
            r = dict(r, cp_best=lng[r["key"]]["cp_best"], cp_status=lng[r["key"]]["cp_status"])
        c = cv[r["key"]]
        by[(r["hold"], r["scen"], r["mode"])].append(dict(r, w1g=c["w1g"], conv=c["sim"]))
    rows = []
    for (h, sc, m), rs in sorted(by.items()):
        opt = [r for r in rs if r["cp_status"] == "OPTIMAL"]
        rows.append(dict(hold=h, scen=sc, mode=m, n=len(rs), opt=len(opt), w1_sum=sum(i(r["w1"]) for r in rs), w1g_sum=sum(i(r["w1g"]) for r in rs),
                         opt_eq_w1=sum(r["cp_best"] == r["w1"] for r in opt), opt_eq_w1g=sum(r["cp_best"] == r["w1g"] for r in opt),
                         gap_w1=sum(i(r["w1"]) - i(r["cp_best"]) for r in opt), gap_w1g=sum(i(r["w1g"]) - i(r["cp_best"]) for r in opt),
                         over_w1g=sum(i(r["cp_best"]) > i(r["w1g"]) for r in rs), sim=sum(i(r["sim"]) for r in rs), conv=sum(i(r["conv"]) for r in rs),
                         cp=sum(i(r["cp_best"]) for r in rs), cp_gt_sim=sum(i(r["cp_best"]) - i(r["sim"]) for r in rs if i(r["cp_best"]) > i(r["sim"])),
                         cp_gt_conv=sum(i(r["cp_best"]) - i(r["conv"]) for r in rs if i(r["cp_best"]) > i(r["conv"])),
                         conv_gt_cp=sum(i(r["conv"]) > i(r["cp_best"]) and r["cp_status"] == "OPTIMAL" for r in rs),
                         opt_eq_conv=sum(r["cp_best"] == r["conv"] for r in opt)))
    wcsv(out / "table2b.csv", rows)
    tot = {k: sum(r[k] for r in rows) for k in rows[0] if k not in ("hold", "scen", "mode")}
    L = ["# Table 2 (two columns added, draft) W1 / W1′ / CP-SAT / simulation fcfs / simulation convoy (540 small E2 instances; CP-SAT from "
         "the committed results, including the 600 s reruns)\n",
         "W1′ = min(W1 (geometric quay-zone Q), chain-cut preparation term). Gaps are summed over proven-optimal instances only.\n",
         "| Q_h | Scenario | Cradle | Instances | Proven optimal | Σ(W1 − opt) → Σ(W1′ − opt) | opt = W1 → = W1′ | CP > W1′ | CP − fcfs (piles) | "
         "CP − convoy (piles) | opt = convoy | convoy > proven opt |",
         "|---:|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|"]
    for r in rows + [dict(tot, hold="Total", scen="", mode="")]:
        L.append(f"| {r['hold']} | {SCEN_ZH.get(r['scen'], r['scen'])} | {MODE_ZH.get(r['mode'], r['mode'])} | {r['n']} | {r['opt']} | {r['gap_w1']} → {r['gap_w1g']} | "
                 f"{r['opt_eq_w1']} → {r['opt_eq_w1g']} | {r['over_w1g']} | {r['cp_gt_sim']} | {r['cp_gt_conv']} | {r['opt_eq_conv']} | {r['conv_gt_cp']} |")
    md(out, "table2b.md", L)
    return tot


# ---------------------------------------------------------------- Appendix C: sensitivity
PAR_ZH = dict(none="Base", hphd="Jack-up / set-down", steer="Steering programme change", v="Loaded speed", lift="Crane cycle",
              x="Direct-lift release time", roro="RoRo on-board work")


def unit(par, val):
    v = float(val)
    return dict(none="—", hphd=f"{v / 60:.0f} min", steer=f"{v / 60:.0f} min", v=f"{v:g} km/h", lift=f"{v / 3600:g} h", x=f"{v:g}p", roro=f"{v:g} h")[par]


def sens(rows, out):
    lv = [(p, v) for p, v in dict.fromkeys((r["par"], r["val"]) for r in rows)]
    A, B, Cc, D = [], [], [], []
    for par, val in lv:
        e1 = [r for r in rows if r["sub"] == "e1" and r["par"] == par and r["val"] == val]
        if e1:
            for sc in ("base", "lane"):
                rs = [r for r in e1 if r["scen"] == sc]
                reg = collections.Counter(r["regime"] for r in rs)
                A.append(dict(par=par, val=val, scen=sc, n=len(rs), sim=sum(i(r["sim"]) for r in rs), tie_w1g=pct(sum(r["sim"] == r["w1g"] for r in rs), len(rs)),
                              over=sum(i(r["sim"]) > i(r["w1g"]) for r in rs), interface=reg["interface"], staging=reg["staging"], flow=reg["flow"],
                              gap_max=max(i(r["w1g"]) - i(r["sim"]) for r in rs)))
        e4r = [r for r in rows if r["sub"] == "e4" and r["par"] == par and r["val"] == val]
        if e4r:
            for sc in ("base", "lane"):
                for m in ("on_road", "pull_in"):
                    g = collections.defaultdict(dict)
                    for r in e4r:
                        if r["scen"] == sc and r["mode"] == m:
                            g[i(r["S"])][i(r["K"])] = r
                    pl = {S: plateau({k: i(r["sim"]) for k, r in d.items()}) for S, d in g.items()}
                    kd = float(g[1][10]["k_dagger"])
                    gain = [pl[S + 1][1] - pl[S][1] for S in range(1, 6)]
                    B.append(dict(par=par, val=val, scen=sc, mode=m, k_dagger=round(kd, 2), ceil_kd=ceil_kd(kd), plat_S1=pl[1][0], n_S1=pl[1][1],
                                  plat_S3=pl[3][0], n_S3=pl[3][1], piles_per_cradle=round(sum(gain) / len(gain), 2), eq_ceil=int(pl[1][0] == ceil_kd(kd))))
        e3 = [r for r in rows if r["sub"] == "e3" and r["par"] == par and r["val"] == val]
        if e3:
            for sc in ("base", "lane"):
                for m in ("on_road", "pull_in"):
                    po = [float(r["port_h"]) for r in e3 if r["scen"] == sc and r["mode"] == m and r["rep"] == "occ" and r["port_h"]]
                    pf = [float(r["port_h"]) for r in e3 if r["scen"] == sc and r["mode"] == m and r["rep"] == "fix" and r["port_h"]]
                    p_ = float(val) if par == "lift" else 3600.0
                    lb = 10 * p_ / 3600.0
                    Cc.append(dict(par=par, val=val, scen=sc, mode=m, crane_lb_h=round(lb, 2), occ_min=round(min(po), 2), fix_min=round(min(pf), 2),
                                   ratio=round(min(po) / min(pf), 3), fix_reaches=int(min(pf) <= lb + 1e-6), occ_reaches=int(min(po) <= lb + 1e-6)))
        e5r = [r for r in rows if r["sub"] == "e5" and r["par"] == par and r["val"] == val]
        for fl in FLEETS:
            for Kt in (2, 4):
                rs = [r for r in e5r if r["fleet"] == fl and i(r["Kt"]) == Kt]
                if rs:
                    D.append(dict(par=par, val=val, fleet=fl, Kt=Kt, total=sum(i(r["sim"]) + i(r["n_ramp"]) for r in rs), n_u=sum(i(r["n_ramp"]) for r in rs),
                                  over=sum(i(r["sim"]) + i(r["n_ramp"]) > i(r["joint_ub"]) for r in rs)))
    for name, t in (("tableC_e1", A), ("tableC_e4", B), ("tableC_e3", Cc), ("tableC_e5", D)):
        wcsv(out / f"{name}.csv", t)
    L = ["# Appendix C (draft) sensitivity: one parameter at a time, others at base (A1; fcfs; Q_h = 0)\n",
         "## C1 E1 (W1′ and simulation; L = 4, 12 h, K = 1–6, S = 0, 1, 3, G = 3, 24 h, both cradle types)\n",
         "| Parameter | Value | Scenario | Points | Total piles | Tie W1′ | Above W1′ | Regime interface / staging / flow | Largest gap |", "|---|---|---|---:|---:|---:|---:|---|---:|"]
    L += [f"| {PAR_ZH[a['par']]} | {unit(a['par'], a['val'])} | {SCEN_ZH[a['scen']]} | {a['n']} | {a['sim']} | {a['tie_w1g']} | {a['over']} | "
          f"{a['interface']} / {a['staging']} / {a['flow']} | {a['gap_max']} |" for a in A]
    L += ["\n## C2 E4 (plateau and cradle-vehicle rate under first-come-first-served; L = 12 h, G = 24 h): plateau K at S = 1 (piles), "
          "plateau at S = 3, K†, piles gained per extra cradle on the plateau (mean over S = 1→6)\n",
          "| Parameter | Value | Scenario | Cradle | K† | Plateau S = 1 | Plateau S = 3 | Plateau = ⌈K†⌉ | Piles / cradle |", "|---|---|---|---|---:|---|---|---:|---:|"]
    L += [f"| {PAR_ZH[b['par']]} | {unit(b['par'], b['val'])} | {SCEN_ZH[b['scen']]} | {MODE_ZH[b['mode']]} | {b['k_dagger']} | K={b['plat_S1']} ({b['n_S1']}) | "
          f"K={b['plat_S3']} ({b['n_S3']}) | {'yes' if b['eq_ceil'] else 'no'} | {b['piles_per_cradle']} |" for b in B]
    L += ["\n## C3 E3 (shortest port time to load 10 piles, K = 1–8, S = 1; fixed durations use the conflict-free travel times, i.e. "
          "calibrated at K_ref = 1)\n",
          "Occupancy / fixed is the ratio of the two shortest port times; \"reaches the bound\" means the shortest port time equals the "
          "crane lower bound 10·p.\n",
          "| Parameter | Value | Scenario | Cradle | Crane lower bound h | Shortest with road occupancy h | Shortest with fixed durations h | "
          "Occupancy / fixed | Reaches bound: occupancy / fixed |", "|---|---|---|---|---:|---:|---:|---:|---|"]
    L += [f"| {PAR_ZH[c['par']]} | {unit(c['par'], c['val'])} | {SCEN_ZH[c['scen']]} | {MODE_ZH[c['mode']]} | {c['crane_lb_h']} | {c['occ_min']} | {c['fix_min']} | "
          f"{c['ratio']} | {'yes' if c['occ_reaches'] else 'no'} / {'yes' if c['fix_reaches'] else 'no'} |" for c in Cc]
    L += ["\n## C4 E5 (RoRo on-board work 3–5 h; base, pull-in, S = 1; summed over x = 0, 0.5, 1 × ramp 6 h / continuous)\n",
          "| Value | Fleet | K_t | Both flows combined | Of which unloading | Above joint bound |", "|---|---|---:|---:|---:|---:|"]
    L += [f"| {unit('roro', d['val'])} | {FLEET_ZH[d['fleet']]} | {d['Kt']} | {d['total']} | {d['n_u']} | {d['over']} |" for d in D]
    md(out, "tableC.md", L)
    return A, B, Cc, D


def sens7(rows, out):
    """Appendix C5: E7 (upscaling) under each sensitivity level: effect of a longer monopile at the same K (range of the pile counts
    over the 4 monopile sizes) and the step from K = 1 to 2."""
    by = {(r["par"], r["val"], r["scen"], r["lev"], i(r["K"])): i(r["sim"]) for r in rows}
    levs = ["85", "100", "110", "120"]
    tab = []
    for par, val in dict.fromkeys((r["par"], r["val"]) for r in rows):
        for sc in ("base", "lane"):
            n = {(lv, K): by[(par, val, sc, lv, K)] for lv in levs for K in (1, 2, 3, 4)}
            tab.append(dict(par=par, val=val, scen=sc, K1=" / ".join(str(n[(lv, 1)]) for lv in levs), K2=" / ".join(str(n[(lv, 2)]) for lv in levs),
                            range_sameK=max(max(n[(lv, K)] for lv in levs) - min(n[(lv, K)] for lv in levs) for K in (1, 2, 3, 4)),
                            step_min=min(n[(lv, 2)] - n[(lv, 1)] for lv in levs), step_max=max(n[(lv, 2)] - n[(lv, 1)] for lv in levs),
                            over=sum(i(r["sim"]) > i(r["w1g"]) for r in rows if r["par"] == par and r["val"] == val and r["scen"] == sc)))
    wcsv(out / "tableC_e7.csv", tab)
    L = (out / "tableC.md").read_text(encoding="utf-8").rstrip("\n").split("\n")
    L += ["\n## C5 E7 (upscaling; A1 single lane 12 m, pull-in, S = 1, L = 12 h, G = 24 h; piles for monopiles of 85 / 100 / 110 / 120 m)\n",
          "Effect of a longer monopile at the same K = largest, over K = 1–4, of the range of the pile counts over the 4 sizes; step = piles "
          "gained from K = 1 to 2 (minimum / maximum over the 4 sizes).\n",
          "| Parameter | Value | Scenario | K = 1 | K = 2 | Range at the same K | Step K = 1→2 | Above W1′ |", "|---|---|---|---|---|---:|---|---:|"]
    L += [f"| {PAR_ZH[t['par']]} | {unit(t['par'], t['val'])} | {SCEN_ZH[t['scen']]} | {t['K1']} | {t['K2']} | {t['range_sameK']} | {t['step_min']}–{t['step_max']} | "
          f"{t['over']} |" for t in tab]
    md(out, "tableC.md", L)
    return tab


# ---------------------------------------------------------------- Summary
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    h = hashlib.sha256(Path(__file__).read_bytes())
    for k in sorted(DIRS):
        h.update(path(k).read_bytes())
    out = ROOT / "results" / f"windport_runs_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "experiments"))
    import windport_runs as T
    cmp4 = e4(load("e4"), out)
    o5 = e5(load("e5"), out)
    sites_md = path("sites").read_text(encoding="utf-8").split("\n", 2)[2]
    t4 = e6(load("e6"), out, sites_md)
    e7(load("e7"), out, T.E7LEV)
    pk = pocket(load("pocket"), load("e1"), out)
    mono = hold(load("conv"), load("e1"), load("e1h"), out)
    t2 = table2(load("e2"), load("e2long"), load("e2c"), out)
    sens(load("sens"), out)
    t7 = sens7(load("sens7"), out)
    rnd = json.loads(path("random").read_text(encoding="utf-8"))
    L = ["# Summary (generated by windport_report2.py)\n"]
    for k in ("e4", "e5", "e6", "e7", "pocket", "conv", "e2c", "sens", "sens7"):
        rs = load(k)
        L.append(f"- {k}: {len(rs)} points; checker failures {sum(r['check_ok'] != '1' for r in rs)}; above W1 {sum(1 for r in rs if r['w1'] and r['rep'] != 'fix' and i(r['sim']) > i(r['w1']))}; "
                 f"above W1′ {sum(1 for r in rs if r['w1g'] and r['rep'] != 'fix' and i(r['sim']) > i(r['w1g']))}; "
                 f"W1′ < W1 {sum(1 for r in rs if r['w1g'] and i(r['w1g']) < i(r['w1']))} points; tie W1 {pct(sum(1 for r in rs if r['w1'] and r['sim'] == r['w1']), len(rs))}"
                 f" → W1′ {pct(sum(1 for r in rs if r['w1g'] and r['sim'] == r['w1g']), len(rs))}.")
    L.append(f"- E5 both flows combined above the joint upper bound: {o5[0]} / {o5[1]} points; in the other sub-grids the \"at most one\" versus "
             f"dedicated-vehicle comparison has the same sign as in the tabulated sub-grid in {o5[2]} / {o5[3]} cells.")
    L.append(f"- Random port-archetype regression ({DIRS['random']}): " + json.dumps(rnd, ensure_ascii=False))
    L.append(f"- Table 2 (540 E2 instances): Σ W1 {t2['w1_sum']} → Σ W1′ {t2['w1g_sum']}; proven optimal and = W1 {t2['opt_eq_w1']} → = W1′ {t2['opt_eq_w1g']}; "
             f"CP-SAT > W1′ {t2['over_w1g']} instances; "
             f"CP − fcfs {t2['cp_gt_sim']} piles → CP − convoy {t2['cp_gt_conv']} piles; convoy > proven optimum {t2['conv_gt_cp']} instances.")
    L.append(f"- Appendix C5 (E7 × sensitivity): largest range of pile counts for a longer monopile at the same K {max(t['range_sameK'] for t in t7)}; "
             f"step K = 1→2 {min(t['step_min'] for t in t7)}–{max(t['step_max'] for t in t7)} piles.")
    L.append(f"- Gate holding places: cells where the pile count does not decrease with Q_h: fcfs {mono[('fcfs', True)]} / 10, convoy {mono[('convoy', True)]} / 10.")
    L.append(f"- E4: counts of plateau versus ⌈K†⌉ {dict(('|'.join(k), v) for k, v in sorted(cmp4.items()))}.")
    L += ["", f"## {DIRS['chain']}/summary.md\n", path("chain").read_text(encoding="utf-8")]
    md(out, "summary.md", L)
    (out / "inputs.json").write_text(json.dumps({k: f"results/{DIRS[k]}/{FILES.get(k, 'points.csv')}" for k in sorted(DIRS)}, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
