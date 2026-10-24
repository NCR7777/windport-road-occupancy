# Two-level storage (campaign storage in the far yard → transfer of one voyage of 10 piles to the near yard between voyages → load-out window from the near yard)

Near yard = the one-voyage storage area of the E4-E7 batches (Okpo zone_trace_027 2.2 ha, route 282.7 m; Yantai zone_trace_003); far yard = the three-voyage storage area (Okpo zone_trace_001 6.82 ha, 2,865 m; Yantai zone_trace_030 5.04 ha). Transfer network: road-adjacent segments of the far yard → pull-in set-down positions at the midpoints of the road-adjacent segments of the near yard (set-down h_d unchanged).

## 1.1 Window port time under the two storage layouts (10 piles per vessel, base, cradle S = 1, Q_h = 0, crane open from G = 24 h; shortest over K = 2–8, L″_lift* in parentheses)

| Shipyard | Cradle | Single level (direct loading from the three-voyage storage area): all feasible / lo / hi | Two level (loading from the near yard): all feasible / lo / hi |
|---|---|---|---|
| Okpo | roadside | 20.42 (14.38) / 20.42 (14.38) / 22.14 (14.38) | 10.00 (10.00) / 10.00 (10.00) / 10.00 (10.00) |
| Okpo | pull-in | 20.42 (14.38) / 20.42 (14.38) / 22.14 (14.38) | 10.00 (10.00) / 10.00 (10.00) / 10.00 (10.00) |
| Yantai | roadside | 10.90 (10.00) / 10.90 (10.00) / 15.19 (10.00) | 10.00 (10.00) / 10.00 (10.00) / 10.00 (10.00) |
| Yantai | pull-in | 10.90 (10.00) / 10.90 (10.00) / 15.19 (10.00) | 10.00 (10.00) / 10.00 (10.00) / 10.00 (10.00) |

### Near-yard window port time vs K (G = 24 h, cradle S = 1; written once where the two cradle types coincide)

| Shipyard | Scenario | Turning | K = 1 | 2 | 3 | 4 | Smallest K returning to 10.00 h |
|---|---|---|---|---|---|---|---:|
| Okpo | base (2.5 km/h) | feas | 12.78 | 10.00 | 10.00 | 10.00 | 2 |
| Okpo | base (2.5 km/h) | hi | 14.57 | 10.00 | 10.00 | 10.00 | 2 |
| Okpo | 1 km/h | feas | 15.75 | 10.05 | 10.00 | 10.00 | 3 |
| Okpo | 1 km/h | hi | 17.73 | 11.41 | 10.00 | 10.00 | 3 |
| Yantai | base (2.5 km/h) | feas | 12.42 | 10.00 | 10.00 | 10.00 | 2 |
| Yantai | base (2.5 km/h) | hi | 13.74 | 10.22 | 10.00 | 10.00 | 3 |
| Yantai | 1 km/h | feas | 14.96 | 10.35 | 10.00 | 10.00 | 3 |
| Yantai | 1 km/h | hi | 16.27 | 11.18 | 10.00 | 10.00 | 3 |

## 1.2 Shortest voyage cycle T_min the far route can support (h; n_v = 10 piles per voyage; K = number of vehicle sets shared by transfer and loading, S = number of quay cradles)

Three quantities: **T_rate** = n_v / r, r = min(K/c, 1/(t_ℓ + t_e)), the long-run rate bound of the far → near transfer (Corollary 1: any dispatch, transfer and loading may overlap, long-run average; c is taken with all turns feasible, which for hi is a weaker necessary condition and still holds); **T_seq\*** = L″*_transfer(10) + return + L″*_window⁰(10) (rule-free lower bound of the sequential policy: first transfer all 10 piles, after that window ends the vehicle sets return empty to the far-yard side, then loading starts from an empty system; both stages use the set-up term of Theorem 2, and the return is a deterministic empty trip); **T_seq** = the same sequential policy in first-come-first-served simulation (set-down time of the 10th transferred pile + return + near-yard window from an empty system until the 10th pile is lifted). Return = shortest empty path from the quay gate to the far-yard waiting area: Okpo 2,865.5 m (0.573 h), Yantai 1,755.5 m (0.351 h), empty speed 5 km/h. Turning taken as hi (main case), all turns feasible in parentheses.

