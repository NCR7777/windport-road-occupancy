"""Summary for the main geometry (first cradle 170 m, quay line 20 m from the apron road, gate turning area radius
60 m): new values of every manuscript table and number, compared with the 40 m old geometry (main measure of the
conservative lifting rule / unified bound). No simulation (L″_lift* of the Okpo and Yantai feasible-turn group is
computed here through the unified entry point); only reads the run directories.

1. reports/after/, numbers/after/: the three committed summary scripts (windport_report.py, windport_report2.py,
   windport_report3.py) and the manuscript's make_numbers.py applied unchanged to the run directories of the main
   geometry (run_reports, numbers, literals of experiments/windport_report_conservative; temporary root R.TMP). E6 (shipyard
   maps) uses the directory of the conservative lifting rule.
2. macros.csv / macros.md: every manuscript macro as manuscript value → old main measure (after the
   conservative-lifting-rule fix, 40 m geometry, conservative rule) → new main measure (main geometry), plus the macros
   added by the unified bound and by the main geometry; tables.md: which tables/*.tex changed against the old main
   measure; numbers_fail.csv: make_numbers.py assertions that fail under the new main measure (compared with the
   conservative lifting rule).
3. core.md: core instances (long single lane / long corridor 1 km/h, 10 piles per vessel) × cradle layout (in-line
   roadside, pull-in, side by side) × first cradle 40 / 150 / 170 m × Q_h = 0, 1, unlimited, FCFS and L″_lift*
   (shortest over K = 1-8); the 40 m geometry also has a row with the span of the lifted load counted to the gate
   (span batch of the conservative lifting rule); side by side also lists the alternative turn into the cradle.
4. yards.md: Okpo and Yantai, three-voyage yards, 10 piles per vessel (cradle S = 1), three levels, with feasible turns
   (siteport of the unified bound) and with alternative turns of 600 and 1,800 s; feasible share of the swept-path
   check.
5. regime.md: A1 points of E1 classified into five regimes by W″_lift under the main geometry, attainment rate per
   class, compared with the unified bound (40 m).
6. spatial/: tables of the summary script of the spatial additions (windport_report_spatial.py) under the main geometry
   (sites, siteport, turn, reserve use the shipyard-map directories of the unified bound).
7. geom.md: geometry check.
Output results/windport_maingeom_report_<first 12 hex digits of the SHA-256 of the inputs and this script>/.
Run: python experiments/windport_report_maingeom.py
"""
import collections
import csv
import hashlib
import itertools
import json
import shutil
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                        # noqa: E402
import windport_report_spatial as AR                               # noqa: E402
import windport_report_conservative as R                                # noqa: E402
import windport_recheck_maingeom as FK                              # noqa: E402

H = 3600.0
R.TMP = ROOT / "out" / "maingeom_rep"
CONSERVATIVE_REP = ROOT / "results" / "tables/conservative"
UNIFIED_REP = ROOT / "results" / "tables/unified"
UNIFIED_RECHECK = ROOT / "results" / "runs/unified_recheck"
UNIFIED_SITEPORT = ROOT / "results" / "runs/unified_siteport"
CONSERVATIVE_SPAN = ROOT / "results" / "runs/conservative_span"
SCEN_ZH, MODE_ZH = AR.SCEN_ZH, dict(AR.MODE_ZH, side="side by side")
ARR_ZH = dict(S0="direct lifting S = 0", S1="cradle S = 1", S1m="mixed lifting S = 1", S3="cradle S = 3",
              S3m="mixed lifting S = 3")
CLS_ZH = dict(crane="crane", cradle="cradle turnover", fleet="fleet", road="road", prep="preparation time")
i, fl, rd, wcsv, md, pct = AR.i, AR.fl, AR.rd, AR.wcsv, AR.md, AR.pct


def one(pre):
    return FK.one_dir(pre)


def dirs():
    D = FK.dirs()
    return dict(run=D, recheck=one("windport_maingeom_recheck_"), codesign=one("windport_maingeom_codesign_"), geom=one("windport_maingeom_geom_"),
                example=one("windport_maingeom_example_"), critical=one("windport_maingeom_critical_"),
                random=sorted(p for p in (ROOT / "results").glob("windport_maingeom_random_*") if (p / "summary.json").exists()))


# ---------------------------------------------------------------- 1. summary scripts and manuscript macros
def batch_dirs(D):
    """Batch key of windport_report_conservative → directory name: rerun directories of the main geometry; E6 from the
    conservative lifting rule, E2 from the main geometry (with e2long)."""
    import windport_rerun_conservative as RR
    import windport_maingeom as F
    out = {b: D["run"][b].name for b in F.rerun_batches()}
    out["runs:e6"] = F.conservative_dir("runs:e6").name
    out["e1e3:e2"] = D["run"]["e1e3:e2"].name
    out["e1e3:e2long"] = out["e1e3:e2"] + "/e2long"
    assert set(RR.SRC) <= set(out)
    return out


def summaries(D, out):
    Db = batch_dirs(D)
    # the example table and the critical length (analytic) are also taken from the main geometry
    R.SWAP[R.RC].update(example="extra:example", critical="extra:critical")
    Db.update({"extra:example": D["example"].name, "extra:critical": D["critical"].name})
    ra = R.run_reports("after", Db, out)
    mp = R.mapping_after(Db, ra)
    mp["results/runs/critical"] = D["critical"].relative_to(ROOT).as_posix()
    mp["results/runs/example"] = D["example"].relative_to(ROOT).as_posix()
    Mf, fails = R.numbers("after", mp, out)
    try:
        lit = R.literals(ra)
    # main geometry: the shortest fixed duration of Table 3 (fix_min) has several values over K_ref ("a/b/c");
    # ratios use the smallest one, the macro is written as a/b/c
    except ValueError:
        import builtins
        R.float = lambda s: min(builtins.float(x) for x in str(s).split("/"))
        try:
            lit = R.literals(ra)
        finally:
            del R.float
    Mf.update(lit)
    if fails:
        wcsv(out / "numbers_fail.csv", fails)
    figures(mp, out)
    return ra, Mf, fails


