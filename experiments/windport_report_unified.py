"""Unified-bound summary: the three branches merged into one bound (no simulation; reads the run directories only, the bounds of
the Okpo three-layer table and of the case classes come from rows.csv of windport_recheck_unified).

1. yupo3: Okpo and Yantai three-voyage storage areas, base case, cradle S = 1: three layers of port time (crane lower limit →
   rule-independent lower bound L″* → first-come-first-served), original lifting rule (simulation of the spatial additions,
   unified W″) next to the conservative lifting rule (rerun, unified W″_lift); Q_h = 0, 1, unlimited.
2. regime: the A1 points of E1 (grid regime5 of the spatial additions) reclassified into the five case classes by the unified W″
   (original-rule simulation) and by W″_lift (conservative-rule simulation of the conservative lifting rule rerun), with the tie
   rate of each class; compared cell by cell with the original table of the spatial additions (W′), listing the cells of the
   fig:regime grid (pull-in, G = 3 h, L = 4, 12 h, main lifting mode) that change class, with the reason (binding terms).
3. spatial_lift/: the table functions of the summary script of the spatial additions (experiments/windport_report_spatial.py)
   applied unchanged to the conservative-rule inputs: the rerun directories of the unified bound and of the conservative lifting
   rule (E4-E7 batches e4, e6, e7, sens and extra analyses port, mix6; summary tables from the corrected E4-E7 / extra-analysis
   summary directories); campaign durations recomputed from the E3 port times of the conservative-rule rerun.
4. lift_rows: per row of each batch of the spatial additions (original rule → conservative rule): rows, changed rows and totals
   for direct lifts, mixed lift-and-carry and cradles.
5. macros: merged macro replacement table (the 483 macros of the conservative lifting rule take their corrected values; macros
   proposed in the reports of the spatial additions, the dead-end coupling and the conservative lifting rule take the merged
   values), compared with the current manuscript values (numbers/before/numbers.tex of the conservative-rule summary directory,
   byte-identical to the manuscript numbers.tex); list of failed statements.
Output results/windport_unified_report_<first 12 hex digits of the SHA-256 of the inputs and this script>/.
Run: python experiments/windport_report_unified.py
"""
import collections
import csv
import hashlib
import json
import re
import shutil
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_runs as T                                        # noqa: E402
import windport_report_spatial as AR                               # noqa: E402

H = 3600.0
SPATIAL_REP = "tables/spatial"
CONSERVATIVE_REP = "tables/conservative"
SPATIAL_REGIME = "runs/spatial_regime5"
DEADEND_PORT = "runs/deadend_port"
SCEN_ZH, MODE_ZH = AR.SCEN_ZH, AR.MODE_ZH
CLS_ZH = dict(crane="crane", cradle="cradle turnover", turnover="cradle turnover", fleet="fleet", road="road", prep="preparation time")
i, fl, rd, wcsv, md, pct = AR.i, AR.fl, AR.rd, AR.wcsv, AR.md, AR.pct


def one(pat):
    ds = sorted(p for p in (ROOT / "results").glob(pat) if p.is_dir())
    assert len(ds) == 1, (pat, ds)
    return ds[0]


def dirs():
    import windport_recheck_conservative as RD
    import windport_rerun_spatial as E
    rnd = sorted(p for p in (ROOT / "results").glob("windport_unified_random_*") if (p / "summary.json").exists())
    return dict(recheck=one("windport_unified_recheck_*"), random=rnd, e={p: E.out_dir(p)[0] for p in E.PARTS}, d={k: ROOT / "results" / v for k, v in RD.dirs().items()})


