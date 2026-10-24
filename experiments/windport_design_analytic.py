"""Analytic part of the design analyses (single process, no simulation):
  eem      Eemshaven Gode Wind 3 single lane (794.6 m measured on imagery, 11.3 m wide): loaded-speed thresholds at which it
           crosses the "any dispatching" critical line (τ_cut = t_ℓ + t_e = p) and the one-group-at-a-time quay-zone criterion
           (τ_zone1 = t_ℓ + d_q + t_e^occ = p): occupancy-time formula (windport_analytic.tau, as in Fig. 12 and the
           real-port points of the public-site survey), bisection on speed; geometry legacy40 (the survey points) and main2.
  sites    Two-stage screening of 8 public sites (the haul paths measured on public satellite imagery (not released)). Stage
           1, geometry: vertices of the path polyline with turn angle ≥ turn_deg count as junctions; junction occupancy τ_j =
           loaded (D + L_v + δ)/v + stop-and-steer (steer + θ·L_v/2/v) + one empty pass (D + L_e + δ)/v_e + sweep turn_sweep_s
           (D = road width of the adjacent segments, unrestricted_w for open sites), treated as a short single lane in the
           τ/p criterion; single-lane segments use τ_cut from critical_points. Stage 2, capacity: fleet cycle
           c = h_p + h_d + path/v + Σ stop-and-steer + path/v_e, long-run K_rate = ⌈c/p⌉; window form K_win = smallest K with
           S + K·⌈(L − p)/c⌉ ≥ ⌊L/p⌋ (L = 12 h, S = 1); for comparison, the smallest K at which the binding term of the
           unified bound W″_lift(12 h) on the A1 proxy (port_rows configuration of the public-site survey) is the crane.
  crane    Public lifting capacity–radius data of installation-vessel main cranes and the distance-based S_r interval.
  checks   Minimal geometry validation set (four configurations × five items).
  campaign Full parameter table of the campaign model of Section 6.3, and the recomputation of 1.21–1.22 days with the E3
           port times of the main geometry.
Output results/windport_design_analytic_<config hash>/. Run: python experiments/windport_design_analytic.py
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

import windport_runs as T                                        # noqa: E402

KMH = 1 / 3.6
CODE = ["experiments/windport_design_analytic.py", "experiments/windport_survey.py", "experiments/windport_analytic.py",
        "experiments/windport_spatial_analytic.py", "experiments/windport_runs.py", "windport/archetypes.py", "windport/main2.py", "windport/bound3.py",
        "windport/bound_all.py", "windport/sim.py", "windport/sim4.py", "occupancy/params.py", "occupancy/network.py"]
INPUTS = ["results/runs/survey/haulpaths.json", "results/runs/survey/critical_points.csv", "results/runs/main2_geom/rows_reach.csv",
          "results/runs/main2_geom/summary.csv"]
E3_DIR = "results/runs/maingeom_e1e3_e3"          # E3 rerun on the main geometry (not changed by the main2 geometry: tandem, no unloading)


def wcsv(path, rows):
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- Eemshaven speed thresholds
def eem_cfg(route, lane, m, v):
    import windport_analytic as A6
    import windport_spatial_analytic as A7
    geo = dict(kind="A1", n_cradles=6, cradle_mode=m, dist_m=route - 100.0, corridor_m=max(10.0, lane), n_junctions=0)
    return A6.cfg_e4("A1", "base", m, A7.GRIDS["critical"]["K"], 1, 12, 24, extra_p=dict(v_loaded=v * KMH), geo=geo)


def eem():
    import windport_analytic as A6
    import windport_survey as TS
    from windport import archetypes as A
    from windport import main2
    from windport import sim2 as S2
    h = TS.haul_survey(json.loads(TS.HAUL.read_text(encoding="utf-8")))["eemshaven_gw3"]
    route, lane = h["len_m"], h["lane_m"]
    rows = []
    for geom in ("legacy40", "main2"):
        if geom == "main2":
            main2.use()
        else:
            A.use("legacy40")
        S2._NETS.clear()
        for m in T.MODES:
            tau = lambda v: A6.tau(eem_cfg(route, lane, m, v))
            row = dict(geometry=geom, mode=m, route_m=route, lane_m=lane, lane_w=h["min_fixed_w_m"])
            for v in (1.0, 2.5):
                t = tau(v)
                row[f"cut_p_{v}"], row[f"zone1_p_{v}"] = round(t["cut"] / 3600, 3), round(t["zone1"] / 3600, 3)
            for k in ("cut", "zone1"):
                f = lambda v: tau(v)[k] / 3600.0 - 1.0               # decreases monotonically with speed
                lo, hi = 0.3, 8.0
                if f(lo) < 0 or f(hi) > 0:
                    row[f"v_{k}"] = None
                    continue
                while hi - lo > 1e-4:
                    mid = (lo + hi) / 2
                    lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
                row[f"v_{k}"] = round((lo + hi) / 2, 3)
            t = tau(1.0)
            row.update(tl_1=round(t["tl"], 1), te_1=round(t["te"], 1), dq_1=round(t["dq"], 1), te_occ_1=round(t["te_occ"], 1), res=t["res"])
            rows.append(row)
            S2._NETS.clear()
    A.use("legacy40")
    return rows


# ---------------------------------------------------------------- public-site screening
def turns_of(xy, deg):
    out = []
    for i in range(1, len(xy) - 1):
        a = math.atan2(xy[i][1] - xy[i - 1][1], xy[i][0] - xy[i - 1][0])
        b = math.atan2(xy[i + 1][1] - xy[i][1], xy[i + 1][0] - xy[i][0])
        th = abs((b - a + math.pi) % (2 * math.pi) - math.pi)
        if math.degrees(th) >= deg:
            out.append((i, th))
    return out


def sites():
    import windport_survey as TS
    from occupancy import params as PP
    from windport import sim as WS
    p = dict(PP.DEFAULTS, **WS.BASE)
    Lv, d, Le, ve, steer, sw, deg = p["Lv"], p["long_clear"], p["plat_len"], p["v_empty"], p["sweep_steer_s"], p["turn_sweep_s"], p["turn_deg"]
    haul = json.loads(TS.HAUL.read_text(encoding="utf-8"))
    surv = TS.haul_survey(haul)
    crit = list(csv.DictReader(open(ROOT / "results/runs/survey/critical_points.csv", encoding="utf-8")))
    rows = []
    for k, s in haul.items():
        name = TS.HAUL_PORTS[k]["name"]
        xy = TS.proj(s["path"])
        segs = TS.segments(k, s)
        W = [g["width_m"] if g["width_m"] is not None else p["unrestricted_w"] for g in segs]
        tn = turns_of(xy, 0.0)                                          # every interior vertex of the polyline counts as a junction (stop-and-steer and sweep added when the angle ≥ turn_deg)
        route = surv[k]["len_m"]
        for v_kmh in (1.0, 2.5):
            v = v_kmh * KMH
            jt = []
            for i, th in tn:
                D = max(W[i - 1], W[i])
                turn = math.degrees(th) >= deg
                tl = (D + Lv + d) / v + (steer + th * Lv / 2 / v if turn else 0.0)
                te = (D + Le + d) / ve + (sw if turn else 0.0)
                jt.append(dict(D=D, deg=round(math.degrees(th), 1), turn=turn, tl=tl, te=te, tau=tl + te))
            D90 = max(W)                                                 # hypothetical: one 90° in-place turn on the path (junction at the widest point of the path)
            tau90 = (D90 + Lv + d) / v + steer + math.pi / 2 * Lv / 2 / v + (D90 + Le + d) / ve + sw
            c = p["hp_s"] + p["hd_s"] + route / v + sum(steer + math.radians(j["deg"]) * Lv / 2 / v for j in jt if j["turn"]) + route / ve
            cr = [r for r in crit if r["name"] == name and abs(float(r["v"]) - v_kmh) < 1e-9]
            lane_cut = max((float(r["ratio_cut"]) for r in cr if float(r["lane_m"]) > 10.0), default=None)
            for pp in (1.0, 0.5):
                P = pp * 3600.0
                jmax = max(jt, key=lambda j: j["tau"]) if jt else None
                rows.append(dict(site=name, key=k, cls=surv[k]["width_class"], route_m=route, lane_m=surv[k]["lane_m"], v=v_kmh, p_h=pp,
                                 n_vertices=len(jt), n_turns=sum(j["turn"] for j in jt), vertex_degs=" ".join(str(j["deg"]) for j in jt),
                                 junction_tau_s=round(jmax["tau"], 1) if jmax else 0.0, junction_tau_p=round(jmax["tau"] / P, 3) if jmax else 0.0,
                                 junction_D=jmax["D"] if jmax else "", turn90_tau_s=round(tau90, 1), turn90_tau_p=round(tau90 / P, 3),
                                 lane_cut_p=None if lane_cut is None else round(lane_cut / pp, 3),
                                 cycle_s=round(c, 1), K_rate=math.ceil(c / P - 1e-9)))
    return rows


KS_SITE = list(range(1, 7))


def sites_w2():
    """The two stage-2 comparisons (the counting formula K_win, which overcounts trips, is not used) on the A1 proxy (port_rows
    of the public-site survey: dist = path − 100 m, single-lane length from imagery, no junctions; S = 1, L = 12 h, G = 24 h,
    main2 geometry, conservative lifting semantics):
      · binding term and value of W″_lift(12 h) (an upper bound: when the binding term is not the crane, the crane cannot be
        the constraint);
      · delivery of the first-come-first-served simulation (windport.sim4.simulate4, verified by the checker check_all).
    K_min = smallest K at which delivery reaches the ship-crane limit ⌊L/p⌋ (empty if no K ≤ 6 reaches it)."""
    import windport_survey as TS
    from windport import archetypes as A
    from windport import bound_all as BA
    from windport import check_all as CA
    from windport import lift as LF
    from windport import main2
    from windport import sim as S
    from windport import sim2 as S2
    from windport import sim4 as S4
    main2.use()
    LF.install()
    S2._NETS.clear()
    surv = TS.haul_survey(json.loads(TS.HAUL.read_text(encoding="utf-8")))
    rows = []
    for k, h in surv.items():
        for v in (1.0, 2.5):
            for m in T.MODES:
                for pp in (1.0, 0.5):
                    nI = math.floor(12 / pp + 1e-9)
                    for K in KS_SITE:
                        c = eem_cfg(h["len_m"], h["lane_m"], m, v)
                        c.update(K=K, n_load=int(12 / pp) + K + 3)
                        c["p"] = dict(c["p"], lift_s=pp * 3600.0)
                        w = BA.parts(c, lift=True)
                        val, keys, cls, sub, nat = BA.binding(BA.terms(w, 12 * 3600.0))
                        net, p, sim, r = S4.simulate4(dict(c, w4=False))
                        D, _, _, _, starts, quay, cal = S4.setup4(c)
                        g, y = S2.idle_nodes(D)
                        ck = CA.check(net, p, sim.trips, starts, quay, cal, False, S.ramp_res(D), S.hold_of(c), sim.H, gate=g, yard=y)
                        rows.append(dict(site=TS.HAUL_PORTS[k]["name"], key=k, v=v, mode=m, p_h=pp, K=K, crane=nI, sim=sum(r["n_vessel"]), w2=val,
                                         w2_binding="+".join(keys), w2_cls=cls, check_ok=int(ck["ok"])))
    S2._NETS.clear()
    A.use("legacy40")
    return rows


# ---------------------------------------------------------------- crane data and geometry checks
CRANES = [
    # (vessel, owner, crane, capacity t, radius m, breadth m, quote, source, page)
    ("Vole au Vent", "Jan De Nul", "Liebherr (main crane)", 1500, 21.5, 41.0, "1,500 t at 21.5 m", "https://jandenul.com/sites/default/files/public/Vole%20au%20vent.pdf", "p.2"),
    ("Les Alizés", "Jan De Nul", "Huisman 5,000 t", 5000, 36.0, 52.0, "Main block 5,000 t at 36 m", "https://jandenul.com/sites/default/files/public/Les%20Aliz%C3%A9s_0.pdf", "p.2"),
    ("Orion", "DEME", "Liebherr HLC 295000", 3000, 50.0, 49.0, "5,000 tonnes to a radius of more than 30 metres and 3,000 tonnes to a radius of more than 50 metres",
     "https://www.khl.com/1125537.article", "web (2017-03-01)"),
    ("Orion", "DEME", "Liebherr HLC 295000", 5000, 35.0, 49.0, "a maximum lifting capacity of 5000 t at an outreach of 35 m",
     "https://www.drybulkmagazine.com/ports-terminals/01042020/liebherr-heavy-lift-crane-installation-near-to-completion/", "web (2020-04-01)"),
    ("Aegir", "Heerema", "main crane", 5000, 33.0, 46.0, "5,000 mT between 18-33m radius", "https://www.heerema.com/hubfs/HMC%20Equipment%20Folder_20211108.pdf", "p.11"),
    ("Seaway Strashnov", "Seaway7", "main crane", 5000, 32.0, 47.0, "Maximum revolving capacity 5,000t at 32m (search excerpt; source returned 403, not checked directly)",
     "https://www.subsea7.com/content/dam/subsea7-corporate2018/Datasheets/Vessel/2026/Seaway_Strashnov-300dpi.pdf.downloadasset.pdf", "p.1 (to be checked against the full text)"),
    ("Thialf", "Heerema", "main crane (single)", 7100, 31.2, 88.4, "Main hoist 7,100 t up to 31.2 m", "https://www.heerema.com/hubfs/HMC%20Equipment%20Folder_20211108.pdf", "p.7"),
    ("Sleipnir", "Heerema", "main crane (single)", 4000, 82.0, 102.0, "4,000 mT at 82 m radius", "https://www.heerema.com/hubfs/HMC%20Equipment%20Folder_20211108.pdf", "p.5"),
]
NOT_FOUND = ["Voltaire (3,200 t, datasheet gives no radius)", "Svanen", "Boreas", "Cadeler A/M class", "Huisman OSC / tub mast product sheet", "Liebherr HLC/CAL product load charts", "Saipem"]
FENDER_M = 2.0                       # hull-to-quay-line (fender) gap: assumed value, used only for one end of the interval
DEDICATED = ("Les Alizés", "Orion")  # dedicated XXL monopile installation vessels; the others are references (heavy-lift vessels, crane vessels)


def s_r(Rq, d0=8.25, pitch=15.36):
    return 0 if Rq < d0 else 1 + math.floor((Rq - d0) / pitch + 1e-9)


def crane():
    """For capacity Q ≥ 2,000 t, the working radius for a 2,000–2,500 t monopile is at least the given R (the load–radius curve
    decreases with radius); R_q = R − distance a from the slewing centre to the quay line, a in [5 m (slewing centre at the
    side, e.g. leg-encircling crane), breadth/2 + fender FENDER_M (slewing centre on the centreline)]. S_r is the resulting
    lower-bound interval."""
    rows = []
    for v, own, cr, Q, R, Bv, q, url, pg in CRANES:
        a_lo, a_hi = 5.0, Bv / 2 + FENDER_M
        rows.append(dict(vessel=v, owner=own, crane=cr, Q_t=Q, R_m=R, breadth_m=Bv, quote=q, source=url, page=pg,
                         applies=int(Q >= 2000), dedicated=int(v in DEDICATED), Rq_lo=round(R - a_hi, 1), Rq_hi=round(R - a_lo, 1),
                         Sr_lo=s_r(R - a_hi) if Q >= 2000 else "", Sr_hi=s_r(R - a_lo) if Q >= 2000 else "",
                         a_for_Sr2=round(R - 23.61, 2) if Q >= 2000 else ""))
    return rows


def checks():
    """Minimal geometry validation set: S = 1 tandem, S = 3 side by side, S = 6 side by side, S = 3 tandem with t_sh; five
    items. Geometry from the archetypes main geometry and the rows_reach / geometry-check summary of the main2 geometry."""
    from windport import archetypes as A
    from windport import main2
    from occupancy import params as PP
    from windport import sim as WS
    p = dict(PP.DEFAULTS, **WS.BASE)
    Lv, B, d, c = p["Lv"], p["B"], p["long_clear"], p["lat_clear"]
    g = dict(A.GEOMETRIES["main"])
    sp = A.DEFAULTS["cradle_spacing"]
    rr = list(csv.DictReader(open(ROOT / INPUTS[2], encoding="utf-8")))
    dist = [float(r["dist_m"]) for r in rr if r["lv"] == "base"]
    pitch = float(rr[0]["pitch_m"])
    gs = list(csv.DictReader(open(ROOT / INPUTS[3], encoding="utf-8")))
    ser = [r for r in gs if r["layout"] == "tandem" and r["kind"] == "A1" and r["lv"] == "110"]
    rows_ = [r for r in gs if r["layout"] == "rows" and r["lv"] == "110"]
    ok = lambda xs: all(r["ok"] == "1" for r in xs)
    mn = lambda xs, k: min(float(r[k]) for r in xs)
    # public data of the dedicated monopile vessels (Les Alizés, Orion): R_q limit with the slewing centre on the centreline (low end) / at the side (high end)
    ded = [r for r in crane() if r["applies"] and r["vessel"] in DEDICATED]
    pv = max(r["R_m"] - (r["breadth_m"] / 2 + FENDER_M) for r in ded)
    pv_hi = max(r["R_m"] - 5.0 for r in ded)
    out = []

    def add(cfg, item, verdict, value, note):
        out.append(dict(config=cfg, item=item, verdict=verdict, value=value, note=note))
    # S = 1 tandem
    add("S=1 tandem", "1 monopile footprint", "pass", f"pile centreline {dist[0]:.2f} m from the quay line, pile edge {dist[0] - B / 2:.2f} m", "pile fully on land (geometry check piles_on_land = 1)")
    add("S=1 tandem", "2 SPMT access paths", "pass" if ok(ser) else "fail", f"minimum sweep clearance water {mn(ser, 'min_water')} / piles {mn(ser, 'min_piles')} / single-lane flanks {mn(ser, 'min_flanks')} m",
        "geometry check of the main2 geometry: loading, return and unloading all pass")
    add("S=1 tandem", "3 adjacent-monopile interference", "pass", "only one cradle position", "—")
    add("S=1 tandem", "4 crane working radius", "pass", f"needs R_q ≥ {dist[0]:.2f} m",
        f"anchor Orion (dedicated monopile vessel, 3,000 t at > 50 m): with the slewing centre on the centreline R_q ≥ {pv:.1f} m ≥ {dist[0]:.2f} m (Vole au Vent 1,500 t at 21.5 m only as a 1,500 t class reference)")
    add("S=1 tandem", "5 vehicle exclusion zone during lifting", "pass", "below the load (its apron segment and junction) exclusive in [s, s + t_u]", "conservative lifting semantics (lift.under_res), verified trip by trip by the checker")
    # S = 3 tandem with t_sh
    gap = sp - Lv
    add("S=3 tandem with t_sh", "1 monopile footprint", "pass", f"cradle positions {g['gate_cradle_m']:.0f} / {g['gate_cradle_m'] + sp:.0f} / {g['gate_cradle_m'] + 2 * sp:.0f} m from the gate", "all three piles on land")
    add("S=3 tandem with t_sh", "2 SPMT access paths", "pass" if ok(ser) else "fail", "as S=1 (all S3 combinations pass the geometry check)", "—")
    add("S=3 tandem with t_sh", "3 adjacent-monopile interference", "fail" if gap < d else "pass", f"end clearance between adjacent piles {gap:.1f} m (cradle spacing {sp:.0f} m − L_v {Lv:.0f} m), longitudinal clearance δ = {d:.0f} m",
        f"design rule: tandem cradle spacing ≥ L_v + δ = {Lv + d:.0f} m (sensitivity in the spacing part of windport_rows_exclusion, core cases only; Tables 7 and 14 and tandem S ≥ 2 of the joint design keep the main geometry {sp:.0f} m)")
    add("S=3 tandem with t_sh", "4 crane working radius", "pass (vessel shift)", "each far cradle along the quay line takes an extra ship-crane time t_sh = 1 h", "main rule S_r = 1, t_sh = 1 h (spatial additions)")
    add("S=3 tandem with t_sh", "5 vehicle exclusion zone during lifting", "pass", "the apron segment and junction below the load are exclusive; the vehicle bringing the next pile may not enter", "verified trip by trip by the checker")
    # side by side
    for S in (3, 6):
        need = dist[S - 1]
        add(f"S={S} side by side", "1 monopile footprint", "pass", f"row pitch {pitch} m, lateral clearance between adjacent piles {pitch - B:.2f} m (≥ empty vehicle width 4.86 + c)", "piles at x = 60–170 m, all on land")
        add(f"S={S} side by side", "2 SPMT access paths", "pass" if ok(rows_) else "fail",
            f"minimum sweep clearance water {mn(rows_, 'min_water')} / piles {mn(rows_, 'min_piles')} / single-lane flanks {mn(rows_, 'min_flanks')} m", "geometry check of the main2 geometry (S = 6, all 6 rows)")
        add(f"S={S} side by side", "3 adjacent-monopile interference", "pass", f"the delivering vehicle drives in along the row; clearance of the vehicle (pile width {B} m) to the piles of the adjacent row {pitch - B:.2f} m ≥ c = {c:.0f} m", "—")
        verdict = "pass" if pv >= need else ("within the interval (reachable only with the slewing centre at the side)" if pv_hi >= need else "fail")
        add(f"S={S} side by side", "4 crane working radius", verdict, f"all reachable needs R_q ≥ {need:.2f} m; public data of dedicated monopile vessels give an R_q lower limit of {pv:.1f}–{pv_hi:.1f} m (slewing centre on centreline / at side)",
            "S_r = 1 + ⌊(R_q − 8.25)/15.36⌋; rows that fail get t_sh by the distance-based S_r (main rule S_r = 1, also S_r = 2)")
        add(f"S={S} side by side", "5 vehicle exclusion zone during lifting", "fail (model closes only the row in use) → pass with the added rule",
            f"when lifting from row k the load passes over rows 0…k−1 closer to the quay", "added: while row k is lifted, rows 0…k−1 are exclusive in [s, s + t_u] (windport_rows_exclusion, simulation and checker changed together)")
    return out


# ---------------------------------------------------------------- campaign model
def campaign():
    import windport_spatial_analytic as AA
    g = AA.GRIDS["campaign"]
    a = 1 - 1 / g["spell_blocks"]
    par = [dict(parameter="n_total", value=g["n_total"], unit="piles", meaning="total monopiles of the campaign (one vessel)"),
           dict(parameter="n_v", value="3 / 10", unit="piles/voyage", meaning="piles loaded per voyage"),
           dict(parameter="voyages", value="20 / 6", unit="voyages", meaning="⌈n_total / n_v⌉"),
           dict(parameter="T_port", value="E3 port time (table tab_e3: base / long single lane 1 km/h × K = 1, 2, pull-in S = 1)", unit="h",
                meaning="port time per voyage: one set each for the road-occupancy model and the fixed-duration representation"),
           dict(parameter="transit_h", value=g["transit_h"], unit="h", meaning="one-way transit (once out, once back, not affected by weather)"),
           dict(parameter="install_h", value=g["install_h"], unit="h/pile", meaning="installation time per pile, counted only in workable blocks, may accumulate across blocks"),
           dict(parameter="block_h", value=g["block_h"], unit="h", meaning="time step (one block) of the weather chain"),
           dict(parameter="q", value="0.6 / 0.8", unit="—", meaning="stationary probability of a workable block (the operating threshold is expressed through q: workable = block with sea state below the installation limit; no measured sea states used)"),
           dict(parameter="spell_blocks", value=g["spell_blocks"], unit="blocks", meaning="mean number of consecutive workable blocks (24 h)"),
           dict(parameter="P(W→W)", value=round(a, 4), unit="—", meaning="1 − 1/spell_blocks"),
           dict(parameter="P(W→U)", value=round(1 - a, 4), unit="—", meaning="1/spell_blocks"),
           ]
    for q in g["q"]:
        b = max(0.0, 1 - q * (1 - a) / (1 - q))
        par += [dict(parameter=f"P(U→U), q = {q}", value=round(b, 4), unit="—", meaning="max(0, 1 − q(1 − a)/(1 − q)), so that the stationary probability is q"),
                dict(parameter=f"P(U→W), q = {q}", value=round(1 - b, 4), unit="—", meaning=f"unworkable spells last {1 / (1 - b):.2f} blocks on average"),
                dict(parameter=f"π_W check, q = {q}", value=round((1 - b) / ((1 - a) + (1 - b)), 4), unit="—", meaning="stationary probability of the two-state chain (1 − b)/((1 − a) + (1 − b))")]
    par += [dict(parameter="initial state", value="Bernoulli(q)", unit="—", meaning="drawn independently for each seed"),
            dict(parameter="seeds", value="1–200", unit="—", meaning="random.Random(seed); 20,000 blocks per seed"),
            dict(parameter="difference", value="Σ over seeds (occupancy − fixed duration) / 200", unit="days", meaning="difference in campaign duration between the two representations on the same weather sequence (mean, P10, P90)")]
    saved = g["e3_dir"]
    g["e3_dir"] = E3_DIR
    try:
        rows = AA.campaign()
    finally:
        g["e3_dir"] = saved
    return par, rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE + INPUTS}
    cfg = dict(task="design", part="analytic", code=code, e3=E3_DIR, cranes=CRANES, fender=FENDER_M)
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    out = ROOT / "results" / f"windport_design_analytic_{h}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    wcsv(out / "crane.csv", crane())
    (out / "crane_not_found.json").write_text(json.dumps(NOT_FOUND, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    wcsv(out / "checks.csv", checks())
    par, cam = campaign()
    wcsv(out / "campaign_params.csv", par)
    wcsv(out / "campaign.csv", cam)
    wcsv(out / "sites.csv", sites())
    wcsv(out / "eem.csv", eem())
    wcsv(out / "sites_w2.csv", sites_w2())
    print(out)


if __name__ == "__main__":
    main()
