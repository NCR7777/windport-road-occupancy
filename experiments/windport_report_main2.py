"""Summary for the main2 geometry (rebuilt side-by-side rows, ramp in line with the apron, bound extension for multi-row dead ends): new values of
every table and number of the manuscript, compared with the main-geometry base case (main). No simulation, only reads run directories (the
core-case macros and a few numbers such as ε_U are computed through the unified entry point, as in the main-geometry summary).

Run directories: the main-geometry batches, with those whose map or network changed replaced by the main2 directories (splice subdirectories, core,
cdv, codesign); the tandem core case, the t_u / x threshold / lifted-load range / shipyard-map batches, E2, the example table and the critical
lengths are taken unchanged from the main geometry (reuse basis: module docstring of windport_main2_runs.py).
1. reports/after/, numbers/after/: the three committed summary scripts and the manuscript make_numbers.py, make_figures.py applied unchanged (as the
   summaries of the main-geometry summary; temporary root R.TMP).
2. macros.csv / macros.md: manuscript macros as current manuscript value → old base case (40 m) → main geometry (main) → **main2**, listing those
   that differ from the main geometry; numbers_fail_new.csv: assertions newly failing under main2 (relative to the main geometry); tables.md,
   figures.md: tables and figures changed relative to the main geometry.
3. core.md: core case (long single lane / long corridor at 1 km/h, 10 piles per vessel): tandem (main), old side-by-side abstraction (main),
   rebuilt side-by-side rows (main2, FCFS and convoy dispatch).
4. geom.md: geometry check, distance of each side-by-side row from the quay line, S_r. 5. e5.md: change of E5 (figure fig_overlap) and of the
   unloading rows from main to main2. 6. reach.md: side-by-side rows of Table 7 and reach by distance.
Output results/windport_main2_report_<first 12 hex digits of the SHA-256 of the inputs and this script>/. Run: python experiments/windport_report_main2.py
"""
import collections
import csv
import hashlib
import itertools
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                        # noqa: E402
import windport_report_conservative as R                                # noqa: E402
import windport_recheck_maingeom as FK                              # noqa: E402
import windport_report_maingeom as FR                               # noqa: E402
import windport_main2_runs as HX                                      # noqa: E402

H = 3600.0
R.TMP = ROOT / "out" / "main2_rep"
F_REP = ROOT / "results" / "tables/maingeom"
i, fl, rd, wcsv, md, pct = FR.i, FR.fl, FR.rd, FR.wcsv, FR.md, FR.pct
SCEN_ZH, ARR_ZH, MODE_ZH = FR.SCEN_ZH, FR.ARR_ZH, FR.MODE_ZH


def h_dirs():
    one = FK.one_dir
    return dict(splice=one("windport_main2_splice_"), core=one("windport_main2_core_"), reachdist=one("windport_main2_reachdist_"), cdv=one("windport_main2_cdv_"),
                codesign=one("windport_main2_codesign_"), sample=one("windport_main2_sample_"), geom=one("windport_main2_geom_"), recheck=one("windport_main2_recheck_"),
                random=sorted(p for p in (ROOT / "results").glob("windport_main2_random_*") if (p / "summary.json").exists()))


def dirs():
    """dirs() of the main-geometry summary, with the changed batches replaced by the main2 directories."""
    D = FR.dirs()
    Hd = h_dirs()
    run = dict(D["run"])
    for b in HX.RERUN + [f"unified:{p}" for p in HX.SPATIAL]:
        run[b] = Hd["splice"] / b.replace(":", "_")
    run["unified:cdv"] = Hd["cdv"]
    return dict(D, run=run, codesign=Hd["codesign"], f=D, h=Hd)


def batch_dirs(D):
    """As windport_report_maingeom.batch_dirs, with directory names written as paths relative to results/ (subdirectories of splice)."""
    import windport_rerun_conservative as RR
    import windport_maingeom as F
    rel = lambda p: p.relative_to(ROOT / "results").as_posix()
    out = {b: rel(D["run"][b]) for b in F.rerun_batches()}
    out["runs:e6"] = F.conservative_dir("runs:e6").name
    out["e1e3:e2"] = rel(D["run"]["e1e3:e2"])
    out["e1e3:e2long"] = out["e1e3:e2"] + "/e2long"
    assert set(RR.SRC) <= set(out)
    return out


def recheck_rows(D):
    """Recheck rows of main2: the main-geometry recheck rows, with recomputed ones replaced by the main2 recheck rows; the old side-by-side
    core-case rows of the main geometry and the cdv rows not in the new recheck set are dropped; core (rebuilt rows) and reachdist are added."""
    f = rd(D["f"]["recheck"] / "rows.csv")
    h = rd(D["h"]["recheck"] / "rows.csv")
    hk = {(r["batch"], r["key"]) for r in h}
    cdv = {r["key"] for r in rd(D["h"]["cdv"] / "points.csv")}
    keep = []
    for r in f:
        if (r["batch"], r["key"]) in hk:
            continue
        if r["batch"] == "maingeom:core" and "lay=side" in r["key"]:
            continue
        if r["batch"] == "unified:cdv" and r["key"] not in cdv:
            continue
        keep.append(r)
    return keep + h