# ---------------------------------------------------------------- 1. Okpo three layers
def yupo3(rec, D, out, N):
    a = {r["key"]: r for r in rd(ROOT / "results" / AR.one("siteport").name / "points.csv")}
    e = {r["key"]: r for r in rd(D["e"]["siteport"] / "points.csv")}
    rp = {r["key"]: r for r in rec if r["batch"] == "spatial:siteport"}
    rl = {r["key"]: r for r in rec if r["batch"] == "unified:siteport"}
    rows = []
    for k, r in a.items():
        d = T.dec(k)
        if d["st"] != "multi" or d["scen"] != "base" or d["arr"] != "S1":
            continue
        rows.append(dict(site=d["kind"][4:], mode=d["mode"], K=int(d["K"]), hold=d.get("hold", "0"), crane=10.0,
                         lstar_spatial=round(fl(r["lstar_lo"]), 4), lstar_plain=round(fl(rp[k]["lstar"]), 4), fcfs_plain=round(fl(r["port_h"]), 4),
                         lstar_lift=round(fl(rl[k]["lstar"]), 4), fcfs_lift=round(fl(e[k]["port_h"]), 4)))
    rows.sort(key=lambda r: (r["site"], r["mode"], {"0": 0, "1": 1, "inf": 2}[r["hold"]], r["K"]))
    wcsv(out / "yupo3.csv", rows)
    L = ["# Okpo and Yantai three-voyage storage areas: three layers of port time for a 10-pile vessel (base case, cradle S = 1; h)\n",
         "Three layers: crane lower limit n_v·p = 10.00 h → rule-independent lower bound L″*(10) (unified entry, any dispatching, fixed "
         "routes) → first-come-first-served. Original lifting rule: simulation of the spatial additions and unified W″; "
         "conservative lifting rule (main rule): rerun and unified W″_lift. The column of the spatial additions is their W″ at the time "
         "(without the terms of the dead-end coupling).\n",
         "| Shipyard | Cradle | Q_h | K | Crane lower limit | L* (W″ of the spatial additions) | Original rule: L″* → FCFS | Conservative rule: L″_lift* → FCFS |", "|---|---|---|---:|---:|---:|---|---|"]
    for r in rows:
        L.append(f"| {r['site']} | {MODE_ZH[r['mode']]} | {dict(inf='unlimited').get(r['hold'], r['hold'])} | {r['K']} | 10.00 | {r['lstar_spatial']:.2f} | "
                 f"{r['lstar_plain']:.2f} → {r['fcfs_plain']:.2f} | {r['lstar_lift']:.2f} → {r['fcfs_lift']:.2f} |")
    md(out, "yupo3.md", L)
    N["yupo3"] = {f"{r['site']}|{r['mode']}|{r['hold']}|{r['K']}": r for r in rows}


