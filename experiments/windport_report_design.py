"""Summary of the design analyses: per-item result tables (for the report and the manuscript), recheck counts of the new simulations,
and the manuscript make_numbers macros and assertions on the design-analysis directories compared with main2. Runs no simulation
(the voyage-period rate bound r = min(K/c, 1/(t_ℓ + t_e)) and the critical point τ are computed through the unified entry point).

Reads: windport_design_{turn, e6_lo, e6_hi, yards, near, transfer, codesign, analytic, rowsx_t7, rowsx_cd, spacing, turnwin, tr10}_*;
E6 of the conservative lifting rule, siteport / sites / turn of the unified bound, E4 / mix6 of the main geometry, and splice
(unified_reach) / reachdist / codesign / cdv / report of the main2 geometry.
Writes results/windport_design_report_<first 12 hex digits of the SHA-256 of the inputs and this script>/:
  twolevel.md / .csv (item 1), eem.md (item 2), screen.md (item 3), turn.md, yards1.md, yards3.md (item 4), crane.md, rate.md,
  checks.md, spacing.md (item 5), codesign.md / .csv (item 6), campaign.md (item 7), recheck.md,
  compat/ (files of the main2 run read by the manuscript, replaced by the main case of the design analyses: yards.csv,
  spatial/table_turn.*, spatial/table7_rate.*), paper_macros.csv / .md,
  numbers_fail_new.csv (failing assertions that are new relative to main2), numbers.json.
Run: python experiments/windport_report_design.py
"""
import collections
import csv
import hashlib
import itertools
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                        # noqa: E402

H = 3600.0
R137 = ROOT / "results"
H_REP = R137 / "tables/main2"
F_REP = R137 / "tables/maingeom"
CONSERVATIVE_E6 = R137 / "runs/conservative_runs_e6"
UNIFIED = dict(siteport=R137 / "runs/unified_siteport", turn=R137 / "runs/unified_turn")
MAINGEOM_E4, MAINGEOM_MIX6 = R137 / "runs/maingeom_runs_e4", R137 / "runs/maingeom_extra_mix6"
MAIN2 = dict(reach=R137 / "runs/main2_splice" / "unified_reach", reachdist=R137 / "runs/main2_reachdist",
             codesign=R137 / "runs/main2_codesign", cdv=R137 / "runs/main2_cdv")
SITE_ZH = dict(okpo="Okpo", yantai="Yantai")
SCEN_ZH = dict(base="base (2.5 km/h)", slow="1 km/h", lane="long single lane 1 km/h", longslow="long passage 1 km/h")
MODE_ZH = dict(on_road="on-road", pull_in="pull-in", side="side by side")
LV_ZH = dict(feas="all feasible (optimistic upper limit)", lo="alternative manoeuvre lo (incl. early steering, switch 30 s)",
             hi="alternative manoeuvre hi (reversing or crabbing, switch 300 s; main case)")
PERIODS_H = [12.0, 24.0, 36.0, 48.0, 72.0, 96.0, 144.0]          # voyage-period sensitivity (h); Table 16 uses 6 days = 144 h


def one(prefix):
    ds = sorted(p for p in R137.glob(prefix + "*") if p.is_dir() and len(p.name) == len(prefix) + 12)
    assert len(ds) == 1, (prefix, ds)
    return ds[0]


def dirs():
    D = {k: one(f"windport_design_{k}_") for k in ("turn", "e6_lo", "e6_hi", "yards", "near", "transfer", "codesign", "analytic", "rowsx_t7", "rowsx_cd",
                                                  "spacing", "turnwin", "tr10", "rowsfin", "cdfin", "cdblk", "cdblk2")}
    return D


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


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


fl = lambda x: None if x in ("", None, "None") else float(x)
i = lambda x: int(round(float(x)))
f2 = lambda x: "-" if x is None else f"{x:.2f}"


def key_of(r, *ks):
    return tuple(str(r.get(k, "")) for k in ks)


# ================================================================ item 1: two-level storage
def rate_bound(site, scen, K):
    """Long-run rate bound of the far → near transfer (Corollary 1): r = min(K/c, 1/(t_ℓ + t_e)), with c, t_ℓ, t_e taken from the parts
    of the unified entry point (see the manuscript); returns (r in monopiles per hour, c, tl, te)."""
    import windport_design as X
    from windport import bound_all as BA
    c = X.transfer_cfg(dict(site=site, scen=scen, K=K, n=10, alt="feas"))
    P = BA.parts(c, lift=True)["P"]
    return min(K / P.c, 1.0 / (P.tl + P.te)) * H, P.c, P.tl, P.te


def return_leg(site):
    """Empty run of a vehicle set after the window, from the quay gate back to the waiting area on the far-yard side (start of the
    transfer): (distance m, duration h); shortest path on the derived graph of the three-voyage storage area, empty speed WS.BASE."""
    import windport_spatial as TA
    from windport import shipyard as SY
    from windport import sim as WS
    from windport import sim4 as S4
    c = TA.cfg_of("siteport", dict(what="port", kind="map:" + site, st="multi", scen="base", mode="pull_in", arr="S1", K=1, n_v=10))
    D_, net, *_ = S4.setup4(c)
    a, b = SY.SITES[site]["gate"], S4.SITES_MULTI[site]["near"]
    d = sum(net.arc[x][2] for x in net.path(a, b))
    return d, d / WS.BASE["v_empty"] / H


