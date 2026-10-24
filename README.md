# windport-road-occupancy

Code, data and results of the paper

> **Road-occupancy capacity of offshore wind marshalling ports: transporter fleet, quayside staging and access-road
> co-design under load-out windows**
> Chunrui Na, Qing Wang, Xiao Han, Jingzheng Yao, Yuntao Zhang, Kun Ma, Chengjing Song
> College of Shipbuilding Engineering, Harbin Engineering University; School of Civil and Environmental Engineering,
> Nanyang Technological University; Yantai Research Institute, Harbin Engineering University; College of Computer Science
> and Technology, Harbin Engineering University; Department of Electronics and Telecommunications, Politecnico di Torino.
> Manuscript prepared for submission to *Ocean Engineering*.

At an offshore wind marshalling port, self-propelled modular transporters (SPMT sets) carry monopiles from the storage area
to the quay, where the installation vessel's crane lifts them on board within a load-out window. Where the haul path
narrows to a single lane, a loaded set holds it alone. The code models the port roads, junctions, quay cradles and the
RoRo ramp as resources that a loaded or empty set holds for load-dependent blocking times, under the conservative lifting
rule (a lift from the vehicle starts only once the vehicle body has left the road, and the area under the load is closed
while it is lifted). It simulates the load-out (and the unloading of barges) on parametric port layouts and on two
shipyards used as monopile bases, with one voyage, three voyages or two levels of storage; computes the bound W″ on the
monopiles a window delivers under any dispatching rule, the rule-free bound on the vessel's port time and the screen of a
load-out site; screens public load-out sites from their haul paths; and checks every simulated schedule with an
independent checker, the bounds by exhaustive enumeration, random regression and constraint programming (CP-SAT).

The repository holds

- the code: the port simulation and its dispatching rules, the bounds, the small-instance enumeration and CP-SAT models, the
  independent checkers, the geometry checks, the screen of public sites, and the script of every experiment of the paper;
- the parametric port layouts (Layouts 1-3 of the paper; `A1`-`A3` in the code) with their main geometry, generated as
  synthetic instances by `windport/archetypes.py` and `windport/main2.py`;
- the road networks of the two shipyards (Okpo, Yantai) as derived graphs without coordinates (`data/networks/`);
- the full parameter register with the public source, evidence class and access date of every value (`data/register/`);
- OpenStreetMap extracts of the public load-out sites, used for comparison only (`data/osm/`, ODbL);
- the result files that the paper reads (configurations, per-point tables, report tables), so that each reading can be
  checked without rerunning, and stored points can be rerun and compared.

## Code

```
windport/             port model: layouts (archetypes.py; main geometry with rebuilt side-by-side rows and the ramp in line
                      with the apron, main2.py), bounds (bound.py, bound2.py, bound3.py, bound4.py, bound_dead.py,
                      bound_lift.py; unified entry bound_all.py), simulation (sim.py, sim2.py, sim3.py; crane reach, cradle
                      rows, alternative turns and reserved periods sim4.py; conservative lifting rule lift.py), independent
                      checkers (check.py, check2.py, check3.py, check4.py, check_lift.py, check_all.py), small-instance
                      enumeration (exact.py, exact_u.py, exact_chain.py, exact_chain_tail.py, exact_chain_lift.py), CP-SAT
                      models (cpsat.py, cpsat_lift.py), geometry check of the layouts (geomcheck.py), shipyard sites on the
                      derived graphs (shipyard.py), public-site survey on OpenStreetMap (port_survey.py)
occupancy/            road-occupancy simulation core that the port model builds on: network and resources (network.py),
                      discrete-event simulation with full-path reservation (sim.py), tasks, bounds, defaults
bounds/, exact/       linear-programming helpers and the schedule checker of the occupancy core
experiments/          the batch, analysis and report scripts (tables below); batch.py: progress files and process pools
tests/                pytest suite of the model, the bounds, the checkers and the experiment code
data/networks/        derived graphs of the two shipyards (README.md there)
data/register/        parameter register (README.md there)
data/osm/             OpenStreetMap extracts of the public load-out sites (README.md there)
results/              runs/ (one directory per batch), tables/ (report tables), MANIFEST.csv, README.md
RECOMPUTE.md          the order of the scripts and the command that recomputes each result directory; the release check
requirements.txt      pinned package versions (Python 3.13.5)
environment.yml       conda environment with Python 3.13.5 and the packages of requirements.txt
LICENSE, LICENSE-data MIT (code), CC BY 4.0 (data; data/osm/ ODbL 1.0)
CITATION.cff          how to cite
```