# ---------------------------------------------------------------- 2. five case classes
def regime(rec, out, N):
    old = rd(ROOT / "results" / SPATIAL_REGIME / "regime5.csv")
    rp = {r["key"]: r for r in rec if r["batch"] == "e1e3:e1" and r["sem"] == "plain"}
    rl = {r["key"]: r for r in rec if r["batch"] == "e1e3:e1" and r["sem"] == "lift"}
    rows = []
    for r in old:
        p, q = rp[r["key"]], rl[r["key"]]
        rows.append(dict(key=r["key"], scen=r["scen"], mode=r["mode"], lift=r["lift"], L=i(r["L"]), K=i(r["K"]), S=i(r["S"]), G=i(r["G"]),
                         sim=i(r["sim"]), wprime=i(r["wprime"]), cls_a=dict(turnover="cradle").get(r["cls"], r["cls"]),
                         nat_a=dict(turnover="cradle").get(r["nature"], r["nature"]), bind_a=r["binding"],
                         w2=i(p["new"]), cls_p=p["cls"], nat_p=p["nature"], bind_p=p["keys"], sub_p=p["sub"],
                         sim_l=i(q["sim"]), w2l=i(q["new"]), cls_l=q["cls"], nat_l=q["nature"], bind_l=q["keys"], sub_l=q["sub"]))
    wcsv(out / "regime.csv", rows)
    main = [r for r in rows if r["lift"] != "mixed"]
    L = ["# Five case classes and tie rate per class: spatial additions (W′) → unified W″ (original rule) → unified W″_lift "
         "(conservative rule, simulation of the conservative-rule rerun)\n",
         "A1 points of E1 (five scenarios × cradle mode × L × K × S × G); classes in the order of windport.bound4.classify (crane, "
         "cradle turnover, fleet, road; a strictly binding preparation term is preparation time); "
         "the unified entry adds: the whole-chain quay-zone term of Corollary 7(b) counts as road (its preparation form as preparation "
         "time), the cradle coupling of Corollary 8 follows its term, crane reach counts as crane, reserved periods as road (this grid "
         "has no reach and no reserved periods).\n",
         "## Points per scenario, main lifting mode (cradle; S = 0 direct lift)\n", "| Scenario | Bound | Crane | Cradle turnover | Fleet | Road | Preparation time | By nature: fleet / road |", "|---|---|---:|---:|---:|---:|---:|---|"]
    cnt = {}
    for sc in ("base", "slow", "longslow", "lane", "fastcrane"):
        for tag, ck, nk in (("spatial W′", "cls_a", "nat_a"), ("unified W″", "cls_p", "nat_p"), ("unified W″_lift", "cls_l", "nat_l")):
            rs = [r for r in main if r["scen"] == sc]
            c = collections.Counter(r[ck] for r in rs)
            n = collections.Counter(r[nk] for r in rs)
            cnt[f"{sc}|{tag}"] = dict(c)
            L.append(f"| {SCEN_ZH[sc]} | {tag} | {c['crane']} | {c['cradle']} | {c['fleet']} | {c['road']} | {c['prep']} | {n['fleet']} / {n['road']} |")
    L += ["\n## Tie rate per class (points with simulation = bound / points in the class; denominators are the classes under each bound)\n",
          "| Case class | Spatial additions W′: points / ties | Unified W″ | Unified W″_lift | Unified W″_lift, mixed lift-and-carry |",
          "|---|---|---|---|---|"]
    tie = {}
    for k in ("crane", "cradle", "fleet", "road", "prep"):
        x = [(sum(1 for r in main if r[c] == k), sum(1 for r in main if r[c] == k and r[s] == r[w])) for c, s, w in
             (("cls_a", "sim", "wprime"), ("cls_p", "sim", "w2"), ("cls_l", "sim_l", "w2l"))]
        mx = [r for r in rows if r["lift"] == "mixed" and r["cls_l"] == k]
        y = (len(mx), sum(1 for r in mx if r["sim_l"] == r["w2l"]))
        tie[k] = x + [y]
        L.append(f"| {CLS_ZH[k]} | " + " | ".join(f"{a} / {pct(b, a)}" for a, b in x + [y]) + " |")
    # fixed denominator: road cells of the spatial additions (the 292 points binding on road under W′) and their ties under the unified bound
    road_a = [r for r in main if r["cls_a"] == "road"]
    L += ["\n## Fixed denominator: points classed as road by the spatial additions (main rule)\n",
          f"points {len(road_a)}; reach W′ {sum(r['sim'] == r['wprime'] for r in road_a)} ({pct(sum(r['sim'] == r['wprime'] for r in road_a), len(road_a))}), "
          f"reach unified W″ {sum(r['sim'] == r['w2'] for r in road_a)} ({pct(sum(r['sim'] == r['w2'] for r in road_a), len(road_a))}), "
          f"conservative rule reaches unified W″_lift {sum(r['sim_l'] == r['w2l'] for r in road_a)} ({pct(sum(r['sim_l'] == r['w2l'] for r in road_a), len(road_a))})."]
    trans = collections.Counter((r["cls_a"], r["cls_p"], r["cls_l"]) for r in main)
    L += ["\n## Class changes (all main-rule points; spatial additions → unified W″ → unified W″_lift)\n",
          "| Spatial additions | Unified W″ | Unified W″_lift | Points |", "|---|---|---|---:|"]
    L += [f"| {CLS_ZH[a]} | {CLS_ZH[b]} | {CLS_ZH[c]} | {n} |" for (a, b, c), n in sorted(trans.items(), key=lambda x: -x[1]) if not a == b == c]
    fig = [r for r in main if r["mode"] == "pull_in" and r["G"] == 3 and r["L"] in (4, 12)]

    def why(r, b, cl, w):
        ks = set(r[b].split("+"))
        tag = []
        if ks & {"chainzone", "chainprep"}:
            tag.append("whole-chain quay-zone term of Corollary 7(b)" + (" (preparation form)" if "chainprep" in ks else ""))
        if r[w] < r["wprime"] and ks & {"fleet", "zone", "cut", "prep_cut", "prep_zone"}:
            tag.append("Corollary 7(a) / 8 tightens the original term")
        if cl == "cls_l" and r["w2l"] < r["w2"]:
            tag.append("conservative-rule parameters (Corollary 11)")
        if cl == "cls_l" and r["sim_l"] != r["sim"]:
            tag.append(f"simulation {r['sim']} → {r['sim_l']}")
        return "; ".join(tag) or "tie order"
    ch = [r for r in fig if not (r["nat_a"] == r["nat_p"] == r["nat_l"] and r["cls_a"] == r["cls_p"] == r["cls_l"])]
    L += [f"\n## Cells of the fig:regime grid (pull-in, G = 3 h, L = 4, 12 h, main lifting mode, {len(fig)} cells) that change class: {len(ch)} cells\n",
          "| Scenario | L | K | S | Simulation (original / conservative) | Spatial additions: class (nature)·binding terms = W′ | Unified W″ | Unified W″_lift | Reason |", "|---|---:|---:|---:|---|---|---|---|---|"]
    for r in sorted(ch, key=lambda r: (r["scen"], r["L"], r["S"], r["K"])):
        L.append(f"| {SCEN_ZH[r['scen']]} | {r['L']} | {r['K']} | {r['S']} | {r['sim']} / {r['sim_l']} | {CLS_ZH[r['cls_a']]} ({CLS_ZH[r['nat_a']]})·{r['bind_a']} = {r['wprime']} | "
                 f"{CLS_ZH[r['cls_p']]} ({CLS_ZH[r['nat_p']]})·{r['bind_p']} = {r['w2']} | {CLS_ZH[r['cls_l']]} ({CLS_ZH[r['nat_l']]})·{r['bind_l']} = {r['w2l']} | "
                 f"{why(r, 'bind_l', 'cls_l', 'w2l') if r['cls_l'] != r['cls_a'] or r['nat_l'] != r['nat_a'] else why(r, 'bind_p', 'cls_p', 'w2')} |")
    md(out, "regime.md", L)
    wcsv(out / "fig_regime_unified.csv", [dict(scen=r["scen"], L=r["L"], K=r["K"], S=r["S"], cls=r["cls_l"], sub=r["sub_l"], nature=r["nat_l"], binding=r["bind_l"],
                                                sim=r["sim_l"], bound=r["w2l"], cls_plain=r["cls_p"], nature_plain=r["nat_p"], sim_plain=r["sim"], bound_plain=r["w2"])
                                           for r in fig])
    N["regime"] = dict(counts=cnt, tie=tie, road_fixed=dict(n=len(road_a), wprime=sum(r["sim"] == r["wprime"] for r in road_a),
                                                             w2=sum(r["sim"] == r["w2"] for r in road_a), w2l=sum(r["sim_l"] == r["w2l"] for r in road_a)),
                       fig_cells=len(fig), fig_changed=len(ch))


