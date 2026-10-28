"""Near-yard buffer (single-voyage storage area of two-level storage: Okpo zone_trace_027, Yantai zone_trace_003): how many
monopiles fit, and whether the vehicle can get in and out. Reads only the Okpo and Yantai maps; outputs only counts, lengths,
durations and layout parameters without coordinates (no figures).

Grid: bounding box of the storage area extended by MARGIN m, RES m per cell. Obstacles = buildings + water (layers of
windport_turn_sweep) dilated by CLEAR_M (the 1 m clearance of the design analyses), minus road surface;
"other occupancy" (other yards, assembly areas, etc.) allows neither storing a pile nor crabbing across it.
  Storage slot: monopile footprint L_v × d_m (110 × 9.5 m) lies entirely inside the storage-area polygon, off road, obstacles
          and other occupancy; centreline distance of adjacent rows PITCH = d_m + w_e + c_lat = 15.36 m (as for the rebuilt
          side-by-side cradles); two piles end to end in one row leave δ = 5 m between them.
  Pure packing: greedy row-by-row placement in each candidate direction (each edge of the storage area and each frontage road;
          rows may be staggered); gives the upper bound that ignores access.
  Family A (rows parallel to the road, crab in and out): rows parallel to one straight frontage line (collinear adjoining
          frontage roads merged into one line). The loaded vehicle drives along the road to the slot position, crabs sideways
          into place and sets down; the empty vehicle crabs back onto the road. For pick-up the empty vehicle crabs in, lifts,
          crabs back loaded onto the road and drives off. The crab sweep [s ± L_v/2] × [road centreline, outer slot edge] must
          lie in storage area ∪ road, off obstacles and other occupancy; rows far from the road are filled first and rows near
          it emptied first (last in, first out), so the near rows swept are empty at that time. With parallel frontage lines on
          both sides the rows are split between the two sides (one dividing line). No turns inside the area, only two
          steering-mode switches (enter and leave crab mode). Slots of one column line up (same chainage along the road);
          adjacent columns leave δ end to end.
  Family B (perpendicular rows, end-on entry, for comparison): rows perpendicular to the frontage road; the loaded vehicle
          turns 90° in place about the pile centre on the road centreline onto the row axis, then drives straight in; every
          pile point swept by the turn and the straight drive must stay off obstacles, other occupancy and placed piles (two
          cases: only this slot in the area; all other slots occupied).
Duration: crab distance / speed (loaded v_l, empty v_e) + 2 steering-mode switches t_sw per crab leg (30 / 300 s, as in the
design analyses).
"""
import math
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import windport_turn_sweep as TA                                 # noqa: E402
from windport import shipyard as SY                              # noqa: E402

RES, MARGIN, CLEAR_M, VERGE_M = 0.5, 90.0, 1.0, 10.0
LV, DM, WE, CLAT, DELTA = 110.0, 9.5, 4.86, 1.0, 5.0
PITCH = DM + WE + CLAT                                            # 15.36 m
TSW = (30.0, 300.0)


def zone_of(site):
    return SY.SITES[site]["storage_zone"]


def poly_of(D, zid):
    return [tuple(q[:2]) for q in (D["zones"][zid].get("boundary") or {}).get("outer") or []]


def road_pts(D, r):
    return [tuple(D["nodes"][r["fromNodeId"]]["position"][:2])] + [tuple(a[:2]) for a in r["geometry"].get("anchors", [])] + \
           [tuple(D["nodes"][r["toNodeId"]]["position"][:2])]


