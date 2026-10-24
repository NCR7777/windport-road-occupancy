# Supporting numbers: plateaus, mixed lifting, cost footnote

## Three plateaus (A1, L = 12 h, G = 24 h, pull-in): rate-bound plateau ⌈K†⌉, rule-free plateau within the window (smallest K at which W1′ reaches its maximum), first-come-first-served / convoy-dispatch plateau

| Scenario | S | K† | ⌈K†⌉ | W1′ plateau (piles) | First-come-first-served plateau (piles) | Convoy plateau (piles) |
|---|---:|---:|---:|---|---|---|
| base | 0 | 4.707 | 5 | K=2 (12) | K=2 (12) | K=2 (12) |
| base | 1 | 6.782 | 7 | K=2 (12) | K=2 (12) | K=2 (12) |
| base | 3 | 6.782 | 7 | K=2 (12) | K=2 (12) | K=2 (12) |
| base | 6 | 6.782 | 7 | K=1 (12) | K=1 (12) | K=1 (12) |
| long single lane + 1 km/h | 0 | 1.674 | 2 | K=2 (8) | K=2 (6) | K=2 (6) |
| long single lane + 1 km/h | 1 | 1.971 | 2 | K=2 (9) | K=2 (6) | K=2 (6) |
| long single lane + 1 km/h | 3 | 1.971 | 2 | K=3 (12) | K=2 (8) | K=2 (8) |
| long single lane + 1 km/h | 6 | 1.971 | 2 | K=2 (12) | K=2 (11) | K=2 (11) |

## Cradle and mixed lifting (x = 0) compared: A1, pull-in, L = 12 h, G = 24 h, first-come-first-served (piles; cradle / mixed)

| Scenario | S | K = 1 | 2 | 3 | 4 | 6 | 10 |
|---|---:|---|---|---|---|---|---|
| base | 1 | 8 / 10 | 12 / 12 | 12 / 12 | 12 / 12 | 12 / 12 | 12 / 12 |
| base | 3 | 10 / 11 | 12 / 12 | 12 / 12 | 12 / 12 | 12 / 12 | 12 / 12 |
| base | 6 | 12 / 12 | 12 / 12 | 12 / 12 | 12 / 12 | 12 / 12 | 12 / 12 |
| long single lane + 1 km/h | 1 | 5 / 5 | 6 / 7 | 6 / 7 | 6 / 7 | 6 / 7 | 6 / 7 |
| long single lane + 1 km/h | 3 | 6 / 7 | 8 / 9 | 8 / 9 | 8 / 9 | 8 / 9 | 8 / 9 |
| long single lane + 1 km/h | 6 | 9 / 9 | 11 / 11 | 11 / 11 | 11 / 11 | 11 / 11 | 11 / 11 |

## Rule 6 (lift from the vehicle when x·p ≤ h_d) at Okpo: port time for one vessel with 10 piles (h), cradle / mixed lifting (x = 0, satisfying x·p = 0 ≤ h_d = 0.5 h)

| Storage area | Scenario | Cradle type | S | K = 1 | 2 | 4 | 8 |
|---|---|---|---:|---|---|---|---|
| one-voyage | base | pull-in | 1 | 12.78 / 10.28 | 10.00 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 |
| one-voyage | base | pull-in | 3 | 10.00 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 |
| one-voyage | base | roadside | 1 | 12.78 / 10.16 | 10.00 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 |
| one-voyage | base | roadside | 3 | 10.00 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 |
| one-voyage | 1 km/h | pull-in | 1 | 15.75 / 12.99 | 10.05 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 |
| one-voyage | 1 km/h | pull-in | 3 | 11.19 / 10.23 | 10.00 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 |
| one-voyage | 1 km/h | roadside | 1 | 15.75 / 12.24 | 10.05 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 |
| one-voyage | 1 km/h | roadside | 3 | 11.19 / 10.23 | 10.00 / 10.00 | 10.00 / 10.00 | 10.00 / 10.00 |
| three-voyage | base | pull-in | 1 | 26.29 / 22.98 | 20.42 / 17.11 | 20.42 / 17.11 | 20.42 / 17.11 |
| three-voyage | base | pull-in | 3 | 19.92 / 17.86 | 15.23 / 13.47 | 10.00 / 10.00 | 10.00 / 10.00 |
| three-voyage | base | roadside | 1 | 26.29 / 22.67 | 20.42 / 16.80 | 20.42 / 16.80 | 20.42 / 16.80 |
| three-voyage | base | roadside | 3 | 20.05 / 17.99 | 15.23 / 13.47 | 15.23 / 13.47 | 15.23 / 13.47 |
| three-voyage | 1 km/h | pull-in | 1 | 42.49 / 39.73 | 34.91 / 32.15 | 34.91 / 32.15 | 34.91 / 32.15 |
| three-voyage | 1 km/h | pull-in | 3 | 31.73 / 29.73 | 25.50 / 23.51 | 25.50 / 23.51 | 25.50 / 23.51 |
| three-voyage | 1 km/h | roadside | 1 | 42.49 / 38.95 | 34.91 / 31.37 | 34.91 / 31.37 | 34.91 / 31.37 |
| three-voyage | 1 km/h | roadside | 3 | 31.73 / 29.73 | 25.50 / 23.51 | 25.50 / 23.51 | 25.50 / 23.51 |

Cells where mixed lifting is slower than cradle: 0 / 64 (x = 0 satisfies x·p ≤ h_d; when x·p > h_d, mixed lifting becomes slower than cradle, see Section 6 of the extra analyses).

## Numbers for the Table 10 charter-cost footnote

For one vessel with 10 piles, pull-in S = 1, going from K = 1 to K = 2 saves 5.05–8.86 h per voyage (four scenarios), i.e. 29,452–51,695 € at 140,000 €/day. The break-even in Table 10 assumes continuous charter (the second fleet is hired for the whole voyage cycle of C days; 43,200 €/voyage at C = 6 days); if charged only for days in port with a minimum of 1 day, the second fleet costs 7,200 € per voyage.
