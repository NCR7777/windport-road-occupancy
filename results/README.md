# Result data

`MANIFEST.csv` lists every file of `results/` with its SHA-256, its size, the commit of the research repository it was
exported from (`source_commit`), how it was exported (`export`) and where the manuscript uses it (`used_for`).
`RECOMPUTE.md` (repository root) names the command that recomputes each directory.

`export` is `as committed` for files copied byte for byte; `configuration: internal fields removed, text translated` for
the `config.json` of a run (the parameters, grids and scenarios are unchanged; removed are the SHA-256 of the code and input
files of the research repository and the run label, and the shipyard maps are replaced by the names of their derived
graphs); `labels translated` for tables whose label columns were in Chinese (the label text only; numbers and keys
unchanged); `paths renamed` for `inputs.json`; `notes translated` and `translated` for JSON notes and markdown reports;
`internal labels renamed` where labels, keys or column names carried internal run labels (the batch labels of
`runs/recheck` are `runs:<part>` for the batches of `windport_runs.py` and `extra:<part>` for those of `windport_extra.py`,
rows sorted by them as the script sorts them; the E1 baseline of `tables/e4_e7/table_pocket.csv` is in `sim_e1` and
`tie_e1`), exactly as the release code writes them.

## Layout

| Directory | Contents |
|---|---|
| `runs/<run>/` | one batch each: `config.json` (layouts, parameters, scenarios, grid), `points.csv` (one row per point), and where the batch writes them `summary.md`, `summary.json`, `cases.csv`, `bad.csv` (random regressions), `<part>.csv` (analytic parts) |
| `tables/e1_e3/` | report tables of E1-E3 (`windport_report.py`): bound against simulation (`fig2.csv`), binding regimes (`fig_regime.csv`), port time of the two representations (`fig3.csv`, `table3.csv`), E2 summary (`table2.csv`), gate holding places (`table_hold.csv`), release time of direct lifts (`table_rel.csv`), `summary.md` |
| `tables/e4_e7/` | report tables of E2 with W′ and convoy dispatch (`table2b.csv`), E4 plateau and cradle-vehicle rates (`table_e4_plateau.csv`, `table_e4_rate.csv`, `fig4.csv`), E5 (`table_e5.csv`), E6 shipyards (`table4.csv`, `fig6.csv`), E7 (`table_e7.csv`), off-road waiting area (`table_pocket.csv`), gate holding places with convoy dispatch (`table_hold2.csv`), sensitivity (`tableC_e*.csv`), `summary.md` (`windport_report2.py`) |
| `tables/extra/` | worked example (`table_example.csv`), added columns of the fixed-time table (`table5x.csv`, `fig5x.csv`) and of the plateau table (`table6x.csv`), cost and configuration (`table_cost.csv`, `table_cost_best.csv`), critical single-lane length (`fig13_critical.csv`, `table_critical_check.csv`), mixed lifting and release time (`table_mixx.csv`, `table_mixx_win.csv`), added sensitivity rows (`tableC3x.csv`, `tableC4x.csv`), diameters (`table7_diam.md`), public projects (`table_pub.md`), `summary.md` (`windport_report3.py`) |
| `tables/sites/` | the berth, storage area, gate and waiting area of each shipyard (`sites.json`, `sites.md`), selected on the yard maps by the rules of `windport/shipyard.py` |

The runs: `w1_grid`, `theorems` (exhaustive checks); `e1`, `e1_hold`, `release_time`, `e3` (`windport_sim.py`); `e2`,
`e2_long` (`windport_e2.py`, `windport_e2long.py`); `e4`, `e5`, `e6`, `e7`, `pocket`, `convoy_hold`, `e2_convoy`, `sens`
(`windport_runs.py`); `sens_e7` (`windport_sens_e7.py`); `chain` (`windport_chain_check.py`); `random_bound`
(`windport_random.py`); `random_lift_1`-`4` (`windport_random_lift.py --gen main|main|port|hold`); `port_time`,
`fixed_time`, `mixed_e4`, `mixed_release`, `sens_extra`, `public_projects` (`windport_extra.py --part port|fix|mix6|mixx|sens|pub`);
`sens_e5` (`windport_sens_e5.py`); `example`, `critical` (`windport_analytic.py`); `facts` (`windport_facts.py`); `recheck`
(`windport_recheck.py`).

## Conventions

- Layouts `A1`, `A2`, `A3` are Layouts 1, 2, 3 of the paper; `map:okpo`, `map:yantai` (or `kind = map` with `site`) the two
  shipyards.
- Scenarios (`scen`): `base` (the Rønne case model: loaded 2.5 km/h, crane cycle 1 h), `slow` (loaded 1 km/h), `long`
  (storage-quay route 1,500 m with a 1,200 m single lane), `longslow` (both), `lane` (as `longslow`, the single lane without
  side branches), `longpile` (vehicle and monopile 123.6 m), `fastcrane` (crane cycle 0.5 h), `joint`, `jointshared`
  (unloading and load-out on shared roads, by a dedicated or the shared fleet).
- Cradles (`mode`): `on_road` roadside cradles, `pull_in` pull-in cradle bays; `S` the number of cradles (0 = direct lift
  from the vehicle); `lift`: `cradle`, `direct`, `mixed`.
- `K` SPMT sets; `L` window length and `G` time before the window (h); `hold` gate holding places Q_h (`inf` unlimited);
  `rule`: `fcfs` first-come-first-served, `convoy` convoy dispatch; `x` the overlap of unloading and load-out (E5) or the
  release time of a direct lift as a share of the crane cycle; `lat` the lateral clearance (m).
- `w1` the bound W, `w1g` the strengthened bound W′, `binding` / `w1g_binding` their binding terms (`interface`, `turnover`,
  `fleet`, `cut`, `zone`, `prep`, `serial`), `regime` interface-, staging- or flow-limited; `sim` the monopiles lifted in the
  window in the simulation; `port_h` the vessel's port time (h); `check_ok` 1 if the independent checker accepts the
  schedule.