class World:
    """Grid around the storage area: inzone, road, block (dilated obstacles minus road), other (other occupancy minus road)."""

    def __init__(self, site, zid=None):
        D, _ = SY.load(site)
        self.D, self.site, self.zid = D, site, zid or zone_of(site)
        P = poly_of(D, self.zid)
        self.P = P
        xs, ys = [x for x, _ in P], [y for _, y in P]
        self.x0, self.y0 = min(xs) - MARGIN, min(ys) - MARGIN
        self.nx = int(math.ceil((max(xs) - min(xs) + 2 * MARGIN) / RES))
        self.ny = int(math.ceil((max(ys) - min(ys) + 2 * MARGIN) / RES))
        X, Y = np.meshgrid(self.x0 + (np.arange(self.nx) + 0.5) * RES, self.y0 + (np.arange(self.ny) + 0.5) * RES, indexing="ij")
        pts = np.stack([X.ravel(), Y.ravel()], 1)
        inside = lambda poly: MPath(poly).contains_points(pts).reshape(self.nx, self.ny)
        self.inzone = inside(P)
        obs = TA.obstacles(site, self.zid)
        lay = {}
        for k, lst in obs.items():
            m = np.zeros((self.nx, self.ny), bool)
            for poly, (a, b, c, d) in lst:
                if c < self.x0 or a > self.x0 + self.nx * RES or d < self.y0 or b > self.y0 + self.ny * RES:
                    continue
                m |= inside(poly)
            lay[k] = m
        road = np.zeros((self.nx, self.ny), bool)
        self.roads = {}
        for rid, r in D["roads"].items():
            w = float((r.get("widthM") or {}).get("value") or 0.0)
            ps = road_pts(D, r)
            self.roads[rid] = (ps, w)
            if w <= 0:
                continue
            for (ax, ay), (bx, by) in zip(ps, ps[1:]):
                dx, dy = bx - ax, by - ay
                L2 = dx * dx + dy * dy
                t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1) if L2 > 0 else 0.0
                road |= (X - ax - t * dx) ** 2 + (Y - ay - t * dy) ** 2 <= (w / 2) ** 2
        self.road = road
        r = int(math.ceil(CLEAR_M / RES))
        self.block = dilate(lay["building"] | lay["water"], r) & ~road
        self.other = lay["other"] & ~road
        self.free_store = self.inzone & ~road & ~self.block & ~self.other     # a pile may be stored here
        # crabbing allowed over: storage area, road, and the verge within VERGE_M outside the storage-area boundary (undigitised
        # ground between frontage road and boundary; neither obstacle nor other occupancy)
        verge = ndimage.binary_dilation(self.inzone, structure=disk(int(math.ceil(VERGE_M / RES))))
        self.free_crab = (self.inzone | road | verge) & ~self.block & ~self.other
        self.free_turn = ~self.block                                          # turning: obstacles only (other occupancy apart)
        self.area_m2 = float(0.5 * abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(P, P[1:] + P[:1]))))

    def look(self, wx, wy, mask, outside=False):
        i = np.floor((wx - self.x0) / RES).astype(int)
        j = np.floor((wy - self.y0) / RES).astype(int)
        ok = (i >= 0) & (i < self.nx) & (j >= 0) & (j < self.ny)
        out = np.full(wx.shape, outside)
        out[ok] = mask[i[ok], j[ok]]
        return out


def disk(r):
    i = np.arange(-r, r + 1)
    return i[:, None] ** 2 + i[None, :] ** 2 <= r * r


def dilate(m, r):
    return ndimage.binary_dilation(m, structure=disk(r))


# ---------------------------------------------------------------- straight lines merged from frontage roads
def frontage_lines(W):
    """[(line, dict(roads, O, d, n, s_lo, s_hi, w))]: frontage roads of the storage area merged into straight lines by
    collinearity (heading difference < 2°, lateral offset < 2 m); n points towards the storage area, s_lo..s_hi is the union
    of the road projections on d (longest connected run)."""
    fr = [f["roadId"] for f in (W.D["zones"][W.zid].get("extensions") or {}).get(SY.RS, {}).get("frontage") or [] if f["roadId"] in W.D["roads"]]
    cx = sum(x for x, _ in W.P) / len(W.P)
    cy = sum(y for _, y in W.P) / len(W.P)
    segs = []
    for rid in fr:
        ps, w = W.roads[rid]
        a, b = ps[0], ps[-1]
        h = math.atan2(b[1] - a[1], b[0] - a[0]) % math.pi
        segs.append((rid, a, b, h, w))
    groups = []
    for s in segs:
        for g in groups:
            r0 = g[0]
            dh = abs((s[3] - r0[3] + math.pi / 2) % math.pi - math.pi / 2)
            d = (math.cos(r0[3]), math.sin(r0[3]))
            off = abs(-(s[1][0] - r0[1][0]) * d[1] + (s[1][1] - r0[1][1]) * d[0])
            if dh < math.radians(2.0) and off < 2.0:
                g.append(s)
                break
        else:
            groups.append([s])
    out = []
    for g in groups:
        h = g[0][3]
        d = (math.cos(h), math.sin(h))
        O = g[0][1]
        n = (-d[1], d[0])
        if (cx - O[0]) * n[0] + (cy - O[1]) * n[1] < 0:
            n = (-n[0], -n[1])
        iv = sorted(tuple(sorted(((p[0] - O[0]) * d[0] + (p[1] - O[1]) * d[1]) for p in (s[1], s[2]))) for s in g)
        runs = []
        for a, b in iv:
            if runs and a <= runs[-1][1] + 1.0:
                runs[-1][1] = max(runs[-1][1], b)
            else:
                runs.append([a, b])
        lo, hi = max(runs, key=lambda x: x[1] - x[0])
        out.append(dict(roads=[s[0] for s in g], O=O, d=d, n=n, s_lo=lo, s_hi=hi, w=min(s[4] for s in g), h=h))
    return out


