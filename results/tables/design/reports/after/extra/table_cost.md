# Cost and configuration tables

Definitions: the **port time** for a vessel load of n_v piles, T(n_v) = from crane opening (vessel arrival) until the n_v-th pile is lifted; **vessel time per pile** = T(n_v)/n_v (h/pile). Vessel cost per voyage = T × day rate / 24; day rates 140,000 (Ursavas 2017, jack-up vessel), 150,000 and 250,000 €/day (Tjaberings 2022, heavy-lift vessel range). The saving per voyage from one more vehicle set = T(K) − T(K + 1) times the day rate; it is the **break-even rent**: a second vehicle set is worth hiring if its rent over one voyage cycle does not exceed it (for a cycle of C days, break-even day rate = saving / C; C only as sensitivity). Converted into vehicle hire days: one vehicle set + two operators at the working rate of Kassels Appendix D, 7,200 €/day, or 9,120 €/day with a supervisor at 80 €/h. The saving from one more cradle is computed the same way; cradles are charged per project (Kassels: 60,000 € each), and the berthings needed for amortisation = cradle cost ÷ saving per voyage (140,000 €/day). A1, first-come-first-served, G = 24 h; mixed-lifting rows use direct-lift release time x = 0 (Section 6: direct lift is no slower than the cradle only for x·p ≤ h_d).

## Saving per voyage from one more vehicle set (K → K + 1) = break-even rent (pull-in cradle, Q_h = 0)