# ---------------------------------------------------------------- core case
def core(D, out, N):
    """Tandem cells from the main-geometry core (170 m); side-by-side: the old abstraction of the main geometry and the rebuilt rows of main2
    (FCFS; Q_h = 0 also with convoy dispatch)."""
    fr = [r for r in rd(D["f"]["run"]["maingeom:core"] / "points.csv") if float(r["first"]) == 170.0 and float(r["extra"]) == 0.0 and r["port_h"] not in ("", None)]
    hr = [r for r in rd(D["h"]["core"] / "points.csv") if r["port_h"] not in ("", None)]
    g = collections.defaultdict(list)
    for r in fr:
        g[(r["scen"], "f:" + r["lay"], r["arr"], r["hold"])].append(r)
    for r in hr:
        g[(r["scen"], "h:" + r["rule"], r["arr"], r["hold"])].append(r)

    def best(rs):
        if not rs:
            return None
        p_, l_, k_ = min((fl(r["port_h"]), fl(r["lstar_lo"]), i(r["K"])) for r in rs)
        return dict(f=p_, l=l_, k=k_, m=min(fl(r["lstar_lo"]) for r in rs))
    tab = {}
    for sc, lay, arr, h in itertools.product(("lane", "longslow"), ("f:on_road", "f:pull_in", "f:side", "h:fcfs", "h:convoy"), ("S0", "S1", "S1m", "S3", "S3m"),
                                              ("0", "1", "inf")):
        b = best(g[(sc, lay, arr, h)])
        if b:
            tab[f"{sc}|{lay}|{arr}|{h}"] = b
    f2 = lambda v: "-" if v is None else f"{v:.2f}"
    cell = lambda k: (lambda b: "-" if b is None else f"{f2(b['f'])} (K = {b['k']}: {f2(b['l'])}; min over K {f2(b['m'])})")(tab.get(k))
    L = ["# Core case: port time for 10 piles per vessel (shortest over K = 1–8; in brackets the K that gives the shortest, L″_lift* at that K, "
         "and the minimum of L″_lift* over K)\n",
         "Tandem from the main geometry (170 m; under main2 the loading network is unchanged and is reused byte for byte). Side-by-side: the main geometry "
         "uses the abstraction \"one 40 m pull-in short road per cradle\"; main2 uses the rebuilt rows (parallel to the quay line, "
         "row pitch 15.36 m, piles at 60–170 m, S cradles use the S rows nearest to the quay line), FCFS; for Q_h = 0 convoy dispatch is also listed "
         "(the conservative-lifting version of windport.sim2.ConvoySim).\n"]
    for sc in ("lane", "longslow"):
        L += [f"## {SCEN_ZH[sc]}\n", "| Lifting | Q_h | Tandem on-road | Tandem pull-in | Side-by-side (main abstraction) | **Side-by-side (main2 rebuilt)** | "
              "Side-by-side rebuilt + convoy dispatch |", "|---|---|---|---|---|---|---|"]
        for arr, h in itertools.product(("S0", "S1", "S1m", "S3", "S3m"), ("0", "1", "inf")):
            L.append(f"| {ARR_ZH[arr]} | {dict(inf='unlimited').get(h, h)} | {cell(f'{sc}|f:on_road|{arr}|{h}')} | {cell(f'{sc}|f:pull_in|{arr}|{h}')} | {cell(f'{sc}|f:side|{arr}|{h}')} | "
                     f"**{cell(f'{sc}|h:fcfs|{arr}|{h}')}** | {cell(f'{sc}|h:convoy|{arr}|{h}') if h == '0' else ''} |")
        L.append("")
    md(out, "core.md", L)
    wcsv(out / "core_main2.csv", [dict(key=k, **v) for k, v in tab.items()])
    N["core_h"] = tab


def core_n(D, N):
    """N["core"] as used by macros() of the main-geometry summary: tandem cells as in the main geometry; side-by-side replaced by the rebuilt rows
    (only 170 m, FCFS with Q_h = 0 / 1 / unlimited)."""
    tmp = R.TMP / "core_f"
    tmp.mkdir(parents=True, exist_ok=True)
    Nf = {}
    FR.core(D["f"], tmp, Nf)
    c = Nf["core"]
    for sc, arr in itertools.product(("lane", "longslow"), ("S0", "S1", "S1m", "S3", "S3m")):
        t = c[f"{sc}|side|{arr}"]
        for tag in [f"{f}_h{h}" for f in (40, 150) for h in ("0", "1", "inf")] + ["170_x600", "170_x1800"]:   # not defined for the rebuilt rows (first cradle position is not a parameter; entry turns are feasible)
            t[f"f{tag}"] = t[f"l{tag}"] = t[f"k{tag}"] = t[f"m{tag}"] = None
        t["nonmono"] = ""
        for h in ("0", "1", "inf"):
            b = N["core_h"].get(f"{sc}|h:fcfs|{arr}|{h}")
            t[f"f170_h{h}"], t[f"l170_h{h}"], t[f"k170_h{h}"], t[f"m170_h{h}"] = (b["f"], b["l"], b["k"], b["m"]) if b else (None,) * 4
    N["core"] = c
    shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- geometry, reach, E5
