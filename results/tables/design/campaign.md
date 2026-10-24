# Campaign model of Section 6.3: parameters (supplementary table) and recomputation

| Parameter | Value | Unit | Meaning |
|---|---|---|---|
| n_total | 60 | piles | total monopiles in the campaign (one vessel) |
| n_v | 3 / 10 | piles/voyage | piles loaded per voyage |
| voyages | 20 / 6 | voyages | ⌈n_total / n_v⌉ |
| T_port | E3 port time (table tab_e3: base / long single lane 1 km/h × K = 1, 2, pull-in S = 1) | h | port time per voyage: one set for the road-occupancy model and one for the fixed-duration representation |
| transit_h | 12.0 | h | one-way sailing (once out, once back; not affected by weather) |
| install_h | 24.0 | h/pile | installation time per pile, counted only in workable blocks, may accumulate across blocks |
| block_h | 6.0 | h | time step of the weather chain (one block) |
| q | 0.6 / 0.8 | — | stationary probability of a workable block (the working limit is expressed through q: workable = block with sea state below the installation limit; no measured sea states used) |
| spell_blocks | 4.0 | blocks | mean number of consecutive workable blocks (24 h) |
| P(W→W) | 0.75 | — | 1 − 1/spell_blocks |
| P(W→U) | 0.25 | — | 1/spell_blocks |
| P(U→U), q = 0.6 | 0.625 | — | max(0, 1 − q(1 − a)/(1 − q)), giving stationary probability q |
| P(U→W), q = 0.6 | 0.375 | — | unworkable spells last 2.67 blocks on average |
| π_W check, q = 0.6 | 0.6 | — | stationary probability of the two-state chain (1 − b)/((1 − a) + (1 − b)) |
| P(U→U), q = 0.8 | 0.0 | — | max(0, 1 − q(1 − a)/(1 − q)), giving stationary probability q |
| P(U→W), q = 0.8 | 1.0 | — | unworkable spells last 1.00 blocks on average |
| π_W check, q = 0.8 | 0.8 | — | stationary probability of the two-state chain (1 − b)/((1 − a) + (1 − b)) |
| Initial state | Bernoulli(q) | — | drawn independently for each seed |
| seeds | 1–200 | — | random.Random(seed); 20,000 blocks per seed |
| Difference | Σ seeds (road occupancy − fixed duration) / 200 | days | difference in campaign duration between the two representations on the same weather sequence (mean, P10, P90) |

## Recomputation (E3 port time from the rerun of e1e3:e3 on the main geometry; mean over 200 seeds, days)

| Scenario | n_v | K | q | Port h: road occupancy / fixed duration | Campaign days: road occupancy / fixed duration | Difference: mean (P10–P90) | Sum of port-time differences |
|---|---:|---:|---:|---|---|---|---:|
| base | 3 | 1 | 0.6 | 3.379 / 3.18 | 126.135 / 126.118 | 0.017 (0.0–0.033) | 0.166 |
| base | 3 | 1 | 0.8 | 3.379 / 3.18 | 98.072 / 97.98 | 0.092 (0.0–0.282) | 0.166 |
| base | 3 | 2 | 0.6 | 3.0 / 3.0 | 125.322 / 125.322 | 0.0 (0.0–0.0) | 0.0 |
| base | 3 | 2 | 0.8 | 3.0 / 3.0 | 97.521 / 97.521 | 0.0 (0.0–0.0) | 0.0 |
| base | 10 | 1 | 0.6 | 15.049 / 15.049 | 110.664 / 110.664 | 0.0 (0.0–0.0) | 0.0 |
| base | 10 | 1 | 0.8 | 15.049 / 15.049 | 84.826 / 84.826 | 0.0 (0.0–0.0) | 0.0 |
| base | 10 | 2 | 0.6 | 10.0 / 10.0 | 109.229 / 109.229 | 0.0 (0.0–0.0) | 0.0 |
| base | 10 | 2 | 0.8 | 10.0 / 10.0 | 83.54 / 83.54 | 0.0 (0.0–0.0) | 0.0 |
| lane | 3 | 1 | 0.6 | 5.232 / 4.898 | 127.11 / 127.051 | 0.06 (0.0–0.058) | 0.278 |
| lane | 3 | 1 | 0.8 | 5.232 / 4.898 | 99.579 / 99.349 | 0.23 (0.0–0.694) | 0.278 |
| lane | 3 | 2 | 0.6 | 4.151 / 3.0 | 126.673 / 125.322 | 1.351 (0.0–4.75) | 0.96 |
| lane | 3 | 2 | 0.8 | 4.151 / 3.0 | 98.716 / 97.521 | 1.195 (0.192–2.49) | 0.96 |
| lane | 10 | 1 | 0.6 | 28.908 / 28.908 | 113.877 / 113.877 | 0.0 (0.0–0.0) | 0.0 |
| lane | 10 | 1 | 0.8 | 28.908 / 28.908 | 88.353 / 88.353 | 0.0 (0.0–0.0) | 0.0 |
| lane | 10 | 2 | 0.6 | 20.047 / 15.241 | 111.882 / 110.675 | 1.207 (0.075–3.421) | 1.201 |
| lane | 10 | 2 | 0.8 | 20.047 / 15.241 | 86.068 / 84.851 | 1.218 (0.541–1.94) | 1.201 |

Long single lane, two vehicle sets, 10 piles per vessel: 1.21–1.22 days (manuscript macros \CampTenLo–\CampTenHi = 1.21–1.22). The second decimal depends on the seeds (seeds 1001–1200 give 1.253 / 1.196 days): the supplementary material states seeds 1–200, and the main text reports "about 1.2 days" with P10–P90.
