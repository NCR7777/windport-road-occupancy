# windport-road-occupancy

Code, data and results of the paper

> **Road-occupancy capacity of offshore wind marshalling ports: transporter fleet, quayside staging and access-road
> co-design under load-out windows**
> Chunrui Na, Qing Wang, Xiao Han, Jingzheng Yao, Yuntao Zhang, Kun Ma, Chengjing Song
> College of Shipbuilding Engineering, Harbin Engineering University; School of Civil and Environmental Engineering,
> Nanyang Technological University; Yantai Research Institute, Harbin Engineering University; College of Computer Science
> and Technology, Harbin Engineering University; Department of Electronics and Telecommunications, Politecnico di Torino.
> Submitted to *Ocean Engineering*.

At an offshore wind marshalling port, self-propelled modular transporters (SPMT sets) carry monopiles from the storage area
to the quay, where the installation vessel's crane lifts them on board within a load-out window. The code models the port
roads, junctions, quay cradles and the RoRo ramp as resources that a loaded or empty set holds for load-dependent blocking
times; simulates the load-out (and the unloading of barges) on three parametric port layouts and on two shipyards used as
bases; computes the window bounds W and W′ on the monopiles delivered per window, the rule-free lower bound L*(n) on the
vessel's port time, and the critical single-lane length; and checks every simulated schedule with an independent checker,
the bounds by exhaustive enumeration and constraint programming (CP-SAT) on small instances.

The repository holds

- the code: the port simulation and its dispatching rules, the bounds, the small-instance enumeration and CP-SAT models, the
  independent checker, and the script of every experiment of the paper;
- the three parametric port layouts (Layouts 1-3 of the paper; `A1`-`A3` in the code), generated as synthetic instances by
  `windport/archetypes.py`;
- the road networks of the two shipyards (Okpo, Yantai) as derived graphs without coordinates (`data/networks/`);
- the full parameter register with the public source of every value (`data/register/parameters.csv`);
- the result data of every experiment (configurations, per-point tables, report tables), so that each reading can be
  checked without rerunning, and any stored point can be rerun and compared.

## Code

```
windport/             port model: layouts (archetypes.py), window bound W (bound.py), strengthened bound W′ (bound2.py),
                      return-route correction and L*(n) (bound3.py), simulation of load-out and unloading (sim.py), off-road
                      waiting area, convoy dispatch and W′ per point (sim2.py), the cut as one resource (sim3.py),
                      independent checkers (check.py, check2.py, check3.py), small-instance enumeration (exact.py,
                      exact_u.py, exact_chain.py), CP-SAT model (cpsat.py), shipyard sites on the derived graphs (shipyard.py)
occupancy/            road-occupancy model of block transport that the port model builds on: network and resources
                      (network.py), discrete-event simulation with full-path reservation (sim.py), tasks, bounds, defaults
bounds/, exact/       linear-programming helpers and the schedule checker of the occupancy model used by the port model
experiments/          the experiment scripts (table below), batch helpers (batch.py) and the report scripts
                      (windport_report.py, windport_report2.py, windport_report3.py) that compute the tables of results/tables/
tests/                pytest suite of the model, the bounds, the checkers and the experiment code
data/networks/        derived graphs of the two shipyards (README.md there)
data/register/        parameter register (README.md there)
results/              runs/ (one directory per batch), tables/ (report tables), MANIFEST.csv, README.md
RECOMPUTE.md          the command that recomputes each result directory, and the release check
requirements.txt      pinned package versions (Python 3.13.5)
environment.yml       conda environment with Python 3.13.5 and the packages of requirements.txt
LICENSE, LICENSE-data MIT (code), CC BY 4.0 (data)
CITATION.cff          how to cite
```

## Installation

Python 3.13.5 (64-bit).

```
python -m venv .venv
.venv\Scripts\activate            (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest tests            (78 tests, about 1.5 minutes)
```

OR-Tools (CP-SAT) is needed for the small-instance experiments (E2) and their tests; matplotlib only for the figures that the
report scripts draw next to their tables.

## Experiments

Every batch script builds its configuration, writes it to `results/windport_<part>_<hash>/config.json` (the hash is that of
the configuration) and computes the points into that directory (`points/` holds one JSON per point and lets an interrupted
run resume; `points.csv` is the per-point table). The scripts accept `--procs N`; `--slots DIR` (optional) shares the
machine with other jobs through a directory of CPU slots, and without it an ordinary process pool is used. The released
directories of `results/runs/` hold the configuration and the per-point table of each batch; their names are those of the
table below. Experiment labels E1-E7 are those of the code; the manuscript locations are in `results/MANIFEST.csv`.

