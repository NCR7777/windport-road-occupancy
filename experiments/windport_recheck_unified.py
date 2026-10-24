"""Recheck of all committed simulation batches (from the E1-E3 batches to the unified-bound rerun) with the unified entry
(windport/bound_all.py): only the bounds are recomputed; delivered counts and port times are taken from the run directories.

Rows under the original lifting rule use W″ (bound_all.w2):
  E1-E3 batches E1 / E1h / rel / E3, all E4-E7 batches (incl. the 20,000 random-regression cases), extra analyses mix6 / sens /
  sens5 / port / pub / mixx (as in experiments/windport_recheck_deadend.items); the 540 small CP-SAT cases of E2
  (runs/e2); the spatial additions sites, siteport, turn, reserve, reach, upsize, ablate, hphd, cdv;
  the two original-rule groups of the conservative-lifting sens batch (orig, shift_orig).
Rows under the conservative lifting rule use W″_lift (bound_all.w2_lift):
  the 20 rerun batches and E2 of the conservative lifting rule (as in experiments/windport_recheck_conservative.items), the four
  conservative groups of its sens batch, span, xscan; the rerun of the spatial additions (experiments/windport_rerun_spatial.py).
Not checked: rows with the fixed-duration representation or "cut as a single resource" (the road-occupancy bound does not apply),
unloading rows of pub, port-time rows that did not fill the vessel.
Window form: simulation > bound and ties, also compared with the old bound recorded in the row (w1g / w1 / w4 of the spatial
additions) and with the branch bound (the unified entry without the crane-reach and reserved-period terms, i.e. bound_dead.wfn4 /
bound_lift.wfn_lift); binding terms use the layered labels of the dead-end coupling (experiments/windport_deadend.label: crane,
cradle turnover, fleet, road; a tie across classes is labelled as a tie, a binding preparation term gets a preparation suffix;
crane reach counts as crane, reserved periods as road) and the five case classes (bound_all.binding). E2: CP-SAT best
solution or simulation > bound, proven optimum = bound.
Port time: bound(port time) < n_v, L″* > port time (port time rounded up by 1.8 ms from the recorded 6 decimals).
Output results/windport_unified_recheck_<config hash>/: config.json, progress.json, rows.csv, summary.csv, strat.csv, summary.md.
Run: python experiments/windport_recheck_unified.py --procs 23 --slots DIR
"""
import argparse
import collections
import csv
import hashlib
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402

CODE = ["windport/lift.py", "windport/bound_lift.py", "windport/bound_dead.py", "windport/bound4.py", "windport/bound_all.py", "windport/sim.py",
        "windport/sim2.py", "windport/sim4.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py", "windport/archetypes.py",
        "windport/shipyard.py", "occupancy/network.py", "occupancy/params.py", "experiments/windport_sim.py", "experiments/windport_runs.py",
        "experiments/windport_random.py", "experiments/windport_extra.py", "experiments/windport_recheck.py", "experiments/windport_recheck_deadend.py",
        "experiments/windport_e2.py", "experiments/windport_spatial.py", "experiments/windport_rerun_conservative.py", "experiments/windport_recheck_conservative.py",
        "experiments/windport_sens_conservative.py", "experiments/windport_span.py", "experiments/windport_xscan.py", "experiments/windport_rerun_spatial.py",
        "experiments/windport_recheck_unified.py"]
H = 3600.0
E2_DIR, E2_LONG = "runs/e2", "runs/e2_long"
SENS, SPAN, XSCAN = "runs/conservative_sens", "runs/conservative_span", "runs/conservative_xscan"
SPATIAL = dict(sites="runs/spatial_sites", siteport="runs/spatial_siteport", turn="runs/spatial_turn",
             reserve="runs/spatial_reserve", reach="runs/spatial_reach", upsize="runs/spatial_upsize",
             ablate="runs/spatial_ablate", hphd="runs/spatial_hphd", cdv="runs/spatial_cdv")
LABEL = dict(crane="crane", cradle="cradle turnover", fleet="fleet", road="road")
_C = {}


