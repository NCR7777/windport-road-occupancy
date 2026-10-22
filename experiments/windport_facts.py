"""Facts confirmed from the code (reads the model only, no simulation; outputs text and numbers, no maps).

1. Turns: on the three layouts (base geometry, 6 cradle positions) and the maps derived from Okpo and Yantai, the turns passed by
   each loaded trip (each saddle row → each cradle position) and each empty leg (leaving the quay, returning to the saddle rows):
   number and angle of turns ≥ turn_deg (60°), the steering stop δ at each (windport.sim.turn_delays, loaded 2.5 and 1 km/h),
   whether the turn is a junction resource, and the other arms of the junction that are swept; the largest bend inside a road
   polyline (not timed by the model, listed separately).
2. Vehicle set: the model treats a vehicle set as one vehicle (empty plat_len × plat_w, loaded vehicle-plus-load length Lv, load
   width B); axle lines implied by the module sizes in the parameter registry; t_e and K† on the cut for empty length 30 / 60 m
   (windport.sim.w1_port, A1 base and long single lane, pull-in cradles, S = 1).
3. Width: resource capacity = road width + c_lat; a loaded vehicle occupies min(C, D + c_lat), an empty one min(C, w_e + c_lat), a
   loaded vehicle holds a junction exclusively (occupancy.network.Net.demand); whether vehicles can pass on the apron, a single
   lane and a two-lane road, the geometric basis of Q_h = 0, the single-lane width threshold D + w_e + c_lat, and the diameters of
   the E7 levels.
Output results/windport_extra_facts_<config hash>/: config.json (SHA-256 of inputs and code), facts.json, facts.md.
Run: .venv/Scripts/python.exe experiments/windport_facts.py
"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from occupancy import params as PP                               # noqa: E402
from windport import shipyard as SY                              # noqa: E402
from windport import sim as S                                    # noqa: E402
from windport import sim2 as S2                                  # noqa: E402
import windport_runs as T                                        # noqa: E402

KMH = 1 / 3.6
CODE = ["windport/sim.py", "windport/sim2.py", "windport/bound.py", "windport/archetypes.py", "windport/shipyard.py", "occupancy/network.py",
        "occupancy/params.py", "experiments/windport_runs.py", "experiments/windport_facts.py"]
INPUTS = ["data/register/parameters.csv"]
SITES = [("A1", None), ("A2", None), ("A3", None), ("map", "okpo"), ("map", "yantai")]


def geo_of(kind, site, mode):
    if kind == "map":
        return dict(kind="map", site=site, cradle_mode=mode, n_cradles=T.NC[site])
    return dict(kind=kind, n_cradles=6, cradle_mode=mode)


def bends(D, rid):
    """Largest bend angle (degrees) inside a road polyline (at its anchors); the model counts turns only between roads. None for
    the derived graphs of the shipyards, which hold no geometry (results/runs/facts holds the values computed on the maps)."""
    r = D["roads"][rid]
    if "geometry" not in r:
        return None
    pts = [D["nodes"][r["fromNodeId"]]["position"][:2]] + [a[:2] for a in r["geometry"].get("anchors") or []] + \
          [D["nodes"][r["toNodeId"]]["position"][:2]]
    out = 0.0
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        h1, h2 = math.atan2(b[1] - a[1], b[0] - a[0]), math.atan2(c[1] - b[1], c[0] - b[0])
        d = abs((h2 - h1 + math.pi) % (2 * math.pi) - math.pi)
        out = max(out, math.degrees(d))
    return out


def turns(net, D, p, src, dst, loaded, cap, size):
    """Turns of one trip: [(node, degrees, junction resource?, other arms swept, δ_2.5, δ_1.0)], plus the number of all turns, the
    route length and the largest in-road bend."""
    arcs = net.path(src, dst)
    runs, _ = S.turn_delays(net, arcs, p["Lv"], p["v_loaded"], p)
    out, n_all = [], 0
    for i in range(1, len(runs)):
        ang = math.degrees(net.turn(runs[i - 1][3], runs[i][2]))
        if ang < 1e-6:
            continue
        n_all += 1
        if ang < p["turn_deg"]:
            continue
        node = net.arc[runs[i][2]][0]
        jr = node in net.node_res
        arms = sorted(q for q in net.incident[node] if q not in (runs[i - 1][0], runs[i][0])) if jr else []
        d = [p["sweep_steer_s"] + math.radians(ang) * p["Lv"] / 2 / (v * KMH) for v in (2.5, 1.0)]
        hold = [(size[node] + p["Lv"] + p["long_clear"]) / (v * KMH) + dd for v, dd in zip((2.5, 1.0), d)] if jr else None
        out.append(dict(node=node, deg=round(ang, 1), junction=jr, swept_arms=arms if loaded else [], delta_s=[round(x, 1) for x in d],
                        junction_hold_s=None if hold is None else [round(x, 1) for x in hold],
                        empty_sweep_s=p["turn_sweep_s"] if (not loaded and jr) else None))
    length = sum(net.arc[a][2] for a in arcs)
    roads = sorted({net.arc[a][3] for a in arcs})
    bs = [bends(D, r) for r in roads if r in D["roads"]]
    return out, n_all, length, None if None in bs else max(bs, default=0.0)


def route_facts(kind, site, mode):
    geo = geo_of(kind, site, mode)
    p = S.params(dict(horizon_h=1))
    D, net = S2.get_net(geo, p)
    cap, size = net.capacities(p)
    W = D["windport"]
    gate, yard = S2.idle_nodes(D)
    rows = [net.stops[o]["node"] for o in W["storage"]]
    quay = [net.stops[d]["node"] for d in W["cradles"]]
    out = dict(kind=kind, site=site, mode=mode, gate=gate, idle=yard, loaded=[], empty=[])
    seen = {}
    for o in rows:
        for q in quay:
            t, n_all, length, bend = turns(net, D, p, o, q, True, cap, size)
            sig = json.dumps(t, sort_keys=True)
            seen.setdefault(sig, dict(turns=t, n_turns_any=n_all, n_routes=0, len_m=[], max_bend_in_road_deg=0.0))
            seen[sig]["n_routes"] += 1
            seen[sig]["len_m"].append(round(length, 1))
            seen[sig]["max_bend_in_road_deg"] = None if bend is None else round(max(seen[sig]["max_bend_in_road_deg"], bend), 1)
    for v in seen.values():
        v["len_m"] = [min(v["len_m"]), max(v["len_m"])]
        out["loaded"].append(v)
    legs = [(q, yard) for q in quay] + [(yard, o) for o in rows]
    seen = {}
    for a, b in legs:
        if a == b:
            continue
        t, n_all, length, bend = turns(net, D, p, a, b, False, cap, size)
        key = json.dumps([[x["node"], x["deg"], x["junction"]] for x in t])
        seen.setdefault(key, dict(turns=t, n_legs=0, len_m=[], max_bend_in_road_deg=0.0))
        seen[key]["n_legs"] += 1
        seen[key]["len_m"].append(round(length, 1))
        seen[key]["max_bend_in_road_deg"] = None if bend is None else round(max(seen[key]["max_bend_in_road_deg"], bend), 1)
    for v in seen.values():
        v["len_m"] = [min(v["len_m"]), max(v["len_m"])]
        out["empty"].append(v)
    return out


def te_facts():
    """Empty length 30 / 60 m: t_e, t_ℓ, c and K† on the cut for A1 base and long single lane, pull-in cradles, S = 1, K = 2, L = 12 h,
    G = 24 h."""
    out = []
    for sc in ("base", "lane"):
        for pl in (30.0, 60.0):
            c = T.cfg_of("e4", T.enc(dict(kind="A1", scen=sc, mode="pull_in", lift="cradle", rule="fcfs", L=12, K=2, S=1, G=24)))
            c["p"] = dict(c["p"], plat_len=pl)
            D, net, p, *_ = S2.setup2(c)
            P, t = S.w1_port(c, D, net, p)
            out.append(dict(scen=sc, plat_len=pl, cut="|".join(map(str, t["res"])), tl=round(t["tl"], 1), te=round(t["te"], 1),
                            te_occ=round(t["te_occ"], 1), c=round(P.c, 1), k_dagger=round(P.c / (t["tl"] + t["te"]), 4)))
    for a, b in zip(out[::2], out[1::2]):
        b["te_rel"] = round(b["te"] / a["te"] - 1, 4) if a["te"] else None
        b["k_dagger_rel"] = round(b["k_dagger"] / a["k_dagger"] - 1, 4)
    return out


def width_facts():
    p = dict(PP.DEFAULTS, **S.BASE)
    c, B, we = p["lat_clear"], p["B"], p["plat_w"]
    out = dict(lat_clear=c, B=B, w_e=we, roads={})
    for name, w in (("apron 12 m", 12.0), ("single lane 10 m", 10.0), ("single lane 12 m (E7)", 12.0), ("double lane 20 m", 20.0)):
        C = w + c
        dl, de = min(C, B + c), min(C, we + c)
        out["roads"][name] = dict(capacity=C, loaded=dl, empty=de, loaded_empty_pass=dl + de <= C + 1e-9, two_loaded_pass=2 * dl <= C + 1e-9,
                                  two_empty_pass=2 * de <= C + 1e-9)
    out["threshold_loaded_empty_m"] = B + we + c          # w ≥ D + w_e + c_lat: an empty vehicle can pass a loaded one
    out["threshold_two_loaded_m"] = 2 * B + c             # w ≥ 2D + c_lat: two loaded vehicles can pass
    out["e7"] = [dict(lev=k, Lv=v["Lv"], D=v["B"], fits_10m=v["B"] <= 10.0, fits_12m=v["B"] <= 12.0,
                      loaded_empty_threshold=v["B"] + we + c, two_loaded_threshold=2 * v["B"] + c) for k, v in T.E7LEV.items()]
    out["diameters_registry"] = dict(note="Parameter registry: Moray West 10 m; Inch Cape 11.5 m, Hornsea 3 11 m (Table B.1)")
    return out


def set_facts():
    p = dict(PP.DEFAULTS, **S.BASE)
    lines_per_file = math.floor(p["plat_len"] / 1.4)
    files = round(p["plat_w"] / 2.43)
    return dict(model="one vehicle set = one vehicle (loaded vehicle-plus-load length Lv, load width B; empty plat_len × plat_w)", Lv=p["Lv"], B=p["B"], plat_len=p["plat_len"],
                plat_w=p["plat_w"], files=files, axle_lines_per_file=lines_per_file, axle_lines_in_footprint=files * lines_per_file,
                axle_lines_needed_1500t=math.ceil(1500 / 18.75), note="1,500 t / 18.75 t = 80 axle lines; a 30 m × 4.86 m platform has about 2 × 21 = 42 axle lines")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    cfg = dict(task="extra", part="facts", sites=SITES, modes=T.MODES, base=S.BASE, code=code,
               inputs={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in INPUTS},
               networks={s: SY.NETWORK[s] for s in ("okpo", "yantai")})
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_extra_facts_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    res = dict(routes=[route_facts(k, s, m) for k, s in SITES for m in T.MODES], te=te_facts(), width=width_facts(), set=set_facts())
    (out / "facts.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    md = ["# Code facts (script-generated)", "", "## Turns (loaded trips grouped by turn pattern; δ at 2.5 / 1 km/h)", ""]
    md.append("| Layout / shipyard | Cradle | Leg | Routes | Length (m) | All turns | Turns ≥ 60° (node: degrees, δ s, junction?, swept arms) | Max in-road bend |")
    md.append("|---|---|---|---|---|---|---|---|")
    for r in res["routes"]:
        name = r["site"] or r["kind"]
        for leg in ("loaded", "empty"):
            for g in r[leg]:
                if leg == "loaded":
                    tt = "; ".join(f"{x['node']}: {x['deg']}°, δ {x['delta_s'][0]}/{x['delta_s'][1]}, {'junction' if x['junction'] else 'not a junction'}"
                                  + (f", sweeps {len(x['swept_arms'])} arms" if x["swept_arms"] else "") for x in g["turns"]) or "none"
                else:                                    # empty vehicles do not stop: turn_sweep_s added at junction resources
                    tt = "; ".join(f"{x['node']}: {x['deg']}°, " + (f"junction +{x['empty_sweep_s']:.0f} s" if x["junction"] else "not a junction, not timed")
                                  for x in g["turns"]) or "none"
                md.append(f"| {name} | {r['mode']} | {'loaded' if leg == 'loaded' else 'empty'} | {g.get('n_routes', g.get('n_legs'))} | "
                          f"{g['len_m'][0]}–{g['len_m'][1]} | {g.get('n_turns_any', '')} | {tt} | {g['max_bend_in_road_deg']}° |")
    md += ["", "## Empty vehicle length 30 / 60 m (A1, pull-in cradles, S = 1)", "", "| Scenario | Empty length | Cut | t_ℓ (s) | t_e (s) | c (s) | K† | t_e change | K† change |",
           "|---|---|---|---|---|---|---|---|---|"]
    for x in res["te"]:
        md.append(f"| {x['scen']} | {x['plat_len']} | {x['cut']} | {x['tl']} | {x['te']} | {x['c']} | {x['k_dagger']} | {x.get('te_rel', '')} | "
                  f"{x.get('k_dagger_rel', '')} |")
    w = res["width"]
    md += ["", "## Width", "", "| Road | Capacity | Loaded | Empty | Loaded + empty pass | Two loaded pass | Two empty pass |", "|---|---|---|---|---|---|---|"]
    for k, x in w["roads"].items():
        md.append(f"| {k} | {x['capacity']} | {x['loaded']} | {x['empty']} | {x['loaded_empty_pass']} | {x['two_loaded_pass']} | {x['two_empty_pass']} |")
    md += ["", f"An empty and a loaded vehicle can pass if road width ≥ D + w_e + c_lat = {w['threshold_loaded_empty_m']:.2f} m; two loaded vehicles if ≥ 2D + c_lat = {w['threshold_two_loaded_m']:.2f} m.", "",
           "| E7 level | Lv | D | ≤ 10 m lane | ≤ 12 m lane | Empty-pass threshold | Two-loaded threshold |", "|---|---|---|---|---|---|---|"]
    for x in w["e7"]:
        md.append(f"| {x['lev']} | {x['Lv']} | {x['D']} | {x['fits_10m']} | {x['fits_12m']} | {x['loaded_empty_threshold']:.2f} | {x['two_loaded_threshold']:.2f} |")
    s = res["set"]
    md += ["", "## Vehicle set", "", f"{s['model']}; Lv = {s['Lv']} m, B = {s['B']} m, empty {s['plat_len']} m × {s['plat_w']} m ({s['files']} files × "
           f"{s['axle_lines_per_file']} axle lines = {s['axle_lines_in_footprint']} axle lines); a 1,500 t monopile at 18.75 t per axle line needs {s['axle_lines_needed_1500t']} axle lines."]
    (out / "facts.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
