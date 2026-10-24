"""Two added rules of the geometry validation and their reruns (main2 geometry, conservative lifting semantics; committed
modules are not changed, the rules are layered on with install()):

  rowsx    Lifting exclusion zone for side-by-side cradles (rows rebuilt in the main2 geometry): when lifting from a cradle in
           row k (the (k + 1)-th closest to the quay), the load passes over rows 0…k−1 closer to the quay, so the segments of
           those rows are also exclusive during [s, s + t_u] while the load is above them (added from the map geometry to both
           windport.lift.under_res and the checker windport.check_lift.under, same range as the row in use: chainage along the
           row (s − L_v, s)). Reruns the side-by-side points with S ≥ 2:
             t7     side-by-side keys of the reach part of the spatial additions (Tables 7 / 14, all reachable) and the
                    reachdist keys of the main2 geometry (distance-based S_r = 1, 2, each far pile t_sh = 1 h);
             cd     side-by-side S ≥ 2 configurations of the joint design (keys reach = all, 1, 2 of windport_design --part codesign).
  spacing  Sensitivity to tandem cradle spacing L_v + δ = 115 m (the main geometry uses 110 m, end clearance 0 between adjacent
           piles): core cases (core_cfg of the main geometry: long single lane / long corridor 1 km/h × on-road / pull-in ×
           S1, S3, S3m × K = 1–8 × Q_h = 0) at 110 and 115 m.
  turnwin  Window-delivery grid of the turn part of the spatial additions (two storage types × cradle mode × base × L = 12 h,
           G = 24 h × K = 1–8 × S = 0–min(4, cradle positions); the same grid as the manuscript sentence "delivery then falls
           by …" and the turn part of the unified-bound recheck), with the alternative-manoeuvre time changed from 600 / 1,800 s
           to lo / hi of the design analyses (extra = 1 / 2 in the key means lo / hi; windport_spatial.turn_extra is replaced by a
           per-turn seconds version).
  tr10     Far → near transfer of exactly 10 piles (grid of windport_design transfer, n = 10), for the voyage-cycle accounting.
Output results/windport_design_<part>_<config hash>/. Run: python experiments/windport_rows_exclusion.py --part rowsx,spacing --procs 22 --slots DIR
"""
import argparse
import hashlib
import itertools
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap, write_json      # noqa: E402
import windport_runs as T                                        # noqa: E402
import windport_design as X                                       # noqa: E402

CODE = X.CODE + ["experiments/windport_rows_exclusion.py", "experiments/windport_rerun_spatial.py", "experiments/windport_maingeom.py", "experiments/windport_main2_runs.py"]
SPACING = dict(scen=["lane", "longslow"], lay=["on_road", "pull_in"], arr=["S1", "S3", "S3m"], K=list(range(1, 9)), spacing=[110.0, 115.0])


def row_of_stop(rid):
    return int(rid.split("_")[1]) if rid.startswith("row_") and rid.split("_")[1].isdigit() else None


def install_rows_exclusion(sim=True, check=True):
    """Adds to lift.under_res (simulation and bound; sim) and check_lift.under (checker; check) the segments of the rows closer
    to the quay that lie within the range of the load."""
    import math
    from windport import check_lift as CL
    from windport import lift as LF
    base_s, base_c = LF.under_res, CL.under

    def under_res(net, sid, Lp, fw):
        out = base_s(net, sid, Lp, fw)
        _, rid, s = net.stops[sid]["node"].split("|")
        k = row_of_stop(rid)
        if not k:
            return out
        s = float(s)
        lo, hi = (s - Lp, s) if fw else (s, s + Lp)
        extra = [("r", q) for q, r in sorted(net.road.items()) if (row_of_stop(r["orig"]) is not None and row_of_stop(r["orig"]) < k
                                                                   and r["s0"] < hi and r["s1"] > lo)]
        return out + [e for e in extra if e not in out]

    def under(net, sid, Lp, fw):
        out = base_c(net, sid, Lp, fw)
        _, rid, s = net.stops[sid]["node"].split("|")
        k = row_of_stop(rid)
        if not k:
            return out
        s = float(s)
        lo, hi = (s - Lp, s) if fw else (s, s + Lp)
        for j in range(k):
            rj = f"row_{j}"
            if rj not in net.D["roads"]:
                continue
            poly = CL.polyline(net.D, net.D["roads"][rj])
            L = sum(math.dist(a, b) for a, b in zip(poly, poly[1:]))
            cuts = [0.0] + list(net.edges.get(rj, [])) + [L]
            names = net.sec.get(rj, [rj])
            out += [("r", q) for q, a, b in zip(names, cuts, cuts[1:]) if a < hi and b > lo and ("r", q) not in out]
        return out
    if sim and not getattr(base_s, "_design", False):
        under_res._design = True
        LF.under_res = under_res
    if check and not getattr(base_c, "_design", False):
        under._design = True
        CL.under = under


