"""Parameters of the road-occupancy core (the defaults that the port simulation builds on).

The port simulation (windport/sim.py) takes these defaults and overrides them with its base case (windport.sim.BASE) and the
parameters of each point; every batch of results stores the full parameter set it ran with (results/runs/*/config.json).
Values and sources: data/register/parameters.csv and the manuscript (Table 4, Appendix B).
"""

DEFAULTS = dict(
    v_empty=12.0 / 3.6,        # m/s
    v_loaded=6.0 / 3.6,        # m/s
    plat_len=16.25,            # m, length of an empty vehicle; a loaded vehicle is max(block length, platform length) long
    plat_w=5.5,                # m, width of an empty vehicle w
    lat_clear=1.0,             # m, lateral clearance c
    long_clear=5.0,            # m, longitudinal clearance (as a time: clearance / speed)
    turn_sweep_s=30.0,         # s, extra time a junction is swept when a vehicle turns by at least turn_deg
    turn_deg=60.0,
    load_s=600.0, unload_s=600.0,
    block_w=(5, 15), block_l=(10, 30),
    width_delta=0.0,           # m, added to every mapped road width
    unrestricted_w=31.0,       # m, equivalent width of a road without width limit = 2 B_max + c: two loaded vehicles pass
    empty_rule="width",        # width: empty vehicles pass by road width; exclusive: empty vehicles hold every road alone; free: always pass
    day_s=16 * 3600.0, days=4, warmup_days=1, batches=8,
    deadlock_recovery_s=900.0,  # stepwise requests: time to clear a deadlock (one vehicle backs onto open ground); None = no recovery
    near_deadlock_s=1800.0,     # a request waiting longer than this counts as a near-deadlock
    frontage_gap=8.0, frontage_min_len=10.0, frontage_merge=3.0,   # frontage rule of docks
    dock_stops=None,           # roadside stops per dock: None = one per frontage stretch; n = only the n longest
    reserve_jit=True,          # full-path reservation: once the loaded run is booked, the empty run is delayed to arrive just in time
    flow_share=None,           # {flow: share}: sets the share of one flow, the other flows scale; None = base weights
    erect_batches=None,        # P6 tasks are released only in these batches (from 0); None = spread like the other tasks
    od_sampling="entity",      # entity: entities of a role equally likely, stops of an entity equally likely (main model);
                               # stop: all stops of a role equally likely (destination not in the origin's entity)
    # Sectioning of long roads (Net._section): None = one resource per road; "stops" = roads longer than section_min_m with
    # roadside stops get section boundaries section_gap_m before and after each stop; with block_m each section is cut
    # further into blocks of length <= block_m
    section=None, section_min_m=200.0, section_gap_m=25.0, block_m=None,
)

# Roles of origins and destinations (flows of the block-transport model and their weights). The port model maps its classes
# onto these roles (windport.archetypes.ROLES): monopile storage -> yard, roadside cradles -> buffer, pull-in cradle bays ->
# assembly_yard, ramp top -> assembly_workshop.
FLOW = [
    ("P1", "assembly_workshop", "outfitting_workshop", 0.5),
    ("P2", "assembly_workshop", "paint_workshop", 0.5),
    ("P3", "outfitting_workshop", "paint_workshop", 0.5),
    ("P4", "paint_workshop", "yard|buffer", 0.7),
    ("P5", "yard|buffer", "assembly_yard", 0.7),
    ("P6", "assembly_yard", "dry_dock", 0.2),
    ("P7", "assembly_workshop", "assembly_yard", 0.05),
    ("P8", "paint_workshop", "assembly_yard", 0.3),
]
START_CLASSES = ("assembly_workshop", "paint_workshop", "outfitting_workshop")
STOP_MODE = {"yard": "pull_in", "assembly_yard": "pull_in", "buffer": "on_road", "dry_dock": "on_road"}
DOCK_CLASS = "dry_dock"
