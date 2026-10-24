"""Public road-network survey of real monopile marshalling ports / direct-shipment ports at manufacturing sites (OpenStreetMap,
© OpenStreetMap contributors, ODbL).

Only a few distances are measured, no full road network is mapped: quay line length, shortest along-road distance from the
working area to the quay front (nearest / farthest end), the narrow-section tags OSM gives along the route as they are (width,
lanes, oneway; if absent, recorded as "no OSM width"), and the number of junctions on the route and of junctions with a turn > 45°.

Data access: Overpass API with the standard-library urllib; the User-Agent gives only the project name; requests are spaced, failed
ones retried with back-off, nothing in parallel. Raw JSON is saved together with the query and fetch time; offline, only the saved
JSON is read and recomputed.
"""
import heapq
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = "windport-survey"
COPYRIGHT = "© OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright)"
# roads SPMTs do not use: footways, cycleways, steps, under construction / proposed
NO_DRIVE = {"footway", "path", "cycleway", "steps", "bridleway", "pedestrian", "corridor", "proposed", "construction", "platform", "elevator"}
TURN_DEG = 45.0
R = 6371008.8


def query(bbox):
    s, w, n, e = bbox
    b = f"({s},{w},{n},{e})"
    # water: harbour basins are often drawn as natural=water (or its multipolygon relation), not coastline; for water relations only
    # the member ways inside the bbox are fetched, the relation itself only outputs its member list
    return ("[out:json][timeout:180];("
            f'way["highway"]{b};way["man_made"~"^(quay|pier)$"]{b};way["natural"="coastline"]{b};way["landuse"]{b};relation["landuse"]{b};'
            f'way["industrial"]{b};way["name"]["landuse"!~"."]["highway"!~"."]{b};node["seamark:type"~"berth|mooring"]{b};'
            f'way["natural"="water"]{b};way["waterway"~"^(dock|riverbank)$"]{b};)->.a;'
            f'relation["natural"="water"]{b}->.wr;way(r.wr){b}->.wm;(.a;.wm;)->.b;(.b;.b>;);out body;.wr out body;')


def is_water_edge(D, wid):
    t = D.ways[wid].get("tags", {})
    return (t.get("natural") in ("coastline", "water") or t.get("man_made") == "quay" or t.get("waterway") in ("dock", "riverbank")
            or wid in D.water_members)


def fetch(bbox, retries=4, pause=10.0):
    """Fetch roads, quays and land-use areas inside bbox (south, west, north, east) from Overpass; returns (data, metadata)."""
    q = query(bbox)
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for k in range(retries):
        url = ENDPOINTS[k % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.load(r)
            meta = dict(endpoint=url, query=q, fetched_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        osm_base=d.get("osm3s", {}).get("timestamp_osm_base"), copyright=COPYRIGHT)
            return d, meta
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as ex:
            last = ex
            time.sleep(pause * 2 ** k)
    raise RuntimeError(f"Overpass fetch failed: {last}")


# ---------------------------------------------------------------- geometry
class Data:
    """Saved JSON -> node coordinates (local plane in m, equirectangular projection centred on the bbox centre), ways, relations."""

    def __init__(self, d, bbox):
        lat0, lon0 = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        kx = math.radians(1) * R * math.cos(math.radians(lat0))
        ky = math.radians(1) * R
        self.xy, self.ways, self.rels = {}, {}, {}
        for e in d["elements"]:
            if e["type"] == "node":
                self.xy[e["id"]] = ((e["lon"] - lon0) * kx, (e["lat"] - lat0) * ky)
            elif e["type"] == "way":
                self.ways[e["id"]] = e
            else:
                self.rels[e["id"]] = e
        self.node_tags = {e["id"]: e.get("tags", {}) for e in d["elements"] if e["type"] == "node" and e.get("tags")}
        self.water_members = {m["ref"] for r in self.rels.values() if r.get("tags", {}).get("natural") == "water"
                              for m in r.get("members", []) if m["type"] == "way"}

    def line(self, wid):
        return [self.xy[n] for n in self.ways[wid]["nodes"] if n in self.xy]

    def ring(self, ref):
        """Working-area boundary: ('way', id) is a closed way; ('rel', id) joins the outer members end to end (only the longest
        ring is kept)."""
        kind, i = ref
        if kind == "way":
            return self.line(i)
        segs = [list(self.ways[m["ref"]]["nodes"]) for m in self.rels[i]["members"]
                if m["type"] == "way" and m.get("role", "outer") in ("outer", "") and m["ref"] in self.ways]
        rings = []
        while segs:
            cur = segs.pop(0)
            grown = True
            while grown and cur[0] != cur[-1]:
                grown = False
                for j, s in enumerate(segs):
                    if s[0] == cur[-1]:
                        cur += s[1:]
                    elif s[-1] == cur[-1]:
                        cur += s[::-1][1:]
                    elif s[-1] == cur[0]:
                        cur = s[:-1] + cur
                    elif s[0] == cur[0]:
                        cur = s[::-1][:-1] + cur
                    else:
                        continue
                    segs.pop(j)
                    grown = True
                    break
            rings.append([self.xy[n] for n in cur if n in self.xy])
        return max(rings, key=lambda r: abs(area(r)))


def plen(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def area(r):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r, r[1:] + r[:1])) / 2


