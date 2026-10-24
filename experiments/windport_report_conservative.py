"""Updated conclusions under the conservative lifting rule: before / after sets of summary tables and new values of all manuscript
macros (the cradle mode also keeps the area under the load closed, so every batch changes).
Reads only points.csv / summary.* / rows.csv and the committed summary directories, not points/.

1. Summary tables: the main of each of the three committed summary scripts (windport_report.py, windport_report2.py,
   windport_report3.py) runs twice with the same directory names, only ROOT is replaced by a temporary root (TMP; under
   results/ one directory junction per directory name points to the run directory in this working tree): before reads the committed
   run directories (must be byte-identical to the committed summary directories, checked in same.md), after reads the new run
   directories of the conservative lifting rule (experiments/windport_rerun_conservative.py, windport_e2_conservative.py). Outputs are copied to
   reports/before|after/<summary directory name>/; changed.md lists the files that differ between before and after.
2. Manuscript macros: the manuscript's scripts/make_numbers.py is executed unchanged twice; src.show still reads src.REPO (git show of
   the same commit; for after, the committed run and summary directories are replaced by the new ones). before keeps all assertions
   (they encode the numbers of the current manuscript), and its output must be byte-identical to the manuscript's numbers.tex; after
   drops the assertions (only the assert statements; reading and formatting unchanged). macros.csv / macros.md: all macros before ->
   after; tables.md: which tables/*.tex changed.
3. Tables of the conservative lifting rule: core case and the Table 5 scenarios (core.md), Kassels Rønne reproduction
   (kassels.md), vehicle release time x (mixx.md), rows that become faster / deliver more under the new rule (better.md).
Output results/windport_conservative_report_<first 12 hex digits of the SHA-256 of the inputs and this script>/.
Run: python experiments/windport_report_conservative.py
"""
import ast
import csv
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import types
import _winapi
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_report as RA                     # noqa: E402
import windport_report2 as RB                # noqa: E402
import windport_report3 as RC               # noqa: E402

PAPER = ROOT / "paper"
TMP = ROOT / "out" / "conservative_rep"
# key in the summary script -> batch of the conservative-lifting rerun
SWAP = {RA: dict(e1="e1e3:e1", e1h="e1e3:e1h", rel="e1e3:rel", e3="e1e3:e3", e2="e1e3:e2", e2long="e1e3:e2long"),
        RB: dict(e4="runs:e4", e5="runs:e5", e6="runs:e6", e7="runs:e7", pocket="runs:pocket", conv="runs:conv", e2c="runs:e2c", sens="runs:sens",
                 sens7="runs:sens7", e1="e1e3:e1", e1h="e1e3:e1h", e2="e1e3:e2", e2long="e1e3:e2long"),
        RC: dict(port="extra:port", fix="extra:fix", mix6="extra:mix6", sens="extra:sens", pub="extra:pub", mixx="extra:mixx", sens5="extra:sens5",
                 e3="e1e3:e3", e4="runs:e4", e5="runs:e5", sens0="runs:sens")}
ORIG = {M: dict(M.DIRS) for M in SWAP}
NAME = {RA: "windport_report", RB: "windport_report2", RC: "windport_report3"}
# summary directories read by the manuscript (REP133 / REP134 / REP136 in src.py)
REP = {RA: "tables/e1_e3", RB: "tables/e4_e7", RC: "tables/extra"}
H = 3600.0


def new_dirs():
    import windport_recheck_conservative as RK
    D = RK.dirs()
    D["e1e3:e2long"] = D["e1e3:e2"] + "/e2long"
    return D


def recheck_dir():
    return sorted((ROOT / "results").glob("windport_conservative_recheck_*"), key=lambda p: p.stat().st_mtime)[-1]


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def wcsv(p, rs):
    RC.wcsv(p, rs)


# ---------------------------------------------------------------- 1. summary scripts before / after
def unlink_tmp():
    """Remove the temporary root: first the directory junctions (only the junctions themselves), then the rest."""
    if not TMP.exists():
        return
    for p in (TMP / "results").iterdir() if (TMP / "results").exists() else []:
        if p.is_junction():
            os.rmdir(p)
    shutil.rmtree(TMP)