# ---------------------------------------------------------------- sampling in a directional frame
class Frame:
    """Directional frame: world point = O + u·d + v·n; u ∈ [u0, u1], v ∈ [v0, v1], RES per cell; masks are resampled into the
    frame, with integral images."""

    def __init__(self, W, O, d, n, u0, u1, v0, v1):
        self.O, self.d, self.n = O, d, n
        self.u = u0 + (np.arange(int(math.ceil((u1 - u0) / RES))) + 0.5) * RES
        self.v = v0 + (np.arange(int(math.ceil((v1 - v0) / RES))) + 0.5) * RES
        U, V = np.meshgrid(self.u, self.v, indexing="ij")
        wx, wy = O[0] + U * d[0] + V * n[0], O[1] + U * d[1] + V * n[1]
        self.m = {k: W.look(wx, wy, getattr(W, k)) for k in ("free_store", "free_crab", "inzone", "road")}
        self.I = {k: integral(v) for k, v in self.m.items()}

    def idx(self, u, v):
        return int(round((u - self.u[0]) / RES)), int(round((v - self.v[0]) / RES))

    def full(self, key, ua, ub, va, vb):
        """Whether all cells in [ua, ub] × [va, vb] are key (False if outside the frame)."""
        i0, j0 = int(math.floor((ua - self.u[0]) / RES + 0.5)), int(math.floor((va - self.v[0]) / RES + 0.5))
        i1, j1 = int(math.ceil((ub - self.u[0]) / RES - 0.5)), int(math.ceil((vb - self.v[0]) / RES - 0.5))
        i0, j0 = max(i0, 0), max(j0, 0)
        if i1 >= len(self.u) or j1 >= len(self.v) or i0 > i1 or j0 > j1:
            return False
        S = self.I[key]
        tot = S[i1 + 1, j1 + 1] - S[i0, j1 + 1] - S[i1 + 1, j0] + S[i0, j0]
        return int(tot) == (i1 - i0 + 1) * (j1 - j0 + 1)


def integral(m):
    S = np.zeros((m.shape[0] + 1, m.shape[1] + 1), np.int64)
    S[1:, 1:] = np.cumsum(np.cumsum(m.astype(np.int64), 0), 1)
    return S


def frame_around(W, O, d, n):
    """Frame on (d, n) covering the storage area's bounding region (extended by margins)."""
    cs = [((x - O[0]) * d[0] + (y - O[1]) * d[1], (x - O[0]) * n[0] + (y - O[1]) * n[1]) for x, y in W.P]
    u0, u1 = min(c[0] for c in cs) - 60.0, max(c[0] for c in cs) + 60.0
    v0, v1 = min(min(c[1] for c in cs), 0.0) - 20.0, max(c[1] for c in cs) + 20.0
    return Frame(W, O, d, n, u0, u1, v0, v1)


# ---------------------------------------------------------------- pure packing (access ignored)
def pack_greedy(F):
    """Rows parallel to d: each row (every PITCH in v) is filled greedily along u; the v start is scanned.
    Returns (piles, rows, v start)."""
    best = (0, 0, None)
    vs = F.v
    for v0 in np.arange(vs[0] + DM / 2, vs[0] + DM / 2 + PITCH, RES):
        tot, rows = 0, 0
        v = v0
        while v + DM / 2 <= vs[-1]:
            k, u = 0, F.u[0] + LV / 2
            while u + LV / 2 <= F.u[-1]:
                if F.full("free_store", u - LV / 2, u + LV / 2, v - DM / 2, v + DM / 2):
                    k += 1
                    u += LV + DELTA
                else:
                    u += RES
            tot += k
            rows += int(k > 0)
            v += PITCH
        if tot > best[0]:
            best = (tot, rows, round(float(v0), 2))
    return best


