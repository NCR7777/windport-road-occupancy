# Reproduction of public project figures (extra analyses, item 12)

## Rønne load-out: 3 piles per vessel, released 12 h before the installation vessel arrives (G = 12 h), crane 1 h (Kassels Fig. 19 mode)

Kassels model (Appendix F, zero-overlap schedule): TO1 (1 support; first lift the pile on the vehicle, the vehicle immediately fetches the third pile, then lift the pile on the support) 3.311 h, TO2 (2 supports) 2.994 h; validation run 3.316 h (Appendix E). Rønne geometry: shortest distance from the saddle rows to the cradle position 250 m (Appendix D, storage area → quayside location). Rønne handling: pick-up and set-down at the Fig. 19 modes (load-out from the vehicle 2 h = h_p, load-out from the support 2.5 h = h_p + h_d), driving counted separately by distance (§4.3: process module + transport module). The "Kassels order" follows the lifting order of §4.3 (one pile pre-placed on 1 support and one on the vehicle; first lift the pile on the vehicle, the vehicle immediately fetches the third pile, then lift the pile on the support), computed with this model's travel times; it is meaningful only for the TO1 configuration (S = 1 mixed lifting, 1 fleet), other rows are left blank; L*(3) is a lower bound for any dispatch. The simulation is first-come-first-served (the pile booked first is lifted first).

| Geometry | Route m | Handling | Cradle | Lifting | K | Simulated port time h | Kassels order h (TO1 only) | L*(3) h | Lifting mode per pile |
|---|---:|---|---|---|---:|---:|---:|---:|---|
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 0 direct lift | 1 | 3.00 |  | 3.00 | direct/direct/direct |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 0 direct lift | 1 | 5.76 |  | 5.57 | direct/direct/direct |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 0 direct lift | 2 | 3.00 |  | 3.00 | direct/direct/direct |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 0 direct lift | 2 | 3.38 |  | 3.29 | direct/direct/direct |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 1 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 cradle | 1 | 4.45 |  | 3.79 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 1 mixed lifting | 1 | 3.00 | 3.00 | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 mixed lifting | 1 | 3.97 | 3.32 | 3.29 | cradle/cradle/direct |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | roadside cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 0 direct lift | 1 | 3.00 |  | 3.00 | direct/direct/direct |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 0 direct lift | 1 | 5.79 |  | 5.57 | direct/direct/direct |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 0 direct lift | 2 | 3.00 |  | 3.00 | direct/direct/direct |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 0 direct lift | 2 | 3.40 |  | 3.29 | direct/direct/direct |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 1 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 cradle | 1 | 4.45 |  | 3.79 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 1 mixed lifting | 1 | 3.00 | 3.00 | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 mixed lifting | 1 | 3.98 | 3.33 | 3.29 | cradle/cradle/direct |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this manuscript 30 + 30 min | pull-in cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 0 direct lift | 1 | 3.30 |  | 3.11 | direct/direct/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 0 direct lift | 1 | 6.30 |  | 6.11 | direct/direct/direct |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 0 direct lift | 2 | 3.00 |  | 3.00 | direct/direct/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 0 direct lift | 2 | 3.65 |  | 3.56 | direct/direct/direct |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 1 cradle | 1 | 3.22 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 cradle | 1 | 4.72 |  | 4.06 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 1 mixed lifting | 1 | 3.00 | 3.00 | 3.00 | cradle/cradle/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 mixed lifting | 1 | 4.24 | 3.59 | 3.56 | cradle/cradle/direct |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | roadside cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 0 direct lift | 1 | 3.33 |  | 3.11 | direct/direct/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 0 direct lift | 1 | 6.33 |  | 6.11 | direct/direct/direct |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 0 direct lift | 2 | 3.00 |  | 3.00 | direct/direct/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 0 direct lift | 2 | 3.67 |  | 3.56 | direct/direct/direct |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 1 cradle | 1 | 3.22 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 cradle | 1 | 4.72 |  | 4.06 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 1 mixed lifting | 1 | 3.00 | 3.00 | 3.00 | cradle/cradle/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 mixed lifting | 1 | 4.25 | 3.60 | 3.56 | cradle/cradle/direct |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this manuscript 30 + 30 min | pull-in cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |

## Rønne unloading (barge): 3 piles, ramp always open, shortest ramp-to-saddle-row distance about 400 m

