"""E6: a shipyard doubling as a marshalling base - a load-out berth, a monopile storage area and an off-road waiting area
overlaid on the road networks of two yards, Okpo (Hanwha Ocean, Geoje) and Yantai (CIMC Raffles).

The networks are the derived graphs of data/networks/ (no coordinates; see data/networks/README.md): nodes, roads with
their lengths and widths, junctions with the allowed movements and their turn angles, entrances, facilities and zones with
their frontage stretches. Each graph already holds the off-road waiting area of this study: a 30 m stub road `pocket_stub`,
20 m wide, from the junction SITES[site]["near"] to the end node `pocket`, in the direction farthest from the roads at that
junction, with movements between the stub and every other road there (one-way roads only in their direction); idle vehicles
park at the end of the stub, and entering and leaving count as road occupancy.
build() returns the map dict that the simulation reads (windport.sim2.build_map):
  - the classes of the yard's zones and facilities are renamed map_<class> (background only: no longer origins or
    destinations, they do not split roads);
  - a monopile storage area wf_storage is added (pull-in; saddle rows = the frontage stretches of the chosen yard zone, one
    stop per stretch);
  - quay cradles wf_cradle are added (roadside, cradle_mode = "on_road") or pull-in cradle bays wf_cradle_bay ("pull_in"):
    at the chainages of SITES[site]["cradles"], one every 110 m from the gate, n_cradles in total;
  - D["windport"]: kind = "map", site, gate, yard-side waiting area, saddle rows, cradles, ramp (none; E6 covers load-out only).
Site selection (computed on the yard maps, which are not released; the selection is results/tables/sites/sites.json):
  - berth: among the frontage stretches of the quay zones with road width >= the monopile width 9.5 m, the longest one
    whose continuous length fits n_cradles cradle slots of 110 m;
  - storage area: among the stockyard zones with area >= 1.65 ha (about one voyage, 10 piles x 110 m x 15 m) and a route
    to the berth with road width >= 9.5 m throughout, the one with the shortest route (ties broken by length);
  - gate: the end of the quay frontage stretch nearer to the storage area; the waiting area is attached to the junction on
    the storage frontage nearest to the gate."""
import copy
import csv
import hashlib
import json
from pathlib import Path

SC = "org.shipyard.spatial_classification"
RS = "org.shipyard.research_semantics"
ROOT = Path(__file__).resolve().parents[1]
NETWORK = dict(okpo="okpo/rev1833", yantai="yantai/rev396")      # data/networks/<yard>/<revision>
# Selected sites. cradles: cradle slots (road, chainage from the road's from-node in m), one every 110 m from the gate;
# gate: the gate; near: the junction the waiting area is attached to.
SITES = dict(
    okpo=dict(yard="yupu", quay_zone="zone_trace_024", storage_zone="zone_trace_027", gate="node_trace_018", near="node_trace_021",
              cradles=[["road_trace_206", 112.1], ["road_trace_206", 2.1], ["road_trace_019", 54.0], ["road_trace_019", 164.0],
                       ["road_trace_019", 274.0], ["road_trace_019", 384.0], ["road_trace_019", 494.0], ["road_trace_019", 604.0]]),
    yantai=dict(yard="yantai", quay_zone="zone_trace_029", storage_zone="zone_trace_003", gate="node_trace_029", near="node_trace_066",
                cradles=[["road_trace_072", 21.1]]),
)