def t7_keys():
    import windport_spatial as TA
    import windport_main2_runs as TH
    g = TA.GRIDS["reach"]
    ks = []
    for sc, K, Sn in itertools.product(g["scen"], g["K"], g["side"]["S"]):
        if Sn >= 2:
            ks += [T.enc(dict(lay="side", kind="A1side", scen=sc, mode="side", lift=lf, rule="fcfs", reach="all", L=g["L"], K=K, S=Sn, G=g["G"]))
                   for lf in g["lift"]]
    return ks + [k for k in TH.reachdist_keys() if int(T.dec(k)["S"]) >= 2]


def cd_keys():
    items = X.cd_items()
    return [k for k in X.cd_keys() if items[int(T.dec(k)["cd"])]["lay"] == "side" and items[int(T.dec(k)["cd"])]["S"] >= 2]


def spacing_keys():
    g = SPACING
    return [T.enc(dict(scen=sc, lay=lay, arr=arr, K=K, hold="0", sp=sp)) for sp, sc, lay, arr, K in
            itertools.product(g["spacing"], g["scen"], g["lay"], g["arr"], g["K"])]


def spacing_cfg(d):
    import windport_maingeom as F
    c = F.core_cfg(dict(first=170.0, scen=d["scen"], lay=d["lay"], arr=d["arr"], K=int(d["K"]), hold=d["hold"], extra=0.0))
    if float(d["sp"]) != 110.0:
        c["geo"] = dict(c["geo"], cradle_spacing=float(d["sp"]))
    return c


TURNWIN = {1.0: "lo", 2.0: "hi"}


def tr10_keys():
    """Far → near transfer of exactly one voyage, 10 piles (windport_design --part transfer uses 30 piles to check the bound pile
    by pile; the voyage-cycle accounting needs a transfer of only 10)."""
    return [k.replace("|n=30|", "|n=10|") for k in X.transfer_keys()]


def turnwin_keys():
    import windport_spatial as TA
    g, out = TA.GRIDS["turn"], []
    for site, st, m, x in itertools.product(g["sites"], g["storage"], T.MODES, sorted(TURNWIN)):
        for K, Sn in itertools.product(g["K"], range(0, min(4, T.NC[site]) + 1)):
            out.append(T.enc(dict(kind="map:" + site, st=st, scen="base", mode=m, lift=T.lift_of(Sn), rule="fcfs", L=g["L"], K=K, S=Sn, G=g["G"], extra=x)))
    return out


def install_turnwin():
    import windport_spatial as TA
    import windport_design_lib as L
    TA.turn_extra = lambda site, st, x: L.turn_extra(site, st, "base", TURNWIN[float(x)])


def compute(part, key):
    if part == "tr10":
        return dict(X.port_point(X.transfer_cfg(T.dec(key))), **T.dec(key))
    if part == "turnwin":
        import windport_rerun_spatial as E
        return E.run_point("turn", key)
    if part == "rowsx:t7":
        import windport_rerun_spatial as E
        return E.run_point("reach", key)
    if part == "rowsx:cd":
        return dict(X.port_point(X.cd_cfg(T.dec(key)), all_j=False), **T.dec(key))
    if part == "spacing":
        return dict(X.port_point(spacing_cfg(T.dec(key)), all_j=True), **T.dec(key))
    raise KeyError(part)


