"""Design analyses: all corridor options of the long-single-lane codesign (single lane, passing places, widened to 16 m, both) rerun with uniform
block signalling.

Block signalling: the existing occupancy retrofit blocks (p["retrofit"] = [{"kind": "blocks", "road": road, "len": BLOCK_M}]) splits each corridor
road of the port-type record (windport.corridor: the single lane corr_lane_0; with passing places, the two narrow sections and the wide section
between them) evenly into blocks of length ≤ BLOCK_M. A block is an independent width resource: vehicles in the same direction may follow block by
block (as when the single lane is split into chain blocks by branch junctions; the chain cut of Corollary 3 counts per block); opposing vehicles in
adjacent blocks overlap in body length within their windows and cannot swap positions at a block boundary, so opposing traffic on the single lane
stays mutually exclusive. After widening to 16 m a block fits one loaded and one empty vehicle passing each other, but not two loaded ones. Block
length BLOCK_M = 150 m (= length of the passing-place wide section, which is exactly one block).
Pure-loaded cut term (the cut terms of Corollary 1 / Theorems 1, 2 with t_e = 0; see the manuscript): for every road r that all loaded loading
trips pass in full and on which two loaded vehicles do not fit (whether or not empty vehicles can pass),
  window: N ≤ S + K + ⌊(L − p)/t_ℓ(r)⌋; empty system: N ≤ ⌊(G + L − p − h_p)/t_ℓ(r)⌋;
t_ℓ(r) = loaded occupancy lower bound of windport.bound.occupancy_times(cut = r), with d_q = 0 and K vehicles on the quay side (both loose, so the
bound still holds). Added to W″ / W″_lift via bound_all.terms.
Recomputed: the long-single-lane codesign configurations (all tandem, side-by-side S ≤ 1, side-by-side S ≥ 2 with full reach and with reach by
distance S_r = 1, 2 picking the quay position by lift-finish time), with the per-pile check W″_lift(T_j) ≥ j.
The base port is unchanged (its corridor has one branch junction and is already split into two blocks) and is reused.
Output results/windport_design_cdblk_<config hash>/. Run: python experiments/windport_codesign_blocks.py --procs 22 --slots DIR
"""
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from batch import Progress, pin, slot_imap, write_json      # noqa: E402
import windport_runs as T                                        # noqa: E402
import windport_design as X                                       # noqa: E402
import windport_rows_exclusion as RX                                # noqa: E402

BLOCK_M = 150.0
CODE = RX.CODE + ["experiments/windport_codesign_finish.py", "experiments/windport_codesign_blocks.py"]


# ---------------------------------------------------------------- pure-loaded cut term
def ll_cuts(cfg):
    """[(resource, t_ℓ)]: roads that all loaded routes (saddle row, quay position) pass in full (not on the apron or at the stops) and on
    which two loaded vehicles do not fit."""
    from occupancy.network import EPS
    from windport import bound as WB
    from windport import bound2 as W2
    from windport import sim4 as S4
    D, net, p, *_ = S4.setup4(cfg)
    W = D["windport"]
    rows, quay = W["storage"], W["cradles"][:max(1, cfg["S"])]
    cap, _ = net.capacities(p)
    common = None
    for o in rows:
        for d in quay:
            rs = {("r", net.arc[a][3]) for a in net.path(net.stops[o]["node"], net.stops[d]["node"])}
            common = rs if common is None else common & rs
    skip = {("r", r) for r in W.get("apron") or []} | {net.stops[s]["res"] for s in rows + quay}
    lift = "direct" if cfg["S"] == 0 else cfg.get("lift", "cradle")
    pt = dict(p, load_s=p["hp_s"], unload_s=0.0 if lift in ("direct", "mixed") else p["hd_s"])
    out = []
    for c in sorted(common - skip, key=str):
        if not W2.excl(cap, c, p, p["B"], p["plat_w"], "ll"):
            continue
        try:
            t = WB.occupancy_times(net, pt, rows, quay, p["Lv"], p["B"], cut=c)
        except AssertionError:
            continue
        if t["tl"] > EPS:
            out.append((c, t["tl"]))
    return out