def pure_packing(W):
    """Maximum number of slots in each candidate direction (each storage-area edge, each frontage road)."""
    hs = set()
    for (x1, y1), (x2, y2) in zip(W.P, W.P[1:] + W.P[:1]):
        if math.dist((x1, y1), (x2, y2)) > 1.0:
            hs.add(round(math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180, 1))
    for ln in frontage_lines(W):
        hs.add(round(math.degrees(ln["h"]) % 180, 1))
    out = []
    for hd in sorted(hs):
        h = math.radians(hd)
        d, n = (math.cos(h), math.sin(h)), (-math.sin(h), math.cos(h))
        F = frame_around(W, W.P[0], d, n)
        k, rows, _ = pack_greedy(F)
        out.append(dict(heading_deg=hd, slots=k, rows=rows))
    return out


# ---------------------------------------------------------------- family A: rows parallel to the road, crab in and out
def family_a(W, ln, opp=None):
    """Rows parallel to frontage line ln (optionally with a parallel line opp on the opposite side): scan (column start u0,
    first-row offset v0) and keep the layout with the most slots reachable by crabbing. Returns dict(slots, rows, cols,
    crab distance per slot, ...)."""
    F = frame_around(W, ln["O"], ln["d"], ln["n"])
    vB = None
    if opp is not None:
        vB = (opp["O"][0] - ln["O"][0]) * ln["n"][0] + (opp["O"][1] - ln["O"][1]) * ln["n"][1]
    s_lo, s_hi = ln["s_lo"], ln["s_hi"]
    if opp is not None:                                          # pile must fit on both roads: intersect the ranges
        oa = [(p - 0) for p in (opp["s_lo"], opp["s_hi"])]
        off = (opp["O"][0] - ln["O"][0]) * ln["d"][0] + (opp["O"][1] - ln["O"][1]) * ln["d"][1]
        b_lo, b_hi = sorted(off + x * (1 if (opp["d"][0] * ln["d"][0] + opp["d"][1] * ln["d"][1]) > 0 else -1) for x in oa)
    best = None
    v_first = ln["w"] / 2 + DM / 2
    for v0 in np.arange(v_first, v_first + PITCH, RES):
        rows_v = []
        v = v0
        while v + DM / 2 <= F.v[-1] and (vB is None or v + DM / 2 <= vB - opp["w"] / 2):
            rows_v.append(float(v))
            v += PITCH
        if not rows_v:
            continue
        for u0 in np.arange(s_lo + LV / 2, s_lo + LV / 2 + LV + DELTA, 1.0):
            cols = []
            u = u0
            while u + LV / 2 <= s_hi + 1e-9:
                cols.append(float(u))
                u += LV + DELTA
            if not cols:
                continue
            tot, plan = 0, []
            for u in cols:
                store = [F.full("free_store", u - LV / 2, u + LV / 2, v - DM / 2, v + DM / 2) for v in rows_v]
                fromA = [store[k] and F.full("free_crab", u - LV / 2, u + LV / 2, -DM / 2, rows_v[k] + DM / 2) for k in range(len(rows_v))]
                fromB = [False] * len(rows_v)
                if vB is not None and b_lo - 1e-9 <= u - LV / 2 and u + LV / 2 <= b_hi + 1e-9:
                    fromB = [store[k] and F.full("free_crab", u - LV / 2, u + LV / 2, rows_v[k] - DM / 2, vB + DM / 2) for k in range(len(rows_v))]
                cr = lambda m: sum(rows_v[k] for k in range(m) if fromA[k]) + sum(vB - rows_v[k] for k in range(m, len(rows_v)) if fromB[k])
                bestc = max(((sum(fromA[:m]) + sum(fromB[m:]), -cr(m), m) for m in range(len(rows_v) + 1)))
                m = bestc[2]
                tot += bestc[0]
                for k, v in enumerate(rows_v):
                    side = "A" if k < m else "B"
                    ok = fromA[k] if side == "A" else fromB[k]
                    if ok:
                        plan.append(dict(u=round(u, 2), row=k, side=side, crab_m=round(v if side == "A" else vB - v, 2)))
            if best is None or tot > best["slots"] or (tot == best["slots"] and sum(p["crab_m"] for p in plan) < best["crab_sum"]):
                best = dict(slots=tot, rows=len({p["row"] for p in plan}), cols=len({p["u"] for p in plan}), v0=round(float(v0), 2), u0=round(float(u0), 2),
                            plan=plan, crab_sum=sum(p["crab_m"] for p in plan), vB=None if vB is None else round(vB, 2))
    return best


