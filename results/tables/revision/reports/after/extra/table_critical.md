# Critical single-lane length

Minimum time one monopile occupies the single lane: τ_cut = t_ℓ + t_e (round trip through the cut, valid for any dispatch and any quay-zone capacity: the cut term of W1); when the quay zone holds only one vehicle set at a time (as in first-come-first-served with Q_h = 0) τ_zone1 = t_ℓ + d_q + t_e^occ (d_q includes the 30 min set-down for cradle mode, not for direct lift). For τ > p no fleet can keep the crane lifting continuously; the critical length ℓ* is the single-lane length at which τ = p.

## Critical length ℓ* (m): loaded speed × p (S = 1)

| Cradle | p (h) | 0.5 km/h | 0.75 km/h | 1.0 km/h | 1.25 km/h | 1.5 km/h | 2.0 km/h | 2.5 km/h | 3.0 km/h | 4.0 km/h | 5.0 km/h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pull-in cradle | 0.5 | 0.0 / 0.0 | 0.0 / 0.0 | 215.5 / 0.0 | 298.8 / 0.0 | 375.6 / 0.0 | 513.1 / 0.0 | 631.9 / 0.0 | 736.1 / 0.0 | 909.7 / 0.0 | 1048.7 / 0.0 |
| pull-in cradle | 1.0 | 253.5 / 0.0 | 450.9 / 157.0 | 632.3 / 169.4 | 798.6 / 254.6 | 952.5 / 333.2 | 1227.4 / 473.6 | 1465.5 / 595.3 | 1673.8 / 701.7 | 2020.8 / 879.4 | 2298.7 / 1021.3 |
| pull-in cradle | 1.5 | 480.5 / 203.4 | 777.0 / 403.0 | 1048.7 / 586.2 | 1298.7 / 754.7 | 1529.4 / 910.1 | 1941.5 / 1188.0 | 2298.7 / 1428.5 | 2611.2 / 1639.5 | 3131.9 / 1990.5 | 3548.6 / 2271.2 |
| roadside cradle | 0.5 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| roadside cradle | 1.0 | 0.0 / 0.0 | 450.9 / 382.9 | 632.3 / 473.9 | 798.6 / 557.7 | 952.5 / 634.8 | 1227.4 / 773.0 | 1465.5 / 892.6 | 1673.8 / 997.5 | 2020.8 / 1171.9 | 2298.7 / 1311.5 |
| roadside cradle | 1.5 | 480.5 / 283.5 | 777.0 / 403.0 | 1048.7 / 586.2 | 1298.7 / 754.7 | 1529.4 / 910.1 | 1941.5 / 1188.0 | 2298.7 / 1428.5 | 2611.2 / 1639.5 | 3131.9 / 1990.5 | 3548.6 / 2271.2 |

(Each cell: critical length for τ_cut / critical length for τ_zone1; 0 means road-limited at any length: the quay-front cut of the roadside cradle already contains the 30 min set-down, which exceeds p = 0.5 h.)

## τ/p of named cases (S = 1)

