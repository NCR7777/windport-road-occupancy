# OpenStreetMap extracts of the public load-out sites

© OpenStreetMap contributors, ODbL 1.0. The files of this directory are extracts of OpenStreetMap
(https://www.openstreetmap.org/copyright), available under the Open Data Commons Open Database License (ODbL) 1.0,
https://opendatacommons.org/licenses/odbl/1-0/. They are not covered by the CC BY 4.0 licence of the other data of this
repository (LICENSE-data).

**They are a comparison only.** The haul paths of the public load-out sites that the paper uses (Table 4, Figs. 4 and 5) are
the paths from the storage area to the loading quay measured on public satellite imagery (Esri World Imagery);
`results/runs/survey/segments_public.csv` and `results/runs/survey/critical_points.csv` give their lengths, widths and
width classes without coordinates. The imagery, the measured polylines and their coordinates are not released. The
OpenStreetMap network serves only as a comparison: the shortest routes on it between the working area and the quay front
(`osm_route_min_m_comparison`, `osm_route_max_m_comparison` in the public-site entries of `data/register/parameters.csv`),
the junctions and turns on them and the width tags OpenStreetMap records; the register states for each site why the
OpenStreetMap route is not the actual haul path.

## Files

For each area (`eemshaven`, `fene`, `lindo`, `maasvlakte`, `nordenham`, `ronne`, `rostock`, `vlissingen`):

- `<area>.json`: the Overpass API response (`version`, `generator`, `osm3s` with the OpenStreetMap data timestamp,
  `elements`: ways, nodes and relations with their tags);
- `<area>.meta.json`: `endpoint`, the Overpass `query`, `fetched_utc` (time of the request), `osm_base` (timestamp of the
  OpenStreetMap data), `copyright`, `bbox` (the bounding box of the query, south, west, north, east in degrees).

All extracts were fetched on 23 October 2026 (`fetched_utc` 13:11-13:44 UTC) from https://overpass-api.de/api/interpreter.

As fetched, except: tags that hold contact addresses (`email`, `contact:email`, and any tag whose value is an e-mail
address) are removed, and so are the tags whose value contains the Dutch / German word for harbour (names of harbour
basins, port authorities and places; the port name Eemshaven is kept) or the word "exchange" (118 tags in total, 16 of them
contact tags); the
copyright note of the metadata is written in ASCII punctuation. Element ids, order and geometry and all other tags are
unchanged. The survey reads none of the removed tags: `windport.port_survey.survey` gives identical results for every site on
the extracts as fetched and as released.

## Use

`windport.port_survey.Data` reads an extract and `windport.port_survey.survey(D, spec)` computes the comparison for one
site; the areas and their specifications are `PORTS` of `experiments/windport_survey.py` (RECOMPUTE.md gives the loop).
`python experiments/windport_survey.py --fetch [AREA ...]` fetches the extracts again from the Overpass API (a new fetch
reflects the current OpenStreetMap data). The full script, which also writes `critical_points.csv` and
`segments_public.csv`, needs the haul paths measured on imagery, which are not released; the released tables are its result.
