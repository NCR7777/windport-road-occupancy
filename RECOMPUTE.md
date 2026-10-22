# Recomputing the results

For each directory of `results/`, the command that recomputes it from the code, the synthetic layouts
(`windport/archetypes.py`), the derived graphs of the shipyards (`data/networks/`) and the parameters (`windport/sim.py`
`BASE`, `occupancy/params.py` `DEFAULTS`, and the scenarios and grids of each script). A batch script writes into
`results/windport_<part>_<hash>/`, where the hash is that of its configuration; the released configurations differ from the
ones the scripts write only in the fields named in `results/README.md` (code hashes, run label, text), so the hash and hence
the directory name differ from the released name. `points/` caches the finished points, so an interrupted run resumes.

## Commands

| Released directory | Command |
|---|---|
| `runs/w1_grid` | `python experiments/windport_w1_check.py` |
| `runs/theorems` | `python experiments/windport_thm.py` |
| `runs/e1`, `runs/e1_hold`, `runs/release_time`, `runs/e3` | `python experiments/windport_sim.py --part e1` (`e1h`, `rel`, `e3`) |
| `runs/e2` | `python experiments/windport_e2.py` (CP-SAT, 60 s per instance, up to 8 threads) |
| `runs/e2_long` | `python experiments/windport_e2long.py` (reads `results/runs/e2/points.csv`; 600 s per instance) |
| `runs/e4`, `runs/e5`, `runs/e6`, `runs/e7`, `runs/pocket`, `runs/convoy_hold`, `runs/e2_convoy`, `runs/sens` | `python experiments/windport_runs.py --part e4` (`e5`, `e6`, `e7`, `pocket`, `conv`, `e2c`, `sens`) |
| `runs/sens_e7` | `python experiments/windport_sens_e7.py` |
| `runs/chain` | `python experiments/windport_chain_check.py` |
| `runs/random_bound` | `python experiments/windport_random.py --n 20000 --start 0` |
| `runs/random_lift_1`, `_2`, `_3`, `_4` | `python experiments/windport_random_lift.py --gen main --n 10000 --start 0`; `--gen main --n 10000 --start 10000`; `--gen port --n 10000`; `--gen hold --n 4000` |
| `runs/port_time`, `runs/fixed_time`, `runs/mixed_e4`, `runs/mixed_release`, `runs/sens_extra`, `runs/public_projects` | `python experiments/windport_extra.py --part port` (`fix`, `mix6`, `mixx`, `sens`, `pub`) |
| `runs/sens_e5` | `python experiments/windport_sens_e5.py` |
| `runs/example`, `runs/critical` | `python experiments/windport_analytic.py --part example` (`critical`) |
| `runs/facts` | `python experiments/windport_facts.py` (the largest bend inside a road of the shipyard routes, `max_bend_in_road_deg`, needs the map geometry: on the derived graphs it is `null`; the released file holds the values computed on the maps) |
| `runs/recheck` | `python experiments/windport_recheck.py` (reads the released per-point tables) |
| `tables/e1_e3` | `python experiments/windport_report.py` (reads `runs/e1`, `e1_hold`, `release_time`, `e2`, `e2_long`, `e3`, `theorems`, `w1_grid`) |
| `tables/e4_e7` | `python experiments/windport_report2.py` (reads the runs named in its `inputs.json`) |
| `tables/extra` | `python experiments/windport_report3.py` (reads the runs named in its `inputs.json` and the parameter register) |
| `tables/sites` | the site selection on the yard maps (not released); the rules are stated in `windport/shipyard.py` |

The batches ran on 22-23 worker processes in a few minutes each (E2: 0.4 h, CP-SAT); the exhaustive checks and the analytic
parts take seconds to minutes on one process.

## Release check

The repository was checked from a fresh copy of the files it publishes, with Python 3.13.5 and the package versions of
`requirements.txt` (numpy 2.1.3, scipy 1.15.3, ortools 9.15.6755, matplotlib 3.10.0, psutil 7.2.2, pytest 8.3.4). The check
used an existing virtual environment with exactly these versions instead of a new `pip install -r requirements.txt`.

**Tests.** `python -m pytest tests`: 78 passed (81 s).

**Shipyard networks.** For Okpo and Yantai, each with roadside and pull-in cradles, the network that the simulation builds
from the derived graph equals the one it builds from the yard map in every road (length, width), arc, permitted movement,
turn angle of every movement (2,814 at Okpo, 490 at Yantai; equal as floating-point numbers), stop, entity, node resource
and capacity.

**Stored points rerun with the released code and data** (every column of the stored row compared):