| Scenario | n_v | Lifting | T(K = 1 / 2 / 3) h | Vessel time per pile K = 1 / 2 / 3 h | K = 1→2 saving: h; € 140k / 250k | Vehicle hire days 140k: without / with supervisor | 250k: without / with supervisor | K = 2→3 saving h |
|---|---:|---|---|---|---|---|---|---|
| base | 3 | S = 0 direct lift | 3.49 / 3.00 / 3.00 | 1.16 / 1.00 / 1.00 | 0.49; 2,838 / 5,068 | 0.4 / 0.3 | 0.7 / 0.6 | 0.00 |
| base | 3 | S = 1 cradle | 3.38 / 3.00 / 3.00 | 1.13 / 1.00 / 1.00 | 0.38; 2,209 / 3,945 | 0.3 / 0.2 | 0.5 / 0.4 | 0.00 |
| base | 3 | S = 1 mixed lifting | 3.00 / 3.00 / 3.00 | 1.00 / 1.00 / 1.00 | 0.00; 0 / 0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.00 |
| base | 3 | S = 3 cradle | 3.00 / 3.00 / 3.00 | 1.00 / 1.00 / 1.00 | 0.00; 0 / 0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.00 |
| base | 5 | S = 0 direct lift | 6.01 / 5.00 / 5.00 | 1.20 / 1.00 / 1.00 | 1.01; 5,887 / 10,512 | 0.8 / 0.6 | 1.5 / 1.2 | 0.00 |
| base | 5 | S = 1 cradle | 6.71 / 5.00 / 5.00 | 1.34 / 1.00 / 1.00 | 1.71; 9,971 / 17,805 | 1.4 / 1.1 | 2.5 / 2.0 | 0.00 |
| base | 5 | S = 1 mixed lifting | 5.52 / 5.00 / 5.00 | 1.10 / 1.00 / 1.00 | 0.52; 3,048 / 5,443 | 0.4 / 0.3 | 0.8 / 0.6 | 0.00 |
| base | 5 | S = 3 cradle | 5.00 / 5.00 / 5.00 | 1.00 / 1.00 / 1.00 | 0.00; 0 / 0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.00 |
| base | 10 | S = 0 direct lift | 12.33 / 10.00 / 10.00 | 1.23 / 1.00 / 1.00 | 2.33; 13,586 / 24,261 | 1.9 / 1.5 | 3.4 / 2.7 | 0.00 |
| base | 10 | S = 1 cradle | 15.05 / 10.00 / 10.00 | 1.50 / 1.00 / 1.00 | 5.05; 29,453 / 52,595 | 4.1 / 3.2 | 7.3 / 5.8 | 0.00 |
| base | 10 | S = 1 mixed lifting | 11.84 / 10.00 / 10.00 | 1.18 / 1.00 / 1.00 | 1.84; 10,748 / 19,192 | 1.5 / 1.2 | 2.7 / 2.1 | 0.00 |
| base | 10 | S = 3 cradle | 11.80 / 10.00 / 10.00 | 1.18 / 1.00 / 1.00 | 1.80; 10,515 / 18,777 | 1.5 / 1.2 | 2.6 / 2.1 | 0.00 |
| long corridor + 1 km/h | 3 | S = 0 direct lift | 7.01 / 4.87 / 4.87 | 2.34 / 1.62 / 1.62 | 2.14; 12,503 / 22,328 | 1.7 / 1.4 | 3.1 / 2.4 | 0.00 |
| long corridor + 1 km/h | 3 | S = 1 cradle | 5.23 / 4.15 / 4.15 | 1.74 / 1.38 / 1.38 | 1.08; 6,304 / 11,258 | 0.9 / 0.7 | 1.6 / 1.2 | 0.00 |
| long corridor + 1 km/h | 3 | S = 1 mixed lifting | 4.81 / 3.73 / 3.73 | 1.60 / 1.24 / 1.24 | 1.08; 6,304 / 11,258 | 0.9 / 0.7 | 1.6 / 1.2 | 0.00 |
| long corridor + 1 km/h | 3 | S = 3 cradle | 3.00 / 3.00 / 3.00 | 1.00 / 1.00 / 1.00 | 0.00; 0 / 0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.00 |
| long corridor + 1 km/h | 5 | S = 0 direct lift | 13.10 / 8.74 / 8.74 | 2.62 / 1.75 / 1.75 | 4.36; 25,427 / 45,405 | 3.5 / 2.8 | 6.3 / 5.0 | 0.00 |
| long corridor + 1 km/h | 5 | S = 1 cradle | 11.99 / 8.69 / 8.69 | 2.40 / 1.74 / 1.74 | 3.30; 19,228 / 34,335 | 2.7 / 2.1 | 4.8 / 3.8 | 0.00 |
| long corridor + 1 km/h | 5 | S = 1 mixed lifting | 10.89 / 7.60 / 7.60 | 2.18 / 1.52 / 1.52 | 3.30; 19,228 / 34,335 | 2.7 / 2.1 | 4.8 / 3.8 | 0.00 |
| long corridor + 1 km/h | 5 | S = 3 cradle | 5.27 / 5.00 / 5.00 | 1.05 / 1.00 / 1.00 | 0.27; 1,564 / 2,794 | 0.2 / 0.2 | 0.4 / 0.3 | 0.00 |
| long corridor + 1 km/h | 10 | S = 0 direct lift | 28.35 / 18.42 / 18.42 | 2.83 / 1.84 / 1.84 | 9.93; 57,893 / 103,381 | 8.0 / 6.3 | 14.4 / 11.3 | 0.00 |
| long corridor + 1 km/h | 10 | S = 1 cradle | 28.91 / 20.05 / 20.05 | 2.89 / 2.00 / 2.00 | 8.86; 51,694 / 92,311 | 7.2 / 5.7 | 12.8 / 10.1 | 0.00 |
| long corridor + 1 km/h | 10 | S = 1 mixed lifting | 26.14 / 17.28 / 17.28 | 2.61 / 1.73 / 1.73 | 8.86; 51,694 / 92,311 | 7.2 / 5.7 | 12.8 / 10.1 | 0.00 |
| long corridor + 1 km/h | 10 | S = 3 cradle | 22.19 / 15.64 / 15.64 | 2.22 / 1.56 / 1.56 | 6.55; 38,210 / 68,233 | 5.3 / 4.2 | 9.5 / 7.5 | 0.00 |
| long single lane + 1 km/h | 3 | S = 0 direct lift | 7.01 / 4.87 / 4.87 | 2.34 / 1.62 / 1.62 | 2.14; 12,503 / 22,328 | 1.7 / 1.4 | 3.1 / 2.4 | 0.00 |
| long single lane + 1 km/h | 3 | S = 1 cradle | 5.23 / 4.15 / 4.15 | 1.74 / 1.38 / 1.38 | 1.08; 6,304 / 11,258 | 0.9 / 0.7 | 1.6 / 1.2 | 0.00 |
| long single lane + 1 km/h | 3 | S = 1 mixed lifting | 4.81 / 3.73 / 3.73 | 1.60 / 1.24 / 1.24 | 1.08; 6,304 / 11,258 | 0.9 / 0.7 | 1.6 / 1.2 | 0.00 |
| long single lane + 1 km/h | 3 | S = 3 cradle | 3.00 / 3.00 / 3.00 | 1.00 / 1.00 / 1.00 | 0.00; 0 / 0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.00 |
| long single lane + 1 km/h | 5 | S = 0 direct lift | 13.10 / 8.74 / 8.74 | 2.62 / 1.75 / 1.75 | 4.36; 25,427 / 45,405 | 3.5 / 2.8 | 6.3 / 5.0 | 0.00 |
| long single lane + 1 km/h | 5 | S = 1 cradle | 11.99 / 8.69 / 8.69 | 2.40 / 1.74 / 1.74 | 3.30; 19,228 / 34,335 | 2.7 / 2.1 | 4.8 / 3.8 | 0.00 |
| long single lane + 1 km/h | 5 | S = 1 mixed lifting | 10.89 / 7.60 / 7.60 | 2.18 / 1.52 / 1.52 | 3.30; 19,228 / 34,335 | 2.7 / 2.1 | 4.8 / 3.8 | 0.00 |
| long single lane + 1 km/h | 5 | S = 3 cradle | 5.27 / 5.00 / 5.00 | 1.05 / 1.00 / 1.00 | 0.27; 1,564 / 2,794 | 0.2 / 0.2 | 0.4 / 0.3 | 0.00 |
| long single lane + 1 km/h | 10 | S = 0 direct lift | 28.35 / 18.42 / 18.42 | 2.83 / 1.84 / 1.84 | 9.93; 57,893 / 103,381 | 8.0 / 6.3 | 14.4 / 11.3 | 0.00 |
| long single lane + 1 km/h | 10 | S = 1 cradle | 28.91 / 20.05 / 20.05 | 2.89 / 2.00 / 2.00 | 8.86; 51,694 / 92,311 | 7.2 / 5.7 | 12.8 / 10.1 | 0.00 |
| long single lane + 1 km/h | 10 | S = 1 mixed lifting | 26.14 / 17.28 / 17.28 | 2.61 / 1.73 / 1.73 | 8.86; 51,694 / 92,311 | 7.2 / 5.7 | 12.8 / 10.1 | 0.00 |
| long single lane + 1 km/h | 10 | S = 3 cradle | 22.19 / 15.64 / 15.64 | 2.22 / 1.56 / 1.56 | 6.55; 38,210 / 68,233 | 5.3 / 4.2 | 9.5 / 7.5 | 0.00 |
| crane 0.5 h | 3 | S = 0 direct lift | 2.94 / 1.72 / 1.50 | 0.98 / 0.57 / 0.50 | 1.21; 7,080 / 12,644 | 1.0 / 0.8 | 1.8 / 1.4 | 0.22 |
| crane 0.5 h | 3 | S = 1 cradle | 2.85 / 2.12 / 2.12 | 0.95 / 0.71 / 0.71 | 0.73; 4,287 / 7,655 | 0.6 / 0.5 | 1.1 / 0.8 | 0.00 |
| crane 0.5 h | 3 | S = 1 mixed lifting | 2.22 / 1.50 / 1.50 | 0.74 / 0.50 / 0.50 | 0.72; 4,216 / 7,529 | 0.6 / 0.5 | 1.0 / 0.8 | 0.00 |
| crane 0.5 h | 3 | S = 3 cradle | 1.50 / 1.50 / 1.50 | 0.50 / 0.50 / 0.50 | 0.00; 0 / 0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.00 |
| crane 0.5 h | 5 | S = 0 direct lift | 5.41 / 2.96 / 2.50 | 1.08 / 0.59 / 0.50 | 2.45; 14,266 / 25,475 | 2.0 / 1.6 | 3.5 / 2.8 | 0.46 |
| crane 0.5 h | 5 | S = 1 cradle | 6.18 / 3.95 / 3.95 | 1.24 / 0.79 / 0.79 | 2.23; 13,018 / 23,247 | 1.8 / 1.4 | 3.2 / 2.5 | 0.00 |
| crane 0.5 h | 5 | S = 1 mixed lifting | 4.70 / 2.74 / 2.50 | 0.94 / 0.55 / 0.50 | 1.96; 11,402 / 20,360 | 1.6 / 1.3 | 2.8 / 2.2 | 0.24 |
| crane 0.5 h | 5 | S = 3 cradle | 2.87 / 2.50 / 2.50 | 0.57 / 0.50 / 0.50 | 0.37; 2,168 / 3,872 | 0.3 / 0.2 | 0.5 / 0.4 | 0.00 |
| crane 0.5 h | 10 | S = 0 direct lift | 11.60 / 5.96 / 5.00 | 1.16 / 0.60 / 0.50 | 5.64; 32,905 / 58,759 | 4.6 / 3.6 | 8.2 / 6.4 | 0.96 |
| crane 0.5 h | 10 | S = 1 cradle | 14.52 / 8.54 / 8.54 | 1.45 / 0.85 / 0.85 | 5.99; 34,925 / 62,366 | 4.9 / 3.8 | 8.7 / 6.8 | 0.00 |
| crane 0.5 h | 10 | S = 1 mixed lifting | 10.89 / 5.96 / 5.00 | 1.09 / 0.60 / 0.50 | 4.93; 28,742 / 51,324 | 4.0 / 3.2 | 7.1 / 5.6 | 0.96 |
| crane 0.5 h | 10 | S = 3 cradle | 11.21 / 6.87 / 5.82 | 1.12 / 0.69 / 0.58 | 4.34; 25,329 / 45,230 | 3.5 / 2.8 | 6.3 / 5.0 | 1.05 |

