# Recheck with the corrected W′ (return-trip occupancy = minimum over the return-trip routes)

| Batch | Rows | Rows with smaller return occupancy | Rows with changed W′ | ΣW′ before → after | Recorded ≠ recomputed before | Sim > W′ before / after | Ties before → after | Rows with changed L* |
|---|---:|---:|---:|---|---:|---|---|---:|
| extra:mix6 | 1440 | 0 | 0 | 16924 → 16924 | 0 | 0 / 0 | 917 → 917 |  |
| extra:port | 7200 | 0 | 0 | 46610 → 46610 | 0 | 0 / 0 | 5810 → 5810 | 0 |
| extra:pub | 96 | 0 | 0 | 302 → 302 | 0 | 0 / 0 | 86 → 86 | 0 |
| extra:sens | 3160 | 0 | 0 | 74190 → 74190 | 0 | 0 / 0 | 1605 → 1605 |  |
| extra:sens5 | 192 | 0 | 0 | 4080 → 4080 | 0 | 0 / 0 | 48 → 48 |  |
| runs:conv | 23040 | 0 | 0 | 229207 → 229207 | 0 | 0 / 0 | 15006 → 15006 |  |
| runs:e2c | 540 | 0 | 0 | 1647 → 1647 | 0 | 0 / 0 | 386 → 386 |  |
| runs:e4 | 10080 | 0 | 0 | 122790 → 122790 | 0 | 0 / 0 | 7336 → 7336 |  |
| runs:e5 | 2560 | 0 | 0 | 57840 → 57840 | 0 | 0 / 0 | 918 → 918 |  |
| runs:e6 | 5376 | 0 | 0 | 79420 → 79420 | 0 | 0 / 0 | 3985 → 3985 |  |
| runs:e7 | 192 | 0 | 0 | 2032 → 2032 | 0 | 0 / 0 | 96 → 96 |  |
| runs:pocket | 12672 | 0 | 0 | 113563 → 113563 | 0 | 0 / 0 | 8417 → 8417 |  |
| runs:random | 20000 | 175 | 2 | 178972 → 178975 | 0 | 0 / 0 | 11738 → 11738 |  |
| runs:sens | 10344 | 0 | 0 | 178168 → 178168 | 0 | 0 / 0 | 5517 → 5517 |  |
| runs:sens7 | 544 | 0 | 0 | 5383 → 5383 | 0 | 0 / 0 | 219 → 219 |  |

Table 2 (E2): of 533 proven optima, = W′ in 388 → 388 cases; Σ(W′ − optimum) 171 → 171; CP-SAT best solution > corrected W′ in 0 cases.

Table 4 (E6, FCFS):
| Shipyard | Scenario | Cradle | Points | Ties before → after | W′ changed | Above corrected W′ |
|---|---|---|---:|---|---:|---:|
| okpo | base | on_road | 320 | 293 → 293 | 0 | 0 |
| okpo | base | pull_in | 320 | 293 → 293 | 0 | 0 |
| okpo | fastcrane | on_road | 320 | 100 → 100 | 0 | 0 |
| okpo | fastcrane | pull_in | 320 | 192 → 192 | 0 | 0 |
| okpo | slow | on_road | 320 | 283 → 283 | 0 | 0 |
| okpo | slow | pull_in | 320 | 283 → 283 | 0 | 0 |
| yantai | base | on_road | 128 | 116 → 116 | 0 | 0 |
| yantai | base | pull_in | 128 | 116 → 116 | 0 | 0 |
| yantai | fastcrane | on_road | 128 | 48 → 48 | 0 | 0 |
| yantai | fastcrane | pull_in | 128 | 48 → 48 | 0 | 0 |
| yantai | slow | on_road | 128 | 108 → 108 | 0 | 0 |
| yantai | slow | pull_in | 128 | 108 → 108 | 0 | 0 |
