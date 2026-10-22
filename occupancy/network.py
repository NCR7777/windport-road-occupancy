"""Shipyard road networks: topology, centre-line lengths, turn permissions, stops of origins and destinations, exclusive
resources and the resources one trip occupies.

A network is read from a map JSON with geometry (checked by SHA-256, read_input): nodes with positions, roads between two
nodes with a centre line (anchors and line or cubic spans) and a width, junctions with their movements, entrances
(accessPoints) of buildings (facilities), and zones with an outline. Road lengths are centre-line lengths (polyline), turn
angles come from the headings of the roads at the junction (heading), and the frontage of a dock is derived from the dock
outline (Net._dock_frontage); the other frontage stretches, the cranes and the crane spans are read from the research
attributes of the map. The synthetic port layouts (windport.archetypes) are maps of this kind.
A map may also come from a derived graph without geometry (the two shipyards, windport.shipyard.load reading
data/networks/): its roads carry their length (lengthM) and its movements their turn angle (turnDeg, degrees as a decimal
string); Net then takes the lengths as stored and Net.turn the angle of the movement, and both equal, to the last bit, what
the map with geometry gives (checked when the graphs were derived).

Resources (keys are tuples):
  ('r', road)      every map road; capacity = width W + c (a width container: each vehicle takes its outer width + c). With
                   sectioning (p["section"]) a long road is cut into sections, one resource each, named <road>@<k>
                   (Net._section);
  ('n', node)      junctions of degree >= 3 and all entrance nodes; capacity = junction size D + c, D = widest adjacent road
                   with a known width;
  ('b', zone, k)   drive-in bays, one vehicle each; dock-side off-road bays and in-door bays (road changes) have capacity =
                   number of places, each vehicle takes 1;
  ('w', zone, k)   dock-side waiting places (road change dock_wait), capacity = number of places, each vehicle takes 1.
A loaded vehicle holds a junction alone; on a road vehicles share by width: two can be on one road iff the sum of their outer
widths + c <= W.
Road changes (p["retrofit"] = [change, ...], applied in order and combinable; without them the network is unchanged):
  widen     {"kind": "widen", "roads": [road], "add": m or "to": m}: add m to the width, or raise it to at least m (known
            widths only; the size of the end junctions follows the junction rule of the map);
  entrance  {"kind": "entrance", "facility": f, "n": 1}: n more entrances for a building, copies of its first entrance (a new
            entrance node at the same place, an access road of the same shape to the same junction, the same movements);
  dock_bay  {"kind": "dock_bay", "cap": c[, "docks": [zone]]}: dock-side off-road bays of capacity c: the roadside stop of a
            dock becomes a drive-in bay beside the dock where vehicles unload and wait for the crane, so the dock road is held
            only while passing. Without crane resources the c places are c parallel unloading places; with cranes, unloading
            (hooking) is limited by the number of cranes and extra places can only wait. All docks if no list is given;
  dock_wait {"kind": "dock_wait", "cap": c[, "docks": [zone]]}: dock-side waiting places: the roadside stop stays on the road,
            one vehicle unloads at a time, and c off-road places beside it let reservation rules wait there until the stop
            (and the crane) is free (Sim._book_dest); occupancy without waiting is unchanged, and so are the bounds. Stepwise
            rules do not use the waiting places (they wait on the road as before);
  passing   {"kind": "passing", "road": r[, "len": 40, "w": width, "at": chainage]}: a passing place on a long single-lane
            road (length len, width w, by default the equivalent width of a road without width limit); centred at `at`,
            or at the middle of the longest stretch between the stops and the ends of the road; its ends are section
            boundaries (as with sectioning);
  blocks    {"kind": "blocks", "road": r, "len": m}: cut the whole road into blocks of length <= m (forced boundaries, width
            unchanged; no boundary within 1 m of a stop), to refine a binding road itself;
  door      {"kind": "door", "facilities": [f]}: door granularity: a door (entrance node) is held only while a vehicle passes,
            (D + vehicle length + longitudinal clearance)/v; loading and unloading take place at an in-door bay (one per
            building, capacity = number of doors); the access roads in front of the doors are shared by width as before.
"""
import collections
import copy
import hashlib
import heapq
import json
import math
import subprocess
from decimal import Decimal, localcontext

from .params import DOCK_CLASS, FLOW, STOP_MODE

SC = "org.shipyard.spatial_classification"
RS = "org.shipyard.research_semantics"
EPS = 1e-6
MAP_KINDS = ("widen", "entrance")          # road changes of the map itself (retrofit_map); others: Net._retrofit, Net._section
PI = Decimal("3.14159265358979323846264338327950288419716939937510")