Break-even day rate (€/day) = saving per voyage ÷ voyage cycle C (sensitivity; pull-in, S = 1, K = 1→2, Q_h = 0, 140,000 €/day):

| Scenario | n_v | C = 3 days | C = 6 days | C = 10 days |
|---|---:|---:|---:|---:|
| base | 3 | 736 | 368 | 221 |
| base | 5 | 3,324 | 1,662 | 997 |
| base | 10 | 9,818 | 4,909 | 2,945 |
| long corridor + 1 km/h | 3 | 2,101 | 1,051 | 630 |
| long corridor + 1 km/h | 5 | 6,409 | 3,205 | 1,923 |
| long corridor + 1 km/h | 10 | 17,231 | 8,616 | 5,169 |
| long single lane + 1 km/h | 3 | 2,101 | 1,051 | 630 |
| long single lane + 1 km/h | 5 | 6,409 | 3,205 | 1,923 |
| long single lane + 1 km/h | 10 | 17,231 | 8,616 | 5,169 |
| crane 0.5 h | 3 | 1,429 | 714 | 429 |
| crane 0.5 h | 5 | 4,339 | 2,170 | 1,302 |
| crane 0.5 h | 10 | 11,642 | 5,821 | 3,492 |

## Effect of a gate holding place Q_h = 1 (pull-in, S = 1, T for K = 1 / 2 / 3, h)

