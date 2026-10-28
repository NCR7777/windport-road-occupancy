# Recomputing the results

The results come from the code of this repository, the synthetic layouts (`windport/archetypes.py`, `windport/main2.py`),
the derived graphs of the shipyards (`data/networks/`), the turn analyses on the yard maps (released as results), the
parameters (`windport/sim.py` `BASE`, `occupancy/params.py` `DEFAULTS`, and the scenarios and grids of each script) and the
public-site data (`results/runs/survey/`, `data/osm/`).

A batch script writes `results/windport_<stage>_<part>_<hash>/`, where the hash is that of its configuration. The released
configurations differ from the ones the scripts write in the fields named in `results/README.md` (code and input hashes,
run label, text), so the hash and hence the directory name differ from the released name. The scripts read their inputs
from the released names (`results/runs/<stage>_<part>/`, `results/tables/<stage>/`); to use a recomputed directory as an
input, copy or rename it to that name. `points/` caches the finished points, so an interrupted run resumes.

## Order of the stages

Each stage reruns or extends the batches of the previous ones; the report script of a stage reads the batches named in its
`inputs.json` and writes `results/windport_<stage>_report_<hash>/`. The commands give the arguments of the released runs
(`--procs N` and `--slots DIR` as convenient).

| Stage | Commands, in order |
|---|---|
| E1-E7 and the extra analyses (first geometry, original lifting rule) | `windport_w1_check.py`; `windport_thm.py`; `windport_sim.py --part e1` (`e1h`, `rel`, `e3`); `windport_e2.py`; `windport_e2long.py`; `windport_runs.py --part e4` (`e5`, `e6`, `e7`, `pocket`, `conv`, `e2c`, `sens`); `windport_sens_e7.py`; `windport_chain_check.py`; `windport_random.py --n 20000 --start 0`; `windport_extra.py --part port` (`fix`, `mix6`, `mixx`, `sens`, `pub`); `windport_sens_e5.py`; `windport_analytic.py --part example` (`critical`); `windport_facts.py`; `windport_random_lift.py --gen main --n 10000 --start 0` (`--start 10000`; `--gen port --n 10000`; `--gen hold --n 4000`); `windport_recheck.py`; reports `windport_report.py`, `windport_report2.py`, `windport_report3.py` |
| Spatial additions (crane reach, cradle rows, alternative turns, reserved periods) | `windport_turn_sweep.py` (yard maps, see below); `windport_spatial.py --part sites` (`siteport`, `hphd`, `reach`, `upsize`, `turn`, `reserve`, `ablate`, `cdv`); `windport_spatial_analytic.py --part regime5` (`critical`, `codesign`, `campaign`); `windport_random_spatial.py --start 0 --n 24000`; `windport_report_spatial.py` |
| Dead-end coupling (W″) | `windport_deadend.py --part port` (`exact`, `chain2`, `strat`); `windport_deadend_ext.py --part tail` (`random`, `port`); `windport_deadend_cpsat.py --shard 0 --of 3` (shards 1, 2); `windport_random_deadend.py --gen dead --start 0 --n 12000`; `windport_recheck_deadend.py` |
| Conservative lifting rule | `windport_rerun_conservative.py --batch all`; `windport_e2_conservative.py`; `windport_exact_conservative.py --chunk 4`; `windport_sens_conservative.py`; `windport_span.py`; `windport_xscan.py`; `windport_random_conservative.py --gen dead --n 30000`; `windport_recheck_conservative.py`; `windport_report_conservative.py` |
| Unified bound | `windport_rerun_spatial.py --part all`; `windport_random_unified.py --gen a --start 24000 --n 12000` (`--gen dead`); `windport_recheck_unified.py`; `windport_report_unified.py` |
| Main geometry (first cradle 170 m) | `windport_maingeom.py --part rerun` (`e2`, `spatial`, `core`, `span`, `xscan`, `yards`, `codesign`, `cdv`, `geom`, `example`, `critical`); `windport_sens_maingeom.py`; `windport_random_maingeom.py --gen a --start 48000 --n 12000` (`--gen dead`); `windport_recheck_maingeom.py`; `windport_report_maingeom.py` |
| Main2 geometry (rebuilt cradle rows, ramp in line with the apron) | `windport_main2_runs.py --part geom` (`splice`, `core`, `reachdist`, `codesign`, `cdv`, `sample`); `windport_random_main2.py --gen a --start 72000 --n 12000`; `windport_random_main2.py --gen dead --start 84000 --n 12000`; `windport_recheck_main2.py`; `windport_report_main2.py` |
| Design analyses (shipyards with alternative turns, two-level storage, joint design, site screen) | `windport_turn_alt_clear.py` (yard maps, see below); `windport_design.py --part e6:lo,e6:hi` (`yards`, `near`, `transfer`, `codesign`); `windport_design_analytic.py`; `windport_codesign_blocks.py`; `windport_codesign_blocks2.py`; `windport_codesign_finish.py`; `windport_rows_exclusion.py --part rowsx,spacing` (`turnwin`, `tr10`); `windport_rows_finish.py`; `windport_report_design.py` |
| Public load-out sites | `windport_survey.py` (haul paths measured on imagery, see below) |
| Revision (cradle spacing 115 m; buffers and two-level storage at the shipyards; joint design) | `windport_revision_r1.py --part x` (`sens`, `e2`, `ex`, `inv`); `windport_revision_r1.py --part recheck`; `windport_revision.py --group a`; `windport_revision.py --group b`; `windport_revision.py --group c` (computes the buffer layouts and runs `bturn` first; yard maps, see below); `windport_gode.py`; `windport_detour.py`; `windport_revision_analytic.py`; `windport_revision_avgcrab.py`; `windport_revision_r1_rated.py`; `windport_revision_r1inv2.py`; `windport_revision_r1rc.py --part main` (`e2`); `windport_report_revision.py` |