def load(d, name="points.csv"):
    return list(csv.DictReader(open(ROOT / "results" / d / name, encoding="utf-8")))


def unified_dirs():
    import windport_rerun_spatial as E
    return {p: E.out_dir(p)[0].name for p in E.PARTS}


def items():
    """[(batch, lifting rule, row)]."""
    import windport_recheck_deadend as RB
    import windport_recheck_conservative as RD
    out = [(b, "plain", r) for b, r in RB.items()]
    out += [("e1e3:e2", "plain", r) for r in load(E2_DIR)]
    for part, d in SPATIAL.items():
        out += [(f"spatial:{part}", "plain", r) for r in load(d)]
    out += [(b, "lift", r) for b, r in RD.items(RD.dirs())]
    for part, d in unified_dirs().items():
        out += [(f"unified:{part}", "lift", r) for r in load(d)]
    for r in load(SENS):
        out.append(("conservative:sens", "plain" if r["var"] in ("orig", "shift_orig") else "lift", r))
    out += [("conservative:span", "lift", r) for r in load(SPAN)] + [("conservative:xscan", "lift", r) for r in load(XSCAN)]
    # E2: merge the CP-SAT results recomputed with 600 s for hard cases (cp_ columns) (as in the strat of experiments/windport_deadend.py;
    # the conservative rule uses the e2long of the conservative lifting rule)
    lng = dict(plain={r["key"]: r for r in load(E2_LONG)}, lift={r["key"]: r for r in load(RD.dirs()["e1e3:e2"], "e2long/points.csv")})
    keep = []
    for b, s, r in out:
        if b.startswith(("spatial:", "unified:")) and (r.get("step") in ("s3", "cf") or r.get("rep") == "fix"):
            continue                                    # cut as a single resource and fixed-duration representation
        if b == "e1e3:e2":
            r = dict(r, **{k: v for k, v in lng[s].get(r["key"], {}).items() if k.startswith("cp_")})
        keep.append((b, s, r))
    return keep


def cfg_of(batch, row):
    """(config, form): win (deliveries in the window), e2 (small CP-SAT case), port (port time to load n piles)."""
    src, part = batch.split(":")
    if batch == "e1e3:e2":
        import windport_e2 as E2
        return E2.cfg_of(row["key"]), "e2"
    if src in ("spatial", "unified"):
        import windport_runs as T
        import windport_spatial as A
        d = T.dec(row["key"])
        c = dict(A.cfg_of(part, d), fixed=False)
        return c, ("port" if d.get("what") == "port" or d.get("rep") else "win")
    if src == "conservative":
        import windport_extra as X
        if part == "sens":
            import windport_sens_conservative as M
            v = M.VARIANTS[row["var"]]
            c = X.port_cfg(row["scen"], row["mode"], row["arr"], int(row["K"]), M.GRID["n_v"], 0, p_extra=None if v["tu"] is None else dict(lift_tu=v["tu"]))
            if v["first"] is not None:
                c["geo"] = dict(c["geo"], first_cradle_m=v["first"])
            return c, "port"
        if part == "span":
            import windport_span as M
            h = row["hold"] if row["hold"] == "inf" else int(row["hold"])
            c = X.port_cfg(row["scen"], row["mode"], row["arr"], int(row["K"]), M.GRID["n_v"], h,
                           p_extra=dict(lift_span=row["span"]) if row["span"] == "gate" else None)
            if row["hold_eff"] != row["hold"]:
                c = dict(c, hold=0)
            return c, "port"
        import windport_xscan as M
        x = float(row["x"])
        return X.port_cfg(M.GRID["scen"], row["mode"], row["arr"], int(row["K"]), M.GRID["n_v"], 0, p_extra=dict(release_frac=x) if row["arr"] == "S0" else None), "port"
    import windport_recheck_conservative as RD
    return RD.cfg_of(batch, row)


def parts(c, sem):
    from windport import bound_all as BA
    key = json.dumps([{k: v for k, v in c.items() if k not in ("cal", "horizon_h", "n_load", "rule", "record", "unload_release_h")}, sem],
                     sort_keys=True, default=str)
    if key not in _C:
        _C[key] = BA.parts(c, lift=sem == "lift")
    return _C[key]