# ---------------------------------------------------------------- 3. tables of the spatial additions under the conservative rule
def spatial_lift(rec, D, out, N):
    import windport_spatial_analytic as AA
    o = out / "spatial_lift"
    o.mkdir(exist_ok=True)
    br = {(r["batch"].split(":")[1], r["key"]): r for r in rec if r["batch"].startswith("unified:") and r["form"] == "win"}
    E = {p: [dict(r, wprime=br[(p, r["key"])]["branch"]) if (p, r["key"]) in br else r for r in rd(D["e"][p] / "points.csv")] for p in D["e"]}
    rep = ROOT / "results" / CONSERVATIVE_REP / "reports" / "after"
    fx = dict(e4=D["d"]["runs:e4"], e6=D["d"]["runs:e6"], e7=D["d"]["runs:e7"], sens=D["d"]["runs:sens"], port=D["d"]["extra:port"], mix6=D["d"]["extra:mix6"],
              rep134=one(str((rep / "windport_runs_report_*").relative_to(ROOT / "results"))), rep136=one(str((rep / "windport_extra_report_*").relative_to(ROOT / "results"))))
    M, err = {}, {}

    def run(name, f, *a):
        try:
            return f(*a)
        except Exception:
            err[name] = traceback.format_exc()[-600:]
    AB = run("sites", AR.sites, E["sites"], rd(fx["e6"] / "points.csv"), E["siteport"], o, M)
    A_, B_ = AB if AB else ({}, {})
    run("turn", AR.turn, AR.one("turngeo"), E["turn"], A_, B_, o, M)
    run("reserve", AR.reserve, E["reserve"], A_, B_, o, M)
    e4, mix6 = rd(fx["e4"] / "points.csv"), rd(fx["mix6"] / "points.csv")
    run("reach", AR.reach, E["reach"], e4, mix6, o, M)
    run("upsize", AR.upsize, E["upsize"], rd(fx["e7"] / "points.csv"), o, M)
    run("ablate", AR.ablate, E["ablate"], rd(fx["port"] / "points.csv"), e4, o, M)
    run("hphd", AR.hphd, E["hphd"], rd(fx["sens"] / "points.csv"), o, M)
    run("codesign", AR.codesign, rd(AR.one("codesign") / "best.csv"), rd(AR.one("codesign") / "codesign.csv"), E["cdv"], o, M)
    g = AA.GRIDS["campaign"]
    saved = g["e3_dir"]
    g["e3_dir"] = str(D["d"]["e1e3:e3"].relative_to(ROOT)).replace("\\", "/")
    try:
        cam = run("campaign_rows", AA.campaign)
    finally:
        g["e3_dir"] = saved
    if cam:
        run("campaign", AR.campaign, [{k: str(v) for k, v in r.items()} for r in cam], o, M)
    run("p15", AR.p15, e4, mix6, fx["rep134"], rd(o / "table_siteport.csv"), fx["rep136"], o, M)
    (o / "numbers.json").write_text(json.dumps(M, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (o / "errors.json").write_text(json.dumps(err, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    N["spatial_lift"], N["spatial_lift_errors"] = M, sorted(err)
    N["spatial_lift_fixed"] = {k: v.name for k, v in fx.items()}


# ---------------------------------------------------------------- 4. row-by-row comparison
def lift_rows(D, out, N):
    tab = []
    for p, d in D["e"].items():
        a = {r["key"]: r for r in rd(AR.one(p) / "points.csv")}
        b = {r["key"]: r for r in rd(d / "points.csv")}
        assert set(a) == set(b), p
        g = collections.defaultdict(list)
        for k in a:
            dd = T.dec(k)
            if p == "cdv":
                x = json.loads(dd["cd"])
                lf = "direct" if x["S"] == 0 else x["lift"]
            elif dd.get("arr"):
                lf = "direct" if dd["arr"] == "S0" else ("mixed" if dd["arr"].endswith("m") else "cradle")
            else:
                lf = dd.get("lift") or ("direct" if dd.get("S") == "0" else "cradle")
            g[lf].append(k)
        for lf, ks in sorted(g.items()):
            col = "sim" if a[ks[0]].get("sim") not in (None, "") else "port_h"
            va, vb = [fl(a[k][col]) for k in ks], [fl(b[k][col]) for k in ks]
            ok = [(x, y) for x, y in zip(va, vb) if x is not None and y is not None]
            tab.append(dict(part=p, lift=lf, col=col, rows=len(ks), changed=sum(1 for x, y in zip(va, vb) if x != y), up=sum(1 for x, y in ok if y > x + 1e-9),
                            down=sum(1 for x, y in ok if y < x - 1e-9), sum_before=round(sum(x for x, _ in ok), 3), sum_after=round(sum(y for _, y in ok), 3),
                            unfilled_before=sum(1 for x in va if x is None), unfilled_after=sum(1 for y in vb if y is None)))
    wcsv(out / "lift_rows.csv", tab)
    L = ["# Batches of the spatial additions row by row: original lifting rule (committed) → conservative lifting rule (rerun)\n",
         "Window form compares deliveries (sim), port-time form compares the port time to load n_v piles (port_h, h); totals only "
         "include rows with values on both sides.\n",
         "| Batch | Lifting | Column | Rows | Changed | Up / down | Total: original → conservative | Not filled: original / conservative |", "|---|---|---|---:|---:|---|---|---|"]
    L += [f"| {t['part']} | {t['lift']} | {t['col']} | {t['rows']:,} | {t['changed']:,} | {t['up']:,} / {t['down']:,} | {t['sum_before']:,} → {t['sum_after']:,} | "
          f"{t['unfilled_before']} / {t['unfilled_after']} |" for t in tab]
    md(out, "lift_rows.md", L)
    N["lift_rows"] = tab


# ---------------------------------------------------------------- 5. macros
def tex_values(path):
    out = {}
    for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{(.*)\}\s*$", Path(path).read_text(encoding="utf-8"), re.M):
        out[m.group(1)] = re.sub(r"\\xspace$", "", m.group(2))
    return out


def macros(rec, D, out, N):
    rep = ROOT / "results" / CONSERVATIVE_REP
    cur = tex_values(rep / "numbers" / "before" / "numbers.tex")
    mc = rd(rep / "macros.csv")
    rows = [dict(macro=r["macro"], source="conservative lifting rule (make_numbers.py, corrected)", manuscript=cur.get(r["macro"], r["before"]), final=r["after"],
                 differs=int(cur.get(r["macro"], r["before"]) != r["after"]), note="" if r["after"] != "" else "unreadable (its sentence is to be removed)") for r in mc]
    y, rg, A = N["yupo3"], N["regime"], N.get("spatial_lift", {})

    def add(name, val, src, note=""):
        rows.append(dict(macro=name, source=src, manuscript=cur.get(name, ""), final=val, differs=int(cur.get(name, "") != val), note=note or ("new" if name not in cur else "")))
    fmt = lambda x: f"{x:.2f}"
    # core example (dead-end coupling / conservative lifting rule)
    core = {r["key"]: r for r in rec if r["batch"] in ("extra:port",) and r["form"] == "port"}
    add("LStarCradle", "18.64", "conservative lifting rule, proposed; W″_lift cradle S = 1 = FCFS")
    add("LStarDirRoad", "16.66", "conservative lifting rule, proposed; direct lift on-road L″_lift* = FCFS")
    add("LStarDirPull", "17.02", "conservative lifting rule, proposed; direct lift pull-in L″_lift* = FCFS")
    add("LStarPlainCradle", "18.42", "dead-end coupling: original-rule L″*(10) = FCFS (appendix comparison)")
    add("LStarKOne", "27.06", "dead-end coupling: K = 1 rule-independent lower bound by saddle order (original rule)")
    add("CpKOne", "27.07", "dead-end coupling: K = 1 CP-SAT best solution (original rule)")
    for site, tag in (("okpo", "Okpo"), ("yantai", "Yantai")):
        for m, mt in (("pull_in", "Pull"), ("on_road", "Road")):
            r2 = y.get(f"{site}|{m}|0|2")
            if not r2:
                continue
            ks = [y[f"{site}|{m}|0|{K}"] for K in (2, 4, 8)]
            lo, hi = min(r["lstar_lift"] for r in ks), max(r["lstar_lift"] for r in ks)
            add(f"{tag}Multi{mt}LStar", fmt(lo) if abs(lo - hi) < 5e-3 else f"{fmt(lo)}–{fmt(hi)}", "unified bound, Okpo three layers: L″_lift*(10), S = 1, Q_h = 0, K = 2, 4, 8")
            fo, fh = min(r["fcfs_lift"] for r in ks), max(r["fcfs_lift"] for r in ks)
            add(f"{tag}Multi{mt}Fcfs", fmt(fo) if abs(fo - fh) < 5e-3 else f"{fmt(fo)}–{fmt(fh)}", "unified bound, Okpo three layers: FCFS (conservative rule)")
            lo, hi = min(r["lstar_plain"] for r in ks), max(r["lstar_plain"] for r in ks)
            add(f"{tag}Multi{mt}LStarPlain", fmt(lo) if abs(lo - hi) < 5e-3 else f"{fmt(lo)}–{fmt(hi)}", "unified bound, Okpo three layers: L″*(10) (original rule, appendix comparison)")
            fo, fh = min(r["fcfs_plain"] for r in ks), max(r["fcfs_plain"] for r in ks)
            add(f"{tag}Multi{mt}FcfsPlain", fmt(fo) if abs(fo - fh) < 5e-3 else f"{fmt(fo)}–{fmt(fh)}", "spatial additions: FCFS (original rule)")
            h1 = y.get(f"{site}|{m}|1|2")
            if h1:
                add(f"{tag}Multi{mt}HoldOne", fmt(h1["fcfs_lift"]), f"unified bound: FCFS with one gate holding place, K = 2 (conservative rule; original rule {fmt(h1['fcfs_plain'])} h)")
    # E1 ties (as in the dead-end coupling: A1 long single lane, on-road cradles, Q_h = 0)
    for sem, tag in (("plain", "Plain"), ("lift", "")):
        e1 = [r for r in rec if r["batch"] == "e1e3:e1" and r["sem"] == sem]
        for g, name in (("A1|lane|on_road|cradle||0", "EOneTieLaneAOneW"), ("A1|lane|pull_in|cradle||0", "EOneTieLanePullW"),
                        ("A2|lane|on_road|cradle||0", "EOneTieLaneATwoW"), ("A3|lane|on_road|cradle||0", "EOneTieLaneAThreeW")):
            rs = [r for r in e1 if r["group"] == g]
            if rs:
                add(name + tag, f"{sum(int(r['tie']) for r in rs) / len(rs) * 100:.1f}\\%", f"as in the dead-end coupling, {'original' if sem == 'plain' else 'conservative'}-rule simulation against the unified bound ({len(rs)} points)")
        add("EOneTieW" + tag, f"{sum(int(r['tie']) for r in e1) / len(e1) * 100:.1f}\\%", f"all {len(e1):,} points of E1 against the unified bound")
        e2 = [r for r in rec if r["batch"] == "e1e3:e2" and r["sem"] == sem and r["cp_status"] == "OPTIMAL"]
        add("ETwoTieWpp" + tag, f"{sum(int(r['tie']) for r in e2)}", f"cases = unified bound among the {len(e2)} proven-optimal E2 cases")
        add("ETwoOptN" + tag, f"{len(e2)}", "number of proven-optimal E2 cases")
    # recheck and random regression
    sm = rd(D["recheck"] / "summary.csv")
    for sem, tag in (("plain", "Plain"), ("lift", "Lift")):
        s = [x for x in sm if x["sem"] == sem]
        rows_ = sum(int(x["rows"]) for x in s)
        win = sum(int(x["win"]) for x in s)
        add(f"Recheck{tag}Rows", f"{rows_:,}".replace(",", "{,}"), "rows in the unified-bound recheck")
        add(f"Recheck{tag}Over", str(sum(int(x["over"]) for x in s)), "rows with simulation / CP-SAT > unified bound")
        add(f"Recheck{tag}Tie", f"{sum(int(x['tie']) for x in s) / win * 100:.1f}\\%", "tie rate in window form (unified bound)")
    rs = [json.loads((d / "summary.json").read_text(encoding="utf-8")) for d in D["random"]]
    add("RandUnifiedN", f"{sum(r['ran'] for r in rs):,}".replace(",", "{,}"), "cases in the unified-bound random regression (both rules per case)")
    add("RandUnifiedPiles", f"{sum(r['lifts'] + r['lifts_lift'] for r in rs):,}".replace(",", "{,}"), "piles checked one by one (both rules together)")
    # case classes (long single lane, conservative rule)
    c = rg["counts"]
    for sc, tag in (("lane", "Lane"), ("fastcrane", "Fast")):
        x = c.get(f"{sc}|unified W″_lift", {})
        for k, kt in (("road", "Road"), ("prep", "Prep"), ("crane", "Crane"), ("fleet", "Fleet")):
            add(f"Regime{tag}{kt}", str(x.get(k, 0)), f"points per case class ({SCEN_ZH[sc]}, unified W″_lift)")
    rt = rg["tie"]["road"][2]
    add("RegimeRoadTie", f"{rt[1] / rt[0] * 100:.1f}\\%" if rt[0] else "—", f"tie rate of the road class (unified W″_lift, main rule, {rt[0]} points)")
    rf = rg["road_fixed"]
    add("RegimeRoadFixedTie", f"{rf['w2l'] / rf['n'] * 100:.1f}\\%", f"share of the {rf['n']} points classed as road by the spatial additions that reach W″_lift under the conservative rule")
    wcsv(out / "macros.csv", rows)
    L = ["# Merged macro replacement table (for the manuscript revision)\n",
         "Current manuscript values from numbers/before/numbers.tex of the conservative-rule summary directory (byte-identical to the "
         "manuscript numbers.tex); final values: the 483 macros of the conservative lifting rule take their corrected values (this "
         "step does not change those simulations), "
         "macros proposed in the reports of the spatial additions, the dead-end coupling and the conservative lifting rule and the new "
         "numbers of the unified bound take the merged main rule (conservative lifting rule, unified W″_lift); original-rule numbers are "
         "listed separately (names with Plain). Only macros that differ from the current value or are new are listed.\n",
         "| Macro | Manuscript value | Final value | Source | Note |", "|---|---|---|---|---|"]
    L += [f"| \\{r['macro']} | {r['manuscript']} | {r['final']} | {r['source']} | {r['note']} |" for r in rows if r["differs"]]
    md(out, "macros.md", L)
    N["macros"] = dict(total=len(rows), differs=sum(r["differs"] for r in rows), new=sum(1 for r in rows if r["macro"] not in cur))
    shutil.copy(rep / "numbers_fail.csv", out / "numbers_fail_conservative.csv")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    D = dirs()
    inputs = [D["recheck"] / "rows.csv", D["recheck"] / "summary.csv"] + [d / "summary.json" for d in D["random"]] + [d / "points.csv" for d in D["e"].values()]
    h = hashlib.sha256(Path(__file__).read_bytes())
    for f in inputs:
        h.update(f.read_bytes())
    out = ROOT / "results" / f"windport_unified_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    rec = rd(D["recheck"] / "rows.csv")
    N = {}
    yupo3(rec, D, out, N)
    regime(rec, out, N)
    spatial_lift(rec, D, out, N)
    lift_rows(D, out, N)
    macros(rec, D, out, N)
    N["random"] = {d.name: json.loads((d / "summary.json").read_text(encoding="utf-8")) for d in D["random"]}
    N["recheck"] = D["recheck"].name
    (out / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out / "inputs.json").write_text(json.dumps([str(f.relative_to(ROOT)).replace("\\", "/") for f in inputs], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)
    print("spatial_lift tables with errors:", N["spatial_lift_errors"])


if __name__ == "__main__":
    main()
