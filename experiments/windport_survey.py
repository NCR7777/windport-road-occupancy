"""Public road-network survey of real monopile marshalling ports / direct-shipment ports at manufacturing sites (OpenStreetMap,
© OpenStreetMap contributors, ODbL); adds a "public survey range" column to the parameter register and real-port points to
Fig. 12 (fig:critical). Only a few distances are measured, no full road network is mapped, no shipyard maps are used.

--fetch [port ...]  re-fetch the raw JSON from Overpass (stored as results/runs/survey/osm/<port>.json and <port>.meta.json:
                    query, fetch time, OSM data timestamp).
(default)           offline: only reads the saved JSON and recomputes all numbers; writes results/runs/survey/: survey.json
                    (all measurements per port and the per-way tags of the routes), critical_points.csv (the real-port points use
                    the haul paths measured on public satellite imagery (not released), haulpaths.json, geometry only; as the
                    real-port branch of windport_spatial_analytic.critical: A1 set by path length, single-lane length = the
                    imagery-measured stretch with a fixed width below 15.36 m (0 if none), speeds 1 and 2.5 km/h),
                    fig12_survey.png (draft), config.json (hashes of code, OSM and haulpaths files), segments_public.csv
                    (per-segment table without coordinates, for the route strip diagram in the manuscript; the polylines and
                    measurement lines of haulpaths.json are not released); and writes the parameter register CSV of the survey
                    (CSV_DOC; imagery paths as the main measure, OSM as reference).
Run: python experiments/windport_survey.py
"""
import argparse
import csv
import hashlib
import io
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from windport import port_survey as PS                           # noqa: E402

OUT = ROOT / "results" / "runs/survey"
OSM = ROOT / "data" / "osm"
CSV_DOC = ROOT / "results" / "runs" / "survey" / "register_sites.csv"
CRIT136 = "results/runs/critical/critical.csv"
CODE = ["windport/port_survey.py", "experiments/windport_survey.py", "experiments/windport_spatial_analytic.py", "experiments/windport_analytic.py",
        "windport/archetypes.py", "windport/bound3.py", "windport/sim4.py", "experiments/windport_runs.py"]