def geom(D, out, N):
    g = D["h"]["geom"]
    s = rd(g / "summary.csv")
    L = ["# Geometry check (main2, windport/geomcheck.py): minimum clearance (m) of the swept circles of all turns on each route (loaded radius L_v/2, "
         "empty 15 m) to the berth water, the piles on the cradles and the side constraints of the single lane\n",
         "Tandem: A1, A2, A3 × base / long single lane × cradle mode × S = 1, 3; loading (including the gate turn), return, unloading (ramp in line with the "
         "apron, no turn at the ramp foot; open turning area of 60 m where the A2 loop joins the south end of the single lane). "
         "Side-by-side: rebuilt rows × S = 6 (all rows) × Q_h = 0, 1; entry turns (turning into a row at a branch node) are counted. E7: four monopile "
         "levels (tandem dimensions do not follow L_v; row dimensions follow L_v, B).\n",
         "| Layout | Port type | Scenario | Cradle | Lifting | Q_h | Monopile level | Loading and return pass | Unloading passes | Piles on land | "
         "Loading / return min. clearance: water / piles / lane sides | Unloading min. clearance |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in s:
        L.append(f"| {r['layout']} | {r['kind']} | {SCEN_ZH.get(r['scen'], r['scen'])} | {MODE_ZH.get(r['mode'], r['mode'])} | {r['arr']} | {r['hold']} | {r['lv']} | "
                 f"{'yes' if r['ok'] == '1' else '**no**'} | {dict(zip(('1', '0', ''), ('yes', '**no**', '-'))).get(r.get('ok_unload', ''), r.get('ok_unload'))} | "
                 f"{'yes' if r['piles_on_land'] == '1' else 'no'} | {r['min_water']} / {r['min_piles']} / {r['min_flanks']} | "
                 f"{r.get('unl_water') or '-'} / {r.get('unl_piles') or '-'} / {r.get('unl_flanks') or '-'} |")
    tr = rd(g / "turns.csv")
    agg = collections.defaultdict(list)
    for r in tr:
        if r["lv"] in ("110",) and r["layout"] in ("tandem", "rows"):
            agg[(r["layout"], r["kind"], r["route"])].append(r)
    mn = lambda rs, k: min((fl(r[k]) for r in rs if r.get(k) not in ("", None)), default=None)
    L += ["\n## By route (monopile 110 m; tandem S = 1, 3 with both cradle modes combined, side-by-side S = 6)\n",
          "| Layout | Port type | Route | Turns | Passed | Min. clearance: water / piles / lane sides |", "|---|---|---|---:|---:|---|"]
    order = ("load-out", "bay entry", "return", "unloading", "ramp foot")
    for k in sorted(agg, key=lambda k: (k[0], k[1], order.index(k[2]) if k[2] in order else 9)):
        rs = agg[k]
        L.append(f"| {k[0]} | {k[1]} | {k[2]} | {len(rs)} | {sum(i(r['ok']) for r in rs)} / {len(rs)} | {mn(rs, 'water')} / {mn(rs, 'piles')} / {mn(rs, 'flanks')} |")
    rr = rd(g / "rows_reach.csv")
    L += ["\n## Rebuilt side-by-side rows: distance of each row's pile centre line from the quay line (m) and crane reach by distance\n",
          "S_r(R_q) = number of rows within R_q of the quay line; R_q is the effective working reach of the ship crane beyond the quay line at monopile "
          "weight (crane working radius minus the distance from the slewing centre to the quay line).\n",
          "| Monopile level | L_v / B (m) | Row pitch | Pile x range | North distance of quay line from gate | Pile centre line from quay line, "
          "cradle positions 0–5 |", "|---|---|---:|---|---:|---|"]
    by = collections.defaultdict(list)
    for r in rr:
        by[r["lv"]].append(r)
    for lv, rs in by.items():
        r0 = rs[0]
        L.append(f"| {lv} | {fl(r0['Lv']):.1f} / {fl(r0['B']):.1f} | {r0['pitch_m']} | {fl(r0['x0_m']):.1f}–{fl(r0['head_m']):.1f} | {r0['quay_edge_m']} | "
                 + " / ".join(r["dist_m"] for r in sorted(rs, key=lambda x: i(x["k"]))) + " |")
    md(out, "geom.md", L)
    N["geom"] = dict(summary=s, reach=rr)


def e5(D, out, N):
    """Unloading-related rows: E5, simultaneous unloading and loading of pocket, e5 of Appendix C, sens5, pub (unloading) and joint of E1, main →
    main2 row by row: number of changed rows and change of the readings."""
    FD = D["f"]["run"]
    L = ["# Unloading-related rows: main geometry main → main2 (ramp in line with the apron, no turn at the ramp foot)\n",
         "| Batch | Recomputed rows | Byte-identical | Changed | Rows with changed count columns (sim / n_ramp) | Checker failures |",
         "|---|---:|---:|---:|---:|---:|"]
    rows = {}
    for b in HX.RERUN:
        d = D["h"]["splice"] / b.replace(":", "_")
        s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        diff = {r["key"]: r for r in rd(d / "diff.csv")}
        old = {r["key"]: r for r in rd(FD[b] / "points.csv")}
        new = {r["key"]: r for r in rd(d / "points.csv")}
        cnt = sum(1 for k in diff if any(old[k].get(c) != new[k].get(c) for c in ("sim", "n_ramp") if c in old[k]))
        L.append(f"| {b} | {s['recomputed']:,} | {s['same']:,} | {s['recomputed'] - s['same']:,} | {cnt:,} | {s['check_fail']} |")
        rows[b] = dict(s, count_changed=cnt)
    N["unload"] = rows
    # figure fig_overlap: E5 readings (E5 table of the E4-E7 summary script, main → main2)
    fa = sorted((F_REP / "reports" / "after").glob("windport_runs_report_*"))[0]
    ha = sorted((out / "reports" / "after").glob("windport_runs_report_*"))[0]
    L += ["\n## E5 table of the E4-E7 summary script (figure fig_overlap, Section 5): files changed from main to main2\n"]
    for p in sorted(fa.rglob("*")):
        if p.is_file() and ("e5" in p.name.lower() or "overlap" in p.name.lower()):
            q = ha / p.relative_to(fa)
            L.append(f"- `{p.relative_to(fa).as_posix()}`: {'same' if q.exists() and q.read_bytes() == p.read_bytes() else '**changed**'}")
    md(out, "e5.md", L)


def splice_md(D, out, N):
    """Spliced recomputation: rows recomputed per batch, byte-identical to / changed from the main geometry, checker failures (summary.json of
    splice)."""
    s = json.loads((D["h"]["splice"] / "summary.json").read_text(encoding="utf-8"))
    L = ["# Rows recomputed under main2 (splice): byte-identical to / changed from the main geometry\n",
         "| Batch | Rows | Recomputed | Same | Changed | Checker failures |", "|---|---:|---:|---:|---:|---:|"]
    L += [f"| {b} | {x['rows']:,} | {x['recomputed']:,} | {x['same']:,} | {x['recomputed'] - x['same']:,} | {x['check_fail']} |" for b, x in s.items()]
    tot = lambda k: sum(x[k] for x in s.values())
    L.append(f"| Total | | {tot('recomputed'):,} | {tot('same'):,} | {tot('recomputed') - tot('same'):,} | {tot('check_fail')} |")
    md(out, "splice.md", L)
    N["splice"] = s


def random_tree(D, out, N):
    """Cases of the rebuilt rows with the tree flag in the random regression, counted separately by gate holding place and (S, K) (cases.csv):
    with Q_h ≠ 0 quay_side_Q returns INF and tree has no effect; with S ≤ 1 or K = 1, min(K, Q_s) = 1 and the extension does not change b_max.
    This regression records only the flag, not per pile whether tree tightens the bound."""
    rows = []
    for d in D["h"]["random"]:
        rs = [r for r in rd(d / "cases.csv") if r["kind"] == "A1rows"]
        g = json.loads((d / "summary.json").read_text(encoding="utf-8"))["gen"]
        piles = lambda x: sum(i(r["n"]) + i(r["n_lift"]) for r in x)
        t = [r for r in rs if r.get("tree") == "1"]
        h0 = [r for r in t if r["hold"] == "0"]
        eff = [r for r in h0 if i(r["S"]) >= 2 and i(r["K"]) >= 2]
        rows.append(dict(gen=g, rows=len(rs), tree=len(t), tree_piles=piles(t), tree_hold=len(t) - len(h0), tree_h0=len(h0), tree_h0_piles=piles(h0),
                         eff=len(eff), eff_piles=piles(eff), eff_viol=sum(i(r["viol"]) + i(r["viol_lift"]) for r in eff)))
    tot = {k: sum(r[k] for r in rows) for k in rows[0] if k != "gen"}
    L = ["# Random regression: cases with the tree flag in the rebuilt rows (split by whether it takes effect)\n",
         "tree = some chain satisfies the premise via \"the quay side is a tree\"; with Q_h ≠ 0 Corollary 7′ is not used (quay_side_Q returns INF); "
         "with S ≤ 1 or K = 1, min(K, Q_s) = 1 and the extension does not change b_max.\n",
         "| Generator | Rebuilt rows (cases) | With tree: cases / piles | of which Q_h ≠ 0 | Q_h = 0: cases / piles | "
         "Q_h = 0, S ≥ 2, K ≥ 2: cases / piles / violations |", "|---|---:|---|---:|---|---|"]
    for r in rows + [dict(tot, gen="total")]:
        L.append(f"| {r['gen']} | {r['rows']:,} | {r['tree']:,} / {r['tree_piles']:,} | {r['tree_hold']:,} | {r['tree_h0']:,} / {r['tree_h0_piles']:,} | "
                 f"{r['eff']:,} / {r['eff_piles']:,} / {r['eff_viol']} |")
    md(out, "random_tree.md", L)
    N["random_tree"] = tot


def reach(D, out, N):
    """Side-by-side rows of Table 7 (side-by-side keys of the reach batch): main abstraction → main2 rebuilt rows; reach by distance (S_r = 1, 2,
    t_sh = 1 h)."""
    f = {r["key"]: r for r in rd(D["f"]["run"]["unified:reach"] / "points.csv") if "lay=side" in r["key"]}
    h = {r["key"]: r for r in rd(D["run"]["unified:reach"] / "points.csv") if "lay=side" in r["key"]}
    rdist = rd(D["h"]["reachdist"] / "points.csv")
    L = ["# Side-by-side rows of Table 7: piles lifted on board in a 12 h window (simulation / W″_lift), main abstraction → main2 rebuilt rows; "
         "crane reach by distance\n"]
    for sc, lf in itertools.product(("base", "lane"), ("cradle", "mixed")):
        L += [f"## {SCEN_ZH[sc]}, {dict(cradle='cradle', mixed='mixed lifting')[lf]} (S = 0 is direct lift)\n", "| K | " + " | ".join(f"S = {s}" for s in range(0, 7)) + " |",
              "|---|" + "---|" * 7]
        for K in range(1, 11):
            cells = []
            for Sn in range(0, 7):
                d = dict(lay="side", kind="A1side", scen=sc, mode="side", lift="direct" if Sn == 0 else lf, rule="fcfs", reach="all", L=12, K=K, S=Sn, G=24)
                k = T.enc(d)
                a, b = f.get(k), h.get(k)
                dd = [r for r in rdist if r["key"].startswith(f"lay=side|kind=A1side|scen={sc}|mode=side|lift={lf}|rule=fcfs|reach=") and f"|K={K}|S={Sn}|" in r["key"]]
                ex = "; ".join(f"S_r={r['key'].split('reach=')[1][0]}: {r['sim']}/{r['w4']}" for r in sorted(dd, key=lambda r: r["key"]))
                cells.append("-" if not b else f"{a['sim']}/{a['w4']} → **{b['sim']}/{b['w4']}**" + (f" ({ex})" if ex else ""))
            L.append(f"| {K} | " + " | ".join(cells) + " |")
        L.append("")
    md(out, "reach.md", L)


def macros_cmp(out, N):
    """Macros computed by the summary (the add() items of macros() of the main-geometry summary, on the main2 directories) compared with the
    main-geometry macros.csv, plus the new main2 macros. For the manuscript make_numbers macros see paper_macros.csv (the same script version on both
    directory sets; the make_numbers column of the main-geometry macros.csv came from an older script version and is not comparable)."""
    own = lambda r: not r["source"].startswith("make_numbers.py")
    new = {r["macro"]: r for r in rd(out / "macros.csv") if own(r)}
    old = {r["macro"]: r for r in rd(F_REP / "macros.csv") if own(r)}
    c, f2 = N["core_h"], (lambda v: f"{v:.2f}")
    rr = [r for r in N["geom"]["reach"] if r["lv"] == "base"]
    extra = dict(
        QuayEdgeSideM=(f"{fl(rr[0]['quay_edge_m']):.2f}", "side-by-side (rebuilt rows): north distance of the quay line from the gate (m) = centre line of the row nearest to the quay line + 8.25 m; used only in the geometry check and figures"),
        RowPitchM=(rr[0]["pitch_m"], "rebuilt side-by-side rows: row pitch B + w_e + c (m)"),
        RowStartM=(f"{fl(rr[0]['x0_m']):.0f}", "rebuilt side-by-side rows: west end of the piles from the branch road (m) = L_v/2 + δ"),
        RowHeadM=(f"{fl(rr[0]['head_m']):.0f}", "rebuilt side-by-side rows: vehicle front from the branch road when the delivering vehicle stops (m) = x0 + L_v"),
        RowDistNear=(rr[0]["dist_m"], "rebuilt side-by-side rows: pile centre line of cradle position 0 from the quay line (m)"),
        RowDistTwo=(rr[1]["dist_m"], "rebuilt side-by-side rows: pile centre line of cradle position 1 from the quay line (m)"),
        RowDistThree=(rr[2]["dist_m"], "rebuilt side-by-side rows: pile centre line of cradle position 2 from the quay line (m)"),
        RowDistFar=(rr[-1]["dist_m"], "rebuilt side-by-side rows: pile centre line of cradle position 5 from the quay line (m)"),
        CoreSideDirect=(f2(c["lane|h:fcfs|S0|0"]["f"]), "core case: rebuilt side-by-side rows, direct lift S = 0 (= L″_lift*)"),
        CoreSideMixed=(f2(c["lane|h:fcfs|S1m|0"]["f"]), "core case: rebuilt side-by-side rows, mixed lifting S = 1"),
        CoreSideThree=(f2(c["lane|h:fcfs|S3|0"]["f"]), "core case: rebuilt side-by-side rows, cradle S = 3 (FCFS)"),
        CoreSideThreeConvoy=(f2(c["lane|h:convoy|S3|0"]["f"]), "core case: rebuilt side-by-side rows, cradle S = 3, convoy dispatch"),
        CoreSideThreeMixedConvoy=(f2(c["lane|h:convoy|S3m|0"]["f"]), "core case: rebuilt side-by-side rows, mixed lifting S = 3, convoy dispatch"),
        CoreSideHoldOne=(f2(c["lane|h:fcfs|S1|1"]["f"]), "core case: rebuilt side-by-side rows, cradle S = 1, one gate holding place"),
        CoreSideHoldInf=(f2(c["lane|h:fcfs|S1|inf"]["f"]), "core case: rebuilt side-by-side rows, cradle S = 1, unlimited gate holding places"))
    for k, (v, src) in extra.items():
        new[k] = dict(new.get(k, dict(macro=k, manuscript="", legacy="")), main=v, source="main2: " + src)
    rows = []
    for k in sorted(set(new) | set(old)):
        a, b = old.get(k, {}), new.get(k, {})
        rows.append(dict(macro=k, manuscript=b.get("manuscript", a.get("manuscript", "")), legacy=b.get("legacy", a.get("legacy", "")), main=a.get("main", ""),
                         main2=b.get("main", ""), changed=int(a.get("main", "") != b.get("main", "")), source=b.get("source", a.get("source", ""))))
    wcsv(out / "macros_main2.csv", rows)
    ch = [r for r in rows if r["changed"]]
    L = ["# Macro table: main geometry (main) → **main2**\n", f"Total {len(rows)} macros; {len(ch)} differ from the main geometry (table below).\n",
         "| Macro | Manuscript value | main | **main2** | Source |", "|---|---|---|---|---|"]
    L += [f"| \\{r['macro']} | {r['manuscript']} | {r['main']} | **{r['main2']}** | {r['source']} |" for r in ch]
    md(out, "macros_main2.md", L)
    N["macros_main2"] = dict(total=len(rows), changed=len(ch))


def fake_src(mapping):
    """Manuscript scripts/src.py: readings first go through its own where (old directory → main-geometry directory), then the main-geometry
    directories in mapping are replaced by the main2 directories of this work tree; everything else via git show."""
    import subprocess
    import types
    m = types.ModuleType("src")
    code = (R.PAPER / "scripts" / "src.py").read_text(encoding="utf-8")
    exec(compile(code, str(R.PAPER / "scripts" / "src.py"), "exec"), m.__dict__)
    keys = sorted(mapping, key=len, reverse=True)

    def local(path):
        for a in keys:
            if path == a or path.startswith(a + "/"):
                return ROOT / (mapping[a] + path[len(a):])
        return None

    def show(path, commit):
        p, c = m.where(path, commit)
        q = local(p)
        if q is not None:
            return q.read_bytes().decode("utf-8-sig")
        return subprocess.run(["git", "-C", str(m.REPO), "show", f"{c}:{p}"], capture_output=True, check=True).stdout.decode("utf-8-sig")

    def tracked(path, commit):
        real, c = m.where(path, commit)
        q = local(real)
        if q is not None:
            fs = sorted(q.rglob("*")) if q.is_dir() else [q]
            return [path + "/" + f.relative_to(q).as_posix() for f in fs if f.is_file()] if q.is_dir() else [path]
        out = subprocess.run(["git", "-C", str(m.REPO), "ls-tree", "-r", "--name-only", c, real], capture_output=True, check=True).stdout.decode("utf-8").split()
        return [path + f[len(real):] for f in out]
    m.show, m.tracked = show, tracked
    m.rows = lambda path, commit: list(csv.DictReader(__import__("io").StringIO(show(path, commit))))
    m.js = lambda path, commit: json.loads(show(path, commit))
    return m


def numbers(tag, mapping, out):
    """Run the manuscript make_numbers.py unchanged (failed assertions and failing top-level statements are recorded without stopping; as the
    after pass of windport_report_conservative.numbers, the source is not modified)."""
    import ast
    d = out / "numbers" / tag
    shutil.rmtree(d, ignore_errors=True)
    (d / "scripts").mkdir(parents=True)
    src = (R.PAPER / "scripts" / "make_numbers.py").read_text(encoding="utf-8")
    tree = R.Soft().top(ast.parse(src))
    saved = sys.modules.get("src")
    sys.modules["src"] = fake_src(mapping)
    g = dict(__name__="__main__", __file__=str(d / "scripts" / "make_numbers.py"), _AF=[], _EF=[])
    try:
        exec(compile(tree, str(R.PAPER / "scripts" / "make_numbers.py"), "exec"), g)
    finally:
        if saved is None:
            sys.modules.pop("src", None)
        else:
            sys.modules["src"] = saved
    shutil.rmtree(d / "scripts")
    lines = src.splitlines()
    fails = [dict(kind="assert", line=n, src=lines[n - 1].strip()) for n in g["_AF"]] + \
        [dict(kind="error", line=n, src=lines[n - 1].strip() + "  ⇒ " + e) for n, e in g["_EF"]]
    wcsv(out / f"numbers_fail_{tag}.csv", fails or [dict(kind="", line="", src="")])
    return dict(g["M"]), fails


def figures(tag, mapping, out):
    """Run the manuscript make_figures.py unchanged (windport_report_maingeom.figures with readings via fake_src); figures are moved to
    numbers/<tag>/figures/."""
    old = R.fake_src
    R.fake_src = fake_src
    a = out / "numbers" / "after"
    if tag != "after":                   # make_figures reads numbers.tex (named_lanes) from the parent of its directory: put this pass's copy there
        a.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / "numbers" / tag / "numbers.tex", a / "numbers.tex")
    try:
        FR.figures(mapping, out)
    finally:
        R.fake_src = old
    b = out / "numbers" / tag / "figures"
    if tag != "after":
        shutil.rmtree(b, ignore_errors=True)
        shutil.move(str(a / "figures"), str(b))
        shutil.rmtree(a, ignore_errors=True)
    (out / "figures_fail.csv").replace(out / f"figures_fail_{tag}.csv")


