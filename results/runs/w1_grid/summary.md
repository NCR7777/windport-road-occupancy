# Exhaustive small-instance check of W1 (release before pick-up at the same instant)

- Single window: 18144 instances, bound exceeded in 0, attained in 17116 (94.3%), gap distribution 0: 17116, 1: 955, 2: 71, 3: 2 (of which exact value > 0 and attained: 13660).
  - Q ∈ {1, K} (original grid): 15120 instances, bound exceeded in 0, attained in 14384 (95.1%), gap distribution 0: 14384, 1: 687, 2: 48, 3: 1.
  - 1 < Q < K (added grid): 3024 instances, bound exceeded in 0, attained in 2732 (90.3%), gap distribution 0: 2732, 1: 268, 2: 23, 3: 1.
- Periodic windows: 384 instances, bound exceeded in 0; attained in 368.
- Mixed lifting (Corollary 2): 2880 instances, bound exceeded in 0, attained in 2674 (92.8%), gap distribution 0: 2674, 1: 174, 2: 32; the W1 computed for cradle mode only is exceeded in 765 instances (out of 1440 any-history instances).
- Two-lane cut (qe = 2): 1920 instances, bound exceeded in 0, attained in 1699 (88.5%), gap distribution 0: 1699, 1: 205, 2: 15, 3: 1.

The earlier candidate formula min{L/p, S + L·r} (without boundary terms) is exceeded by the exact value in 1788 instances (1363 any-history instances; maximum excess 2.60 pieces). First 5 instances:

| K | S | Q | hp | tl | hd | te | er | p | L | Start | G | Exact | Candidate | W1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0 | 3 | 1 | 3 | 0 | 2 | 0 | 1 | 12 | any |  | 5 | 2.4 | 5 |
| 3 | 0 | 3 | 1 | 3 | 0 | 2 | 0 | 2 | 12 | any |  | 5 | 2.4 | 5 |
| 3 | 0 | 3 | 2 | 3 | 0 | 2 | 0 | 1 | 12 | any |  | 5 | 2.4 | 5 |
| 3 | 0 | 3 | 2 | 3 | 0 | 2 | 0 | 2 | 12 | any |  | 5 | 2.4 | 5 |
| 3 | 0 | 3 | 1 | 1 | 0 | 1 | 0 | 1 | 5 | any |  | 5 | 2.5 | 5 |

| Start | Binding term | Instances | Attained | Attained share |
|---|---|---:|---:|---:|
| any | cut | 1470 | 1211 | 82% |
| any | fleet | 1597 | 1373 | 86% |
| any | interface | 3992 | 3877 | 97% |
| any | turnover | 525 | 485 | 92% |
| any | zone | 985 | 926 | 94% |
| empty G=0 | cut | 15 | 15 | 100% |
| empty G=0 | fleet | 65 | 50 | 77% |
| empty G=0 | interface | 247 | 34 | 14% |
| empty G=0 | prep | 3101 | 2723 | 88% |
| empty G=0 | turnover | 4 | 0 | 0% |
| empty G=0 | zone | 12 | 12 | 100% |
| empty G=4 | cut | 348 | 337 | 97% |
| empty G=4 | fleet | 378 | 353 | 93% |
| empty G=4 | interface | 1961 | 1877 | 96% |
| empty G=4 | prep | 4643 | 4477 | 96% |
| empty G=4 | turnover | 184 | 155 | 84% |
| empty G=4 | zone | 238 | 237 | 100% |

Instances with bound = 0 are excluded from the table above (window shorter than one lift, or too short for the first handover).

Instances with gap ≥ 2 (first 15):

| K | S | Q | hp | tl | hd | te | er | p | L | Start | G | Exact | Bound | Binding |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 2 | 1 | 1 | 2 | 1 | 0 | 3 | 12 | empty | 0 | 2 | 4 | interface+prep |
| 2 | 1 | 2 | 2 | 1 | 1 | 1 | 0 | 3 | 12 | empty | 0 | 2 | 4 | interface+prep |
| 2 | 1 | 2 | 2 | 3 | 2 | 0 | 2 | 2 | 12 | any |  | 3 | 5 | fleet+cut |
| 2 | 2 | 2 | 1 | 1 | 2 | 1 | 0 | 1 | 12 | any |  | 6 | 8 | fleet+cut |
| 2 | 2 | 2 | 1 | 1 | 2 | 1 | 0 | 3 | 12 | empty | 0 | 2 | 4 | interface+prep |
| 2 | 2 | 2 | 1 | 1 | 2 | 0 | 2 | 1 | 8 | any |  | 4 | 6 | fleet |
| 2 | 2 | 2 | 2 | 1 | 1 | 1 | 0 | 3 | 12 | empty | 0 | 2 | 4 | interface+prep |
| 2 | 2 | 2 | 2 | 1 | 2 | 1 | 0 | 1 | 8 | any |  | 4 | 6 | fleet+cut |
| 2 | 2 | 2 | 2 | 3 | 2 | 0 | 2 | 2 | 12 | any |  | 4 | 6 | interface+fleet+cut |
| 2 | 3 | 2 | 1 | 1 | 2 | 1 | 0 | 1 | 12 | any |  | 7 | 9 | fleet+cut |
| 2 | 3 | 2 | 1 | 1 | 2 | 1 | 0 | 3 | 12 | empty | 0 | 2 | 4 | interface+prep |
| 2 | 3 | 2 | 1 | 1 | 2 | 0 | 2 | 1 | 8 | any |  | 5 | 7 | fleet |
| 2 | 3 | 2 | 2 | 1 | 1 | 1 | 0 | 3 | 12 | empty | 0 | 2 | 4 | interface+prep |
| 2 | 3 | 2 | 2 | 1 | 2 | 1 | 0 | 1 | 8 | any |  | 5 | 7 | fleet+cut |
| 3 | 0 | 1 | 2 | 1 | 0 | 0 | 2 | 2 | 12 | empty | 0 | 4 | 6 | interface+prep |