def deg_to_rad(s):
    """Turn angle of a derived graph (degrees, decimal string with 25 significant digits) -> radians, exactly the float the
    angle had when it was computed from the map geometry."""
    with localcontext() as c:
        c.prec = 50
        return float(Decimal(s) * PI / 180)


def retrofit_map(D, specs):
    """Road changes on the map itself (widen, entrance; see the module docstring): returns a changed deep copy, or D itself
    when there are none of these two kinds."""
    if not any(s["kind"] in MAP_KINDS for s in specs):
        return D
    D = copy.deepcopy(D)
    for s in specs:
        if s["kind"] == "widen":
            for rid in s["roads"]:
                w = D["roads"][rid]["widthM"]
                if w["state"] == "known":
                    w["value"] = w["value"] + s["add"] if "add" in s else max(w["value"], s["to"])
        elif s["kind"] == "entrance":
            f = D["facilities"][s["facility"]]
            ap0 = f["accessPointIds"][0]
            n0 = D["accessPoints"][ap0]["nodeId"]
            (rid0, r0), = [(k, r) for k, r in D["roads"].items() if n0 in (r["fromNodeId"], r["toNodeId"])]
            js = [jid for jid, j in D["junctions"].items() if n0 in j["nodeIds"]]
            for k in range(1, s.get("n", 1) + 1):
                tag = f"~{k}"
                n1, rid1, ap1 = n0 + tag, rid0 + tag, ap0 + tag
                D["nodes"][n1] = copy.deepcopy(D["nodes"][n0])
                D["roads"][rid1] = dict(copy.deepcopy(r0), **{e: n1 for e in ("fromNodeId", "toNodeId") if r0[e] == n0})
                D["accessPoints"][ap1] = dict(copy.deepcopy(D["accessPoints"][ap0]), nodeId=n1)
                f["accessPointIds"].append(ap1)
                for jid in js:
                    D["junctions"][jid + tag] = dict(copy.deepcopy(D["junctions"][jid]), nodeIds=[n1])
                for mid, m in list(D["movements"].items()):
                    if rid0 in (m["incomingArc"]["roadId"], m["outgoingArc"]["roadId"]):
                        m1 = copy.deepcopy(m)
                        for a in (m1["incomingArc"], m1["outgoingArc"]):
                            if a["roadId"] == rid0:
                                a["roadId"] = rid1
                        if m["junctionId"] in js:
                            m1["junctionId"] += tag
                        D["movements"][mid + tag] = m1
    return D


def polyline(D, r):
    """Centre line of a road from the map geometry (end node positions, anchors, line or cubic spans); cubic spans flattened
    at about 0.5 m (the same flattening as for the frontage chainages recorded in the map, so that chainages s agree)."""
    P = lambda n: tuple(D["nodes"][n]["position"][:2])
    pts = [P(r["fromNodeId"])] + [tuple(a[:2]) for a in r["geometry"]["anchors"]] + [P(r["toNodeId"])]
    out = [pts[0]]
    for i, sp in enumerate(r["geometry"]["spans"]):
        a, b = pts[i], pts[i + 1]
        if sp["kind"] == "line":
            out.append(b)
            continue
        c1, c2 = sp["control1"][:2], sp["control2"][:2]
        n = max(8, int(math.dist(a, b) / 0.5) + 1)
        for k in range(1, n + 1):
            t = k / n
            u = 1 - t
            out.append(tuple(u ** 3 * a[j] + 3 * u * u * t * c1[j] + 3 * u * t * t * c2[j] + t ** 3 * b[j] for j in (0, 1)))
    return out


def samples(poly, step):
    """A point every `step` metres along a polyline [(s, x, y)]; the end point is always included."""
    out, s = [(0.0, *poly[0])], 0.0
    nxt = step
    for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
        L = math.hypot(x2 - x1, y2 - y1)
        while L > 0 and nxt <= s + L:
            f = (nxt - s) / L
            out.append((nxt, x1 + f * (x2 - x1), y1 + f * (y2 - y1)))
            nxt += step
        s += L
    if out[-1][0] < s - EPS:
        out.append((s, *poly[-1]))
    return out


def heading(poly, at_end, look=3.0):
    """Heading (rad) of a road at one end, in the from → to direction (towards the first polyline point at least `look` m
    from the end)."""
    pts = poly[::-1] if at_end else poly
    p0 = pts[0]
    for q in pts[1:]:
        if math.dist(p0, q) >= look:
            break
    a = math.atan2(q[1] - p0[1], q[0] - p0[0])
    return a + math.pi if at_end else a