def run_reports(tag, D, out):
    unlink_tmp()
    (TMP / "results").mkdir(parents=True)
    for f in RC.EXTRA:
        (TMP / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / f, TMP / f)
    made = {}
    try:
        for M, sw in SWAP.items():
            M.DIRS.clear()
            M.DIRS.update(ORIG[M])
            if tag == "after":
                M.DIRS.update({k: D[b] for k, b in sw.items()})
            for v in M.DIRS.values():
                top = v.split("/")[0]
                if not (TMP / "results" / top).exists():
                    _winapi.CreateJunction(str(ROOT / "results" / top), str(TMP / "results" / top))
            M.ROOT = TMP
            before = set((TMP / "results").iterdir())
            M.main()
            new = [p for p in (TMP / "results").iterdir() if p not in before and p.name.startswith(NAME[M] + "_")]
            assert len(new) == 1, new
            dst = out / "reports" / tag / new[0].name
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(new[0], dst)
            made[M] = dst
    finally:
        for M in SWAP:
            M.ROOT = ROOT
            M.DIRS.clear()
            M.DIRS.update(ORIG[M])
        sys.stdout.reconfigure(encoding="utf-8")
        unlink_tmp()
    return made


def same_files(a, b):
    fa = {p.relative_to(a).as_posix(): p for p in a.rglob("*") if p.is_file()}
    fb = {p.relative_to(b).as_posix(): p for p in b.rglob("*") if p.is_file()}
    return {k: (k in fa and k in fb and fa[k].read_bytes() == fb[k].read_bytes()) for k in sorted(set(fa) | set(fb))}


# ---------------------------------------------------------------- 2. manuscript macros (make_numbers.py executed unchanged)
def fake_src(mapping):
    """Same constants and same repository as the manuscript's scripts/src.py (src.REPO, git show of the same commit); committed
    directories in mapping are replaced by the new directories of this working tree."""
    m = types.ModuleType("src")
    code = (PAPER / "scripts" / "src.py").read_text(encoding="utf-8")
    exec(compile(code, str(PAPER / "scripts" / "src.py"), "exec"), m.__dict__)

    def local(path):
        for a, b in mapping.items():
            if path == a or path.startswith(a + "/"):
                return ROOT / (b + path[len(a):])
        return None

    def show(path, commit):
        p = local(path)
        if p is not None:
            return p.read_bytes().decode("utf-8-sig")
        r = subprocess.run(["git", "-C", str(m.REPO), "show", f"{commit}:{path}"], capture_output=True, check=True)
        return r.stdout.decode("utf-8-sig")

    def tracked(path, commit):
        p = local(path)
        if p is not None:
            return sorted(path + "/" + q.relative_to(p).as_posix() for q in p.rglob("*") if q.is_file()) if p.is_dir() else [path]
        r = subprocess.run(["git", "-C", str(m.REPO), "ls-tree", "-r", "--name-only", commit, path], capture_output=True, check=True)
        return r.stdout.decode("utf-8").split()

    m.show, m.tracked = show, tracked
    return m


