# Parameter register

`parameters.csv` is the full register of the public values behind the model parameters, the scenarios and the case data
of the paper: 152 entries in seven parts (`register_part`):

| Part | Entries | Content |
|---|---:|---|
| `main` | 85 | monopiles, SPMT, process and windows, costs and port data (the register of the first experiments) |
| `addendum: Ronne case model` | 7 | rates, fines, port times and load-out order of the Rønne case model (cost screen, replication of public cases) |
| `addendum: spatial additions` | 14 | crane reach, side-by-side cradles, alternative turns, reserved periods, storage areas, campaigns |
| `addendum: main geometry` | 3 | first cradle position, quay line and turning area of the parametric layouts |
| `addendum: main2 geometry` | 9 | rebuilt side-by-side cradle rows, crane radii and capacities |
| `addendum: design analyses` | 18 | cradle and SPMT costs, crane data of the installation vessels, two-level storage, alternative manoeuvres |
| `addendum: public sites` | 16 | public monopile load-out sites: haul path measured on imagery and the OpenStreetMap comparison |

Supplementary Table S21 of the paper lists the entries of the first two parts that enter the model (`manuscript_label` gives
their label there); Table 3 gives the base parameters with their evidence class; Table 4 and Figs. 4-5 use the public
sites. The other entries hold background values (project data, port requirements, values of published case models) that the paper
cites or compares with. Entries whose value was not checked against the source text are not included: two entries of the
research register taken from search-engine snippets of pages that could not be opened (in-port moves at Eemshaven, one in
the main register and one among the spatial additions) are left out.

| Column | Meaning |
|---|---|
| `parameter` | key of the entry |
| `value`, `unit` | the value as reported (several values separated by " / "), its unit; for the public sites the haul path length measured on imagery (empty where the site could not be located) |
| `description` | what the value describes |
| `evidence_class` | C, published project case; M, model assumption of a published case model; S, manufacturer specification; L, literature measurement or test; A, assumption of this study, varied in the sensitivity analysis (as in Table 3 of the paper); I, measured by this study on public satellite imagery (Esri World Imagery), OpenStreetMap values for comparison only |
| `source` | web address of the source, or the bibliographic reference; "this study (...)" for values set in the code |
| `reading_depth` | how much of the source was read: `full text` (articles, theses and reports read in full; web pages quoted from their body text); `abstract, introduction and conclusions` (articles read in these parts and the cited table or section only); `manufacturer material` (product pages, data sheets, equipment news); `online copy of the guideline (cited sections and tables)`; `data record`; `imagery measurement (this study)`; `not applicable (this study)` |
| `locator` | where in the source (page, section, table), with the quoted text where the source is English |
| `accessed` | access date of a web source (YYYY-MM-DD); for the public sites the date of the OpenStreetMap extract (data/osm/) |
| `status` | `known`, a single public value; `range`, several values or a bound; `scenario`, no direct public value, set as a range by this study; `not located` (public sites that could not be identified on the imagery); `not found` (no public value found) |
| `lower`, `upper` | range of the value where one is given |
| `transformation` | how the value is turned into a model parameter |
| `used_in` | where the value is used |
| `manuscript_label` | label of the entry in Supplementary Table S21 (empty: not in the table) |
| `register_part` | the part (above) |

The web sources of the first two parts were accessed on 21 October 2026; the addenda give their access dates in `accessed`.
In the public-site entries, the quotes that identify a site and its quay were taken through a web-fetch tool and are marked
"to be checked word for word"; the values of these entries (haul path lengths and widths) are measurements of this study on
the imagery.