def family_a_best(W):
    """Best family-A layouts over all frontage lines (single-sided, and both sides of paired parallel lines)."""
    lns = frontage_lines(W)
    res = []
    for i, ln in enumerate(lns):
        r = family_a(W, ln)
        if r:
            res.append(dict(r, line=i, roads="+".join(ln["roads"]), opp=None, w=ln["w"], len_m=round(ln["s_hi"] - ln["s_lo"], 1)))
        for j, op in enumerate(lns):
            dh = abs((op["h"] - ln["h"] + math.pi / 2) % math.pi - math.pi / 2)
            side = (op["O"][0] - ln["O"][0]) * ln["n"][0] + (op["O"][1] - ln["O"][1]) * ln["n"][1]
            if j != i and dh < math.radians(2.0) and side > 2 * LV / 10:
                r2 = family_a(W, ln, op)
                if r2:
                    res.append(dict(r2, line=i, roads="+".join(ln["roads"]), opp="+".join(op["roads"]), w=ln["w"], len_m=round(ln["s_hi"] - ln["s_lo"], 1)))
    return lns, res


# ---------------------------------------------------------- family B: perpendicular rows, 90° turn in place, then end-on entry
def body_pts(ds=1.0, nt=5):
    s = np.arange(-LV / 2, LV / 2 + 1e-9, ds)
    t = np.linspace(-DM / 2, DM / 2, nt)
    S, T_ = np.meshgrid(s, t, indexing="ij")
    return S.ravel(), T_.ravel()


def family_b(W, ln, step_deg=1.0):
    """Rows perpendicular to frontage line ln (axis along n): slot centre (u, v_c), v_c = road edge + δ + L_v/2; one slot every
    PITCH along u. Each slot: turn 90° in place at (u, 0) on the road centreline (either turning direction that is feasible),
    then drive straight along n into place. Returns dict(slots, reachable with only this slot in the area, reachable with all
    other slots occupied)."""
    d, n = ln["d"], ln["n"]
    O = ln["O"]
    F = frame_around(W, O, (n[0], n[1]), (-d[0], -d[1]))           # frame: u' along n (row axis), v' along −d
    vc = ln["w"] / 2 + DELTA + LV / 2
    cands = []
    for u in np.arange(ln["s_lo"] + DM / 2, ln["s_hi"] - DM / 2 + 1e-9, RES):
        if F.full("free_store", vc - LV / 2, vc + LV / 2, -u - DM / 2, -u + DM / 2):
            cands.append(float(u))
    slots = []
    for u in cands:                                              # greedy: one every PITCH
        if not slots or u >= slots[-1] + PITCH - 1e-9:
            slots.append(u)
    bs, bt = body_pts()
    world = lambda c, h: (c[0] + bs * math.cos(h) - bt * math.sin(h), c[1] + bs * math.sin(h) + bt * math.cos(h))
    hr = math.atan2(d[1], d[0])
    hn = math.atan2(n[1], n[0])
    foot = {}
    for u in slots:
        cxy = (O[0] + u * d[0] + vc * n[0], O[1] + u * d[1] + vc * n[1])
        foot[u] = world(cxy, hn)
    res = []
    for u in slots:
        X = (O[0] + u * d[0], O[1] + u * d[1])
        ok_alone = ok_full = False
        for sgn in (1, -1):
            a = (hn - hr) % (2 * math.pi)
            a = a if sgn == 1 else a - 2 * math.pi
            if abs(a) > math.pi + 1e-9:
                a = a - math.copysign(math.pi, a)                 # pile is end-symmetric: a or a − π both align with n
            px, py = [], []
            nstep = max(1, int(math.ceil(abs(math.degrees(a)) / step_deg)))
            for k in range(nstep + 1):
                x, y = world(X, hr + a * k / nstep)
                px.append(x)
                py.append(y)
            for k in range(0, int(vc) + 1, 2):
                x, y = world((X[0] + k * n[0], X[1] + k * n[1]), hn)
                px.append(x)
                py.append(y)
            px, py = np.concatenate(px), np.concatenate(py)
            clear = not W.look(px, py, W.block).any() and not W.look(px, py, W.other).any()
            if not clear:
                continue
            ok_alone = True
            others = [foot[q] for q in slots if q != u]
            hit = False
            for fx, fy in others:
                poly = MPath(hull(fx, fy))
                if poly.contains_points(np.stack([px, py], 1)).any():
                    hit = True
                    break
            ok_full = ok_full or not hit
        res.append(dict(u=round(u, 2), alone=int(ok_alone), full=int(ok_full)))
    return dict(slots=len(slots), alone=sum(r["alone"] for r in res), full=sum(r["full"] for r in res), per=res)


