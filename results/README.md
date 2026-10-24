# Result data

The files of this directory are the result files that the paper reads, with the configuration of each run directory and
the inputs of each report directory, and two inputs of the shipyard batches (the turn analyses on the yard maps).
`MANIFEST.csv` lists every file of `results/` with its SHA-256, its size, the commit of the research repository it was
exported from (`source_commit`), how it was exported (`export`) and where the paper uses it (`used_for`). `RECOMPUTE.md`
(repository root) gives the command and the order of the scripts.

`export` is
- `as committed`: copied byte for byte;
- `configuration: internal fields removed, text translated`: the `config.json` of a run. The parameters, grids and scenarios
  are unchanged; removed are the SHA-256 of the code and input files of the research repository and the run label; the
  shipyard maps are replaced by the names of their derived graphs (`networks`); directory names and batch labels are
  written as in this release; the key `geometry` (the parameters of the layout geometry, as `windport.archetypes.GEOMETRIES`)
  is written `geometry_params`;
- `labels translated, internal names renamed` / `text translated, internal names renamed` / `notes translated`: CSV and JSON
  data whose labels or notes were in Chinese (the label text only; numbers and keys unchanged), and whose batch labels and
  directory names are written as in this release (the same renaming as the code: below);
- `translated`: markdown reports, translated;
- `paths renamed`: `inputs.json` of a report directory;
- `split in two parts`: `tables/design/compat/e_recheck_rows_part1.csv` and `_part2.csv` are one table of 317,308 data rows
  (58 MB) split at data row 158,654 so that each file stays below 50 MB; both parts carry the header row; part 1 followed by
  part 2 without its header row is the table.

## Layout

| Directory | Contents |
|---|---|
| `runs/w1_grid`, `runs/theorems`, `runs/chain` | exhaustive checks of W, of Theorems 3 and 4, of the cut in series (two-block chains) |
| `runs/random_bound`, `runs/random_lift_1`-`4`, `runs/main2_random_a`, `runs/main2_random_dead` | random-layout regressions (summaries) |
| `runs/recheck`, `runs/facts` | recheck of the return correction; code facts (set composition, widths) |
| `runs/deadend_exact`, `runs/deadend_chain2`, `runs/conservative_exact` | exhaustive checks against W″ (original and conservative lifting rule; summaries) |
| `runs/maingeom_<batch>` | batches on the main geometry of the layouts (first cradle 170 m), conservative lifting rule: `e1e3_e1h` (gate holding places), `runs_e4` (fleet and cradles), `runs_conv` (convoy dispatch), `extra_port` (port times), `extra_sens` (sensitivity), `e2` (CP-SAT small instances, `e2long/` with 600 s), `critical`, `example`, `sens` (closure under the load), `xscan` (release threshold) |
| `runs/main2_splice`, `runs/main2_codesign` | main2 geometry: rerun points spliced into their batches (`e1e3_e1/`, `runs_pocket/`, `extra_sens5/`); joint-design enumeration |
| `runs/design_e6_hi` | shipyards, one voyage of storage, alternative manoeuvres (upper durations) |
| `runs/design_turn`, `runs/spatial_turn_sweep` | turn analyses on the yard maps: class and duration of each alternative turn (`turn_alt.json`), turns that need one (`turn_extra.json`) |
| `runs/survey` | public load-out sites: `segments_public.csv` (haul paths by segment, measured on imagery, no coordinates), `critical_points.csv` (the sites as points of the critical-length figure) |
| `tables/sites`, `tables/sites_multi` | the berth, storage area, gate and waiting area of each shipyard, one voyage and three voyages of storage |
| `tables/spatial`, `tables/conservative`, `tables/main2`, `tables/design` | report tables of the stages (spatial additions, conservative lifting rule, main2 geometry, design analyses); `reports/after/e1_e3`, `e4_e7`, `extra`: the report tables of `windport_report.py`, `windport_report2.py`, `windport_report3.py` on the batches of the stage |

## Conventions

- Layouts `A1`, `A2`, `A3` are Layouts 1, 2, 3 of the paper (`A1rows`: Layout 1 with the rebuilt side-by-side cradle rows of
  the main2 geometry; `A1side`, `A1pass`: side-by-side cradles and passing places of the spatial additions); `map:okpo`,
  `map:yantai` (or `kind = map` with `site`) the two shipyards; `storage`: `runs` one voyage, `multi` three voyages,
  `transfer` the two-level transfer.
- Batch labels: `<stage>:<part>`, with the stages `e1e3` (E1-E3), `runs` (E4-E7), `extra` (the extra analyses), `spatial`,
  `deadend`, `conservative`, `unified`, `maingeom`, `main2`, `design`; directory names `runs/<stage>_<part>`.
- `semantics`: `lift_tu0.05_head` is the conservative lifting rule with the area under the load closed for t_u = 0.05 p and
  the load extent of the main measure; `src` names the batch whose keys a rerun takes.
- Scenarios (`scen`): `base` (the Rønne case model: loaded 2.5 km/h, crane cycle 1 h), `slow` (loaded 1 km/h), `long`
  (storage-quay route 1,500 m with a 1,200 m single lane), `longslow` (both), `lane` (as `longslow`, the single lane without
  side branches), `longpile` (vehicle and monopile 123.6 m), `fastcrane` (crane cycle 0.5 h), `joint`, `jointshared`
  (unloading and load-out on shared roads, by a dedicated or the shared fleet).
- Cradles (`mode`): `on_road` roadside cradles, `pull_in` pull-in cradle bays; `S` the number of cradles (0 = direct lift
  from the vehicle); `lift`: `cradle`, `direct`, `mixed`; `S1m`, `S3m` mixed lifting with 1 or 3 cradles.
- `K` SPMT sets; `L` window length and `G` time before the window (h); `hold` gate holding places Q_h (`inf` unlimited);
  `rule`: `fcfs` first-come-first-served, `convoy` convoy dispatch; `x` the overlap of unloading and load-out or the release
  time of a direct lift as a share of the crane cycle; `lat` the lateral clearance (m); `reach` / `S_r` the cradle positions
  within the crane's reach, `shift_s` / `t_sh` the time to shift for the others.
- `w1` the bound W, `w1g` the strengthened bound W′, `new` the bound W″ of the recheck tables (`sem = lift`: conservative lifting rule),
  `binding`, `cls`, `lab` their binding terms (`crane`, `cradle turnover`, `fleet`, `road`; `tie (...)` when several bind;
  `·preparation` when the preparation term binds), `regime` interface-, staging- or flow-limited; `sim` the monopiles lifted
  in the window in the simulation; `port_h` the vessel's port time (h); `lstar` the rule-free bound on it; `check_ok` 1 if
  the independent checker accepts the schedule.
- Alternative turns (`cls`): `in place, feasible (road surface only)`, `early re-orientation`, `reversing or crab steering`,
  `no space (operator to confirm)`; durations `t` for loaded speed `base` / `slow` and the lower (`lo`) and upper (`hi`) end.