V = [1.0, 2.5]                     # km/h: as for Baltica 2 in the spatial additions (monopile-specific speed not published; 1 km/h slow case, 2.5 km/h Kassels model)
MIN_ROUTE = 120.0                  # in A1 the cradle row to cradle distance is dist_m + 100 m; shorter routes are not put into Fig. 12
# identification level: A = the working area / plant is an OSM area with a name (or operator); B = only identified down to the
# enclosing industrial land-use area or port area (farthest distance is at port-area scale, too large)
PORTS = [
    dict(key="maasvlakte", name="Rotterdam Maasvlakte 2 (Sif)", kind="direct shipment from manufacturing site", level="A", bbox=[51.955, 3.99, 51.98, 4.035],
         area=[["way", 598924443]], area_how="OSM area 'Sif Maasvlakte 2' (landuse=industrial, operator=Sif)",
         src=[("https://offshorewind.biz/2017/01/03/sifs-maasvlakte-2-operational-innovation-picks-up-galloper-monopiles",
               "'the first four monopiles were loaded from Sif's Maasvlakte 2 site'; 'The first 150 meters of the new quay are now ready'; 'the 42-hectare terminal' (2017-01-03)",
               "2026-10-23")]),
    dict(key="fene", name="Ferrol / Fene (Navantia Seanergies-Windar)", kind="direct shipment from manufacturing site", level="A", bbox=[43.46, -8.20, 43.485, -8.16],
         area=[["way", 34692108]], area_how="OSM area 'Estaleiro Navantia - Fene' (landuse=industrial)",
         src=[("https://www.mammoet.com/cases/14-xxl-monopiles-readied-for-installation-with-efficient-movements-and-specialized-equipment/",
               "'Navantia's Fene production facility in Ferrol'; 'moved to a temporary storage area, near the quayside'; 'using a ro-ro ramp, avoiding the need for cranes'; "
               "'a full 180-degree rotation' (no distances given)", "2026-10-23")]),
    dict(key="nordenham", name="Nordenham-Blexen (Steelwind)", kind="direct shipment from manufacturing site", level="A", bbox=[53.505, 8.50, 53.545, 8.57],
         area=[["way", 213115192], ["way", 293282997]], area_how="OSM areas 'Steelwind' (plant) and 'Steelwind Lagerfläche' (yard), combined",
         src=[("https://offshorewind.biz/2019/10/21/jumbo-picks-up-first-yunlin-monopiles",
               "'arrived at Steelwind Nordenham's quayside'; 'the heavy-lift terminal Blexen'; 'the first four monopiles' (2019-10-21)", "2026-10-23"),
              ("https://www.offshorewind.biz/2025/10/13/steelwind-loads-out-final-baltic-power-monopiles/",
               "'its port facility in Germany'; 'all 78 monopiles that the company produced were successfully delivered' (2025-10-13)", "2026-10-23")]),
    dict(key="rostock", name="Rostock Überseehafen (EEW SPC)", kind="direct shipment from manufacturing site", level="B", bbox=[54.14, 12.095, 54.165, 12.135],
         area=[["way", 114078402]], start_name="Am Eisenwerk",
         area_how="public address of EEW SPC, Am Eisenwerk 1 (wirtschaftsforum.de); the plant has no separate area in OSM, so the industrial land-use area "
                  "containing that street is used (125 ha, Liebherr is in the same area); start points only on road nodes of Am Eisenwerk",
         src=[("https://www.ajot.com/news/liebherr-heavy-duty-crane-loads-monopiles",
               "'loaded directly into the water at berth 15 in Rostock's overseas port' (2020-11-10)", "2026-10-23"),
              ("https://eew-group.com/locations/eew-spc/", "'Direct access to the quay enables uncomplicated transport of the monopiles to the wind farm.'", "2026-10-23"),
              ("https://www.wirtschaftsforum.de/eew-special-pipe-constructions-gmbh", "Anschrift: 'Am Eisenwerk 1 18147 Rostock'", "2026-10-23")]),
    dict(key="ronne", name="Rønne (Bornholm)", kind="marshalling port", level="B", bbox=[55.090, 14.670, 55.115, 14.705],
         area=[["way", 1038343418]], area_how="OSM area 'Rønne Havn' (industrial=port, 62 ha, whole port area); public sources do not name the yard used for marshalling",
         src=[("https://oceannews.com/news/energy/mammoet-completes-first-electric-monopile-transport-in-real-world-conditions/",
               "'receive, marshal, and load-out 111 1,700 t monopiles at the Port of Ronne'; 'a single 1,700 t monopile was transported 815 meters'", "2026-10-22"),
              ("https://sheetpiling.arcelormittal.com/sites/default/files/2024-04/AMCRPS_CS%20038_Port%20of%20Ronne_Bornholm_Denmark_GB_web.pdf",
               "'Quay 33, a heavy-duty quay ... Quay 33 is around 280 m long'", "2026-10-22")]),
    dict(key="vlissingen_scaldia", name="Vlissingen (Verbrugge Scaldia Terminals)", kind="marshalling port", level="A", bbox=[51.43, 3.62, 51.465, 3.72],
         area=[["way", 1226608116]], area_how="OSM area 'Verbrugge Scaldia Terminals B.V.'; public sources only say Verbrugge Terminals, not which of the two terminals",
         src=[("https://offshorewind.biz/2014/06/04/verbrugge-terminals-loads-in-first-eneco-luchterduinen-monopile",
               "Verbrugge Terminals 'in the Port of Vlissingen successfully completed the first load-in' (Luchterduinen, 2014-06-04); "
               "'over 200 hectares and over 3.000m of heavy duty quay side'", "2026-10-23")]),
    dict(key="vlissingen_zeeland", name="Vlissingen (Verbrugge Zeeland Terminals)", kind="marshalling port", level="A", osm="vlissingen", bbox=[51.43, 3.62, 51.465, 3.72],
         area=[["way", 854930096]], area_how="OSM area 'Verbrugge Zeeland Terminals'; as above, one of the two",
         src=[("https://offshorewind.biz/2014/06/04/verbrugge-terminals-loads-in-first-eneco-luchterduinen-monopile", "as above", "2026-10-23")]),
]
for _p in PORTS:
    _p.setdefault("osm", _p["key"].split("_")[0])