Comments in the code number the corollaries as the derivation notes of the study do (Corollaries 1-11); the numbering in
the paper differs.

## Installation

Python 3.13.5 (64-bit).

```
python -m venv .venv
.venv\Scripts\activate            (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest tests            (180 tests, about 3 minutes; 13 are skipped, see RECOMPUTE.md)
```

OR-Tools (CP-SAT) 9.15.6755 is needed for the small-instance experiments and their tests; matplotlib only for the draft
figures that some report scripts draw next to their tables.

## Tables and figures of the paper

Every batch script builds its configuration, writes it to `results/windport_<stage>_<part>_<hash>/config.json` (the hash is
that of the configuration) and computes the points into that directory (`points/` holds one JSON per point and lets an
interrupted run resume; `points.csv` is the per-point table). The scripts accept `--procs N`; `--slots DIR` (optional)
shares the machine with other jobs through a directory of CPU slots, and without it an ordinary process pool is used. The
released directories carry the names of `results/runs/` and `results/tables/`, which are also the names the scripts read
their inputs from (RECOMPUTE.md). Python 3.13.5 throughout; the solver column names where OR-Tools CP-SAT 9.15.6755 is used,
everything else is simulation or closed-form evaluation. The configuration of each item is the `config.json` of its run
directories (`inputs.json` for report tables); `results/MANIFEST.csv` gives, for every file, the place in the paper where it
is used.