def figures(mapping, out):
    """Runs the manuscript's make_figures.py unchanged (assertions do not stop it, as in the after run of
    make_numbers), reading the same new directories; figures go to numbers/after/figures/ (no maps drawn)."""
    import ast
    d = out / "numbers" / "after"
    (d / "scripts").mkdir(parents=True, exist_ok=True)
    src = (R.PAPER / "scripts" / "make_figures.py").read_text(encoding="utf-8")
    tree = R.Soft().top(ast.parse(src))
    saved = sys.modules.get("src")
    sys.modules["src"] = R.fake_src(mapping)
    g = dict(__name__="figures", __file__=str(d / "scripts" / "make_figures.py"), _AF=[], _EF=[])
    try:
        exec(compile(tree, str(R.PAPER / "scripts" / "make_figures.py"), "exec"), g)
        for name in ("fig_bound", "fig_regime", "fig_fixed", "fig_plateau", "fig_iso", "fig_overlap", "fig_upsize", "fig_sens", "fig_yards", "fig_critical",
                     "fig_cheapest"):
            try:
                g[name]()
            except Exception as e:
                g["_EF"].append((0, f"{name}: {e!r}"[:300]))
    finally:
        if saved is None:
            sys.modules.pop("src", None)
        else:
            sys.modules["src"] = saved
        shutil.rmtree(d / "scripts", ignore_errors=True)
    lines = src.splitlines()
    fails = [dict(kind="assert", line=n, src=lines[n - 1].strip()) for n in g["_AF"]] + \
        [dict(kind="error", line=n, src=(lines[n - 1].strip() + "  ⇒ " if n else "") + e) for n, e in g["_EF"]]
    wcsv(out / "figures_fail.csv", fails or [dict(kind="", line="", src="")])


# ---------------------------------------------------------------- 3. core instances
def core(D, out, N):
    rows = rd(D["run"]["maingeom:core"] / "points.csv")
    span = rd(CONSERVATIVE_SPAN / "points.csv")
    g = collections.defaultdict(list)
    for r in rows:
        if r["port_h"] not in ("", None):
            g[(r["scen"], r["lay"], r["arr"], r["hold"], float(r["first"]), float(r["extra"]))].append(r)
    def best(rs):
        """(FCFS minimised over K, L″_lift* at the K attaining it, that K, L″_lift* minimised over K)."""
        if not rs:
            return None, None, None, None
        p_, l_, k_ = min((fl(r["port_h"]), fl(r["lstar_lo"]), i(r["K"])) for r in rs)
        return p_, l_, k_, min(fl(r["lstar_lo"]) for r in rs)
    tab = []

    def put(t, tag, rs):
        t[f"f{tag}"], t[f"l{tag}"], t[f"k{tag}"], t[f"m{tag}"] = best(rs)
    for sc, lay, arr in itertools.product(("lane", "longslow"), ("on_road", "pull_in", "side"), ("S0", "S1", "S1m", "S3", "S3m")):
        t = dict(scen=sc, lay=lay, arr=arr)
        for first in (40.0, 150.0, 170.0):
            for h in ("0", "1", "inf"):
                put(t, f"{int(first)}_h{h}", g[(sc, lay, arr, h, first, 0.0)])
        if lay == "side":
            for x in (600.0, 1800.0):
                put(t, f"170_x{int(x)}", g[(sc, lay, arr, "0", 170.0, x)])
            a, b, c = t["f170_h0"], t["f170_x600"], t["f170_x1800"]
            t["nonmono"] = int(b < a - 1e-9 or c < a - 1e-9 or c < b - 1e-9)       # faster with the alternative turn: FCFS non-monotone
        if lay != "side":
            sp = [r for r in span if (r["span"], r["scen"], r["mode"], r["arr"], r["hold"]) == ("gate", sc, lay, arr, "0") and r["port_h"] not in ("", None)]
            t["f40_gate"] = min((fl(r["port_h"]) for r in sp), default=None)
        tab.append(t)
    wcsv(out / "core.csv", tab)
    f2 = lambda v: "-" if v is None else f"{v:.2f}"
    cell = lambda t, tag: f"{f2(t['f' + tag])} (K = {t['k' + tag]}: {f2(t['l' + tag])})"
    tags = [f"{f}_h{h}" for f in (40, 150, 170) for h in ("0", "1", "inf")] + ["170_x600", "170_x1800"]
    diff = [(t, tag) for t in tab for tag in tags if t.get("m" + tag) is not None and t["m" + tag] < t["l" + tag] - 1e-9]
    mins = sorted({f2(t["m" + tag]) for t, tag in diff})
    nm = [t for t in tab if t.get("nonmono")]
    L = ["# Core instances: port time for 10 piles per vessel (FCFS, shortest over K = 1-8; in brackets the K "
         "attaining it and L″_lift* at that K)\n",
         "First cradle: 40 m (old geometry, violates \"first cradle at least one vehicle-plus-load length from the "
         "gate\"), 150 m (the whole vehicle stands on the apron, but the pile tail on the cradle is still inside the "
         "gate turning circle), 170 m (main geometry, the geometry check of the loading routes passes). "
         "Conservative lifting rule t_u = 0.05 p. The 40 m column also lists the span of the lifted load counted to "
         "the gate (span batch of the conservative lifting rule, Q_h = 0). Side by side: one 40 m pull-in stub per "
         "cradle, 20 m apart (the abstraction of the spatial additions, not the actual placement of the piles), "
         "first stub as far from the gate as the first cradle; the alternative turn into the cradle of 600 and "
         "1,800 s is a scenario value (the turn into the cradle is not checked geometrically).\n",
         f"Cells where L″_lift* minimised over K (rule-independent lower bound with K also free, column m of "
         f"core.csv) differs from the bracketed value: {len(diff)} "
         f"(of {sum(1 for t in tab for tag in tags if t.get('m' + tag) is not None)} cells), "
         f"minimised over K they are all {', '.join(mins) or '-'} h"
         + ("; for in-line cells with Q_h = 0 the two coincide" if not any(tag.endswith("_h0") and t["lay"] != "side" for t, tag in diff) else "") + ".\n"]
    if nm:
        L.append("† With the alternative turn FCFS becomes faster or non-monotone (non-monotonicity of no-wait FCFS; "
                 "checker passes): " +
                 "; ".join(f"{SCEN_ZH[t['scen']]} {ARR_ZH[t['arr']]} {f2(t['f170_h0'])} / {f2(t['f170_x600'])} / {f2(t['f170_x1800'])} h" for t in nm) +
                 ". These cells are not cited as \"alternative-turn ranges\".\n")
    for sc in ("lane", "longslow"):
        L += [f"## {SCEN_ZH[sc]}\n", "| Layout | Lifting | 40 m: Q_h = 0 (load to gate) | 150 m: Q_h = 0 | "
              "**170 m: Q_h = 0** | 170 m: Q_h = 1 | 170 m: Q_h unlimited | 170 m side by side + alternative 600 / 1,800 s |",
              "|---|---|---|---|---|---|---|---|"]
        for t in tab:
            if t["scen"] != sc:
                continue
            gate = f" (to gate {f2(t['f40_gate'])})" if t.get("f40_gate") is not None else ""
            sx = (f"{f2(t.get('f170_x600'))} / {f2(t.get('f170_x1800'))}" + ("†" if t.get("nonmono") else "")) if t["lay"] == "side" else ""
            L.append(f"| {MODE_ZH[t['lay']]} | {ARR_ZH[t['arr']]} | {cell(t, '40_h0')}{gate} | {cell(t, '150_h0')} | **{cell(t, '170_h0')}** | {cell(t, '170_h1')} | "
                     f"{cell(t, '170_hinf')} | {sx} |")
        L.append("")
    md(out, "core.md", L)
    N["core_nonmono"] = [f"{t['scen']}|{t['arr']}" for t in nm]
    N["core"] = {f"{t['scen']}|{t['lay']}|{t['arr']}": t for t in tab}