| Scenario | n_v | Q_h = 0 | Q_h = 1 |
|---|---:|---|---|
| base | 3 | 3.38 / 3.00 / 3.00 | 3.38 / 3.00 / 3.00 |
| base | 5 | 6.71 / 5.00 / 5.00 | 6.71 / 5.00 / 5.00 |
| base | 10 | 15.05 / 10.00 / 10.00 | 15.05 / 10.00 / 10.00 |
| long corridor + 1 km/h | 3 | 5.23 / 4.15 / 4.15 | 5.23 / 4.15 / 4.15 |
| long corridor + 1 km/h | 5 | 11.99 / 8.69 / 8.69 | 11.99 / 8.05 / 7.42 |
| long corridor + 1 km/h | 10 | 28.91 / 20.05 / 20.05 | 28.91 / 16.37 / 17.27 |
| long single lane + 1 km/h | 3 | 5.23 / 4.15 / 4.15 | 5.23 / 4.15 / 4.15 |
| long single lane + 1 km/h | 5 | 11.99 / 8.69 / 8.69 | 11.99 / 8.38 / 7.86 |
| long single lane + 1 km/h | 10 | 28.91 / 20.05 / 20.05 | 28.91 / 18.25 / 18.38 |
| crane 0.5 h | 3 | 2.85 / 2.12 / 2.12 | 2.85 / 2.12 / 2.12 |
| crane 0.5 h | 5 | 6.18 / 3.95 / 3.95 | 6.18 / 3.98 / 3.74 |
| crane 0.5 h | 10 | 14.52 / 8.54 / 8.54 | 14.52 / 8.29 / 8.11 |

