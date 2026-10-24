"""The spatial additions, turning: swept-path check of turns on the digitized Okpo and Yantai geometry (reads only the two maps, writes
only text and data, draws no maps).

Okpo, Yantai × storage area (one-voyage area of the E4-E7 batches / relaxed SITES_MULTI) × cradle mode: on every loading route (saddle
row → cradle bay), each turn at which the occupancy model stops to steer (turn angle ≥ turn_deg) is checked for its swept path on the
map: the monopile turns about the junction from the incoming to the outgoing heading (the sector swept by a rectangle of length Lv and
width B; sample points every 2°, every 2 m along the length and at −B/2, 0, B/2 across; points within 8 m of the junction count as
inside the junction and are ignored), and a full circle (radius Lv/2).
Obstacles in three layers: buildings (facility polygons); water (dry docks, floating docks); other occupied areas (yards, assembly
yards, buffers, steel stockyards, offshore fabrication yards, gantry-crane spans; the storage area and quay working area of this site
excepted). Feasible = no swept sample point lies in a polygon of this layer or an earlier one. Output turn.csv (one row per turn node),
turn_routes.csv (one row per route), turn_extra.json (the turns "node|from|to" whose sector hits buildings or water: the simulation
--part turn adds the alternative-manoeuvre time only at these turns; recorded per turn, not per node).
Output results/windport_spatial_turn_<config hash>/: config.json, turn.csv, turn_routes.csv, turn_extra.json.
Run: python experiments/windport_turn_sweep.py
"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from windport import shipyard as SY                              # noqa: E402
from windport import sim as WS                                   # noqa: E402
from windport import sim4 as S4                                  # noqa: E402
import windport_runs as T                                        # noqa: E402

CODE = ["windport/sim.py", "windport/sim2.py", "windport/sim4.py", "windport/archetypes.py", "windport/shipyard.py", "occupancy/network.py",
        "occupancy/params.py", "experiments/windport_runs.py", "experiments/windport_turn_sweep.py"]
LAYERS = dict(building=None, water=("dry_dock", "floating_dock"),
              other=("yard", "assembly_yard", "buffer", "steel_stockyard", "offshore_fabrication_yard", "gantry_crane_span"))
GRIDS = dict(turn=dict(sites=["okpo", "yantai"], storage=["runs", "multi"], modes=T.MODES, step_deg=2.0, step_m=2.0, inner_m=8.0))


# ---------------------------------------------------------------- turning
def inside(pt, poly):
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def obstacles(site, storage_zone):
    """{layer: [(polygon, bbox)]}; uses the original map (classes not modified)."""
    D, _ = SY.load(site)
    out = {k: [] for k in LAYERS}
    for fid, f in sorted(D["facilities"].items()):
        poly = [tuple(q[:2]) for q in (f.get("boundary") or {}).get("outer") or []]
        if len(poly) >= 3:
            out["building"].append(poly)
    for zid, z in sorted(D["zones"].items()):
        ext = z.get("extensions") or {}
        cls = (ext.get(SY.SC) or {}).get("classId") or (ext.get(SY.RS) or {}).get("role")
        poly = [tuple(q[:2]) for q in (z.get("boundary") or {}).get("outer") or []]
        if len(poly) < 3 or zid == storage_zone:
            continue
        for k, cs in LAYERS.items():
            if cs and cls in cs:
                out[k].append(poly)
    bb = lambda P: (min(x for x, _ in P), min(y for _, y in P), max(x for x, _ in P), max(y for _, y in P))
    return {k: [(P, bb(P)) for P in v] for k, v in out.items()}


def hits(pts, obs):
    """Number of sample points inside the polygons of each layer."""
    out = {}
    for k, lst in obs.items():
        n = 0
        for x, y in pts:
            for P, (a, b, c, d) in lst:
                if a <= x <= c and b <= y <= d and inside((x, y), P):
                    n += 1
                    break
        out[k] = n
    return out


def sweep_pts(xy, hin, d, Lv, B, g):
    """Sample points swept by a rectangle centred at xy turning from heading hin through d (rad, signed); |s| < inner_m is skipped."""
    n = max(1, int(math.ceil(abs(math.degrees(d)) / g["step_deg"])))
    out = []
    ss = [s for s in [-Lv / 2 + g["step_m"] * k for k in range(int(Lv / g["step_m"]) + 1)] if abs(s) >= g["inner_m"]]
    for j in range(n + 1):
        f = hin + d * j / n
        c, s_ = math.cos(f), math.sin(f)
        for s in ss:
            for t in (-B / 2, 0.0, B / 2):
                out.append((xy[0] + s * c - t * s_, xy[1] + s * s_ + t * c))
    return out


def circle_pts(xy, R, g):
    out = []
    r = g["inner_m"]
    while r <= R + 1e-9:
        n = max(8, int(2 * math.pi * r / g["step_m"]))
        out += [(xy[0] + r * math.cos(2 * math.pi * k / n), xy[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
        r += g["step_m"]
    return out


def turn_cfg(site, storage, mode):
    c = T.cfg_of("e6", T.enc(dict(kind="map:" + site, scen="base", mode=mode, lift="cradle", rule="fcfs", L=12, K=1, S=T.NC[site], G=24)))
    if storage == "multi":
        c["geo"] = dict(c["geo"], storage="multi")
    return c


def turn():
    g = GRIDS["turn"]
    nodes, routes, extra = [], [], {}
    for site in g["sites"]:
        for st in g["storage"]:
            S = S4.SITES_MULTI[site] if st == "multi" else SY.SITES[site]
            obs = obstacles(site, S["storage_zone"])
            seen = {}
            for mode in g["modes"]:
                c = turn_cfg(site, st, mode)
                D, net, p, *_ = S4.setup4(c)
                W = D["windport"]
                for o in W["storage"]:
                    for d in W["cradles"]:
                        so, sd = net.stops[o], net.stops[d]
                        runs, dl = WS.turn_delays(net, net.path(so["node"], sd["node"]), p["Lv"], p["v_loaded"], p)
                        tn = []
                        for i in range(1, len(runs)):
                            if not dl[i]:
                                continue
                            a, b = runs[i - 1][3], runs[i][2]
                            n = net.arc[b][0]
                            _, _, _, ra, fa = net.arc[a]
                            _, _, _, rb, fb = net.arc[b]
                            hin = net.road[ra]["h1"] if fa else net.road[ra]["h0"] + math.pi
                            hout = net.road[rb]["h0"] if fb else net.road[rb]["h1"] + math.pi
                            dd = (hout - hin + math.pi) % (2 * math.pi) - math.pi
                            key = (n, round(hin, 4), round(dd, 4))
                            if key not in seen:
                                xy = D["nodes"][n]["position"][:2]
                                hs = hits(sweep_pts(xy, hin, dd, p["Lv"], p["B"], g), obs)
                                hc = hits(circle_pts(xy, p["Lv"] / 2, g), obs)
                                seen[key] = dict(site=site, storage=st, node=n, turn_deg=round(math.degrees(abs(dd)), 1),
                                                 sweep_building=hs["building"], sweep_water=hs["water"], sweep_other=hs["other"],
                                                 circle_building=hc["building"], circle_water=hc["water"], circle_other=hc["other"], routes=0,
                                                 moves="")
                            seen[key]["routes"] += 1
                            mv = sorted(set(filter(None, seen[key]["moves"].split(";"))) | {f"{n}|{ra}|{rb}"})
                            seen[key]["moves"] = ";".join(mv)
                            tn.append(key)
                        ok = lambda ks, lay: all(sum(seen[k][f"sweep_{x}"] for x in lay) == 0 for k in ks)
                        routes.append(dict(site=site, storage=st, mode=mode, row=o, cradle=d, turns=len(tn),
                                           ok_building=int(ok(tn, ["building"])), ok_water=int(ok(tn, ["building", "water"])),
                                           ok_other=int(ok(tn, ["building", "water", "other"]))))
            nodes += list(seen.values())
            # record per turn (node|from|to), not per node: the other direction at the same node is not added if it hits no obstacle
            bad = sorted({m for v in seen.values() if v["sweep_building"] + v["sweep_water"] > 0 for m in v["moves"].split(";")})
            extra[f"{site}|{st}"] = bad
    return nodes, routes, extra


def wcsv(path, rows):
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="spatial", part="turn", grid=GRIDS["turn"], base=WS.BASE, code=code, layers=LAYERS,
               code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest(), sites_multi=S4.SITES_MULTI,
               networks={s: SY.NETWORK[s] for s in ("okpo", "yantai")})
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_spatial_turn_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    nodes, routes, extra = turn()
    wcsv(out / "turn.csv", nodes)
    wcsv(out / "turn_routes.csv", routes)
    (out / "turn_extra.json").write_text(json.dumps(extra, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