def install_ll():
    """bound_all.parts also records t_ℓ of the pure-loaded cuts; bound_all.terms adds two terms ("cut_ll" counted as road, "prep_ll" as
    preparation time)."""
    from windport import bound_all as BA
    if getattr(BA.terms, "_design", False):
        return
    parts0, terms0 = BA.parts, BA.terms

    def parts(cfg, lift=False, signed=True):
        w = parts0(cfg, lift, signed)
        return dict(w, ll=ll_cuts(cfg), K_ll=cfg["K"], S_ll=cfg["S"])

    def terms(w, L, empty=True):
        t = terms0(w, L, empty)
        ll = w.get("ll") or []
        if ll:
            P = w["P"]
            tl = max(x for _, x in ll)
            t["cut_ll"] = w["S_ll"] + w["K_ll"] + (math.floor((L - P.p) / tl + 1e-9) if L >= P.p else 0)
            if empty:
                t["prep_ll"] = max(0, math.floor((w["G"] + L - P.p - w["hp"]) / tl + 1e-9))
        return t
    terms._design = True
    BA.parts, BA.terms = parts, terms
    BA.CLASS["cut_ll"], BA.CLASS["prep_ll"] = "road", "road"
    BA.PREP.add("prep_ll")


# ---------------------------------------------------------------- points
def corridor_roads(c):
    from windport import sim4 as S4
    D = S4.build_map4(c["geo"])
    return list(D["windport"]["corridor"]) + [r for r in D["roads"] if r.startswith("corr_lane_0_p")]


def blk_cfg(d):
    c = X.cd_cfg(d)
    if d.get("disp") == "finish":
        c["p"] = dict(c["p"], reach_key="finish")
    roads = sorted(set(corridor_roads(c)))
    c["p"] = dict(c["p"], retrofit=[dict(kind="blocks", road=r, len=BLOCK_M) for r in roads])
    return c


def keys():
    items = X.cd_items()
    out = []
    for k in X.cd_keys():
        d = T.dec(k)
        x = items[int(d["cd"])]
        if x["scen"] != "lane":
            continue
        if x["lay"] == "side" and x["S"] >= 2:
            out.append(k + "|disp=finish" if d["reach"] in ("1", "2") else k)
        else:
            out.append(k)
    return out


def compute(key):
    d = T.dec(key)
    return dict(X.port_point(blk_cfg(d), all_j=True), **d)


_OUT = None


def init(out):
    global _OUT
    pin(list(range(1, os.cpu_count())))
    RX.install(True)
    install_ll()
    _OUT = Path(out)


def chunk(ks):
    for k in ks:
        f = _OUT / "points" / T.fname(k)
        if not f.exists():
            write_json(f, dict(compute(k), key=k))
    return ks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--slots", default=None)
    ap.add_argument("--chunk", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    RX.install(True)
    install_ll()
    from windport import archetypes as A
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="design", part="cdblk", geometry=A.GEOMETRIES[X.GEO], code=code, block_m=BLOCK_M, rule="rows_exclusion", semantics="lift_tu0.05_head")
    out = ROOT / "results" / f"windport_design_cdblk_{hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]}"
    X.prepare(out, cfg)
    ks = keys()
    todo = [k for k in ks if not (out / "points" / T.fname(k)).exists()]
    prog = Progress(out / "progress.json", len(ks), len(ks) - len(todo), a.procs, "design analyses cdblk (long-single-lane codesign, uniform block signalling)", "design")
    try:
        for ds in slot_imap(chunk, [todo[i:i + a.chunk] for i in range(0, len(todo), a.chunk)], a.procs, initializer=init, initargs=(str(out),),
                            slots_dir=a.slots, tag="design"):
            prog.write(done=prog.d["done"] + len(ds))
    except BaseException as e:
        prog.write(state="failed", note=repr(e)[:300])
        raise
    rs = [json.loads((out / "points" / T.fname(k)).read_text(encoding="utf-8")) for k in ks]
    X.wcsv(out / "points.csv", [X.sim_row("codesign", k, r) for k, r in zip(ks, rs)])
    lb = sum(1 for r in rs if r["port_h"] is not None and r["port_h"] < r["lstar_lo"] - 1e-9)
    vi = sum(int(r["viol"] or 0) for r in rs)
    note = f"{len(rs)} points; checker failures {sum(1 for r in rs if not r['check_ok'])}; port time < L″_lift* {lb}; W″_lift(T_j) < j for {vi} piles (of {sum(r['lifts'] for r in rs)})"
    prog.write(state="done", note=note)
    print(out.name, note)


if __name__ == "__main__":
    main()