def sens(D, out, N):
    """t_u sensitivity: sens of the conservative lifting rule (40 m) and of the main geometry, shortest over K = 1-8."""
    old = rd(ROOT / "results" / "runs/conservative_sens" / "points.csv")
    new = rd(D["run"]["conservative:sens"] / "points.csv")
    best = lambda rows, *k: min((fl(r["port_h"]) for r in rows if (r["var"], r["scen"], r["mode"], r["arr"]) == k), default=None)
    L = ["# t_u sensitivity of the core instances: 40 m (conservative lifting rule) → main geometry, 10 piles per "
         "vessel, Q_h = 0, shortest over K = 1-8 (h)\n",
         "| Scenario | Cradle layout | Lifting | Original rule | t_u = 0 | t_u = 0.05 p | t_u = 0.1 p |",
         "|---|---|---|---|---|---|---|"]
    tab = {}
    for sc, m, arr in itertools.product(("lane", "longslow"), T.MODES, ("S0", "S1", "S1m", "S3", "S3m")):
        cells = []
        for v in ("orig", "tu0", "tu05", "tu10"):
            a, b = best(old, v, sc, m, arr), best(new, v, sc, m, arr)
            tab[f"{sc}|{m}|{arr}|{v}"] = (a, b)
            cells.append(f"{a:.2f} → **{b:.2f}**")
        L.append(f"| {SCEN_ZH[sc]} | {MODE_ZH[m]} | {ARR_ZH[arr]} | " + " | ".join(cells) + " |")
    md(out, "sens.md", L)
    N["sens"] = tab


# ---------------------------------------------------------------- 4. Okpo and Yantai, three voyages
def turn_share():
    """Swept-path check of the spatial additions: share of three-voyage yard loading routes whose sector is clear of
    buildings / of buildings and water along the whole route."""
    d = AR.one("turngeo")
    out = {}
    for r in rd(d / "turn_routes.csv"):
        if r["storage"] != "multi":
            continue
        k = r["site"]
        a = out.setdefault(k, dict(n=0, ok_building=0, ok_water=0))
        a["n"] += 1
        a["ok_building"] += i(r["ok_building"])
        a["ok_water"] += i(r["ok_water"])
    return out