def label(t):
    """Layered label of the dead-end coupling (as in experiments/windport_deadend.label, with the class table bound_all.CLASS)."""
    from windport import bound_all as BA
    t = {k: v for k, v in t.items() if k != "prep"}
    for k in ("zone", "chainzone"):
        if k in t and "fleet" in t and t[k] >= t["fleet"]:
            del t[k]
    v = min(t.values())
    keys = [k for k, x in t.items() if x == v]
    cls = sorted({BA.CLASS[k] for k in keys})
    prep = any(k in BA.PREP for k in keys)
    lab = LABEL[cls[0]] if len(cls) == 1 else "tie (" + ", ".join(LABEL[x] for x in cls) + ")"
    return lab + ("·preparation" if prep and len(cls) == 1 else "")


NEW = ("reach", "reserve", "reserve_pre")


def one(arg):
    batch, sem, row = arg
    from windport import bound_all as BA
    c, form = cfg_of(batch, row)
    G = c["cal"]["crane"][0][0] * H
    w = dict(parts(c, sem), G=G)
    f = BA.w2_lift(c, w) if sem == "lift" else BA.w2(c, w)
    fb = lambda L: min(v for k, v in BA.terms(w, L).items() if k not in NEW + ("prep",))
    out = dict(batch=batch, sem=sem, key=row.get("key") or row.get("i") or "|".join(row.get(k, "") for k in ("var", "span", "scen", "mode", "arr", "hold", "x", "K")),
               form=form, lift="direct" if c["S"] == 0 else c.get("lift", "cradle"), map=int(c["geo"].get("kind") == "map"),
               ext=int(w["Sr"] is not None or w["rp"] is not None),
               group="|".join(str(row.get(k, "")) for k in ("kind", "scen", "mode", "lift", "arr", "hold")))
    if form == "port":
        if row.get("port_h") in (None, ""):
            return dict(out, skip=1)
        n = int(row.get("n_v") or c["n_load"])
        ph = float(row["port_h"]) * H + 0.5e-6 * H
        ls, lb = BA.lstar(f, n)[0] / H, BA.lstar(fb, n)[0] / H
        return dict(out, sim=n, port_h=row["port_h"], over=int(f(ph) < n), lstar=round(ls, 6), lstar_branch=round(lb, 6),
                    lstar_hi=int(ls > float(row["port_h"]) + 1e-6))
    L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * H
    t = BA.terms(w, L)
    v, keys, cls, sub, nat = BA.binding(t)
    vb = fb(L)
    out.update(new=v, branch=vb, lab=label(t), cls=cls, sub=sub, nature=nat, keys="+".join(keys))
    if form == "e2":
        sim, cp = int(row["sim"]), int(row["cp_best"])
        opt = row["cp_status"] == "OPTIMAL"
        old = int(row["w1"])
        return dict(out, sim=sim, cp=cp, cp_status=row["cp_status"], old=old, over=int(max(sim, cp) > v), ref=cp if opt else "",
                    tie_old=int(opt and cp == old), tie_branch=int(opt and cp == vb), tie=int(opt and cp == v))
    sim = int(row["n"] if batch == "runs:random" else row["sim"])
    if batch.startswith("unified"):
        old = ""                                        # rerun rows already record the unified W″_lift: no old bound
    elif batch.startswith("spatial"):
        old = row.get("w4")
    else:
        old = row.get("w1g") if row.get("w1g") not in (None, "") else row.get("w1")
    old = int(float(old)) if old not in (None, "") else ""
    return dict(out, sim=sim, old=old, over=int(sim > v), over_branch=int(sim > vb), ref=sim, tie_old=int(old != "" and sim == old),
                tie_branch=int(sim == vb), tie=int(sim == v))


def chunk(its):
    return [one(x) for x in its]


def init():
    pin(list(range(1, os.cpu_count())))
    from windport import lift as LF
    LF.install()                    # only so sim2.build_map accepts first_cradle_m (150 m in sens); bounds need no sim classes