# the OSM "waterside of the working area" is all water-edge lines within 25 m of the working-area boundary (including slipways,
# dock entrances, breakwaters), not the monopile berth length; berth lengths stated in public sources are recorded as given
QUAY_PUB = dict(maasvlakte="first stretch 150 m (2017-01, offshorewind.biz); full length not published", fene="not published (RoRo ramp loading)",
                nordenham="not published", rostock="berth 15, length not published",
                ronne="Quay 33 about 280 m (ArcelorMittal); the OSM water edge includes breakwaters, not used as quay length",
                vlissingen_scaldia="Verbrugge total > 3,000 m heavy-duty quay (both terminals together, offshorewind.biz 2014)", vlissingen_zeeland="as above")
# ports that cannot be identified (not forced)
GAPS = [
    ("Eemshaven (Buss Terminal)", "no OSM area for Buss Terminal (only the 335 ha 'Westelijk Industrieterrein'); public sources only place it in the north of "
                                  "Juliana harbour basin (GSP page returns 403, to be checked in full text)"),
    ("Odense / Lindø (Bladt -> CS Wind Offshore)", "certificate error on bladt.dk, only the title on doi.dk; OSM has only the 225 ha whole-port area "
                                                   "'Odense Havn', plant and loading quay cannot be identified"),
    ("Esbjerg (Horns Rev 3)", "public sources only name Esbjerg as base port (offshorewind.biz 2017-10-02), no quay or yard"),
    ("Deutsche Bucht (port on the Elbe estuary)", "monopiles lifted from barges directly onto the installation vessel, not landed (windtech-international 2018-08-29), no SPMT leg"),
    ("Mukran (Sassnitz)", "public material covers Arkona transition pieces and towers, no monopile marshalling found"),
    ("Taichung port (Formosa 1 phase 2)", "Jan De Nul leased 7.6 ha for monopile storage and loading (offshorewind.biz), quay number not given"),
    ("Oostende (REBO)", "only a quay bearing capacity of 20 t/m² (bluecluster.eu), no monopile working area found"),
]

# ---------------------------------------------------------------- haul paths measured on imagery (main measure)
HAUL = OUT / "haulpaths.json"
TA, TC = 15.36, 20.0               # width class limits (as on the checking page index.html): A < TA loaded monopile vehicle alone; B an empty vehicle can pass a loaded one; C >= TC or no fixed narrow point
# node interval of the single-lane stretch on the path polyline (A class only): Gode Wind 3 runs along the port road on the
# west side of Juliana harbour basin, measured on imagery as about 795 m (taken as 795 m)
LANE_SPAN = dict(eemshaven_gw3=(1, 4))
# three site classes
SITE_CLS = dict(open="dedicated marshalling quay or manufacturing site, yard right behind the quay front (interface-limited)",
                road="split-site marshalling or through the port area / public roads (road-constrained or opened by calendar)")