def install(part_rows):
    import windport_main2_runs as TH
    X.setup_env()
    TH.install()                                     # main2 geometry: side-by-side replaced by the rebuilt rows (windport_spatial.cfg_of wrapped by main2.rows_cfg), checker and ordering of the conservative lifting rule
    from windport import check as C
    from windport import check_all as CA
    C.check = CA.check
    if part_rows:
        install_rows_exclusion()
    install_turnwin()


_OUTS = {}


def init(outs, rows_on):
    pin(list(range(1, os.cpu_count())))
    install(rows_on)
    _OUTS.update({k: Path(v) for k, v in outs.items()})


def chunk(arg):
    part, ks = arg
    for k in ks:
        f = _OUTS[part] / "points" / T.fname(k)
        if not f.exists():
            write_json(f, dict(compute(part, k), key=k))
    return part, ks


def out_dir(name, extra):
    from windport import archetypes as A
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="design", part=name, geometry=A.GEOMETRIES[X.GEO], code=code, **extra)
    return ROOT / "results" / f"windport_design_{name.replace(':', '_')}_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}", cfg


def run(parts, a, rows_on):
    outs, progs, chunks, ks = {}, {}, [], {}
    for part in parts:
        extra = dict(rule="rows_exclusion" if part.startswith("rowsx") else "none", spacing=SPACING if part == "spacing" else None,
                     semantics="lift_tu0.05_head", **(X.turn_input() if part in ("turnwin", "tr10") else {}))
        out, cfg = out_dir(part, extra)
        X.prepare(out, cfg)
        outs[part] = out
        ks[part] = dict(**{"rowsx:t7": t7_keys, "rowsx:cd": cd_keys, "spacing": spacing_keys, "turnwin": turnwin_keys, "tr10": tr10_keys})[part]()
        todo = [k for k in ks[part] if not (out / "points" / T.fname(k)).exists()]
        progs[part] = Progress(out / "progress.json", len(ks[part]), len(ks[part]) - len(todo), a.procs, f"design {part}", "design")
        chunks += [(part, todo[i:i + a.chunk]) for i in range(0, len(todo), a.chunk)]
    try:
        for part, ds in slot_imap(chunk, chunks, a.procs, initializer=init, initargs=({k: str(v) for k, v in outs.items()}, rows_on), slots_dir=a.slots,
                                  tag="design"):
            progs[part].write(done=progs[part].d["done"] + len(ds))
    except BaseException as e:
        for pg in progs.values():
            pg.write(state="failed", note=repr(e)[:300])
        raise
    for part, out in outs.items():
        rs = [json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8")) for k in ks[part]]
        if part in ("rowsx:t7", "turnwin"):
            import windport_rerun_spatial as E
            rows = [E.row_of(k, r) for k, r in zip(ks[part], rs)]
            over = sum(1 for r in rows if r.get("w4") not in (None, "") and r["sim"] > r["w4"])
            note = f"{len(rows)} points; checker failures {sum(1 for r in rows if not r['check_ok'])}; above W″_lift {over}; under-load checks {sum(r['n_under'] for r in rows)}"
        else:
            rows = [X.sim_row(part, k, r) for k, r in zip(ks[part], rs)]
            lb = sum(1 for r in rs if r["port_h"] is not None and r["port_h"] < r["lstar_lo"] - 1e-9)
            note = f"{len(rows)} points; checker failures {sum(1 for r in rs if not r['check_ok'])}; port time < L″_lift* {lb}; W″_lift(T_j) < j {sum(int(r['viol'] or 0) for r in rs)}"
        X.wcsv(out / "points.csv", rows)
        progs[part].write(state="done", note=note)
        print(out.name, note)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, help="rowsx (= rowsx:t7,rowsx:cd), spacing")
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    parts = [p for q in a.part.split(",") for p in (["rowsx:t7", "rowsx:cd"] if q == "rowsx" else [q])]
    rx = [p for p in parts if p.startswith("rowsx")]
    if rx:
        install(True)
        run(rx, a, True)
    rest = [p for p in parts if p in ("spacing", "turnwin", "tr10")]
    if rest:
        run(rest, a, False)


if __name__ == "__main__":
    main()
