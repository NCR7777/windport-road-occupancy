"""Fig. 2, regime map, Table 2, Fig. 3, Table 3, gate holding place table, release time table and summary (draft figures). Reads
only the per-point summaries points.csv tracked in git and the summary.md files of the theorem checks, not points/, so a clean copy
can rebuild everything. Base case: gate holding places Q_h = 0 (after release the vehicle leaves through the single lane to the
yard side); Table 2 separates "proven optimal" and "feasible only" and splits the differences into positive and negative sides
(unsigned); Table 3 calibrates the fixed-time representation at K_ref.

Inputs (run directory names registered in DIRS; a new directory gives a new output directory):
  e1, e1h, rel, e3  experiments/windport_sim.py --part ...   E1 (Q_h = 0), gate holding places Q_h = 1, 2, unlimited, release time
                                                             of direct lifts, E3
  e2   experiments/windport_e2.py             E2: W1 / CP-SAT / simulation (Table 2)
  e2long  experiments/windport_e2long.py      E2 instances only proven feasible within 60 s, rerun with 600 s; Table 2 uses the rerun
  thm  experiments/windport_thm.py            exhaustive check of Theorems 3 and 4
  w1   experiments/windport_w1_check.py       W1 grid
Output results/windport_report_<first 12 hex digits of the SHA-256 of the inputs and this script>/: fig2.png, fig2.csv,
fig_regime.png, fig_regime.csv, table2.md, table2.csv, fig3.png, fig3.csv, table3.md, table3.csv, table_hold.md, table_hold.csv,
table_rel.md, table_rel.csv, summary.md, inputs.json.

Run: .venv/Scripts/python.exe experiments/windport_report.py
"""
import collections
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIRS = dict(e1="runs/e1", e1h="runs/e1_hold", rel="runs/release_time", e3="runs/e3",
            e2="runs/e2", e2long="runs/e2_long", thm="runs/theorems", w1="runs/w1_grid")
FILES = dict(e1="points.csv", e1h="points.csv", rel="points.csv", e3="points.csv", e2="points.csv", e2long="points.csv", thm="summary.md",
             w1="summary.md")
META = {"Software": None}
SCEN_ZH = dict(base="base", slow="1 km/h", long="long corridor", longslow="long corridor + 1 km/h", lane="long single lane (one segment) + 1 km/h",
               longpile="123.6 m monopile", fastcrane="crane 0.5 h", joint="unload + load (dedicated unloading vehicle)", jointshared="unload + load (shared fleet)")
SC5 = ["base", "slow", "longslow", "lane", "fastcrane"]
plt.rcParams.update({"font.family": ["Microsoft YaHei", "SimHei", "DejaVu Sans"], "axes.unicode_minus": False, "font.size": 8})


def load(k):
    return list(csv.DictReader(open(ROOT / "results" / DIRS[k] / FILES[k], encoding="utf-8")))


def save(fig, out, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, metadata=META)
    (out / name).write_bytes(buf.getvalue())
    plt.close(fig)


def wcsv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def i(x):
    return int(float(x)) if x not in ("", None) else None


def main_lift(r):
    return r["lift"] in ("cradle", "direct")


