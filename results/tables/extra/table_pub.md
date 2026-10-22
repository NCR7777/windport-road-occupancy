# Reproduction of public project figures

## Rønne load-out: 3 monopiles per vessel, released 12 h before the installation vessel arrives (G = 12 h), ship crane 1 h (mode of Kassels Fig. 19)

Kassels model (Appendix F, zero-overlap schedule): TO1 (1 support; first lift the pile on the vehicle while the vehicle immediately fetches the third pile, then lift the pile on the support) 3.311 h, TO2 (2 supports) 2.994 h; validation run 3.316 h (Appendix E). Rønne geometry: shortest distance from the saddle row to the cradle position 250 m (storage area → quayside location in Appendix D). Rønne handling: pick-up and set-down follow the modes of Fig. 19 (load-out from the vehicle 2 h = h_p, from a support 2.5 h = h_p + h_d), with driving counted separately by distance (§4.3: process module + transport module). "Kassels order" applies the lift order of §4.3 (one pile pre-placed on 1 support and one on the vehicle; first lift the pile on the vehicle while the vehicle immediately fetches the third pile, then lift the pile on the support) with the travel times of this model; it is meaningful only for the TO1 configuration (S = 1 mixed lifting, 1 vehicle set) and is left blank in the other rows; L*(3) is a lower bound for any dispatch. The simulation is first-come-first-served (the pile booked first is lifted first).

| Geometry | Route m | Handling | Cradle | Lifting | K | Simulated port time h | Kassels order h (TO1 only) | L*(3) h | Lift mode per pile |
|---|---:|---|---|---|---:|---:|---:|---:|---|
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 0 direct lift | 1 | 3.00 |  | 3.00 | direct/direct/direct |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 0 direct lift | 1 | 5.62 |  | 5.57 | direct/direct/direct |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 0 direct lift | 2 | 3.00 |  | 3.00 | direct/direct/direct |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 0 direct lift | 2 | 3.30 |  | 3.29 | direct/direct/direct |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 1 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 cradle | 1 | 4.30 |  | 3.79 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 1 mixed lifting | 1 | 3.00 | 3.00 | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 mixed lifting | 1 | 3.80 | 3.29 | 3.29 | cradle/cradle/direct |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | roadside cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 0 direct lift | 1 | 3.00 |  | 3.00 | direct/direct/direct |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 0 direct lift | 1 | 5.64 |  | 5.57 | direct/direct/direct |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 0 direct lift | 2 | 3.00 |  | 3.00 | direct/direct/direct |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 0 direct lift | 2 | 3.30 |  | 3.29 | direct/direct/direct |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 1 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 cradle | 1 | 4.30 |  | 3.79 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 1 mixed lifting | 1 | 3.00 | 3.00 | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 mixed lifting | 1 | 3.80 | 3.29 | 3.29 | cradle/cradle/direct |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | this paper 30 + 30 min | pull-in cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| Rønne | 250.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 0 direct lift | 1 | 3.16 |  | 3.11 | direct/direct/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 0 direct lift | 1 | 6.16 |  | 6.11 | direct/direct/direct |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 0 direct lift | 2 | 3.00 |  | 3.00 | direct/direct/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 0 direct lift | 2 | 3.57 |  | 3.56 | direct/direct/direct |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 1 cradle | 1 | 3.07 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 cradle | 1 | 4.57 |  | 4.06 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 1 mixed lifting | 1 | 3.00 | 3.00 | 3.00 | cradle/cradle/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 mixed lifting | 1 | 4.07 | 3.56 | 3.56 | cradle/cradle/direct |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | roadside cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | roadside cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 0 direct lift | 1 | 3.18 |  | 3.11 | direct/direct/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 0 direct lift | 1 | 6.18 |  | 6.11 | direct/direct/direct |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 0 direct lift | 2 | 3.00 |  | 3.00 | direct/direct/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 0 direct lift | 2 | 3.57 |  | 3.56 | direct/direct/direct |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 1 cradle | 1 | 3.07 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 cradle | 1 | 4.57 |  | 4.06 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 1 mixed lifting | 1 | 3.00 | 3.00 | 3.00 | cradle/cradle/direct |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 mixed lifting | 1 | 4.07 | 3.56 | 3.56 | cradle/cradle/direct |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 1 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 mixed lifting | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 2 mixed lifting | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 3 cradle | 1 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | this paper 30 + 30 min | pull-in cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |
| A1 base | 700.0 | Rønne handling (h_p 2 h, h_d 0.5 h) | pull-in cradle | S = 3 cradle | 2 | 3.00 |  | 3.00 | cradle/cradle/cradle |

## Rønne load-in (barge): 3 monopiles, ramp always open, shortest ramp-to-saddle-row distance about 400 m