def geom_compat(D, out):
    """The manuscript reads the main-geometry check directory (summary.csv, turns.csv, main-geometry format): rows with first cradle 170 m (three
    port types, four E7 levels, longpile) are recomputed under main2 (grid and format as windport_maingeom.run_geom; the unloading rows change since
    there is no turn at the ramp foot; the 60 m open area at the A2 loop junction increases the clearance of the empty A2 return); 40 / 150 m rows
    are taken from the main geometry."""
    import windport_extra as X
    from windport import archetypes as A
    from windport import geomcheck as GC
    g = out / "geom_compat"
    g.mkdir(exist_ok=True)
    old_s, old_t = rd(D["f"]["geom"] / "summary.csv"), rd(D["f"]["geom"] / "turns.csv")
    sums, rows = [r for r in old_s if float(r["first"]) != 170.0], [r for r in old_t if float(r["first"]) != 170.0]
    for kind, sc, m, arr in itertools.product(A.KINDS, ("base", "lane"), T.MODES, ("S1", "S3")):
        c = X.port_cfg(sc, m, arr, 2, 10, 0)
        c["geo"] = dict(c["geo"], kind=kind)
        r = GC.check(c)
        tag = dict(first=170.0, kind=kind, scen=sc, mode=m, arr=arr)
        rows += [dict(tag, **x) for x in r["rows"]]
        sums.append(dict(tag, ok=r["ok"], piles_on_land=r["piles_on_land"], **{f"min_{k}": v for k, v in r["min_clear"].items()}))
    for lv in ("85", "100", "110", "120"):
        c = X.port_cfg("base", "on_road", "S1", 2, 10, 0)
        c["p"] = dict(c["p"], **{k: v for k, v in T.E7LEV[lv].items() if k != "t"})
        r = GC.check(c)
        sums.append(dict(first=170.0, kind="A1", scen=f"E7 Lv={lv}", mode="on_road", arr="S1", ok=r["ok"], piles_on_land=r["piles_on_land"],
                         **{f"min_{k}": v for k, v in r["min_clear"].items()}))
    c = X.port_cfg("longpile", "on_road", "S1", 2, 10, 0)
    r = GC.check(c)
    sums.append(dict(first=170.0, kind="A1", scen="longpile Lv=123.6", mode="on_road", arr="S1", ok=r["ok"], piles_on_land=r["piles_on_land"],
                     **{f"min_{k}": v for k, v in r["min_clear"].items()}))
    order = lambda r: (float(r["first"]),)
    HX.wcsv(g / "summary.csv", sorted(sums, key=order), list(old_s[0].keys()))
    HX.wcsv(g / "turns.csv", sorted(rows, key=order), list(old_t[0].keys()))