def yards(D, out, N):
    from windport import archetypes as A
    from windport import bound_all as BA
    import windport_spatial as TA
    A.use("legacy40")                                     # shipyard maps are independent of the archetype geometry
    base = {r["key"]: r for r in rd(UNIFIED_SITEPORT / "points.csv")}
    new = rd(D["run"]["maingeom:yards"] / "points.csv")
    rows = []
    KS = range(2, 9)                                       # shortest over K = 2-8 (K = 1 is a separate level)
    for site, m, h in itertools.product(("okpo", "yantai"), T.MODES, ("0", "1", "inf")):
        r = dict(site=site, mode=m, hold=h, K="2–8", crane=10.0)
        fc, ls = [], []
        for K in KS:
            d = dict(what="port", kind="map:" + site, st="multi", scen="base", mode=m, arr="S1", K=K, n_v=10)
            if h != "0":
                d["hold"] = h
            k = T.enc(d)
            if k in base and base[k]["port_h"] not in ("", None):
                fc.append((fl(base[k]["port_h"]), K))
                ls.append(BA.lstar(BA.w2_lift(TA.cfg_of("siteport", d)), 10)[0] / H)
        if not fc:
            continue
        r.update(lstar_0=round(min(ls), 4), fcfs_0=min(fc)[0], K_0=min(fc)[1])
        for x in (600, 1800):
            ys = [q for q in new if q["kind"] == "map:" + site and q["mode"] == m and q.get("hold", "0") == h and i(q["K"]) in KS and q["arr"] == "S1"
                  and float(q["extra"]) == x and q["port_h"] not in ("", None)]
            b = min(ys, key=lambda q: fl(q["port_h"]))
            r[f"lstar_{x}"], r[f"fcfs_{x}"], r[f"K_{x}"] = min(fl(q["lstar_lo"]) for q in ys), fl(b["port_h"]), i(b["K"])
        rows.append(r)
    A.use("main")
    wcsv(out / "yards.csv", rows)
    ts = turn_share()
    L = ["# Okpo and Yantai, three-voyage yards: three levels of port time for 10 piles per vessel (base, cradle "
         "S = 1), two turn treatments (h)\n",
         "Three levels: vessel-crane limit n_v·p = 10.00 h → rule-independent lower bound L″_lift*(10) (unified "
         "entry point, any dispatching, fixed routes) → FCFS (conservative lifting rule). Feasible turns: simulation "
         "of the unified-bound runs; alternative turn: the turn in the direction whose sector hits buildings or water "
         "in the swept-path check of the spatial additions is replaced by an alternative move (reversing plus "
         "crabbing, or turning in advance in open space), adding 600 s or 1,800 s (scenario values).\n",
         "Swept-path check (spatial additions, three-voyage yards, sector clear of buildings / of buildings and water "
         "along the whole route): " +
         "; ".join(f"{dict(okpo='Okpo', yantai='Yantai')[k]} {v['ok_building']} / {v['n']}, {v['ok_water']} / {v['n']}" for k, v in sorted(ts.items())) + ".\n",
         "Shortest over K = 2-8 (in brackets the K attaining it); L″_lift* is also minimised over K.\n",
         "| Shipyard | Cradle layout | Q_h | Vessel-crane limit | Feasible turns: L″_lift* → FCFS | "
         "Alternative 600 s | Alternative 1,800 s |", "|---|---|---|---:|---|---|---|"]
    for r in rows:
        L.append(f"| {dict(okpo='Okpo', yantai='Yantai')[r['site']]} | {MODE_ZH[r['mode']]} | {dict(inf='unlimited').get(r['hold'], r['hold'])} | 10.00 | "
                 f"{r['lstar_0']:.2f} → {r['fcfs_0']:.2f} (K = {r['K_0']}) | {r['lstar_600']:.2f} → {r['fcfs_600']:.2f} (K = {r['K_600']}) | "
                 f"{r['lstar_1800']:.2f} → {r['fcfs_1800']:.2f} (K = {r['K_1800']}) |")
    md(out, "yards.md", L)
    N["yards"], N["turn_share"] = {f"{r['site']}|{r['mode']}|{r['hold']}": r for r in rows}, ts


# ---------------------------------------------------------------- 5. five regimes
def regime(rec, out, N):
    import windport_spatial_analytic as AA
    old = {r["key"]: r for r in rd(UNIFIED_RECHECK / "rows.csv") if r["batch"] == "e1e3:e1" and r["sem"] == "lift"}
    new = {r["key"]: r for r in rec if r["batch"] == "e1e3:e1"}
    keep = AA.GRIDS["regime5"]["scen"]
    rows = []
    for k, q in new.items():
        f = k.split("|")
        if f[0] != "A1" or f[1] not in keep:
            continue
        o = old[k]
        rows.append(dict(key=k, scen=f[1], mode=f[2], lift=f[3], L=int(f[4][1:]), K=int(f[5][1:]), S=int(f[6][1:]), G=int(f[7][1:]),
                         sim_old=i(o["sim"]), w_old=i(o["new"]), cls_old=o["cls"], nat_old=o["nature"], bind_old=o["keys"],
                         sim=i(q["sim"]), w=i(q["new"]), cls=q["cls"], nat=q["nature"], bind=q["keys"], sub=q["sub"]))
    wcsv(out / "regime.csv", rows)
    main = [r for r in rows if r["lift"] != "mixed"]
    L = ["# Five regimes: A1 points of E1 (regime5 grid of the spatial additions), conservative-rule simulation and "
         "W″_lift; 40 m geometry (unified bound) → main geometry\n",
         "## Points per scenario (main lifting modes)\n",
         "| Scenario | Geometry | Crane | Cradle turnover | Fleet | Road | Preparation time | By nature: fleet / road |",
         "|---|---|---:|---:|---:|---:|---:|---|"]
    cnt = {}
    for sc in keep:
        for tag, ck, nk in (("40 m", "cls_old", "nat_old"), ("170 m", "cls", "nat")):
            rs = [r for r in main if r["scen"] == sc]
            c, n = collections.Counter(r[ck] for r in rs), collections.Counter(r[nk] for r in rs)
            cnt[f"{sc}|{tag}"] = dict(c)
            L.append(f"| {SCEN_ZH[sc]} | {tag} | {c['crane']} | {c['cradle']} | {c['fleet']} | {c['road']} | {c['prep']} | {n['fleet']} / {n['road']} |")
    L += ["\n## Attainment rate per class (points with simulation = bound / points in the class)\n",
          "| Regime | 40 m: points / attained | 170 m: points / attained |", "|---|---|---|"]
    tie = {}
    for k in ("crane", "cradle", "fleet", "road", "prep"):
        x = [(sum(1 for r in main if r[c] == k), sum(1 for r in main if r[c] == k and r[s] == r[w])) for c, s, w in
             (("cls_old", "sim_old", "w_old"), ("cls", "sim", "w"))]
        tie[k] = x
        L.append(f"| {CLS_ZH[k]} | " + " | ".join(f"{a} / {pct(b, a)}" for a, b in x) + " |")
    trans = collections.Counter((r["cls_old"], r["cls"]) for r in main)
    L += ["\n## Class changes (all main-measure points)\n", "| 40 m | 170 m | Points |", "|---|---|---:|"]
    L += [f"| {CLS_ZH[a]} | {CLS_ZH[b]} | {n} |" for (a, b), n in sorted(trans.items(), key=lambda x: -x[1]) if a != b]
    fig = [r for r in main if r["mode"] == "pull_in" and r["G"] == 3 and r["L"] in (4, 12)]
    ch = [r for r in fig if (r["cls_old"], r["nat_old"]) != (r["cls"], r["nat"])]
    L += [f"\nIn the fig:regime grid (pull-in, G = 3 h, L = 4, 12 h, {len(fig)} cells) the class changes in {len(ch)} cells.\n"]
    md(out, "regime.md", L)
    wcsv(out / "fig_regime_main.csv", [dict(scen=r["scen"], L=r["L"], K=r["K"], S=r["S"], cls=r["cls"], sub=r["sub"], nature=r["nat"], binding=r["bind"],
                                            sim=r["sim"], bound=r["w"]) for r in fig])
    N["regime"] = dict(counts=cnt, tie=tie, fig_cells=len(fig), fig_changed=len(ch))


