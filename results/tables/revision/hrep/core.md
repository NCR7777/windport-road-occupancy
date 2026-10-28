# Core instance: port time for one vessel with 10 piles (shortest over K = 1–8; in parentheses the K attaining it, L″_lift* at that K, and the minimum of L″_lift* over K)

In-series values are taken from the main geometry (170 m; under main2 the load-out road network is unchanged and reused byte for byte). Side by side: the main geometry uses the abstraction "one 40 m pull-in spur per cradle"; the main2 geometry uses reconstructed rows (parallel to the shoreline, row spacing 15.36 m, piles at 60–170 m, S cradles using the S rows nearest the shore), first-come-first-served; for Q_h = 0, convoy dispatch is listed separately (conservative-lifting-rule version of windport.sim2.ConvoySim).

## Long single lane + 1 km/h

| Lifting | Q_h | In series, roadside | In series, pull-in | Side by side (main-geometry abstraction) | **Side by side (main2 reconstruction)** | Side by side, reconstructed + convoy dispatch |
|---|---|---|---|---|---|---|
| direct lift S = 0 | 0 | 17.39 (K = 2: 17.39; min over K 17.39) | 18.42 (K = 2: 18.42; min over K 18.42) | 19.67 (K = 5: 10.00; min over K 10.00) | **18.22 (K = 2: 18.22; min over K 18.22)** | 18.22 (K = 2: 18.22; min over K 18.22) |
| direct lift S = 0 | 1 | 16.18 (K = 5: 10.00; min over K 10.00) | 16.48 (K = 4: 11.26; min over K 10.00) | 17.32 (K = 4: 11.39; min over K 10.00) | **16.11 (K = 4: 10.62; min over K 10.00)** |  |
| direct lift S = 0 | unlimited | 14.15 (K = 8: 10.00; min over K 10.00) | 14.27 (K = 8: 10.00; min over K 10.00) | 14.40 (K = 8: 10.00; min over K 10.00) | **13.30 (K = 8: 10.00; min over K 10.00)** |  |
| cradle S = 1 | 0 | 20.05 (K = 2: 20.05; min over K 20.05) | 20.05 (K = 2: 20.05; min over K 20.05) | 21.19 (K = 5: 10.00; min over K 10.00) | **20.78 (K = 2: 20.78; min over K 20.78)** | 20.78 (K = 2: 20.78; min over K 20.78) |
| cradle S = 1 | 1 | 18.25 (K = 2: 14.30; min over K 10.00) | 18.25 (K = 2: 14.30; min over K 10.00) | 18.26 (K = 2: 14.93; min over K 10.00) | **17.54 (K = 2: 14.67; min over K 10.00)** |  |
| cradle S = 1 | unlimited | 14.65 (K = 7: 10.00; min over K 10.00) | 14.65 (K = 7: 10.00; min over K 10.00) | 14.50 (K = 7: 10.00; min over K 10.00) | **13.70 (K = 7: 10.00; min over K 10.00)** |  |
| mixed lifting S = 1 | 0 | 16.36 (K = 2: 15.17; min over K 15.17) | 17.28 (K = 2: 16.09; min over K 16.09) | 18.25 (K = 4: 10.00; min over K 10.00) | **17.09 (K = 2: 15.90; min over K 15.90)** | 17.09 (K = 2: 15.90; min over K 15.90) |
| mixed lifting S = 1 | 1 | 15.97 (K = 5: 10.00; min over K 10.00) | 16.27 (K = 4: 10.00; min over K 10.00) | 16.97 (K = 4: 10.00; min over K 10.00) | **15.90 (K = 4: 10.00; min over K 10.00)** |  |
| mixed lifting S = 1 | unlimited | 14.11 (K = 7: 10.00; min over K 10.00) | 14.22 (K = 7: 10.00; min over K 10.00) | 14.07 (K = 7: 10.00; min over K 10.00) | **13.16 (K = 7: 10.00; min over K 10.00)** |  |
| cradle S = 3 | 0 | 16.23 (K = 2: 15.51; min over K 15.51) | 15.64 (K = 3: 10.00; min over K 10.00) | 16.35 (K = 3: 10.00; min over K 10.00) | **15.86 (K = 3: 10.00; min over K 10.00)** | 14.86 (K = 3: 10.00; min over K 10.00) |
| cradle S = 3 | 1 | 14.56 (K = 4: 10.00; min over K 10.00) | 14.13 (K = 4: 10.00; min over K 10.00) | 14.03 (K = 2: 11.46; min over K 10.00) | **13.50 (K = 2: 11.15; min over K 10.00)** |  |
| cradle S = 3 | unlimited | 12.05 (K = 6: 10.00; min over K 10.00) | 11.18 (K = 7: 10.00; min over K 10.00) | 10.47 (K = 7: 10.00; min over K 10.00) | **10.00 (K = 7: 10.00; min over K 10.00)** |  |
| mixed lifting S = 3 | 0 | 13.89 (K = 2: 11.62; min over K 11.62) | 13.88 (K = 2: 10.00; min over K 10.00) | 14.48 (K = 3: 10.00; min over K 10.00) | **13.51 (K = 2: 10.00; min over K 10.00)** | 11.90 (K = 4: 10.00; min over K 10.00) |
| mixed lifting S = 3 | 1 | 12.90 (K = 4: 10.00; min over K 10.00) | 13.03 (K = 4: 10.00; min over K 10.00) | 13.18 (K = 4: 10.00; min over K 10.00) | **12.37 (K = 4: 10.00; min over K 10.00)** |  |
| mixed lifting S = 3 | unlimited | 11.51 (K = 6: 10.00; min over K 10.00) | 10.76 (K = 7: 10.00; min over K 10.00) | 10.04 (K = 7: 10.00; min over K 10.00) | **10.00 (K = 7: 10.00; min over K 10.00)** |  |