Kassels model TI0 (no temporary supports): mean barge port time 12.940 h (Appendix F); unloading time triangular 3/4/5 h (Fig. 19, mean 4 h; includes ramp installation, ballasting, jacking onto the saddles, grillage removal), and the vehicle is released on reaching the yard (§4.3). This manuscript records the 3rd pile's vehicle tail leaving the ramp (F_ramp) and its set-down on the saddles (F_yard); the gap is decomposed by source at the mean of 4 h.

| K | RoRo h | Variant | Route m | 3rd pile leaves ramp h | 3rd pile set on saddles h |
|---:|---:|---|---:|---:|---:|
| 1 | 3.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 11.28 | 12.06 |
| 1 | 3.0 | no saddle set-down (h_y = 0) | 445.0 | 10.28 | 10.56 |
| 1 | 3.0 | turning without stopping | 445.0 | 10.80 | 11.45 |
| 1 | 3.0 | both removed | 445.0 | 9.80 | 9.95 |
| 1 | 4.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 14.28 | 15.06 |
| 1 | 4.0 | no saddle set-down (h_y = 0) | 445.0 | 13.28 | 13.56 |
| 1 | 4.0 | turning without stopping | 445.0 | 13.80 | 14.45 |
| 1 | 4.0 | both removed | 445.0 | 12.80 | 12.95 |
| 1 | 5.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 17.28 | 18.06 |
| 1 | 5.0 | no saddle set-down (h_y = 0) | 445.0 | 16.28 | 16.56 |
| 1 | 5.0 | turning without stopping | 445.0 | 16.80 | 17.45 |
| 1 | 5.0 | both removed | 445.0 | 15.80 | 15.95 |
| 2 | 3.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 9.98 | 10.77 |
| 2 | 3.0 | no saddle set-down (h_y = 0) | 445.0 | 9.98 | 10.27 |
| 2 | 3.0 | turning without stopping | 445.0 | 9.64 | 10.29 |
| 2 | 3.0 | both removed | 445.0 | 9.64 | 9.79 |
| 2 | 4.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 12.98 | 13.77 |
| 2 | 4.0 | no saddle set-down (h_y = 0) | 445.0 | 12.98 | 13.27 |
| 2 | 4.0 | turning without stopping | 445.0 | 12.64 | 13.29 |
| 2 | 4.0 | both removed | 445.0 | 12.64 | 12.79 |
| 2 | 5.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 15.98 | 16.77 |
| 2 | 5.0 | no saddle set-down (h_y = 0) | 445.0 | 15.98 | 16.27 |
| 2 | 5.0 | turning without stopping | 445.0 | 15.64 | 16.29 |
| 2 | 5.0 | both removed | 445.0 | 15.64 | 15.79 |

## Eemshaven unloading 1 → 2 piles per tide (Theorem 3): A1 base geometry, 3 piles released per tide, 4 tides

Each cell: piles unloaded in each tide in the simulation (/-separated); in parentheses the Theorem 3 per-tide upper bound. ρ is the ramp operation (on-vessel work + empty and loaded driving on the ramp), c_u the minimum interval between two consecutive ramp operations of one fleet.

| K | Tidal window h | On-vessel work 1.5 h | On-vessel work 2.0 h | On-vessel work 2.5 h | On-vessel work 3.0 h | On-vessel work 3.5 h | On-vessel work 4.0 h |
|---:|---:|---|---|---|---|---|---|
| 1 | 4.0 | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 0/0/0/0 (0/0/0/0) |
| 1 | 5.0 | 2/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) |
| 1 | 6.0 | 2/2/2/2 (2/2/2/2) | 2/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) |
| 2 | 4.0 | 1/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 0/0/0/0 (0/0/0/0) |
| 2 | 5.0 | 2/2/2/2 (3/3/3/3) | 1/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) |
| 2 | 6.0 | 2/2/2/2 (3/3/3/3) | 2/2/2/2 (2/2/2/2) | 1/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) |

ρ, c_u (h): on-vessel 1.5 h → ρ = 1.64, c_u = 3.01; on-vessel 2.0 h → ρ = 2.14, c_u = 3.51; on-vessel 2.5 h → ρ = 2.64, c_u = 4.01; on-vessel 3.0 h → ρ = 3.14, c_u = 4.51; on-vessel 3.5 h → ρ = 3.64, c_u = 5.01; on-vessel 4.0 h → ρ = 4.14, c_u = 5.51.
Shortening on-vessel work shortens both ρ and c_u: with one fleet, 2 piles per tide require ρ + c_u ≤ L (fleet term); with two fleets, only ρ ≤ L/2 (ramp term).
