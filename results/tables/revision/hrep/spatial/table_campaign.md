# Campaign duration: one vessel, 60 monopiles, weather windows; port time in two representations

Each voyage = port time + 2 × 12 h sailing + 24 h installation per monopile (counted only in workable 6 h periods); weather is a two-state Markov chain (workable probability q, mean workable spell 24 h), seeds 1-200. Port time: road-occupancy model (first come, first served of experiment E3, pull-in, S = 1, Q_h = 0) against the fixed-duration representation (calibrated in the same scenario at K_ref = 1).

| Scenario | n_v | K | q | Port h: occupancy / fixed duration | Voyages | Campaign (days): occupancy / fixed duration | Difference: mean (10%-90%) | Port differences summed |
|---|---:|---:|---:|---|---:|---|---|---:|
| baseline | 3 | 1 | 0.6 | 3.379 / 3.18 | 20 | 126.135 / 126.118 | 0.017 (0.0-0.033) | 0.166 |
| baseline | 3 | 1 | 0.8 | 3.379 / 3.18 | 20 | 98.072 / 97.98 | 0.092 (0.0-0.282) | 0.166 |
| baseline | 3 | 2 | 0.6 | 3.0 / 3.0 | 20 | 125.322 / 125.322 | 0.0 (0.0-0.0) | 0.0 |
| baseline | 3 | 2 | 0.8 | 3.0 / 3.0 | 20 | 97.521 / 97.521 | 0.0 (0.0-0.0) | 0.0 |
| baseline | 10 | 1 | 0.6 | 15.049 / 15.049 | 6 | 110.664 / 110.664 | 0.0 (0.0-0.0) | 0.0 |
| baseline | 10 | 1 | 0.8 | 15.049 / 15.049 | 6 | 84.826 / 84.826 | 0.0 (0.0-0.0) | 0.0 |
| baseline | 10 | 2 | 0.6 | 10.0 / 10.0 | 6 | 109.229 / 109.229 | 0.0 (0.0-0.0) | 0.0 |
| baseline | 10 | 2 | 0.8 | 10.0 / 10.0 | 6 | 83.54 / 83.54 | 0.0 (0.0-0.0) | 0.0 |
| long single lane + 1 km/h | 3 | 1 | 0.6 | 5.232 / 4.898 | 20 | 127.11 / 127.051 | 0.06 (0.0-0.058) | 0.278 |
| long single lane + 1 km/h | 3 | 1 | 0.8 | 5.232 / 4.898 | 20 | 99.579 / 99.349 | 0.23 (0.0-0.694) | 0.278 |
| long single lane + 1 km/h | 3 | 2 | 0.6 | 4.151 / 3.0 | 20 | 126.673 / 125.322 | 1.351 (0.0-4.75) | 0.96 |
| long single lane + 1 km/h | 3 | 2 | 0.8 | 4.151 / 3.0 | 20 | 98.716 / 97.521 | 1.195 (0.192-2.49) | 0.96 |
| long single lane + 1 km/h | 10 | 1 | 0.6 | 28.908 / 28.908 | 6 | 113.877 / 113.877 | 0.0 (0.0-0.0) | 0.0 |
| long single lane + 1 km/h | 10 | 1 | 0.8 | 28.908 / 28.908 | 6 | 88.353 / 88.353 | 0.0 (0.0-0.0) | 0.0 |
| long single lane + 1 km/h | 10 | 2 | 0.6 | 20.047 / 15.241 | 6 | 111.882 / 110.675 | 1.207 (0.075-3.421) | 1.201 |
| long single lane + 1 km/h | 10 | 2 | 0.8 | 20.047 / 15.241 | 6 | 86.068 / 84.851 | 1.218 (0.541-1.94) | 1.201 |