## Saving per voyage from one more cradle (S = 0→1, 1→3) and berthings to amortise it (pull-in, Q_h = 0, 140k €/day)

| Scenario | n_v | K | S 0→1: h (berthings) | S 1→3: h (berthings) |
|---|---:|---:|---|---|
| base | 3 | 1 | 0.11 (95.3) | 0.38 (54.3) |
| base | 3 | 2 | 0.00 (—) | 0.00 (—) |
| base | 5 | 1 | -0.70 (—) | 1.71 (12.0) |
| base | 5 | 2 | 0.00 (—) | 0.00 (—) |
| base | 10 | 1 | -2.72 (—) | 3.25 (6.3) |
| base | 10 | 2 | 0.00 (—) | 0.00 (—) |
| long corridor + 1 km/h | 3 | 1 | 1.78 (5.8) | 2.23 (9.2) |
| long corridor + 1 km/h | 3 | 2 | 0.72 (14.3) | 1.15 (17.9) |
| long corridor + 1 km/h | 5 | 1 | 1.11 (9.2) | 6.72 (3.1) |
| long corridor + 1 km/h | 5 | 2 | 0.05 (205.7) | 3.69 (5.6) |
| long corridor + 1 km/h | 10 | 1 | -0.56 (—) | 6.72 (3.1) |
| long corridor + 1 km/h | 10 | 2 | -1.62 (—) | 4.41 (4.7) |
| long single lane + 1 km/h | 3 | 1 | 1.78 (5.8) | 2.23 (9.2) |
| long single lane + 1 km/h | 3 | 2 | 0.72 (14.3) | 1.15 (17.9) |
| long single lane + 1 km/h | 5 | 1 | 1.11 (9.2) | 6.72 (3.1) |
| long single lane + 1 km/h | 5 | 2 | 0.05 (205.7) | 3.69 (5.6) |
| long single lane + 1 km/h | 10 | 1 | -0.56 (—) | 6.72 (3.1) |
| long single lane + 1 km/h | 10 | 2 | -1.62 (—) | 4.41 (4.7) |
| crane 0.5 h | 3 | 1 | 0.08 (124.1) | 1.35 (15.2) |
| crane 0.5 h | 3 | 2 | -0.40 (—) | 0.62 (33.2) |
| crane 0.5 h | 5 | 1 | -0.78 (—) | 3.31 (6.2) |
| crane 0.5 h | 5 | 2 | -0.99 (—) | 1.45 (14.2) |
| crane 0.5 h | 10 | 1 | -2.92 (—) | 3.31 (6.2) |
| crane 0.5 h | 10 | 2 | -2.57 (—) | 1.67 (12.3) |

## Cheapest configuration (sensitivity: cost per voyage = vessel time cost + rent of K vehicle sets over a voyage cycle of C days (working rate, no supervisor) + cradle cost per project amortised over 10 berthings; K ≤ 3, S ∈ {0, 1, 3}, mixed lifting (x = 0) included; pull-in, Q_h = 0)