def recheck_compat(rec, out):
    d = out / "recheck"
    d.mkdir(exist_ok=True)
    HX.wcsv(d / "rows.csv", rec, FK.COLS)


def paper_mapping(D, out, ra):
    """Main-geometry directories read by the manuscript (paths after where of src.py) → main2 directories (relative to ROOT)."""
    f, hd = D["f"], D["h"]
    rel = lambda p: p.relative_to(ROOT).as_posix()
    mp = {}
    for b in HX.RERUN + [f"unified:{p}" for p in HX.SPATIAL]:
        mp[rel(f["run"][b])] = rel(D["run"][b])
    mp[rel(f["run"]["unified:cdv"])] = rel(hd["cdv"])
    mp[rel(f["codesign"])] = rel(hd["codesign"])
    mp[rel(f["recheck"])] = rel(out / "recheck")
    mp[rel(f["geom"])] = rel(out / "geom_compat")
    fr = {json.loads((p / "summary.json").read_text(encoding="utf-8"))["gen"]: p for p in f["random"]}
    hr = {json.loads((p / "summary.json").read_text(encoding="utf-8"))["gen"]: p for p in hd["random"]}
    for gname, p in fr.items():
        if gname in hr:
            mp[rel(p)] = rel(hr[gname])
    mp[rel(F_REP)] = rel(out)
    for p in (F_REP / "reports" / "after").iterdir():
        new = next(q for q in ra.values() if q.name.split("_")[:-1] == p.name.split("_")[:-1])
        mp[rel(p)] = rel(new)
    return mp


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    HX.install()
    D = dirs()
    FR.batch_dirs = batch_dirs
    Hd = D["h"]
    inputs = [Hd["recheck"] / "rows.csv", Hd["codesign"] / "codesign.csv", Hd["geom"] / "summary.csv", Hd["core"] / "points.csv", Hd["reachdist"] / "points.csv"] + \
        [d / "summary.json" for d in Hd["random"]] + [d / "points.csv" for d in D["run"].values()]
    h = hashlib.sha256(Path(__file__).read_bytes())
    for f in inputs:
        h.update(f.read_bytes())
    out = ROOT / "results" / f"windport_main2_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    rec = recheck_rows(D)
    N = {}
    # 1. the three committed summary scripts on the main2 directories (reports/after/)
    Db = batch_dirs(D)
    R.SWAP[R.RC].update(example="extra:example", critical="extra:critical")
    Db.update({"extra:example": D["example"].name, "extra:critical": D["critical"].name})
    ra = R.run_reports("after", Db, out)
    # 2. files with the names of the main-geometry summary (read by the manuscript): core.csv, yards.csv, regime.csv, fig_regime_main.csv, spatial/,
    #    macros.csv (the first pass contains only the summary macros)
    core(D, out, N)
    core_n(D, N)
    wcsv(out / "core.csv", list(N["core"].values()))
    FR.sens(D, out, N)
    FR.yards(D, out, N)
    from windport import archetypes as A
    A.use("main2")
    FR.regime(rec, out, N)
    FR.spatial(D, ra, rec, out, N)
    geom(D, out, N)
    geom_compat(D, out)
    recheck_compat(rec, out)
    Dm = dict(D, random=Hd["random"])
    FR.macros(Dm, {}, [], rec, out, N)
    # 3. manuscript make_numbers / make_figures: once unchanged (main-geometry baseline) and once reading the main2 directories
    mp = paper_mapping(D, out, ra)
    (out / "paper_mapping.json").write_text(json.dumps(mp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    M0, f0 = numbers("main", {}, out)
    figures("main", {}, out)
    M1, f1 = numbers("after", mp, out)
    figures("after", mp, out)
    FR.macros(Dm, M1, f1, rec, out, N)               # full macro table (the main column holds the main2 values); the few read by the manuscript FMAC equal the first pass
    rows = []
    for k in sorted(set(M0) | set(M1)):
        rows.append(dict(macro=k, main=M0.get(k, ""), main2=M1.get(k, ""), changed=int(M0.get(k, "") != M1.get(k, ""))))
    wcsv(out / "paper_macros.csv", rows)
    ch = [r for r in rows if r["changed"]]
    key = lambda r: (r["kind"], r["src"].split("  ⇒")[0])
    k0 = {key(r) for r in f0}
    newf = [r for r in f1 if key(r) not in k0]
    wcsv(out / "numbers_fail_new_main2.csv", newf or [dict(kind="", line="", src="")])
    md(out, "paper_macros.md", ["# Manuscript macros (current scripts/make_numbers.py): main-geometry directories (main) → main2 directories\n",
                                f"Total {len(rows)} macros; {len(ch)} changed; failed make_numbers assertions / failing statements: main {len(f0)}, main2 {len(f1)}, "
                                f"new in main2 {len(newf)} (numbers_fail_new_main2.csv).\n", "| Macro | main | **main2** |", "|---|---|---|"] +
       [f"| \\{r['macro']} | {r['main']} | **{r['main2']}** |" for r in ch])
    N["paper"] = dict(macros=len(rows), changed=len(ch), fails_main=len(f0), fails_main2=len(f1), fails_new=len(newf))
    tb = R.same_files(out / "numbers" / "main" / "tables", out / "numbers" / "after" / "tables")
    fg = R.same_files(out / "numbers" / "main" / "figures", out / "numbers" / "after" / "figures")
    md(out, "paper_tables.md", ["# Manuscript tables and data figures: main-geometry directories (main) → main2 directories\n", "| File | Same |", "|---|---|"] +
       [f"| tables/{k} | {'yes' if v else '**no**'} |" for k, v in tb.items()] + [f"| figures/{k} | {'yes' if v else '**no**'} |" for k, v in fg.items()])
    N["paper"].update(tables_changed=sorted(k for k, v in tb.items() if not v), figures_changed=sorted(k for k, v in fg.items() if not v))
    ta = R.same_files(F_REP / "spatial", out / "spatial")
    N["spatial_changed"] = sorted(k for k, v in ta.items() if not v)
    e5(D, out, N)
    reach(D, out, N)
    splice_md(D, out, N)
    random_tree(D, out, N)
    macros_cmp(out, N)
    N["random"] = {d.name: json.loads((d / "summary.json").read_text(encoding="utf-8")) for d in Hd["random"]}
    N["recheck_rows"] = len(rec)
    (out / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out / "inputs.json").write_text(json.dumps([str(f.relative_to(ROOT)).replace("\\", "/") for f in inputs], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)
    print("spatial-additions tables with errors:", N["spatial_errors"], "; manuscript:", json.dumps(N["paper"], ensure_ascii=False)[:800], N["macros_main2"],
          "spatial-additions tables changed:", N["spatial_changed"])


if __name__ == "__main__":
    main()