## Long corridor + 1 km/h

| Lifting | Q_h | In series, roadside | In series, pull-in | Side by side (main-geometry abstraction) | **Side by side (main2 reconstruction)** | Side by side, reconstructed + convoy dispatch |
|---|---|---|---|---|---|---|
| direct lift S = 0 | 0 | 17.39 (K = 2: 17.39; min over K 17.39) | 18.42 (K = 2: 18.42; min over K 18.42) | 19.67 (K = 4: 10.00; min over K 10.00) | **18.22 (K = 2: 18.22; min over K 18.22)** | 18.22 (K = 2: 18.22; min over K 18.22) |
| direct lift S = 0 | 1 | 14.92 (K = 3: 10.00; min over K 10.00) | 15.61 (K = 3: 10.00; min over K 10.00) | 16.26 (K = 2: 13.48; min over K 10.00) | **15.48 (K = 3: 10.00; min over K 10.00)** |  |
| direct lift S = 0 | unlimited | 11.11 (K = 8: 10.00; min over K 10.00) | 11.22 (K = 8: 10.00; min over K 10.00) | 11.36 (K = 8: 10.00; min over K 10.00) | **11.09 (K = 8: 10.00; min over K 10.00)** |  |
| cradle S = 1 | 0 | 20.05 (K = 2: 20.05; min over K 20.05) | 20.05 (K = 2: 20.05; min over K 20.05) | 21.19 (K = 3: 10.00; min over K 10.00) | **20.78 (K = 2: 20.78; min over K 20.78)** | 20.78 (K = 2: 20.78; min over K 20.78) |
| cradle S = 1 | 1 | 16.37 (K = 2: 14.30; min over K 10.00) | 16.37 (K = 2: 14.30; min over K 10.00) | 16.60 (K = 2: 14.93; min over K 10.00) | **16.22 (K = 2: 14.67; min over K 10.00)** |  |
| cradle S = 1 | unlimited | 11.61 (K = 7: 10.00; min over K 10.00) | 11.61 (K = 7: 10.00; min over K 10.00) | 11.46 (K = 7: 10.00; min over K 10.00) | **11.50 (K = 7: 10.00; min over K 10.00)** |  |
| mixed lifting S = 1 | 0 | 16.36 (K = 2: 15.17; min over K 15.17) | 17.28 (K = 2: 16.09; min over K 16.09) | 18.25 (K = 3: 10.00; min over K 10.00) | **17.09 (K = 2: 15.90; min over K 15.90)** | 17.09 (K = 2: 15.90; min over K 15.90) |
| mixed lifting S = 1 | 1 | 14.71 (K = 3: 10.00; min over K 10.00) | 15.40 (K = 3: 10.00; min over K 10.00) | 15.86 (K = 2: 13.28; min over K 10.00) | **15.27 (K = 3: 10.00; min over K 10.00)** |  |
| mixed lifting S = 1 | unlimited | 11.07 (K = 7: 10.00; min over K 10.00) | 11.18 (K = 7: 10.00; min over K 10.00) | 11.02 (K = 7: 10.00; min over K 10.00) | **10.96 (K = 7: 10.00; min over K 10.00)** |  |
| cradle S = 3 | 0 | 16.23 (K = 2: 15.51; min over K 15.51) | 15.64 (K = 3: 10.00; min over K 10.00) | 16.35 (K = 3: 10.00; min over K 10.00) | **15.86 (K = 3: 10.00; min over K 10.00)** | 14.26 (K = 3: 10.00; min over K 10.00) |
| cradle S = 3 | 1 | 13.32 (K = 2: 10.99; min over K 10.00) | 12.73 (K = 2: 10.99; min over K 10.00) | 12.85 (K = 2: 11.46; min over K 10.00) | **12.57 (K = 2: 11.15; min over K 10.00)** |  |
| cradle S = 3 | unlimited | 10.00 (K = 6: 10.00; min over K 10.00) | 10.00 (K = 5: 10.00; min over K 10.00) | 10.00 (K = 5: 10.00; min over K 10.00) | **10.00 (K = 5: 10.00; min over K 10.00)** |  |
| mixed lifting S = 3 | 0 | 13.89 (K = 2: 11.62; min over K 11.62) | 13.88 (K = 2: 10.00; min over K 10.00) | 14.48 (K = 3: 10.00; min over K 10.00) | **13.51 (K = 2: 10.00; min over K 10.00)** | 10.87 (K = 3: 10.00; min over K 10.00) |
| mixed lifting S = 3 | 1 | 12.25 (K = 4: 10.00; min over K 10.00) | 11.87 (K = 4: 10.00; min over K 10.00) | 12.26 (K = 2: 10.21; min over K 10.00) | **11.75 (K = 3: 10.00; min over K 10.00)** |  |
| mixed lifting S = 3 | unlimited | 10.00 (K = 6: 10.00; min over K 10.00) | 10.00 (K = 5: 10.00; min over K 10.00) | 10.00 (K = 5: 10.00; min over K 10.00) | **10.00 (K = 5: 10.00; min over K 10.00)** |  |