Kassels model TI0 (no temporary supports): mean barge port time 12.940 h (Appendix F); unloading duration triangular 3/4/5 h (Fig. 19, mean 4 h; includes ramp installation, ballasting, jacking onto saddles and grillage removal), and a vehicle is released on reaching the yard (§4.3). This paper records when the vehicle with the 3rd pile clears the ramp with its tail (F_ramp) and when that pile is set onto saddles (F_yard); the sources of the difference are separated at the mean of 4 h.

| K | RoRo h | Variant | Route m | 3rd pile clears ramp h | 3rd pile on saddles h |
|---:|---:|---|---:|---:|---:|
| 1 | 3.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 11.28 | 12.06 |
| 1 | 3.0 | no saddle set-down (h_y = 0) | 445.0 | 10.28 | 10.56 |
| 1 | 3.0 | turn without stopping | 445.0 | 10.80 | 11.45 |
| 1 | 3.0 | both removed | 445.0 | 9.80 | 9.95 |
| 1 | 4.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 14.28 | 15.06 |
| 1 | 4.0 | no saddle set-down (h_y = 0) | 445.0 | 13.28 | 13.56 |
| 1 | 4.0 | turn without stopping | 445.0 | 13.80 | 14.45 |
| 1 | 4.0 | both removed | 445.0 | 12.80 | 12.95 |
| 1 | 5.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 17.28 | 18.06 |
| 1 | 5.0 | no saddle set-down (h_y = 0) | 445.0 | 16.28 | 16.56 |
| 1 | 5.0 | turn without stopping | 445.0 | 16.80 | 17.45 |
| 1 | 5.0 | both removed | 445.0 | 15.80 | 15.95 |
| 2 | 3.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 9.98 | 10.77 |
| 2 | 3.0 | no saddle set-down (h_y = 0) | 445.0 | 9.98 | 10.27 |
| 2 | 3.0 | turn without stopping | 445.0 | 9.64 | 10.29 |
| 2 | 3.0 | both removed | 445.0 | 9.64 | 9.79 |
| 2 | 4.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 12.98 | 13.77 |
| 2 | 4.0 | no saddle set-down (h_y = 0) | 445.0 | 12.98 | 13.27 |
| 2 | 4.0 | turn without stopping | 445.0 | 12.64 | 13.29 |
| 2 | 4.0 | both removed | 445.0 | 12.64 | 12.79 |
| 2 | 5.0 | this model (saddle set-down 30 min, stop to turn) | 445.0 | 15.98 | 16.77 |
| 2 | 5.0 | no saddle set-down (h_y = 0) | 445.0 | 15.98 | 16.27 |
| 2 | 5.0 | turn without stopping | 445.0 | 15.64 | 16.29 |
| 2 | 5.0 | both removed | 445.0 | 15.64 | 15.79 |

## Eemshaven load-in 1 → 2 piles per tide (Theorem 3): A1 base geometry, 3 piles released per tide, 4 tides

Each cell: pieces unloaded in each tide in the simulation (separated by /); in parentheses, the Theorem 3 bound per tide. ρ is the ramp operation (on-board work + empty and loaded driving on the ramp), c_u is the shortest interval between two consecutive ramp operations of one vehicle set.

| K | Tidal window h | On-board work 1.5 h | On-board work 2.0 h | On-board work 2.5 h | On-board work 3.0 h | On-board work 3.5 h | On-board work 4.0 h |
|---:|---:|---|---|---|---|---|---|
| 1 | 4.0 | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 0/0/0/0 (0/0/0/0) |
| 1 | 5.0 | 2/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) |
| 1 | 6.0 | 2/2/2/2 (2/2/2/2) | 2/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) |
| 2 | 4.0 | 1/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 0/0/0/0 (0/0/0/0) |
| 2 | 5.0 | 2/2/2/2 (3/3/3/3) | 1/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) |
| 2 | 6.0 | 2/2/2/2 (3/3/3/3) | 2/2/2/2 (2/2/2/2) | 1/2/2/2 (2/2/2/2) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) | 1/1/1/1 (1/1/1/1) |

ρ, c_u (h): on board 1.5 h → ρ = 1.64, c_u = 3.01; on board 2.0 h → ρ = 2.14, c_u = 3.51; on board 2.5 h → ρ = 2.64, c_u = 4.01; on board 3.0 h → ρ = 3.14, c_u = 4.51; on board 3.5 h → ρ = 3.64, c_u = 5.01; on board 4.0 h → ρ = 4.14, c_u = 5.51.
Shortening the on-board work shortens both ρ and c_u: with one vehicle set, 2 piles per tide require ρ + c_u ≤ L (fleet term); with two vehicle sets, only ρ ≤ L/2 (ramp term).