| Batch | Points rerun | Differing |
|---|---|---|
| `runs/e6` (shipyards, from the derived graphs) | all 5,376 | 0 |
| `runs/e1` | 600 drawn at random (seed 1) of 31,680 | 0 |
| `runs/port_time`, rows with 10 monopiles, no gate holding place, first-come-first-served (the occupancy column of Table 6 and the cost table) | all 400 | 0 |
| `runs/e2`: simulation, W, binding term, candidate count, checker | all 540 | 0 |
| `runs/e2`: CP-SAT (60 s) on instances proven optimal | 6 drawn at random | 0 (same optimum, OPTIMAL, checker passes) |

**Recomputed files.** `windport_analytic.py --part example` and `--part critical` give `example.csv` and `critical.csv` byte
for byte equal to `runs/example` and `runs/critical`. The three report scripts, run on the released per-point tables, give
all 34 CSV tables of `tables/e1_e3`, `tables/e4_e7` and `tables/extra` byte for byte (their `inputs.json` differ only in line
ends and key order; the markdown reports are English translations of the committed ones and are written afresh).
`windport_recheck.py`, run on the released per-point tables, gives `summary.csv`, `changed.csv`, `e2.csv` and `e6.csv` of
`runs/recheck` byte for byte. The internal run labels of the committed files were renamed (`results/README.md`, `export`);
apart from these labels the renamed files hold the committed values row for row (`tables/e4_e7/table_pocket.csv`: column
names only; `runs/recheck/summary.csv`: batch labels, and its rows re-sorted by them).
`windport_facts.py` gives `runs/facts/facts.json` except the in-road bends of the shipyard routes (above) and the wording of
two notes.

**Key numbers of the manuscript recomputed** from these files with the manuscript's definitions, each equal to the number
printed in the manuscript (92 numbers):

| Item | Numbers (manuscript value = recomputed value) |
|---|---|
| Table 3, worked example | K† 6.46 (base, pull-in), 2.63 (base, roadside), 1.88 (long single lane); t_ℓ 2,102 s (roadside); cut 200 m (lane block) and 1,200 m (single lane); long single lane with two sets: W′ = 9, simulation 6; all 3 + 6 table lines equal |
| E1 summary (Section 4.2) | 31,680 points, W attained in 73.4 %; 17,280 points with gate holding places; attained by layout, base: 96.7 % / 97.1 % / 95.4 %; long single lane 38.5 % (Layout 1), 59.4 % (Layout 2); crane 0.5 h 25.8 % (roadside), 44.2 % (pull-in); regimes of Layout 1 (1,152 points per cell): base 1,026 / 66 / 60 (89 % interface-limited), long single lane 442 / 212 / 498 (43 % flow-limited; cut binding in 200), crane 0.5 h 774 / 199 / 179; gate holding places 3,187 / 3,527 / 3,824 / 4,168 monopiles for Q_h = 0, 1, 2, unlimited (+31 %); release time of direct lifts 10 / 9 / 7 / 6 against 8 with one cradle |
| E2, Table 5 | 540 instances, 533 proven optimal; optimum = W in 353, = W′ in 388; Σ(W − optimum) 228, Σ(W′ − optimum) 171; CP-SAT above simulation by 18 monopiles (17 instances), above convoy dispatch by 10; 524 optima equal to convoy dispatch, 518 to first-come-first-served; long corridor 31 / 13 (roadside) and 28 / 12 (pull-in); 17 instances rerun with 600 s, 10 proven; all 21 table lines equal |
| E3, Table 6 | occupancy column (fcfs port time of 10 monopiles): all 30 rows equal; port time 18.42 h against 10.0 h with fixed times (+84 %); with gate holding places 11.23 h (long corridor) and 14.27 h (long single lane); crane 0.5 h: 7.71 h against 5.73-7.31 h; fixed-time plateau at K = 3-8; 1 km/h 10.74 h; fixed times at three sets 10.02 h, 46 % below |
| Cost, Table 10 | all 9 table lines equal; second set saves 4.20 h (base) and 8.86 h (long accesses) per voyage of ten, 24,490 / 51,694 EUR at 140,000 EUR/day and 43,732 / 92,311 EUR at 250,000 EUR/day, 3.4 / 7.2 and 6.1 / 12.8 hire days; with three monopiles 0.07 h, 430 EUR |
| Critical single-lane length (Fig. 12) | 632 m (any dispatch) and 278 m (one set in the quay zone) at 1 km/h, 1,466 m and 682 m at 2.5 km/h (crane 1 h); check of 18 rows: 7 cut-limited, quay-zone criterion agrees in 16; τ/p 1.68 (long single lane) and 0.24 (base) |
