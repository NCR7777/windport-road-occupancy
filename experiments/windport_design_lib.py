"""Shared parts of the design analyses (committed modules are not modified; the new semantics are layered on with install(), as in
windport/lift.py and main2.py, but kept under experiments/ so that the glob hash of windport/*.py does not change again).

1. Transfer network for two-level storage: with geo = dict(kind="map", site, storage="transfer") the derived graph starts at the campaign storage
   area (the far yard of SITES_MULTI) and ends at the near yard sized for one voyage (the storage zone of SITES, Okpo zone_trace_027, Yantai
   zone_trace_003): the near yard has one pull-in set-down position at the midpoint of each frontage segment ("cradle", cradle_mode = "pull_in"),
   set-down h_d as before; the "ship crane" is TRANSFER_LIFT_S (removal after set-down in the near yard, not limiting) and is open from 0
   (empty system, no preparation before the window). The waiting area is attached on the far-yard side (near of SITES_MULTI); the "gate" is the
   waiting-area junction of the near yard (near of SITES).
2. Alternative turns: turn_extra(site, st, scen, level) gives the seconds of each turn from the windport_turn_alt result (turn_alt.json).
install(): replaces windport.sim4.build_map4 by a version that accepts storage = "transfer" (otherwise byte for byte the original function)."""
import copy
import json
from pathlib import Path

from windport import shipyard as SY
from windport import sim4 as S4

ROOT = Path(__file__).resolve().parents[1]
TRANSFER_LIFT_S = 60.0
_BUILD4 = S4.build_map4


def near_slots(site):
    """Set-down positions of the near yard: (road, chainage) = midpoint of each frontage segment."""
    D, _ = SY.load(site)
    z = D["zones"][SY.SITES[site]["storage_zone"]]
    fr = (z.get("extensions") or {}).get(SY.RS, {}).get("frontage") or []
    return [[f["roadId"], round((f["sStartM"] + f["sEndM"]) / 2, 2)] for f in fr if f["roadId"] in D["roads"]]


def transfer_site(site):
    far = S4.SITES_MULTI[site]
    return dict(far, quay_zone=SY.SITES[site]["storage_zone"], gate=SY.SITES[site]["near"], cradles=near_slots(site))


def build_map4(geo):
    if geo.get("kind") == "map" and geo.get("storage") == "transfer":
        S = transfer_site(geo["site"])
        D = SY.build(geo["site"], "pull_in", geo.get("n_cradles") or len(S["cradles"]), S=S)
        D["windport"]["transfer"] = dict(far=S["storage_zone"], near=S["quay_zone"])
        return D
    return _BUILD4(geo)


def install():
    S4.build_map4 = build_map4


def transfer_cfg(site, K, n, scen_p, open_h=400.0):
    """Far → near transfer: empty system, the ship crane (removal in the near yard) open from 0; n piles."""
    nc = len(near_slots(site))
    p = dict(scen_p, lift_s=TRANSFER_LIFT_S)
    return dict(geo=dict(kind="map", site=site, cradle_mode="pull_in", n_cradles=nc, storage="transfer"), p=p, S=nc, K=K, lift="cradle",
                horizon_h=open_h, cal=dict(crane=[[0.0, open_h]]), n_load=n, fixed=False, hold=0, rule="fcfs")


# ---------------------------------------------------------------- alternative turns
def turn_file():
    fs = sorted(ROOT.glob("results/runs/design_turn/turn_alt.json"))
    assert len(fs) == 1, f"need exactly one turn result directory: {fs}"
    return fs[0]


_ALT = {}


def turn_extra(site, st, scen, level):
    """{turn key: seconds}: level = "feas" (all feasible) → {}; "lo" = shortest of all feasible families, steering-mode switch at the low end of
    TSW; "hi" = reverse-crab only, high end of TSW (windport_design --part turn). Speed by scenario (slow: 1 km/h, otherwise 2.5 km/h)."""
    if level == "feas":
        return {}
    if not _ALT:
        _ALT.update(json.loads(turn_file().read_text(encoding="utf-8")))
    vn = "slow" if scen == "slow" else "base"
    return {key: x["t"][f"{vn}|{level}"] for key, x in _ALT[f"{site}|{st}"].items()}


def with_turns(c, site, st, scen, level):
    c = copy.deepcopy(c)
    ex = turn_extra(site, st, scen, level)
    if ex:
        c["p"] = dict(c["p"], turn_extra=ex)
    return c
