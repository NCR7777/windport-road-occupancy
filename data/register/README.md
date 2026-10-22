# Parameter register

`parameters.csv` is the full register of the public values behind the model parameters and the scenarios of the paper:
92 entries, the 85 of the main register followed by the 7 of the addendum (`register_part`). Table B.1 of the paper lists
the entries that enter the model (`manuscript_label` gives their label there); the other entries hold background values
(project data, port requirements, values of other models) that the paper cites or compares with, and do not enter the model.
Entries whose value was not checked against the source text are not included: one entry of the research register, taken
from a search-engine snippet of a page that could not be opened, is left out.

| Column | Meaning |
|---|---|
| `parameter` | key of the entry |
| `value`, `unit` | the value as reported (several values separated by " / "), its unit |
| `description` | what the value describes |
| `evidence_class` | C, published project case; M, model assumption of a published case model; S, manufacturer specification; L, literature measurement or test; A, assumption of this study, varied in the sensitivity analysis (as in Table 4 of the paper) |
| `source` | web address of the source, or the bibliographic reference |
| `reading_depth` | how much of the source was read: `full text` (articles, theses and reports read in full; web pages quoted from their body text); `abstract, introduction and conclusions` (articles read in these parts and the cited table or section only); `manufacturer material` (product pages, data sheets, equipment news); `online copy of the guideline (cited sections and tables)`; `data record`; `not applicable (this study)` |
| `locator` | where in the source (page, section, table), with the quoted text where the source is English |
| `status` | `known`, a single public value; `range`, several values or a bound; `scenario`, no direct public value, set as a range by this study |
| `lower`, `upper` | range of the value where one is given |
| `transformation` | how the value is turned into a model parameter |
| `used_in` | where the value is used |
| `manuscript_label` | label of the entry in Table B.1 (empty: not in the table) |
| `register_part` | `main` or `addendum` (values of the Rønne case model used for the cost screen and the public-project replication) |

Web sources were accessed on 21 October 2026.
