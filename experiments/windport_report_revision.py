"""Summary of the revision studies: per-item result tables (for the report and the manuscript), recheck counts of the new points,
and a comparison of the manuscript's make_numbers / make_figures macros, tables, figures and assertions on the revision-study
directories (against the design analyses). Runs no simulation.

Reads: windport_revision_{cd, s01, plans, bturn, bnear, btr, bmulti, analytic, t8_*, rate_*}_* (first runs);
windport_revision_r1_{x, sens, e2, ex, inv, recheck, rated}_* (the 115 m spacing re-runs: every parametric-port batch that feeds the
manuscript, re-run at 115 m and spliced back into the submitted format, see windport_revision_r1.py); the design-analyses summary
tables/design (numbers.json, paper_mapping.json, compat/), the main2-geometry summary
tables/main2 and the design-analyses batch directories (IR.dirs).
Writes results/windport_revision_report_<first 12 hex of SHA-256 of inputs and this script>/:
  scope.md (re-run list: batch, manuscript source, rows, changed rows and largest difference), t8.md, rate.md, codesign.md / .csv
  (Table 12, tab_cddisp), econ.md, buffer.md, stage.md, rated.md, premise.md, p2.md, recheck.md, hrep/ (the files of the
  main2-geometry summary redone on the 115 m batches: core, regime, spatial/, macros, geom_compat, recheck/rows.csv), compat/,
  reports/after/, paper_macros.csv / .md, paper_tables.md, numbers_fail_*.csv, figures_fail_*.csv, numbers.json.
Run: python experiments/windport_report_revision.py
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
import windport_report_design as IR                               # noqa: E402

H = 3600.0
R = ROOT / "results"
I_REP = R / "tables/design"
SITE_ZH, MODE_ZH, SCEN_ZH = IR.SITE_ZH, IR.MODE_ZH, IR.SCEN_ZH
rd, md, fl, i_ = IR.rd, IR.md, IR.fl, IR.i
SPEED_ZH = dict(v1="1 km/h", v25="2.5 km/h", r10="rated 10 / 11.5 km/h", r5="rated 5 / 11.5 km/h")
PAVE = dict(usd_per_yd2=42.0, src="PCA PL620 (2006): roller-compacted concrete yard pavement at Norfolk International Terminals, 16.5 in + 3 in asphalt, 'The final cost ($42 per square yard)'",
            url="https://pacaweb.org/uploads/documents/Ports_RCC.pdf")
PAVE_M2 = PAVE["usd_per_yd2"] / 0.83612736                    # $/m²
LANE_M, LANE_W, WIDEN_W, PP_M = 1200.0, 10.0, 16.0, 150.0     # long single lane 1.2 km, 10 m; widened to 16 m; passing place 150 m × 16 m (cd_configs)
HOLD_AREA = (110.0 + 2 * 5.0) * (9.5 + 2 * 1.0)                # gate holding place: stop for one loaded vehicle group (L_v + 2δ) × (d_m + 2c_lat), assumed


def one(prefix):
    ds = sorted(p for p in R.glob(prefix + "*") if p.is_dir() and len(p.name) == len(prefix) + 12)
    assert len(ds) == 1, (prefix, ds)
    return ds[0]


H_REP = R / "tables/main2"


def kdirs():
    K = {k: one(f"windport_revision_{k}_") for k in ("t8_port", "t8_e3", "t8_fix", "rate_e4", "rate_mix6", "rate_reach", "cd", "s01", "plans", "bturn", "bnear", "btr",
                                                  "bmulti", "analytic", "avgcrab")}
    K.update({f"r1_{k}": one(f"windport_revision_r1_{k}_") for k in ("x", "sens", "e2", "ex", "inv", "rated")})
    K.update({f"r1rc_{k}": one(f"windport_revision_r1rc_{k}_") for k in ("main", "e2")})
    K["r1inv2"] = one("windport_revision_r1inv2_")
    return K


def r1_rows(K):
    """W″_lift recheck of the 115 m re-run rows (main and e2 parts of windport_revision_r1rc)."""
    return rd(K["r1rc_main"] / "rows.csv") + rd(K["r1rc_e2"] / "rows.csv")


def wcsv(p, rows):
    IR.wcsv(p, rows)


def f2(x):
    return "-" if x is None else f"{x:.2f}"


# ================================================================ splice: submitted batches with the 115 m rows swapped in (splice subdirs of windport_revision_r1)
def splice(K):
    """{batch: splice dir} (x, sens, e2 parts of windport_revision_r1) and the per-batch splice statistics (summary.json)."""
    made, stat = {}, {}
    for part in ("r1_x", "r1_sens", "r1_e2"):
        for d in sorted((K[part] / "splice").iterdir()):
            b = d.name.replace("_", ":", 1)
            made[b] = d
            s = d / "summary.json"
            stat[b] = json.loads(s.read_text(encoding="utf-8")) if s.exists() else None
    stat["e1e3:e2"] = json.loads((K["r1_e2"] / "summary.json").read_text(encoding="utf-8"))
    return made, stat


def batch_dirs_k(made):
    """Batch of the windport_report_conservative summary scripts → directory relative to results/: the directories of the main2-geometry
    summary (runs:e6 takes the design-analyses e6:hi), re-run batches replaced by their splice directories."""
    import windport_report_main2 as HR
    HD = HR.dirs()
    Db = HR.batch_dirs(HD)
    Db.update({"extra:example": HD["example"].name, "extra:critical": HD["critical"].name})
    Db["runs:e6"] = IR.dirs()["e6_hi"].name
    rel = lambda p: p.relative_to(R).as_posix()
    for b, d in made.items():
        if b in Db:
            Db[b] = rel(d)
    Db["e1e3:e2long"] = Db["e1e3:e2"] + "/e2long"
    return Db


def reports_after(out, made, K):
    """Re-run the three submitted summary scripts unchanged: batch directories as in batch_dirs_k, example table and critical
    length from the 115 m re-run ex."""
    import windport_report_conservative as RD
    RD.TMP = ROOT / "out" / "revision_rep"
    Db = batch_dirs_k(made)
    RD.SWAP[RD.RC].update(example="extra:example", critical="extra:critical")
    Db.update({"extra:example": (K["r1_ex"] / "example").relative_to(R).as_posix(), "extra:critical": (K["r1_ex"] / "critical").relative_to(R).as_posix()})
    return RD.run_reports("after", Db, out)


# ================================================================ files of the main2-geometry summary redone on the 115 m batches
def recheck_rows_k(made, K):
    """Recheck rows.csv read by the manuscript: recheck rows of the main2-geometry summary (recheck_rows), with re-run
    (batch, key) pairs replaced by the rows of the 115 m re-run recheck."""
    import windport_report_main2 as HR
    D = HR.dirs()
    rec = HR.recheck_rows(D)
    new = {(r["batch"], r["key"]): r for r in r1_rows(K)}
    hit = 0
    out = []
    for r in rec:
        x = new.get((r["batch"], r["key"]))
        if x is not None:
            hit += 1
            r = x
        out.append(r)
    return out, hit, len(new)


def hrep(made, ra, K, out, N):
    """Step 2 of windport_report_main2.main (core, core_n, sens, yards, regime, spatial, geom_compat, recheck, macros) with the
    batch directories replaced by the splice directories; writes out/hrep/ (first copies the other manuscript files of the
    main2-geometry summary, then overwrites the redone ones). Installs the 115 m spacing and main2 in the process (used by the
    parts of geom_compat and macros computed on the fly)."""
    import windport_report_maingeom as FR
    import windport_main2_runs as HX
    import windport_report_main2 as HR
    import windport_revision_lib as KL
    import windport_report_conservative as RD
    HX.install()
    KL.install_spacing(115.0)
    ho = out / "hrep"
    if ho.exists():
        shutil.rmtree(ho)
    shutil.copytree(H_REP, ho, ignore=shutil.ignore_patterns("numbers", "reports"))
    D = HR.dirs()
    for b, d in made.items():
        if b in D["run"]:
            D["run"][b] = d
        if b in D["f"]["run"]:
            D["f"]["run"][b] = d
    D["example"] = D["f"]["example"] = K["r1_ex"] / "example"
    D["critical"] = D["f"]["critical"] = K["r1_ex"] / "critical"
    FR.batch_dirs = HR.batch_dirs
    rec, hit, n_new = recheck_rows_k(made, K)
    N["recheck_rows"] = dict(rows=len(rec), replaced=hit, r1_rows=n_new)
    RD.TMP = ROOT / "out" / "revision_hrep"
    RD.TMP.mkdir(parents=True, exist_ok=True)
    Nh = {}
    HR.core(D, ho, Nh)
    HR.core_n(D, Nh)
    wcsv(ho / "core.csv", list(Nh["core"].values()))
    FR.sens(D, ho, Nh)
    FR.yards(D, ho, Nh)
    from windport import archetypes as A
    A.use("main2")
    KL.install_spacing(115.0)
    FR.regime(rec, ho, Nh)
    FR.spatial(D, ra, rec, ho, Nh)
    HR.geom_compat(D, ho)
    HR.recheck_compat(rec, ho)
    Dm = dict(D, random=D["h"]["random"])
    FR.macros(Dm, {}, [], rec, ho, Nh)
    same = RD.same_files(H_REP, ho)
    N["hrep"] = dict(changed=sorted(k for k, v in same.items() if not v and not k.startswith(("numbers/", "reports/"))))
    return ho, D, rec, Dm, Nh


# ================================================================ re-run list
def scope(made, stat, reads, figreads, out, N):
    """Re-run list: batch, files read by the manuscript, rows, recomputed rows, rows byte-identical to the submitted ones, largest
    numeric difference (port time h / window lifts)."""
    BD = {}
    import windport_report_main2 as HR
    for b, d in HR.dirs()["run"].items():
        BD[b] = d
    L = ["# Re-run list: parametric-port batches that feed the manuscript, cradle spacing 110 → 115 m (windport_revision_r1)\n",
         "Manuscript sources are inferred from the files make_numbers / make_figures actually read under the revision-study mapping (paths after src.where and the mapping; summary files are assigned to batches as the three summary scripts and the main2-geometry summary read them).\n",
         "| Batch | Submitted dir | Rows | Recomputed | Byte-identical | Changed rows | Max port-time diff h (per point) | Max lift diff (per point) | Checker failures |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    rows = []
    for b in sorted(made):
        d = made[b]
        if b == "e1e3:e2":
            df = rd(d / "diff.csv")
            ch = [r for r in df if r["same"] != "1"]
            dcp = max((abs(int(r["cp_new"]) - int(r["cp_old"])) for r in df), default=0)
            dsim = max((abs(int(r["sim_new"]) - int(r["sim_old"])) for r in df), default=0)
            s = stat["e1e3:e2"]
            rows.append(dict(batch=b, src="runs/maingeom_e2", rows=s["rows"], recomputed=s["recomputed"], same=s["same"], changed=len(ch), dport="",
                             dsim=max(dcp, dsim), check_fail=s["check_fail"]))
            continue
        s = stat[b]
        new = {}
        lines_new = (d / "points.csv").read_text(encoding="utf-8").splitlines()
        lines_old = (BD[b] / "points.csv").read_text(encoding="utf-8").splitlines()
        on, oo = list(csv.DictReader(lines_new)), list(csv.DictReader(lines_old))
        dp = ds = 0.0
        nch = 0
        for a, o in zip(on, oo):
            if a == o:
                continue
            nch += 1
            for c in ("port_h", "occ", "port_h_occ"):
                if c in a and a[c] not in ("", "None") and o[c] not in ("", "None"):
                    dp = max(dp, abs(float(a[c]) - float(o[c])))
            for c in ("sim", "lifts"):
                if c in a and a[c] not in ("", "None") and o[c] not in ("", "None"):
                    ds = max(ds, abs(float(a[c]) - float(o[c])))
        rows.append(dict(batch=b, src=s["src"], rows=s["rows"], recomputed=s["recomputed"], same=s["same"], changed=nch, dport=round(dp, 3), dsim=int(ds),
                         check_fail=s["check_fail"]))
    for r in rows:
        L.append(f"| {r['batch']} | {r['src']} | {r['rows']:,} | {r['recomputed']:,} | {r['same']:,} | {r['changed']:,} | {r['dport']} | {r['dsim']} | {r['check_fail']} |")
    tot = lambda k: sum(int(r[k]) for r in rows)
    L.append(f"| **Total** | | {tot('rows'):,} | {tot('recomputed'):,} | {tot('same'):,} | {tot('changed'):,} | {max(float(r['dport'] or 0) for r in rows):.3f} | "
             f"{max(int(r['dsim']) for r in rows)} | {tot('check_fail')} |")
    # files read by the manuscript (after mapping)
    files = sorted({(r["local"] or r["where"]) for r in reads + figreads})
    L += ["\n## Result files read by the manuscript make_numbers / make_figures (after src.where and the revision-study mapping)\n"] + [f"- `{f}`" for f in files if f.startswith("results/")]
    md(out, "scope.md", L)
    wcsv(out / "scope.csv", rows)
    N["scope"] = rows


# ================================================================ item 1: the S = 3 rows of Table 8
def t8(K, out, ra, N):
    new5 = {(r["scen"], r["mode"], r["arr"]): r for r in rd(ra["extra"] / "table5x.csv")}
    old5 = {(r["scen"], r["mode"], r["arr"]): r for r in rd(I_REP / "reports" / "after" / "extra" / "table5x.csv")}
    def ls_of(rows_):
        out_ = collections.defaultdict(lambda: math.inf)
        for r in rows_:
            if r["batch"] != "extra:port":
                continue
            kv = T.dec(r["key"])
            if (kv["n_v"], kv["hold"], kv["rep"]) == ("10", "0", "fcfs"):
                out_[(kv["scen"], kv["mode"], kv["arr"])] = min(out_[(kv["scen"], kv["mode"], kv["arr"])], float(r["lstar"]))
        return out_
    lso = ls_of(rd(H_REP / "recheck" / "rows.csv"))
    lsn = ls_of(r1_rows(K))
    lsn = collections.defaultdict(lambda: math.inf, {k: lsn.get(k, lso[k]) for k in lso})
    cols = [("occ", "road occupancy FCFS"), ("cut", "single-resource cut"), ("hold1", "Q_h = 1"), ("hold_inf", "Q_h = ∞"), ("fixed", "fixed duration K_ref = 1"), ("muhabie_1h", "1 h per pile (literature value)")]
    rows = []
    L = ["# Item 1: Table 8 (tab:fixed) S = 3 tandem rows, cradle spacing 110 → 115 m (L_v + δ)\n",
         "A1, shortest port time to load 10 piles (K = 1-8, h), G = 24 h; columns as in Table 8 (table5x of the extra analyses). L*(10): rule-independent lower bound W″_lift (min over K = 1-8, Q_h = 0). "
         "1 h per pile: fixed-duration baseline with the literature value (single server of about 1 h per item, Muhabie et al.: bound3.muhabie_port, independent of K).\n",
         "| Scenario | Cradles | Lifting | " + " | ".join(z for _, z in cols) + " | L*(10) |", "|---|---|---|" + "---|" * (len(cols) + 1)]
    for sc in ("base", "slow", "longslow", "lane", "fastcrane"):
        for m in T.MODES:
            for arr in ("S3", "S3m"):
                o, n = old5[(sc, m, arr)], new5[(sc, m, arr)]
                row = dict(scen=sc, mode=m, arr=arr, lstar_old=round(lso[(sc, m, arr)], 4), lstar_new=round(lsn[(sc, m, arr)], 4))
                cells = []
                for c, _ in cols:
                    a, b = o[c].split(" / ")[0], n[c].split(" / ")[0]
                    row[f"{c}_old"], row[f"{c}_new"] = a, b
                    cells.append(f"{a} → **{b}**" if a != b else a)
                ls = f"{math.floor(row['lstar_old'] * 100 + 1e-9) / 100:.2f}" + (f" → **{math.floor(row['lstar_new'] * 100 + 1e-9) / 100:.2f}**"
                                                                              if abs(row['lstar_new'] - row['lstar_old']) > 1e-6 else "")
                rows.append(row)
                L.append(f"| {SCEN_ZH.get(sc, sc)} | {MODE_ZH[m]} | {'mixed lifting' if arr.endswith('m') else 'cradle'} | " + " | ".join(cells) + f" | {ls} |")
    d = [abs(float(r["occ_new"]) - float(r["occ_old"])) for r in rows]
    L.append(f"\nRoad occupancy FCFS column: {sum(x > 0.005 for x in d)} / {len(d)} rows changed (max {max(d):.2f} h); L*(10) changed in {sum(abs(r['lstar_new'] - r['lstar_old']) > 1e-6 for r in rows)} rows.")
    wcsv(out / "t8.csv", rows)
    md(out, "t8.md", L)
    N["t8"] = dict(rows=rows, max_occ_diff=round(max(d), 3), n_changed=sum(x > 0.005 for x in d))


# ================================================================ item 1: tandem rows of Table 10
def rate_tab(K, out, comp, N, made):
    import windport_report_spatial as AR
    rows = rd(made["unified:reach"] / "points.csv")
    e4 = rd(made["runs:e4"] / "points.csv")
    mx = rd(made["extra:mix6"] / "points.csv")
    # the Table 10 points of the first revision-study runs must match the same-key rows of the 115 m splice dirs field by field
    # (same semantics, same spacing; deterministic check)
    for src, base in ((K["rate_reach"], rows), (K["rate_e4"], e4), (K["rate_mix6"], mx)):
        bk = {r["key"]: r for r in base}
        bad = [r["key"] for r in rd(src / "points.csv") if any(str(r[c]) != str(bk[r["key"]].get(c, "")) for c in ("sim", "check_ok") if c in r)]
        assert not bad, (src.name, bad[:3])
    rows = [dict(r, wprime=r.get("wprime", r["w4"])) for r in rows]
    d = out / "ratetmp"
    d.mkdir(exist_ok=True)
    M = {}
    AR.reach(rows, e4, mx, d, M)
    tab = rd(d / "table7_rate.csv")
    old = rd(I_REP / "compat" / "spatial" / "table7_rate.csv")
    new_t = [r for r in tab if r["layout"] != "side"] + [r for r in old if r["layout"] == "side"]
    keyf = lambda r: (r["layout"], r["scen"], r["mode"], r["lift"])
    order = {keyf(r): k for k, r in enumerate(old)}
    new_t.sort(key=lambda r: order[keyf(r)])
    (comp / "spatial").mkdir(parents=True, exist_ok=True)
    with open(comp / "spatial" / "table7_rate.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(old[0].keys()))
        w.writeheader()
        w.writerows(new_t)
    shutil.copyfile(I_REP / "compat" / "spatial" / "table7_rate.md", comp / "spatial" / "table7_rate.md")
    oldm = {keyf(r): r for r in old}
    L = ["# Item 1: Table 10 (tab:rate) tandem rows, cradle spacing 110 → 115 m\n", "L = 12 h, G = 24 h, first come first served; \"best\" = for each (S, K) the one of cradle and mixed lifting with more lifts; drive-in (the tandem rows of manuscript Table 10) and roadside side by side.\n",
         "| Tandem variant | Scenario | Cradles | Lifts / cradle (K = 1) | Second group ≈ cradles | K = 1 / K = 2 (S = 1) | Lifts / cradle (plateau) | Plateau S = 1 → 6 |", "|---|---|---|---|---|---|---|---|"]
    LZ = dict(tandem_all="all reachable", **{f"tandem_{rc}{d_}": f"S_r = {rc[0]}, t_sh = {int(rc[2:]) / 3600:g} h, {z}" for rc in ("1_3600", "2_1800", "2_3600", "2_7200")
                                       for d_, z in (("", "earliest lift start"), ("|finish", "by lift finish time"), ("|prestage", "far cradles prestage only"), ("|best", "best of the three"))})
    ch = []
    for r in new_t:
        if r["layout"] == "side" or r["lift"] != "best":
            continue
        o = oldm[keyf(r)]
        cell = lambda c: o[c] if o[c] == r[c] else f"{o[c]} → **{r[c]}**"
        if any(o[c] != r[c] for c in ("per_cradle_K1", "second_set", "n11", "n12", "per_cradle_plat", "n1_10", "n6_10")):
            ch.append(keyf(r))
        L.append(f"| {LZ[r['layout']]} | {SCEN_ZH[r['scen']]} | {MODE_ZH[r['mode']]} | {cell('per_cradle_K1')} | {cell('second_set')} | {cell('n11')} / {cell('n12')} | "
                 f"{cell('per_cradle_plat')} | {cell('n1_10')} → {cell('n6_10')} |")
    L.append(f"\nChanged rows (best lifting): {len(ch)} / {sum(1 for r in new_t if r['layout'] != 'side' and r['lift'] == 'best')}.")
    md(out, "rate.md", L)
    shutil.rmtree(d)
    N["rate"] = dict(changed=["|".join(k) for k in ch], tab=[r for r in new_t if r["layout"] != "side"])


# ================================================================ item 1: Table 12
def cd_points(K):
    P = {}
    for r in rd(K["cd"] / "points.csv"):
        P[(int(r["cd"]), int(r["n_v"]), r["rc"], r.get("disp") or "start", r.get("blk") or "")] = r
    return P


def cd_src(D, items, blk, rule, P, rc="main"):
    """Sources of the design analyses (IR.cd_sources) with tandem S ≥ 2 replaced by the 115 m points: rc = main (S_r = 1,
    t_sh = 1 h, berth-picking rule chosen by rule) or all (all reachable)."""
    src = IR.cd_sources(D, items, blk, rule)
    for (i, n, reach), r in list(src.items()):
        x = items[i]
        if x["lay"] != "tandem" or x["S"] < 2:
            continue
        b = blk if x["scen"] == "lane" else ""
        if rc == "all":
            q = P[(i, n, "all", "start", b)]
        else:
            st, fi = P[(i, n, "main", "start", b)], P[(i, n, "main", "finish", b)]
            q = {"start": st, "finish": fi}.get(rule) or (fi if fl(fi["port_h"]) <= fl(st["port_h"]) + 1e-9 else st)
        src[(i, n, reach)] = dict(q, _blk=b, reach=reach)
    return src


def rent_rows(rows, g, with_G=False):
    """Rent charged for port days only (⌈T/24⌉ days, at least 1 day): fleet_eur and cost_*k recomputed. with_G: configurations
    with S ≥ 1 also pay the G = 24 h of cradle loading before the window (⌈(T + G)/24⌉ days)."""
    out = []
    for r in rows:
        days = max(1, math.ceil((r["port_h"] + (g["G"] if with_G and r["S"] >= 1 else 0)) / 24 - 1e-9))
        fleet = r["K"] * g["set_day"] * days
        x = dict(r, fleet_eur=fleet)
        for rate in g["rates"]:
            x[f"cost_{rate // 1000}k"] = r[f"vessel_{rate // 1000}k"] + fleet + r["cradle_eur"]
        out.append(x)
    return out


def codesign(D, K, out, N):
    import windport_spatial_analytic as AA
    import windport_design as X
    g = AA.GRIDS["codesign"]
    items = X.cd_items()
    lst = {r["cfg"]: fl(r["lstar_h"]) for r in rd(IR.MAIN2["codesign"] / "codesign.csv")}
    P = cd_points(K)
    var = {(b, rule): IR.cd_rows(cd_src(D, items, b, rule, P), items, g, lst) for b in ("75", "150", "300") for rule in ("best", "finish")}
    rows = var[("150", "best")]
    rows_all = IR.cd_rows(cd_src(D, items, "150", "best", P, "all"), items, g, lst)
    old_rows = IR.cd_rows(IR.cd_sources(D, items, "150", "best"), items, g, lst)
    wcsv(out / "codesign.csv", rows)
    res, res_old, res_all = IR.cd_best(rows, g), IR.cd_best(old_rows, g), IR.cd_best(rows_all, g)
    res_rent, res_rent_old = IR.cd_best(rent_rows(rows, g), g), IR.cd_best(rent_rows(old_rows, g), g)
    wcsv(out / "codesign_best.csv", res)
    wv, wc = IR.cd_widen(rows)
    _, wc_old = IR.cd_widen(old_rows)
    key = lambda x: (x["scen"], x["n_v"], x["rate"])
    O, A_, RT, RTO = ({key(x): x for x in r} for r in (res_old, res_all, res_rent, res_rent_old))
    L = ["# Item 1: Table 12 (tab:codesign) co-design, cradle spacing of tandem S ≥ 2 110 → 115 m\n",
         "Tandem S ≥ 2 main variant: crane reach S_r = 1, far cradles t_sh = 1 h per pile (same as the side-by-side main variant of Table 10; already in cd_configs), the berth-picking rule is a design variable (each configuration takes the faster of the two rules); "
         "all reachable is the optimistic reference. Long single-lane access uniformly uses 150 m block sections. Other configurations (S ≤ 1, side by side) are reused from the design analyses (the 768 points with S ≤ 1 are identical field by field at 115 m, see recheck.md).\n",
         "| Scenario | Per vessel | Day rate | Cost-optimal (€/voyage) | No-upgrade optimum: 110 m → 115 m | Gate holding place / passing place / widening / both: saving (110 → 115 m) | Optimum with tandem all reachable | Extra cost of the L* first choice |",
         "|---|---:|---|---|---|---|---|---:|"]
    for t in res:
        o, a = O[key(t)], A_[key(t)]
        sv = lambda k: f"{o[k + '_save']:,} → **{t[k + '_save']:,}**" if o[k + "_save"] != t[k + "_save"] else f"{t[k + '_save']:,}"
        L.append(f"| {SCEN_ZH.get(t['scen'], t['scen'])} | {t['n_v']} | {t['rate'] // 1000}k | {t['opt']} ({t['opt_infra']}); {t['opt_cost']:,}"
                 + ("" if o["opt_cost"] == t["opt_cost"] else f" (110 m: {o['opt_cost']:,})") +
                 f" | {o['plain_cfg']}; {o['plain_cost']:,} → **{t['plain_cfg']}; {t['plain_cost']:,}** | " + " / ".join(sv(k) for k in ("hold", "pass_", "widen", "pass_widen")) +
                 f" | {a['opt']}; {a['opt_cost']:,} | {t['lstar_pick_extra']:,} |")
    L.append(f"\nWidening vs passing place (long single lane, 10 piles per vessel, no gate holding place, same configuration): faster / same / slower = {wc_old['faster']} / {wc_old['same']} / {wc_old['slower']} (110 m) → "
             f"**{wc['faster']} / {wc['same']} / {wc['slower']}** ({wc['slower_by'] or '-'}); widening at the lower bound {wc_old['at_lb']} → {wc['at_lb']} groups.")
    # block-length sensitivity (115 m)
    L += ["\n## Block-length sensitivity (115 m; berth-picking rule of the main variant)\n", "| Block length | Day rate | 10 piles per vessel: cost-optimal | No-upgrade optimum | Gate holding place / passing place / widening / both: saving | Widening vs passing place |", "|---:|---|---|---|---|---|"]
    sens = {}
    for b in ("75", "150", "300"):
        rs = IR.cd_best(var[(b, "best")], g)
        _, wcb = IR.cd_widen(var[(b, "best")])
        sens[b] = dict(best=[x for x in rs if x["scen"] == "lane"], widen=wcb)
        for t in (x for x in rs if x["scen"] == "lane" and x["n_v"] == 10):
            L.append(f"| {b} m | {t['rate'] // 1000}k | {t['opt']} ({t['opt_infra']}); {t['opt_cost']:,} | {t['plain_cfg']}; {t['plain_cost']:,} | "
                     f"{t['hold_save']:,} / {t['pass__save']:,} / {t['widen_save']:,} / {t['pass_widen_save']:,} | {wcb['faster']} / {wcb['same']} / {wcb['slower']} |")
    bd = {}
    m150 = {(r["i"], r["n_v"], r["reach"]): r for r in var[("150", "best")] if r["scen"] == "lane"}
    for b in ("75", "300"):
        dd = [(r["port_h"] - m150[(r["i"], r["n_v"], r["reach"])]["port_h"], r) for r in var[(b, "best")] if r["scen"] == "lane"]
        dd = [(x, r) for x, r in dd if abs(x) > 1e-6]
        bd[f"best_{b}"] = dict(n=len(dd), shorter=sum(1 for x, _ in dd if x < 0), longer=sum(1 for x, _ in dd if x > 0), max_abs=round(max((abs(x) for x, _ in dd), default=0.0), 3),
                               lstar_diff=sum(1 for r in var[(b, "best")] if r["scen"] == "lane" and abs(r["lstar_h"] - m150[(r["i"], r["n_v"], r["reach"])]["lstar_h"]) > 1e-9))
    L.append("\nPort-time difference caused by block length (long single lane, point by point against 150 m): " + "; ".join(f"{k}: {v}" for k, v in bd.items()))
    # size of the change of tandem S ≥ 2 at 115 m (main variant, same configuration)
    dif = []
    news = cd_src(D, items, "150", "best", P)
    olds = IR.cd_sources(D, items, "150", "best")
    for k in news:
        x = items[k[0]]
        if x["lay"] == "tandem" and x["S"] >= 2:
            dif.append(fl(news[k]["port_h"]) - fl(olds[k]["port_h"]))
    L.append(f"\n{len(dif)} tandem S ≥ 2 points (main variant): port time 115 m minus 110 m, mean {sum(dif) / len(dif):+.3f} h, max {max(dif):+.2f} h, min {min(dif):+.2f} h; "
             f"slower {sum(1 for x in dif if x > 1e-6)}, same {sum(1 for x in dif if abs(x) <= 1e-6)}, faster {sum(1 for x in dif if x < -1e-6)}.")
    md(out, "codesign.md", L)
    N["codesign"] = dict(best=res, widen=wc, n_rows=len(rows), check_bad=sum(1 for r in rows if str(r["check_ok"]) not in ("1", "True")),
                         below_lstar=sum(1 for r in rows if r["port_h"] < r["lstar_h"] - 1e-9))
    N["codesign_widen_cmp"] = wc
    N["codesign_sens"] = sens
    N["codesign_blockdiff"] = bd
    N["codesign_all"] = res_all
    N["codesign_serial_diff"] = dict(n=len(dif), mean=round(sum(dif) / len(dif), 4), max=round(max(dif), 3), min=round(min(dif), 3),
                                     slower=sum(1 for x in dif if x > 1e-6), same=sum(1 for x in dif if abs(x) <= 1e-6), faster=sum(1 for x in dif if x < -1e-6))
    # supplementary table tab_cddisp (codesign_disp in numbers.json): lift-finish rule vs earliest lift start, tandem S ≥ 2 uses
    # the 115 m start / finish points
    st, fi = cd_src(D, items, "150", "start", P), cd_src(D, items, "150", "finish", P)
    acc = collections.defaultdict(lambda: dict(faster=0, same=0, slower=0, d_slow=[], d_fast=[]))
    for k in st:
        x = items[k[0]]
        if not IR.cd_dep(x, k[2]):
            continue
        dd = fl(fi[k]["port_h"]) - fl(st[k]["port_h"])
        c = acc[(x["scen"], x["lay"], "K = 1" if x["K"] == 1 else "K ≥ 2")]
        c["faster" if dd < -1e-6 else "slower" if dd > 1e-6 else "same"] += 1
        (c["d_slow"] if dd > 1e-6 else c["d_fast"] if dd < -1e-6 else []).append(dd)
    de = {"|".join(k): dict(faster=v["faster"], same=v["same"], slower=v["slower"], slow_mean=round(sum(v["d_slow"]) / len(v["d_slow"]), 2) if v["d_slow"] else None,
                            slow_max=round(max(v["d_slow"]), 2) if v["d_slow"] else None, fast_mean=round(sum(v["d_fast"]) / len(v["d_fast"]), 2) if v["d_fast"] else None)
          for k, v in sorted(acc.items())}
    old_de = json.loads((I_REP / "numbers.json").read_text(encoding="utf-8"))["codesign_disp"]
    N["codesign_disp"] = de
    N["codesign_disp_changed"] = {k: dict(old=old_de.get(k), new=v) for k, v in de.items() if old_de.get(k) != v}
    rr = IR.cd_best(rent_rows(rows, g, with_G=True), g)
    N["rent_G"] = [dict(scen=t["scen"], n_v=t["n_v"], rate=t["rate"], opt=t["opt"], plain=t["plain_cfg"], widen_save=t["widen_save"], pass_save=t["pass__save"],
                        hold_save=t["hold_save"]) for t in rr]
    econ(res, RT, RTO, O, out, N, g)


def econ(res, RT, RTO, O, out, N, g):
    """Item 6: two rent conventions, investment and payback, passing-place vs widening ratio, campaign share."""
    key = lambda x: (x["scen"], x["n_v"], x["rate"])
    L = ["# Item 6: economics (long single lane, 10 piles per vessel; 115 m main variant)\n", "## 6.1 Two rent conventions\n",
         "Continuous rent: K × 7,200 €/day × 6 days (current convention of Table 12); port days only: K × 7,200 €/day × ⌈T/24⌉ days (at least 1 day). Otherwise as Table 12.\n",
         "| Scenario | Per vessel | Day rate | Continuous rent: cost-optimal; no-upgrade optimum | Port days only: cost-optimal; no-upgrade optimum | Port days only: widening / passing place / gate holding place saving |", "|---|---:|---|---|---|---|"]
    for t in res:
        r_ = RT[key(t)]
        L.append(f"| {SCEN_ZH.get(t['scen'], t['scen'])} | {t['n_v']} | {t['rate'] // 1000}k | {t['opt']} ({t['opt_infra']}); {t['plain_cfg']} | "
                 f"{r_['opt']} ({r_['opt_infra']}); {r_['plain_cfg']} |{r_['widen_save']:,} / {r_['pass__save']:,} / {r_['hold_save']:,} |")
    same = sum(1 for t in res if RT[key(t)]["opt"].split(", T")[0] == t["opt"].split(", T")[0])
    L.append(f"\nCells with the same cost-optimal configuration under both rent conventions: {same} / {len(res)}.")
    RG = {key(t): t for t in N["rent_G"]}
    sameG = sum(1 for t in res if RG[key(t)]["opt"].split(", T")[0] == t["opt"].split(", T")[0])
    ln = [RG[k] for k in sorted(RG) if k[0] == "lane" and k[1] == 10]
    L.append(f"Port-day convention plus the G = 24 h of cradle loading before the window (only for configurations with S ≥ 1, ⌈(T + G)/24⌉ days): cells with the same optimum as continuous rent {sameG} / {len(res)}; "
             + "; ".join(f"long single lane, 10 piles per vessel, {t['rate'] // 1000}k: optimum {t['opt']}, widening / passing place / gate holding place saving {t['widen_save']:,} / {t['pass_save']:,} / {t['hold_save']:,} €" for t in ln) + ".")
    N["rent_G_same"] = sameG
    # 6.2 investment, payback, ratio
    area = dict(widen=LANE_M * (WIDEN_W - LANE_W), pass_=PP_M * (WIDEN_W - LANE_W), hold=HOLD_AREA, pass_widen=LANE_M * (WIDEN_W - LANE_W))
    L += ["\n## 6.2 Upgrade investment, break-even and payback\n",
          f"New pavement: widening {LANE_M:,.0f} m × {WIDEN_W - LANE_W:.0f} m = {area['widen']:,.0f} m²; passing place {PP_M:.0f} m × {WIDEN_W - LANE_W:.0f} m = {area['pass_']:,.0f} m²"
          f" (= {area['pass_'] / area['widen']:.3f} of widening, i.e. 1/{area['widen'] / area['pass_']:.0f}); gate holding place taken as the stop of one loaded vehicle group (L_v + 2δ)(d_m + 2c_lat) = {area['hold']:,.0f} m² (assumed). "
          f"Public anchor for the unit cost of heavy-duty pavement: {PAVE['src']}, i.e. {PAVE_M2:.1f} $/m² ({PAVE['url']}; surface and base course only, no ground improvement, rough conversion 1 € ≈ 1 $). "
          "Break-even unit cost = saving per voyage × 10 voyages / new area; payback voyages = ⌈area × unit cost / saving per voyage⌉.\n",
          "| Rent | Day rate | Upgrade | Saving per voyage € | New area m² | Break-even unit cost over 10 voyages €/m² | Investment at anchor cost € | Payback voyages |", "|---|---|---|---:|---:|---:|---:|---:|"]
    inv = []
    for tag, src in (("continuous", {key(t): t for t in res}), ("port days", RT)):
        for t in (x for x in src.values() if x["scen"] == "lane" and x["n_v"] == 10):
            for k, z in (("pass_", "passing place"), ("widen", "widening to 16 m"), ("hold", "gate holding place")):
                s = t[f"{k}_save"]
                cap = area[k] * PAVE_M2
                n = math.ceil(cap / s) if s > 0 else None
                inv.append(dict(rent=tag, rate=t["rate"], infra=k, save=s, area=area[k], breakeven=round(10 * s / area[k], 1), invest=round(cap), payback=n))
                L.append(f"| {tag} | {t['rate'] // 1000}k | {z} | {s:,} | {area[k]:,.0f} | {10 * s / area[k]:,.1f} | {cap:,.0f} | {n if n else '-'} |")
    lane = [t for t in res if t["scen"] == "lane" and t["n_v"] == 10]
    ratio = [t["pass__save"] / t["widen_save"] for t in lane if t["widen_save"]]
    L.append(f"\nThe passing place obtains {min(ratio) * 100:.1f}-{max(ratio) * 100:.1f}% of the widening saving with 1/{area['widen'] / area['pass_']:.0f} of the new pavement.")
    # 6.3 campaign share
    cg = [r for r in md_rows(I_REP / "campaign.md") if r["Scenario"] == "lane" and r["n_v"] == "10" and r["K"] == "2"]
    camp = []
    for r in cg:
        dd = float(r["Difference: mean (P10–P90)"].split(" (")[0])
        fx = float(r["Campaign days: road occupancy / fixed duration"].split(" / ")[1])
        camp.append(dict(q=r["q"], diff_d=dd, campaign_fixed_d=fx, pct=round(100 * dd / fx, 2)))
    L += ["\n## 6.3 Campaign extension as a share of campaign duration (long single lane, two vehicle groups, 10 piles per vessel; recomputed in the design analyses, seeds 1-200, campaign model unchanged)\n", "| q | Extension (days) | Campaign days (fixed duration) | Share |", "|---|---:|---:|---:|"]
    L += [f"| {c['q']} | {c['diff_d']:.3f} | {c['campaign_fixed_d']:.3f} | {c['pct']:.2f}% |" for c in camp]
    md(out, "econ.md", L)
    N["econ"] = dict(rent_same=same, invest=inv, pass_ratio=[round(min(ratio), 4), round(max(ratio), 4)], area=area, pave_usd_m2=round(PAVE_M2, 2), campaign=camp,
                     rent=[dict(scen=t["scen"], n_v=t["n_v"], rate=t["rate"], opt=t["opt"], plain=t["plain_cfg"], widen_save=t["widen_save"], pass_save=t["pass__save"])
                           for t in RT.values()])


def md_rows(p):
    """First pipe table of a markdown file."""
    lines = p.read_text(encoding="utf-8").splitlines()
    out = []
    for k, ln in enumerate(lines):
        if ln.startswith("| Scenario |"):
            cols = [c.strip() for c in ln.strip("|").split("|")]
            for x in lines[k + 2:]:
                if not x.startswith("|"):
                    break
                out.append(dict(zip(cols, [c.strip() for c in x.strip("|").split("|")])))
            break
    return out


# ================================================================ item 2: near-yard buffer
def buffer(K, out, N):
    import windport_design_lib as L_
    plans = json.loads((K["plans"] / "plans.json").read_text(encoding="utf-8"))
    near = {(r["site"], r["scen"], r["mode"], r["K"], r["lv"], r["G"]): r for r in rd(K["bnear"] / "points.csv")}
    tr = {(r["site"], r["scen"], r["K"], r["lv"], r["ban"]): r for r in rd(K["btr"] / "points.csv")}
    mul = {(r["mode"], r["K"], r["hold"], r["lv"]): r for r in rd(K["bmulti"] / "points.csv")}
    alt = rd(K["bturn"] / "turn_alt.csv")
    import windport_revision_buffer as B
    L = ["# Item 2: feasibility of the near-yard buffer (one-voyage storage area of two-level storage)\n",
         f"Storage slot: monopile {B.LV:.0f} × {B.DM} m, row pitch {B.PITCH:.2f} m (d_m + w_e + c_lat), {B.DELTA:.0f} m gap between piles in a row; obstacles (buildings, water) 1 m clearance; "
         f"0.5 m grid. Access: family A rows parallel to the road, crab in and out, last in first out; family B rows perpendicular, turn 90° in place on the road centre line then enter end-on (reference). Numbers only, no figure.\n",
         "## 2.1 Piles per yard zone\n", "| Yard | Yard zone | Area m² | Pure packing bound (ignoring access) | Family A: crab access | Rows | Frontage line (width m, straight length m) | Family B: end-on entry feasible (only this slot in the zone / all others occupied) |",
         "|---|---|---:|---:|---:|---:|---|---|"]
    fb = {}
    for s in ("okpo", "yantai"):
        for z in plans[s]["zones"]:
            W = B.World(s, z["zone"])
            lns = B.frontage_lines(W)
            bb = [B.family_b(W, ln) for ln in lns]
            fb[(s, z["zone"])] = dict(slots=max(b["slots"] for b in bb), alone=max(b["alone"] for b in bb), full=max(b["full"] for b in bb))
            L.append(f"| {SITE_ZH[s]} | {z['zone']} | {z['area_m2']:,} | {z['pure']} | **{z['slots']}** | {z['rows']} | {z['line']}"
                     + (f" and opposite side {z['opp']}" if z["opp"] else "") + f" ({z['road_w']:g}, {z['line_len_m']:g}) | "
                     f"{fb[(s, z['zone'])]['slots']} slots: {fb[(s, z['zone'])]['alone']} / {fb[(s, z['zone'])]['full']} |")
    L += ["\n## 2.2 Chosen layout (10 piles per voyage)\n", "| Yard | Columns (yard zone, frontage, slots in the column) | Total slots | Quay cradle S = 1 preloaded | Piles per voyage | Farthest crab m | Extra per pickup (switch 30 / 300 s, 2.5 km/h) |",
          "|---|---|---:|---:|---:|---:|---|"]
    sch = {}
    for s in ("okpo", "yantai"):
        p = plans[s]
        cols = "; ".join(f"{c['zone']} {c['road']} {c['slots']} slots" for c in p["columns"])
        ex = [B.crab_extra(p, 2.5 / 3.6, 5.0 / 3.6, t) for t in B.TSW]
        L.append(f"| {SITE_ZH[s]} | {cols} | {p['slots']} | 1 | {min(10, p['slots'] + 1)} | {max(c['crab_max_m'] for c in p['columns']):.1f} | {ex[0] / 60:.1f} / {ex[1] / 60:.1f} min |")
        sch[s] = dict(rows=sum(z["rows"] or 0 for z in p["zones"]), columns=len(p["columns"]), slots=p["slots"], row_len_m=B.LV, pitch_m=round(B.PITCH, 2), gap_m=B.DELTA,
                      first_row_offset_m=min(min(c["crabs"]) for c in p["columns"]), entry="drive in parallel along the frontage, crab into the slot; last in first out", turn_area_m="no turning inside the zone; end-on entry needs a turning area of radius 55.2 m",
                      road_w_m=[z["road_w"] for z in p["zones"]], zones=len(p["zones"]))
    L.append("\nFamily B (end-on entry) is almost never feasible at either yard: turning in place sweeps a circle of radius about 55 m that hits buildings or neighbouring slots (with all other slots occupied, at most 1 slot is reachable over both yards); so near-yard rows must run parallel to the frontage with crab access.")
    # 2.3 turns after the layout
    L += ["\n## 2.3 Turns of the loaded route after the layout (1 m clearance; Okpo route with node_trace_016 banned)\n", "| Yard | Route | Turns failing the sector test | Early reorientation | Reverse or crab | No space |", "|---|---|---:|---:|---:|---:|"]
    VZ = dict(near="near yard → quay", transfer="far yard → near yard (transfer)", transfer_ban="transfer, node_trace_016 banned", multi_ban="three-voyage direct loading, node_trace_016 banned")
    tc = {}
    for s in ("okpo", "yantai"):
        for v in ("near", "transfer", "transfer_ban", "multi_ban"):
            rs = [r for r in alt if r["site"] == s and r["var"] == v and r["bad"] == "1"]
            if not rs and not any(r["site"] == s and r["var"] == v for r in alt):
                continue
            c = collections.Counter(r["cls"] for r in rs)
            tc[f"{s}|{v}"] = dict(c)
            L.append(f"| {SITE_ZH[s]} | {VZ[v]} | {len(rs)} | {c.get('early re-orientation', 0)} | {c.get('reversing or crab steering', 0)} | {c.get('no space (operator to confirm)', 0)} |")
    # 2.4 window
    LZ = dict(feas="all turns feasible, switch 30 s", hi="turns hi, switch 300 s (main variant)")
    old_kw = json.loads((I_REP / "numbers.json").read_text(encoding="utf-8"))["twolevel"]["kwin"]
    L += ["\n## 2.4 Near-yard window under the layout (G = 24 h, S = 1; slower of the two cradle modes; FCFS; in parentheses: the frontage stop-point model of the design analyses; L″* is the certified lower bound for the same points)\n",
          "| Yard | Scenario | Variant | K = 1 | 2 | 3 | 4 | Smallest K back to 10.00 h (FCFS) | L″* (K ≥ 2) |", "|---|---|---|---|---|---|---|---:|---:|"]
    kwin, wtab = {}, []
    for s, sc, lv in itertools.product(("okpo", "yantai"), ("base", "slow"), ("feas", "hi")):
        v = {k: max(fl(near[(s, sc, m, str(k), lv, "24")]["port_h"]) for m in T.MODES) for k in range(1, 9)}
        lb = {k: min(fl(near[(s, sc, m, str(k), lv, "24")]["lstar_lo"]) for m in T.MODES) for k in range(1, 9)}
        k10 = next((k for k in range(1, 9) if v[k] <= 10.0 + 1e-6), None)
        kwin[f"{s}|{sc}|{lv}"] = k10
        wtab.append(dict(site=s, scen=sc, lv=lv, **{f"K{k}": round(v[k], 3) for k in range(1, 9)}, **{f"L{k}": round(lb[k], 3) for k in range(1, 9)}, k10=k10))
        L.append(f"| {SITE_ZH[s]} | {SCEN_ZH[sc]} | {LZ[lv]} | " + " | ".join(f"{v[k]:.2f}" for k in range(1, 5)) +
                 f" | {k10 if k10 else '> 8'} ({old_kw.get(f'{s}|{sc}|{lv}')}) | {max(lb[k] for k in range(2, 9)):.2f} |")
    # 2.5 voyage cycle
    ret = {s: IR.return_leg(s) for s in ("okpo", "yantai")}
    L.append("\n(Okpo 1 km/h, turns hi, switch 300 s: FCFS is still > 10.00 h at K = 8 while the certified lower bound is L″* = 10.00 h - the bound does not exclude 10.00 h; the gap comes from FCFS picking piles on demand from a single column in series. "
             "Table 6 reads \"> 8 (FCFS); L″* = 10.00 h\".)")
    L += ["\n## 2.5 Voyage cycle T_seq (transfer of 10 piles to the layout columns + return leg + near-yard window from an empty system; h) and rule-free lower bound T_seq*\n",
          "| Yard | Scenario | Variant | Route | K = 1 | 2 | 3 | 4 | 8 |", "|---|---|---|---|---|---|---|---|---|"]
    tseq = {}
    old_tm = json.loads((I_REP / "numbers.json").read_text(encoding="utf-8"))["twolevel"]["tmin"]
    for s, sc, lv in itertools.product(("okpo", "yantai"), ("base", "slow"), ("feas", "hi")):
        for ban in (["0", "1"] if s == "okpo" else ["0"]):
            cells = []
            for k in (1, 2, 3, 4, 8):
                t = tr[(s, sc, str(k), lv, ban)]
                w0 = [near[(s, sc, m, str(k), lv, "0")] for m in T.MODES]
                ts = fl(t["port_h"]) + ret[s][1] + min(fl(r["port_h"]) for r in w0)
                tl = fl(t["lstar_lo"]) + ret[s][1] + min(fl(r["lstar_lo"]) for r in w0)
                tseq[f"{s}|{sc}|{lv}|{ban}|{k}"] = dict(T_seq=round(ts, 3), T_seq_lb=round(tl, 3), tr=fl(t["port_h"]), win0=min(fl(r["port_h"]) for r in w0))
                cells.append(f"{tl:.1f} / **{ts:.1f}**")
            L.append(f"| {SITE_ZH[s]} | {SCEN_ZH[sc]} | {LZ[lv]} | {'node_trace_016 banned' if ban == '1' else 'original route'} | " + " | ".join(cells) + " |")
    L.append("\nEach cell: T_seq* / **T_seq**. Design analyses (frontage stop-point model, original route, hi, K = 2): Okpo "
             f"{old_tm['okpo|base|S1|2']['T_seq_hi']:.1f} / 1 km/h {old_tm['okpo|slow|S1|2']['T_seq_hi']:.1f} h, Yantai {old_tm['yantai|base|S1|2']['T_seq_hi']:.1f} / {old_tm['yantai|slow|S1|2']['T_seq_hi']:.1f} h. "
             "6-day voyage cycle = 144 h.")
    # 2.6 three-voyage single-level direct loading, node_trace_016 banned
    old_y = {"0": 22.14, "1": None}
    L += ["\n## 2.6 Okpo three-voyage single-level direct loading (S = 1, base) with node_trace_016 banned (shortest over K = 2-8)\n", "| Q_h | Cradle | lo | hi | Design analyses (original route, node_trace_016 as in the previous version) lo / hi |", "|---|---|---|---|---|"]
    mtab = []
    y3 = {(r["site"], r["mode"], r["hold"]): r for r in rd(I_REP / "compat" / "yards.csv")} if (I_REP / "compat" / "yards.csv").exists() else {}
    for h in ("0", "1"):
        for m in T.MODES:
            v = {lv: min(fl(mul[(m, str(k), h, lv)]["port_h"]) for k in range(2, 9)) for lv in ("lo", "hi")}
            mtab.append(dict(hold=h, mode=m, **v))
            L.append(f"| {h} | {MODE_ZH[m]} | {v['lo']:.2f} | {v['hi']:.2f} | see table tab_yards3 of the design analyses |")
    md(out, "buffer.md", L)
    N["buffer"] = dict(plans={s: dict(slots=plans[s]["slots"], columns=[{k: c[k] for k in ("zone", "road", "slots", "crab_max_m")} for c in plans[s]["columns"]],
                                      zones=plans[s]["zones"]) for s in plans}, famb=fb and {f"{a}|{b}": v for (a, b), v in fb.items()}, schematic=sch,
                       turns=tc, kwin=kwin, window=wtab, tseq=tseq, multi=mtab, ret={s: round(ret[s][1], 4) for s in ret})


# ================================================================ items 3, 5, 4 (analytic)
def stage(K, out, N):
    rs = rd(K["analytic"] / "stage.csv")
    L = ["# Item 3: smallest pre-window staging σ* that neutralises the road (window form of W″_lift: smallest S with every road term ≥ I = ⌊L/p⌋; K = 8, q = min(K, Q) loaded vehicles can wait on the quay side, already in W″)\n",
         "σ_rate = ⌈L/p − (L − p)/τ_cut⌉ − q (integer form of the rate condition S + β < L/p − (L − p)/τ_cut, with β = q), τ_cut = t_ℓ + t_e is the occupancy of one cycle on the cut used by W″. "
         "σ* ≤ 1 is written as 1 (cradle mode has at least one cradle). σ* is a necessary condition: the quay side needs at least σ* piles, otherwise the road enters the window (any admissible schedule); σ* piles do not guarantee the crane bound. "
         "σ* uses Q of the given geometry and counts the piles beyond the cut, whether or not within crane reach.\n",
         "| Case | Cradle | Speed | L (h) | I | τ_cut/p | q | **σ\\* (W″)** | σ_rate | Raw rate value | Binding road term with too little staging |", "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in rs:
        L.append(f"| {r['case']} | {MODE_ZH[r['mode']]} | {SPEED_ZH[r['speed']]} | {r['L_h']} | {r['I']} | {r['tau_cut_p']} | {r['q']} | **{r['sigma'] or '> I'}** | "
                 f"{r['sigma_rate']} | {r['rate_raw']} | {r['binding_below'] or '-'} |")
    md(out, "stage.md", L)
    N["stage"] = rs


def rated(K, out, N):
    rs = rd(K["analytic"] / "rated.csv")
    L = ["# Item 5: certified port-time lower bound L″*(10) at rated speeds (h; W″_lift, minimum over K ≤ 8) and critical speed v*\n",
         "Rated: Scheuerle 6-axle-line SPMT 210.12.4 G4 data sheet (2015-10-13, 49500002_S02, p. 2) 'Admissible travel speed / axle line load': TT20 / TL24 tyres 27 t @ 10 km/h, 30 t @ 5 km/h, "
         "32 t @ 3 km/h, 40 t @ 1 km/h, unloaded 11.5 km/h (parameter registry spmt_axle_load_vs_speed_scheuerle, spmt_speed_unloaded; Kamag 2400 unloaded about 5 km/h). "
         "The base monopile of 1,500 t on 80 axle lines (Eemshaven public figure) gives about 18.75 t per axle line plus about 4 t self weight, below 27 t, so the rated loaded speed is 10 km/h; above 2,000 t, with 27-30 t per axle line, 5 km/h. "
         "The bound uses only speed upper limits and duration lower limits, so a bound computed at rated speeds holds for any operation of that vehicle. v*: below loaded speed v* the certified lower bound exceeds the crane bound 10.00 h (unloaded 5 km/h, minimum over K ≤ 8). "
         "The two-level row uses the main near-yard layout of item 2 (piles picked by column, each pickup adds the farthest-slot crab and 4 mode switches of 300 s; windport_revision_r1_rated), "
         "the main variant also adds the alternative-turn durations of bturn (the 1 km/h set at 1 km/h, the 2.5 km/h set at 2.5 km/h and at rated speeds), with an extra row for all turns feasible and switch 30 s; the v* bisection adds no alternative-turn time.\n",
         "| Case | Cradle | 1 km/h | 2.5 km/h | Rated 5 / 11.5 | Rated 10 / 11.5 | v* (km/h; unloaded 5 km/h, K ≤ 8) |", "|---|---|---:|---:|---:|---:|---:|"]
    r2 = rd(K["r1_rated"] / "rated2.csv")
    for r in rs:
        if r["obj"].endswith("|cycle") or r["obj"].endswith("|runs"):
            continue
        L.append(f"| {r['case']} | {MODE_ZH.get(r['mode'], r['mode'])} | {r['L_v1']} | {r['L_v25']} | {r['L_r5']} | {r['L_r10']} | {r['v_crit']} |")
    LV = dict(hi="turns hi, switch 300 s (main variant)", feas="all turns feasible, switch 30 s")
    for r in r2:
        if r["mode"] == "cycle":
            continue
        L.append(f"| {r['site']} two-level: near-yard window (layout, {LV[r['level']]}) | {MODE_ZH.get(r['mode'], r['mode'])} | {r['L_v1']} | {r['L_v25']} | {r['L_r5']} | {r['L_r10']} | {r['v_crit']} |")
    L += ["\nVoyage cycle of two-level storage (K = 2): T_rate / T_seq* (h; main near-yard layout, transfer drop-off adds the crab)\n", "| Yard | Variant | 1 km/h | 2.5 km/h | Rated 5 / 11.5 | Rated 10 / 11.5 |", "|---|---|---|---|---|---|"]
    for r in r2:
        if r["mode"] == "cycle":
            L.append(f"| {r['site']} | {LV[r['level']]} | " + " | ".join(f"{r[f'Trate_{s}']} / {r[f'Tseq_lb_{s}']}" for s in ("v1", "v25", "r5", "r10")) + " |")
    L += ["\nStaging criterion σ* of the two-level window (layout, K = 8): " + "; ".join(f"{r['site']} {LV[r['level']]} {MODE_ZH.get(r['mode'], r['mode'])}: "
                                                          + " / ".join(f"{SPEED_ZH[s]} {r[f'sigma_{s}']}" for s in ("v1", "v25", "r5", "r10"))
                                                          for r in r2 if r["mode"] != "cycle") + "."]
    old_cycle = [r for r in rs if r["obj"].endswith("|cycle")]
    L += ["\nReference: voyage cycle T_rate / T_seq* (K = 2) with the frontage stop-point model of the design analyses: " + "; ".join(
        f"{r['case']} " + " / ".join(f"{r[f'Trate_{s}']} / {r[f'Tseq_lb_{s}']}" for s in ("v1", "v25", "r5", "r10")) for r in old_cycle) + "."]
    md(out, "rated.md", L)
    N["rated"] = rs
    N["rated2"] = r2


def premise(K, out, N):
    rs = rd(K["analytic"] / "premise.csv")
    L = ["# Item 4: terms of W″_lift that actually enter in the co-design (long single lane, block length 150 m, 10 piles per vessel, L = 10 h; premise check)\n",
         "cut: binding cut (block number @k); chains: number of chains (block chains) of Corollary 3; zc: quay-zone chains of the dead-end coupling of Corollary 7; ll: admissible links of the loaded-only cut; Q: quay-zone capacity (Corollary 4).\n",
         "| K | S | Gate holding place | Passing place | Widening | Cut | Chains | Dead-end coupling | Loaded-only cut | Q | t_ℓ / t_e (s) | Entering terms | W″ | Binding |", "|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---:|---|"]
    for r in rs:
        L.append(f"| {r['K']} | {r['S']} | {r['hold']} | {r['pass_']} | {r['widen']} | {r['cut']} | {r['chains']} | {r['zc']} | {r['ll']} | {r['Q']} | {r['tl_s']} / {r['te_s']} | "
                 f"{r['terms']} | {r['W']} | {r['binding']} |")
    md(out, "premise.md", L)
    N["premise"] = rs


# ================================================================ item 7
def p2(out, N):
    import windport_design as X
    items = X.cd_items()
    base = len(items) * 3
    side2 = sum(1 for x in items if x["lay"] == "side" and x["S"] == 2)
    side3 = sum(1 for x in items if x["lay"] == "side" and x["S"] == 3)
    extra = (side2 * 1 + side3 * 2) * 3
    L = ["# Item 7: small additions\n", "## 7.1 Composition of the 7,680 co-design simulation points\n",
         f"2,176 configurations × n_v = 3, 5, 10 = {base:,}; the {side2} side-by-side S = 2 configurations add one level with distance-reachable S_r = 1, the {side3} S = 3 configurations add two levels S_r = 1, 2 (all reachable is the original level), "
         f"× 3 loads = {extra:,}; total {base + extra:,}. In addition, sensitivity points for the two slot-picking rules of in-line S ≥ 2 and block lengths 75 / 300 m (not counted in the 7,680).\n",
         "## 7.2 Fixed-duration baseline with the literature value\n", "Extra column of Table 8 (the \"1 h per pile\" column of t8.md): single-server model with 1 h per item (windport/bound3.muhabie_port; fixed handling time of Muhabie et al. in the manuscript), independent of the fleet.\n",
         "## 7.3 Basis for modelling the empty platform as one 30 m × 4.86 m unit\n",
         "Parameter registry: SPMT module width 2.43 m (spmt_module_width, Scheuerle / Kamag / Goldhofer ES-E), two side by side 4.86 m; axle spacing 1.4 m (spmt_axle_spacing), 6-axle-line module 8.4 m (spmt_module_length_6axle), "
         "PPU length 4.73 m (spmt_ppu_length). 80 axle lines as two columns of 40 give about 56 m per column; on the empty return, following the Eemshaven and Rønne operations, the empty group can split in halves or be shortened (parameter registry axle_lines_*); "
         "30 m is the length of one column of about 3 six-axle-line modules plus PPU. The empty length only enters the empty-return occupancy (L_e + δ)/v_e: the main case uses 30 m, the sensitivity in Appendix C uses 60 m (extra analyses, sens platlen); "
         "the manuscript states this modelling choice and the sensitivity result; the note of Table 3 reads \"empty vehicles as 2 columns × about 30 m after splitting (4.86 m is the width of two module columns), 60 m in Appendix C\"."]
    md(out, "p2.md", L)
    N["p2"] = dict(cd_points=base + extra, cd_base=base, cd_side_extra=extra, side2=side2, side3=side3)


# ================================================================ recheck
def recheck(K, out, N):
    """New points: checker, simulation ≤ W″_lift (computed now for window-form batches), port time ≥ L″_lift*, per-pile check."""
    import windport_design as X
    import windport_revision_lib as KL
    from windport import bound_all as BA
    X.setup_env()
    KL.install_spacing(115.0)
    tot = collections.Counter()
    L = ["# Recheck of the new points\n", "| Batch | Rows | Checker failures | Simulation > W″_lift | Port time < L″_lift* | W″_lift(T_j) < j (piles / piles checked) |", "|---|---:|---:|---:|---:|---|"]
    for name in ("rate_e4", "rate_mix6"):
        rs = rd(K[name] / "points.csv")
        over = 0
        for r in rs:
            part = "e4" if name == "rate_e4" else "mix6"
            if part == "e4":
                c = T.cfg_of("e4", r["key"])
            else:
                import windport_extra as X6
                c = T.cfg_of("e4", r["key"])
                c["lift"] = "mixed"
            Lw = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * H
            w = BA.w2_lift(c, BA.parts(c, lift=True))(Lw)
            over += int(int(r["sim"]) > w)
        a = dict(n=len(rs), bad=sum(1 for r in rs if r["check_ok"] not in ("1", "True")), over=over, lb=0, viol=0, roots=0)
        tot.update(a)
        L.append(f"| {name} | {a['n']} | {a['bad']} | {a['over']} | - | - |")
    rs = rd(K["rate_reach"] / "points.csv")
    a = dict(n=len(rs), bad=sum(1 for r in rs if r["check_ok"] not in ("1", "True")), over=sum(1 for r in rs if int(r["sim"]) > int(r["w4"])), lb=0, viol=0, roots=0)
    tot.update(a)
    L.append(f"| rate_reach | {a['n']} | {a['bad']} | {a['over']} | - | - |")
    rs = rd(K["t8_port"] / "points.csv")
    lb = sum(1 for r in rs if r["rep"] == "fcfs" and r["port_h"] not in ("", "None") and float(r["port_h"]) < float(r["lstar_w2"]) - 1e-9)
    a = dict(n=len(rs), bad=sum(1 for r in rs if r["check_ok"] not in ("1", "True")), over=0, lb=lb, viol=0, roots=0)
    tot.update(a)
    L.append(f"| t8_port | {a['n']} | {a['bad']} | - | {lb} | - |")
    for name in ("t8_e3", "t8_fix"):
        rs = rd(K[name] / "points.csv")
        a = dict(n=len(rs), bad=sum(1 for r in rs if r["check_ok"] not in ("1", "True")), over=0, lb=0, viol=0, roots=0)
        tot.update(a)
        L.append(f"| {name} | {a['n']} | {a['bad']} | - | - | - |")
    KL.install_spacing(110.0)
    for name in ("cd", "s01", "bnear", "btr", "bmulti"):
        rs = rd(K[name] / "points.csv")
        a = dict(n=len(rs), bad=sum(1 for r in rs if r["check_ok"] not in ("1", "True")), over=0,
                 lb=sum(1 for r in rs if fl(r["port_h"]) is not None and fl(r["port_h"]) < fl(r["lstar_lo"]) - 1e-9),
                 viol=sum(i_(r["viol"]) for r in rs if r.get("viol") not in ("", None, "None")), roots=sum(i_(r["lifts"]) for r in rs if r.get("viol") not in ("", None, "None")))
        tot.update(a)
        L.append(f"| {name} | {a['n']} | {a['bad']} | - | {a['lb']} | {a['viol']} / {a['roots']} |")
    L.append(f"| **Total (110 m points)** | {tot['n']} | {tot['bad']} | {tot['over']} | {tot['lb']} | {tot['viol']} / {tot['roots']} |")
    # the 115 m spacing re-runs: all re-run rows (diff.csv of the spliced directories) and their W″_lift recheck
    rr = r1_rows(K)
    nbad = sum(int(v["check_fail"]) for b, v in N["splice"].items() if v and "check_fail" in v)
    nrec = sum(int(v["recomputed"]) for b, v in N["splice"].items() if v and "recomputed" in v)
    over = sum(int(r["over"] or 0) for r in rr)
    lh = sum(int(r["lstar_hi"] or 0) for r in rr if r["form"] == "port")
    win = sum(1 for r in rr if r["form"] in ("win", "e2"))
    prt = sum(1 for r in rr if r["form"] == "port" and not r.get("skip"))
    L += ["\n## The 115 m spacing re-runs (windport_revision_r1)\n", "| Item | Count |", "|---|---:|",
          f"| Re-run rows (sum of the spliced diff.csv over batches, incl. the 180 E2 S = 2 cases) | {nrec:,} |", f"| Checker failures | {nbad} |",
          f"| Rows rechecked against W″_lift (fixed-duration representation, single-resource cut and fixed-duration groups not checked) | {len(rr):,} (window form {win:,} / port time {prt:,}) |",
          f"| Simulation / CP-SAT > W″_lift | {over} |", f"| L″_lift* > port time | {lh} |"]
    md(out, "recheck.md", L)
    N["recheck"] = dict(tot)
    N["recheck_r1"] = dict(recomputed=nrec, check_fail=nbad, rows=len(rr), win=win, port=prt, over=over, lstar_hi=lh)


# ================================================================ manuscript
def compat_recheck(K, comp):
    """The manuscript reads the recheck rows.csv of the main geometry (mapped by the design analyses to the main2 recheck)
    for the L* column of Table 8: the S3, S3m, n_v = 10 rows of extra:port are replaced by the 115 m port times and the
    L* of W″_lift."""
    src = R / "tables/main2" / "recheck" / "rows.csv"
    new = {r["key"]: r for r in rd(K["t8_port"] / "points.csv")}
    ls = {}
    for r in new.values():
        if r["rep"] == "fcfs":
            ls[(r["scen"], r["mode"], r["arr"], r["K"], r["n_v"], r["hold"])] = r["lstar_w2"]
    lines = src.read_text(encoding="utf-8").splitlines()
    cols = next(csv.reader([lines[0]]))
    out, hit = [], 0
    for r in csv.DictReader(lines):
        if r["batch"] == "extra:port" and r["key"] in new:
            kv = T.dec(r["key"])
            q = new[r["key"]]
            l_ = ls.get((kv["scen"], kv["mode"], kv["arr"], kv["K"], kv["n_v"], kv["hold"]), r["lstar"])
            r = dict(r, port_h=q["port_h"], sim=q.get("lifts", r["sim"]), lstar=str(round(float(l_), 6)))
            hit += 1
        out.append(r)
    with open(comp / "recheck_rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(out)
    return hit


def logged(fn, log):
    """Wrap windport_report_main2.fake_src: log every file the manuscript reads (after src.where and mapping rewrites)."""
    import io
    import windport_report_main2 as HR
    orig = HR.fake_src

    def fake(mapping):
        m = orig(mapping)
        show0 = m.show
        keys = sorted(mapping, key=len, reverse=True)

        def show(path, commit):
            p, c = m.where(path, commit)
            loc = next((mapping[a] + p[len(a):] for a in keys if p == a or p.startswith(a + "/")), None)
            log.append(dict(where=p, commit=c, local=loc))
            return show0(path, commit)
        m.show = show
        m.rows = lambda path, commit: list(csv.DictReader(io.StringIO(show(path, commit))))
        m.js = lambda path, commit: json.loads(show(path, commit))
        return m
    HR.fake_src = fake
    try:
        return fn()
    finally:
        HR.fake_src = orig


def paper(out, comp, made, ra, ho, N, K):
    """Run the manuscript make_numbers / make_figures unchanged twice: with the mapping of the design analyses (baseline)
    and with the mapping of the revision studies. Keys of the latter are paths after the src.where rewrite (the committed
    design-analyses mapping applies first): main2 summary → hrep/; reports/after of the three summaries → those re-run
    here; batch directories read directly by the manuscript → spliced directories; numbers.json and table7_rate of the
    design-analyses summary → compat/."""
    import windport_report_conservative as RD
    import windport_report_main2 as HR
    mp_i = json.loads((I_REP / "paper_mapping.json").read_text(encoding="utf-8"))
    rel = lambda p: p.relative_to(ROOT).as_posix()
    mp_k = {}
    mp_k[rel(H_REP)] = rel(ho)
    for p in (I_REP / "reports" / "after").iterdir():
        new = next(q for q in ra.values() if q.name.split("_")[:-1] == p.name.split("_")[:-1])
        mp_k[rel(p)] = rel(new)
    for f in ("table7_rate.csv", "table7_rate.md"):
        mp_k[rel(I_REP / "compat" / "spatial" / f)] = rel(comp / "spatial" / f)
    nj = json.loads((I_REP / "numbers.json").read_text(encoding="utf-8"))
    for k in ("codesign", "codesign_widen_cmp", "codesign_sens", "codesign_blockdiff", "codesign_disp"):
        nj[k] = N[k]
    (comp / "numbers.json").write_text(json.dumps(nj, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    mp_k[rel(I_REP / "numbers.json")] = rel(comp / "numbers.json")
    BD = HR.dirs()["run"]
    for b, d in made.items():
        mp_k[rel(BD[b])] = rel(d)
    import windport_report_maingeom as FR
    Df = FR.dirs()
    mp_k[rel(Df["example"])] = rel(K["r1_ex"] / "example")
    mp_k[rel(Df["critical"])] = rel(K["r1_ex"] / "critical")
    (out / "paper_mapping.json").write_text(json.dumps(mp_k, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    M0, f0 = HR.numbers("design", mp_i, out)
    reads, freads = [], []
    M1, f1 = logged(lambda: HR.numbers("revision", mp_k, out), reads)
    logged(lambda: HR.figures("design", mp_i, out), [])
    logged(lambda: HR.figures("revision", mp_k, out), freads)
    rows = [dict(macro=k, design=M0.get(k, ""), revision=M1.get(k, ""), changed=int(M0.get(k, "") != M1.get(k, ""))) for k in sorted(set(M0) | set(M1))]
    wcsv(out / "paper_macros.csv", rows)
    ch = [r for r in rows if r["changed"]]
    key = lambda r: (r["kind"], r["src"].split("  ⇒")[0])
    k0 = {key(r) for r in f0}
    newf = [r for r in f1 if key(r) not in k0]
    wcsv(out / "numbers_fail_new.csv", newf or [dict(kind="", line="", src="")])
    ff0, ff1 = rd(out / "figures_fail_design.csv"), rd(out / "figures_fail_revision.csv")
    fk0 = {key(r) for r in ff0 if r.get("kind")}
    newff = [r for r in ff1 if r.get("kind") and key(r) not in fk0]
    tb = RD.same_files(out / "numbers" / "design" / "tables", out / "numbers" / "revision" / "tables")
    fg = RD.same_files(out / "numbers" / "design" / "figures", out / "numbers" / "revision" / "figures")
    import difflib
    dl = []
    for k in (k for k, v in tb.items() if not v):
        a, b = ((out / "numbers" / t / "tables" / k).read_text(encoding="utf-8").splitlines() for t in ("design", "revision"))
        dl += [f"\n### tables/{k}\n", "```"] + [x for x in difflib.unified_diff(a, b, lineterm="", n=0) if not x.startswith(("---", "+++"))] + ["```"]
    md(out, "paper_tables.md", ["# Manuscript tables and data figures: design-analyses directories → revision-study directories\n", "| File | Same |", "|---|---|"] +
       [f"| tables/{k} | {'yes' if v else '**no**'} |" for k, v in tb.items()] + [f"| figures/{k} | {'yes' if v else '**no**'} |" for k, v in fg.items()] +
       ["\n## Changed tables, line by line (- design analyses, + revision studies)"] + dl)
    md(out, "paper_macros.md", ["# Manuscript macros (current scripts/make_numbers.py): design-analyses directories → revision-study directories (all parametric port batches feeding the manuscript at 115 m)\n",
                                f"{len(rows)} macros, {len(ch)} changed; failing assertions / erroring statements: design analyses {len(f0)}, revision studies {len(f1)}, new {len(newf)}; "
                                f"make_figures new {len(newff)}. Tables changed {sum(1 for v in tb.values() if not v)}, figure files (and their data) changed {sum(1 for v in fg.values() if not v)}.\n",
                                "| Macro | Design analyses | **Revision studies** |", "|---|---|---|"] + [f"| \\{r['macro']} | {r['design']} | **{r['revision']}** |" for r in ch] +
       ["\n## New failing assertions / erroring statements (make_numbers)\n", "| Kind | Line | Statement |", "|---|---:|---|"] + [f"| {r['kind']} | {r['line']} | `{r['src'][:200]}` |" for r in newf] +
       ["\n## New failing assertions / erroring statements (make_figures)\n", "| Kind | Line | Statement |", "|---|---:|---|"] + [f"| {r['kind']} | {r['line']} | `{r['src'][:200]}` |" for r in newff])
    N["paper"] = dict(macros=len(rows), changed=len(ch), fails_i=len(f0), fails_k=len(f1), fails_new=len(newf), fig_fails_new=len(newff),
                      tables_changed=sorted(k for k, v in tb.items() if not v), figures_changed=sorted(k for k, v in fg.items() if not v))
    return reads, freads


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_design as X
    X.setup_env()
    D = IR.dirs()
    K = kdirs()
    ins = sorted(p for d in K.values() for p in d.glob("*.csv")) + [K["plans"] / "plans.json", K["bturn"] / "turn_alt.json"]
    h = hashlib.sha256(Path(__file__).read_bytes())
    for f in ins:
        h.update(f.read_bytes())
    out = R / f"windport_revision_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    comp = out / "compat"
    comp.mkdir(exist_ok=True)
    N = {}
    made, st = splice(K)
    N["splice"] = st
    ra0 = reports_after(out, made, K)
    ra = {("extra" if "extra" in v.name else "runs" if "runs" in v.name else "e1e3"): v for v in ra0.values()}
    ho, *_ = hrep(made, ra0, K, out, N)
    t8(K, out, ra, N)
    rate_tab(K, out, comp, N, made)
    codesign(D, K, out, N)
    buffer(K, out, N)
    stage(K, out, N)
    rated(K, out, N)
    premise(K, out, N)
    p2(out, N)
    recheck(K, out, N)
    reads, freads = paper(out, comp, made, ra0, ho, N, K)
    scope(made, st, reads, freads, out, N)
    N["inv"] = {k: v for k, v in json.loads((K["r1_inv"] / "summary.json").read_text(encoding="utf-8")).items() if k != "e2"}     # the e2 item is void, see inv2
    N["inv2_e2"] = json.loads((K["r1inv2"] / "summary.json").read_text(encoding="utf-8"))
    N["ex_same"] = json.loads((K["r1_ex"] / "summary.json").read_text(encoding="utf-8"))
    (out / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out / "inputs.json").write_text(json.dumps([str(f.relative_to(ROOT)).replace("\\", "/") for f in ins], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)
    print(json.dumps(dict(paper=N["paper"], recheck=N["recheck"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