| Shipyard | Scenario | Lifting | K = 1 | 2 | 3 | 4 | 6 | 8 |
|---|---|---|---|---|---|---|---|---|
| Okpo | base (2.5 km/h) | S1 | 26.3 / 41.5 / **48.4** (43.4) | 13.1 / 24.3 / **34.2** (30.2) | 8.8 / 21.5 / **29.8** (25.8) | 6.6 / 18.6 / **27.4** (22.2) | 4.4 / 15.8 / **25.1** (22.1) | 3.3 / 15.8 / **25.1** (22.1) |
| Okpo | base (2.5 km/h) | S3 | 26.3 / 40.9 / **47.8** (42.8) | 13.1 / 24.3 / **33.9** (30.1) | 8.8 / 21.5 / **29.7** (25.7) | 6.6 / 18.6 / **27.4** (22.1) | 4.4 / 15.8 / **25.1** (22.1) | 3.3 / 15.8 / **25.1** (22.1) |
| Okpo | 1 km/h | S1 | 42.3 / 60.3 / **70.9** (64.9) | 21.2 / 32.7 / **55.2** (50.4) | 14.1 / 28.2 / **53.6** (49.9) | 10.6 / 23.7 / **53.0** (49.9) | 7.1 / 19.2 / **49.0** (49.9) | 5.3 / 19.2 / **49.0** (49.9) |
| Okpo | 1 km/h | S3 | 42.3 / 59.0 / **69.5** (63.6) | 21.2 / 32.7 / **54.0** (49.7) | 14.1 / 28.2 / **53.2** (49.7) | 10.6 / 23.7 / **52.9** (49.7) | 7.1 / 19.2 / **48.9** (49.7) | 5.3 / 19.2 / **48.9** (49.7) |
| Yantai | base (2.5 km/h) | S1 | 20.7 / 38.7 / **43.2** (35.9) | 10.4 / 23.2 / **32.2** (23.6) | 6.9 / 20.6 / **25.9** (21.4) | 5.2 / 18.0 / **25.9** (21.4) | 3.5 / 16.5 / **25.9** (20.2) | 2.7 / 16.5 / **25.9** (20.2) |
| Yantai | 1 km/h | S1 | 30.9 / 51.1 / **57.7** (49.6) | 15.5 / 28.7 / **44.0** (31.7) | 10.3 / 25.0 / **32.9** (28.7) | 7.7 / 21.3 / **32.9** (28.7) | 5.5 / 20.1 / **32.9** (28.7) | 5.5 / 20.1 / **32.9** (28.7) |

Each cell: T_rate / T_seq\* / **T_seq** (all turns feasible).

## 1.3 Criterion (each of the two conditions stated once): for a voyage cycle T ≥ T_seq(K, S), sequential transfer stays out of the window, the load-out window is the near-yard window, and the far route constrains only the transfer between voyages; for the window to return to the crane floor of 10.00 h, K must also be large enough ("smallest K returning to 10.00 h" in the table above). For T < T_rate(K) no dispatch can refill the near yard, and the road enters the window

Table below: for each voyage cycle, the smallest number of vehicle sets K for which the sequential policy is feasible (T ≥ T_seq) (S = 1, turning hi; recorded as > 8 when K ≤ 8 is not enough), and the K with T < T_rate (road necessarily enters the window). This is only the transfer condition; for the window to be crane-limited, K must also be at least the smallest K of the table above.

| Shipyard | Scenario | T = 12 h | T = 24 h | T = 36 h | T = 48 h | T = 72 h | T = 96 h | T = 144 h |
|---|---|---|---|---|---|---|---|---|
| Okpo | base (2.5 km/h) | > 8; road enters window for K ≤ 2 | > 8; road enters window for K ≤ 1 | K ≥ 2 | K ≥ 2 | K ≥ 1 | K ≥ 1 | K ≥ 1 |
| Okpo | 1 km/h | > 8; road enters window for K ≤ 3 | > 8; road enters window for K ≤ 1 | > 8; road enters window for K ≤ 1 | > 8 | K ≥ 1 | K ≥ 1 | K ≥ 1 |
| Yantai | base (2.5 km/h) | > 8; road enters window for K ≤ 1 | > 8 | K ≥ 2 | K ≥ 1 | K ≥ 1 | K ≥ 1 | K ≥ 1 |
| Yantai | 1 km/h | > 8; road enters window for K ≤ 2 | > 8; road enters window for K ≤ 1 | K ≥ 3 | K ≥ 2 | K ≥ 1 | K ≥ 1 | K ≥ 1 |