| Item | Result files (under `results/`) | Script and command | Solver |
|---|---|---|---|
| Table 3, base parameters and scenarios | `data/register/parameters.csv`; sensitivity ranges `runs/maingeom_extra_sens/points.csv` | parameters in `windport/sim.py` (`BASE`), `occupancy/params.py`, `windport/archetypes.py`; `python experiments/windport_maingeom.py --part rerun` | - |
| Table 4, public load-out sites and their screen | `runs/survey/critical_points.csv`, `runs/survey/segments_public.csv`; `tables/design/screen.md`, `screen_kmin.csv`, `numbers.json` (`screen`) | `python experiments/windport_survey.py` (needs the haul paths measured on imagery, not released); `python experiments/windport_design_analytic.py`; `python experiments/windport_report_design.py` | - |
| Table 5, shipyards as monopile bases (one voyage) | `runs/design_e6_hi/points.csv`; `tables/design/reports/after/e4_e7/table4.csv`; `tables/design/compat/e_recheck_rows_part1.csv`, `_part2.csv`, `compat/yards.csv`, `compat/spatial/table_turn.csv`; `tables/sites/` | `python experiments/windport_design.py --part e6:lo,e6:hi`; `python experiments/windport_report_design.py` | - |
| Table 6, two-level storage at the shipyards | `tables/design/twolevel.md`, `tables/design/numbers.json` (`twolevel`); inputs `runs/design_turn/turn_alt.json` | `python experiments/windport_design.py --part near,transfer`; `python experiments/windport_report_design.py` | - |
| Table 7, small instances: CP-SAT optima, W″ and simulation | `runs/maingeom_e2/points.csv`, `runs/maingeom_e2/e2long/points.csv`; `tables/design/reports/after/e4_e7/table2b.csv`; `tables/main2/recheck/rows.csv` | `python experiments/windport_maingeom.py --part e2` (60 s per instance, 600 s for the instances only proven feasible) | CP-SAT |
| Table 8, representations of port transport (core case: long single lane, 1 km/h, ten monopiles) | `tables/design/reports/after/e1_e3/table3.csv`, `fig3.csv`, `reports/after/extra/table5x.csv`; `runs/maingeom_extra_port/points.csv`; `tables/main2/core.csv`, `core.md` | `python experiments/windport_maingeom.py --part rerun,core`; `python experiments/windport_main2_runs.py --part core`; `python experiments/windport_report_main2.py`; `python experiments/windport_report_design.py` | - |
| Table 9, model elements removed in turn | `tables/main2/spatial/table_ablate.csv` | `python experiments/windport_maingeom.py --part spatial`; `python experiments/windport_report_main2.py` | - |
| Table 10, cradle-vehicle rates | `tables/design/compat/spatial/table7_rate.csv`, `tables/design/numbers.json` (`rate`); `tables/design/reports/after/e4_e7/table_e4_rate.csv`; `runs/maingeom_runs_e4/points.csv`; `tables/main2/recheck/rows.csv` | `python experiments/windport_maingeom.py --part rerun,spatial`; `python experiments/windport_main2_runs.py --part reachdist`; `python experiments/windport_rows_exclusion.py --part rowsx`; `python experiments/windport_rows_finish.py`; `python experiments/windport_report_design.py` | - |
| Table 11, price of a second set | `tables/design/reports/after/extra/table_cost.csv`, `table_cost.md`, `table_cost_best.csv` | `python experiments/windport_maingeom.py --part rerun`; `python experiments/windport_report_design.py` | - |
| Table 12, joint design | `runs/main2_codesign/codesign.csv`; `tables/design/numbers.json` (`codesign`) | `python experiments/windport_design.py --part codesign`; `python experiments/windport_codesign_blocks.py`; `windport_codesign_blocks2.py`; `windport_codesign_finish.py`; `python experiments/windport_report_design.py` | - |
| Table B.1, dimensions of the layouts | `data/register/parameters.csv`; `runs/survey/critical_points.csv` | `windport/archetypes.py` (`DEFAULTS`, `GEOMETRIES`), `windport/main2.py` | - |
| Table B.2, replication of public cases | `tables/conservative/reports/after/extra/table_pub.md`, `tables/conservative/kassels.md` | `python experiments/windport_rerun_conservative.py --batch extra:pub`; `python experiments/windport_report_conservative.py` | - |
| Fig. 4, critical single-lane length | `runs/maingeom_critical/critical.csv`; `tables/design/reports/after/extra/table_critical.md`, `table_critical_check.csv`; `runs/survey/critical_points.csv`; `tables/spatial/table_critical_points.md` | `python experiments/windport_maingeom.py --part critical` | - |
| Fig. 5, haul paths of the public sites | `runs/survey/segments_public.csv`; `data/register/parameters.csv` (public sites) | `python experiments/windport_survey.py` (as Table 4) | - |
| Fig. 6, regime map | `tables/main2/fig_regime_main.csv`, `tables/main2/regime.csv` | `python experiments/windport_main2_runs.py --part splice`; `python experiments/windport_recheck_main2.py`; `python experiments/windport_report_main2.py` | - |
| Fig. 7, port time of the two representations | `tables/design/reports/after/e1_e3/fig3.csv` | as Table 8 | - |
| Fig. 8, fleet plateau | `tables/design/reports/after/e4_e7/fig4.csv`, `table_e4_plateau.csv`; `tables/main2/recheck/rows.csv` | `python experiments/windport_maingeom.py --part rerun`; `python experiments/windport_recheck_main2.py`; `python experiments/windport_report_design.py` | - |
| Fig. 9, upsizing | `tables/main2/spatial/table_upsize.csv`; `tables/design/reports/after/e4_e7/table_e7.csv` | `python experiments/windport_maingeom.py --part rerun,spatial`; `python experiments/windport_report_main2.py` | - |
| Supplementary Tables S1-S21, Figs. S1-S5 | `runs/w1_grid` (S1); `tables/design/numbers.json` (S2 checks, S3 crane reach, S9 alternative turns, S10 joint-design dispatch); `runs/maingeom_example`, `reports/after/extra/table_example.csv` (S4); `reports/after/e4_e7/table_e4_plateau.csv`, `reports/after/extra/table6x.csv` (S5); `reports/after/extra/table_mixx*.csv` (S6); `tables/sites_multi`, `tables/main2/spatial/table_sites.csv`, `table_siteport.csv`, `compat/yards.csv` (S7-S8); `tables/design/campaign.md`, `tables/main2/spatial/table_campaign.md` (S11); `tables/main2/spatial/table_upsize.csv` (S12); `reports/after/e4_e7/tableC_e*.csv`, `reports/after/extra/tableC3x.csv`, `tableC4x.csv` (S13-S18); `reports/after/extra/table5x.csv` (S19); `runs/maingeom_e2` (S20); `data/register/parameters.csv` (S21); `reports/after/e1_e3/fig2.csv` (Fig. S1); `runs/maingeom_runs_e4` (Fig. S2); `reports/after/e4_e7/table_e5.csv` (Fig. S3); `reports/after/e4_e7/fig6.csv` (Fig. S4); sensitivity tables (Fig. S5) | the scripts of the corresponding main items; RECOMPUTE.md | CP-SAT for S20 |
| Verification counts of the text (exhaustive checks, random regression, recheck of every simulated point) | `runs/theorems`, `runs/chain`, `runs/deadend_exact`, `runs/deadend_chain2`, `runs/conservative_exact`, `runs/random_bound`, `runs/random_lift_1`-`4`, `runs/main2_random_a`, `runs/main2_random_dead`, `runs/recheck`, `runs/facts`, `runs/main2_splice`, `runs/maingeom_e1e3_e1h`, `runs/maingeom_runs_conv`, `runs/maingeom_sens`, `runs/maingeom_xscan`; `tables/main2/recheck/rows.csv`, `tables/main2/macros*.csv`, `tables/main2/geom_compat/` | RECOMPUTE.md | CP-SAT for the small instances |

