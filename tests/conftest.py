"""Shared fixture: restore the module attributes that the experiment overlays patch globally (main2 geometry, lifting
semantics, transfer network, revision overlays, network cache) and the default cradle spacing."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

PATCHED = [("windport.sim", "PortSim"), ("windport.sim2", "ConvoySim"), ("windport.sim3", "CutSim"), ("windport.sim2", "build_map"),
           ("windport.sim2", "get_net"), ("windport.check", "check"), ("windport.archetypes", "build"), ("windport.archetypes", "GEOMETRY"),
           ("windport.sim4", "build_map4"), ("windport.sim", "setup"), ("windport.sim", "get_net"), ("windport.sim4", "get_net4"),
           ("windport.lift", "under_res"), ("windport.check_lift", "under"), ("windport_extra", "kassels_order"), ("windport.bound_all", "parts"),
           ("windport.bound_all", "terms"), ("windport.shipyard", "load"), ("windport_spatial", "cfg_of"), ("windport_recheck_unified", "cfg_of"),
           ("windport_recheck_maingeom", "cfg_of")]


@pytest.fixture
def restore():
    mods = {m: importlib.import_module(m) for m, _ in PATCHED}
    old = [(mods[m], a, getattr(mods[m], a)) for m, a in PATCHED]
    from windport import archetypes as A
    sp = A.DEFAULTS["cradle_spacing"]
    yield
    for mod, a, v in old:
        setattr(mod, a, v)
    A.DEFAULTS["cradle_spacing"] = sp
    from windport import sim as WS, sim2 as S2
    S2._NETS.clear()
    WS._NETS.clear()