def inside(p, r):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def seg_dist(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def poly_dist(p, pts):
    return min(seg_dist(p, a, b) for a, b in zip(pts, pts[1:]))


# ---------------------------------------------------------------- road network
class Graph:
    """Undirected road network: nodes = OSM nodes, edges = adjacent node pairs on a way (one-way roads count as two-way and the
    oneway tag is reported as is - SPMT moves in ports often close the road and drive against the direction, so undirected gives
    the optimistic shortest route)."""

    def __init__(self, xy, ways):
        self.xy, self.adj, self.way_of = xy, {}, {}
        for wid, w in ways.items():
            ns = [n for n in w["nodes"] if n in xy]
            for a, b in zip(ns, ns[1:]):
                if a == b:
                    continue
                d = math.dist(xy[a], xy[b])
                for u, v in ((a, b), (b, a)):
                    old = self.adj.setdefault(u, {}).get(v)
                    if old is None or d < old:
                        self.adj[u][v] = d
                self.way_of.setdefault(frozenset((a, b)), wid)

    @classmethod
    def from_data(cls, D, exclude=NO_DRIVE):
        ways = {i: w for i, w in D.ways.items() if "highway" in w.get("tags", {}) and w["tags"]["highway"] not in exclude
                and w["tags"].get("area") != "yes"}
        return cls(D.xy, ways)

    def dijkstra(self, sources):
        dist, prev = {s: 0.0 for s in sources}, {}
        pq = [(0.0, s) for s in sources]
        heapq.heapify(pq)
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for v, w in self.adj.get(u, {}).items():
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        return dist, prev

    def degree(self, n):
        return len(self.adj.get(n, {}))


def path_of(prev, t):
    p = [t]
    while p[-1] in prev:
        p.append(prev[p[-1]])
    return p                       # t -> source (working area -> quay front)


def heading(G, path, i, step, look=10.0):
    """Direction vector at path[i] going at least look m in direction step (±1) (avoids false turns from short OSM fragments)."""
    x0, y0 = G.xy[path[i]]
    j, acc = i, 0.0
    while 0 <= j + step < len(path) and acc < look:
        acc += math.dist(G.xy[path[j]], G.xy[path[j + step]])
        j += step
    x1, y1 = G.xy[path[j]]
    return x1 - x0, y1 - y0


def turn_angle(G, path, i, look=10.0):
    bx, by = heading(G, path, i, -1, look)        # points back to where we came from
    fx, fy = heading(G, path, i, +1, look)        # points to where we go
    nb, nf = math.hypot(bx, by), math.hypot(fx, fy)
    if nb == 0 or nf == 0:
        return 0.0
    c = max(-1.0, min(1.0, (-bx * fx - by * fy) / (nb * nf)))
    return math.degrees(math.acos(c))              # 0 = straight on


def path_stats(G, ways, path, look=10.0):
    """Number of junctions (intermediate nodes of degree >= 3), number of junctions with a turn > 45°, and the narrow-section tags
    of each way."""
    junc = [i for i in range(1, len(path) - 1) if G.degree(path[i]) >= 3]
    angles = [round(turn_angle(G, path, i, look), 1) for i in junc]
    tags, seen, nowidth = [], {}, 0.0
    for a, b in zip(path, path[1:]):
        wid = G.way_of[frozenset((a, b))]
        L = math.dist(G.xy[a], G.xy[b])
        t = ways[wid].get("tags", {})
        if not any(k in t for k in ("width", "est_width")):
            nowidth += L
        if wid not in seen:
            seen[wid] = len(tags)
            tags.append(dict(way=wid, highway=t.get("highway"), name=t.get("name", ""), width=t.get("width", t.get("est_width", "")),
                             lanes=t.get("lanes", ""), oneway=t.get("oneway", ""), length_m=0.0))
        tags[seen[wid]]["length_m"] += L
    for t in tags:
        t["length_m"] = round(t["length_m"], 1)
    return dict(n_junctions=len(junc), n_turns=sum(a > TURN_DEG for a in angles), junction_angles=angles, ways=tags,
                len_no_width_m=round(nowidth, 1), length_m=round(sum(math.dist(G.xy[a], G.xy[b]) for a, b in zip(path, path[1:])), 1))


def quay_lines(D, rings, buf=25.0, ways=None):
    """Quay line: of the water-edge lines (natural=coastline / water, man_made=quay, waterway=dock / riverbank, member ways of water
    multipolygon relations), the short pieces with both end nodes within buf m of the working-area boundary (or inside it),
    de-duplicated by node pair (length is not counted twice where coastline and water boundary share nodes), each as a two-point
    polyline. If ways is given, only those ways are used (full length)."""
    if ways is not None:
        return [D.line(w) for w in ways]
    ok, segs = {}, set()
    for wid in D.ways:
        if not is_water_edge(D, wid):
            continue
        ns = [n for n in D.ways[wid]["nodes"] if n in D.xy]
        for n in ns:
            if n not in ok:
                p = D.xy[n]
                ok[n] = any(inside(p, r) or poly_dist(p, r + r[:1]) <= buf for r in rings)
        segs |= {frozenset((a, b)) for a, b in zip(ns, ns[1:]) if a != b and ok[a] and ok[b]}
    return [[D.xy[a], D.xy[b]] for a, b in (tuple(s) for s in sorted(segs, key=sorted))]


def survey(D, spec):
    """Measurements for one port. spec: area ([('way'|'rel', id)...], boundary of the working area / yard / plant), quay_ways
    (optional, given quay ways; by default quay_lines picks the shoreline next to the working-area boundary), quay_buf (default
    25 m), front_m (quay-front band width: road nodes within front_m of the quay line are the front, default 30 m),
    exclude_area_front (front nodes inside the working area are not start points, default yes)."""
    G = Graph.from_data(D)
    ways = D.ways
    rings = [D.ring(tuple(r)) for r in spec["area"]]
    quay = quay_lines(D, rings, spec.get("quay_buf", 25.0), spec.get("quay_ways"))
    if not quay:
        return dict(status="no OSM shoreline (coastline / man_made=quay) next to the working-area boundary", area_ha=round(sum(abs(area(r)) for r in rings) / 1e4, 2))
    quay_len = sum(plen(q) for q in quay)
    fm = spec.get("front_m", 30.0)
    nodes = list(G.adj)
    front = {n for n in nodes if min(poly_dist(G.xy[n], q) for q in quay) <= fm}
    area_nodes = [n for n in nodes if any(inside(G.xy[n], r) for r in rings)]
    if spec.get("start_name"):           # start points are the plant access road instead (by OSM road name; for ports whose plant has no separate boundary in OSM)
        sn = {n for wid, w in ways.items() if w.get("tags", {}).get("name") == spec["start_name"] for n in w["nodes"] if n in G.adj}
        area_nodes = [n for n in area_nodes if n in sn]
    out = dict(quay_len_m=round(quay_len, 1), n_front=len(front), n_area_nodes=len(area_nodes),
               area_ha=round(sum(abs(area(r)) for r in rings) / 1e4, 2))
    # straight-line distance from the working area to the quay line (reference where there are no roads inside; working-area vertices to quay line)
    verts = [p for r in rings for p in r]
    out["straight_min_m"] = round(min(min(poly_dist(p, q) for q in quay) for p in verts), 1)
    out["straight_max_m"] = round(max(min(poly_dist(p, q) for q in quay) for p in verts), 1)
    if not front or not area_nodes:
        out.update(status="OSM road network does not reach the quay front, or no roads inside the working area")
        return out
    dist, prev = G.dijkstra(front)
    starts = [n for n in area_nodes if n in dist and (n not in front or not spec.get("exclude_area_front", True))]
    if not starts:
        out.update(status="all road nodes inside the working area lie in the quay-front band or are not connected to the front")
        return out
    near = min(starts, key=lambda n: dist[n])
    far = max(starts, key=lambda n: dist[n])
    out.update(status="ok", route_min_m=round(dist[near], 1), route_max_m=round(dist[far], 1),
               near_node=near, far_node=far, unreached=sum(n not in dist for n in area_nodes))
    out["far"] = path_stats(G, ways, path_of(prev, far))
    out["near"] = path_stats(G, ways, path_of(prev, near))
    return out