HAUL_PORTS = {p["key"]: dict(name=p["name"], kind=p["kind"], level=p["level"], cls="open") for p in PORTS}
HAUL_PORTS["nordenham"]["cls"] = "road"
HAUL_PORTS["eemshaven_gw3"] = dict(name="Eemshaven (Gode Wind 3: BOW storage area → Wagenborg quay)", kind="split-site marshalling", level="A", cls="road")
# why the farthest OSM route is not the actual haul path (from the notes in haulpaths.json; Fene, Scaldia and Nordenham have no
# note and are written from the OSM survey method)
OSM_WHY = dict(
    maasvlakte="the OSM route goes round the east side of the plant to the south end; the actual path runs west from the east edge of the storage block straight across the open yard to the quay",
    fene="the OSM start is the farthest road node inside the plant area and includes the in-plant transport hall -> jetty (outside the loading window); "
         "the monopiles are actually stored right at the jetty quay front",
    nordenham="OSM follows the mapped roads, no road is mapped on the pavement between yard and shore; the actual path crosses on the paved road over the dike; "
              "both lengths are similar",
    rostock="essentially the same as the imagery path",
    ronne="the OSM start falls in the power-plant area in the north-east corner of the port; the actual path runs straight across the open yard behind the quay to the front",
    vlissingen_scaldia="the OSM start is the farthest road node inside the working area and detours along mapped roads; the actual path crosses the open area "
                       "south-west of the warehouse to the front",
    vlissingen_zeeland="the OSM route goes round the warehouse area; the actual path crosses the open area diagonally from the far end of the yard to the quay",
    eemshaven_gw3="not measured in the OSM survey (Buss Terminal cannot be identified in OSM; the Gode Wind 3 yard and quay were added afterwards)",
)
SRC_URL = dict(
    eemshaven_gw3="https://www.groningen-seaports.com/en/nieuws/immense-monopiles-transported-through-the-port-area/",
    nordenham="https://cometto.com/stories/big-things-moved-where-big-things-are-created",
)
SRC_EXTRA = dict(
    eemshaven_gw3=f"Groningen Seaports 2023-06-26 'Immense monopiles transported through the port area' ({SRC_URL['eemshaven_gw3']}): "
                  "107 monopiles moved one by one from the BOW yard at Beatrix harbour basin along port roads to the Wagenborg quay on the south bank of Juliana harbour basin, "
                  "lanes added at bends, some sections widened, roads closed and opened 18:00-06:00, the first pile about 5.5 h (quote to be checked verbatim)",
    nordenham=f"Cometto 2022-06 Steelwind Nordenham case ({SRC_URL['nordenham']}): the move crosses two public roads, opening periods set by the "
              "municipality of Nordenham (quote to be checked verbatim)",
)
# only a note for the manuscript parameter table; the parameter register read by the experiments is not changed (run directory names are computed from its content)
DIST_NOTE = ("lower end of the port-type dist_m range 300 -> 100 m: imagery paths are 129-688 m, 2 of them below 300 m; 100 m is also the fixed offset of A1. "
             "Only a note for the manuscript parameter table; the parameter register and the existing experiments are unchanged")
IMG_SRC ="yard-to-loading-quay paths measured on public satellite imagery (Esri World Imagery)"
PUBLIC_CSV = OUT / "segments_public.csv"   # no coordinates, for the route strip diagram of the manuscript; haulpaths.json (polylines and measurement lines) is not released