def load(site):
    """The derived graph of the site's yard as a map dict without geometry: roads carry lengthM, movements turnDeg (degrees
    as the decimal string of the file; occupancy.network.deg_to_rad). Returns (dict, source note)."""
    d = ROOT / "data" / "networks" / NETWORK[site]
    rd = lambda name: list(csv.DictReader(open(d / name, encoding="utf-8", newline="")))
    cls = lambda c: {SC: dict(classId=c)} if c else {}
    D = dict(nodes={}, roads={}, junctions={}, movements={}, accessPoints={}, facilities={}, zones={})
    for r in rd("nodes.csv"):
        D["nodes"][r["node_id"]] = dict(name=r["name"], kind=r["kind"])
    for r in rd("roads.csv"):
        D["roads"][r["road_id"]] = dict(fromNodeId=r["from_node"], toNodeId=r["to_node"], name=r["name"], lengthM=float(r["length_m"]),
                                        widthM=dict(state="known", value=float(r["width_m"])) if r["width_state"] == "known"
                                        else dict(state=r["width_state"]))
    for r in rd("junctions.csv"):
        D["junctions"][r["junction_id"]] = dict(nodeIds=[r["node_id"]])
    for r in rd("movements.csv"):
        D["movements"][r["movement_id"]] = dict(junctionId=r["junction_id"], allowed=r["allowed"] == "true", turnDeg=r["turn_deg"],
                                                incomingArc=dict(roadId=r["in_road"], direction=r["in_dir"]),
                                                outgoingArc=dict(roadId=r["out_road"], direction=r["out_dir"]))
    for r in rd("access_points.csv"):
        D["accessPoints"][r["access_id"]] = dict(name=r["name"], nodeId=r["node_id"], facilityId=r["facility_id"])
    for r in rd("facilities.csv"):
        D["facilities"][r["facility_id"]] = dict(name=r["name"], extensions=cls(r["class"]), accessPointIds=r["access_points"].split())
    for r in rd("zones.csv"):
        D["zones"][r["zone_id"]] = dict(name=r["name"], extensions=dict(cls(r["class"]), **{RS: dict(frontage=[])}))
    for r in rd("frontage.csv"):
        D["zones"][r["zone_id"]]["extensions"][RS]["frontage"].append(dict(roadId=r["road_id"], sStartM=float(r["s_start_m"]),
                                                                           sEndM=float(r["s_end_m"])))
    return D, f"data/networks/{NETWORK[site]}"


def build(site, cradle_mode="on_road", n_cradles=None, S=None):
    """Map dict of the site (S defaults to SITES[site]). Cradle positions: on_road and pull_in use the same chainages."""
    S = S or SITES[site]
    D0, how = load(site)
    D = copy.deepcopy(D0)
    for kind in ("zones", "facilities"):
        for z in D[kind].values():
            ext = z.get("extensions") or {}
            if SC in ext and ext[SC].get("classId"):
                ext[SC]["classId"] = "map_" + ext[SC]["classId"]
    n = len(S["cradles"]) if n_cradles is None else n_cradles
    assert 1 <= n <= len(S["cradles"]), (site, n)
    g = S["gate"]
    runs = [(rid, s - 5.0, s + 5.0) for rid, s in S["cradles"][:n]]
    roads = sorted({rid for rid, _ in S["cradles"]})
    st = D["zones"][S["storage_zone"]]
    fr = [(f["roadId"], f["sStartM"], f["sEndM"]) for f in (st.get("extensions") or {}).get(RS, {}).get("frontage") or []
          if f["roadId"] in D["roads"]]

    def zone(zid, cls, rs, name, mode):
        D["zones"][zid] = dict(name=name, kind="zone", extensions={SC: dict(classId=cls), RS: dict(
            classId=cls, defaultStopMode=mode, frontage=[dict(roadId=r, sStartM=a, sEndM=b) for r, a, b in rs])})
    zone("z_storage", "wf_storage", fr, "monopile storage (derived)", "pull_in")
    zone("z_cradle", "wf_cradle" if cradle_mode == "on_road" else "wf_cradle_bay", runs, "quay cradles (derived)", cradle_mode)
    assert "pocket" in D["nodes"] and S["near"] in (D["roads"]["pocket_stub"]["fromNodeId"], D["roads"]["pocket_stub"]["toNodeId"])
    D["windport"] = dict(kind="map", site=site, params=dict(S, cradle_mode=cradle_mode, n_cradles=n), source=dict(network=how),
                         gates=[g], storage=[f"z_storage#{k}" for k in range(len(fr))], cradles=[f"z_cradle#{k}" for k in range(n)],
                         ramp=[], corridor=[], loop=[], apron=list(roads), pocket="pocket")
    return D


def dumps(D):
    return json.dumps(D, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")


def sha(D):
    return hashlib.sha256(dumps(D)).hexdigest()