class Soft(ast.NodeTransformer):
    """For after: a failing assertion records its line number (_AF) without stopping; a failing top-level statement records its line
    number and exception (_EF) and is skipped, execution continues after it."""
    def visit_Assert(self, node):
        rec = ast.parse(f"_AF.append({node.lineno})").body
        t = ast.Try(body=[ast.If(test=ast.UnaryOp(op=ast.Not(), operand=node.test), body=rec, orelse=[])],
                    handlers=[ast.ExceptHandler(type=ast.Name(id="Exception", ctx=ast.Load()), name=None, body=ast.parse(f"_AF.append({node.lineno})").body)],
                    orelse=[], finalbody=[])
        return ast.copy_location(t, node)

    def top(self, tree):
        body = []
        for st in self.visit(tree).body:
            if isinstance(st, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
                body.append(st)
                continue
            h = ast.ExceptHandler(type=ast.Name(id="Exception", ctx=ast.Load()), name="_e", body=ast.parse(f"_EF.append(({st.lineno}, repr(_e)))").body)
            body.append(ast.copy_location(ast.Try(body=[st], handlers=[h], orelse=[], finalbody=[]), st))
        tree.body = body
        return ast.fix_missing_locations(tree)


def numbers(tag, mapping, out):
    """Execute make_numbers.py and write to out/numbers/<tag>/ (numbers.tex, tables/); return the macro dict."""
    d = out / "numbers" / tag
    shutil.rmtree(d, ignore_errors=True)
    (d / "scripts").mkdir(parents=True)
    src = (PAPER / "scripts" / "make_numbers.py").read_text(encoding="utf-8")
    if tag == "after":                   # regex hard-codes current numbers (533 optimal etc.): use wildcards
        a = "proven optimal 533, feasible only 7; CP-SAT > W1 0 cases; proven optimal and = W1 353 cases;"
        assert src.count(a) == 1
        src = src.replace(a, r"proven optimal \d+, feasible only \d+; CP-SAT > W1 \d+ cases; proven optimal and = W1 \d+ cases;")
    tree = ast.parse(src)
    if tag == "after":
        tree = Soft().top(tree)
    saved = sys.modules.get("src")
    sys.modules["src"] = fake_src(mapping)
    g = dict(__name__="__main__", __file__=str(d / "scripts" / "make_numbers.py"), _AF=[], _EF=[])
    try:
        exec(compile(tree, str(PAPER / "scripts" / "make_numbers.py"), "exec"), g)
    finally:
        if saved is None:
            sys.modules.pop("src", None)
        else:
            sys.modules["src"] = saved
    shutil.rmtree(d / "scripts")
    lines = src.splitlines()
    fails = [dict(kind="assert", line=n, src=lines[n - 1].strip()) for n in g["_AF"]] + \
        [dict(kind="error", line=n, src=lines[n - 1].strip() + "  ⇒ " + e) for n, e in g["_EF"]]
    return dict(g["M"]), fails


def mapping_after(D, reps):
    S = importlib.import_module("windport_rerun_conservative").SRC
    mp = {f"results/{S[b]}": f"results/{D[b]}" for b in S}
    mp["results/runs/e2"] = f"results/{D['e1e3:e2']}"
    mp["results/runs/e2_long"] = f"results/{D['e1e3:e2long']}"
    for M, d in reps.items():
        mp[f"results/{REP[M]}"] = d.relative_to(ROOT).as_posix()
    return mp


def literals(ra):
    """Macros that make_numbers.py writes as literals tied to the data by the assertion next to them (if the assertion fails after
    the change, the literal no longer matches the data): read them from the after summary tables with the same definition."""
    h2 = lambda v: f"{float(v):.2f}"
    A, B, C = ra[RA], ra[RB], ra[RC]
    by = {}
    for r in rows(A / "table3.csv"):
        by.setdefault((r["scen"], r["mode"], r["S"]), []).append(r)
    one = lambda rs, k: "/".join(sorted({r[k] for r in rs}))
    lane1, fc = by[("lane", "pull_in", "1")], sorted(by[("fastcrane", "pull_in", "1")], key=lambda r: r["kref"])
    occ, fix = float(one(lane1, "occ_min")), float(one(lane1, "fix_min"))
    M = dict(EThreeOcc=one(lane1, "occ_min"), EThreeFix=one(lane1, "fix_min"), EThreeGain=f"{100 * (occ / fix - 1):.0f}\\%",
             EThreeFastOcc=one(fc, "occ_min"), EThreeFastFixLo=min((r["fix_min"] for r in fc), key=float), EThreeFastFixHi=max((r["fix_min"] for r in fc), key=float),
             EThreeHoldLong=one(by[("longslow", "pull_in", "1")], "occ_inf_min"), EThreeHoldLane=one(lane1, "occ_inf_min"),
             EThreeFixPlatLo=min((r["fix_plat"] for r in lane1), key=int), EThreeFixPlatHi=max((r["fix_plat"] for r in lane1), key=int),
             EThreeSlowOcc=one(by[("slow", "on_road", "1")], "occ_min"))
    T5 = {(r["scen"], r["mode"], r["arr"]): r for r in rows(C / "table5x.csv")}
    M["MuhFastOneH"] = h2(T5[("fastcrane", "pull_in", "S1")]["muhabie_1h"])
    pl = [r for r in rows(B / "table_e4_plateau.csv") if r["scen"] == "lane" and int(r["S"]) >= 1]
    gt = [r for r in pl if int(r["plat_convoy"]) > int(r["ceil_kd"])]
    g = [int(r["convoy_gain_after_ceil"]) for r in gt]
    M.update(ConvGainLo=str(min(g)) if g else "—", ConvGainHi=str(max(g)) if g else "—",
             ConvDispatchOnly=["none", "one", "two", "three"][sum(int(r["gain_dispatch"]) > 0 for r in gt)] if gt else "—")
    E5 = {(r["scen"], r["mode"], r["tide"], r["fleet"], r["Kt"], r["S"], r["rule"], r["x"]): r for r in rows(B / "table_e5.csv")}
    g5 = lambda sc, tide, fl, kt, x: E5[(sc, "pull_in", tide, fl, str(kt), "1", "fcfs", x)]
    dl = {k: [int(g5("longslow", "cont", "ded", k, x)["total"]) for x in ("0.0", "0.25", "0.5", "0.75", "1.0")] for k in (3, 4, 6)}
    z, lo, hi = "/".join(sorted({str(v[0]) for v in dl.values()})), min(v[-1] for v in dl.values()), max(v[-1] for v in dl.values())
    z0 = min(v[0] for v in dl.values())
    M.update(FivePlainNuZero=g5("base", "cont", "plain", 2, "0.0")["n_u"], FiveLongDedZero=z, FiveLongDedLo=str(lo), FiveLongDedHi=str(hi),
             FiveLongDedPctLo=f"{100 * (1 - hi / z0):.0f}\\%", FiveLongDedPctHi=f"{100 * (1 - lo / z0):.0f}\\%",
             FiveTideZero=str(int(g5("base", "6", "ded", 3, "0.0")["total"])),
             FiveTideOne="/".join(sorted({str(int(g5("base", "6", "ded", k, "1.0")["total"])) for k in (3, 4, 6)})))
    T4 = {(r["site"], r["scen"], r["mode"]): r for r in rows(B / "table4.csv")}
    num = lambda s: s.split(" (")[1].rstrip(")")
    plat6 = {k: s["plat_L12_S1"].split(" (")[0].lstrip("K=") for k, s in T4.items()}
    a_, b_ = int(T4[("okpo", "fastcrane", "on_road")]["sum_fcfs"]), int(T4[("okpo", "fastcrane", "pull_in")]["sum_fcfs"])
    M.update(SixOkpoFastN=num(T4[("okpo", "fastcrane", "on_road")]["plat_L12_S1"]), SixYantaiFastN=num(T4[("yantai", "fastcrane", "on_road")]["plat_L12_S1"]),
             SixPlatBase="/".join(sorted({v for k, v in plat6.items() if k[1] == "base"})), SixPlatSlowYantai=plat6[("yantai", "slow", "on_road")],
             SixPlatFast="/".join(sorted({v for k, v in plat6.items() if k[1] == "fastcrane"})),
             SixOkpoRoadSum=grp(a_), SixOkpoPullSum=grp(b_), SixOkpoRoadCost=f"{100 * (1 - a_ / b_):.0f}\\%")
    hd2 = {(r["scen"], r["mode"], r["hold"]): r for r in rows(B / "table_hold2.csv")}
    f_, c_ = int(hd2[("longslow", "pull_in", "0")]["fcfs"]), int(hd2[("longslow", "pull_in", "0")]["convoy"])
    M.update(ConvHoldF=grp(f_), ConvHoldC=grp(c_), ConvHoldPct=f"{100 * (c_ / f_ - 1):.1f}\\%")
    return M


def grp(v):
    return f"{int(v):,d}".replace(",", "{,}")


# ---------------------------------------------------------------- 3. tables of the conservative lifting rule
def core(D, rk, out):
    """Core case and the Table 5 scenarios: one vessel with 10 monopiles, Q_h = 0, first come first served; shortest over K = 1-8 and
    over K = 2-8; L* of the three bounds."""
    old = rows(ROOT / "results" / ORIG[RC]["port"] / "points.csv")
    new = rows(ROOT / "results" / D["extra:port"] / "points.csv")
    rr = {r["key"]: r for r in rows(rk / "rows.csv") if r["batch"] == "extra:port"}
    pick = lambda rs, sc, m, arr, K0: [r for r in rs if (r["scen"], r["mode"], r["arr"], r["n_v"], r["hold"], r["rep"]) == (sc, m, arr, "10", "0", "fcfs")
                                      and int(r["K"]) >= K0]
    tab = []
    for sc in ("lane", "longslow", "fastcrane", "base"):
        for m in ("on_road", "pull_in"):
            for arr in ("S0", "S1m", "S3m", "S1", "S3"):
                for K0 in (1, 2):
                    a, b = pick(old, sc, m, arr, K0), pick(new, sc, m, arr, K0)
                    x = [rr[r["key"]] for r in b if r["key"] in rr]
                    tab.append(dict(scen=sc, mode=m, arr=arr, K=f"{K0}–8", before=min(float(r["port_h"]) for r in a), after=min(float(r["port_h"]) for r in b),
                                    lstar_lift=min((float(r["lstar_lift"]) for r in x), default=None),
                                    lstar_clear=min((float(r["lstar_clear"]) for r in x), default=None),
                                    lstar_plain=min((float(r["lstar_plain"]) for r in x), default=None),
                                    lstar_w1p=min(float(r["lstar_lo"]) for r in b)))
    L = ["# Core case and Table 5 scenarios: time in port (one vessel, 10 monopiles, Q_h = 0, first come first served), before → after, rule-independent lower bounds\n",
         "Before = original rule (lifting may start while the vehicle tail still occupies the single lane, no road closure; committed port batch of the extra analyses); "
         "after = conservative lifting rule (t_u = 0.05 p, the cradle mode also closes the area under the load). "
         "L*: inf{L : bound(L) ≥ 10} of W″_lift, W″_clear (holds only for direct lifts), W″ (Corollary 6 not extended) and W′ (extra analyses, column lstar_lo), "
         "each minimised over K.\n",
         "| Scenario | Cradle | Lifting | K | Before h | After h | Diff h | L*: W″_lift | W″_clear | W″ | W′ | After / L*_lift |", "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    f4 = lambda v: "-" if v is None else f"{v:.4f}"
    for t in tab:
        L.append(f"| {RC.SCEN_ZH[t['scen']]} | {RC.MODE_ZH[t['mode']]} | {RC.ARR_ZH[t['arr']]} | {t['K']} | {t['before']:.4f} | {t['after']:.4f} | {t['after'] - t['before']:+.4f} | "
                 f"{f4(t['lstar_lift'])} | {f4(t['lstar_clear'])} | {f4(t['lstar_plain'])} | {t['lstar_w1p']:.4f} | "
                 f"{'-' if t['lstar_lift'] is None else f'{t['after'] / t['lstar_lift']:.3f}'} |")
    (out / "core.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    wcsv(out / "core.csv", tab)


def kassels(D, rk, out):
    old = rows(ROOT / "results" / ORIG[RC]["pub"] / "points.csv")
    new = {r["key"]: r for r in rows(ROOT / "results" / D["extra:pub"] / "points.csv")}
    rr = {r["key"]: r for r in rows(rk / "rows.csv") if r["batch"] == "extra:pub"}
    L = ["# Kassels Rønne reproduction (loading, one vessel with 3 monopiles, G = 12 h), before → after\n",
         "TO1 = 1 cradle, 1 vehicle set, mixed lifting (S1m); TO2 = 2 cradles, cradle mode (S2). The \"Kassels sequence\" (third monopile lifted from the vehicle) "
         "adds, under the new rule, the time for the vehicle body to leave the road after arrival "
         "(experiments/windport_rerun_conservative.kassels_lift). L*(3): W′ (committed column) and W″_lift (new rule).\n",
         "| Geometry | Handling | Cradle | Lifting | K | Sim before → after h | Kassels sequence before → after h | L*(3) W′ | L*(3) W″_lift | Lifting per monopile, after |", "|---|---|---|---|---:|---|---|---:|---:|---|"]
    for r in old:
        if r["pub"] != "out":
            continue
        n, x = new[r["key"]], rr.get(r["key"], {})
        L.append(f"| {r['geo']} | {r['hand']} | {RC.MODE_ZH[r['mode']]} | {RC.ARR_ZH.get(r['arr'], r['arr'])} | {r['K']} | {float(r['port_h']):.3f} → {float(n['port_h']):.3f} | "
                 f"{float(r['kassels_h']):.3f} → {float(n['kassels_h']):.3f} | {float(n['lstar_lo']):.3f} | "
                 f"{('%.3f' % float(x['lstar_lift'])) if x.get('lstar_lift') else '-'} | {n['how']} |")
    (out / "kassels.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def mixx(out, before, after):
    a = {(r["scen"], r["mode"], r["K"], r["arr"]): r for r in rows(before / "table_mixx.csv")}
    b = {(r["scen"], r["mode"], r["K"], r["arr"]): r for r in rows(after / "table_mixx.csv")}
    XS = ("x0.0", "x0.25", "x0.5", "x0.75", "x1.0")
    L = ["# Condition on the vehicle release time x: time in port to load 10 monopiles (Q_h = 0, first come first served), before → after; \"from which x slower than the cradle mode\"\n",
         "| Scenario | Cradle | K | Lifting | Cradle mode h before → after | " + " | ".join(f"x = {x[1:]}" for x in XS) + " | Slower than cradle from, before → after |",
         "|---|---|---|---|---|" + "---|" * len(XS) + "---|"]
    for k in sorted(b):
        L.append(f"| {RC.SCEN_ZH[k[0]]} | {RC.MODE_ZH[k[1]]} | {k[2]} | {RC.ARR_ZH[k[3]]} | {a[k]['cradle']} → {b[k]['cradle']} | " +
                 " | ".join(f"{a[k][x]} → {b[k][x]}" for x in XS) + f" | {a[k]['worse_from'] or '-'} → {b[k]['worse_from'] or '-'} |")
    wa = {(r["x"], r["what"]): r for r in rows(before / "table_mixx_win.csv")}
    wb = {(r["x"], r["what"]): r for r in rows(after / "table_mixx_win.csv")}
    L += ["\n## Window delivery (A1 subgrid of E4, 40 points / S): more / same / fewer than the cradle mode at the same point, before → after\n", "| x | Comparison | More | Same | Fewer |", "|---|---|---|---|---|"]
    for k in sorted(wb):
        L.append(f"| {k[0]} | {k[1]} | {wa[k]['more']} → {wb[k]['more']} | {wa[k]['same']} → {wb[k]['same']} | {wa[k]['fewer']} → {wb[k]['fewer']} |")
    (out / "mixx.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def better(D, out):
    """The new rule only adds constraints, but the first-come-first-served dispatch order changes with it: compare each row before /
    after (delivered count for the window form, time in port for the time-in-port form)."""
    S = importlib.import_module("windport_rerun_conservative").SRC
    res, ex = [], []
    for b in list(S) + ["e1e3:e2"]:
        src = ROOT / "results" / (S[b] if b in S else "runs/e2") / "points.csv"
        old = {r["key"]: r for r in rows(src)}
        n = more = faster = 0
        for r in rows(ROOT / "results" / D[b] / "points.csv"):
            o = old[r["key"]]
            n += 1
            if r.get("port_h") not in (None, "") and o.get("port_h") not in (None, ""):
                if float(r["port_h"]) < float(o["port_h"]) - 1e-9:
                    faster += 1
                    ex.append((float(o["port_h"]) - float(r["port_h"]), b, r["key"], f"{float(o['port_h']):.4f} → {float(r['port_h']):.4f} h"))
            elif r.get("sim") not in (None, "") and o.get("sim") not in (None, "") and int(float(r["sim"])) > int(float(o["sim"])):
                more += 1
                ex.append((int(float(r["sim"])) - int(float(o["sim"])), b, r["key"], f"{o['sim']} → {r['sim']} pcs"))
        res.append(dict(batch=b, rows=n, more=more, faster=faster))
    L = ["# Rows that become faster / deliver more under the new rule (first-come-first-served dispatch order effect)\n", "| Batch | Rows | More delivered | Shorter time in port |", "|---|---:|---:|---:|"]
    L += [f"| {r['batch']} | {r['rows']:,} | {r['more']} | {r['faster']} |" for r in res]
    L.append(f"| Total | {sum(r['rows'] for r in res):,} | {sum(r['more'] for r in res)} | {sum(r['faster'] for r in res)} |")
    L += ["", "## The 15 rows with the largest difference", "", "| Batch | Key | Before → after |", "|---|---|---|"]
    L += [f"| {b} | `{k}` | {t} |" for _, b, k, t in sorted(ex, key=lambda e: (-e[0], e[1], e[2]))[:15]]
    (out / "better.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    wcsv(out / "better.csv", res)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    D = new_dirs()
    rk = recheck_dir()
    h = hashlib.sha256(Path(__file__).read_bytes())
    for f in ("make_numbers.py", "src.py"):
        h.update((PAPER / "scripts" / f).read_bytes())
    for b in sorted(D):
        h.update((ROOT / "results" / D[b] / "points.csv").read_bytes())
    h.update((rk / "rows.csv").read_bytes())
    out = ROOT / "results" / f"windport_conservative_report_{h.hexdigest()[:12]}"
    out.mkdir(parents=True, exist_ok=True)
    rb, ra = run_reports("before", D, out), run_reports("after", D, out)
    L = ["# Summary scripts rerun: is before byte-identical to the committed summary directories; which files differ between after and before\n"]
    for M in SWAP:
        s = same_files(ROOT / "results" / REP[M], rb[M])
        L.append(f"- {NAME[M]}: before = {rb[M].name} (committed {REP[M]}), {sum(s.values())} / {len(s)} files byte-identical" +
                 ("" if all(s.values()) else "; different: " + ", ".join(k for k, v in s.items() if not v)))
    (out / "same.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    L = ["# Differences between the before / after summary tables (same summary script, only the input directories replaced)\n", "| Summary script | File | Same |", "|---|---|---|"]
    for M in SWAP:
        L += [f"| {NAME[M]} | {k} | {'yes' if v else '**no**'} |" for k, v in same_files(rb[M], ra[M]).items()]
    (out / "changed.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    Mb, fb = numbers("before", {}, out)
    assert not fb
    nb = (out / "numbers" / "before" / "numbers.tex").read_bytes() == (PAPER / "numbers.tex").read_bytes()
    Ma, fa = numbers("after", mapping_after(D, ra), out)
    if fa:
        wcsv(out / "numbers_fail.csv", fa)
    lit = literals(ra)
    lit_changed = sorted(k for k, v in lit.items() if Ma.get(k) != v)
    Ma.update(lit)
    mrows = [dict(macro=k, before=Mb.get(k, ""), after=Ma.get(k, ""), changed=int(Mb.get(k) != Ma.get(k))) for k in sorted(set(Mb) | set(Ma))]
    wcsv(out / "macros.csv", mrows)
    L = ["# Manuscript macros (make_numbers.py executed unchanged): before → after\n",
         f"before keeps all assertions and reads the committed directories; its numbers.tex is {'byte-identical to' if nb else '**different from**'} the manuscript's numbers.tex; after drops the assertions and reads the new directories of the conservative lifting rule. "
         f"{len(mrows)} macros, {sum(r['changed'] for r in mrows)} changed. The {len(lit)} macros that make_numbers.py writes as literals tied to the data by assertions are read from the after summary tables with the same definition"
         f" (`literals`); {len(lit_changed)} of them differ from the literal: {', '.join(chr(92) + k for k in lit_changed)}.\n", "| Macro | Before | After |", "|---|---|---|"]
    L += [f"| \\{r['macro']} | {r['before']} | {r['after']} |" for r in mrows if r["changed"]]
    L += ["", "## Unchanged macros", "", ", ".join(f"\\{r['macro']}" for r in mrows if not r["changed"])]
    L += ["", f"## Failing assertions and statements of make_numbers.py after the change ({len(fa)}; the assertions encode numbers or wording of the current manuscript, each failure marks a sentence of the text to revise)", "",
          "| Kind | Line | Statement |", "|---|---:|---|"] + [f"| {f['kind']} | {f['line']} | `{f['src'][:300]}` |" for f in fa]
    (out / "macros.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    tb, ta = out / "numbers" / "before" / "tables", out / "numbers" / "after" / "tables"
    L = ["# Manuscript tables tables/*.tex: before → after\n", "| File | Same |", "|---|---|"]
    L += [f"| {k} | {'yes' if v else '**no**'} |" for k, v in same_files(tb, ta).items()]
    (out / "tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    core(D, rk, out)
    kassels(D, rk, out)
    mixx(out, ROOT / "results" / REP[RC], ra[RC])
    better(D, out)
    (out / "inputs.json").write_text(json.dumps(dict(new=D, recheck=rk.name, orig={M.__name__: ORIG[M] for M in SWAP}, reports={M.__name__: REP[M] for M in REP}),
                                     ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