def hav(a, b, r=6371000.0):
    """Algorithm of the checking page (Leaflet map.distance: haversine, R = 6,371,000 m)."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def proj(pts, ref=None):
    """As port_survey: equirectangular projection (R = PS.R) with origin at the centre of the ref polyline (default pts), in m."""
    ref = ref or pts
    lat0 = (min(p[0] for p in ref) + max(p[0] for p in ref)) / 2
    lon0 = (min(p[1] for p in ref) + max(p[1] for p in ref)) / 2
    kx, ky = math.radians(1) * PS.R * math.cos(math.radians(lat0)), math.radians(1) * PS.R
    return [((lo - lon0) * kx, (la - lat0) * ky) for la, lo in pts]


def local_len(pts):
    return PS.plen(proj(pts))


def width_class(site):
    w = [x["w"] for x in site["widths"] if x.get("fixed", True)]
    if not w:
        return None, "C"
    m = min(w)
    return m, "A" if m < TA else "B" if m < TC else "C"


def segments(k, s):
    """Path segment by segment (adjacent polyline nodes form a segment, no coordinates): length, width class, fixed narrow width.
    A measurement line is assigned to the nearest segment by its midpoint; the segments in the single-lane interval all belong to
    the same A-class road."""
    P = s["path"]
    xy = proj(P)
    i, j = LANE_SPAN.get(k, (0, 0))
    lane_w = min((w["w"] for w in s["widths"] if w.get("fixed", True)), default=None) if j > i else None
    segs = [dict(seg=n + 1, len_m=math.dist(a, b), width_m=lane_w if i <= n < j else None, measured=False,
                 desc="single-lane stretch (same road as the width measurement)" if i <= n < j else "open area (yard, quay pavement)") for n, (a, b) in enumerate(zip(xy, xy[1:]))]
    for w in s["widths"]:
        if not w.get("fixed", True):
            continue                                                # storage aisles are not counted
        m = proj([[(w["a"][0] + w["b"][0]) / 2, (w["a"][1] + w["b"][1]) / 2]], ref=P)[0]
        n = min(range(len(segs)), key=lambda q: PS.seg_dist(m, xy[q], xy[q + 1]))
        g = segs[n]
        g.update(width_m=w["w"] if g["width_m"] is None else min(g["width_m"], w["w"]), measured=True, desc=f"width measured in this segment: {w['note']}")
    for g in segs:
        g["width_class"] = width_class(dict(widths=[dict(w=g["width_m"])] if g["width_m"] is not None else []))[1]
    return segs


def haul_survey(d):
    out = {}
    for k, s in d.items():
        P = s["path"]
        L = local_len(P)
        Lp = sum(hav(a, b) for a, b in zip(P, P[1:]))
        mw, cls = width_class(s)
        segs = segments(k, s)
        lane = sum(g["len_m"] for g in segs if g["width_class"] == "A")
        assert (cls == "A") == (lane > 0), k                       # only class A has a single-lane stretch
        assert abs(sum(g["len_m"] for g in segs) - L) < 1e-6 and min(g["width_class"] for g in segs) == cls, k
        out[k] = dict(len_m=round(L, 1), len_page_m=round(Lp, 1), rel_diff=round(abs(L - Lp) / Lp, 5), min_fixed_w_m=mw, width_class=cls,
                      lane_m=round(lane, 1), n_widths=len(s["widths"]), note=s["note"].replace("[to be checked]", "").strip(),
                      segments=[dict(g, len_m=round(g["len_m"], 1)) for g in segs])
    return out


def port_rows(name, route_m, lane_m, src):
    """As the real-port branch of windport_spatial_analytic.critical (A1 matched by path length: dist_m = path − 100 m), except that
    the single-lane length is given directly (there only the two ends 0 and 100% are given)."""
    import windport_runs as T
    import windport_analytic as A6
    import windport_spatial_analytic as A7
    from windport import sim4 as S4
    rows = []
    for v in V:
        for m in T.MODES:
            dist = route_m - 100.0
            geo = dict(kind="A1", n_cradles=6, cradle_mode=m, dist_m=dist, corridor_m=max(10.0, lane_m), n_junctions=0)
            c = A6.cfg_e4("A1", "base", m, A7.GRIDS["critical"]["K"], 1, 12, 24, extra_p=dict(v_loaded=v * A7.KMH), geo=geo)
            D, net, *_ = S4.setup4(c)
            route = min(sum(net.arc[a][2] for a in net.path(net.stops[o]["node"], net.stops[D["windport"]["cradles"][0]]["node"]))
                        for o in D["windport"]["storage"])
            t = A6.tau(c)
            rows.append(dict(kind="port", name=name, storage="", scen="", mode=m, p=1.0, turn_extra=0.0, route_m=round(route, 1), v=v,
                             lane_frac=round(lane_m / dist, 3), lane_m=geo["corridor_m"], src=src,
                             **{k: (round(x, 1) if isinstance(x, float) else x) for k, x in t.items()},
                             ratio_cut=round(t["cut"] / 3600, 3), ratio_zone1=round(t["zone1"] / 3600, 3), ratio_w=round(t["w"] / 3600, 3)))
    return rows


def load(p):
    meta = json.loads((OSM / f"{p['osm']}.meta.json").read_text(encoding="utf-8"))
    D = PS.Data(json.loads((OSM / f"{p['osm']}.json").read_text(encoding="utf-8")), meta["bbox"])
    return D, meta


def fetch(keys):
    OSM.mkdir(parents=True, exist_ok=True)
    done = set()
    for p in PORTS:
        if p["osm"] in done or (keys and p["osm"] not in keys):
            continue
        d, meta = PS.fetch(p["bbox"])
        meta["bbox"] = p["bbox"]
        (OSM / f"{p['osm']}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        (OSM / f"{p['osm']}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print(p["osm"], len(d["elements"]), meta["osm_base"], flush=True)
        done.add(p["osm"])
        time.sleep(15)                                           # rate limit: one request at a time, 15 s apart


def narrow_txt(st):
    """The width / lanes / oneway tags OSM gives along the route, as they are (way by way); the length without width is recorded
    separately."""
    xs = [f"{w['name'] or w['highway']} ({w['length_m']:.0f} m: " + ", ".join(f"{k}={w[k]}" for k in ("width", "lanes", "oneway") if w[k]) + ")"
          for w in st["ways"] if w["width"] or w["lanes"] or w["oneway"]]
    return "; ".join(xs) if xs else "no width / lanes / oneway tags", st["len_no_width_m"]


def run():
    import windport_spatial_analytic as A7
    rows, res = [], {}
    for p in PORTS:
        D, meta = load(p)
        if not p.get("area"):
            res[p["key"]] = dict(status=p["area_how"])
            continue
        r = PS.survey(D, dict(area=[tuple(a) for a in p["area"]], start_name=p.get("start_name")))
        r["meta"] = dict(fetched_utc=meta["fetched_utc"], osm_base=meta["osm_base"], bbox=meta["bbox"])
        res[p["key"]] = r
    # the real-port points of Fig. 12 use the imagery paths (Okpo and Yantai are not run)
    haul = haul_survey(json.loads(HAUL.read_text(encoding="utf-8")))
    crit = []
    for k, h in haul.items():
        assert h["len_m"] >= MIN_ROUTE, k
        crit += port_rows(HAUL_PORTS[k]["name"], h["len_m"], h["lane_m"], "imagery path")
    A7.wcsv(OUT / "critical_points.csv", crit)
    (OUT / "survey.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    # parameter register: imagery paths as the main measure, OSM as reference
    for key in list(HAUL_PORTS):
        hp, h = HAUL_PORTS[key], haul[key]
        p = next((q for q in PORTS if q["key"] == key), None)
        r = res.get(key, {})
        ok = r.get("status") == "ok"
        nt, nw = narrow_txt(r["far"]) if ok else ("", "")
        # working area counted from an address street (level B): the straight-line columns use the whole land-use area and do not
        # depend on the start points, so they are left empty (survey.json keeps the raw computation)
        street = bool(p and p.get("start_name"))
        note = f"straight-line columns left empty: start points only on {p['start_name']}, the working-area boundary is the whole land-use area, so the straight-line distance does not depend on the start" if street else ""
        src = "; ".join(f"{u} quote: {q} (accessed {d})" for u, q, d in p["src"]) + " (quotes paraphrased by the fetch tool, to be checked verbatim)" if p else ""
        rows.append({"port": hp["name"], "kind": hp["kind"], "level": hp["level"], "site_class": SITE_CLS[hp["cls"]],
                     "haul_path_imagery_m": h["len_m"], "narrowest_fixed_width_m": h["min_fixed_w_m"] if h["min_fixed_w_m"] is not None else "no fixed narrow point",
                     "width_class": h["width_class"], "single_lane_imagery_m": h["lane_m"], "note": h["note"],
                     "osm_why_not_the_actual_path": OSM_WHY[key],
                     "area_how": p["area_how"] if p else "imagery annotation: BOW / Q3 terminal (OSM label) -> Wagenborg quay (Wagenborg quay information)",
                     # the quotes here and in the spatial additions were taken through a web-fetch tool: to be checked word for word
                     "source": "; ".join(x for x in (src, SRC_EXTRA.get(key, "")) if x),
                     "osm_area_ha": r.get("area_ha", ""), "waterside_osm_m": r.get("quay_len_m", ""), "quay_public": QUAY_PUB.get(key, ""),
                     "osm_route_min_m_comparison": r.get("route_min_m", ""), "osm_route_max_m_comparison": r.get("route_max_m", ""),
                     "straight_min_m": "" if street else r.get("straight_min_m", ""), "straight_max_m": "" if street else r.get("straight_max_m", ""),
                     "note": note, "narrow_far": nt, "len_no_width_far_m": nw,
                     "junctions_far": r["far"]["n_junctions"] if ok else "", "turns45_far": r["far"]["n_turns"] if ok else "",
                     "junctions_near": r["near"]["n_junctions"] if ok else "", "turns45_near": r["near"]["n_turns"] if ok else "",
                     "status": r.get("status", "ok (imagery path; no OSM survey)"), "osm_fetched_utc": r.get("meta", {}).get("fetched_utc", ""),
                     "osm_base": r.get("meta", {}).get("osm_base", ""), "copyright": PS.COPYRIGHT if ok else ""})
    for name, why in GAPS:
        rows.append(dict(port=name, level="C", status=f"cannot be identified: {why}", copyright=""))
    rows.append({"port": "(parameter note) archetype_dist_m", "note": DIST_NOTE})
    A7.wcsv(CSV_DOC, rows)
    # public segment table: no coordinates (polylines and measurement lines are not released)
    pub = []
    for key, hp in HAUL_PORTS.items():
        h, p = haul[key], next((q for q in PORTS if q["key"] == key), None)
        urls = [u for u, *_ in p["src"]] if p else []
        src = "; ".join([IMG_SRC] + ([f"operator and quay: {', '.join(urls)}"] if urls else []) + ([SRC_EXTRA[key]] if key in SRC_EXTRA else []))
        for g in h["segments"]:
            pub.append({"site": hp["name"], "kind": hp["kind"], "site_class": SITE_CLS[hp["cls"]], "level": hp["level"],
                        "path_m": h["len_m"], "path_width_class": h["width_class"], "seg": g["seg"], "seg_m": g["len_m"],
                        "seg_width_class": g["width_class"], "fixed_width_m": "" if g["width_m"] is None else g["width_m"],
                        "width_measured_here": int(g["measured"]), "seg_desc": g["desc"], "source": src})
    A7.wcsv(PUBLIC_CSV, pub)
    fig(crit, haul)
    code = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE}
    osm = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(OSM.glob("*.json"))}
    cfg = dict(task="survey (survey: imagery paths as the main measure)", ports=PORTS, gaps=GAPS, v=V, min_route=MIN_ROUTE, turn_deg=PS.TURN_DEG, no_drive=sorted(PS.NO_DRIVE),
               crit136=CRIT136, haul=haul, haul_ports=HAUL_PORTS, lane_span=LANE_SPAN, width_class=dict(TA=TA, TC=TC),
               haul_sha256={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in (HAUL, HAUL.with_suffix(".meta.json"))},
               code=code, code_sha256=hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest(), osm_sha256=osm, copyright=PS.COPYRIGHT)
    (OUT / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return res, crit, haul


def fig(crit, haul):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    cr = [r for r in csv.DictReader(open(ROOT / CRIT136, encoding="utf-8")) if r["part"] == "longrun" and r["p"] == "1.0"]
    fig_, ax = plt.subplots(figsize=(7, 4.5))
    for m, ls, lab_m in (("pull_in", "-", "pull-in"), ("on_road", "--", "roadside")):
        q = sorted((float(r["v"]), r) for r in cr if r["mode"] == m)
        for k, col, lab in (("ell_cut", "C0", "τ_cut = p"), ("ell_zone1", "C3", "τ_zone1 = p")):
            ax.plot([v for v, r in q if r[k]], [float(r[k]) for v, r in q if r[k]], ls, color=col, lw=1, label=f"{lab} ({lab_m})")
    # the two Vlissingen sites are merged into one point; marker = single-lane length, dotted line = full path length (covering both sites' range when two)
    groups = [(k, [k]) for k in haul if not k.startswith("vlissingen")] + [("vlissingen", ["vlissingen_scaldia", "vlissingen_zeeland"])]
    mk = "osD^v<>p"
    cols = ["C1", "C2", "C4", "C5", "C6", "C7", "C8", "C9"]          # C0 and C3 are reserved for the critical lines
    for i, (g, ks) in enumerate(groups):
        dx = (i - (len(groups) - 1) / 2) * 0.07
        hp = HAUL_PORTS[ks[0]]
        lens = sorted(haul[k]["len_m"] for k in ks)
        lane = haul[ks[0]]["lane_m"]
        name = "Vlissingen (two sites)" if len(ks) > 1 else "Eemshaven Gode Wind 3" if g == "eemshaven_gw3" else hp["name"].split(" (")[0]
        lab = f"{name}{' (level B)' if hp['level'] == 'B' else ''}: path {'-'.join(f'{x:,.0f}' for x in lens)} m, single lane {lane:,.0f} m"
        for v in V:
            x, col = v + dx, cols[i % len(cols)]
            ax.plot([x, x], [0, lens[-1]], ":", color=col, lw=0.9)
            ax.plot([x] * len(lens), lens, "_", color=col, ms=7, mew=1.2)
            ax.plot([x], [lane], mk[i % len(mk)], color=col, ms=5, mfc="none" if hp["level"] == "B" else col, label=lab if v == V[0] else None)
    ax.set_xlabel("loaded speed (km/h)")
    ax.set_ylabel("single-lane length (m)")
    ax.set_ylim(-60, 2700)
    ax.set_xlim(0.4, 3.2)
    ax.legend(fontsize=5.5, ncol=2, loc="upper left")
    ax.set_title("Fig. 12 (draft): lines = critical single-lane length (p = 1 h); markers = fixed single-lane length measured on imagery (stretches narrower than 15.36 m, 0 if none);\n"
                 "dotted lines and ticks = full yard-to-loading-quay path length (scale only, not single-lane length); hollow = level B (working-area location inferred at port-area scale);\n"
                 "speed not published, 1 and 2.5 km/h used; paths measured on public satellite imagery (Esri World Imagery)", fontsize=6.5)
    fig_.tight_layout()
    buf = io.BytesIO()
    fig_.savefig(buf, format="png", dpi=150, metadata={"Software": None})
    (OUT / "fig12_survey.png").write_bytes(buf.getvalue())
    plt.close(fig_)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", nargs="*", default=None, help="re-fetch from Overpass (ports may be listed; default all)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.fetch is not None:
        fetch(set(a.fetch))
        return
    res, crit, haul = run()
    for k, r in res.items():
        print(k, {x: r.get(x) for x in ("status", "area_ha", "quay_len_m", "route_min_m", "route_max_m", "straight_min_m", "straight_max_m")})
        if r.get("status") == "ok":
            print("   far", {x: r["far"][x] for x in ("n_junctions", "n_turns", "len_no_width_m", "length_m")}, narrow_txt(r["far"])[0])
    for k, h in haul.items():
        print("haul", k, {x: h[x] for x in ("len_m", "len_page_m", "rel_diff", "min_fixed_w_m", "width_class", "lane_m")})
    for r in crit:
        if r["mode"] == "pull_in":
            print("crit", r["name"], r["v"], r["lane_m"], r["ratio_cut"], r["ratio_zone1"], r["ratio_w"])
    print(OUT)


if __name__ == "__main__":
    main()