| Experiment | Command | Released results | Manuscript |
|---|---|---|---|
| Exhaustive check of W on small instances | `python experiments/windport_w1_check.py` | `runs/w1_grid` | Table A.1; Section 3.1 |
| Exhaustive check of Theorems 3 and 4 | `python experiments/windport_thm.py` | `runs/theorems` | Section 3.3; Appendix A |
| E1: W against simulation, binding regimes | `python experiments/windport_sim.py --part e1` (`e1h`: gate holding places; `rel`: release time of direct lifts) | `runs/e1`, `runs/e1_hold`, `runs/release_time` | Figs. 3-4; Section 4.2 |
| E2: small instances, W / W′ / CP-SAT / simulation | `python experiments/windport_e2.py`, then `windport_e2long.py` (600 s for the instances only proven feasible); convoy dispatch: `windport_runs.py --part e2c` | `runs/e2`, `runs/e2_long`, `runs/e2_convoy` | Table 5; Section 4.3 |
| E3: fixed-time against road-occupancy representation | `python experiments/windport_sim.py --part e3`; added columns: `windport_extra.py --part port` and `--part fix` | `runs/e3`, `runs/port_time`, `runs/fixed_time` | Table 6; Fig. 5; Section 4.4 |
| E4: fleet plateau, cradles against sets | `python experiments/windport_runs.py --part e4`; mixed lifting: `windport_extra.py --part mix6`, `--part mixx` | `runs/e4`, `runs/mixed_e4`, `runs/mixed_release` | Table 7; Figs. 6-7; Section 4.5 |
| E5: overlap of unloading and load-out | `python experiments/windport_runs.py --part e5` | `runs/e5` | Fig. 8; Section 4.6 |
| E6: shipyards as marshalling bases | `python experiments/windport_runs.py --part e6` | `runs/e6`, `tables/sites`, `runs/facts` | Table 9; Fig. 11; Section 5 |
| E7: upsizing | `python experiments/windport_runs.py --part e7` | `runs/e7` | Fig. 9; Section 4.7 |
| Verification: off-road waiting area, convoy dispatch with gate holding places, cuts in series, random layouts, recheck of W′ | `windport_runs.py --part pocket`, `--part conv`; `windport_chain_check.py`; `windport_random.py`; `windport_random_lift.py`; `windport_recheck.py` | `runs/pocket`, `runs/convoy_hold`, `runs/chain`, `runs/random_bound`, `runs/random_lift_1`-`4`, `runs/recheck` | Section 4.8 |
| Sensitivity | `windport_runs.py --part sens`; `windport_sens_e7.py`; `windport_extra.py --part sens`; `windport_sens_e5.py` | `runs/sens`, `runs/sens_e7`, `runs/sens_extra`, `runs/sens_e5` | Fig. 10; Supplementary Tables S2-S7 |
| Worked example, critical single-lane length | `python experiments/windport_analytic.py --part example`, `--part critical` | `runs/example`, `runs/critical` | Table 3; Fig. 12; Section 6.1 |
| Public projects (Rønne, Eemshaven) | `python experiments/windport_extra.py --part pub` | `runs/public_projects` | Table B.2 |
| Report tables | `python experiments/windport_report.py`, `windport_report2.py`, `windport_report3.py` | `tables/e1_e3`, `tables/e4_e7`, `tables/extra` | Tables 3, 5-7, 9, 10; Figs. 3-12; Supplementary Tables |

The report scripts read the released per-point tables of `results/runs/` and write their tables into
`results/windport_report_<hash>/`, `results/windport_runs_report_<hash>/` and `results/windport_extra_report_<hash>/`.
`RECOMPUTE.md` gives the command for every result directory and the results of the release check.

## Rerunning stored points

Every point is determined by its configuration (a layout or shipyard, parameters, fleet, cradles, windows); there is no
random seed outside the random-layout regressions, whose cases are drawn from fixed seeds. The functions that compute one
point are `run_one` / `rows_of` of the batch scripts, for example

```python
import csv, sys
sys.path[:0] = [".", "experiments"]
import windport_runs as T
row = next(csv.DictReader(open("results/runs/e6/points.csv")))
new = T.row_of("e6", row["key"], T.run_one("e6", row["key"]))
print({k: (row[k], str(new.get(k, ""))) for k in T.COLS if row[k] != str(new.get(k, ""))})   # {} : identical
```

## Data sources and what is not released

The parameters come from published sources: project reports, manufacturers' data sheets, the Rønne case model of Kassels
(2023) and the literature; `data/register/parameters.csv` gives every value with its source, page, evidence class and how
much of the source was read. Entries not checked against the source text are not included in the register. The three port
layouts are synthetic.

The shipyard road networks were digitised from Google Earth imagery (Google Earth Pro; Okpo dated 15 November 2023: Google,
Airbus, TMap Mobility; Yantai dated 11 March 2025: Google, Airbus). Neither the imagery nor the centre-line geometry traced
from it is released: the networks are released as derived graphs (`data/networks/`), which hold everything the model uses.
Map lines delineate study areas and do not necessarily depict accepted national boundaries.

Not released: the imagery, the yard maps and their geometry; the site selection on the yard maps (its result is
`results/tables/sites/sites.json`, and `windport/shipyard.py` states the rules); the per-point caches of the runs
(`points/`); the progress files and figure images of the runs; the markdown versions of report tables whose data are in a
CSV of the same directory; and the scripts that typeset the paper's text, tables and figures.

## License and citation

Code: MIT License (`LICENSE`). Data (the derived road networks in `data/networks/`, the parameter register in
`data/register/` and the result data in `results/`): Creative Commons Attribution 4.0 International, full legal text in
`LICENSE-data`. Copyright 2026 the authors. Please cite the paper (`CITATION.cff`).

Repository: https://github.com/NCR7777/windport-road-occupancy. On acceptance of the paper the accompanying version will be
archived in Zenodo; its DOI will be given here.