def poly_dist(p, poly):
    """Distance from a point to a polygon, 0 inside."""
    x, y = p
    inside, best = False, float("inf")
    for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        best = min(best, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return 0.0 if inside else best


def read_input(path, sha, git=None):
    """Reads an input file by path and checks its SHA-256. If the working-tree file has changed (hash mismatch) and
    git = {repo, commit, path} is given, the same path is read from that commit instead (read only) and checked against the
    same SHA-256; stops if both fail. Returns (bytes, source note)."""
    raw = open(path, "rb").read()
    if hashlib.sha256(raw).hexdigest() == sha:
        return raw, "worktree"
    if git:
        raw = subprocess.run(["git", "-C", git["repo"], "show", f"{git['commit']}:{git['path']}"], capture_output=True, check=True).stdout
        if hashlib.sha256(raw).hexdigest() == sha:
            return raw, f"git {git['commit'][:7]}"
    raise RuntimeError(f"input SHA-256 mismatch: {path} ({hashlib.sha256(open(path, 'rb').read()).hexdigest()})")


class Net:
    def __init__(self, map_path, map_sha256, p, roles=None, git=None):
        """roles = {role in FLOW: class in the map}: entities of that class take part in the flows in that role (for instance
        a steel processing shop as the assembly workshop). git: the commit that holds the registered version (read_input);
        read from there when the working-tree file has changed."""
        raw, self.source = read_input(map_path, map_sha256, git)
        self.retro = p.get("retrofit") or []
        D = retrofit_map(json.loads(raw.decode("utf-8")), self.retro)
        self.D = D
        self.role_of = {c: r for r, c in (roles or {}).items()}
        self.road = {}
        for rid, r in D["roads"].items():
            if "lengthM" in r:            # derived graph: stored length; turn angles per movement (Net.turn)
                poly, L, h0, h1 = None, r["lengthM"], None, None
            else:
                poly = polyline(D, r)
                L = sum(math.dist(a, b) for a, b in zip(poly, poly[1:]))
                h0, h1 = heading(poly, False), heading(poly, True)
            w = r["widthM"]
            # orig, s0, s1: the map road this one belongs to and its chainage on it (without sectioning: itself and [0, L])
            self.road[rid] = dict(a=r["fromNodeId"], b=r["toNodeId"], L=L, poly=poly, name=r["name"],
                                  W=float(w["value"]) if w["state"] == "known" else None,
                                  h0=h0, h1=h1, orig=rid, s0=0.0, s1=L)
        deg = collections.Counter(x for r in self.road.values() for x in (r["a"], r["b"]))
        self.access = {a["nodeId"] for a in D["accessPoints"].values()}
        self.node_res = {n for n in D["nodes"] if deg[n] >= 3 or n in self.access}
        self.incident = collections.defaultdict(list)
        for rid, r in self.road.items():
            self.incident[r["a"]].append(rid)
            self.incident[r["b"]].append(rid)
        self._stops(D, p)
        self._retrofit()
        self._section(p)
        self._graph(D)
        self._trees = {}

    def _retrofit(self):
        """Road changes of the stops (dock_bay, dock_wait, door; see the module docstring). bay_cap = {off-road bay / in-door
        bay / waiting place: number of places}; dock_bays = dock-side off-road bays; wait_at = {dock stop node: waiting place};
        doors = door nodes."""
        self.bay_cap, self.dock_bays, self.doors, self.wait_at = {}, set(), set(), {}
        for s in self.retro:
            if s["kind"] == "dock_wait":
                for z in s.get("docks") or self.by_cls[DOCK_CLASS]:
                    for k, sid in enumerate(self.ents[z]["stops"]):
                        if self.stops[sid]["mode"] == "on_road":
                            self.wait_at[self.stops[sid]["node"]] = ("w", z, k)
                            self.bay_cap[("w", z, k)] = float(s["cap"])
            elif s["kind"] == "dock_bay":
                for z in s.get("docks") or self.by_cls[DOCK_CLASS]:
                    for k, sid in enumerate(self.ents[z]["stops"]):
                        st = self.stops[sid]
                        if st["mode"] == "on_road":
                            st.update(mode="pull_in", res=("b", z, k), bay=True)
                            self.bay_cap[st["res"]] = float(s["cap"])
                            self.dock_bays.add(st["res"])
            elif s["kind"] == "door":
                for f in s["facilities"]:
                    res = ("b", f, "in")
                    for sid in self.ents[f]["stops"]:
                        assert self.stops[sid]["mode"] == "node", sid
                        self.stops[sid].update(mode="door", res=res)
                        self.doors.add(self.stops[sid]["node"])
                    self.bay_cap[res] = float(len(self.ents[f]["stops"]))

    # ---------------------------------------------------------------- entities of origins and destinations, and their stops
    def _stops(self, D, p):
        """stops[id] = dict(node, res, mode, ent); ents[entity] = dict(cls, stops)."""
        classes = {c for f in FLOW for x in f[1:3] for c in x.split("|")}
        self.ents, self.stops = {}, {}
        cuts = collections.defaultdict(set)
        for fid, f in D["facilities"].items():
            mc = (f.get("extensions") or {}).get(SC, {}).get("classId")
            c = self.role_of.get(mc, mc)
            nodes = [D["accessPoints"][a]["nodeId"] for a in f.get("accessPointIds", []) if a in D["accessPoints"]]
            if c in classes and nodes:
                ids = []
                for n in nodes:
                    self.stops[n] = dict(node=n, res=("n", n), mode="node", ent=fid)
                    ids.append(n)
                self.ents[fid] = dict(cls=c, map_cls=mc, stops=ids, name=f["name"])
        for zid, z in D["zones"].items():
            mc = (z.get("extensions") or {}).get(SC, {}).get("classId")
            c = self.role_of.get(mc, mc)
            if c not in classes:
                continue
            fr = self._dock_frontage(z, p) if c == "dry_dock" else \
                [(x["roadId"], x["sStartM"], x["sEndM"]) for x in (z.get("extensions") or {}).get(RS, {}).get("frontage") or []]
            mode = STOP_MODE[c]
            ids = []
            for k, (rid, s0, s1) in enumerate(fr):
                L = self.road[rid]["L"]
                s = round(min(max((s0 + s1) / 2, min(1.0, L / 2)), max(L - 1.0, L / 2)), 1)
                node = f"S|{rid}|{s}"
                cuts[rid].add(s)
                sid = f"{zid}#{k}"
                self.stops[sid] = dict(node=node, res=("r", rid) if mode == "on_road" else ("b", zid, k), mode=mode, ent=zid)
                ids.append(sid)
            if ids:
                self.ents[zid] = dict(cls=c, map_cls=mc, stops=ids, name=z["name"])
        self.cuts = {rid: sorted(v) for rid, v in cuts.items()}
        self.by_cls = collections.defaultdict(list)
        for e, v in sorted(self.ents.items()):
            self.by_cls[v["cls"]].append(e)

    def _dock_frontage(self, z, p):
        """Frontage of a dock, from the map geometry: the continuous stretches of road whose centre line lies within half the
        road width + frontage_gap of the dock outline (gaps <= frontage_merge closed, stretches shorter than frontage_min_len
        dropped); roads attached to entrance nodes (access roads) are excluded.
        One roadside stop at the middle of each stretch; p["dock_stops"] = n keeps only the n longest (ties by road id and
        chainage), in their order."""
        out = self._frontage_runs(z, p)
        n = p.get("dock_stops")
        if n is not None:
            keep = set(sorted(out, key=lambda x: (-(x[2] - x[1]), x[0], x[1]))[:n])
            out = [x for x in out if x in keep]
        return out

    def _frontage_runs(self, z, p):
        poly = [tuple(q[:2]) for q in z["boundary"]["outer"]]
        out = []
        for rid, r in sorted(self.road.items()):
            if r["a"] in self.access or r["b"] in self.access:
                continue
            lim = (r["W"] if r["W"] is not None else 12.0) / 2 + p["frontage_gap"]
            hits = [s for s, x, y in samples(r["poly"], 1.0) if poly_dist((x, y), poly) <= lim]
            runs = []
            for s in hits:
                if runs and s - runs[-1][1] <= p["frontage_merge"]:
                    runs[-1][1] = s
                else:
                    runs.append([s, s])
            out += [(rid, s0, s1) for s0, s1 in runs if s1 - s0 >= p["frontage_min_len"]]
        return out

    def near(self, cls):
        """Resources around the zones of class cls, [ring 0, ring 1] (disjoint). Ring 0 = the stop resources of its entities
        (for roadside stops the whole road, or with sectioning the section of the stop); ring 1 = the junctions at both ends of
        the map road of each stop (or the entrance node), the roads at these ends, and the map road of the stop itself (its
        sections when sectioned; if not in ring 0)."""
        ring0 = {self.stops[s]["res"] for e in self.by_cls[cls] for s in self.ents[e]["stops"]}
        roads, ends = set(), set()
        for e in self.by_cls[cls]:
            for s in self.ents[e]["stops"]:
                n = self.stops[s]["node"]
                if n.startswith("S|"):
                    secs = self.sec.get(n.split("|")[1], [n.split("|")[1]])
                    roads |= set(secs)
                    ends |= {self.road[secs[0]]["a"], self.road[secs[-1]]["b"]}
                else:
                    ends.add(n)
        ring1 = {("n", x) for x in ends if x in self.node_res} | {("r", r) for x in ends for r in self.incident[x]} \
            | {("r", r) for r in roads}
        return [ring0, ring1 - ring0]

    # ---------------------------------------------------------------- sectioning
    def _section(self, p, min_gap=1.0):
        """p["section"] = "stops": a road longer than section_min_m with roadside stops (on_road) gets section boundaries
        section_gap_m before and after each stop on it (roadside stops and drive-in points) and is cut into sections, one
        resource each (same width); with block_m each section is further cut into blocks of length <= block_m.
        No boundary within min_gap of a stop, a road end or another boundary (no slivers, no stop on a boundary).
        Sections are named <road>@<k> (names get @k); boundaries are new cut points S|<road>|<chainage> (named by the chainage
        on the map road, like stops) that can only be passed straight on; a roadside stop's resource becomes its section.
        sec = {map road: [sections]}, edges = {map road: [boundary chainages]}; both empty without sectioning.
        Stops of dock-side bays (dock_bay) still set boundaries; the ends of a passing place (passing) are forced boundaries
        (also without sectioning), with the width of the passing place."""
        self.sec, self.edges = {}, {}
        force, wide = self._passing(p, min_gap)
        if not p.get("section") and not force:
            return
        if p.get("section") not in (None, "stops"):
            raise ValueError(f"unknown sectioning: {p['section']}")
        on_road = {st["res"][1] for st in self.stops.values() if st["mode"] == "on_road"} | \
            {st["node"].split("|")[1] for st in self.stops.values() if st.get("bay")} if p.get("section") else set()
        gap, B = p["section_gap_m"], p.get("block_m")
        for rid in sorted(on_road | set(force)):
            r = self.road[rid]
            L, cuts = r["L"], self.cuts.get(rid, [])
            edges = list(force.get(rid, []))

            def add(e):
                if min_gap < e < L - min_gap and all(abs(e - x) > min_gap for x in cuts + edges):
                    edges.append(e)
            if rid in on_road and L > p["section_min_m"]:
                for s in cuts:
                    add(round(s - gap, 1))
                    add(round(s + gap, 1))
                if B:
                    pts = [0.0] + sorted(edges) + [L]
                    for a, b in zip(pts, pts[1:]):
                        n = math.ceil((b - a) / B - EPS)
                        for j in range(1, n):
                            add(round(a + j * (b - a) / n, 1))
            if not edges:
                continue
            pts = [0.0] + sorted(edges) + [L]
            node_at = lambda x: r["a"] if x == 0.0 else (r["b"] if x == L else f"S|{rid}|{x}")
            secs = []
            for k, (a, b) in enumerate(zip(pts, pts[1:])):
                sid = f"{rid}@{k}"
                self.road[sid] = dict(r, a=node_at(a), b=node_at(b), L=b - a, s0=a, s1=b, name=f"{r['name']}@{k}",
                                      **{"W": w for wa, wb, w in wide.get(rid, ()) if wa - EPS <= a and b <= wb + EPS})
                secs.append(sid)
            del self.road[rid]
            self.sec[rid], self.edges[rid] = secs, pts[1:-1]
            for end, s in ((r["a"], secs[0]), (r["b"], secs[-1])):
                self.incident[end] = [s if x == rid else x for x in self.incident[end]]
            for st in self.stops.values():
                if st["res"] == ("r", rid):
                    at = float(st["node"].split("|")[2])
                    st["res"] = ("r", next(s for s in secs if self.road[s]["s0"] < at < self.road[s]["s1"]))

    def _passing(self, p, min_gap):
        """Passing places and blocks (road changes): {road: [chainages of the forced boundaries]} and {road: [(start, end,
        width)]}. A passing place sits at the middle of the longest stretch between the stops and the ends of the road (the
        middle of a long single-lane road), length len (default 40 m: the longest loaded vehicle, 30 m, plus the longitudinal
        clearance of 5 m, with room to spare), width w (default the equivalent width without width limit, where two loaded
        vehicles pass)."""
        force, wide = {}, {}
        for s in self.retro:
            if s["kind"] not in ("passing", "blocks"):
                continue
            rid = s["road"]
            L = self.road[rid]["L"]
            cuts = self.cuts.get(rid, [])
            if s["kind"] == "blocks":     # the whole road in blocks of length <= len; no boundary within min_gap of a stop
                n = math.ceil(L / s["len"] - EPS)
                e = [round(j * L / n, 1) for j in range(1, n)]
                force.setdefault(rid, []).extend(x for x in e if all(abs(x - c) > min_gap for c in cuts))
                continue
            ln = s.get("len", 40.0)
            if "at" in s:
                a = b = s["at"]
            else:
                pts = [0.0] + cuts + [L]
                a, b = max(zip(pts, pts[1:]), key=lambda x: x[1] - x[0])
            e = [round((a + b - ln) / 2, 1), round((a + b + ln) / 2, 1)]
            assert min_gap < e[0] and e[1] < L - min_gap and all(not (e[0] - min_gap <= x <= e[1] + min_gap) for x in cuts), (rid, e)
            force.setdefault(rid, []).extend(e)
            wide.setdefault(rid, []).append((e[0], e[1], s.get("w", p["unrestricted_w"])))
        return force, wide

    def runs(self, src, dst):
        """The parts of a trip merged by (road, direction), one per decision point of leg: part k is entered at decision point
        k (used by the direction lock)."""
        out = []
        for a in (self.path(src, dst) if src != dst else []):
            x = (self.arc[a][3], self.arc[a][4])
            if not out or out[-1] != x:
                out.append(x)
        return out

    # ---------------------------------------------------------------- directed arcs (roads cut at stops and boundaries)
    def _graph(self, D):
        self.arc = []        # (tail, head, length, road, forward)
        for rid, r in sorted(self.road.items()):
            o = r["orig"]
            if o == rid:                  # road not sectioned
                marks, pts = self.cuts.get(rid, []), [0.0] + self.cuts.get(rid, []) + [r["L"]]
            else:                         # section: the stops inside it
                marks = [c for c in self.cuts.get(o, []) if r["s0"] < c < r["s1"]]
                pts = [r["s0"]] + marks + [r["s1"]]
            nodes = [r["a"]] + [f"S|{o}|{s}" for s in marks] + [r["b"]]
            for i in range(len(pts) - 1):
                self.arc.append((nodes[i], nodes[i + 1], pts[i + 1] - pts[i], rid, True))
                self.arc.append((nodes[i + 1], nodes[i], pts[i + 1] - pts[i], rid, False))
        self.out = collections.defaultdict(list)
        for i, a in enumerate(self.arc):
            self.out[a[0]].append(i)
        allowed = collections.defaultdict(set)
        jn = {jid: j["nodeIds"][0] for jid, j in D["junctions"].items()}
        # derived graph: turn angle (rad) of each movement, by (node, in road, forward, out road, forward)
        self.turn_at = {(jn[m["junctionId"]], m["incomingArc"]["roadId"], m["incomingArc"]["direction"] == "forward",
                         m["outgoingArc"]["roadId"], m["outgoingArc"]["direction"] == "forward"): deg_to_rad(m["turnDeg"])
                        for m in D["movements"].values() if "turnDeg" in m}
        for m in D["movements"].values():
            if m["allowed"]:
                ia, oa = m["incomingArc"], m["outgoingArc"]
                allowed[jn[m["junctionId"]]].add(((ia["roadId"], ia["direction"] == "forward"),
                                                  (oa["roadId"], oa["direction"] == "forward")))
        orig = {rid: r["orig"] for rid, r in self.road.items()}       # turn permissions refer to map roads
        self.succ = []
        for t, h, _, rid, fw in self.arc:
            if h.startswith("S|"):        # stops and section boundaries: only straight on along the same map road
                self.succ.append([j for j in self.out[h] if orig[self.arc[j][3]] == orig[rid] and self.arc[j][4] == fw])
            else:
                self.succ.append([j for j in self.out[h] if ((orig[rid], fw), (orig[self.arc[j][3]], self.arc[j][4])) in allowed[h]])

    def tree(self, src):
        """Shortest paths (by distance) from src that respect the turn permissions: best[node] = (distance, arriving arc),
        pred[arc] = previous arc."""
        if src in self._trees:
            return self._trees[src]
        dist, pred = {}, {}
        heap = [(self.arc[a][2], a, -1) for a in self.out[src]]
        heapq.heapify(heap)
        while heap:
            d, a, p = heapq.heappop(heap)
            if a in dist:
                continue
            dist[a], pred[a] = d, p
            for b in self.succ[a]:
                if b not in dist:
                    heapq.heappush(heap, (d + self.arc[b][2], b, a))
        best = {src: (0.0, -1)}
        for a, d in dist.items():
            h = self.arc[a][1]
            if d < best.get(h, (math.inf,))[0]:
                best[h] = (d, a)
        self._trees[src] = (best, pred)
        return best, pred

    def dist(self, src, dst):
        return self.tree(src)[0].get(dst, (math.inf,))[0]

    def path(self, src, dst):
        best, pred = self.tree(src)
        if dst not in best:
            raise RuntimeError(f"unreachable: {src} -> {dst}")
        out, a = [], best[dst][1]
        while a != -1:
            out.append(a)
            a = pred[a]
        return out[::-1]

    # ---------------------------------------------------------------- capacities and occupancy
    def capacities(self, p):
        """cap[resource] and size[node resource] (junction size D)."""
        c = p["lat_clear"]
        W = {rid: (r["W"] + p["width_delta"]) if r["W"] is not None else p["unrestricted_w"] for rid, r in self.road.items()}
        cap = {("r", rid): w + c for rid, w in W.items()}
        size = {}
        for n in self.node_res:
            known = [W[rid] for rid in self.incident[n] if self.road[rid]["W"] is not None]
            size[n] = max(known) if known else p["unrestricted_w"]
            cap[("n", n)] = size[n] + c
        for s in self.stops.values():
            if s["res"][0] == "b":
                cap[s["res"]] = self.bay_cap.get(s["res"], 1.0)
        for w in self.wait_at.values():
            cap[w] = self.bay_cap[w]
        if p.get("crane_n"):          # crane-paced erection: resource ('c', dock) per dock, capacity = number of cranes
            for z, n in self.crane_counts(p).items():
                cap[("c", z)] = float(n)
        return cap, size

    def crane_counts(self, p):
        """Cranes per dock: p["crane_n"] = "map" counts the cranes in the crane list of the dock in the map that have
        countsForErection set; an integer (the same for every dock) or {dock: number} gives them directly (scenarios with
        other crane numbers, such as the ρ curves)."""
        n = p["crane_n"]
        if n == "map":
            return {z: sum(c["count"] for c in self.D["zones"][z]["extensions"][RS].get("cranes", []) if c["countsForErection"])
                    for z in self.by_cls[DOCK_CLASS]}
        return {z: (n[z] if isinstance(n, dict) else n) for z in self.by_cls[DOCK_CLASS]}

    def spans(self):
        """Gantry crane spans (zones with research_semantics.role = gantry_crane_span in the map): {span zone: (dock, polygon,
        {assembly area: share covered})}. The share is the map's coversZones (share of the area's surface inside the span)."""
        out = {}
        for zid, z in self.D["zones"].items():
            r = (z.get("extensions") or {}).get(RS, {})
            if r.get("role") == "gantry_crane_span":
                out[zid] = (r["dockZoneId"], [tuple(q[:2]) for q in z["boundary"]["outer"]], r["coversZones"])
        return out

    def lift_pairs(self, p):
        """P6 (assembly area, dock) pairs inside a crane span: the span of the dock covers at least p["span_min"] of the area,
        so the gantry crane lifts the block directly and no road is used. span_min None (or a scenario without crane-paced
        erection): all pairs are outside the span (no lifts)."""
        m = p.get("span_min") if p.get("crane_n") else None
        if m is None:
            return set()
        return {(e, dock) for dock, _, cov in self.spans().values() for e, f in cov.items() if f >= m}

    @staticmethod
    def demand(res, b, loaded, p, cap):
        """The "width" a vehicle takes on a resource. A loaded vehicle holds a junction alone; a bay takes one place per vehicle
        (a drive-in bay has one place, so it is held alone); an empty vehicle follows empty_rule."""
        C = cap[res]
        if res[0] == "b":
            return 1.0
        if not loaded:
            if p["empty_rule"] == "free":
                return 0.0
            if p["empty_rule"] == "exclusive":
                return C
        elif res[0] == "n":
            return C
        return min(C, b + p["lat_clear"])

    def turn(self, a, b):
        """Turn angle (rad) entering by arc a and leaving by arc b, from the headings of the two roads (derived graph: the
        stored angle of the movement at the node between them)."""
        _, h, _, ra, fa = self.arc[a]
        _, _, _, rb, fb = self.arc[b]
        if self.road[ra]["h0"] is None:
            key = (h, self.road[ra]["orig"], fa, self.road[rb]["orig"], fb)
            if key not in self.turn_at:      # straight on at a stop or section boundary: needs the road's geometry
                raise NotImplementedError(f"no turn angle at {h} in a derived graph (sectioned roads need the map)")
            return self.turn_at[key]
        hin = self.road[ra]["h1"] if fa else self.road[ra]["h0"] + math.pi
        hout = self.road[rb]["h0"] if fb else self.road[rb]["h1"] + math.pi
        d = (hout - hin) % (2 * math.pi)
        return min(d, 2 * math.pi - d)

    def leg(self, src, dst, v, Lv, b, loaded, p, cap, size, end_res, end_d, start_node=False):
        """Resources occupied by one trip (src → dst, without waiting).
        Returns (T, st, uses, arr): T travel time; st[k] time of decision point k (from departure); arr index of the arrival;
        uses = [(resource, width taken, acquired at decision point, released at decision point or None, release delay)], None
        meaning released by the task logic (the destination stop).
        Decision points: 0 = departure, k = entering part k, arr = arrival. A road is held until the vehicle's tail has left
        the next junction plus the longitudinal clearance; a junction for (D + vehicle length + longitudinal clearance)/v plus
        the turn sweep; the destination stop is requested together with the last road (no access road is held without it).
        Doors (door): requested at decision point 0 when leaving a door and at arr when arriving at one, released after
        (D + vehicle length + longitudinal clearance)/v.
        Dock-side off-road bays (dock_bay): the last road is released at entry + its travel time + the tail clearance, so a
        vehicle waiting for the crane in the bay no longer holds it.
        Dock-side waiting places (dock_wait): the last road is released as usual at arrival + tail clearance, and the roadside
        stop is acquired at decision point arr (start of unloading); without waiting their union is unchanged, and reservation
        rules can insert a wait in the waiting place between the two (Sim._book_dest)."""
        tail = (Lv + p["long_clear"]) / v
        if src == dst:
            return 0.0, [0.0], [(end_res, end_d, 0, None, 0.0)], 0
        door = lambda n: (("n", n), self.demand(("n", n), b, loaded, p, cap), (size[n] + Lv + p["long_clear"]) / v)
        arcs = self.path(src, dst)
        runs = []                         # [road, chainage at entry, first arc, last arc]
        D = 0.0
        for a in arcs:
            t, h, L, rid, fw = self.arc[a]
            if runs and runs[-1][0] == rid and self.arc[runs[-1][3]][4] == fw:
                runs[-1][3] = a
            else:
                runs.append([rid, D, a, a])
            D += L
        m = len(runs) - 1
        st = [r[1] / v for r in runs] + [D / v]
        uses = []
        if src in self.doors:
            r_, d_, dl = door(src)
            uses.append((r_, d_, 0, 0, dl))
        elif start_node and ("n", src) in cap:
            uses.append((("n", src), self.demand(("n", src), b, loaded, p, cap), 0, 0, tail))
        for i, (rid, _, a0, a1) in enumerate(runs):
            res = ("r", rid)
            if i > 0:
                n = self.arc[a0][0]
                if n in self.node_res:
                    sweep = p["turn_sweep_s"] if math.degrees(self.turn(runs[i - 1][3], a0)) >= p["turn_deg"] else 0.0
                    uses.append((("n", n), self.demand(("n", n), b, loaded, p, cap), i, i, (size[n] + Lv + p["long_clear"]) / v + sweep))
            if i == m and res == end_res and dst in self.wait_at:     # roadside stop + waiting place: stop taken at unloading
                uses.append((res, self.demand(res, b, loaded, p, cap), i, i + 1, tail))
                uses.append((end_res, max(end_d, self.demand(res, b, loaded, p, cap)), m + 1, None, 0.0))
            elif i == m and res == end_res:          # roadside stop: this road is the stop resource
                uses.append((res, max(end_d, self.demand(res, b, loaded, p, cap)), i, None, 0.0))
            elif i == m and end_res in self.dock_bays:     # into a dock-side bay: released on arrival, not held for the crane
                uses.append((res, self.demand(res, b, loaded, p, cap), i, i, st[i + 1] - st[i] + tail))
            else:
                uses.append((res, self.demand(res, b, loaded, p, cap), i, i + 1, tail))
        if end_res != ("r", runs[-1][0]):
            uses.append((end_res, end_d, m, None, 0.0))
        if dst in self.doors:
            r_, d_, dl = door(dst)
            uses.append((r_, d_, m + 1, m + 1, dl))
        return D / v, st, uses, m + 1


def _area(pts):
    """Polygon area (shoelace)."""
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2 if pts else 0.0


def cover(poly, clip):
    """Share of the area of polygon poly inside the convex polygon clip (edge-by-edge clipping; a repeated closing point does
    no harm). Used to check the map's coversZones."""
    clip = clip[:-1] if clip[0] == clip[-1] else clip
    sgn = 1 if sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(clip, clip[1:] + clip[:1])) > 0 else -1
    side = lambda p, a, b: sgn * ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) >= 0
    pts = poly
    for a, b in zip(clip, clip[1:] + clip[:1]):
        out = []
        for p, q in zip(pts, pts[1:] + pts[:1]):
            if side(p, a, b) != side(q, a, b):
                d = (b[0] - a[0]) * (q[1] - p[1]) - (b[1] - a[1]) * (q[0] - p[0])
                t = ((b[0] - a[0]) * (a[1] - p[1]) - (b[1] - a[1]) * (a[0] - p[0])) / d
                out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
            if side(q, a, b):
                out.append(q)
        pts = out
        if not pts:
            break
    return _area(pts) / _area(poly)