| Port type / shipyard | Scenario | Cradle | p (h) | Cut | t_ℓ | t_e | d_q | Q | τ_cut/p | τ_zone1/p | τ_W/p |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| A1 | base | roadside cradle | 1.0 | r|apron_0 | 2289.2 | 73.8 | 0.0 | 1 | 0.656 | 0.677 | 0.677 |
| A1 | base | roadside cradle | 0.5 | r|apron_0 | 2289.2 | 73.8 | 0.0 | 1 | 1.313 | 1.354 | 1.354 |
| A1 | base | pull-in cradle | 1.0 | r|corr_lane_1 | 698.0 | 169.2 | 1879.2 | 2 | 0.241 | 0.763 | 0.358 |
| A1 | base | pull-in cradle | 0.5 | r|corr_lane_1 | 698.0 | 169.2 | 1879.2 | 2 | 0.482 | 1.526 | 0.716 |
| A1 | slow | roadside cradle | 1.0 | r|apron_0 | 2843.0 | 73.8 | 0.0 | 1 | 0.81 | 0.831 | 0.831 |
| A1 | slow | roadside cradle | 0.5 | r|apron_0 | 2843.0 | 73.8 | 0.0 | 1 | 1.62 | 1.661 | 1.661 |
| A1 | slow | pull-in cradle | 1.0 | r|corr_lane_1 | 1565.0 | 169.2 | 1998.0 | 2 | 0.482 | 1.037 | 0.495 |
| A1 | slow | pull-in cradle | 0.5 | r|corr_lane_1 | 1565.0 | 169.2 | 1998.0 | 2 | 0.963 | 2.073 | 0.99 |
| A1 | longslow | roadside cradle | 1.0 | r|corr_lane_1 | 3005.0 | 457.2 | 1998.0 | 2 | 0.962 | 1.517 | 0.962 |
| A1 | longslow | roadside cradle | 0.5 | r|corr_lane_1 | 3005.0 | 457.2 | 1998.0 | 2 | 1.923 | 3.033 | 1.923 |
| A1 | longslow | pull-in cradle | 1.0 | r|corr_lane_1 | 3005.0 | 457.2 | 1998.0 | 2 | 0.962 | 1.517 | 0.962 |
| A1 | longslow | pull-in cradle | 0.5 | r|corr_lane_1 | 3005.0 | 457.2 | 1998.0 | 2 | 1.923 | 3.033 | 1.923 |
| A1 | lane | roadside cradle | 1.0 | r|corr_lane_0 | 5165.0 | 889.2 | 1998.0 | 2 | 1.682 | 2.237 | 1.682 |
| A1 | lane | roadside cradle | 0.5 | r|corr_lane_0 | 5165.0 | 889.2 | 1998.0 | 2 | 3.363 | 4.473 | 3.363 |
| A1 | lane | pull-in cradle | 1.0 | r|corr_lane_0 | 5165.0 | 889.2 | 1998.0 | 2 | 1.682 | 2.237 | 1.682 |
| A1 | lane | pull-in cradle | 0.5 | r|corr_lane_0 | 5165.0 | 889.2 | 1998.0 | 2 | 3.363 | 4.473 | 3.363 |
| A2 | base | roadside cradle | 1.0 | r|apron_0 | 2289.2 | 73.8 | 0.0 | 1 | 0.656 | 0.677 | 0.677 |
| A2 | base | roadside cradle | 0.5 | r|apron_0 | 2289.2 | 73.8 | 0.0 | 1 | 1.313 | 1.354 | 1.354 |
| A2 | base | pull-in cradle | 1.0 | r|loop | 427.3 | 399.6 | 1861.9 | 2 | 0.23 | 0.747 | 0.318 |
| A2 | base | pull-in cradle | 0.5 | r|loop | 427.3 | 399.6 | 1861.9 | 2 | 0.459 | 1.494 | 0.636 |
| A2 | slow | roadside cradle | 1.0 | r|apron_0 | 2843.0 | 73.8 | 0.0 | 1 | 0.81 | 0.831 | 0.831 |
| A2 | slow | roadside cradle | 0.5 | r|apron_0 | 2843.0 | 73.8 | 0.0 | 1 | 1.62 | 1.661 | 1.661 |
| A2 | slow | pull-in cradle | 1.0 | r|corr_lane_1 | 1565.0 | 0.0 | 1998.0 | 10 | 0.435 | 0.99 | 0.435 |
| A2 | slow | pull-in cradle | 0.5 | r|corr_lane_1 | 1565.0 | 0.0 | 1998.0 | 10 | 0.869 | 1.979 | 0.869 |
| A2 | longslow | roadside cradle | 1.0 | r|corr_lane_1 | 3005.0 | 0.0 | 1998.0 | 10 | 0.835 | 1.39 | 0.835 |
| A2 | longslow | roadside cradle | 0.5 | r|corr_lane_1 | 3005.0 | 0.0 | 1998.0 | 10 | 1.669 | 2.779 | 1.669 |
| A2 | longslow | pull-in cradle | 1.0 | r|corr_lane_1 | 3005.0 | 0.0 | 1998.0 | 10 | 0.835 | 1.39 | 0.835 |
| A2 | longslow | pull-in cradle | 0.5 | r|corr_lane_1 | 3005.0 | 0.0 | 1998.0 | 10 | 1.669 | 2.779 | 1.669 |
| A2 | lane | roadside cradle | 1.0 | r|corr_lane_0 | 5165.0 | 0.0 | 1998.0 | 10 | 1.435 | 1.99 | 1.435 |
| A2 | lane | roadside cradle | 0.5 | r|corr_lane_0 | 5165.0 | 0.0 | 1998.0 | 10 | 2.869 | 3.979 | 2.869 |
| A2 | lane | pull-in cradle | 1.0 | r|corr_lane_0 | 5165.0 | 0.0 | 1998.0 | 10 | 1.435 | 1.99 | 1.435 |
| A2 | lane | pull-in cradle | 0.5 | r|corr_lane_0 | 5165.0 | 0.0 | 1998.0 | 10 | 2.869 | 3.979 | 2.869 |
| A3 | base | roadside cradle | 1.0 | r|apron_0 | 2289.2 | 240.3 | 0.0 | 1 | 0.703 | 0.769 | 0.769 |
| A3 | base | roadside cradle | 0.5 | r|apron_0 | 2289.2 | 240.3 | 0.0 | 1 | 1.405 | 1.539 | 1.539 |
| A3 | base | pull-in cradle | 1.0 | r|apron_0 | 654.8 | 240.3 | 1634.4 | 10 | 0.249 | 0.769 | 0.249 |
| A3 | base | pull-in cradle | 0.5 | r|apron_0 | 654.8 | 240.3 | 1634.4 | 10 | 0.497 | 1.539 | 0.497 |
| A3 | slow | roadside cradle | 1.0 | r|apron_0 | 2843.0 | 240.3 | 0.0 | 1 | 0.856 | 0.923 | 0.923 |
| A3 | slow | roadside cradle | 0.5 | r|apron_0 | 2843.0 | 240.3 | 0.0 | 1 | 1.713 | 1.846 | 1.846 |
| A3 | slow | pull-in cradle | 1.0 | r|apron_0 | 1457.0 | 240.3 | 1386.0 | 10 | 0.471 | 0.923 | 0.471 |
| A3 | slow | pull-in cradle | 0.5 | r|apron_0 | 1457.0 | 240.3 | 1386.0 | 10 | 0.943 | 1.846 | 0.943 |
| A3 | longslow | roadside cradle | 1.0 | r|apron_0 | 2843.0 | 240.3 | 0.0 | 1 | 0.856 | 0.923 | 0.923 |
| A3 | longslow | roadside cradle | 0.5 | r|apron_0 | 2843.0 | 240.3 | 0.0 | 1 | 1.713 | 1.846 | 1.846 |
| A3 | longslow | pull-in cradle | 1.0 | r|corr1_lane_1 | 3005.0 | 0.0 | 1998.0 | 10 | 0.835 | 1.39 | 0.835 |
| A3 | longslow | pull-in cradle | 0.5 | r|corr1_lane_1 | 3005.0 | 0.0 | 1998.0 | 10 | 1.669 | 2.779 | 1.669 |
| A3 | lane | roadside cradle | 1.0 | r|corr1_lane_0 | 5165.0 | 0.0 | 1998.0 | 10 | 1.435 | 1.99 | 1.435 |
| A3 | lane | roadside cradle | 0.5 | r|corr1_lane_0 | 5165.0 | 0.0 | 1998.0 | 10 | 2.869 | 3.979 | 2.869 |
| A3 | lane | pull-in cradle | 1.0 | r|corr1_lane_0 | 5165.0 | 0.0 | 1998.0 | 10 | 1.435 | 1.99 | 1.435 |
| A3 | lane | pull-in cradle | 0.5 | r|corr1_lane_0 | 5165.0 | 0.0 | 1998.0 | 10 | 2.869 | 3.979 | 2.869 |
| okpo | base | roadside cradle | 1.0 | r|road_trace_206 | 1961.4 | 53.0 | 0.0 | 1 | 0.56 | 0.574 | 0.574 |
| okpo | base | roadside cradle | 0.5 | r|road_trace_206 | 1961.4 | 53.0 | 0.0 | 1 | 1.119 | 1.149 | 1.149 |
| okpo | base | pull-in cradle | 1.0 | r|road_trace_206 | 327.0 | 53.0 | 1634.4 | 10 | 0.106 | 0.574 | 0.106 |
| okpo | base | pull-in cradle | 0.5 | r|road_trace_206 | 327.0 | 53.0 | 1634.4 | 10 | 0.211 | 1.149 | 0.211 |
| okpo | slow | roadside cradle | 1.0 | r|road_trace_206 | 2203.6 | 53.0 | 0.0 | 1 | 0.627 | 0.642 | 0.642 |
| okpo | slow | roadside cradle | 0.5 | r|road_trace_206 | 2203.6 | 53.0 | 0.0 | 1 | 1.254 | 1.283 | 1.283 |
| okpo | slow | pull-in cradle | 1.0 | r|road_trace_206 | 817.6 | 53.0 | 1386.0 | 10 | 0.242 | 0.642 | 0.242 |
| okpo | slow | pull-in cradle | 0.5 | r|road_trace_206 | 817.6 | 53.0 | 1386.0 | 10 | 0.484 | 1.283 | 0.484 |
| yantai | base | roadside cradle | 1.0 | r|road_trace_072 | 1842.8 | 23.3 | 0.0 | 1 | 0.518 | 0.525 | 0.525 |
| yantai | base | roadside cradle | 0.5 | r|road_trace_072 | 1842.8 | 23.3 | 0.0 | 1 | 1.037 | 1.05 | 1.05 |
| yantai | base | pull-in cradle | 1.0 | r|road_trace_049 | 280.9 | 41.4 | 1861.6 | 10 | 0.09 | 0.618 | 0.09 |
| yantai | base | pull-in cradle | 0.5 | r|road_trace_049 | 280.9 | 41.4 | 1861.6 | 10 | 0.179 | 1.236 | 0.179 |
| yantai | slow | roadside cradle | 1.0 | r|road_trace_072 | 1907.0 | 23.3 | 0.0 | 1 | 0.536 | 0.543 | 0.543 |
| yantai | slow | roadside cradle | 0.5 | r|road_trace_072 | 1907.0 | 23.3 | 0.0 | 1 | 1.072 | 1.085 | 1.085 |
| yantai | slow | pull-in cradle | 1.0 | r|road_trace_049 | 702.3 | 41.4 | 1953.9 | 10 | 0.207 | 0.761 | 0.207 |
| yantai | slow | pull-in cradle | 0.5 | r|road_trace_049 | 702.3 | 41.4 | 1953.9 | 10 | 0.413 | 1.522 | 0.413 |

