# Gate holding place Q_h (A1, cradle mode and direct lift, L × K × S × G, 576 points per cell)

Note: delivery is not necessarily monotone in Q_h (e.g. 1 km/h roadside cradle, Q_h = 2 delivers more than unlimited; crane 0.5 h roadside cradle, the share at the bound for Q_h = 1, 2 is below that for 0). This is an artefact of the first-come-first-served rule: a vehicle parked at the gate must still cross the single lane against the flow on its next trip, and the rule does not choose the timing; the E4-E7 batches use bottleneck-queued convoy dispatch as the comparison. "Unlimited" coincides with the original model only in how an idle gate is handled.

| Scenario | Cradle | Q_h | Simulated units total | W1 total | Share at the bound | Departures to holding place / to storage-yard side (trips) |
|---|---|---|---:|---:|---:|---|
| base | on_road | 0 | 5291 | 5340 | 92.5% | 0 / 6761 |
| base | on_road | 1 | 5291 | 5340 | 92.5% | 2732 / 4036 |
| base | on_road | 2 | 5291 | 5340 | 92.5% | 4484 / 2284 |
| base | on_road | inf | 5291 | 5340 | 92.5% | 6768 / 0 |
| base | pull_in | 0 | 5304 | 5340 | 94.3% | 0 / 6782 |
| base | pull_in | 1 | 5304 | 5340 | 94.3% | 2746 / 4036 |
| base | pull_in | 2 | 5304 | 5340 | 94.3% | 4498 / 2284 |
| base | pull_in | inf | 5304 | 5340 | 94.3% | 6782 / 0 |
| 1 km/h | on_road | 0 | 4376 | 5155 | 43.8% | 0 / 5791 |
| 1 km/h | on_road | 1 | 4462 | 5155 | 41.7% | 2343 / 3539 |
| 1 km/h | on_road | 2 | 4614 | 5155 | 47.4% | 3957 / 2079 |
| 1 km/h | on_road | inf | 4975 | 5155 | 83.5% | 6402 / 0 |
| 1 km/h | pull_in | 0 | 4434 | 5155 | 45.5% | 0 / 5858 |
| 1 km/h | pull_in | 1 | 4614 | 5155 | 52.9% | 2393 / 3652 |
| 1 km/h | pull_in | 2 | 4745 | 5155 | 58.3% | 4035 / 2142 |
| 1 km/h | pull_in | inf | 4997 | 5155 | 84.9% | 6433 / 0 |
| long corridor + 1 km/h | on_road | 0 | 2928 | 4778 | 27.8% | 0 / 4281 |
| long corridor + 1 km/h | on_road | 1 | 3235 | 4778 | 33.0% | 1885 / 2722 |
| long corridor + 1 km/h | on_road | 2 | 3518 | 4778 | 36.5% | 3241 / 1656 |
| long corridor + 1 km/h | on_road | inf | 3884 | 4778 | 41.8% | 5269 / 0 |
| long corridor + 1 km/h | pull_in | 0 | 2939 | 4778 | 28.0% | 0 / 4298 |
| long corridor + 1 km/h | pull_in | 1 | 3292 | 4778 | 34.4% | 1907 / 2770 |
| long corridor + 1 km/h | pull_in | 2 | 3581 | 4778 | 38.4% | 3292 / 1681 |
| long corridor + 1 km/h | pull_in | inf | 3947 | 4778 | 43.9% | 5341 / 0 |
| long single lane (one segment) + 1 km/h | on_road | 0 | 2928 | 3995 | 27.8% | 0 / 4281 |
| long single lane (one segment) + 1 km/h | on_road | 1 | 3079 | 3995 | 34.9% | 1829 / 2606 |
| long single lane (one segment) + 1 km/h | on_road | 2 | 3200 | 3995 | 39.2% | 3045 / 1519 |
| long single lane (one segment) + 1 km/h | on_road | inf | 3379 | 3995 | 45.1% | 4745 / 0 |
| long single lane (one segment) + 1 km/h | pull_in | 0 | 2939 | 3995 | 28.0% | 0 / 4298 |
| long single lane (one segment) + 1 km/h | pull_in | 1 | 3149 | 3995 | 35.1% | 1862 / 2652 |
| long single lane (one segment) + 1 km/h | pull_in | 2 | 3275 | 3995 | 39.9% | 3097 / 1551 |
| long single lane (one segment) + 1 km/h | pull_in | inf | 3435 | 3995 | 46.5% | 4810 / 0 |
| crane 0.5 h | on_road | 0 | 6745 | 9054 | 21.2% | 0 / 8153 |
| crane 0.5 h | on_road | 1 | 6883 | 9054 | 20.8% | 3169 / 5133 |
| crane 0.5 h | on_road | 2 | 7065 | 9054 | 19.4% | 5421 / 3070 |
| crane 0.5 h | on_road | inf | 7534 | 9054 | 19.1% | 8960 / 0 |
| crane 0.5 h | pull_in | 0 | 8008 | 9588 | 31.9% | 0 / 9442 |
| crane 0.5 h | pull_in | 1 | 8235 | 9588 | 34.7% | 3523 / 6148 |
| crane 0.5 h | pull_in | 2 | 8353 | 9588 | 34.0% | 6074 / 3715 |
| crane 0.5 h | pull_in | inf | 8764 | 9588 | 56.2% | 10200 / 0 |
