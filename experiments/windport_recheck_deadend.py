"""Dead-end coupling recheck: the committed simulation batches rechecked with W″ (windport/bound_dead.py, Corollaries 6 and 7) and its
generalisation W″ₛ (Corollary 6 extended to dq < 0). Only the bounds are recomputed; simulated counts and port times are taken from the
points.csv / cases.csv of each run directory (no simulation is rerun).

Batches: e1, e1h, rel, e3 of the E1-E3 batches (occupancy representation); e4, e5, e6 of the E4-E7 batches (Okpo and Yantai shipyard maps,
read by their registered commit and SHA-256, as in the E4-E7 batches), e7, pocket, conv, e2c, sens, sens7, random (20,000 cases, including
shipyard-derived maps); mix6, sens, sens5, port (FCFS and convoy dispatch), pub (loading), mixx of the extra analyses.
Not rechecked: rows with the fixed-duration representation or "cut as a single resource" (the occupancy bound does not apply), and unloading
port times (pub unloading, including the per-tide case; the bound there is Theorem 3, not W″).
Window-form rows: simulated count > W″ / W″ₛ, equality (compared with the old bound stored in the row); port-time rows: W″(port time) < n_v,
L″* > port time (the port time stored to 6 decimals is rounded up by 1.8 ms). Also an E1 equality table by group (same grouping as the
E1-E3 report: archetype × scenario × cradle × lifting × Q_h), matching \\EOneTie… in the manuscript numbers.tex.
Output results/windport_deadend_recheck_<config hash>/: config.json, progress.json, rows.csv (per row), summary.csv, e1_groups.csv, summary.md.
Run: python experiments/windport_recheck_deadend.py --procs 8 --slots DIR
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap               # noqa: E402

CODE = ["windport/sim.py", "windport/sim2.py", "windport/bound.py", "windport/bound2.py", "windport/bound3.py", "windport/bound_dead.py",
        "windport/archetypes.py", "windport/shipyard.py", "occupancy/network.py", "occupancy/params.py", "experiments/windport_sim.py",
        "experiments/windport_runs.py", "experiments/windport_random.py", "experiments/windport_extra.py", "experiments/windport_recheck.py",
        "experiments/windport_recheck_deadend.py"]
E1E3 = dict(e1="runs/e1", e1h="runs/e1_hold", rel="runs/release_time", e3="runs/e3")
RUNS = dict(e4="runs/e4", e5="runs/e5", e6="runs/e6",
            e7="runs/e7", pocket="runs/pocket", conv="runs/convoy_hold",
            e2c="runs/e2_convoy", sens="runs/sens", sens7="runs/sens_e7",
            random="runs/random_bound")
EXTRA = dict(mix6="runs/mixed_e4", sens="runs/sens_extra", sens5="runs/sens_e5",
            port="runs/port_time", pub="runs/public_projects", mixx="runs/mixed_release")
H = 3600.0
_C = {}


def load(d, name="points.csv"):
    return list(csv.DictReader(open(ROOT / "results" / d / name, encoding="utf-8")))


def cfg_of(batch, row):
    """(config, form): form is "win" (items within the window, sim column) or "port" (port time to load n piles)."""
    src, part = batch.split(":")
    if src == "e1e3":
        import windport_sim as E
        c = E.cfg_of(part, row["key"])
        return c, ("port" if part == "e3" and row["key"].split("|")[0] == "port" else "win")
    if src == "extra" and part == "mixx":
        import windport_runs as T
        import windport_extra as X
        d = T.dec(row["key"])
        x = float(d["x"])
        if d["what"] == "port":
            return X.port_cfg(d["scen"], d["mode"], d["arr"], int(d["K"]), X.GRIDS["mixx"]["port"]["n_v"], 0, p_extra=dict(release_frac=x)), "port"
        c = T.cfg_of("e4", T.enc({a: b for a, b in d.items() if a not in ("what", "x")}))
        c["p"] = dict(c["p"], release_frac=x)
        return c, "win"
    import windport_recheck as RC
    c = RC.cfg_of(batch, row)
    if batch == "extra:pub":                          # handling from the row's hand (Rønne etc.), not the looser base handling
        import windport_runs as T
        import windport_extra as X
        c["p"] = dict(c["p"], **X.GRIDS["pub"]["hand"][T.dec(row["key"])["hand"]])
    return c, ("port" if batch in ("extra:port", "extra:pub") else "win")


def parts(c, signed):
    from windport import bound_dead as BD
    key = json.dumps([{k: v for k, v in c.items() if k not in ("cal", "horizon_h", "n_load", "rule", "record", "unload_release_h")}, signed],
                     sort_keys=True, default=str)
    if key not in _C:
        _C[key] = BD.parts4(c, signed=signed)
    return _C[key]


def one(arg):
    batch, row = arg
    from windport import bound3 as B3
    from windport import bound_dead as BD
    c, form = cfg_of(batch, row)
    G = c["cal"]["crane"][0][0] * H
    f = BD.wfn4(c, dict(parts(c, False), G=G))
    fs = BD.wfn4(c, dict(parts(c, True), G=G))
    out = dict(batch=batch, key=row.get("key") or row.get("i"), map=int(c["geo"].get("kind") == "map"), form=form)
    if form == "port":
        if row.get("port_h") in (None, ""):                # rows not filled within the window (empty port time) are not checked
            return dict(out, skip=1, sim=0, over=0, over_s=0, lstar_hi=0, lstar_s_hi=0)
        n = int(row.get("n_v") or c["n_load"])
        ph = float(row["port_h"]) * H + 0.5e-6 * H
        ls, lss = B3.lstar(f, n)[0] / H, B3.lstar(fs, n)[0] / H
        return dict(out, sim=n, new=f(ph), new_s=fs(ph), over=int(f(ph) < n), over_s=int(fs(ph) < n), port_h=row["port_h"],
                    lstar=round(ls, 6), lstar_s=round(lss, 6), lstar_hi=int(ls > float(row["port_h"]) + 1e-6), lstar_s_hi=int(lss > float(row["port_h"]) + 1e-6))
    L = (c["cal"]["crane"][0][1] - c["cal"]["crane"][0][0]) * H
    sim = int(row["n"] if batch == "runs:random" else row["sim"])
    old = row.get("w1g") if row.get("w1g") not in (None, "") else row.get("w1")
    v, vs = f(L), fs(L)
    return dict(out, sim=sim, new=v, new_s=vs, over=int(sim > v), over_s=int(sim > vs), old=old, tie_old=int(old not in (None, "") and sim == int(float(old))),
                tie=int(sim == v), tie_s=int(sim == vs), group="|".join(str(row.get(k, "")) for k in ("kind", "scen", "mode", "lift", "hold")))


def chunk(items):
    return [one(x) for x in items]


def init():
    pin(list(range(1, os.cpu_count())))


def items():
    out = []
    for part, d in E1E3.items():
        out += [(f"e1e3:{part}", r) for r in load(d) if r.get("repr", "occ") == "occ" and r["key"].split("|")[0] != "fix"]
    for part, d in RUNS.items():
        rows = load(d, "cases.csv") if part == "random" else load(d)
        out += [(f"runs:{part}", r) for r in rows if (part != "random" or r.get("w1g")) and r.get("rep") not in ("fix", "cut")]
    for part, d in EXTRA.items():
        rows = load(d)
        if part == "port":
            rows = [r for r in rows if r["rep"] in ("fcfs", "convoy")]
        if part == "pub":
            rows = [r for r in rows if r["pub"] == "out"]
        out += [(f"extra:{part}", r) for r in rows]
    out.sort(key=lambda x: (x[0], json.dumps({k: v for k, v in x[1].items() if k in ("kind", "scen", "mode", "S", "K", "lift", "hold", "lev", "par", "val",
                                                                                         "arr", "geo", "x", "what", "site")}, sort_keys=True)))
    return out


COLS = ["batch", "key", "map", "form", "sim", "old", "new", "new_s", "over", "over_s", "tie_old", "tie", "tie_s", "port_h", "lstar", "lstar_s", "lstar_hi",
        "lstar_s_hi", "group"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="deadend", round=1, part="recheck", e1e3=E1E3, runs=RUNS, extra=EXTRA, code=code)
    out = ROOT / "results" / ("windport_deadend_recheck_" + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    its = items()
    chunks = [its[k:k + 200] for k in range(0, len(its), 200)]
    prog = Progress(out / "progress.json", len(its), 0, a.procs, "Dead-end coupling recheck: W″ and W″ₛ on the committed batches", "deadend")
    res = []
    try:
        for rs in slot_imap(chunk, chunks, a.procs, initializer=init, slots_dir=a.slots, tag="deadend"):
            res += rs
            prog.write(done=len(res))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    res.sort(key=lambda r: (r["batch"], str(r["key"])))
    with open(out / "rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(res)
    by = collections.defaultdict(list)
    for r in res:
        by[r["batch"]].append(r)
    summ = []
    for b, rs in sorted(by.items()):
        win = [r for r in rs if r["form"] == "win"]
        prt = [r for r in rs if r["form"] == "port"]
        summ.append(dict(batch=b, rows=len(rs), maps=sum(r["map"] for r in rs), win=len(win), port=len(prt), skipped=sum(r.get("skip", 0) for r in rs),
                         over=sum(r["over"] for r in rs), over_s=sum(r["over_s"] for r in rs),
                         tie_old=sum(r["tie_old"] for r in win), tie=sum(r["tie"] for r in win), tie_s=sum(r["tie_s"] for r in win),
                         lstar_hi=sum(r["lstar_hi"] for r in prt), lstar_s_hi=sum(r["lstar_s_hi"] for r in prt)))
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(summ[0]))
        w.writeheader()
        w.writerows(summ)
    g = collections.defaultdict(list)
    for r in by["e1e3:e1"]:
        g[r["group"]].append(r)
    groups = [dict(group=k, n=len(rs), tie_old=sum(r["tie_old"] for r in rs), tie=sum(r["tie"] for r in rs), tie_s=sum(r["tie_s"] for r in rs),
                   gap_old=sum(int(float(r["old"])) - r["sim"] for r in rs), gap=sum(r["new"] - r["sim"] for r in rs)) for k, rs in sorted(g.items())]
    with open(out / "e1_groups.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(groups[0]))
        w.writeheader()
        w.writerows(groups)
    L = ["# Dead-end coupling recheck: W″ and W″ₛ (committed simulation batches, bounds recomputed only)", "",
         "| Batch | Rows | Of which shipyard / shipyard-derived maps | Window form / port-time form | Sim > W″ | Sim > W″ₛ | Equality old bound → W″ → W″ₛ (window form) | L″* > port time / L″ₛ* > port time |",
         "|---|---:|---:|---|---:|---:|---|---|"]
    L += [f"| {s['batch']} | {s['rows']:,} | {s['maps']:,} | {s['win']:,} / {s['port']:,}" + (f" (not filled, not checked: {s['skipped']})" if s["skipped"] else "") +
          f" | {s['over']} | {s['over_s']} | "
          f"{s['tie_old']:,} → {s['tie']:,} → {s['tie_s']:,} | {s['lstar_hi']} / {s['lstar_s_hi']} |" for s in summ]
    tot = {k: sum(s[k] for s in summ) for k in ("rows", "maps", "win", "port", "over", "over_s", "tie_old", "tie", "tie_s", "lstar_hi", "lstar_s_hi")}
    L += [f"| Total | {tot['rows']:,} | {tot['maps']:,} | {tot['win']:,} / {tot['port']:,} | {tot['over']} | {tot['over_s']} | "
          f"{tot['tie_old']:,} → {tot['tie']:,} → {tot['tie_s']:,} | {tot['lstar_hi']} / {tot['lstar_s_hi']} |", "",
          "## E1 equality by group (archetype|scenario|cradle|lifting|Q_h; same grouping as the E1 equality table of the E1-E3 batches, old bound is their W1)", "",
          "| Group | Points | Equal W1 | Equal W″ | Equal W″ₛ | Σ(W1 − sim) | Σ(W″ − sim) |", "|---|---:|---|---|---|---:|---:|"]
    L += [f"| {x['group']} | {x['n']} | {x['tie_old']} ({x['tie_old'] / x['n']:.1%}) | {x['tie']} ({x['tie'] / x['n']:.1%}) | {x['tie_s']} ({x['tie_s'] / x['n']:.1%}) | "
          f"{x['gap_old']} | {x['gap']} |" for x in groups]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    prog.write(state="done", note=f"{tot['rows']} rows; sim > W″ {tot['over']}, > W″ₛ {tot['over_s']}; L″* > port time {tot['lstar_hi']}")
    print(out)
    print("\n".join(L[:40]))


if __name__ == "__main__":
    main()
