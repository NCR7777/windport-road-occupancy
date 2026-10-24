"""Completing the key of the network cache (fixes a program error).

windport.sim.get_net, windport.sim2.get_net and windport.sim4.get_net4 cache networks by [geo, p["section"]], but
occupancy.network.Net also reads the parameters in BUILD when building a network (retrofit; block_m / section_gap_m /
section_min_m of the sectional blocking; dock_stops / frontage_* of the dock frontage stops; unrestricted_w of the passing
stretches; checked one by one in Net.__init__, _stops, _dock_frontage, _frontage_runs, _section, _passing). Within one process,
a network built first for a geo would be reused by later configurations that differ in these parameters. install() wraps the
three functions: if the cached network under the same key was not built with the same set of build parameters (or not through
this module), it is dropped and rebuilt.
The cache dictionaries and the original functions are unchanged (the hashed windport/*.py files are not modified); once the keys
of the three modules are changed to build_key, this module can be removed.
"""
import json

BUILD = ("retrofit", "section", "block_m", "section_gap_m", "section_min_m", "dock_stops", "frontage_gap", "frontage_merge", "frontage_min_len", "unrestricted_w")


def build_key(geo, p):
    return json.dumps([geo, {k: p.get(k) for k in BUILD}], sort_keys=True, default=str)


def _wrap(fn, cache):
    def get(geo, p):
        base = json.dumps([geo, p.get("section")], sort_keys=True)
        full = build_key(geo, p)
        hit = cache.get(base)
        if hit is not None and getattr(hit[1], "_build_key", None) != full:
            del cache[base]
        out = fn(geo, p)
        out[1]._build_key = full
        return out
    get._netcache_orig = fn
    return get


def install():
    """Idempotent. windport_design.setup_env replaces sim2.get_net by sim4.get_net4; this function may be called before or after."""
    from windport import sim as WS, sim2 as S2, sim4 as S4
    for mod, name, cache in ((WS, "get_net", WS._NETS), (S2, "get_net", S2._NETS), (S4, "get_net4", S2._NETS)):
        fn = getattr(mod, name)
        if not hasattr(fn, "_netcache_orig"):
            setattr(mod, name, _wrap(fn, cache))