## Check against Table 5 and Appendix C3

Road-limited (observed) = shortest port time more than 2% above the crane floor. agree_cut: for τ_cut > p the observation must be road-limited (sufficient condition); agree_zone1: τ_zone1 > p agrees with the observation.

| Source | Scenario | Cradle | Criterion | Shortest port time h | Road-limited | Agrees with τ_cut | Agrees with τ_zone1 |
|---|---|---|---|---:|---:|---:|---:|
| Table 5 | base | roadside cradle | 0.656 / 0.677 | 10.0 | 0 | 1 | 1 |
| Table 5 | crane 0.5 h | roadside cradle | 1.313 / 1.354 | 8.54 | 1 | 1 | 1 |
| Table 5 | base | pull-in cradle | 0.241 / 0.763 | 10.0 | 0 | 1 | 1 |
| Table 5 | crane 0.5 h | pull-in cradle | 0.482 / 1.526 | 8.54 | 1 | 1 | 1 |
| Table 5 | 1 km/h | roadside cradle | 0.81 / 0.831 | 12.37 | 1 | 1 | 0 |
| Table 5 | 1 km/h | pull-in cradle | 0.482 / 1.037 | 12.37 | 1 | 1 | 1 |
| Table 5 | long corridor + 1 km/h | roadside cradle | 0.962 / 1.517 | 20.05 | 1 | 1 | 1 |
| Table 5 | long corridor + 1 km/h | pull-in cradle | 0.962 / 1.517 | 20.05 | 1 | 1 | 1 |
| Table 5 | long single lane + 1 km/h | roadside cradle | 1.682 / 2.237 | 20.05 | 1 | 1 | 1 |
| Table 5 | long single lane + 1 km/h | pull-in cradle | 1.682 / 2.237 | 20.05 | 1 | 1 | 1 |
| Appendix C3 (long single lane 1,200 m) | v = 1 km/h | roadside cradle | ℓ* 632.3 / 473.9 | 20.05 | 1 | 1 | 1 |
| Appendix C3 (long single lane 1,200 m) | v = 1.5 km/h | roadside cradle | ℓ* 952.5 / 634.8 | 16.08 | 1 | 1 | 1 |
| Appendix C3 (long single lane 1,200 m) | v = 2 km/h | roadside cradle | ℓ* 1227.4 / 773.0 | 14.09 | 1 | 1 | 1 |
| Appendix C3 (long single lane 1,200 m) | v = 2.5 km/h | roadside cradle | ℓ* 1465.5 / 892.6 | 12.9 | 1 | 1 | 1 |
| Appendix C3 (long single lane 1,200 m) | v = 1 km/h | pull-in cradle | ℓ* 632.3 / 169.4 | 20.05 | 1 | 1 | 1 |
| Appendix C3 (long single lane 1,200 m) | v = 1.5 km/h | pull-in cradle | ℓ* 952.5 / 333.2 | 16.08 | 1 | 1 | 1 |
| Appendix C3 (long single lane 1,200 m) | v = 2 km/h | pull-in cradle | ℓ* 1227.4 / 473.6 | 14.09 | 1 | 1 | 1 |
| Appendix C3 (long single lane 1,200 m) | v = 2.5 km/h | pull-in cradle | ℓ* 1465.5 / 595.3 | 12.9 | 1 | 1 | 1 |

All 18 rows: agree with τ_cut 18, agree with τ_zone1 17.

Comparison with Table 6: critical length of the window criterion (L = 12 h, S = 1): 1.0 km/h: 765.7 m; 2.5 km/h: 1738.9 m. The long single lane of 1,200 m (1 km/h) exceeds it, and the Table 6 plateau delivers 6–11 < 12; the 200 m base block (2.5 km/h) is far below it, and the Table 6 plateau delivers 12.