COLS = ["batch", "sem", "key", "form", "lift", "map", "ext", "sim", "cp", "cp_status", "old", "branch", "new", "over", "over_branch", "tie_old", "tie_branch",
        "tie", "lab", "cls", "sub", "nature", "keys", "port_h", "lstar", "lstar_branch", "lstar_hi", "skip", "group"]


def pct(a, n):
    return f"{a / n:.1%}" if n else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=23)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import windport_recheck_conservative as RD
    dirs = dict(spatial=SPATIAL, conservative=RD.dirs(), unified=unified_dirs(), e2=E2_DIR, e2long=E2_LONG, sens=SENS, span=SPAN, xscan=XSCAN)
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    srcs = sorted({d for v in dirs.values() for d in (v.values() if isinstance(v, dict) else [v])})
    import windport_recheck_deadend as RB
    srcs += sorted(set(RB.E1E3.values()) | set(RB.RUNS.values()) | set(RB.EXTRA.values()))
    psha = {d: hashlib.sha256(b"".join((ROOT / "results" / d / n).read_bytes() for n in ("points.csv", "cases.csv", "e2long/points.csv") if (ROOT / "results" / d / n).exists()))
            .hexdigest() for d in srcs}
    cfg = dict(task="unified", part="recheck", dirs=dirs, points_sha256=psha, code=code)
    out = ROOT / "results" / ("windport_unified_recheck_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = items()
    ck = lambda x: json.dumps({k: v for k, v in x[2].items() if k in ("kind", "scen", "mode", "S", "K", "lift", "hold", "lev", "par", "val", "arr", "geo", "x",
                                                                      "what", "site", "st", "lay", "reach", "disp", "extra", "f", "sub", "lv", "step", "cd")},
                              sort_keys=True)
    its.sort(key=lambda x: (x[0], x[1], ck(x)))
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "unified bound: recheck of committed batches with the unified entry W″ / W″_lift", "unified")
    res = []
    try:
        for rs in slot_imap(chunk, [its[k:k + 150] for k in range(0, len(its), 150)], a.procs, initializer=init, slots_dir=a.slots, tag="unified"):
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res.sort(key=lambda r: (r["batch"], r["sem"], str(r["key"])))
    with open(out / "rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(res)
    by = collections.defaultdict(list)
    for r in res:
        by[(r["batch"], r["sem"])].append(r)
    summ = []
    for (b, s), rs in sorted(by.items()):
        win = [r for r in rs if r["form"] in ("win", "e2")]
        prt = [r for r in rs if r["form"] == "port" and not r.get("skip")]
        summ.append(dict(batch=b, sem=s, rows=len(rs), maps=sum(r["map"] for r in rs), ext=sum(r["ext"] for r in rs), win=len(win), port=len(prt),
                         skipped=sum(r.get("skip", 0) for r in rs), over=sum(r.get("over", 0) for r in rs), over_branch=sum(r.get("over_branch", 0) for r in rs),
                         tie_old=sum(r["tie_old"] for r in win), tie_branch=sum(r["tie_branch"] for r in win), tie=sum(r["tie"] for r in win),
                         tighter=sum(1 for r in win if r["new"] < r["branch"]), lstar_hi=sum(r["lstar_hi"] for r in prt),
                         lstar_up=sum(1 for r in prt if r["lstar"] > r["lstar_branch"] + 1e-9)))
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(summ[0]))
        w.writeheader()
        w.writerows(summ)
    # tightness by class: denominators fixed to the classes under the unified entry; compare the row's old bound, the branch bound
    # and the unified entry (window form and proven-optimal E2 cases)
    strat = []
    for s in ("plain", "lift"):
        for scope, ok in (("all window-form rows", lambda r: r["form"] == "win"), ("E2 proven optimal", lambda r: r["form"] == "e2" and r["cp_status"] == "OPTIMAL"),
                          ("spatial / unified batches", lambda r: r["form"] == "win" and r["batch"].startswith(("spatial", "unified")))):
            rs = [r for r in res if r["sem"] == s and ok(r) and r["new"] > 0]
            for lab in sorted({r["lab"] for r in rs}) + ["road involved (incl. ties)", "total"]:
                a_ = [r for r in rs if (lab == "total") or (r["lab"] == lab) or (lab.startswith("road involved") and "road" in r["lab"])]
                strat.append(dict(sem=s, scope=scope, lab=lab, n=len(a_), tie_old=sum(r["tie_old"] for r in a_), tie_branch=sum(r["tie_branch"] for r in a_),
                                  tie=sum(r["tie"] for r in a_)))
    with open(out / "strat.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(strat[0]))
        w.writeheader()
        w.writerows(strat)
    tot = lambda s, k: sum(x[k] for x in summ if x["sem"] == s)
    L = ["# Unified-bound recheck: unified entry W″ (original lifting rule) and W″_lift (conservative lifting rule), bounds only", "",
         "| Batch | Rule | Rows | Shipyard maps | With reach / reserved periods | Window form / port time | Sim > unified bound | Ties (window form) old bound → branch → unified | Unified strictly below branch | L″* > port time | L″* raised |",
         "|---|---|---:|---:|---:|---|---:|---|---:|---:|---:|"]
    for x in summ:
        L.append(f"| {x['batch']} | {x['sem']} | {x['rows']:,} | {x['maps']:,} | {x['ext']:,} | {x['win']:,} / {x['port']:,}" +
                 (f" (not filled, not checked: {x['skipped']})" if x["skipped"] else "") + f" | {x['over']} | {x['tie_old']:,} → {x['tie_branch']:,} → {x['tie']:,} | "
                 f"{x['tighter']:,} | {x['lstar_hi']} | {x['lstar_up']} |")
    for s in ("plain", "lift"):
        win = tot(s, "win")
        L.append(f"| Total | {s} | {tot(s, 'rows'):,} | {tot(s, 'maps'):,} | {tot(s, 'ext'):,} | {win:,} / {tot(s, 'port'):,} | {tot(s, 'over')} | "
                 f"{tot(s, 'tie_old'):,} ({pct(tot(s, 'tie_old'), win)}) → {tot(s, 'tie_branch'):,} ({pct(tot(s, 'tie_branch'), win)}) → "
                 f"{tot(s, 'tie'):,} ({pct(tot(s, 'tie'), win)}) | {tot(s, 'tighter'):,} | {tot(s, 'lstar_hi')} | {tot(s, 'lstar_up')} |")
    L += ["", "Tie denominators are the window-form rows (E2: 540 cases, tie = proven optimal and = bound); the old bound is the W1 / W1′ "
          "recorded in each row (E1-E3 batches to the extra analyses) or the W″ of the spatial additions.",
          "Branch: bound_dead.wfn4 (dead-end coupling) under the original rule, bound_lift.wfn_lift (conservative lifting rule) under the "
          "conservative rule, i.e. the unified entry without the crane-reach and reserved-period terms.", "",
          "## Tightness by class (denominators fixed to the classes under the unified entry)", ""]
    for s in ("plain", "lift"):
        for scope in ("all window-form rows", "E2 proven optimal", "spatial / unified batches"):
            L += [f"### {'original lifting rule W″' if s == 'plain' else 'conservative lifting rule W″_lift'}: {scope}", "",
                  "| Class | Cases | = old bound | = branch | = unified |", "|---|---:|---|---|---|"]
            for x in strat:
                if x["sem"] == s and x["scope"] == scope:
                    L.append(f"| {x['lab']} | {x['n']:,} | {x['tie_old']:,} ({pct(x['tie_old'], x['n'])}) | {x['tie_branch']:,} ({pct(x['tie_branch'], x['n'])}) | "
                             f"{x['tie']:,} ({pct(x['tie'], x['n'])}) |")
            L.append("")
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=f"original rule {tot('plain', 'rows')} rows > W″ {tot('plain', 'over')}; conservative rule {tot('lift', 'rows')} rows > W″_lift {tot('lift', 'over')}")
    print(out)
    print("\n".join(L[:80]))


if __name__ == "__main__":
    main()
