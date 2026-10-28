# windport-road-occupancy

Code, data and results of the paper

> **Road occupancy in offshore wind monopile load-out: capacity bounds and fleet–infrastructure co-design**
> Chunrui Na, Qing Wang, Jingzheng Yao, Xiao Han, Yuntao Zhang, Kun Ma, Chengjing Song
> College of Shipbuilding Engineering, Harbin Engineering University; School of Civil and Environmental Engineering,
> Nanyang Technological University; Yantai Research Institute, Harbin Engineering University; College of Computer Science
> and Technology, Harbin Engineering University; Department of Electronics and Telecommunications, Politecnico di Torino.
> Manuscript submitted to *Ocean Engineering*.

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
python -m pytest tests            (192 tests, about 3 minutes; 18 are skipped, see RECOMPUTE.md)
```

OR-Tools (CP-SAT) 9.15.6755 is needed for the small-instance experiments and their tests; matplotlib only for the draft
figures that some report scripts draw next to their tables.

## Tables and figures of the paper

Every batch script builds its configuration, writes it to `results/windport_<stage>_<part>_<hash>/config.json` (the hash is
that of the configuration) and computes the points into that directory (`points/` holds one JSON per point and lets an
interrupted run resume; `points.csv` is the per-point table). `windport_revision_r1.py` and `windport_revision.py` write
the batches they rerun into `splice/<batch>/` subdirectories of their run directory, with the columns of the earlier
tables. The scripts accept `--procs N`; `--slots DIR` (optional) shares the machine with other jobs through a directory of
CPU slots, and without it an ordinary process pool is used. The released directories carry the names of `results/runs/`
and `results/tables/`, which are also the names the scripts read their inputs from (RECOMPUTE.md). Python 3.13.5
throughout; the solver column names where OR-Tools CP-SAT 9.15.6755 is used, everything else is simulation or closed-form
evaluation. The configuration of each item is the `config.json` of its run directories (`inputs.json` for report tables);
`results/MANIFEST.csv` gives, for every file, the place in the paper where it is used. Below, `hrep/` stands for
`tables/revision/hrep/` and `reports/` for `tables/revision/reports/after/`.

| Item | Result files (under `results/`) | Script and command | Solver |
|---|---|---|---|
| Table 3, base parameters and scenarios | `data/register/parameters.csv`; sensitivity ranges `runs/revision_r1_x/splice/extra_sens5/points.csv` | parameters in `windport/sim.py` (`BASE`), `occupancy/params.py`, `windport/archetypes.py`; `python experiments/windport_revision_r1.py --part x` | - |
| Table 4, haul paths of public load-out sites | `runs/survey/critical_points.csv`, `runs/survey/segments_public.csv`; `tables/revision/numbers.json`, `tables/revision/compat/numbers.json` | `python experiments/windport_survey.py` (needs the haul paths measured on imagery, not released); `python experiments/windport_revision_analytic.py`; `python experiments/windport_report_revision.py` | - |
| Table 5, two-level storage at the shipyards | `runs/detour/numbers.json`; inputs `runs/revision_bturn/turn_alt.json` | `python experiments/windport_detour.py` | - |
| Table 6, small instances: CP-SAT optima, W″ and simulation | `runs/revision_r1_e2/splice/e1e3_e2/points.csv`, `e1e3_e2/e2long/points.csv`; `hrep/recheck/rows.csv` | `python experiments/windport_revision_r1.py --part e2` (60 s per instance, 600 s for the instances only proven feasible; up to 4 threads) | CP-SAT |
| Table 7, crane limit and shortest port time, road-occupancy and fixed-time representations | `hrep/core.csv`, `core.md` | `python experiments/windport_revision_r1.py --part x` (`maingeom:core`); `python experiments/windport_report_revision.py` | - |
| Table 8, model elements removed in turn | `hrep/spatial/table_ablate.csv`, `hrep/spatial/numbers.json` | `python experiments/windport_revision_r1.py --part x` (`unified:ablate`); `python experiments/windport_report_revision.py` | - |
| Table 9, exchange rates | `tables/revision/compat/spatial/table7_rate.csv`, `tables/revision/compat/numbers.json`; `reports/e4_e7/table_e4_rate.csv` | `python experiments/windport_revision_r1.py --part x`; `python experiments/windport_revision.py --group a`; `python experiments/windport_report_revision.py` | - |
| Table 10, joint design | `runs/main2_codesign/codesign.csv`; `tables/revision/numbers.json` (`codesign`) | `python experiments/windport_main2_runs.py --part codesign`; `python experiments/windport_revision.py --group b`; `python experiments/windport_report_revision.py` | - |
| Table B.1, dimensions of the parametric layouts | `data/register/parameters.csv` | `windport/archetypes.py` (`DEFAULTS`, `GEOMETRIES`), `windport/main2.py` | - |
| Table B.2, replication of public cases | `tables/conservative/reports/after/extra/table_pub.md`, `tables/conservative/kassels.md` | `python experiments/windport_rerun_conservative.py --batch extra:pub`; `python experiments/windport_report_conservative.py` | - |
| Fig. 4, haul paths of public sites | `runs/survey/segments_public.csv`; `data/register/parameters.csv` (public sites) | as Table 4 | - |
| Fig. 5, critical single-lane length | `runs/revision_r1_ex/critical/critical.csv`; `reports/extra/table_critical.md`, `table_critical_check.csv`; `tables/spatial/table_critical_points.md` | `python experiments/windport_revision_r1.py --part ex` | - |
| Fig. 6, speed certificate | as Table 4 | as Table 4 | - |
| Fig. 7, two-level storage, near-buffer layouts | `runs/gode/numbers.json`; inputs `runs/revision_bturn/turn_alt.json`, `runs/design_turn/turn_alt.json` | `python experiments/windport_gode.py` | - |
| Fig. 8, regime map | `hrep/fig_regime_main.csv`, `hrep/regime.csv` | `python experiments/windport_revision_r1.py --part x,recheck`; `python experiments/windport_report_revision.py` | - |
| Fig. 9, W″ against the exact optima | `hrep/recheck/rows.csv`; `runs/revision_r1_e2/` | as Table 6; `python experiments/windport_revision_r1.py --part recheck` | CP-SAT |
| Fig. 10, port time of the two representations | `reports/e1_e3/fig3.csv`, `reports/e1_e3/table3.csv` | `python experiments/windport_revision_r1.py --part x`; `python experiments/windport_report_revision.py` | - |
| Fig. 11, fleet plateau | `reports/e4_e7/fig4.csv`, `table_e4_plateau.csv`; `hrep/recheck/rows.csv` | as Fig. 10 | - |
| Fig. 12, road changes on the long single lane | `reports/extra/table_cost.csv`, `table_cost.md`, `table_cost_best.csv` | as Fig. 10 | - |
| Supplementary Tables S1-S24, Figs. S1-S9 | `runs/w1_grid` (S1); `hrep/core.md` (S2, S3); `runs/revision_r1_ex/example`, `reports/extra/table_example.csv` (S4); `reports/extra/table6x.csv` (S5); `reports/extra/table_mixx*.csv` (S6); `runs/facts` (S7); `runs/detour`, `tables/sites`, `tables/sites_multi`, `hrep/spatial/table_sites.csv`, `table_siteport.csv` (S8, S9); `runs/revision_bmulti`, `tables/design/compat/yards.csv` (S10); `tables/design/screen.md`, `screen_kmin.csv`, `runs/design_turn`, `runs/spatial_turn_sweep` (S11, S12); `reports/extra/table_cost*` (S13); `tables/design/campaign.md`, `hrep/spatial/table_campaign.md` (S14); `reports/e4_e7/table_e7.csv`, `hrep/spatial/table_upsize.csv` (S15); `reports/e4_e7/tableC_e*.csv`, `reports/extra/tableC3x.csv`, `tableC4x.csv`, `runs/revision_r1_sens` (S16-S21); `hrep/core.csv` (S22); `runs/revision_r1_e2` (S23); `data/register/parameters.csv` (S24); `reports/e1_e3/fig2.csv` (Fig. S1); `hrep/fig_regime_main.csv` (Fig. S2); `hrep/recheck/rows.csv`, `reports/e4_e7/table_e4_plateau.csv` (Fig. S3); `runs/revision_r1_x/splice/runs_e4` (Fig. S4); `reports/e4_e7/table_e5.csv` (Fig. S5); `tables/design/compat/e_recheck_rows_part1.csv`, `_part2.csv`, `reports/e4_e7/fig6.csv` (Fig. S6); `hrep/spatial/table_upsize.csv` (Fig. S8); sensitivity tables (Fig. S9) | the scripts of the corresponding main items; RECOMPUTE.md | CP-SAT for S23 |
| Verification counts of the text (exhaustive checks, random regression, recheck of every simulated point) | `runs/theorems`, `runs/chain`, `runs/deadend_exact`, `runs/deadend_chain2`, `runs/conservative_exact`, `runs/random_bound`, `runs/random_lift_1`-`4`, `runs/main2_random_a`, `runs/main2_random_dead`, `runs/recheck`, `runs/w1_grid`, `runs/revision_r1_x/splice/`; `hrep/recheck/rows.csv`, `hrep/macros*.csv`, `hrep/geom_compat/` | RECOMPUTE.md | CP-SAT for the small instances |

`tables/revision/reports/after/e1_e3/`, `e4_e7/` and `extra/` are the report tables that `experiments/windport_report.py`,
`windport_report2.py` and `windport_report3.py` write when run on the `runs/revision_r1_*` batches
(`windport_report_revision.py` runs them); `tables/conservative/reports/after/extra/` the same for the conservative-rule
batches.

## Rerunning stored points

Every point is determined by its configuration (a layout or shipyard, parameters, fleet, cradles, windows); there is no
random seed outside the random regressions, whose cases are drawn from fixed seeds. For example, two rows of the E4 batch
on the main geometry (conservative lifting rule, cradle spacing 115 m):

```python
import csv, sys
sys.path[:0] = [".", "experiments"]
import windport_revision_r1 as R1
R1.install()                        # main geometry, conservative lifting rule, cradle spacing 115 m, as in the worker processes
batch = "runs:e4"
lines = open("results/runs/revision_r1_x/splice/runs_e4/points.csv", encoding="utf-8").read().splitlines()
cols = next(csv.reader([lines[0]]))
for line in (lines[1], lines[len(lines) // 2]):
    key = next(csv.DictReader([lines[0], line]))["key"]
    row = R1.rows_of(batch, key, R1.compute(batch, key))[0]
    print(key, R1.row_line(cols, row) == line)             # True: identical row
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
(`results/runs/spatial_turn_sweep/`, `results/runs/design_turn/`, `results/runs/revision_bturn/`,
`results/runs/revision_plans/`). Map lines delineate study areas and do not necessarily depict accepted national
boundaries.

The haul paths of the public load-out sites were measured on public satellite imagery (Esri World Imagery); their lengths,
widths and width classes are released without coordinates (`results/runs/survey/`, `data/register/parameters.csv`). The
imagery, the measured polylines and measurement lines and their coordinates are not released. The OpenStreetMap extracts of
`data/osm/` serve only as a comparison (© OpenStreetMap contributors, ODbL 1.0, https://opendatacommons.org/licenses/odbl/1-0/).

Not released: the imagery, the yard maps and their geometry (map JSON files), the measured haul paths (`haulpaths.json`)
and every polyline, measurement line or coordinate taken from the imagery; the site selection on the yard maps (its results
are `results/tables/sites/` and `results/tables/sites_multi/`, and `windport/shipyard.py` and `windport/sim4.py` state the
rules); the per-point caches of the runs (`points/`); the progress files, figure images and comparison files of the runs;
the batches that the report scripts read but the paper does not; and the scripts that typeset the paper's text, tables and
figures. Where a script needs one of these inputs, it reads the released result instead when the input is absent, or the
corresponding test is skipped (RECOMPUTE.md).

## License and citation

Code: MIT License (`LICENSE`). Data (the derived road networks in `data/networks/`, the parameter register in
`data/register/` and the result data in `results/`): Creative Commons Attribution 4.0 International, full legal text in
`LICENSE-data`. The OpenStreetMap extracts in `data/osm/`: © OpenStreetMap contributors, Open Data Commons Open Database
License 1.0. Copyright 2026 the authors. Please cite the paper (`CITATION.cff`).

Repository: https://github.com/NCR7777/windport-road-occupancy. On acceptance of the paper the accompanying version will be
archived in Zenodo; its DOI will be given here.