`tables/design/reports/after/e1_e3/`, `e4_e7/` and `extra/` are the report tables that `experiments/windport_report.py`,
`windport_report2.py` and `windport_report3.py` write when run on the batches of the main2 geometry
(`windport_report_design.py` runs them); `tables/conservative/reports/after/extra/` the same for the conservative-rule
batches.

## Rerunning stored points

Every point is determined by its configuration (a layout or shipyard, parameters, fleet, cradles, windows); there is no
random seed outside the random regressions, whose cases are drawn from fixed seeds. For example, two rows of the E4 batch
on the main geometry (conservative lifting rule):

```python
import csv, io, sys
sys.path[:0] = [".", "experiments"]
import windport_maingeom as F, windport_rerun_conservative as RR
F.init_rerun({})                    # conservative lifting rule, main geometry, as in the worker processes of the batch
batch = "runs:e4"
lines = open("results/runs/maingeom_runs_e4/points.csv", encoding="utf-8").read().splitlines()
for line in (lines[1], lines[len(lines) // 2]):
    key = next(csv.DictReader([lines[0], line]))["key"]
    buf = io.StringIO()
    csv.DictWriter(buf, RR.cols(batch), lineterminator="\n").writerow(RR.rows(batch, key, RR.compute(batch, key))[0])
    print(key, buf.getvalue().rstrip("\n") == line)          # True: identical row
```

## Data sources and what is not released

The parameters come from published sources: project reports, manufacturers' data sheets, the Rønne case model of Kassels
(2023) and the literature; `data/register/parameters.csv` gives every value with its source, page or address, evidence
class, access date and how much of the source was read. Entries not checked against the source text are not included. The
parametric port layouts are synthetic.

The shipyard road networks were digitised from Google Earth imagery (Google Earth Pro; Okpo dated 15 November 2023: Google,
Airbus, TMap Mobility; Yantai dated 11 March 2025: Google, Airbus). Neither the imagery nor the centre-line geometry traced
from it is released: the networks are released as derived graphs (`data/networks/`), which hold everything the model uses;
the turns that need an alternative manoeuvre, found on the map geometry, are released as results
(`results/runs/spatial_turn_sweep/`, `results/runs/design_turn/`). Map lines delineate study areas and do not necessarily
depict accepted national boundaries.

The haul paths of the public load-out sites were measured on public satellite imagery (Esri World Imagery); their lengths,
widths and width classes are released without coordinates (`results/runs/survey/`, `data/register/parameters.csv`). The
imagery, the measured polylines and measurement lines and their coordinates are not released. The OpenStreetMap extracts of
`data/osm/` serve only as a comparison (© OpenStreetMap contributors, ODbL 1.0, https://opendatacommons.org/licenses/odbl/1-0/).

Not released: the imagery, the yard maps and their geometry, the measured haul paths; the site selection on the yard maps
(its results are `results/tables/sites/` and `results/tables/sites_multi/`, and `windport/shipyard.py` and
`windport/sim4.py` state the rules); the per-point caches of the runs (`points/`); the progress files, figure images and
comparison files of the runs; the batches that the report scripts read but the paper does not; and the scripts that typeset
the paper's text, tables and figures.

## License and citation

Code: MIT License (`LICENSE`). Data (the derived road networks in `data/networks/`, the parameter register in
`data/register/` and the result data in `results/`): Creative Commons Attribution 4.0 International, full legal text in
`LICENSE-data`. The OpenStreetMap extracts in `data/osm/`: © OpenStreetMap contributors, Open Data Commons Open Database
License 1.0. Copyright 2026 the authors. Please cite the paper (`CITATION.cff`).

Repository: https://github.com/NCR7777/windport-road-occupancy. On acceptance of the paper the accompanying version will be
archived in Zenodo; its DOI will be given here.