def twolevel(D, out, N):
    near = {key_of(r, "kind", "scen", "mode", "arr", "K", "alt", "G"): r for r in rd(D["near"] / "points.csv")}
    ret = {s: return_leg(s) for s in ("okpo", "yantai")}
    tr10 = {key_of(r, "site", "scen", "K", "alt"): r for r in rd(D["tr10"] / "points.csv")}
    tr30 = {key_of(r, "site", "scen", "K", "alt"): r for r in rd(D["transfer"] / "points.csv")}
    yards = {key_of(r, "kind", "mode", "arr", "K", "hold", "alt"): r for r in rd(D["yards"] / "points.csv")}
    sp = {key_of(r, "kind", "st", "scen", "mode", "arr", "K", "hold"): r for r in rd(UNIFIED["siteport"] / "points.csv")}
    L = ["# Item 1: two-level storage (campaign storage in the far yard → transfer of one voyage, 10 monopiles, to the near yard "
         "between voyages → loading window from the near yard)\n",
         "Near yard = the one-voyage storage area of the E4-E7 batches (Okpo zone_trace_027 2.2 ha, route 282.7 m; Yantai zone_trace_003); "
         "far yard = the three-voyage storage area (Okpo zone_trace_001 6.82 ha, "
         "2,865 m; Yantai zone_trace_030 5.04 ha). Transfer network: road-side segments of the far yard → pull-in placing positions "
         "at the midpoints of the road-side segments of the near yard (placing h_d unchanged).\n",
         "## 1.1 Window port time under the two storage options (10 monopiles per vessel, base, cradles S = 1, Q_h = 0, vessel crane "
         "open from G = 24 h; shortest over K = 2–8, L″_lift* in parentheses)\n",
         "| Yard | Cradle | Single level (direct loading from the three-voyage area): all feasible / lo / hi | "
         "Two levels (loading from the near yard): all feasible / lo / hi |", "|---|---|---|---|"]
    tab = []
    for site, m in itertools.product(("okpo", "yantai"), T.MODES):
        one = []
        for lv in ("feas", "lo", "hi"):
            if lv == "feas":
                rs = [sp[(f"map:{site}", "multi", "base", m, "S1", str(K), "")] for K in range(2, 9)]
            else:
                rs = [yards[(f"map:{site}", m, "S1", str(K), "0", lv)] for K in range(2, 9)]
            one.append((min(fl(r["port_h"]) for r in rs), min(fl(r["lstar_lo"]) for r in rs)))
        two = []
        for lv in ("feas", "lo", "hi"):
            rs = [near[(f"map:{site}", "base", m, "S1", str(K), lv, "24")] for K in range(2, 9)]
            two.append((min(fl(r["port_h"]) for r in rs), min(fl(r["lstar_lo"]) for r in rs)))
        tab.append(dict(site=site, mode=m, **{f"single_{lv}": a for lv, (a, _) in zip(("feas", "lo", "hi"), one)},
                        **{f"single_lstar_{lv}": b for lv, (_, b) in zip(("feas", "lo", "hi"), one)},
                        **{f"two_{lv}": a for lv, (a, _) in zip(("feas", "lo", "hi"), two)}, **{f"two_lstar_{lv}": b for lv, (_, b) in zip(("feas", "lo", "hi"), two)}))
        L.append(f"| {SITE_ZH[site]} | {MODE_ZH[m]} | " + " / ".join(f"{a:.2f} ({b:.2f})" for a, b in one) + " | " + " / ".join(f"{a:.2f} ({b:.2f})" for a, b in two) + " |")
    # 1.1b near-yard window vs K (how many vehicle sets bring the window back to the crane lower limit)
    L += ["\n### Near-yard window port time vs K (G = 24 h, cradles S = 1; the larger of the two cradle modes)\n",
          "| Yard | Scenario | Turns | K = 1 | 2 | 3 | 4 | Smallest K back to 10.00 h |",
          "|---|---|---|---|---|---|---|---:|"]
    kwin = {}
    for site, sc, lv in itertools.product(("okpo", "yantai"), ("base", "slow"), ("feas", "hi")):
        v = {K: max(fl(near[(f"map:{site}", sc, m, "S1", str(K), lv, "24")]["port_h"]) for m in T.MODES) for K in range(1, 9)}
        k10 = next((K for K in range(1, 9) if v[K] <= 10.0 + 1e-6), None)
        kwin[(site, sc, lv)] = k10
        L.append(f"| {SITE_ZH[site]} | {SCEN_ZH[sc]} | {lv} | " + " | ".join(f"{v[K]:.2f}" for K in range(1, 5)) + f" | {k10} |")
    # 1.2 voyage period
    L += ["\n## 1.2 Shortest voyage period T_min supported by the far route (h; n_v = 10 monopiles per voyage; K = vehicle sets "
          "shared by transfer and loading, S = quay cradles)\n",
          "Three quantities: **T_rate** = n_v / r, where r = min(K/c, 1/(t_ℓ + t_e)) is the long-run rate bound of the far → near "
          "transfer (Corollary 1: any dispatching, transfer may overlap loading, long-run average; c is taken with all turns feasible, "
          "which for hi is a weaker necessary condition and still holds); "
          "**T_seq\\*** = L″*_transfer(10) + return + L″*_window⁰(10) (rule-independent lower bound of the sequential policy: first "
          "transfer all 10 monopiles; after the window the vehicle sets run empty back to the far-yard side, then load from an empty "
          "system; both parts use the set-up term of Theorem 2, "
          "the return is a deterministic empty run); "
          "**T_seq** = the same sequential policy simulated first-come-first-served (placing time of the 10th transferred monopile "
          "+ return + near-yard window from an empty system until the 10th lift ends). "
          f"Return = shortest empty path from the quay gate to the far-yard waiting area: Okpo {ret['okpo'][0]:,.1f} m ({ret['okpo'][1]:.3f} h), "
          f"Yantai {ret['yantai'][0]:,.1f} m ({ret['yantai'][1]:.3f} h), "
          "empty speed 5 km/h. Turns: hi (main case); all feasible in parentheses.\n",
          "| Yard | Scenario | Lifting | K = 1 | 2 | 3 | 4 | 6 | 8 |", "|---|---|---|---|---|---|---|---|---|"]
    tm = []
    for site, sc in itertools.product(("okpo", "yantai"), ("base", "slow")):
        rb = {K: rate_bound(site, sc, K) for K in range(1, 9)}
        for arr in (["S1", "S3"] if site == "okpo" else ["S1"]):
            cells = []
            for K in range(1, 9):
                rh = ret[site][1]
                row = dict(site=site, scen=sc, arr=arr, K=K, r_per_h=round(rb[K][0], 4), c_s=round(rb[K][1], 1), tl_s=round(rb[K][2], 1), te_s=round(rb[K][3], 1),
                           T_rate_h=round(10 / rb[K][0], 3), return_h=round(rh, 4))
                for lv in ("feas", "lo", "hi"):
                    t = tr10[(site, sc, str(K), lv)]
                    w = [near[(f"map:{site}", sc, m, arr, str(K), lv, "0")] for m in T.MODES]
                    wb = min(w, key=lambda r: fl(r["port_h"]))
                    row.update({f"tr_{lv}": fl(t["port_h"]), f"tr_lstar_{lv}": fl(t["lstar_lo"]), f"win0_{lv}": fl(wb["port_h"]),
                                f"win0_lstar_{lv}": min(fl(r["lstar_lo"]) for r in w), f"win0_mode_{lv}": wb["mode"],
                                f"T_seq_{lv}": round(fl(t["port_h"]) + rh + fl(wb["port_h"]), 3),
                                f"T_seq_lb_{lv}": round(fl(t["lstar_lo"]) + rh + min(fl(r["lstar_lo"]) for r in w), 3),
                                f"tr30_{lv}": fl(tr30[(site, sc, str(K), lv)]["port_h"])})
                tm.append(row)
                cells.append(f"{row['T_rate_h']:.1f} / {row['T_seq_lb_hi']:.1f} / **{row['T_seq_hi']:.1f}** ({row['T_seq_feas']:.1f})")
            L.append(f"| {SITE_ZH[site]} | {SCEN_ZH[sc]} | {arr} | " + " | ".join(cells[k - 1] for k in (1, 2, 3, 4, 6, 8)) + " |")
    L.append("\nEach cell: T_rate / T_seq\\* / **T_seq** (all feasible).")
    # 1.3 criterion and period sensitivity
    L += ["\n## 1.3 Criterion (each of the two conditions stated once): with voyage period T ≥ T_seq(K, S) the sequential transfer "
          "stays out of the window, the loading window is the near-yard window, and the far route constrains only the transfer "
          "between voyages; "
          "bringing the window back to the crane lower limit 10.00 h also needs enough K (\"smallest K back to 10.00 h\" above). "
          "With T < T_rate(K) no dispatching can refill the near yard and the road enters the window\n",
          "Table: for each voyage period, the smallest number of vehicle sets K for which the sequential policy is feasible "
          "(T ≥ T_seq) (S = 1, turns hi; > 8 when K ≤ 8 is not enough), and the K with T < T_rate (road necessarily in the window). "
          "This is only the transfer condition; because of the crane the window also needs K at least the smallest K of the table above.\n",
          "| Yard | Scenario | " + " | ".join(f"T = {p:g} h" for p in PERIODS_H) + " |", "|---|---|" + "---|" * len(PERIODS_H)]
    crit = []
    for site, sc in itertools.product(("okpo", "yantai"), ("base", "slow")):
        rs = {r["K"]: r for r in tm if r["site"] == site and r["scen"] == sc and r["arr"] == "S1"}
        cells = []
        for P in PERIODS_H:
            kseq = next((K for K in range(1, 9) if rs[K]["T_seq_hi"] <= P + 1e-9), None)
            krate = [K for K in range(1, 9) if P < rs[K]["T_rate_h"] - 1e-9]
            crit.append(dict(site=site, scen=sc, period_h=P, K_seq=kseq if kseq else ">8", K_road=" ".join(map(str, krate))))
            cells.append(f"K ≥ {kseq}" if kseq else "> 8" + (f"; road in window for K ≤ {max(krate)}" if krate else ""))
            if kseq and krate:
                cells[-1] += f"; road in window for K ≤ {max(krate)}"
        L.append(f"| {SITE_ZH[site]} | {SCEN_ZH[sc]} | " + " | ".join(cells) + " |")
    wcsv(out / "twolevel_window.csv", tab)
    wcsv(out / "twolevel_tmin.csv", tm)
    wcsv(out / "twolevel_period.csv", crit)
    md(out, "twolevel.md", L)
    N["twolevel"] = dict(window=tab, crit=crit, ret={s: dict(m=round(v[0], 1), h=round(v[1], 4)) for s, v in ret.items()},
                         kwin={"|".join(k): v for k, v in kwin.items()}, tmin={f"{r['site']}|{r['scen']}|{r['arr']}|{r['K']}": {k: r[k] for k in ("T_rate_h", "T_seq_lb_hi", "T_seq_hi", "T_seq_feas")}
                                                      for r in tm})


# ================================================================ items 2 and 3
def eem(D, out, N):
    rs = rd(D["analytic"] / "eem.csv")
    L = ["# Item 2: Eemshaven Gode Wind 3 (split site: BOW yard → Wagenborg quay), speed threshold of the single lane\n",
         "Single lane 794.6 m, pavement 11.3 m (haul paths measured on public satellite imagery, not released). Bisection on speed "
         "with the occupancy-time formula (windport_analytic.tau: t_ℓ, t_e, d_q, t_e^occ from the window of the road-occupancy "
         "model, as in Fig. 12); "
         "no linear interpolation between the two points 1.20p and 0.60p. p = 1 h. The source (Groningen Seaports 2023-06-26) only "
         "says that the monopiles were hauled over port roads to the Wagenborg quay with the roads closed 18:00–06:00, "
         "**and does not say whether they were hauled back and forth during the loading window or pre-staged at the quay before "
         "loading**.\n",
         "| Geometry | Cradle | τ_cut/p: 1 / 2.5 km/h | τ_zone1/p: 1 / 2.5 km/h | Speed crossing the any-dispatch critical line "
         "(τ_cut = p) | Speed crossing the quay-zone one-set-at-a-time criterion (τ_zone1 = p) |",
         "|---|---|---|---|---:|---:|"]
    for r in rs:
        L.append(f"| {r['geometry']} | {MODE_ZH[r['mode']]} | {r['cut_p_1.0']} / {r['cut_p_2.5']} | {r['zone1_p_1.0']} / {r['zone1_p_2.5']} | {r['v_cut']} km/h | {r['v_zone1']} km/h |")
    L.append("\nReading: below v_cut one loaded run plus one empty return on the single lane takes longer than one lift, so every "
             "dispatching is road-constrained; v_cut does not depend on the cradle mode or the geometry (only the single lane counts). "
             "The quay-zone criterion also contains d_q (from leaving the single lane to the handover) and varies with the cradle mode "
             "and the quay geometry. The quay-zone thresholds of the on-road cradle (main2 2.09 km/h, legacy40 2.55 km/h) are jump "
             "points where the cut switches from the single lane to the apron segment "
             "(main2: τ_zone1 = 1.23 p at 2.0 km/h, 0.70 p at 2.1 km/h), not a continuous crossing.")
    md(out, "eem.md", L)
    N["eem"] = rs


