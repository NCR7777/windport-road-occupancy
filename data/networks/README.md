# Road networks of the two shipyards (derived graphs)

The shipyard case of the paper (Section 5, experiment E6) places a load-out berth, a monopile storage area and an off-road
waiting area on the road networks of two shipyards. The networks are released as derived graphs: the topology and the
quantities the model uses, with no coordinates. They were derived from vector maps digitised from Google Earth imagery
(Google Earth Pro; Okpo dated 15 November 2023: Google, Airbus, TMap Mobility; Yantai dated 11 March 2025: Google, Airbus).
Neither the imagery nor the centre-line geometry traced from it is released. Map lines delineate study areas and do not
necessarily depict accepted national boundaries.

| Directory | Yard | Map revision | Site key (`windport.shipyard.SITES`) |
|---|---|---|---|
| `okpo/rev1833` | Okpo (Hanwha Ocean, Geoje, Korea) | 1833 | `okpo` |
| `yantai/rev396` | Yantai (CIMC Raffles, China) | 396 | `yantai` |

`windport.shipyard.load(site)` reads a graph; `windport.shipyard.build(site, cradle_mode, n_cradles)` adds the storage area,
the cradles and the gate of `SITES` and returns the network the simulation runs on (`windport.sim2.build_map` with
`geo = dict(kind="map", site=..., cradle_mode=..., n_cradles=...)`).

Each graph holds the yard's road network as mapped, plus the off-road waiting area of this study: a stub road
`pocket_stub` (30 m long, 20 m wide) from the junction `SITES[site]["near"]` beside the storage area to the end node
`pocket`, laid in the direction farthest from the roads at that junction, with movements between the stub and every other
road at the junction (one-way roads only in their direction). Idle vehicles park at `pocket`.

Names (of roads, nodes, buildings, zones) are the map's names translated from Chinese; identifiers (`road_…`, `node_…`,
`facility_…`, `zone_…`) are those of the maps and appear in the result files. All files are UTF-8 CSV with a header row;
lengths and chainages are written in full precision (Python `repr`), so they read back exactly.

## Files

**`meta.json`** - `yard`, `revision`, and `frontage_rule` (`gap`, `min_len`, `merge`, in m): the rule with which the dock
frontage stretches of `frontage.csv` were derived.

**`nodes.csv`** - `node_id`, `name`, `kind` (`access`: an entrance node of a building; `ordinary`).

**`roads.csv`** - one row per road (an undirected edge; the model forms one arc per direction and splits a road at its stops).

| Field | Meaning |
|---|---|
| `road_id`, `name` | identifier and map name |
| `from_node`, `to_node` | end nodes; "forward" runs from `from_node` to `to_node` |
| `length_m` | length of the centre line (m) |
| `width_m` | road width (m) when `width_state` is `known` |
| `width_state` | `known`, or `unrestricted` for access roads without a width limit (the model gives these the equivalent width `unrestricted_w`) |

A road is a resource with capacity `width_m + c` (lateral clearance `c`); junctions of degree three or more and all entrance
nodes are resources too, of size `D` = the largest known width of the adjacent roads.

**`junctions.csv`** - `junction_id`, `node_id`: the node at which the movements of a junction take place.

**`movements.csv`** - one row per possible movement through a junction: `movement_id`, `junction_id`, `in_road`, `in_dir`
(`forward`, `backward`), `out_road`, `out_dir`, `allowed` (`true` if permitted; shortest paths use only permitted movements)
and `turn_deg`, the turn angle (degrees, 0 = straight on, 180 = U-turn) from the headings of the two roads 3 m from the
junction. `turn_deg` is written with 25 significant digits so that `occupancy.network.deg_to_rad` returns, to the last bit,
the angle in radians that the simulation computed from the map geometry: a loaded SPMT set stops and changes its steering
programme at every turn of at least `turn_deg` (60 degrees), and the time of the turn grows with the angle
(`windport.sim.turn_delays`).

**`access_points.csv`** - entrances of buildings: `access_id`, `name`, `node_id`, `facility_id`.

**`facilities.csv`** - buildings: `facility_id`, `name`, `class`, `access_points` (separated by spaces).

**`zones.csv`** - open areas: `zone_id`, `name`, `class` (`yard`, `buffer`, `assembly_yard`, `dry_dock`, `floating_dock`,
`quay`, ...).

**`frontage.csv`** - stretches of road along a zone where vehicles stop: `zone_id`, `k`, `road_id`, `s_start_m`, `s_end_m`
(chainage from `from_node`). The saddle rows of the monopile storage area are the stretches of the storage zone of `SITES`.

**`cranes.csv`**, **`crane_spans.csv`** - the erection cranes of the docks and the gantry-crane spans (from the map; not used
by the port model, kept so that the graph is complete).

In the port model all classes of the yard are background (`windport.shipyard.build` renames them `map_<class>`): only the
storage area, the cradles and the waiting area of the study take part in the flows.

## Checks

The graphs were derived from the maps with the simulation's own code: for both yards and both cradle modes, the network
built from a graph and the network built from the map are identical in every road length and width, every arc, permitted
movement and turn angle (bit for bit), every stop, entrance and resource capacity (RECOMPUTE.md); the simulated points of
`results/runs/e6` rerun from the graphs to every column of `points.csv`.