def hull(xs, ys):
    """Four corners of a monopile footprint (oriented rectangle around the sample points, from their extreme points)."""
    P = np.stack([xs, ys], 1)
    c = P.mean(0)
    d = P[np.argmax(((P - c) ** 2).sum(1))] - c
    d = d / np.linalg.norm(d)
    nrm = np.array([-d[1], d[0]])
    a, b = (P - c) @ d, (P - c) @ nrm
    return [tuple(c + x * d + y * nrm) for x, y in ((a.min(), b.min()), (a.max(), b.min()), (a.max(), b.max()), (a.min(), b.max()))]


def family_a_pick(res):
    """Among the family-A candidates, the one with the most slots and the shortest total crab distance."""
    return max(res, key=lambda r: (r["slots"], -r["crab_sum"])) if res else None


def road_s(W, roads, X):
    """Projection of point X on the nearest of roads (straight roads): (road, chainage from start, lateral distance)."""
    best = None
    for rid in roads:
        ps, _ = W.roads[rid]
        a, b = ps[0], ps[-1]
        L = math.dist(a, b)
        t = ((X[0] - a[0]) * (b[0] - a[0]) + (X[1] - a[1]) * (b[1] - a[1])) / L
        tc = min(max(t, 5.0), L - 5.0)
        e = math.dist(X, (a[0] + (b[0] - a[0]) * tc / L, a[1] + (b[1] - a[1]) * tc / L))
        if best is None or e < best[2]:
            best = (rid, round(tc, 3), round(e, 3))
    return best


def zone_columns(W, best, lns):
    """Family-A layout -> columns: dict(zone, road, s, side, slots, crab_max_m, crabs); column centre on that side's road
    centreline."""
    ln = lns[best["line"]]
    opp = next((x for x in lns if "+".join(x["roads"]) == best["opp"]), None) if best["opp"] else None
    cols = {}
    for p in best["plan"]:
        cols.setdefault((p["u"], p["side"]), []).append(p["crab_m"])
    out = []
    for (u, side), crabs in sorted(cols.items()):
        v = 0.0 if side == "A" else best["vB"]
        X = (ln["O"][0] + u * ln["d"][0] + v * ln["n"][0], ln["O"][1] + u * ln["d"][1] + v * ln["n"][1])
        rid, s, e = road_s(W, (ln if side == "A" else opp)["roads"], X)
        assert e < 1.0, (W.zid, u, side, e)
        out.append(dict(zone=W.zid, road=rid, s=s, side=side, slots=len(crabs), crab_max_m=max(crabs), crabs=sorted(crabs)))
    return out


def make_plan(site, extra_zones=()):
    """Near-yard slot layout: the single-voyage storage area (best family-A layout), optionally plus some yard zones (extra_zones,
    same method). Returns dict(columns, zones, slots, order); order = column index of each successive pick-up by the load-out
    tasks (last in, first out within a column, round robin across columns, as in windport.sim.setup)."""
    cols, zones = [], []
    for zid in (zone_of(site),) + tuple(extra_zones):
        W = World(site, zid)
        lns, res = family_a_best(W)
        best = family_a_pick(res)
        cs = zone_columns(W, best, lns) if best and best["slots"] else []
        cols += cs
        zones.append(dict(zone=zid, area_m2=round(W.area_m2), slots=sum(c["slots"] for c in cs), rows=best and best["rows"], line=best and best["roads"],
                          opp=best and best["opp"], road_w=best and best["w"], line_len_m=best and best["len_m"], pure=max(x["slots"] for x in pure_packing(W))))
    left = [c["slots"] for c in cols]
    order = []
    while any(left):
        for k in range(len(cols)):
            if left[k]:
                order.append(k)
                left[k] -= 1
    return dict(site=site, columns=cols, zones=zones, slots=sum(c["slots"] for c in cols), order=order)


def crab_extra(plan, v_l, v_e, tsw):
    """Extra duration (s) of one pick-up (empty crab in, loaded crab out) or one set-down (loaded crab in, empty crab out),
    for the farthest slot: one loaded leg, one empty leg, 2 mode switches each."""
    m = max(c["crab_max_m"] for c in plan["columns"])
    return m / v_l + m / v_e + 4 * tsw
