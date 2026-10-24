"""Alternative turns with a 1 m clearance: the feasibility test adds 1 m clearance and all selected manoeuvres are re-judged.
windport_turn_alt.py is left unchanged (it is in the code hash of the design-analysis batches); on import this module
replaces its Grid and analyse with:
  · the obstacle grid (buildings + water) is first dilated by CLEAR_M (3 × 3 neighbourhood, at least 1 m clearance on a 1 m
    grid), then all road surface is removed;
  · the selected manoeuvre is rechecked with dense sampling (0.5 m along the pile, 11 lines across, motion step 0.5 m); if the
    recheck fails, the next candidate in order of duration is tried (at most MAX_TRY); if none passes, the family is infeasible.
Run (reruns --part turn; the configuration of the result directory also records clear_m and the SHA-256 of this module):
  python experiments/windport_turn_alt_clear.py --procs 6 --slots DIR
"""
import argparse
import hashlib
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_turn_alt as TI                                 # noqa: E402

CLEAR_M = 1.0
FINE = dict(ds=0.5, nt=11, step=0.5)
MAX_TRY = 40
_Grid = TI.Grid


def dilate(m, r):
    out = m.copy()
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            if di == 0 and dj == 0:
                continue
            s = np.zeros_like(m)
            a0, a1 = max(0, di), m.shape[0] + min(0, di)
            b0, b1 = max(0, dj), m.shape[1] + min(0, dj)
            s[a0:a1, b0:b1] = m[a0 - di:a1 - di, b0 - dj:b1 - dj]
            out |= s
    return out


class Grid(_Grid):
    def __init__(self, xy, layers, roads):
        super().__init__(xy, layers, roads)
        r = max(1, int(math.ceil(CLEAR_M / TI.RES)))
        self.block = dilate(self.mask["building"] | self.mask["water"], r) & ~self.road


def body_fine(L, B):
    s = np.arange(-L / 2, L / 2 + 1e-9, FINE["ds"])
    t = np.linspace(-B / 2, B / 2, FINE["nt"])
    S, T_ = np.meshgrid(s, t, indexing="ij")
    return np.stack([S.ravel(), T_.ravel()], 1)


def sweep_fine(c, J, hin, dA, dB, L, B, bd):
    st = FINE["step"]
    X = (J[0] + c["s"] * dA[0], J[1] + c["s"] * dA[1])
    F = (J[0] + c["f"] * dB[0], J[1] + c["f"] * dB[1])
    hout = hin + c["a"]
    parts = []
    if c["s"] > 0:
        parts.append(TI.translate(bd, J, X, hin, st))
    if c["fam"][0] == "R":
        parts.append(TI.rotate(bd, X, hin, c["C"], c["a"], TI.rmax_of(X, hin, c["C"], L, B), st))
    else:
        P = c["P"]
        parts += [TI.translate(bd, X, P, hin, st), TI.rotate(bd, P, hin, P, c["a"], math.hypot(L / 2, B / 2), st), TI.translate(bd, P, F, hout, st)]
    if c["f"] < 0:
        parts.append(TI.translate(bd, F, J, hout, st))
    return np.concatenate(parts)


def analyse(G, J, hin, th, L, B, speeds):
    """As windport_turn_alt.analyse, but the selected manoeuvre is rechecked with dense sampling (dilated obstacle grid);
    if it fails, the next candidate is tried."""
    bd = TI.body(L, B, TI.STEP_TIP)
    fine = body_fine(L, B)
    base = dict(fam="R+", a=th, s=0.0, lam=0.0, C=J, f=0.0)
    dA, dB = (math.cos(hin), math.sin(hin)), (math.cos(hin + th), math.sin(hin + th))
    pts = sweep_fine(base, J, hin, dA, dB, L, B, fine)
    out = dict(base_block=G.count(pts), base_other=G.count(pts, "other"))
    cands, dA, dB = TI.candidates(J, hin, th, L, B)
    feas = []
    for c in cands:
        p = TI.sweep(c, J, hin, dA, dB, L, B, bd)
        if G.count(p) == 0:
            feas.append(dict(c, clean=G.count(p, "other") == 0))
    out["n_cand"], out["n_feas"], out["n_clean"] = len(cands), len(feas), sum(c["clean"] for c in feas)
    fams = {}
    for c in feas:
        fams.setdefault(c["fam"], []).append(c)
    out["fams"], out["n_try"] = {}, 0
    for fam, cs in sorted(fams.items()):
        for want_clean in (True, False):
            pool = [c for c in cs if c["clean"]] if want_clean else cs
            if not pool:
                continue
            done = {}
            for vn, v in speeds.items():
                for k, tsw in enumerate(TI.TSW):
                    for c0 in sorted(pool, key=lambda c: TI.extra_s(c, J, hin, th, L, B, v, tsw)[0])[:MAX_TRY]:
                        out["n_try"] += 1
                        c1 = TI.refine(c0, J, hin, th, dA, dB, L, B, bd, G, v, tsw, want_clean)
                        ok = None
                        for cc in (c1, c0):
                            pf = sweep_fine(cc, J, hin, dA, dB, L, B, fine)
                            if G.count(pf) == 0 and (not want_clean or G.count(pf, "other") == 0):
                                ok = cc
                                break
                        if ok is None:
                            continue
                        t, info = TI.extra_s(ok, J, hin, th, L, B, v, tsw)
                        pf = sweep_fine(ok, J, hin, dA, dB, L, B, fine)
                        done[f"{fam}|{vn}|{k}"] = dict(t=round(float(t), 1), s=round(float(ok["s"]), 1), lam=round(float(ok.get("lam", 0.0)), 1),
                                                       u=round(float(ok.get("u", 0.0)), 1), f=round(float(ok["f"]), 1), clean=int(want_clean),
                                                       other=G.count(pf, "other"), ok_fine=1,
                                                       **{a: (float(b) if isinstance(b, (float, np.floating)) else b) for a, b in info.items()})
                        break
            if len(done) == len(speeds) * len(TI.TSW):
                out["fams"].update(done)
                break
            if not want_clean or not [c for c in cs if not c["clean"]]:
                out["fams"].update(done)
                break
    return out


TI.Grid, TI.analyse = Grid, analyse                               # takes effect on import (worker processes import this module via turn_one)
import windport_design as X                                       # noqa: E402
_ORIG_ONE = X.turn_one                                           # the original function looks up TI.Grid / TI.analyse as module attributes, i.e. the versions replaced above


def turn_one(arg):
    return _ORIG_ONE(arg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--slots", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    X.setup_env()
    od = X.out_dir
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    X.out_dir = lambda name, extra=None: od(name, dict(extra or {}, clear_m=CLEAR_M, fine=FINE, max_try=MAX_TRY, turn1m_sha256=sha))
    X.turn_one = turn_one
    try:
        X.run_turn(a)
    finally:
        X.out_dir, X.turn_one = od, _ORIG_ONE


if __name__ == "__main__":
    main()