All commands are `python experiments/<script> ...` from the repository root. The simulation batches are written for many
worker processes (the released runs used 4-23); the exhaustive checks and the analytic parts run on one process.

## Released directories

| Released directory | Command |
|---|---|
| `runs/w1_grid`, `runs/theorems`, `runs/chain`, `runs/random_bound`, `runs/random_lift_1`-`4`, `runs/facts`, `runs/recheck` | first stage (above) |
| `runs/deadend_exact`, `runs/deadend_chain2` | `windport_deadend.py --part exact`, `--part chain2` |
| `runs/conservative_exact` | `windport_exact_conservative.py --chunk 4` |
| `runs/revision_r1_x` | `windport_revision_r1.py --part x` (the batches of the earlier stages rerun at cradle spacing 115 m, in `splice/<batch>/`) |
| `runs/revision_r1_e2` | `windport_revision_r1.py --part e2` (CP-SAT, 60 s per instance and 600 s for the instances only proven feasible, up to 4 threads per instance) |
| `runs/revision_r1_ex`, `runs/revision_r1_sens` | `windport_revision_r1.py --part ex`, `--part sens` |
| `runs/revision_plans`, `runs/revision_bturn`, `runs/revision_bmulti` | `windport_revision.py --group c` (the buffer layouts and the turn check of `bturn` need the yard maps; with the released `revision_plans` and `revision_bturn`, `--group c --part bmulti` runs without them) |
| `runs/gode`, `runs/detour` | `windport_gode.py`, `windport_detour.py` (after `windport_revision.py --group c`) |
| `runs/main2_codesign` | `windport_main2_runs.py --part codesign` (after `windport_maingeom.py --part codesign`) |
| `runs/main2_random_a`, `runs/main2_random_dead` | `windport_random_main2.py --gen a --start 72000 --n 12000`; `--gen dead --start 84000 --n 12000` |
| `runs/design_e6_hi` | `windport_design.py --part e6:hi` |
| `runs/design_turn` | `windport_turn_alt_clear.py` (yard maps) |
| `runs/spatial_turn_sweep` | `windport_turn_sweep.py` (yard maps) |
| `runs/survey` | `windport_survey.py` (imagery haul paths) |
| `tables/spatial`, `tables/conservative`, `tables/design` | `windport_report_spatial.py`, `windport_report_conservative.py`, `windport_report_design.py` |
| `tables/revision` | `windport_report_revision.py` (reads the batches of the revision stage named in its `inputs.json`) |
| `tables/sites`, `tables/sites_multi` | site selection on the yard maps (not released); the rules are stated in `windport/shipyard.py` and `windport/sim4.py` |

