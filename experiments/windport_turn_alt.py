"""Alternative turns of the design analyses: feasibility and kinematic duration (reads only the two maps, Okpo and Yantai;
outputs only node ids, counts and distances, no maps).

Objects: turns on the loaded loading routes (and on the far → near transfer routes of the two-tier storage) where the
road-occupancy model stops to steer (turn angle ≥ turn_deg) and the sector of an in-place rotation centred on the junction
hits buildings or water (the same criterion as the sweep test of the spatial additions; obstacles / sweep_pts / hits of
windport_turn_sweep reused as they are).
For each such turn, three families of alternative manoeuvres are searched on a grid of ±HALF m around the junction (RES m;
building and water polygons minus all road surface: road polylines widened by widthM):
  R+  early steering (offset rotation): rotate through the original angle θ about a point C that is not the pile centre (a
      large-radius all-wheel-steer turn, starting before or past the junction). C lies on the line C = J + λ(I − R_θ)⁻¹d_B that
      maps the incoming axis onto the outgoing axis; the pile centre starts on the incoming axis at X = J + s·d_A and ends on
      the outgoing axis at F = J + (λ + s)·d_B;
  R−  reverse departure: as above, rotating through θ − π·sgn θ (the pile axis again lands on the outgoing road, the vehicle
      leaves in reverse);
  C±  crabbing: at X on the incoming axis move sideways by u to P = X + u·n_A, rotate in place about P by θ or θ − π·sgn θ,
      then move sideways onto the outgoing axis at F (projection of P on the outgoing road).
A candidate is feasible if no sample point of the swept area (straight run past the junction on the incoming road, sideways
moves, rotation, straight run behind the junction on the outgoing road) falls in the obstacle grid; whether it hits "other
occupancy" (yards, assembly areas, etc., the third layer of the spatial additions) is recorded separately.
Duration (in addition to the in-place rotation stop δ = 120 s + θ·L_v/2/v, lower limit 0):
  straight change (s − f)/v + rotation change (|α|·r_max − |θ|·L_v/2)/v + sideways (|u| + |F − P|)/v + for the lateral family
  2 steering-mode switches t_sw;
  r_max is the largest distance from a point of the pile to C, v is the loaded speed of the scenario (reversing and crabbing at
  the same speed: not given in public sources, the known speed is used), t_sw ∈ TSW (no value in seconds in public sources).
Classes: R+ feasible → "early steering"; otherwise R− or C± feasible → "reversing or crabbing"; none feasible → "no space
  (operator to confirm)", with the generic duration L_v/v + Δw/v + 2·t_sw (Δw = road-width difference between outgoing and
  incoming road, at least B); an in-place rotation centred on the junction that is feasible once road surface is removed is
  recorded as "in-place feasible (road surface only)".
"""
import math
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_turn_sweep as TA                                 # noqa: E402
from windport import shipyard as SY                              # noqa: E402
from windport import sim as WS                                   # noqa: E402

RES, HALF = 1.0, 260.0            # m: grid resolution, half-width of the window around the junction
TSW = (30.0, 300.0)               # s: one steering-mode switch (public sources only say "switchable within seconds" and switchable when stopped and fully loaded, no value; assumed interval 30–300 s)
GRID = dict(s=(-110.0, 110.0, 10.0), lam=(-160.0, 160.0, 10.0), u=(-110.0, 110.0, 10.0), fine=2.5)
STEP_TIP, NT = 2.0, 3             # sampling: each point of the pile moves at most STEP_TIP m per step; NT points across