# ---------------------------------------------------------------- Fig. 2: A1 base, W1 and simulation
def fig2(e1, out):
    rs = [r for r in e1 if r["kind"] == "A1" and r["scen"] == "base" and main_lift(r)]
    Ss, Ks, modes, Gs = [0, 1, 3, 6], [1, 2, 4], ["on_road", "pull_in"], [3, 24]
    fig, ax = plt.subplots(len(modes) * len(Gs), len(Ss), figsize=(11, 9), sharex=True, sharey="row")
    mk = dict(interface="o", staging="s", flow="^")
    data = []
    for a, (mode, G) in enumerate([(m, g) for m in modes for g in Gs]):
        for b, S in enumerate(Ss):
            x = ax[a][b]
            for K, col in zip(Ks, ["C0", "C1", "C2"]):
                pts = sorted((i(r["L"]), i(r["sim"]), i(r["w1"]), r["regime"], r["binding"]) for r in rs
                             if r["mode"] == mode and i(r["G"]) == G and i(r["S"]) == S and i(r["K"]) == K)
                x.plot([p[0] for p in pts], [p[2] for p in pts], "--", color=col, lw=1)
                for L, sim, w1, reg, bd in pts:
                    x.plot(L, sim, mk[reg], color=col, ms=4, mfc="none" if sim < w1 else col)
                    data.append(dict(mode=mode, G=G, S=S, K=K, L=L, sim=sim, w1=w1, gap=w1 - sim, regime=reg, binding=bd))
            x.set_title(f"{'roadside cradles (quay front is the cut)' if mode == 'on_road' else 'pull-in cradles'}, G = {G} h, S = {S}", fontsize=7)
            if a == len(ax) - 1:
                x.set_xlabel("crane window L (h)")
            if b == 0:
                x.set_ylabel("piles lifted onto vessel in window")
    hs = [plt.Line2D([], [], color=c, label=f"K = {K}") for K, c in zip(Ks, ["C0", "C1", "C2"])]
    hs += [plt.Line2D([], [], ls="--", color="k", label="W1 (dashed)")]
    hs += [plt.Line2D([], [], ls="", marker=m, color="k", label=f"simulation, binding: {n}") for n, m in (("interface", "o"), ("staging", "s"), ("flow", "^"))]
    fig.legend(handles=hs, loc="lower center", ncol=7, fontsize=7)
    fig.suptitle("Fig. 2 (draft) layout A1, base parameters, no gate holding place (Q_h = 0): simulation (markers; hollow = below the bound) and W1 (dashed)", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    save(fig, out, "fig2.png")
    wcsv(out / "fig2.csv", data)


# ---------------------------------------------------------------- regime map
def fig_regime(e1, out):
    Ls = [4, 12]
    col = dict(interface=0, staging=1, flow=2)
    fig, ax = plt.subplots(len(Ls), len(SC5), figsize=(12, 5))
    data = []
    for a, L in enumerate(Ls):
        for b, sc in enumerate(SC5):
            g = {(i(r["K"]), i(r["S"])): r for r in e1 if r["kind"] == "A1" and r["scen"] == sc and r["mode"] == "pull_in" and i(r["G"]) == 3
                 and i(r["L"]) == L and main_lift(r)}
            Ks, Ss = sorted({k for k, _ in g}), sorted({s for _, s in g})
            M = [[col[g[(K, S)]["regime"]] for K in Ks] for S in Ss]
            x = ax[a][b]
            x.imshow(M, origin="lower", cmap=matplotlib.colors.ListedColormap(["#4C72B0", "#DD8452", "#55A868"]), vmin=-0.5, vmax=2.5, aspect="auto")
            for yi, S in enumerate(Ss):
                for xi, K in enumerate(Ks):
                    r = g[(K, S)]
                    x.text(xi, yi, f"{r['sim']}/{r['w1']}", ha="center", va="center", fontsize=5.5, color="w")
                    data.append(dict(scen=sc, L=L, K=K, S=S, regime=r["regime"], binding=r["binding"], sim=i(r["sim"]), w1=i(r["w1"])))
            x.set_xticks(range(len(Ks)), Ks)
            x.set_yticks(range(len(Ss)), Ss)
            x.set_title(f"{SCEN_ZH[sc]}, L = {L} h", fontsize=7)
            x.set_xlabel("K")
            if b == 0:
                x.set_ylabel("S")
    hs = [matplotlib.patches.Patch(color=c, label=n) for c, n in zip(["#4C72B0", "#DD8452", "#55A868"], ["interface-limited", "staging-limited", "flow-limited"])]
    fig.legend(handles=hs, loc="lower center", ncol=3, fontsize=7)
    fig.suptitle("Regime map (draft) A1, pull-in cradles, G = 3 h, Q_h = 0: regime of the binding W1 term; cells show simulation / W1", fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    save(fig, out, "fig_regime.png")
    wcsv(out / "fig_regime.csv", data)


# ---------------------------------------------------------------- Table 2: E2
def table2(e2, out, e2long=()):
    """e2long: the 600 s rerun of the instances only proven feasible within 60 s replaces their CP-SAT columns; instances still not
    proven optimal are listed after the table with the gap between bound and best solution."""
    lng = {r["key"]: r for r in e2long}
    e2 = [dict(r, cp_best=lng[r["key"]]["cp_best"], cp_bound=lng[r["key"]]["cp_bound"], cp_status=lng[r["key"]]["cp_status"],
               cp_check=lng[r["key"]]["cp_check"], long="1") if r["key"] in lng else dict(r, long="") for r in e2]
    by = collections.defaultdict(list)
    for r in e2:
        by[(r["hold"], r["scen"], r["mode"])].append(r)
    rows, exc = [], []
    for (h, sc, m), rs in sorted(by.items()):
        opt = [r for r in rs if r["cp_status"] == "OPTIMAL"]
        fea = [r for r in rs if r["cp_status"] != "OPTIMAL"]
        d = lambda r: i(r["cp_best"]) - i(r["sim"])
        rows.append(dict(hold=h, scen=sc, mode=m, n=len(rs), opt=len(opt), feas=len(fea), opt_eq_w1=sum(i(r["cp_best"]) == i(r["w1"]) for r in opt),
                         w1_minus_cp=sum(i(r["w1"]) - i(r["cp_best"]) for r in opt), w1_over=sum(i(r["cp_best"]) > i(r["w1"]) for r in rs),
                         opt_eq_sim=sum(d(r) == 0 for r in opt), cp_gt_sim_n=sum(d(r) > 0 for r in rs), cp_gt_sim=sum(d(r) for r in rs if d(r) > 0),
                         sim_gt_cp_n=sum(d(r) < 0 for r in rs), sim_gt_cp=sum(-d(r) for r in rs if d(r) < 0),
                         checks=sum(r["sim_check"] == "1" and r["cp_check"] in ("1", "") for r in rs)))
        exc += [dict(key=r["key"], w1=r["w1"], cp=r["cp_best"], status=r["cp_status"], sim=r["sim"]) for r in rs if d(r) < 0 or i(r["cp_best"]) > i(r["w1"])]
    wcsv(out / "table2.csv", rows)
    tot = {k: sum(r[k] for r in rows) for k in rows[0] if k not in ("hold", "scen", "mode")}
    L = ["# Table 2 (draft) small instances: W1 / CP-SAT (optimum with waiting only at the origin, W1 + 2 candidate monopiles) / simulation\n",
         "Q_h: number of gate holding places (0 = base case). CP-SAT time limit 60 s; instances only proven feasible within 60 s are rerun with 600 s "
         "and the table uses the rerun. \"Proven optimal\" and \"feasible only\" are listed separately; W1 − optimum is summed over proven-optimal "
         "instances only; CP − simulation is split into positive and negative sides (unsigned).\n",
         "| Q_h | scenario | cradles | instances | proven optimal | feasible only | optimum = W1 | Σ(W1 − optimum) | CP > W1 | optimum = simulation | "
         "CP > simulation: instances / piles | simulation > CP: instances / piles | both schedules verified |",
         "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|"]
    for r in rows + [dict(tot, hold="Total", scen="", mode="")]:
        L.append(f"| {r['hold']} | {SCEN_ZH.get(r['scen'], r['scen'])} | {r['mode']} | {r['n']} | {r['opt']} | {r['feas']} | {r['opt_eq_w1']} | "
                 f"{r['w1_minus_cp']} | {r['w1_over']} | {r['opt_eq_sim']} | {r['cp_gt_sim_n']} / {r['cp_gt_sim']} | {r['sim_gt_cp_n']} / {r['sim_gt_cp']} | {r['checks']} |")
    if exc:
        L += ["\nExceptions (simulation > CP-SAT or CP-SAT > W1):\n", "| instance | W1 | CP-SAT | status | simulation |", "|---|---:|---:|---|---:|"]
        L += [f"| {x['key']} | {x['w1']} | {x['cp']} | {x['status']} | {x['sim']} |" for x in exc]
    if lng:
        L += ["\nInstances only proven feasible within 60 s, rerun with 600 s. The bounds in the \"60 s\" and \"600 s\" columns are the raw CP-SAT"
              " objective bounds and can exceed W1 (W1 + 2 candidate monopiles); only the last column, min(W1, 600 s bound) − best, is the unproven margin:\n",
              "| instance | W1 | simulation | 60 s: best / bound / status | 600 s: best / bound / status | min(W1, 600 s bound) − best |", "|---|---:|---:|---|---|---:|"]
        for k, x in sorted(lng.items()):
            key = k.replace("|", "\\|")
            L.append(f"| {key} | {x['w1']} | {x['sim']} | {x['cp60_best']} / {float(x['cp60_bound']):g} / {x['cp60_status']} | "
                     f"{x['cp_best']} / {float(x['cp_bound']):g} / {x['cp_status']} | "
                     f"{min(i(x['w1']), float(x['cp_bound'])) - i(x['cp_best']):g} |")
    (out / "table2.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return tot


# ---------------------------------------------------------------- Fig. 3, Table 3: E3
def e3_tables(e3, out):
    occ = [r for r in e3 if r["repr"] == "occ"]
    fix = [r for r in e3 if r["repr"] == "fixed"]
    get = lambda rs, **kw: [r for r in rs if all(str(r[k]) == str(v) for k, v in kw.items())]
    modes = ["on_road", "pull_in"]
    fig, ax = plt.subplots(len(modes), len(SC5), figsize=(12, 5), sharex=True)
    data = []
    for a, m in enumerate(modes):
        for b, sc in enumerate(SC5):
            x = ax[a][b]
            for lab, rs, st in (("occupancy Q_h = 0", get(occ, scen=sc, mode=m, S=1, n_v=10, hold="0"), "o-"),
                                ("occupancy Q_h unlimited", get(occ, scen=sc, mode=m, S=1, n_v=10, hold="inf"), "s:"),
                                ("fixed-time K_ref = 1", get(fix, scen=sc, mode=m, S=1, n_v=10, kref=1), "x--"),
                                ("fixed-time K_ref = 3", get(fix, scen=sc, mode=m, S=1, n_v=10, kref=3), "+--")):
                pts = sorted((i(r["K"]), float(r["port_h"])) for r in rs if r["port_h"] != "")
                x.plot([p[0] for p in pts], [p[1] for p in pts], st, ms=3, lw=1, label=lab)
                data += [dict(scen=sc, mode=m, series=lab, S=1, n_v=10, K=K, port_h=ph) for K, ph in pts]
            kd = next(float(r["k_dagger"]) for r in get(occ, scen=sc, mode=m, S=1, n_v=10, hold="0") if r["k_dagger"])
            x.axvline(kd, color="grey", lw=0.8, ls=":")
            x.text(kd, x.get_ylim()[1], f" K† = {kd:.2f}", fontsize=6, va="top")
            x.set_title(f"{SCEN_ZH[sc]}, {'roadside cradles' if m == 'on_road' else 'pull-in cradles'}", fontsize=7)
            if a == 1:
                x.set_xlabel("SPMT groups K")
            if b == 0:
                x.set_ylabel("port time to load 10 piles (h)")
    h, l = ax[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=7)
    fig.suptitle("Fig. 3 (draft) fixed-time vs occupancy representation: vessel port time against K (cradles ready 24 h ahead, S = 1)", fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    save(fig, out, "fig3.png")
    wcsv(out / "fig3.csv", data)
    rows = []
    for sc in SC5:
        for m in modes:
            for S in (0, 1, 3):
                po = {i(r["K"]): float(r["port_h"]) for r in get(occ, scen=sc, mode=m, S=S, n_v=10, hold="0") if r["port_h"] != ""}
                wo = {i(r["K"]): i(r["sim"]) for r in get(occ, scen=sc, mode=m, S=S, L=12, hold="0")}
                pinf = {i(r["K"]): float(r["port_h"]) for r in get(occ, scen=sc, mode=m, S=S, n_v=10, hold="inf") if r["port_h"] != ""}
                crane = 10 * (1800 if sc == "fastcrane" else 3600) / 3600
                plat = lambda ph: min(K for K, v in ph.items() if v <= min(ph.values()) * 1.02)
                base = dict(scen=sc, mode=m, S=S, crane_h=crane, occ_min=round(min(po.values()), 2), occ_plat=plat(po), occ_inf_min=round(min(pinf.values()), 2),
                            occ_K2=wo[2], occ_K4=wo[4])
                for kr in (1, 2, 3, 4):
                    pf = {i(r["K"]): float(r["port_h"]) for r in get(fix, scen=sc, mode=m, S=S, n_v=10, kref=kr) if r["port_h"] != ""}
                    wf = {i(r["K"]): i(r["sim"]) for r in get(fix, scen=sc, mode=m, S=S, L=12, kref=kr)}
                    f = float(get(fix, scen=sc, mode=m, S=S, kref=kr)[0]["factor"])
                    rows.append(dict(base, kref=kr, factor=round(f, 3), fix_min=round(min(pf.values()), 2), fix_plat=plat(pf), fix_K2=wf[2], fix_K4=wf[4]))
    wcsv(out / "table3.csv", rows)
    L = ["# Table 3 (draft) fixed-time / occupancy representation (Q_h = 0)\n",
         "In the fixed-time representation both speeds are multiplied by 1/f, where f makes its port time for 10 piles at K = K_ref equal to that of the "
         "occupancy representation. Minimum port time = minimum over K = 1–8; plateau K = smallest K with port time within 1.02 times the minimum; "
         "piles = piles lifted onto the vessel within a 12 h window. Crane lower bound = 10·p.\n",
         "| scenario | cradles | S | crane lower bound h | K_ref | f | min port time h occupancy / fixed | occupancy Q_h unlimited | "
         "plateau K occupancy / fixed | piles K=2 occupancy / fixed | K=4 |",
         "|---|---|---:|---:|---:|---:|---|---:|---|---|---|"]
    for r in rows:
        L.append(f"| {SCEN_ZH[r['scen']]} | {r['mode']} | {r['S']} | {r['crane_h']:.0f} | {r['kref']} | {r['factor']} | {r['occ_min']} / {r['fix_min']} | "
                 f"{r['occ_inf_min']} | {r['occ_plat']} / {r['fix_plat']} | {r['occ_K2']} / {r['fix_K2']} | {r['occ_K4']} / {r['fix_K4']} |")
    (out / "table3.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return rows


# ---------------------------------------------------------------- gate holding places, release time
def table_hold(e1, e1h, out):
    rows = []
    for sc in SC5:
        for m in ("on_road", "pull_in"):
            for h in ("0", "1", "2", "inf"):
                rs = [r for r in (e1 if h == "0" else e1h) if r["kind"] == "A1" and r["scen"] == sc and r["mode"] == m and r["hold"] == h and main_lift(r)]
                n = len(rs)
                rows.append(dict(scen=sc, mode=m, hold=h, n=n, sim=sum(i(r["sim"]) for r in rs), w1=sum(i(r["w1"]) for r in rs),
                                 tight=round(sum(i(r["gap"]) == 0 for r in rs) / n, 4), exit_hold=sum(i(r["exit_hold"]) for r in rs),
                                 exit_yard=sum(i(r["exit_yard"]) for r in rs)))
    wcsv(out / "table_hold.csv", rows)
    L = ["# Gate holding places Q_h (A1, cradle mode and direct lift, L × K × S × G = 576 points per cell)\n",
         "Note: delivery is not necessarily monotone in Q_h (e.g. at 1 km/h with roadside cradles Q_h = 2 delivers more than unlimited; with crane 0.5 h "
         "and roadside cradles the equality share at Q_h = 1, 2 is lower than at 0). This is an artefact of the first-come-first-served rule: "
         "a vehicle waiting at the gate must still cross the single lane against the flow on its next trip, and the rule does not choose the moment; "
         "the convoy dispatch rule (queueing at the bottleneck) is the comparison. \"Unlimited\": waiting at the gate occupies no space.\n",
         "| scenario | cradles | Q_h | total simulated piles | total W1 | equality share | exits to holding place / to yard side (trips) |",
         "|---|---|---|---:|---:|---:|---|"]
    for r in rows:
        L.append(f"| {SCEN_ZH[r['scen']]} | {r['mode']} | {r['hold']} | {r['sim']} | {r['w1']} | {r['tight']:.1%} | {r['exit_hold']} / {r['exit_yard']} |")
    (out / "table_hold.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def table_rel(rel, out):
    rows = []
    for r in sorted(rel, key=lambda r: (r["mode"], i(r["L"]), i(r["G"]), i(r["K"]), i(r["S"]), float(r["frac"]))):
        rows.append(dict(mode=r["mode"], L=i(r["L"]), G=i(r["G"]), K=i(r["K"]), S=i(r["S"]), lift=r["lift"], frac=float(r["frac"]), sim=i(r["sim"]),
                         w1=i(r["w1"]), binding=r["binding"]))
    wcsv(out / "table_rel.csv", rows)
    L = ["# Release time of direct lifts (A1 base, Q_h = 0): the vehicle is released x·p after the lift starts; S = 1 is the cradle-mode reference\n",
         "| cradle placement | L | G | K | direct lift x = 0 | 0.25 | 0.5 | 1 | cradle S = 1 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r["mode"], r["L"], r["G"], r["K"])][("c" if r["S"] else r["frac"])] = r["sim"]
    for (m, Lh, G, K), d in sorted(by.items()):
        L.append(f"| {m} | {Lh} | {G} | {K} | {d[0.0]} | {d[0.25]} | {d[0.5]} | {d[1.0]} | {d['c']} |")
    (out / "table_rel.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- summary
def summary(e1, e1h, e2tot, out):
    L = ["# Summary (generated by windport_report.py)\n"]
    for name, rs in (("E1 (Q_h = 0)", e1), ("E1h (Q_h = 1, 2, unlimited)", e1h)):
        L.append(f"- {name}: {len(rs)} points; independent checker failed at {sum(r['check_ok'] != '1' for r in rs)} points; simulation above W1 at {sum(i(r['gap']) < 0 for r in rs)} points; "
                 f"equality at {sum(i(r['gap']) == 0 for r in rs)} points ({sum(i(r['gap']) == 0 for r in rs) / len(rs):.1%}).")
    j = [r for r in e1 if r["thm3_over"] != ""]
    L.append(f"- Simultaneous unloading and loading (E1 joint, jointshared, {len(j)} points): Theorem 3 exceeded in {sum(i(r['thm3_over']) for r in j)} windows; minimum Theorem 4 slack "
             f"{min((float(r['thm4_gap']) for r in j if r['thm4_gap'] not in ('', 'inf')), default=float('nan')):.0f} s.")
    L.append(f"- E2: {e2tot['n']} instances; proven optimal {e2tot['opt']}, feasible only {e2tot['feas']}; CP-SAT > W1: {e2tot['w1_over']}; proven optimal and = W1: {e2tot['opt_eq_w1']}; "
             f"proven optimal and = simulation: {e2tot['opt_eq_sim']}; CP > simulation: {e2tot['cp_gt_sim_n']} instances ({e2tot['cp_gt_sim']} piles); simulation > CP: {e2tot['sim_gt_cp_n']} instances"
             f" ({e2tot['sim_gt_cp']} piles).\n")
    L += ["## E1 W1 − simulation per group (≥ 3 merged; denominator = points per group)\n",
          "| layout | scenario | cradles | lift | Q_h | points | 0 | 1 | 2 | ≥3 | equality share |",
          "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|"]
    by = collections.defaultdict(collections.Counter)
    for r in e1 + e1h:
        by[(r["kind"], r["scen"], r["mode"], r["lift"], r["hold"])][min(i(r["gap"]), 3)] += 1
    for (k, sc, m, lf, h), c in sorted(by.items()):
        n = sum(c.values())
        L.append(f"| {k} | {SCEN_ZH[sc]} | {m} | {lf} | {h} | {n} | {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[0] / n:.1%} |")
    reg = collections.defaultdict(collections.Counter)
    for r in e1:
        if main_lift(r):
            reg[(r["kind"], r["scen"])][r["regime"]] += 1
            reg[(r["kind"], r["scen"])]["cut"] += "cut" in r["binding"].split("+")
    L += ["\n## Binding regimes in E1 (Q_h = 0, cradle mode and direct lift, both cradle placements; 1,152 points per cell)\n",
          "| layout | scenario | interface-limited | staging-limited | flow-limited | of which cut binding |", "|---|---|---:|---:|---:|---:|"]
    for (k, sc), c in sorted(reg.items()):
        L.append(f"| {k} | {SCEN_ZH[sc]} | {c['interface']} | {c['staging']} | {c['flow']} | {c['cut']} |")
    for k in ("thm", "w1"):
        L += ["", f"## {DIRS[k]}/summary.md\n", "\n\n".join((ROOT / "results" / DIRS[k] / "summary.md").read_text(encoding="utf-8").split("\n\n")[1:2])]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    h = hashlib.sha256(Path(__file__).read_bytes())
    for k in sorted(DIRS):
        h.update((ROOT / "results" / DIRS[k] / FILES[k]).read_bytes())
    out = ROOT / "results" / f"windport_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    e1, e1h, rel, e2, e3, e2l = (load(k) for k in ("e1", "e1h", "rel", "e2", "e3", "e2long"))
    fig2(e1, out)
    fig_regime(e1, out)
    tot = table2(e2, out, e2l)
    e3_tables(e3, out)
    table_hold(e1, e1h, out)
    table_rel(rel, out)
    summary(e1, e1h, tot, out)
    (out / "inputs.json").write_text(json.dumps({k: f"results/{DIRS[k]}/{FILES[k]}" for k in sorted(DIRS)}, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