| Scenario | n_v | Day rate €/day | C = 3 days | C = 6 days | C = 10 days |
|---|---:|---:|---|---|---|
| base | 3 | 140,000 | S = 0 direct lift, K = 1 (T = 3.49 h, 41,938 €) | S = 0 direct lift, K = 1 (T = 3.49 h, 63,538 €) | S = 0 direct lift, K = 1 (T = 3.49 h, 92,338 €) |
| base | 3 | 150,000 | S = 0 direct lift, K = 1 (T = 3.49 h, 43,391 €) | S = 0 direct lift, K = 1 (T = 3.49 h, 64,991 €) | S = 0 direct lift, K = 1 (T = 3.49 h, 93,791 €) |
| base | 3 | 250,000 | S = 0 direct lift, K = 1 (T = 3.49 h, 57,918 €) | S = 0 direct lift, K = 1 (T = 3.49 h, 79,518 €) | S = 0 direct lift, K = 1 (T = 3.49 h, 108,318 €) |
| base | 5 | 140,000 | S = 0 direct lift, K = 1 (T = 6.01 h, 56,653 €) | S = 0 direct lift, K = 1 (T = 6.01 h, 78,253 €) | S = 0 direct lift, K = 1 (T = 6.01 h, 107,053 €) |
| base | 5 | 150,000 | S = 0 direct lift, K = 1 (T = 6.01 h, 59,157 €) | S = 0 direct lift, K = 1 (T = 6.01 h, 80,757 €) | S = 0 direct lift, K = 1 (T = 6.01 h, 109,557 €) |
| base | 5 | 250,000 | S = 0 direct lift, K = 1 (T = 6.01 h, 84,195 €) | S = 0 direct lift, K = 1 (T = 6.01 h, 105,795 €) | S = 0 direct lift, K = 1 (T = 6.01 h, 134,595 €) |
| base | 10 | 140,000 | S = 0 direct lift, K = 1 (T = 12.33 h, 93,519 €) | S = 0 direct lift, K = 1 (T = 12.33 h, 115,119 €) | S = 0 direct lift, K = 1 (T = 12.33 h, 143,919 €) |
| base | 10 | 150,000 | S = 0 direct lift, K = 1 (T = 12.33 h, 98,656 €) | S = 0 direct lift, K = 1 (T = 12.33 h, 120,256 €) | S = 0 direct lift, K = 1 (T = 12.33 h, 149,056 €) |
| base | 10 | 250,000 | S = 0 direct lift, K = 2 (T = 10.0 h, 147,367 €) | S = 3 mixed lifting, K = 1 (T = 10.5 h, 170,571 €) | S = 3 mixed lifting, K = 1 (T = 10.5 h, 199,371 €) |
| long corridor + 1 km/h | 3 | 140,000 | S = 1 mixed lifting, K = 1 (T = 4.81 h, 55,636 €) | S = 1 mixed lifting, K = 1 (T = 4.81 h, 77,236 €) | S = 1 mixed lifting, K = 1 (T = 4.81 h, 106,036 €) |
| long corridor + 1 km/h | 3 | 150,000 | S = 1 mixed lifting, K = 1 (T = 4.81 h, 57,639 €) | S = 1 mixed lifting, K = 1 (T = 4.81 h, 79,239 €) | S = 1 mixed lifting, K = 1 (T = 4.81 h, 108,039 €) |
| long corridor + 1 km/h | 3 | 250,000 | S = 3 cradle, K = 1 (T = 3.0 h, 70,850 €) | S = 3 cradle, K = 1 (T = 3.0 h, 92,450 €) | S = 3 cradle, K = 1 (T = 3.0 h, 121,250 €) |
| long corridor + 1 km/h | 5 | 140,000 | S = 3 mixed lifting, K = 1 (T = 5.0 h, 68,767 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 90,367 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 119,167 €) |
| long corridor + 1 km/h | 5 | 150,000 | S = 3 mixed lifting, K = 1 (T = 5.0 h, 70,850 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 92,450 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 121,250 €) |
| long corridor + 1 km/h | 5 | 250,000 | S = 3 mixed lifting, K = 1 (T = 5.0 h, 91,683 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 113,283 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 142,083 €) |
| long corridor + 1 km/h | 10 | 140,000 | S = 3 mixed lifting, K = 2 (T = 13.87 h, 142,115 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 179,292 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 208,092 €) |
| long corridor + 1 km/h | 10 | 150,000 | S = 3 mixed lifting, K = 2 (T = 13.87 h, 147,894 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 187,727 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 216,527 €) |
| long corridor + 1 km/h | 10 | 250,000 | S = 3 mixed lifting, K = 2 (T = 13.87 h, 205,691 €) | S = 3 mixed lifting, K = 2 (T = 13.87 h, 248,891 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 300,878 €) |
| long single lane + 1 km/h | 3 | 140,000 | S = 1 mixed lifting, K = 1 (T = 4.81 h, 55,636 €) | S = 1 mixed lifting, K = 1 (T = 4.81 h, 77,236 €) | S = 1 mixed lifting, K = 1 (T = 4.81 h, 106,036 €) |
| long single lane + 1 km/h | 3 | 150,000 | S = 1 mixed lifting, K = 1 (T = 4.81 h, 57,639 €) | S = 1 mixed lifting, K = 1 (T = 4.81 h, 79,239 €) | S = 1 mixed lifting, K = 1 (T = 4.81 h, 108,039 €) |
| long single lane + 1 km/h | 3 | 250,000 | S = 3 cradle, K = 1 (T = 3.0 h, 70,850 €) | S = 3 cradle, K = 1 (T = 3.0 h, 92,450 €) | S = 3 cradle, K = 1 (T = 3.0 h, 121,250 €) |
| long single lane + 1 km/h | 5 | 140,000 | S = 3 mixed lifting, K = 1 (T = 5.0 h, 68,767 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 90,367 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 119,167 €) |
| long single lane + 1 km/h | 5 | 150,000 | S = 3 mixed lifting, K = 1 (T = 5.0 h, 70,850 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 92,450 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 121,250 €) |
| long single lane + 1 km/h | 5 | 250,000 | S = 3 mixed lifting, K = 1 (T = 5.0 h, 91,683 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 113,283 €) | S = 3 mixed lifting, K = 1 (T = 5.0 h, 142,083 €) |
| long single lane + 1 km/h | 10 | 140,000 | S = 3 mixed lifting, K = 2 (T = 13.87 h, 142,115 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 179,292 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 208,092 €) |
| long single lane + 1 km/h | 10 | 150,000 | S = 3 mixed lifting, K = 2 (T = 13.87 h, 147,894 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 187,727 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 216,527 €) |
| long single lane + 1 km/h | 10 | 250,000 | S = 3 mixed lifting, K = 2 (T = 13.87 h, 205,691 €) | S = 3 mixed lifting, K = 2 (T = 13.87 h, 248,891 €) | S = 3 mixed lifting, K = 1 (T = 20.24 h, 300,878 €) |
| crane 0.5 h | 3 | 140,000 | S = 0 direct lift, K = 1 (T = 2.94 h, 38,730 €) | S = 0 direct lift, K = 1 (T = 2.94 h, 60,330 €) | S = 0 direct lift, K = 1 (T = 2.94 h, 89,130 €) |
| crane 0.5 h | 3 | 150,000 | S = 0 direct lift, K = 1 (T = 2.94 h, 39,954 €) | S = 0 direct lift, K = 1 (T = 2.94 h, 61,554 €) | S = 0 direct lift, K = 1 (T = 2.94 h, 90,354 €) |
| crane 0.5 h | 3 | 250,000 | S = 1 mixed lifting, K = 1 (T = 2.22 h, 50,754 €) | S = 1 mixed lifting, K = 1 (T = 2.22 h, 72,354 €) | S = 1 mixed lifting, K = 1 (T = 2.22 h, 101,154 €) |
| crane 0.5 h | 5 | 140,000 | S = 0 direct lift, K = 1 (T = 5.41 h, 53,153 €) | S = 0 direct lift, K = 1 (T = 5.41 h, 74,753 €) | S = 0 direct lift, K = 1 (T = 5.41 h, 103,553 €) |
| crane 0.5 h | 5 | 150,000 | S = 3 mixed lifting, K = 1 (T = 2.5 h, 55,225 €) | S = 3 mixed lifting, K = 1 (T = 2.5 h, 76,825 €) | S = 3 mixed lifting, K = 1 (T = 2.5 h, 105,625 €) |
| crane 0.5 h | 5 | 250,000 | S = 3 mixed lifting, K = 1 (T = 2.5 h, 65,642 €) | S = 3 mixed lifting, K = 1 (T = 2.5 h, 87,242 €) | S = 3 mixed lifting, K = 1 (T = 2.5 h, 116,042 €) |
| crane 0.5 h | 10 | 140,000 | S = 0 direct lift, K = 2 (T = 5.96 h, 77,985 €) | S = 0 direct lift, K = 1 (T = 11.6 h, 110,890 €) | S = 0 direct lift, K = 1 (T = 11.6 h, 139,690 €) |
| crane 0.5 h | 10 | 150,000 | S = 0 direct lift, K = 2 (T = 5.96 h, 80,470 €) | S = 3 mixed lifting, K = 1 (T = 8.69 h, 115,543 €) | S = 3 mixed lifting, K = 1 (T = 8.69 h, 144,343 €) |
| crane 0.5 h | 10 | 250,000 | S = 0 direct lift, K = 2 (T = 5.96 h, 105,316 €) | S = 0 direct lift, K = 2 (T = 5.96 h, 148,516 €) | S = 3 mixed lifting, K = 1 (T = 8.69 h, 180,572 €) |