# ---------------------------------------------------------------- grid
class Grid:
    def __init__(self, xy, layers, roads):
        self.x0, self.y0 = xy[0] - HALF, xy[1] - HALF
        self.n = int(round(2 * HALF / RES))
        c = (np.arange(self.n) + 0.5) * RES
        X, Y = np.meshgrid(self.x0 + c, self.y0 + c, indexing="ij")
        self.mask = {}
        for k, polys in layers.items():
            m = np.zeros((self.n, self.n), bool)
            for P, (a, b, cc, d) in polys:
                if cc < self.x0 or a > self.x0 + 2 * HALF or d < self.y0 or b > self.y0 + 2 * HALF:
                    continue
                i0, i1 = max(0, int((a - self.x0) / RES)), min(self.n, int((cc - self.x0) / RES) + 1)
                j0, j1 = max(0, int((b - self.y0) / RES)), min(self.n, int((d - self.y0) / RES) + 1)
                if i1 <= i0 or j1 <= j0:
                    continue
                pts = np.stack([X[i0:i1, j0:j1].ravel(), Y[i0:i1, j0:j1].ravel()], 1)
                m[i0:i1, j0:j1] |= MPath(P).contains_points(pts).reshape(i1 - i0, j1 - j0)
            self.mask[k] = m
        road = np.zeros((self.n, self.n), bool)
        for pts, w in roads:
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                lo_x, hi_x = min(ax, bx) - w / 2, max(ax, bx) + w / 2
                lo_y, hi_y = min(ay, by) - w / 2, max(ay, by) + w / 2
                if hi_x < self.x0 or lo_x > self.x0 + 2 * HALF or hi_y < self.y0 or lo_y > self.y0 + 2 * HALF:
                    continue
                i0, i1 = max(0, int((lo_x - self.x0) / RES)), min(self.n, int((hi_x - self.x0) / RES) + 1)
                j0, j1 = max(0, int((lo_y - self.y0) / RES)), min(self.n, int((hi_y - self.y0) / RES) + 1)
                px, py = X[i0:i1, j0:j1], Y[i0:i1, j0:j1]
                dx, dy = bx - ax, by - ay
                L2 = dx * dx + dy * dy
                t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0, 1) if L2 > 0 else 0.0
                road[i0:i1, j0:j1] |= (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2 <= (w / 2) ** 2
        self.road = road
        self.block = (self.mask["building"] | self.mask["water"]) & ~road
        self.other = self.mask["other"] & ~road

    def count(self, pts, which="block"):
        i = np.floor((pts[:, 0] - self.x0) / RES).astype(int)
        j = np.floor((pts[:, 1] - self.y0) / RES).astype(int)
        ok = (i >= 0) & (i < self.n) & (j >= 0) & (j < self.n)
        return int(getattr(self, which)[i[ok], j[ok]].sum())


# ---------------------------------------------------------------- sampling
def body(L, B, ds):
    s = np.arange(-L / 2, L / 2 + 1e-9, ds)
    t = np.linspace(-B / 2, B / 2, NT)
    S, T_ = np.meshgrid(s, t, indexing="ij")
    return np.stack([S.ravel(), T_.ravel()], 1)                 # pile frame (along axis, across)


def pose(bd, X, h):
    c, s = math.cos(h), math.sin(h)
    return np.stack([X[0] + bd[:, 0] * c - bd[:, 1] * s, X[1] + bd[:, 0] * s + bd[:, 1] * c], 1)


def translate(bd, X0, X1, h, step=STEP_TIP):
    d = math.dist(X0, X1)
    n = max(1, int(math.ceil(d / step)))
    return np.concatenate([pose(bd, (X0[0] + (X1[0] - X0[0]) * k / n, X0[1] + (X1[1] - X0[1]) * k / n), h) for k in range(n + 1)])


def rotate(bd, X, h, C, a, rmax, step=STEP_TIP):
    n = max(1, int(math.ceil(abs(a) * rmax / step)))
    out = []
    for k in range(n + 1):
        b = a * k / n
        cb, sb = math.cos(b), math.sin(b)
        Y = (C[0] + (X[0] - C[0]) * cb - (X[1] - C[1]) * sb, C[1] + (X[0] - C[0]) * sb + (X[1] - C[1]) * cb)
        out.append(pose(bd, Y, h + b))
    return np.concatenate(out)


def rmax_of(X, h, C, L, B):
    c, s = math.cos(h), math.sin(h)
    return max(math.dist(C, (X[0] + a * c - b * s, X[1] + a * s + b * c)) for a in (-L / 2, L / 2) for b in (-B / 2, B / 2))


# ---------------------------------------------------------------- one turn
def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def candidates(J, hin, th, L, B):
    """Coarse parameter grid of the three families: each candidate is dict(fam, α, segments)."""
    dA, dB = (math.cos(hin), math.sin(hin)), (math.cos(hin + th), math.sin(hin + th))
    nA = (-dA[1], dA[0])
    rng = lambda a: np.arange(a[0], a[1] + 1e-9, a[2])
    out = []
    for sense, fam_r, fam_c in ((1, "R+", "C+"), (-1, "R-", "C-")):
        a = th if sense == 1 else th - math.copysign(math.pi, th)
        if abs(a) < 1e-6:
            continue
        ca, sa = math.cos(a), math.sin(a)
        M = np.linalg.inv(np.array([[1 - ca, sa], [-sa, 1 - ca]]))  # (I − R_a)⁻¹
        md = M @ np.array(dB)
        sgn = 1.0 if sense == 1 else -1.0                         # R_a d_A = sgn·d_B
        for lam in rng(GRID["lam"]):
            for s in rng(GRID["s"]):
                C = (J[0] + lam * md[0], J[1] + lam * md[1])
                out.append(dict(fam=fam_r, a=a, s=float(s), lam=float(lam), C=C, f=float(lam + sgn * s)))
        for s in rng(GRID["s"]):
            for u in rng(GRID["u"]):
                X = (J[0] + s * dA[0], J[1] + s * dA[1])
                P = (X[0] + u * nA[0], X[1] + u * nA[1])
                f = (P[0] - J[0]) * dB[0] + (P[1] - J[1]) * dB[1]
                out.append(dict(fam=fam_c, a=a, s=float(s), u=float(u), P=P, f=float(f)))
    return out, dA, dB


def sweep(c, J, hin, dA, dB, L, B, bd):
    """Swept sample points of a candidate (incoming run past the junction, sideways moves, rotation, outgoing run behind the junction)."""
    X = (J[0] + c["s"] * dA[0], J[1] + c["s"] * dA[1])
    F = (J[0] + c["f"] * dB[0], J[1] + c["f"] * dB[1])
    hout = hin + c["a"]
    parts = []
    if c["s"] > 0:
        parts.append(translate(bd, J, X, hin))
    if c["fam"][0] == "R":
        parts.append(rotate(bd, X, hin, c["C"], c["a"], rmax_of(X, hin, c["C"], L, B)))
    else:
        P = c["P"]
        parts += [translate(bd, X, P, hin), rotate(bd, P, hin, P, c["a"], math.hypot(L / 2, B / 2)), translate(bd, P, F, hout)]
    if c["f"] < 0:
        parts.append(translate(bd, F, J, hout))
    return np.concatenate(parts)


def extra_s(c, J, hin, th, L, B, v, tsw):
    """Duration in addition to the in-place rotation stop (s, lower limit 0)."""
    dA = (math.cos(hin), math.sin(hin))
    X = (J[0] + c["s"] * dA[0], J[1] + c["s"] * dA[1])
    straight = (c["s"] - c["f"]) / v
    if c["fam"][0] == "R":
        rot = (abs(c["a"]) * rmax_of(X, hin, c["C"], L, B) - abs(th) * L / 2) / v
        return max(0.0, straight + rot), dict(straight_m=round(c["s"] - c["f"], 1), rmax_m=round(rmax_of(X, hin, c["C"], L, B), 1), crab_m=0.0, n_sw=0)
    P = c["P"]
    dB = (math.cos(hin + th), math.sin(hin + th))
    F = (J[0] + c["f"] * dB[0], J[1] + c["f"] * dB[1])
    crab = abs(c["u"]) + math.dist(P, F)
    rot = (abs(c["a"]) - abs(th)) * L / 2 / v
    return max(0.0, straight + crab / v + rot + 2 * tsw), dict(straight_m=round(c["s"] - c["f"], 1), rmax_m=round(L / 2, 1), crab_m=round(crab, 1), n_sw=2)


def refine(c, J, hin, th, dA, dB, L, B, bd, G, v, tsw, clean):
    """Refines around a feasible candidate with step GRID["fine"] and keeps the shortest feasible one (with clean, it must also
    not hit other occupancy)."""
    best = c
    step = GRID["fine"]
    keys = ("lam", "s") if c["fam"][0] == "R" else ("s", "u")
    base_t = extra_s(c, J, hin, th, L, B, v, tsw)[0]
    for d1 in np.arange(-GRID["s"][2], GRID["s"][2] + 1e-9, step):
        for d2 in np.arange(-GRID["s"][2], GRID["s"][2] + 1e-9, step):
            x = rebuild(dict(c, **{keys[0]: c[keys[0]] + d1, keys[1]: c[keys[1]] + d2}), J, hin, th)
            t = extra_s(x, J, hin, th, L, B, v, tsw)[0]
            if t < base_t - 1e-9:
                pts = sweep(x, J, hin, dA, dB, L, B, bd)
                if G.count(pts) == 0 and (not clean or G.count(pts, "other") == 0):
                    best, base_t = x, t
    return best


def rebuild(c, J, hin, th):
    dA, dB = (math.cos(hin), math.sin(hin)), (math.cos(hin + th), math.sin(hin + th))
    a = c["a"]
    if c["fam"][0] == "R":
        ca, sa = math.cos(a), math.sin(a)
        md = np.linalg.inv(np.array([[1 - ca, sa], [-sa, 1 - ca]])) @ np.array(dB)
        sgn = 1.0 if c["fam"] == "R+" else -1.0
        return dict(c, C=(J[0] + c["lam"] * md[0], J[1] + c["lam"] * md[1]), f=float(c["lam"] + sgn * c["s"]))
    nA = (-dA[1], dA[0])
    X = (J[0] + c["s"] * dA[0], J[1] + c["s"] * dA[1])
    P = (X[0] + c["u"] * nA[0], X[1] + c["u"] * nA[1])
    return dict(c, P=P, f=float((P[0] - J[0]) * dB[0] + (P[1] - J[1]) * dB[1]))


def analyse(G, J, hin, th, L, B, speeds):
    """One turn: whether the in-place rotation (road surface removed) is feasible; feasible candidates (no building or water;
    clean = also no other occupancy); for each family, speed v (speeds: name → m/s) and both ends of TSW, the shortest feasible
    alternative manoeuvre (the shortest clean one if any is clean)."""
    bd = body(L, B, STEP_TIP)
    fine = body(L, B, 1.0)
    base = dict(fam="R+", a=th, s=0.0, lam=0.0, C=J, f=0.0)
    dA, dB = (math.cos(hin), math.sin(hin)), (math.cos(hin + th), math.sin(hin + th))
    pts = sweep(base, J, hin, dA, dB, L, B, bd)
    out = dict(base_block=G.count(pts), base_other=G.count(pts, "other"))
    cands, dA, dB = candidates(J, hin, th, L, B)
    feas = []
    for c in cands:
        pts = sweep(c, J, hin, dA, dB, L, B, bd)
        if G.count(pts) == 0:
            feas.append(dict(c, clean=G.count(pts, "other") == 0))
    out["n_cand"], out["n_feas"], out["n_clean"] = len(cands), len(feas), sum(c["clean"] for c in feas)
    fams = {}
    for c in feas:
        fams.setdefault(c["fam"], []).append(c)
    out["fams"] = {}
    for fam, cs in sorted(fams.items()):
        pool = [c for c in cs if c["clean"]] or cs
        clean = pool[0]["clean"]
        for vn, v in speeds.items():
            for k, tsw in enumerate(TSW):
                c0 = min(pool, key=lambda c: extra_s(c, J, hin, th, L, B, v, tsw)[0])
                c1 = refine(c0, J, hin, th, dA, dB, L, B, bd, G, v, tsw, clean)
                t, info = extra_s(c1, J, hin, th, L, B, v, tsw)
                pf = sweep(c1, J, hin, dA, dB, L, B, fine)
                out["fams"][f"{fam}|{vn}|{k}"] = dict(t=round(float(t), 1), s=round(float(c1["s"]), 1), lam=round(float(c1.get("lam", 0.0)), 1),
                                                     u=round(float(c1.get("u", 0.0)), 1), f=round(float(c1["f"]), 1), clean=int(clean),
                                                     other=G.count(pf, "other"), ok_fine=int(G.count(pf) == 0),
                                                     **{a: (float(b) if isinstance(b, (float, np.floating)) else b) for a, b in info.items()})
    return out


# ---------------------------------------------------------------- turns on the network
def layers_of(site, zones_free):
    """The three obstacle layers of the spatial additions (original map); zones in zones_free (the chosen storage area, the near
    yard) do not count as "other occupancy"."""
    obs = TA.obstacles(site, zones_free[0])
    if len(zones_free) > 1:
        D, _ = SY.load(site)
        drop = [[tuple(q[:2]) for q in (D["zones"][z].get("boundary") or {}).get("outer") or []] for z in zones_free[1:]]
        obs["other"] = [(P, bb) for P, bb in obs["other"] if P not in drop]
    return obs


def road_polys(site):
    D, _ = SY.load(site)
    out = []
    for r in D["roads"].values():
        pts = [tuple(D["nodes"][r["fromNodeId"]]["position"][:2])] + [tuple(a[:2]) for a in r["geometry"].get("anchors", [])] + \
              [tuple(D["nodes"][r["toNodeId"]]["position"][:2])]
        w = float((r.get("widthM") or {}).get("value") or 0.0)
        if w > 0:
            out.append((pts, w))
    return out


def route_turns(D, net, p):
    """Turns with stop-and-steer on every loaded route (saddle row → cradle) of the derived graph:
    {(node, incoming road, outgoing road): dict(xy, hin, θ, number of routes, widths)}."""
    W = D["windport"]
    seen = {}
    for o in W["storage"]:
        for d in W["cradles"]:
            so, sd = net.stops[o], net.stops[d]
            runs, dl = WS.turn_delays(net, net.path(so["node"], sd["node"]), p["Lv"], p["v_loaded"], p)
            for i in range(1, len(runs)):
                if not dl[i]:
                    continue
                a, b = runs[i - 1][3], runs[i][2]
                n = net.arc[b][0]
                _, _, _, ra, fa = net.arc[a]
                _, _, _, rb, fb = net.arc[b]
                hin = net.road[ra]["h1"] if fa else net.road[ra]["h0"] + math.pi
                hout = net.road[rb]["h0"] if fb else net.road[rb]["h1"] + math.pi
                key = f"{n}|{ra}|{rb}"
                x = seen.setdefault(key, dict(node=n, xy=tuple(D["nodes"][n]["position"][:2]), hin=hin, th=wrap(hout - hin), routes=0,
                                              w_in=float(net.road[ra]["W"]), w_out=float(net.road[rb]["W"])))
                x["routes"] += 1
    return seen


def sector_bad(site_obs, x, L, B):
    """Criterion of the spatial additions: the sector centred on the junction hits buildings or water (sampling as in windport_turn_sweep)."""
    g = TA.GRIDS["turn"]
    h = TA.hits(TA.sweep_pts(x["xy"], x["hin"], x["th"], L, B, g), site_obs)
    return h["building"] + h["water"] > 0, h


def generic_s(L, B, v, tsw, w_in, w_out):
    """Generic formula: reverse about one pile length + crab sideways by the road-width difference (at least B) + two steering-mode switches."""
    return L / v + max(B, abs(w_out - w_in)) / v + 2 * tsw


def classify(res):
    fams = {k.split("|")[0] for k in res["fams"]}
    if res["base_block"] == 0:
        return "in place, feasible (road surface only)"
    if "R+" in fams:
        return "early re-orientation"
    if fams & {"R-", "C+", "C-"}:
        return "reversing or crab steering"
    return "no space (operator to confirm)"


def best_alt(res, vn, k, fams=None):
    """Shortest feasible alternative manoeuvre (family, record) over the families (only those in fams if given) at speed vn and
    end k of TSW: taken among those that do not hit other occupancy if there are any; None if none is feasible."""
    xs = [(f.split("|")[0], r) for f, r in res["fams"].items() if f.endswith(f"|{vn}|{k}") and r["ok_fine"] and (fams is None or f.split("|")[0] in fams)]
    xs = [x for x in xs if x[1]["clean"]] or xs
    return min(xs, key=lambda x: (x[1]["t"], x[0])) if xs else None