## What needs data that is not released

- **Yard maps.** The site selection, the sweep check of the turns (`windport_turn_sweep.py`), the search for
  alternative manoeuvres (`windport_turn_alt_clear.py`, `windport_design.py --part turn`, `windport_revision.py --group c
  --part bturn`) and the buffer layouts (`windport_revision_buffer.py`) read the polygons of the yard maps. Their results are
  released (`tables/sites`, `tables/sites_multi`, `runs/spatial_turn_sweep`, `runs/design_turn`, `runs/revision_bturn`,
  `runs/revision_plans`), and every simulation of the shipyards runs on the derived graphs with them.
- **Haul paths measured on imagery.** `windport_survey.py` and the split-site part of `windport_design_analytic.py` read
  them; the released `runs/survey/critical_points.csv` and `segments_public.csv` are their result. The OpenStreetMap
  comparison alone is recomputed from `data/osm/` with

  ```python
  import json, sys
  sys.path[:0] = [".", "experiments"]
  from windport import port_survey as PS
  import windport_survey as S
  for p in S.PORTS:
      if p.get("area"):
          meta = json.load(open(f"data/osm/{p['osm']}.meta.json", encoding="utf-8"))
          D = PS.Data(json.load(open(f"data/osm/{p['osm']}.json", encoding="utf-8")), meta["bbox"])
          r = PS.survey(D, dict(area=[tuple(a) for a in p["area"]], start_name=p.get("start_name")))
          print(p["key"], r.get("route_min_m"), r.get("route_max_m"))
  ```
- **Batches the paper does not read.** The report scripts read run directories of their stage that are not released
  (`inputs.json` names them); recompute them with the commands of their stage first.
- **Manuscript sources.** The `numbers` steps of `windport_report_conservative.py`, `windport_report_maingeom.py`,
  `windport_report_main2.py`, `windport_report_design.py` and `windport_report_revision.py` rerun the scripts that typeset the paper's numbers (expected
  in `paper/`, not released) on the new run directories; the report tables do not depend on them.

## Release check

The repository was checked from the files it publishes, with Python 3.13.5 and the package versions of
`requirements.txt` (numpy 2.1.3, scipy 1.15.3, ortools 9.15.6755, matplotlib 3.10.0, psutil 7.2.2, pytest 8.3.4), in an
existing virtual environment with exactly these versions instead of a new `pip install -r requirements.txt`. No result was
recomputed from scratch for this release.

**Code hash.** The results record the hash of `windport/sim*.py` before a later change that only moves the temporary map
files into the cache directory and leaves the computation unchanged: rerunning a batch with the released code gives
byte-identical results.

**Tests.** `python -m pytest tests`: 192 tests, 174 passed, 18 skipped. The skipped tests compare with inputs that are not
released: run directories of the research batches that the paper does not read, the code of an earlier commit, the site
selection on the yard maps, the haul paths measured on imagery, and the results of `windport_design_analytic.py` (run it
first to include that test).

**Shipyard networks.** For Okpo and Yantai the network that the simulation builds from the derived graph equals the one the
code builds from the yard map in every road (length, width, chainage), arc, permitted movement, turn angle (equal as
floating-point numbers), stop, entity, node resource and capacity, for the ten networks the paper uses: one-voyage and
three-voyage storage, each with roadside and pull-in cradles, and the two-level transfer.

**OpenStreetMap extracts.** `windport.port_survey.survey` gives identical results for all seven sites on the extracts as
fetched and as released (data/osm/README.md).

**Release checker** (local paths, e-mail addresses, internal names, imagery and coordinates, file sizes, manifest,
licences): no finding.

The records of reruns in the earlier versions of this file refer to result files of the earlier versions of the paper,
which this version replaces; they are not repeated here (see commits 74bff4d and b633f46 of this repository).