def screen(D, out, N):
    s = rd(D["analytic"] / "sites.csv")
    w = rd(D["analytic"] / "sites_w2.csv")
    g = collections.defaultdict(dict)                                # (key, v, p, mode) → {K: row}
    for r in w:
        g[(r["key"], r["v"], r["p_h"], r["mode"])][int(r["K"])] = r

    def kmin(key, v, p):
        """Per cradle mode: the smallest K whose simulated delivery reaches the vessel-crane limit, and the smallest K at which the
        binding term of W″ is the crane; the larger over the two cradle modes is taken (stricter). None = not reached for K ≤ 6."""
        ks, kw, prof = [], [], {}
        for m in T.MODES:
            G_ = g[(key, v, p, m)]
            ks.append(next((K for K in sorted(G_) if int(G_[K]["sim"]) >= int(G_[K]["crane"])), None))
            kw.append(next((K for K in sorted(G_) if G_[K]["w2_cls"] == "crane"), None))
            prof[m] = " ".join(G_[K]["sim"] for K in sorted(G_))
        worst = lambda xs: None if None in xs else max(xs)
        return worst(ks), worst(kw), prof
    L = ["# Item 3: two-level screening of 8 public sites (haul paths measured on public satellite imagery, not released)\n",
         "Level 1 (geometry): single-lane segments (width class A) use τ_cut = t_ℓ + t_e; junctions = inner vertices of the route "
         "polyline, with occupation τ_j = loaded (D + L_v + δ)/v (plus a stop-and-steer 120 s + θ·L_v/2/v when the turn angle ≥ 60°) "
         "+ one empty pass (D + L_e + δ)/v_e (plus a sweep of 30 s when ≥ 60°), inserted into the τ/p criterion as a short single "
         "lane; D = width of the adjacent road segment, open areas use unrestricted_w = 31 m. "
         "No vertex of the image polylines has ≥ 60°; a hypothetical 90° in-place turn τ_90 (at the widest point of the route) is "
         "listed as an upper bound. "
         "Level 2 (capacity): K_rate = ⌈c/p⌉ (c = h_p + h_d + route/v + Σ turn stops + route/v_e, a long-run necessary condition); "
         "K_W″ = smallest K at which the binding term of W″_lift(12 h) on the A1 proxy graph is the crane "
         "(an upper bound: when the binding term is not the crane, the crane cannot be the constraint, so this is a necessary "
         "condition); **K_min = smallest K at which the first-come-first-served simulation on the same proxy graph delivers the "
         "vessel-crane limit ⌊L/p⌋** (L = 12 h, S = 1, G = 24 h, "
         "main geometry main2, conservative lifting semantics; verified by the checker). The stricter of the two cradle modes is taken.\n",
         "| Site | Class | Route m | Speed km/h | Max junction τ_j/p | Hypothetical 90° turn τ_90/p | Single lane τ_cut/p | K_rate | "
         "K_W″ | Simulated delivery K = 1 … 6 (on-road / pull-in, limit 12) | **K_min** | Conclusion (p = 1 h) |",
         "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|"]
    tab = []
    for r in s:
        if r["p_h"] != "1.0":
            continue
        km, kw, prof = kmin(r["key"], r["v"], "1.0")
        lane = fl(r["lane_cut_p"])
        concl = f"crane-constrained for K ≥ {km} vehicle sets" if km else "road-constrained (delivery below the vessel-crane limit for all K ≤ 6)"
        tab.append(dict(site=r["site"], key=r["key"], v=r["v"], p_h=1.0, K_rate=r["K_rate"], K_w2=kw, K_min=km))
        L.append(f"| {r['site']} | {r['cls']} | {r['route_m']} | {r['v']} | {r['junction_tau_p']} | {r['turn90_tau_p']} | {'-' if lane is None else lane} | {r['K_rate']} | "
                 f"{kw or '-'} | {prof['on_road']} / {prof['pull_in']} | **{km or '-'}** | {concl} |")
    L += ["\n### p = 0.5 h (vessel crane 0.5 h, limit 24)\n",
          "| Site | Speed | Max junction τ_j/p | τ_90/p | Single lane τ_cut/p | K_rate | K_W″ | Simulated delivery K = 1 … 6 "
          "(on-road / pull-in) | K_min |",
          "|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    for r in s:
        if r["p_h"] == "0.5":
            km, kw, prof = kmin(r["key"], r["v"], "0.5")
            tab.append(dict(site=r["site"], key=r["key"], v=r["v"], p_h=0.5, K_rate=r["K_rate"], K_w2=kw, K_min=km))
            L.append(f"| {r['site']} | {r['v']} | {r['junction_tau_p']} | {r['turn90_tau_p']} | {r['lane_cut_p'] or '-'} | {r['K_rate']} | {kw or '-'} | "
                     f"{prof['on_road']} / {prof['pull_in']} | {km or '-'} |")
    L.append("\n\"-\": for K ≤ 6 the crane is never the binding term / the simulation never reaches the vessel-crane limit. "
             "The checker passes everywhere (check_ok of `sites_w2.csv`).")
    bad = sum(1 for r in w if r["check_ok"] != "1")
    wcsv(out / "screen_kmin.csv", tab)
    md(out, "screen.md", L)
    N["screen"] = dict(rows=s, kmin=tab, check_bad=bad, n_sim=len(w))


# ================================================================ item 4
def turn(D, out, N):
    rows = rd(D["turn"] / "turn_alt.csv")
    bad = [r for r in rows if r["bad"] == "1"]
    L = ["# Item 4: feasibility and kinematic duration of alternative turns (Okpo, Yantai; each turn failing the sector check is "
         "examined)\n",
         "Turns whose in-place rotation sector around the junction hits buildings or water (criterion of the spatial additions; the "
         "list matches turn_extra.json of the spatial additions, 4 / 4 groups). On a 1 m grid within ±260 m of the junction "
         "(buildings + water, "
         "minus all road surface) three families of alternative manoeuvres are searched: **R+ early steering** (rotation through the "
         "original turn angle about a point other than the monopile centre: a large-radius turn that may start before the junction); "
         "**R− reverse rotation** (rotation through 180° − θ in the opposite sense, "
         "so that the monopile axis lies on the outgoing road and the vehicle leaves rear first; not a \"reverse by about one "
         "monopile length\" manoeuvre); **C± crabbing** (sideways shift to a point offset from the junction, in-place rotation, "
         "sideways shift back to the road axis). "
         "Feasible = **1 m clearance** between the swept area and buildings or water (obstacle grid dilated by 1 m, minus road "
         "surface; the selected manoeuvre is rechecked with dense sampling: 0.5 m along the monopile, 11 lines across, 0.5 m motion "
         "step; "
         "if it fails, the next candidate is taken); whether it also hits other occupied areas (storage yards, assembly areas, etc.) "
         "is recorded, and manoeuvres that do not are preferred.\n",
         "Duration (beyond the stop for an in-place rotation, floor 0): change of straight travel + change of rotation (arc length "
         "travelled by the farthest monopile point at v) + sideways distance/v + 2 steering-mode switches t_sw for the sideways family. "
         "Reversing and crabbing speeds use the known loaded speed (public sources give no separate value); t_sw: the Scheuerle "
         "specification only says \"the steering program can be changed when stopped and fully loaded\", the Goldhofer rental page "
         "says \"switchable within seconds\", "
         "neither gives seconds, so an assumed range of 30–300 s is used. Two ends: **lo** = shortest of all feasible families, "
         "t_sw = 30 s; **hi** = reversing-crabbing only (sideways family), t_sw = 300 s (main case); "
         "if an end has no feasible manoeuvre, the generic formula L_v/v + Δw/v + 2t_sw is used (Δw = width difference between "
         "outgoing and incoming roads, at least B); hi uses this scenario value for the turns where crabbing is geometrically "
         "infeasible (node_trace_014, 016, 056). "
         "Crab-rotate-crab physically needs about 4 mode switches; 2 are counted here; the only public source with a statement "
         "says \"within seconds\", so 300 s is the pessimistic end.\n",
         "| Yard | Route | Turn (node) | Turn angle | Class | Feasible families (those not hitting other occupied areas) | "
         "lo: family, 2.5 / 1 km/h (s) | hi: family, 2.5 / 1 km/h (s) | Generic hi, 2.5 / 1 km/h (s) |",
         "|---|---|---|---:|---|---|---|---|---|"]
    ST = dict(runs="one-voyage", multi="three-voyage", transfer="far → near transfer")
    for r in bad:
        L.append(f"| {SITE_ZH[r['site']]} | {ST[r['storage']]} | {r['node']} | {r['turn_deg']} | {r['cls']} | {r['fams_feasible'] or '-'} ({r['fams_clean'] or '-'}) | "
                 f"{r['fam_base_lo']}, {r['t_base_lo']} / {r['t_slow_lo']} | {r['fam_base_hi']}, {r['t_base_hi']} / {r['t_slow_hi']} | {r['generic_base_hi']} / {r['generic_slow_hi']} |")
    cnt = collections.Counter((r["site"], r["storage"], r["cls"]) for r in bad)
    L += ["\n## Class counts\n", "| Yard | Route | Early steering | Reversing or crabbing | No space (operator to confirm) |", "|---|---|---:|---:|---:|"]
    for site, st in itertools.product(("okpo", "yantai"), ("runs", "multi", "transfer")):
        L.append(f"| {SITE_ZH[site]} | {ST[st]} | {cnt[(site, st, 'early re-orientation')]} | {cnt[(site, st, 'reversing or crab steering')]} | {cnt[(site, st, 'no space (operator to confirm)')]} |")
    nclean = sum(1 for r in bad if r["fams_clean"])
    L.append(f"\nOf the {len(bad)} (route × turn) cases failing the sector check, {nclean} have an alternative manoeuvre that does not hit "
             "other occupied areas; the others must cross corners of storage or assembly areas (space to be coordinated with the yard).")
    md(out, "turn.md", L)
    N["turn"] = dict(bad=len(bad), counts={"|".join(k): v for k, v in cnt.items()}, clean=nclean,
                     times={f"{r['site']}|{r['storage']}|{r['node']}": {k: r[k] for k in ("cls", "t_base_lo", "t_base_hi", "t_slow_lo", "t_slow_hi")} for r in bad})


def yards1(D, out, N):
    """Table tab_yards (one-voyage E6 grid): all turns feasible (conservative-lifting-rule run) vs alternative manoeuvres lo / hi."""
    base = {r["key"]: r for r in rd(CONSERVATIVE_E6 / "points.csv")}
    lo = {r["key"]: r for r in rd(D["e6_lo"] / "points.csv")}
    hi = {r["key"]: r for r in rd(D["e6_hi"] / "points.csv")}
    rl = {r["key"]: r for r in rd(D["e6_lo"] / "recheck.csv")}
    rh = {r["key"]: r for r in rd(D["e6_hi"] / "recheck.csv")}
    L = ["# Table tab_yards (one-voyage storage area, E6 grid of 5,376 points): all turns feasible → alternative manoeuvres lo / hi\n",
         "| Yard | Scenario | Total delivery: all feasible → lo → hi | Change lo / hi | Points with lower delivery lo / hi | "
         "At W″_lift: lo / hi | Crane binding: lo / hi |", "|---|---|---|---|---|---|---|"]
    tab = []
    for site, sc in itertools.product(("okpo", "yantai"), ("base", "slow", "fastcrane")):
        ks = [k for k, r in base.items() if r["kind"] == f"map:{site}" and r["scen"] == sc]
        a, b, c = (sum(i(X[k]["sim"]) for k in ks) for X in (base, lo, hi))
        tie = lambda R: sum(i(R[k]["sim"]) == i(R[k]["w2_lift"]) for k in ks) / len(ks)
        crn = lambda R: sum(R[k]["w2_cls"] == "crane" for k in ks) / len(ks)
        tab.append(dict(site=site, scen=sc, n=len(ks), feas=a, lo=b, hi=c, lower_lo=sum(i(lo[k]["sim"]) < i(base[k]["sim"]) for k in ks),
                        lower_hi=sum(i(hi[k]["sim"]) < i(base[k]["sim"]) for k in ks), tie_lo=round(tie(rl), 4), tie_hi=round(tie(rh), 4), crane_lo=round(crn(rl), 4),
                        crane_hi=round(crn(rh), 4)))
        t = tab[-1]
        L.append(f"| {SITE_ZH[site]} | {sc} | {a} → {b} → {c} | {(b - a) / a:+.1%} / {(c - a) / a:+.1%} | {t['lower_lo']} / {t['lower_hi']} | {t['tie_lo']:.1%} / {t['tie_hi']:.1%} | "
                 f"{t['crane_lo']:.1%} / {t['crane_hi']:.1%} |")
    L.append("\nOn the one-voyage routes the 4 + 4 turns failing the sector check add 0 s at the lo end (early steering or reverse "
             "rotation), so lo equals all feasible point by point; hi (reversing-crabbing) is the main case. "
             "W″_lift does not read the durations of alternative manoeuvres (only the simulation and the checker do); the \"crane "
             "binding\" column is equal at both ends because the bound does not see the alternative manoeuvres, and no conclusion is "
             "drawn from it; the alternative manoeuvres are verified by the checker (all pass).")
    wcsv(out / "yards1.csv", tab)
    md(out, "yards1.md", L)
    N["yards1"] = tab


def yards3(D, out, N, comp):
    """Table tab_yards3 (three-voyage storage area, 10 monopiles per vessel): turns feasible (siteport of the unified bound),
    alternative manoeuvres lo / hi (yards of the design analyses); also writes the yards.csv read by the manuscript (format of the
    main geometry: column 600 holds lo, column 1800 holds hi)."""
    sp = {key_of(r, "kind", "st", "scen", "mode", "arr", "K", "hold"): r for r in rd(UNIFIED["siteport"] / "points.csv")}
    ya = {key_of(r, "kind", "mode", "arr", "K", "hold", "alt"): r for r in rd(D["yards"] / "points.csv")}
    old = {key_of(r, "site", "mode", "hold"): r for r in rd(H_REP / "yards.csv")}
    rows, L = [], ["# Table tab_yards3 (three-voyage storage area, 10 monopiles per vessel, base, cradles S = 1; shortest over "
                   "K = 2–8, the K giving the shortest in parentheses)\n",
                   "| Yard | Cradle | Q_h | Crane lower limit | L″_lift* | Turns feasible | lo | **hi (main case)** | "
                   "main2: 600 / 1,800 s |", "|---|---|---|---:|---:|---|---|---|---|"]
    for site, m, h in itertools.product(("okpo", "yantai"), T.MODES, ("0", "1", "inf")):
        r = dict(site=site, mode=m, hold=h, K="2–8", crane=10.0)
        fc = []
        for K in range(2, 9):
            q = sp.get((f"map:{site}", "multi", "base", m, "S1", str(K), "" if h == "0" else h))
            if q and q["port_h"] not in ("", None):
                fc.append((fl(q["port_h"]), K, fl(q["lstar_lo"])))
        if not fc:
            continue
        b = min(fc)
        r.update(lstar_0=old[(site, m, h)]["lstar_0"], fcfs_0=b[0], K_0=b[1])
        for lv, col in (("lo", 600), ("hi", 1800)):
            ys = [ya[(f"map:{site}", m, "S1", str(K), h, lv)] for K in range(2, 9)]
            bb = min(ys, key=lambda q: fl(q["port_h"]))
            r[f"lstar_{col}"], r[f"fcfs_{col}"], r[f"K_{col}"] = min(fl(q["lstar_lo"]) for q in ys), fl(bb["port_h"]), i(bb["K"])
        rows.append(r)
        o = old[(site, m, h)]
        L.append(f"| {SITE_ZH[site]} | {MODE_ZH[m]} | {dict(inf='unlimited').get(h, h)} | 10.00 | {fl(r['lstar_0']):.2f} | {r['fcfs_0']:.2f} ({r['K_0']}) | "
                 f"{r['fcfs_600']:.2f} ({r['K_600']}) | **{r['fcfs_1800']:.2f}** ({r['K_1800']}) | {fl(o['fcfs_600']):.2f} / {fl(o['fcfs_1800']):.2f} |")
    cols = list(rd(H_REP / "yards.csv")[0].keys())
    (comp).mkdir(parents=True, exist_ok=True)
    with open(comp / "yards.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    md(out, "yards3.md", L)
    N["yards3"] = rows


def turnwin_compat(D, out, N, comp):
    """spatial/table_turn.csv / .md read by the manuscript (turn table of the spatial-additions report; the two columns
    "+600 s / +1,800 s" hold lo / hi)."""
    import windport_report_spatial as AR
    (comp / "_tmp").mkdir(parents=True, exist_ok=True)
    A_, B_ = AR.sites(rd(R137 / "runs/unified_sites" / "points.csv"), rd(CONSERVATIVE_E6 / "points.csv"), rd(UNIFIED["siteport"] / "points.csv"),
                      comp / "_tmp", {})
    rows = []
    for r in rd(D["turnwin"] / "points.csv"):
        rows.append(dict(r, extra={1.0: 600.0, 2.0: 1800.0}[float(r["extra"])]))
    (comp / "spatial").mkdir(parents=True, exist_ok=True)
    M = {}
    AR.turn(AR.one("turngeo"), rows, A_, B_, comp / "spatial", M)
    shutil.rmtree(comp / "_tmp", ignore_errors=True)
    N["turnwin"] = M["turn"]


def crit_tau(N, out):
    """Yantai three-voyage, pull-in: τ_cut/p of the cut (the TurnTauFrom / To pair of the critical-point table of the spatial
    additions), turns all feasible / lo / hi."""
    import windport_analytic as A6
    import windport_design_lib as L
    from windport import sim2 as S2
    from windport import sim4 as S4
    rows = []
    for lv in ("feas", "lo", "hi"):
        c = T.cfg_of("e6", T.enc(dict(kind="map:yantai", scen="base", mode="pull_in", lift="cradle", rule="fcfs", L=12, K=10, S=1, G=24)))
        c["geo"] = dict(c["geo"], storage="multi")
        c = L.with_turns(c, "yantai", "multi", "base", lv)
        S2._NETS.clear()
        S4.setup4(c)                                     # build TurnNet first (knows the alternative manoeuvres); A6.tau reads the same cache
        t = A6.tau(c)
        rows.append(dict(level=lv, tau_cut_p=round(t["cut"] / H, 3), tau_zone1_p=round(t["zone1"] / H, 3), res=t["res"]))
    S2._NETS.clear()
    wcsv(out / "crit_tau.csv", rows)
    N["crit_tau"] = rows


# ================================================================ item 5
def crane(D, out, N):
    rows = rd(D["analytic"] / "crane.csv")
    nf = json.loads((D["analytic"] / "crane_not_found.json").read_text(encoding="utf-8"))
    L = ["# Item 5(a): public capacity-radius data of the main cranes of installation vessels, and S_r by distance\n",
         "S_r(R_q) = 1 + ⌊(R_q − 8.25)/15.36⌋ (centre lines of the rebuilt side-by-side rows at 8.25 + 15.36k m from the quay edge); "
         "R_q = radius − distance a from the slewing centre to the quay edge. Points with capacity Q ≥ 2,000 t give the "
         "lower radius bound for 2,000–2,500 t monopiles (the load-radius curve decreases with radius); a ranges over [5 m (slewing "
         "centre at the ship side, e.g. a leg-encircling crane), breadth/2 + 2 m fender (slewing centre on the centre line)], and the "
         "two ends give a lower-bound interval of S_r. "
         "No vessel publishes the distance from the slewing centre to the ship side.\n",
         "| Vessel | Crane | Public point | Breadth m | Applies (Q ≥ 2,000 t) | R_q lower bound m (centre line / ship side) | "
         "S_r lower bound (centre line / ship side) | a ≤ (m) needed for S_r = 2 | Quote | Source |", "|---|---|---|---:|---|---|---|---:|---|---|"]
    for r in rows:
        L.append(f"| {r['vessel']}{' (monopile dedicated)' if r['dedicated'] == '1' else ''} | {r['crane']} | {r['Q_t']} t at {r['R_m']} m | {r['breadth_m']} | {'yes' if r['applies'] == '1' else 'no'} | "
                 f"{r['Rq_lo']} / {r['Rq_hi']} | {r['Sr_lo'] or '-'} / {r['Sr_hi'] or '-'} | {r['a_for_Sr2'] or '-'} | {r['quote']} | {r['source']} ({r['page']}) |")
    L.append("\nNo radius data found: " + ", ".join(nf) + ".")
    L.append("\nReading: the anchor for 2,000–2,500 t monopiles is the monopile-dedicated **Orion** (3,000 t at > 50 m): with the "
             "slewing centre on the centre line (a ≈ breadth/2 + fender = 26.5 m) R_q ≥ 23.5 m, "
             "S_r ≥ 1, only 0.1 m from the S_r = 2 bound (a ≤ 26.4 m); with the slewing centre near the ship side S_r ≥ 3. "
             "**Main case S_r = 1**, because no vessel publishes the slewing-centre position and the centre-line case lies just "
             "below the bound, "
             "so the lower value is taken; S_r = 2 is the supported upper case. Vole au Vent (1,500 t at 21.5 m) has a maximum "
             "capacity below the monopiles of this study and serves only as a 1,500 t-class reference. "
             "Reaching all of S = 6 needs R_q ≥ 85.1 m, beyond all public data.")
    md(out, "crane.md", L)
    N["crane"] = rows


def rate(D, out, N, comp):
    """Table tab_rate (Table 14): the main case of the side-by-side layout becomes S_r = 1 by distance (with the lifting exclusion
    zone), S_r = 2 is also given; all reachable becomes the optimistic upper limit."""
    import windport_report_spatial as AR
    reach = rd(MAIN2["reach"] / "points.csv")
    side = {(r["scen"], r["lift"], i(r["S"]), i(r["K"])): r for r in reach if r["lay"] == "side"}
    rx = {(r["scen"], r["lift"], r["reach"], i(r["S"]), i(r["K"])): r for r in rd(D["rowsx_t7"] / "points.csv")}
    rdist = {(r["scen"], r["lift"], r["reach"], i(r["S"]), i(r["K"])): r for r in rd(MAIN2["reachdist"] / "points.csv")}
    rf = {(r["scen"], r["lift"], r["reach"], i(r["S"]), i(r["K"])): r for r in rd(D["rowsfin"] / "points.csv")}

    def grid(var):
        G = {}
        for sc, lf, S_, K in itertools.product(("base", "lane"), ("cradle", "mixed"), range(0, 7), range(1, 11)):
            if S_ == 0 and lf == "mixed":
                continue
            lfx = "direct" if S_ == 0 else lf
            v = side[(sc, lfx, S_, K)]
            if S_ >= 2:
                if var == "all_x":
                    v = rx[(sc, lf, "all", S_, K)]
                elif var in ("sr1_x", "sr2_x", "sr1_xf", "sr2_xf"):
                    Sr = int(var[2])
                    src = rf if var.endswith("f") else rx
                    v = src[(sc, lf, f"{Sr}_3600", S_, K)] if S_ > Sr else rx[(sc, lf, "all", S_, K)]
                elif var in ("sr1_h", "sr2_h"):
                    Sr = int(var[2])
                    v = rdist[(sc, lf, f"{Sr}_3600", S_, K)] if S_ > Sr else side[(sc, lf, S_, K)]
            G[(sc, lf, S_, K)] = i(v["sim"])
        return G
    VAR = dict(sr1_xf="S_r = 1 by distance + exclusion zone + quay slot by lift-end time (main case)",
               sr2_xf="S_r = 2 by distance + exclusion zone + quay slot by lift-end time",
               all_x="all reachable + exclusion zone (optimistic upper limit, needs R_q ≥ 23.6 / 39.0 m)",
               sr1_x="S_r = 1 + exclusion zone, earliest lift start (original dispatching)", sr2_x="S_r = 2 + exclusion zone, earliest lift start",
               all_h="all reachable, no exclusion zone (main case of the main2 geometry)", sr1_h="S_r = 1, no exclusion zone, earliest lift start (main2)",
               sr2_h="S_r = 2, no exclusion zone, earliest lift start (main2)")
    L = ["# Table tab_rate (Table 14), side-by-side cradles: main case changed to vessel-crane reach S_r by distance (item 5(b)), "
         "lifting exclusion zone added (item 5(c), point 5)\n",
         "A side-by-side row k beyond S_r occupies the vessel crane t_sh = 1 h longer per monopile; exclusion zone: while row k is "
         "lifted, rows 0…k−1 are blocked during [s, s + t_u]; dispatching: under limited reach the quay slot is chosen by lift-end time "
         "(the rule of the spatial additions for tandem reach; \"earliest lift start\" sends vehicles to rows the crane cannot reach "
         "and loses output). L = 12 h, G = 24 h, first-come-first-served. Columns as in Table 7 of the spatial additions.\n",
         "Note: the two \"pieces / cradle\" columns are averages over S = 1 → 6 (only the two ends) and are flattened where unreachable "
         "rows add no output; per-S counts are in Section 1.2.\n",
         "| Side-by-side case | Scenario | Lifting | Pieces / cradle (K = 1) | Second set ≈ cradle count | K = 1 / K = 2 (S = 1) | "
         "Pieces / cradle (plateau) | Plateau S = 1 → 6 |", "|---|---|---|---:|---|---|---:|---|"]
    tab, prof = [], []
    for var, zh in VAR.items():
        G = grid(var)
        for sc in ("base", "lane"):
            c = {(S_, K): G[(sc, "cradle", S_, K)] for S_ in range(0, 7) for K in range(1, 11)}
            x = {(S_, K): G[(sc, "mixed", S_, K)] if S_ else G[(sc, "cradle", 0, K)] for S_ in range(0, 7) for K in range(1, 11)}
            best = {k: max(c[k], x[k]) for k in c}
            for lift, G_ in (("cradle", c), ("mixed", x), ("best", best)):
                t = dict(var=var, scen=sc, lift=lift, **AR.rates(G_))
                tab.append(t)
                L.append(f"| {zh} | {SCEN_ZH[sc]} | {dict(cradle='cradle', mixed='mixed', best='best')[lift]} | {t['per_cradle_K1']} | {t['second_set']} | {t['n11']} / {t['n12']} | "
                         f"{t['per_cradle_plat']} | {t['n1_10']} → {t['n6_10']} |")
                for K in (1, 2, 10):
                    prof.append(dict(var=var, scen=sc, lift=lift, K=K, **{f"S{S_}": G_[(S_, K)] for S_ in range(0, 7)}))
    L += ["\n## 1.2 Pieces per S (S = 0 … 6; cradle / mixed / best)\n", "| Side-by-side case | Scenario | Lifting | K | S = 0 | 1 | 2 | 3 | 4 | 5 | 6 |",
          "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    L += [f"| {VAR[p['var']]} | {SCEN_ZH[p['scen']]} | {dict(cradle='cradle', mixed='mixed', best='best')[p['lift']]} | {p['K']} | " + " | ".join(str(p[f"S{S_}"]) for S_ in range(0, 7)) + " |"
          for p in prof if p["var"] in ("sr1_xf", "sr2_xf", "all_x", "sr1_x")]
    wcsv(out / "rate.csv", tab)
    wcsv(out / "rate_profile.csv", prof)
    md(out, "rate.md", L)
    N["rate"] = dict(tab=tab, profile=prof)
    # spatial/table7_rate.csv read by the manuscript: side-by-side rows replaced by the main case (S_r = 1 + exclusion zone + quay slot by lift-end time)
    rows = [r for r in reach if r["lay"] != "side"]
    G = grid("sr1_xf")
    for r in reach:
        if r["lay"] == "side":
            S_, K = i(r["S"]), i(r["K"])
            rows.append(dict(r, sim=G[(r["scen"], "cradle" if r["lift"] == "direct" else r["lift"], S_, K)]))
    (comp / "spatial").mkdir(parents=True, exist_ok=True)
    M = {}
    rows = [dict(r, wprime=r.get("wprime", r["w4"])) for r in rows]          # rows from the unified bound on have no W′ column (AR.reach uses it in one count only)
    AR.reach(rows, rd(MAINGEOM_E4 / "points.csv"), rd(MAINGEOM_MIX6 / "points.csv"), comp / "spatial", M)
    for f in ("fig7_layouts.png", "fig7_iso.csv"):
        (comp / "spatial" / f).unlink(missing_ok=True)


def checks(D, out, N):
    rs = rd(D["analytic"] / "checks.csv")
    sp = rd(D["spacing"] / "points.csv")
    L = ["# Item 5(c): minimal geometric validation set (four configurations × five items)\n", "| Configuration | Check | Verdict | Value | Note |",
         "|---|---|---|---|---|"]
    L += [f"| {r['config']} | {r['item']} | {r['verdict']} | {r['value']} | {r['note']} |" for r in rs]
    by = {(r["scen"], r["lay"], r["arr"], i(r["K"]), float(r["sp"])): fl(r["port_h"]) for r in sp}
    L += ["\n## Tandem cradle spacing 110 → 115 m (L_v + δ): port time of the core cases (h, 10 monopiles per vessel, Q_h = 0, "
          "first-come-first-served)\n",
          "| Scenario | Cradle | Lifting | K = 1 | 2 | 3 | 4 | 8 | Max difference |", "|---|---|---|---|---|---|---|---|---:|"]
    mx = 0.0
    for sc, lay, arr in itertools.product(("lane", "longslow"), T.MODES, ("S1", "S3", "S3m")):
        d = [by[(sc, lay, arr, K, 115.0)] - by[(sc, lay, arr, K, 110.0)] for K in range(1, 9)]
        mx = max(mx, max(abs(x) for x in d))
        L.append(f"| {SCEN_ZH[sc]} | {MODE_ZH[lay]} | {arr} | " + " | ".join(f"{by[(sc, lay, arr, K, 110.0)]:.2f} → {by[(sc, lay, arr, K, 115.0)]:.2f}" for K in (1, 2, 3, 4, 8)) +
                 f" | {max(d, key=abs):+.2f} |")
    md(out, "checks.md", L)
    N["checks"] = dict(rows=rs, spacing_max_diff_h=round(mx, 3))


# ================================================================ item 6
def cd_dep(x, rc):
    """Configurations where the quay-slot rule matters: tandem S ≥ 2 (far cradles t_sh) and side by side S ≥ 2 with reach by distance
    (S_r = 1, 2). Elsewhere both rules give the same result."""
    return x["S"] >= 2 and (x["lay"] == "tandem" or rc in ("1", "2"))


def cd_sources(D, items, blk="150", rule="best"):
    """{(cd, n_v, reach): point}: sources of the co-design points. Base port (passage not blocked): codesign, rowsx_cd adding the
    exclusion zone for side by side S ≥ 2, cdfin for slot choice by lift-end time (side by side), and cdblk2 with blk = "" (tandem).
    Long single lane (passage uniformly split into blocks of length blk): 150 m uses cdblk + cdblk2 with blk = 150, 75 / 300 m use
    cdblk2 only. Each dispatch-dependent key has two versions (earliest lift start "start" / by lift-end time "finish"):
    rule = "best" (main case: the quay-slot rule is a design variable, the one with the shorter port time is taken, "finish" on ties),
    "finish" (earlier main rule, kept for comparison), "start"."""
    key = lambda r: (int(r["cd"]), int(r["n_v"]), r["reach"])
    var = {}
    lane = lambda r: items[key(r)[0]]["scen"] == "lane"
    side2 = lambda r: items[key(r)[0]]["lay"] == "side" and items[key(r)[0]]["S"] >= 2

    def put(r, b):
        var.setdefault(key(r), {})["finish" if r.get("disp") == "finish" else "start"] = dict(r, _blk=b)
    for r in rd(D["codesign"] / "points.csv"):
        if not lane(r) and not side2(r):
            put(r, "")
    for name in ("rowsx_cd", "cdfin"):
        for r in rd(D[name] / "points.csv"):
            if not lane(r):
                put(r, "")
    if blk == "150":
        for r in rd(D["cdblk"] / "points.csv"):
            put(r, "150")
    for r in rd(D["cdblk2"] / "points.csv"):
        if (r.get("blk", "") == "" and not lane(r)) or (r.get("blk", "") == blk and lane(r)):
            put(r, r.get("blk", ""))
    out = {}
    for k, v in var.items():
        x = items[k[0]]
        want = blk if x["scen"] == "lane" else ""
        assert all(r["_blk"] == want for r in v.values()), (k, blk)
        if cd_dep(x, k[2]):
            assert set(v) == {"start", "finish"}, (k, set(v))
            if rule == "best":
                r = v["finish"] if fl(v["finish"]["port_h"]) <= fl(v["start"]["port_h"]) + 1e-9 else v["start"]
            else:
                r = v[rule]
        else:
            assert set(v) == {"start"}, (k, set(v))
            r = v["start"]
        out[k] = r
    return out


def cd_disp_effect(D, items):
    """Lift-end time vs earliest lift start (same configuration, same block length; base port unblocked, long single lane 150 m):
    dispatch-dependent keys compared one by one."""
    st, fi = cd_sources(D, items, "150", "start"), cd_sources(D, items, "150", "finish")
    out = collections.defaultdict(lambda: dict(faster=0, same=0, slower=0, d_slow=[], d_fast=[]))
    for k in st:
        x = items[k[0]]
        if not cd_dep(x, k[2]):
            continue
        d = fl(fi[k]["port_h"]) - fl(st[k]["port_h"])
        c = out[(x["scen"], x["lay"], "K = 1" if x["K"] == 1 else "K ≥ 2")]
        c["faster" if d < -1e-6 else "slower" if d > 1e-6 else "same"] += 1
        (c["d_slow"] if d > 1e-6 else c["d_fast"] if d < -1e-6 else []).append(d)
    return {k: dict(faster=v["faster"], same=v["same"], slower=v["slower"], slow_mean=round(sum(v["d_slow"]) / len(v["d_slow"]), 2) if v["d_slow"] else None,
                    slow_max=round(max(v["d_slow"]), 2) if v["d_slow"] else None, fast_mean=round(sum(v["d_fast"]) / len(v["d_fast"]), 2) if v["d_fast"] else None)
            for k, v in sorted(out.items())}


def cd_rows(pts, items, g, lst):
    rows = []
    for (ix, n, rc), r in sorted(pts.items()):
        x = items[ix]
        T_ = fl(r["port_h"])
        fleet = x["K"] * g["set_day"] * g["cycle"]
        cradle = x["S"] * g["support"] / g["calls"]
        cfgs = json.dumps(dict(geo=x["geo"], p=x["p"], S=x["S"], K=x["K"], lift=x["lift"], hold=x["hold"], n_v=n), sort_keys=True)
        row = dict(i=ix, scen=x["scen"], n_v=n, K=x["K"], S=x["S"], lay=x["lay"], mode=x["mode"], lift=x["lift"], hold=x["hold"], pass_=x["pass_"],
                   widen=x["widen"], reach=rc, port_h=T_, lstar_h=fl(r["lstar_lo"]), lstar_main2=lst.get(cfgs), check_ok=r["check_ok"], fleet_eur=fleet, cradle_eur=cradle,
                   disp=r.get("disp") or ("start" if cd_dep(x, rc) else ""), blk=r["_blk"])
        for rate in g["rates"]:
            row[f"vessel_{rate // 1000}k"] = T_ / 24 * rate
            row[f"cost_{rate // 1000}k"] = T_ / 24 * rate + fleet + cradle
        # feasible: tandem (far cradles t_sh = 1 h per monopile when S > 1); side by side S ≤ 1; side by side S ≥ 2 with S_r = 1 by
        # distance (main case). S_r = 2 and all reachable are listed separately. Quay-slot rule: see cd_sources.
        row["main"] = int(x["lay"] != "side" or x["S"] <= 1 and rc == "all" or (x["S"] >= 2 and rc == "1"))
        rows.append(row)
    return rows


INF = [("plain", (0, 0, 0)), ("hold", (1, 0, 0)), ("pass_", (0, 1, 0)), ("widen", (0, 0, 1)), ("pass_widen", (0, 1, 1))]


def cd_desc(r):
    side = r["lay"] == "side" and r["S"] >= 2
    return (f"K = {r['K']}, S = {r['S']} {MODE_ZH.get(r['mode'], r['mode'])}" + (" (" + ("S_r = " + r["reach"] if r["reach"] in ("1", "2") else "all reachable") + ")" if side else "") +
            f", {dict(cradle='cradle', mixed='mixed lifting', direct='direct lift')[r['lift']]}, T = {r['port_h']:.2f} h")


def cd_best(rows, g):
    res = []
    for sc, n in itertools.product(g["scen"], g["n_v"]):
        for rate in g["rates"]:
            ck = f"cost_{rate // 1000}k"
            pool = [r for r in rows if r["scen"] == sc and r["n_v"] == n and r["main"]]
            best = {}
            for tag, flags in INF:
                c = [r for r in pool if (r["hold"], r["pass_"], r["widen"]) == flags]
                best[tag] = min(c, key=lambda r: (r[ck], r["port_h"], r["i"]))
            opt = min(pool, key=lambda r: (r[ck], r["port_h"], r["i"]))
            b0 = best["plain"]
            line = dict(scen=sc, n_v=n, rate=rate, opt=cd_desc(opt), opt_cost=round(opt[ck]),
                        opt_infra="+".join(t for t, fl_ in INF[1:] if (opt["hold"], opt["pass_"], opt["widen"]) == fl_) or "none")
            for tag, _ in INF:
                b = best[tag]
                line[f"{tag}_cfg"] = cd_desc(b)
                line[f"{tag}_cost"] = round(b[ck])
                if tag != "plain":
                    line[f"{tag}_save"] = round(b0[ck] - b[ck])
                    line[f"{tag}_save_vessel"] = round(b0[f"vessel_{rate // 1000}k"] - b[f"vessel_{rate // 1000}k"])
                    line[f"{tag}_save_fleet"] = round(b0["fleet_eur"] - b["fleet_eur"])
                    line[f"{tag}_save_cradle"] = round(b0["cradle_eur"] - b["cradle_eur"])
            for var in ("2", "all"):                               # optimum under optimistic reach (S_r = 2 / all reachable)
                pv = [r for r in rows if r["scen"] == sc and r["n_v"] == n and (r["main"] or (r["lay"] == "side" and r["S"] >= 2 and r["reach"] == var))]
                ov = min(pv, key=lambda r: (r[ck], r["port_h"], r["i"]))
                line[f"opt_{var}"] = cd_desc(ov)
                line[f"opt_{var}_cost"] = round(ov[ck])
            lb = min(pool, key=lambda r: (r["lstar_h"] / 24 * rate + r["fleet_eur"] + r["cradle_eur"], r["i"]))
            line["lstar_pick"] = cd_desc(lb)
            line["lstar_pick_extra"] = round(lb[ck] - opt[ck])
            res.append(line)
    return res


def cd_widen(rows):
    wv = []
    for r in rows:
        if r["scen"] == "lane" and r["n_v"] == 10 and r["main"] and r["hold"] == 0 and r["pass_"] == 1 and r["widen"] == 0:
            twin = [q for q in rows if q["scen"] == "lane" and q["n_v"] == 10 and q["main"] and q["hold"] == 0 and (q["K"], q["S"], q["lay"], q["mode"], q["lift"], q["reach"]) ==
                    (r["K"], r["S"], r["lay"], r["mode"], r["lift"], r["reach"])]
            w = [q for q in twin if (q["pass_"], q["widen"]) == (0, 1)]
            pw = [q for q in twin if (q["pass_"], q["widen"]) == (1, 1)]
            if w and pw:
                wv.append(dict(K=r["K"], S=r["S"], lay=r["lay"], mode=r["mode"], lift=r["lift"], pass_T=r["port_h"], pass_L=r["lstar_h"], widen_T=w[0]["port_h"],
                               widen_L=w[0]["lstar_h"], both_T=pw[0]["port_h"], both_L=pw[0]["lstar_h"]))
    faster = [x for x in wv if x["widen_T"] < x["pass_T"] - 1e-6]
    slower = [x for x in wv if x["widen_T"] > x["pass_T"] + 1e-6]
    at_lb = [x for x in wv if abs(x["widen_T"] - x["widen_L"]) < 1e-6]
    return wv, dict(n=len(wv), faster=len(faster), same=len(wv) - len(faster) - len(slower), slower=len(slower), at_lb=len(at_lb),
                    slower_by=dict(collections.Counter(f"{x['lay']} S={x['S']}" for x in slower)))


def codesign(D, out, N):
    import windport_spatial_analytic as AA
    import windport_design as X
    g = AA.GRIDS["codesign"]
    items = X.cd_items()
    lst = {r["cfg"]: fl(r["lstar_h"]) for r in rd(MAIN2["codesign"] / "codesign.csv")}
    variant = {(b, rule): cd_rows(cd_sources(D, items, b, rule), items, g, lst) for b in ("75", "150", "300") for rule in ("best", "finish")}
    rows = variant[("150", "best")]
    wcsv(out / "codesign.csv", rows)
    res = cd_best(rows, g)
    wcsv(out / "codesign_best.csv", res)
    L = ["# Item 6: co-design - full simulation of the enumeration space (2,176 configurations × n_v = 3, 5, 10; "
         "first-come-first-served, conservative lifting semantics, main geometry main2)\n",
         "Cost = vessel day rate × T/24 + K × 7,200 €/day × 6 days (vehicle-set hire charged continuously over the voyage period) "
         "+ S × 60,000 €/10 calls (cradle amortisation, Kassels Appendix D: 10 voyages in 61 days). "
         "Feasible configurations (main case): tandem (far cradles t_sh = 1 h per monopile when S > 1; cradle spacing 110 m as in the "
         "main geometry, zero end gap between adjacent piles; the 115 m rule was only tested as a sensitivity on the core cases, "
         "effect ≤ 0.01 h), "
         "side by side S ≤ 1, side by side S ≥ 2 with S_r = 1 by distance (with the lifting exclusion zone). S_r = 2 and all "
         "reachable are computed separately (optimistic). "
         "**The quay-slot rule is a design variable**: dispatch-dependent configurations (tandem S ≥ 2, side by side S ≥ 2 with "
         "reach by distance) are simulated with both \"earliest lift start\" and \"by lift-end time\", and the shorter port time is taken; "
         "slot choice by lift-end time only (the rule of Table 14) is the comparison at the end. "
         "Optimum = lowest simulated cost in the enumeration space (no ranking by L* first followed by spot checks); saving = optimum "
         "without upgrade − optimum with the upgrade, split into port time (vessel hire), vehicle hire and cradle amortisation; "
         "×10 voyages gives the break-even investment of one campaign. "
         "All passage options of the long single lane (single lane, passing place, widening to 16 m, both) use block signalling: "
         "passage segments are split evenly into blocks ≤ 150 m (main case; blocks extension of occupancy), same-direction vehicles "
         "may follow block by block, "
         "opposite directions stay mutually exclusive; the bound adds a pure loaded cut term (see the manuscript). Block lengths "
         "75 / 300 m: sensitivity at the end.\n"]
    for sc, n in itertools.product(g["scen"], g["n_v"]):
        L += [f"\n## {SCEN_ZH.get(sc, sc)}, {n} monopiles per vessel\n",
              "| Day rate | Operating-cost optimum (€/voyage) | Optimum without upgrade | Gate holding place | Passing place | "
              "Widening to 16 m | Passing place + widening | Optimum with S_r = 2 / all reachable | Extra cost of the L* first pick |",
              "|---|---|---|---|---|---|---|---|---:|"]
        for line in [x for x in res if x["scen"] == sc and x["n_v"] == n]:
            cell = lambda t: (f"{line[t + '_cfg']}; {line[t + '_cost']:,}" + ("" if t == "plain" else
                              f"; saves {line[t + '_save']:,} (port time {line[t + '_save_vessel']:,} / vehicles {line[t + '_save_fleet']:,} / cradles {line[t + '_save_cradle']:,})"))
            L.append(f"| {line['rate'] // 1000}k | {line['opt']}; {line['opt_cost']:,} ({line['opt_infra']}) | " + " | ".join(cell(t) for t, _ in INF) +
                     f" | {line['opt_2_cost']:,} / {line['opt_all_cost']:,} | {line['lstar_pick_extra']:,} |")
    wv, wc = cd_widen(rows)
    wcsv(out / "widen_vs_pass.csv", wv)
    L += ["\n## Widening to 16 m vs passing place: port time and rule-independent lower bound for the same configuration (long single "
          "lane, 10 monopiles per vessel, no gate holding place; the 12 groups with the largest difference)\n",
          "| Configuration | Passing place: T / L″* | Widening 16 m: T / L″* | Passing place + widening: T / L″* |", "|---|---|---|---|"]
    for x in sorted(wv, key=lambda x: abs(x["widen_T"] - x["pass_T"]), reverse=True)[:12]:
        L.append(f"| K = {x['K']}, S = {x['S']} {'side by side' if x['lay'] == 'side' else MODE_ZH[x['mode']]}, {x['lift']} | {x['pass_T']:.2f} / {x['pass_L']:.2f} | "
                 f"{x['widen_T']:.2f} / {x['widen_L']:.2f} | {x['both_T']:.2f} / {x['both_L']:.2f} |")
    L.append(f"\n{wc['n']} groups in total (uniform block signalling 150 m): widening faster than passing place in {wc['faster']}, equal in {wc['same']}, "
             f"slower in {wc['slower']} ({wc['slower_by'] or '-'}); "
             f"widening port time equal to its lower bound L″* in {wc['at_lb']} groups.")
    # block-length sensitivity (main-case rule)
    sens = {}
    L += ["\n## Block-length sensitivity (long single lane; same block length for the four passage options; quay-slot rule as in the "
          "main case)\n",
          "| Block length | Day rate | Optimum for 3 / 5 monopiles per vessel (€) | 10 per vessel: operating-cost optimum | "
          "Optimum without upgrade (€) | Gate holding place / passing place / widening / both: saving (€) | "
          "Widening vs passing place: faster / equal / slower | Extra cost of the L* first pick (10 per vessel) |",
          "|---:|---|---|---|---:|---|---|---:|"]
    for b in ("75", "150", "300"):
        rb = variant[(b, "best")]
        rs = cd_best(rb, g)
        _, wcb = cd_widen(rb)
        sens[b] = dict(best=[x for x in rs if x["scen"] == "lane"], widen=wcb)
        for rate in g["rates"]:
            ln = {x["n_v"]: x for x in rs if x["scen"] == "lane" and x["rate"] == rate}
            t = ln[10]
            L.append(f"| {b} m | {rate // 1000}k | {ln[3]['opt_cost']:,} / {ln[5]['opt_cost']:,} | {t['opt']} ({t['opt_infra']}); {t['opt_cost']:,} | {t['plain_cost']:,} | "
                     f"{t['hold_save']:,} / {t['pass__save']:,} / {t['widen_save']:,} / {t['pass_widen_save']:,} | {wcb['faster']} / {wcb['same']} / {wcb['slower']} | {t['lstar_pick_extra']:,} |")
    # port-time differences caused by the block length (point by point, same rule)
    bd = {}
    for rule in ("best", "finish"):
        m = {(r["i"], r["n_v"], r["reach"]): r for r in variant[("150", rule)] if r["scen"] == "lane"}
        for b in ("75", "300"):
            d = [(r["port_h"] - m[(r["i"], r["n_v"], r["reach"])]["port_h"], r) for r in variant[(b, rule)] if r["scen"] == "lane"]
            d = [(x, r) for x, r in d if abs(x) > 1e-6]
            bd[f"{rule}_{b}"] = dict(n=len(d), shorter=sum(1 for x, _ in d if x < 0), longer=sum(1 for x, _ in d if x > 0),
                                     max_abs=round(max((abs(x) for x, _ in d), default=0.0), 3), over_02=sum(1 for x, _ in d if abs(x) > 0.2),
                                     lstar_diff=sum(1 for r in variant[(b, rule)] if r["scen"] == "lane" and abs(r["lstar_h"] - m[(r["i"], r["n_v"], r["reach"])]["lstar_h"]) > 1e-9),
                                     by=dict(collections.Counter(f"n_v={r['n_v']} hold={r['hold']} pass={r['pass_']}" for _, r in d)))
    L += ["\nPort-time differences caused by the block length (long single lane, 3,840 points, point by point against 150 m):"]
    for k, v in bd.items():
        L.append(f"- {k}: {v['n']} points differ (shorter {v['shorter']} / longer {v['longer']}, max {v['max_abs']} h, {v['over_02']} points > 0.2 h); "
                 f"L″* differs at {v['lstar_diff']} points; {v['by']}")
    # comparison: quay slot by lift-end time only
    rs = cd_best(variant[("150", "finish")], g)
    _, wcf = cd_widen(variant[("150", "finish")])
    sens["finish"] = dict(best=rs, widen=wcf)
    L += ["\n## Comparison: dispatch-dependent configurations with the quay slot chosen by lift-end time only (as in Table 14; "
          "block length 150 m)\n",
          "| Scenario | Per vessel | Day rate | Operating-cost optimum | Optimum without upgrade | Gate holding place / passing place / "
          "widening / both: saving (€) | Extra cost of the L* first pick |", "|---|---:|---|---|---|---|---:|"]
    for t in rs:
        L.append(f"| {SCEN_ZH.get(t['scen'], t['scen'])} | {t['n_v']} | {t['rate'] // 1000}k | {t['opt']} ({t['opt_infra']}); {t['opt_cost']:,} | {t['plain_cfg']}; {t['plain_cost']:,} | "
                 f"{t['hold_save']:,} / {t['pass__save']:,} / {t['widen_save']:,} / {t['pass_widen_save']:,} | {t['lstar_pick_extra']:,} |")
    L.append(f"\nWidening vs passing place (same 112 groups): faster {wcf['faster']}, equal {wcf['same']}, slower {wcf['slower']} ({wcf['slower_by'] or '-'}); "
             f"widening equal to the lower bound in {wcf['at_lb']} groups.")
    # dispatching effect
    de = cd_disp_effect(D, items)
    L += ["\n## Lift-end time vs earliest lift start (dispatch-dependent configurations; base port unblocked, long single lane 150 m)\n",
          "| Scenario | Layout | Vehicle sets | Faster | Equal | Slower | Mean of faster | Mean / max of slower (h) |",
          "|---|---|---|---:|---:|---:|---:|---|"]
    dash = lambda v: "-" if v is None else v
    for (sc, lay, kk), v in de.items():
        L.append(f"| {SCEN_ZH.get(sc, sc)} | {'tandem' if lay == 'tandem' else 'side by side'} | {kk} | {v['faster']} | {v['same']} | {v['slower']} | {dash(v['fast_mean'])} | "
                 f"{dash(v['slow_mean'])} / {dash(v['slow_max'])} |")
    pick = collections.Counter(f"{r['scen']}:{r['disp']}" for r in rows if cd_dep(items[r["i"]], r["reach"]))
    L.append(f"\nRules chosen by the main case (faster of the two): {dict(pick)} (ties counted as finish).")
    md(out, "codesign.md", L)
    N["codesign_widen_cmp"] = wc
    N["codesign_sens"] = sens
    N["codesign_blockdiff"] = bd
    N["codesign_disp"] = {"|".join(k): v for k, v in de.items()}
    N["codesign"] = dict(best=res, widen=wc, n_rows=len(rows),
                         check_bad=sum(1 for r in rows if str(r["check_ok"]) not in ("1", "True")), below_lstar=sum(1 for r in rows if r["port_h"] < r["lstar_h"] - 1e-9))


# ================================================================ item 7
def campaign(D, out, N):
    par = rd(D["analytic"] / "campaign_params.csv")
    cam = rd(D["analytic"] / "campaign.csv")
    L = ["# Item 7: parameters of the campaign model of Section 6.3 (supplementary table) and recomputation\n", "| Parameter | Value | Unit | Meaning |",
         "|---|---|---|---|"]
    L += [f"| {r['parameter']} | {r['value']} | {r['unit']} | {r['meaning']} |" for r in par]
    L += ["\n## Recomputation (E3 port times from the E3 batch rerun on the main geometry; mean over 200 seeds, days)\n",
          "| Scenario | n_v | K | q | Port h: road occupancy / fixed duration | Campaign days: road occupancy / fixed duration | "
          "Difference: mean (P10–P90) | Sum of port-time differences |",
          "|---|---:|---:|---:|---|---|---|---:|"]
    L += [f"| {r['scen']} | {r['n_v']} | {r['K']} | {r['q']} | {r['port_occ_h']} / {r['port_fix_h']} | {r['days_occ']} / {r['days_fix']} | {r['diff_mean']} ({r['diff_p10']}–{r['diff_p90']}) | {r['naive']} |"
          for r in cam]
    got = sorted(round(float(r["diff_mean"]), 2) for r in cam if r["scen"] == "lane" and r["n_v"] == "10" and r["K"] == "2")
    L.append(f"\nLong single lane, two vehicle sets, 10 monopiles per vessel: {got[0]:.2f}–{got[-1]:.2f} days (manuscript \\CampTenLo–\\CampTenHi = 1.21–1.22). "
             "The second decimal depends on the seeds (seeds 1001–1200 give "
             "1.253 / 1.196 days): the supplementary material states seeds 1–200, the main text says \"about 1.2 days\" with P10–P90.")
    md(out, "campaign.md", L)
    N["campaign"] = dict(ten=got)


# ================================================================ recheck
def recheck(D, out, N):
    L = ["# Recheck of the new simulations (checker, upper bound, lower bound, per-monopile W″_lift(T_j) ≥ j)\n",
         "| Batch | Points | Checker failures | Simulation > W″_lift | Port time < L″_lift* | W″_lift(T_j) < j (monopiles) | "
         "Monopiles checked one by one |", "|---|---:|---:|---:|---:|---:|---:|"]
    tot = collections.Counter()
    for name in ("e6_lo", "e6_hi"):
        rc = rd(D[name] / "recheck.csv")
        pts = rd(D[name] / "points.csv")
        a = dict(n=len(pts), bad=sum(1 for r in pts if r["check_ok"] != "1"), over=sum(int(r["over"]) for r in rc), lb=0, viol=0, roots=0)
        L.append(f"| {name} | {a['n']} | {a['bad']} | {a['over']} | - | - | - |")
        tot.update(a)
    for name in ("yards", "near", "transfer", "codesign", "rowsx_cd", "cdfin", "cdblk", "cdblk2", "spacing", "tr10"):
        pts = rd(D[name] / "points.csv")
        a = dict(n=len(pts), bad=sum(1 for r in pts if r["check_ok"] not in ("1", "True")), over=0,
                 lb=sum(1 for r in pts if fl(r["port_h"]) is not None and fl(r["port_h"]) < fl(r["lstar_lo"]) - 1e-9),
                 viol=sum(i(r["viol"]) for r in pts if r.get("viol") not in ("", None, "None")),
                 roots=sum(i(r["lifts"]) for r in pts if r.get("viol") not in ("", None, "None")))
        L.append(f"| {name} | {a['n']} | {a['bad']} | - | {a['lb']} | {a['viol']} | {a['roots']} |")
        tot.update(a)
    for name in ("rowsx_t7", "rowsfin", "turnwin"):
        pts = rd(D[name] / "points.csv")
        a = dict(n=len(pts), bad=sum(1 for r in pts if r["check_ok"] not in ("1", "True")), over=sum(1 for r in pts if r.get("w4") not in ("", None) and i(r["sim"]) > i(r["w4"])),
                 lb=0, viol=0, roots=0)
        L.append(f"| {name} | {a['n']} | {a['bad']} | {a['over']} | - | - | - |")
        tot.update(a)
    L.append(f"| **Total** | {tot['n']} | {tot['bad']} | {tot['over']} | {tot['lb']} | {tot['viol']} | {tot['roots']} |")
    md(out, "recheck.md", L)
    N["recheck"] = dict(tot)


# ================================================================ manuscript
E_RECHECK = R137 / "runs/unified_recheck"


def e_recheck_compat(D, comp):
    """The manuscript reads the E6 attainment share and binding terms (runs:e6, conservative semantics) from rows.csv of the
    unified-bound recheck: these rows are replaced by the e6:hi simulation of the design analyses and the unified upper bound
    W″_lift (other rows unchanged)."""
    hi = {r["key"]: r for r in rd(D["e6_hi"] / "recheck.csv")}
    src = rd(E_RECHECK / "rows.csv")
    out = []
    for r in src:
        if r["batch"] == "runs:e6" and r["sem"] == "lift":
            h = hi[r["key"]]
            r = dict(r, sim=h["sim"], new=h["w2_lift"], tie=str(int(int(h["sim"]) == int(h["w2_lift"]))), cls=h["w2_cls"], nature=h["w2_nature"], keys=h["w2_binding"],
                     over=str(int(int(h["sim"]) > int(h["w2_lift"]))))
        out.append(r)
    with open(comp / "e_recheck_rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(src[0].keys()))
        w.writeheader()
        w.writerows(out)


def reports_after(out, D):
    """The three committed summary scripts (reports of the E1-E3 batches, the E4-E7 batches and the extra analyses) applied unchanged
    to the batch directories of the main2 geometry, with only runs:e6 replaced by e6:hi of the design analyses (the manuscript table
    tab_yards comes from the E6 table of the E4-E7 summary; same use as run_reports in windport_report_main2)."""
    import windport_report_conservative as R
    import windport_report_main2 as HR
    R.TMP = ROOT / "out" / "design_rep"
    HD = HR.dirs()
    Db = HR.batch_dirs(HD)
    R.SWAP[R.RC].update(example="extra:example", critical="extra:critical")
    Db.update({"extra:example": HD["example"].name, "extra:critical": HD["critical"].name})
    Db["runs:e6"] = D["e6_hi"].name
    return R.run_reports("after", Db, out)


def paper(out, comp, D, N):
    import windport_report_main2 as HR
    mp_h = json.loads((H_REP / "paper_mapping.json").read_text(encoding="utf-8"))
    rel = lambda p: p.relative_to(ROOT).as_posix()
    fr = rel(F_REP)
    mp_i = dict(mp_h)
    mp_i[rel(CONSERVATIVE_E6)] = rel(D["e6_hi"])                                   # table tab_yards: main case hi
    e_recheck_compat(D, comp)
    mp_i[rel(E_RECHECK) + "/rows.csv"] = rel(comp / "e_recheck_rows.csv")
    ra = reports_after(out, D)
    for p in (F_REP / "reports" / "after").iterdir():
        new = next(q for q in ra.values() if q.name.split("_")[:-1] == p.name.split("_")[:-1])
        mp_i[rel(p)] = rel(new)
    mp_i[fr + "/yards.csv"] = rel(comp / "yards.csv")
    for f in ("table_turn.csv", "table_turn.md", "table7_rate.csv", "table7_rate.md"):
        mp_i[fr + "/spatial/" + f] = rel(comp / "spatial" / f)
    (out / "paper_mapping.json").write_text(json.dumps(mp_i, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    M0, f0 = HR.numbers("main2", mp_h, out)
    M1, f1 = HR.numbers("design", mp_i, out)
    rows = [dict(macro=k, main2=M0.get(k, ""), design=M1.get(k, ""), changed=int(M0.get(k, "") != M1.get(k, ""))) for k in sorted(set(M0) | set(M1))]
    wcsv(out / "paper_macros.csv", rows)
    ch = [r for r in rows if r["changed"]]
    key = lambda r: (r["kind"], r["src"].split("  ⇒")[0])
    k0 = {key(r) for r in f0}
    newf = [r for r in f1 if key(r) not in k0]
    wcsv(out / "numbers_fail_new.csv", newf or [dict(kind="", line="", src="")])
    md(out, "paper_macros.md", ["# Manuscript macros (current scripts/make_numbers.py): main2 directories → design-analysis directories "
                                "(table tab_yards uses hi; the two columns of tab_yards3 and table_turn replaced by lo / hi; side-by-side "
                                "rows of Table 7 replaced by S_r = 1 + exclusion zone + quay slot by lift-end time)\n",
                                f"{len(rows)} macros, {len(ch)} changed; failing assertions / erroring statements: main2 {len(f0)}, "
                                f"design analyses {len(f1)}, {len(newf)} new.\n",
                                "| Macro | main2 | **design analyses** |", "|---|---|---|"] + [f"| \\{r['macro']} | {r['main2']} | **{r['design']}** |" for r in ch])
    N["paper"] = dict(macros=len(rows), changed=len(ch), fails_h=len(f0), fails_i=len(f1), fails_new=len(newf))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_design as X
    X.setup_env()
    D = dirs()
    ins = sorted(p for d in D.values() for p in d.glob("*.csv")) + [D["turn"] / "turn_alt.json"]
    h = hashlib.sha256(Path(__file__).read_bytes())
    for f in ins:
        h.update(f.read_bytes())
    out = R137 / f"windport_design_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    comp = out / "compat"
    N = {}
    twolevel(D, out, N)
    eem(D, out, N)
    screen(D, out, N)
    turn(D, out, N)
    yards1(D, out, N)
    yards3(D, out, N, comp)
    crit_tau(N, out)
    turnwin_compat(D, out, N, comp)
    crane(D, out, N)
    rate(D, out, N, comp)
    checks(D, out, N)
    codesign(D, out, N)
    campaign(D, out, N)
    recheck(D, out, N)
    paper(out, comp, D, N)
    (out / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out / "inputs.json").write_text(json.dumps([str(f.relative_to(ROOT)).replace("\\", "/") for f in ins], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)
    print(json.dumps(dict(paper=N["paper"], recheck=N["recheck"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