# ---------------------------------------------------------------- 6. tables of the spatial additions
def spatial(D, ra, rec, out, N):
    import windport_spatial_analytic as AA
    o = out / "spatial"
    o.mkdir(exist_ok=True)
    br = {(r["batch"].split(":")[1], r["key"]): r for r in rec if r["batch"].startswith("unified:") and r["form"] == "win"}
    e_old = {p: ROOT / "results" / n for p, n in (("sites", "runs/unified_sites"), ("siteport", "runs/unified_siteport"),
                                                   ("turn", "runs/unified_turn"), ("reserve", "runs/unified_reserve"))}
    bo = {(r["batch"].split(":")[1], r["key"]): r for r in rd(UNIFIED_RECHECK / "rows.csv") if r["batch"].startswith("unified:") and r["form"] == "win"}
    E = {p: [dict(r, wprime=bo[(p, r["key"])]["branch"]) if (p, r["key"]) in bo else r for r in rd(d / "points.csv")] for p, d in e_old.items()}
    for p in ("hphd", "reach", "upsize", "ablate", "cdv"):
        E[p] = [dict(r, wprime=br[(p, r["key"])]["branch"]) if (p, r["key"]) in br else r for r in rd(D["run"][f"unified:{p}"] / "points.csv")]
    run = D["run"]
    import windport_maingeom as F
    e6 = F.conservative_dir("runs:e6")
    M, err = {}, {}

    def go(name, f, *a):
        try:
            return f(*a)
        except Exception:
            err[name] = traceback.format_exc()[-600:]
    AB = go("sites", AR.sites, E["sites"], rd(e6 / "points.csv"), E["siteport"], o, M)
    A_, B_ = AB if AB else ({}, {})
    go("turn", AR.turn, AR.one("turngeo"), E["turn"], A_, B_, o, M)
    go("reserve", AR.reserve, E["reserve"], A_, B_, o, M)
    e4, mix6 = rd(run["runs:e4"] / "points.csv"), rd(run["extra:mix6"] / "points.csv")
    go("reach", AR.reach, E["reach"], e4, mix6, o, M)
    go("upsize", AR.upsize, E["upsize"], rd(run["runs:e7"] / "points.csv"), o, M)
    go("ablate", AR.ablate, E["ablate"], rd(run["extra:port"] / "points.csv"), e4, o, M)
    go("hphd", AR.hphd, E["hphd"], rd(run["runs:sens"] / "points.csv"), o, M)
    go("codesign", AR.codesign, rd(D["codesign"] / "best.csv"), rd(D["codesign"] / "codesign.csv"), E["cdv"], o, M)
    g = AA.GRIDS["campaign"]
    saved = g["e3_dir"]
    g["e3_dir"] = str(run["e1e3:e3"].relative_to(ROOT)).replace("\\", "/")
    try:
        cam = go("campaign_rows", AA.campaign)
    finally:
        g["e3_dir"] = saved
    if cam:
        go("campaign", AR.campaign, [{k: str(v) for k, v in r.items()} for r in cam], o, M)
    rep134 = next(v for k, v in ra.items() if v.name.startswith("windport_runs_report_"))
    rep136 = next(v for k, v in ra.items() if v.name.startswith("windport_extra_report_"))
    go("p15", AR.p15, e4, mix6, rep134, rd(o / "table_siteport.csv"), rep136, o, M)
    (o / "numbers.json").write_text(json.dumps(M, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (o / "errors.json").write_text(json.dumps(err, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    N["spatial"], N["spatial_errors"] = M, sorted(err)


# ---------------------------------------------------------------- 7. geometry check
def geom(D, out, N):
    s = rd(D["geom"] / "summary.csv")
    L = ["# Geometry check (windport/geomcheck.py): minimum clearance (m, < 0 means overlap) of the turn swept "
         "circles (loaded radius L_v/2 = 55 m, empty 15 m) to berth water, piles on cradles and the single-lane "
         "flank constraints\n",
         "| First cradle m | Archetype | Scenario | Cradle layout | Lifting | Loading and return pass | Piles on land | "
         "Water | Piles on cradles | Single-lane flanks |", "|---:|---|---|---|---|---|---|---:|---:|---:|"]
    for r in s:
        L.append(f"| {float(r['first']):.0f} | {r['kind']} | {SCEN_ZH.get(r['scen'], r['scen'])} | {MODE_ZH.get(r['mode'], r['mode'])} | {r['arr']} | "
                 f"{'yes' if r['ok'] == '1' else '**no**'} | {'yes' if r['piles_on_land'] == '1' else 'no'} | {r['min_water']} | {r['min_piles']} | {r['min_flanks']} |")
    # by route (turns.csv): loading and return count towards pass / fail; unloading listed separately; the ramp foot
    # (turn after descending the ramp when unloading) only records clearance, under the crabbing / reorientation assumption
    tr = rd(D["geom"] / "turns.csv")
    agg = collections.defaultdict(list)
    for r in tr:
        agg[(float(r["first"]), r["kind"], r["route"])].append(r)
    mn = lambda rs, k: min((fl(r[k]) for r in rs if r.get(k) not in ("", None)), default=None)
    L += ["\n## By route (three archetypes × base / long single lane × two cradle modes × S = 1, 3)\n",
          "Loading (saddle row → cradle, loaded) and return (empty) count towards pass / fail; unloading (ramp top → "
          "saddle row, loaded) is listed separately; the ramp foot is the first turn after descending the ramp when "
          "unloading and, by assumption "
          "(the SPMT crabs or reorients, not counted as a 90° swept turn), only its clearance is recorded.\n",
          "| First cradle m | Archetype | Route | Turns | Pass | Minimum clearance: water / piles on cradles / "
          "single-lane flanks |", "|---:|---|---|---:|---:|---|"]
    order = ("load-out", "return", "unloading", "ramp foot")
    for k in sorted(agg, key=lambda k: (k[0], k[1], order.index(k[2]) if k[2] in order else 9)):
        rs = agg[k]
        L.append(f"| {k[0]:.0f} | {k[1]} | {k[2]} | {len(rs)} | {sum(i(r['ok']) for r in rs)} / {len(rs)} | {mn(rs, 'water')} / {mn(rs, 'piles')} / {mn(rs, 'flanks')} |")
    # side-by-side cradles (computed here): quay line at bay_m + long_clear; the turn into the cradle is an
    # abstraction, recorded only
    import windport_extra as X
    import windport_spatial as TA
    from windport import geomcheck as GC
    side = []
    for sc in ("base", "lane"):
        c = X.port_cfg(sc, "on_road", "S1", 2, 10, 0)
        c["geo"] = TA.side_geo(sc)
        r = GC.check(c)
        side.append(dict(scen=sc, ok=r["ok"], bays_on_land=r["bays_on_land"], **{f"min_{k}": v for k, v in r["min_clear"].items()},
                         **{f"assumed_{a}_water": v["water"] for a, v in r["assumed"].items()}))
    from windport import sim4 as S4
    D0, _, p0, *_ = S4.setup4(c)
    L += [f"\n## Side-by-side cradles (A1side, main geometry): quay line {GC.quay_edge(D0, p0):.0f} m from the apron "
          f"road centre line (stub length + longitudinal clearance, used only for the geometry check and drawings)\n",
          "In the model, side by side is the abstraction \"one pull-in stub per cradle\" (a 40 m stub cannot hold a "
          "110 m pile; it does not represent the actual placement of piles), so no piles are placed; for the turn into "
          "the cradle (from the apron into the stub) only the clearance is recorded.\n",
          "| Scenario | Loading and return pass | Stub end on land | Minimum clearance: water / single-lane flanks | "
          "Water clearance of the turn into the cradle (recorded only) |", "|---|---|---|---|---|"]
    L += [f"| {SCEN_ZH[x['scen']]} | {'yes' if x['ok'] else '**no**'} | {'yes' if x['bays_on_land'] else 'no'} | {x.get('min_water')} / {x.get('min_flanks')} | "
          f"{x.get('assumed_bay entry_water', '-')} |" for x in side]
    md(out, "geom.md", L)
    wcsv(out / "geom_side.csv", side)
    N["geom"], N["geom_side"] = s, side


# ---------------------------------------------------------------- 2. macros
def macros(D, Mf, fails, rec, out, N):
    old = {r["macro"]: r for r in rd(CONSERVATIVE_REP / "macros.csv")}
    rows = [dict(macro=k, manuscript=old[k]["before"] if k in old else "", legacy=old[k]["after"] if k in old else "", main=Mf.get(k, ""),
                 source="make_numbers.py (macros of the conservative-lifting-rule report)") for k in sorted(set(old) | set(Mf))]
    e_old = {r["macro"]: r for r in rd(UNIFIED_REP / "macros.csv")}
    byname = {r["macro"]: r for r in rows}

    def add(name, val, src):
        if name in byname:
            byname[name].update(main=val, source=src)
            return
        r = dict(macro=name, manuscript=e_old[name]["manuscript"] if name in e_old else "", legacy=e_old[name]["final"] if name in e_old else "", main=val,
                 source=src)
        rows.append(r)
        byname[name] = r
    f2 = lambda x: f"{x:.2f}"
    c = N["core"]
    add("LStarCradle", f2(c["lane|on_road|S1"]["m170_h0"]), "main geometry core: L″_lift* for cradle S = 1, Q_h = 0 "
        "(minimised over K; = FCFS)")
    add("LStarDirRoad", f2(c["lane|on_road|S0"]["m170_h0"]), "main geometry core: direct lifting, roadside "
        "(L″_lift* minimised over K)")
    add("LStarDirPull", f2(c["lane|pull_in|S0"]["m170_h0"]), "main geometry core: direct lifting, pull-in "
        "(L″_lift* minimised over K)")
    add("CoreCradleLegacy", f2(c["lane|on_road|S1"]["f40_h0"]), "core instance, cradle S = 1, 40 m old geometry "
        "(violates the first-cradle rule)")
    add("CoreCradleLegacyGate", f2(c["lane|on_road|S1"]["f40_gate"]), "40 m old geometry, span of the lifted load "
        "counted to the gate (span batch of the conservative lifting rule)")
    add("CoreCradleFirstOneFifty", f2(c["lane|on_road|S1"]["f150_h0"]), "first cradle 150 m (same value in the sens "
        "batch of the conservative lifting rule)")
    add("CoreCradleHoldOne", f2(c["lane|pull_in|S1"]["f170_h1"]), "main geometry, one gate holding place (pull-in)")
    add("CoreCradleHoldInf", f2(c["lane|pull_in|S1"]["f170_hinf"]), "main geometry, unlimited gate holding places (pull-in)")
    add("CoreSideCradle", f2(c["lane|side|S1"]["f170_h0"]), "main geometry, side-by-side cradles S = 1 (side by side "
        "is the pull-in stub abstraction)")
    s = N["sens"]
    add("TuRangeCradle", f"{f2(s['lane|on_road|S1|tu0'][1])}–{f2(s['lane|on_road|S1|tu10'][1])}", "main geometry: "
        "cradle S = 1 (roadside) for t_u = 0-0.1 p")
    add("TuRangeDirect", f"{f2(s['lane|on_road|S0|tu0'][1])}–{f2(s['lane|on_road|S0|tu10'][1])}", "main geometry: "
        "direct lifting S = 0 (roadside) for t_u = 0-0.1 p")
    add("CorePlainCradle", f2(s["lane|on_road|S1|orig"][1]), "main geometry: cradle S = 1 under the original lifting "
        "rule (appendix comparison)")
    xs = rd(D["run"]["conservative:xscan"] / "points.csv")
    for m, tag in (("on_road", "Road"), ("pull_in", "Pull")):
        b = collections.defaultdict(lambda: 1e9)
        for r in xs:
            if r["mode"] == m:
                b[(r["arr"], float(r["x"]))] = min(b[(r["arr"], float(r["x"]))], fl(r["port_h"]))
        cr = b[("S1", 0.0)]
        pts = sorted((x, v) for (a, x), v in b.items() if a == "S0")
        cut = next(((x1, v1, x2, v2) for (x1, v1), (x2, v2) in zip(pts, pts[1:]) if v1 <= cr + 1e-9 < v2), None)
        if cut:
            x1, v1, x2, v2 = cut
            xp = 3600 * (x1 + (cr - v1) / (v2 - v1) * (x2 - x1))
            add(f"XThresh{tag}", f"{xp:.0f}", f"main geometry: release-time threshold x·p above which direct lifting "
                f"S = 0 is slower than cradle S = 1 (s, {MODE_ZH[m]}, linear interpolation of xscan)")
    import windport_extra as X
    from windport import bound_all as BA
    from windport import lift as LF
    from windport import sim2 as S2
    for m, tag in (("on_road", "Road"), ("pull_in", "Pull")):
        c = X.port_cfg("lane", m, "S1", 2, 10, 0)
        Dm, net, p, *_ = S2.setup2(c)
        Wm = Dm["windport"]
        o = min(v["off"] for v in LF.pair_times(net, p, Wm["storage"], Wm["cradles"][:1]).values())
        add(f"Clear{tag}", f"{o:.0f}", f"main geometry: time o from arrival at the first cradle until the vehicle "
            f"body has left the road (s, {MODE_ZH[m]})")
        if m == "on_road":
            add("EpsU", f"{BA.parts(c, lift=True)['eps_u']:.0f}", "main geometry: time ε_U for the delivering vehicle "
                "to leave the area below the lifted load (s, core instance)")
    from windport import archetypes as A
    g = A.GEOMETRIES["main"]
    add("FirstCradleM", f"{g['gate_cradle_m']:.0f}", "main geometry: distance of the first cradle from the gate (m)")
    add("TurnOpenM", f"{g['turn_open_m']:.0f}", "main geometry: gate turning area radius (m)")
    add("QuayEdgeM", f"{g['quay_edge_m']:.0f}", "main geometry: quay line distance from the apron road centre line "
        "(m, in-line; only for the geometry check and drawings)")
    from windport import geomcheck as GC
    from windport import sim4 as S4
    import windport_spatial as TA
    cs = X.port_cfg("lane", "on_road", "S1", 2, 10, 0)
    cs["geo"] = TA.side_geo("lane")
    Ds, _, ps, *_ = S4.setup4(cs)
    add("QuayEdgeSideM", f"{GC.quay_edge(Ds, ps):.0f}", "quay line distance from the apron road centre line for "
        "side-by-side cradles (m, stub length + longitudinal clearance; only for the geometry check and drawings)")
    y = N["yards"]
    for site, tag in (("okpo", "Okpo"), ("yantai", "Yantai")):
        for m, mt in (("pull_in", "Pull"), ("on_road", "Road")):
            r = y[f"{site}|{m}|0"]
            for x, xt in (("600", "TurnSix"), ("1800", "TurnEighteen")):
                add(f"{tag}Multi{mt}LStar{xt}", f2(r[f"lstar_{x}"]), f"three voyages, L″_lift* (K = 2-8), alternative turn {x} s")
                add(f"{tag}Multi{mt}Fcfs{xt}", f2(r[f"fcfs_{x}"]), f"three voyages, FCFS (shortest over K = 2-8), "
                    f"alternative turn {x} s")
            add(f"{tag}Multi{mt}FcfsRange", f"{f2(r['fcfs_0'])}–{f2(r['fcfs_1800'])}", "three-voyage FCFS range: "
                "feasible turns → alternative 1,800 s (main figure in the text)")
            h1 = y.get(f"{site}|{m}|1")
            if h1:
                add(f"{tag}Multi{mt}HoldOneRange", f"{f2(h1['fcfs_0'])}–{f2(h1['fcfs_1800'])}", "one gate holding "
                    "place: feasible turns → alternative 1,800 s")
    ts = N["turn_share"]
    add("OkpoMultiTurnOk", f"{ts['okpo']['ok_building']}/{ts['okpo']['n']}", "swept-path check of the spatial "
        "additions: Okpo three-voyage routes feasible along the whole route")
    # E1, E2, recheck, random regression (rows of the main geometry)
    e1 = [r for r in rec if r["batch"] == "e1e3:e1"]
    for gk, name in (("A1|lane|on_road|cradle||0", "EOneTieLaneAOneW"), ("A1|lane|pull_in|cradle||0", "EOneTieLanePullW"),
                     ("A2|lane|on_road|cradle||0", "EOneTieLaneATwoW"), ("A3|lane|on_road|cradle||0", "EOneTieLaneAThreeW")):
        rs = [r for r in e1 if r["group"] == gk]
        if rs:
            add(name, f"{sum(i(r['tie']) for r in rs) / len(rs) * 100:.1f}\\%", f"E1 manuscript measure against the "
                f"unified W″_lift ({len(rs)} points)")
    add("EOneTieW", f"{sum(i(r['tie']) for r in e1) / len(e1) * 100:.1f}\\%", f"E1, all {len(e1):,} points")
    e2 = [r for r in rec if r["batch"] == "e1e3:e2" and r["cp_status"] == "OPTIMAL"]
    add("ETwoTieWpp", str(sum(i(r["tie"]) for r in e2)), f"E2: cases = W″_lift among the {len(e2)} proven optimal")
    add("ETwoOptN", str(len(e2)), "E2: number of cases proven optimal")
    lr = [r for r in rec if r["sem"] == "lift"]
    win = [r for r in lr if r["form"] in ("win", "e2")]
    add("RecheckLiftRows", f"{len(lr):,}".replace(",", "{,}"), f"recheck rows (main geometry, conservative rule, with "
        f"W″_lift; another {len(rec) - len(lr)} rows of the original rule with W″, {len(rec):,} rows in total)")
    add("RecheckOrigSensRows", str(len(rec) - len(lr)), "recheck rows under the original lifting rule (orig group of "
        "the t_u sensitivity, with W″)")
    add("RecheckLiftOver", str(sum(i(r["over"] or 0) for r in lr)), "rows with simulation / CP-SAT > W″_lift")
    add("RecheckLiftTie", f"{sum(i(r['tie']) for r in win) / len(win) * 100:.1f}\\%", "equality rate in the window form")
    rs = [json.loads((d / "summary.json").read_text(encoding="utf-8")) for d in D["random"]]
    add("RandUnifiedN", f"{sum(r['ran'] for r in rs):,}".replace(",", "{,}"), "random regression cases under the main "
        "geometry (two rules per case)")
    add("RandUnifiedPiles", f"{sum(r['lifts'] + r['lifts_lift'] for r in rs):,}".replace(",", "{,}"), "piles checked one by one")
    rg = N["regime"]
    x = rg["counts"].get("lane|170 m", {})
    for k, kt in (("road", "Road"), ("prep", "Prep"), ("crane", "Crane"), ("fleet", "Fleet")):
        add(f"RegimeLane{kt}", str(x.get(k, 0)), "points per regime (long single lane, main geometry)")
    rt = rg["tie"]["road"][1]
    add("RegimeRoadTie", f"{rt[1] / rt[0] * 100:.1f}\\%" if rt[0] else "-", f"attainment rate of the road class "
        f"(main geometry, {rt[0]} points)")
    for r in rows:
        r["changed"] = int(r["legacy"] != r["main"])
    wcsv(out / "macros.csv", rows)
    L = ["# Macro replacement table: manuscript value → old main measure (40 m geometry, conservative rule: after the "
         "conservative-lifting-rule fix / final value of the unified bound) → new main measure (main geometry)\n",
         f"Macros: {len(rows)}; differing between the new and the old main measure: "
         f"{sum(r['changed'] for r in rows)} (table below); make_numbers.py "
         f"assertions failing / statements raising under the new main measure: {len(fails)} "
         "(numbers_fail.csv). An empty old-main-measure column marks a macro added for the main geometry.\n",
         ("Cells of core.md where FCFS is non-monotone with the alternative turn (" + ", ".join(N.get("core_nonmono", []))
          + ") are not cited for conclusions; no macro is taken from them.\n"
          if N.get("core_nonmono") else ""),
         "| Macro | Manuscript value | Old main measure | **New main measure** | Source |", "|---|---|---|---|---|"]
    L += [f"| \\{r['macro']} | {r['manuscript']} | {r['legacy']} | **{r['main']}** | {r['source']} |" for r in rows if r["changed"]]
    md(out, "macros.md", L)
    N["macros"] = dict(total=len(rows), changed=sum(r["changed"] for r in rows))


def tables(out, N):
    a, b = CONSERVATIVE_REP / "numbers" / "after" / "tables", out / "numbers" / "after" / "tables"
    s = R.same_files(a, b)
    md(out, "tables.md", ["# Manuscript tables tables/*.tex: old main measure (after the conservative-lifting-rule fix) "
                          "→ new main measure (main geometry)\n", "| File | Same |", "|---|---|"] +
       [f"| {k} | {'yes' if v else '**no**'} |" for k, v in s.items()])
    old = {(r["kind"], r["src"].split("  ⇒")[0]) for r in rd(CONSERVATIVE_REP / "numbers_fail.csv")}
    new = rd(out / "numbers_fail.csv") if (out / "numbers_fail.csv").exists() else []
    wcsv(out / "numbers_fail_new.csv", [r for r in new if (r["kind"], r["src"].split("  ⇒")[0]) not in old])
    N["tables"] = dict(changed=sorted(k for k, v in s.items() if not v), fails=len(new), fails_new=sum(1 for r in new if (r["kind"], r["src"].split("  ⇒")[0]) not in old))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    from windport import archetypes as A
    A.use("main")
    D = dirs()
    inputs = [D["recheck"] / "rows.csv", D["codesign"] / "codesign.csv", D["geom"] / "summary.csv"] + [d / "summary.json" for d in D["random"]] + \
        [d / "points.csv" for d in D["run"].values()]
    h = hashlib.sha256(Path(__file__).read_bytes())
    for f in inputs:
        h.update(f.read_bytes())
    out = ROOT / "results" / f"windport_maingeom_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    rec = rd(D["recheck"] / "rows.csv")
    N = {}
    ra, Mf, fails = summaries(D, out)
    core(D, out, N)
    sens(D, out, N)
    yards(D, out, N)
    regime(rec, out, N)
    spatial(D, ra, rec, out, N)
    geom(D, out, N)
    macros(D, Mf, fails, rec, out, N)
    tables(out, N)
    N["random"] = {d.name: json.loads((d / "summary.json").read_text(encoding="utf-8")) for d in D["random"]}
    (out / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out / "inputs.json").write_text(json.dumps([str(f.relative_to(ROOT)).replace("\\", "/") for f in inputs], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)
    print("tables of the spatial additions with errors:", N["spatial_errors"], "; changed tables:", N["tables"])


if __name__ == "__main__":
    main()
