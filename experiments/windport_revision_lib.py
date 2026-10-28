"""Shared parts of the revision studies (committed modules are not changed; the new semantics are layered on with install(),
live under experiments/ and stay outside the windport/*.py glob hash).

1. Tandem cradle spacing: install_spacing(sp) replaces windport.archetypes.DEFAULTS["cradle_spacing"] with sp (cradle positions
   of layouts A1-A3 are x_k = first cradle + k·spacing; process-wide, one value per process) and clears the network caches.
   Design rule L_v + δ = 115 m; with the default 110 m the results are byte-identical to the committed ones.
2. Near-yard storage slots: when geo["buf"] = layout name ("okpo" / "yantai"), the road frontage of the one-voyage storage zone
   in the derived map is replaced by the columns of the layout (one drive-in stop per column: the loaded vehicle crabs sideways
   into and out of the slot; slots in one column are last in, first out). Load-out tasks pick from the columns in the order the
   layout gives (cfg["revision_origins"]); each pick-up adds a crabbing time (added to hp_s in cfg's p, for the farthest slot). The
   layouts are computed on the map by windport_revision_buffer (plans.json).
3. Turn bans (node_trace_016): when geo["ban"] = [[node, incoming road, outgoing road], ...], these loaded turning movements are
   set to not allowed in the derived map, so routes use other roads.
install_all(plans): wraps the derived-map entry points (windport.sim4.build_map4, windport.sim.setup) for all three;
configurations without these markers are byte-identical to the original functions.
"""
import copy

from windport import archetypes as A
from windport import shipyard as SY
from windport import sim as WS
from windport import sim2 as S2
from windport import sim4 as S4

PLANS = {}
_LOAD = SY.load


def install_spacing(sp):
    A.DEFAULTS["cradle_spacing"] = float(sp)
    WS._NETS.clear()
    S2._NETS.clear()


def frontage_runs(site, plan):
    """Layout columns -> road frontage of the one-voyage storage zone (one run per column, 10 m long, written like the cradle
    positions in shipyard.build)."""
    return [dict(roadId=c["road"], sStartM=round(c["s"] - 5.0, 3), sEndM=round(c["s"] + 5.0, 3)) for c in plan["columns"]]


def patched_load(site, buf, ban):
    D, how = _LOAD(site)
    D = copy.deepcopy(D)
    if buf:
        z = D["zones"][SY.SITES[site]["storage_zone"]]
        z["extensions"][SY.RS]["frontage"] = frontage_runs(site, PLANS[buf])
    for node, ra, rb in ban or []:
        hit = 0
        for m in D["movements"].values():
            j = D["junctions"][m["junctionId"]]
            if node in j["nodeIds"] and m["incomingArc"]["roadId"] == ra and m["outgoingArc"]["roadId"] == rb:
                m["allowed"] = False
                hit += 1
        assert hit >= 1, (site, node, ra, rb)
    return D, how


def install_all(plans=None):
    """Idempotent. Install windport_design_lib (transfer network) first, then this layer."""
    if plans:
        PLANS.update(plans)
    b4 = S4.build_map4
    if not getattr(b4, "_revision", False):
        def build_map4(geo):
            if geo.get("buf") or geo.get("ban"):
                SY.load = lambda s, _g=geo: patched_load(s, _g.get("buf"), _g.get("ban"))
                try:
                    return b4(geo)
                finally:
                    SY.load = _LOAD
            return b4(geo)
        build_map4._revision = True
        S4.build_map4 = build_map4
    st = WS.setup
    if not getattr(st, "_revision", False):
        def setup(cfg):
            out = st(cfg)
            o = cfg.get("revision_origins")
            if o:
                D, net, p, tasks, starts, quay, cal = out
                rows = D["windport"]["storage"]
                for t in tasks:
                    if t["flow"] == "load":
                        t["o"] = rows[o[t["id"] % len(o)]]
            return out
        setup._revision = True
        WS.setup = setup
