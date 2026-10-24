# Two-level screening of 8 public sites (paths measured on public satellite imagery)

Level 1 (geometry): single-lane segments (width class A) use τ_cut = t_ℓ + t_e; junctions = interior vertices of the path polyline, with occupancy τ_j = loaded (D + L_v + δ)/v (plus a 120 s stop to steer + θ·L_v/2/v for turns ≥ 60°) + one empty pass (D + L_e + δ)/v_e (plus a 30 s sweep for turns ≥ 60°), entered in the τ/p criterion as a short single lane; D is the road width of the adjacent segment, open yards use unrestricted_w = 31 m. The polylines measured on public satellite imagery have no vertex ≥ 60°; a hypothetical 90° turn on the spot, τ_90 (at the widest point of the path), is listed as an upper bound. Level 2 (capacity): K_rate = ⌈c/p⌉ (c = h_p + h_d + path/v + Σ turning stops + path/v_e; a long-run necessary condition); K_W″ = smallest K for which the binding term of W″_lift(12 h) on the A1 proxy graph is the crane (upper bound: if the binding term is not the crane, the crane cannot be the constraint, so this is a necessary condition); **K_min = smallest K for which first-come-first-served simulation on the same proxy graph delivers the crane limit ⌊L/p⌋** (L = 12 h, S = 1, G = 24 h, main2 geometry, conservative lifting rule; verified by the checker). The stricter of the two cradle types is taken.

| Site | Class | Path m | Speed km/h | Max junction τ_j/p | Hypothetical 90° turn τ_90/p | Single lane τ_cut/p | K_rate | K_W″ | Simulated delivery K = 1 … 6 (roadside / pull-in, limit 12) | **K_min** | Conclusion (p = 1 h) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| Rotterdam Maasvlakte 2 (Sif) | C | 655.6 | 1.0 | 0.159 | 0.287 | — | 2 | 2 | 6 11 12 12 12 12 / 6 11 12 12 12 12 | **3** | crane-limited for K ≥ 3 vehicle sets |
| Rotterdam Maasvlakte 2 (Sif) | C | 655.6 | 2.5 | 0.072 | 0.148 | — | 2 | 2 | 8 12 12 12 12 12 / 8 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Ferrol / Fene (Navantia Seanergies–Windar) | C | 322.0 | 1.0 | 0.159 | 0.287 | — | 2 | 2 | 7 12 12 12 12 12 / 7 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Ferrol / Fene (Navantia Seanergies–Windar) | C | 322.0 | 2.5 | 0.072 | 0.148 | — | 2 | 2 | 9 12 12 12 12 12 / 9 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Nordenham-Blexen (Steelwind) | C | 687.8 | 1.0 | 0.159 | 0.287 | — | 2 | 3 | 6 10 12 12 12 12 / 6 10 12 12 12 12 | **3** | crane-limited for K ≥ 3 vehicle sets |
| Nordenham-Blexen (Steelwind) | C | 687.8 | 2.5 | 0.072 | 0.148 | — | 2 | 2 | 8 12 12 12 12 12 / 8 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Rostock Überseehafen (EEW SPC) | C | 325.0 | 1.0 | 0.159 | 0.287 | — | 2 | 2 | 7 12 12 12 12 12 / 7 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Rostock Überseehafen (EEW SPC) | C | 325.0 | 2.5 | 0.072 | 0.148 | — | 2 | 2 | 9 12 12 12 12 12 / 9 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Rønne (Bornholm) | C | 129.4 | 1.0 | 0.0 | 0.287 | — | 2 | 2 | 8 12 12 12 12 12 / 8 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Rønne (Bornholm) | C | 129.4 | 2.5 | 0.0 | 0.148 | — | 2 | 2 | 9 12 12 12 12 12 / 9 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Vlissingen (Verbrugge Scaldia Terminals) | C | 239.1 | 1.0 | 0.159 | 0.287 | — | 2 | 2 | 7 12 12 12 12 12 / 7 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Vlissingen (Verbrugge Scaldia Terminals) | C | 239.1 | 2.5 | 0.072 | 0.148 | — | 2 | 2 | 9 12 12 12 12 12 / 9 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Vlissingen (Verbrugge Zeeland Terminals) | C | 366.5 | 1.0 | 0.159 | 0.287 | — | 2 | 2 | 7 12 12 12 12 12 / 7 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Vlissingen (Verbrugge Zeeland Terminals) | C | 366.5 | 2.5 | 0.072 | 0.148 | — | 2 | 2 | 8 12 12 12 12 12 / 8 12 12 12 12 12 | **2** | crane-limited for K ≥ 2 vehicle sets |
| Eemshaven (Gode Wind 3: BOW storage yard → Wagenborg quay) | A | 1135.2 | 1.0 | 0.159 | 0.287 | 1.195 | 3 | — | 5 7 7 7 7 7 / 5 7 7 7 7 7 | **—** | road-limited (no K ≤ 6 reaches the crane limit) |
| Eemshaven (Gode Wind 3: BOW storage yard → Wagenborg quay) | A | 1135.2 | 2.5 | 0.072 | 0.148 | 0.598 | 2 | — | 7 10 10 10 10 10 / 7 10 10 10 10 10 | **—** | road-limited (no K ≤ 6 reaches the crane limit) |

### p = 0.5 h (crane 0.5 h, limit 24)

| Site | Speed | Max junction τ_j/p | τ_90/p | Single lane τ_cut/p | K_rate | K_W″ | Simulated delivery K = 1 … 6 (roadside / pull-in) | K_min |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| Rotterdam Maasvlakte 2 (Sif) | 1.0 | 0.318 | 0.575 | — | 4 | — | 6 11 14 14 14 14 / 6 11 14 14 14 14 | — |
| Rotterdam Maasvlakte 2 (Sif) | 2.5 | 0.143 | 0.296 | — | 3 | — | 8 15 17 17 17 17 / 8 15 17 17 17 17 | — |
| Ferrol / Fene (Navantia Seanergies–Windar) | 1.0 | 0.318 | 0.575 | — | 3 | — | 7 13 14 14 14 14 / 7 13 14 14 14 14 | — |
| Ferrol / Fene (Navantia Seanergies–Windar) | 2.5 | 0.143 | 0.296 | — | 3 | — | 9 16 17 17 17 17 / 9 16 17 17 17 17 | — |
| Nordenham-Blexen (Steelwind) | 1.0 | 0.318 | 0.575 | — | 4 | — | 6 11 14 14 14 14 / 6 11 14 14 14 14 | — |
| Nordenham-Blexen (Steelwind) | 2.5 | 0.143 | 0.296 | — | 3 | — | 8 15 17 17 17 17 / 8 15 17 17 17 17 | — |
| Rostock Überseehafen (EEW SPC) | 1.0 | 0.318 | 0.575 | — | 3 | — | 7 13 14 14 14 14 / 7 13 14 14 14 14 | — |
| Rostock Überseehafen (EEW SPC) | 2.5 | 0.143 | 0.296 | — | 3 | — | 9 16 17 17 17 17 / 9 16 17 17 17 17 | — |
| Rønne (Bornholm) | 1.0 | 0.0 | 0.575 | — | 3 | — | 8 14 14 14 14 14 / 8 14 14 14 14 14 | — |
| Rønne (Bornholm) | 2.5 | 0.0 | 0.296 | — | 3 | — | 10 17 17 17 17 17 / 10 17 17 17 17 17 | — |
| Vlissingen (Verbrugge Scaldia Terminals) | 1.0 | 0.318 | 0.575 | — | 3 | — | 8 14 14 14 14 14 / 8 14 14 14 14 14 | — |
| Vlissingen (Verbrugge Scaldia Terminals) | 2.5 | 0.143 | 0.296 | — | 3 | — | 9 17 17 17 17 17 / 9 17 17 17 17 17 | — |
| Vlissingen (Verbrugge Zeeland Terminals) | 1.0 | 0.318 | 0.575 | — | 3 | — | 7 13 14 14 14 14 / 7 13 14 14 14 14 | — |
| Vlissingen (Verbrugge Zeeland Terminals) | 2.5 | 0.143 | 0.296 | — | 3 | — | 9 16 17 17 17 17 / 9 16 17 17 17 17 | — |
| Eemshaven (Gode Wind 3: BOW storage yard → Wagenborg quay) | 1.0 | 0.318 | 0.575 | 2.39 | 5 | — | 5 7 7 7 7 7 / 5 7 7 7 7 7 | — |
| Eemshaven (Gode Wind 3: BOW storage yard → Wagenborg quay) | 2.5 | 0.143 | 0.296 | 1.196 | 4 | — | 7 11 11 11 11 11 / 7 11 11 11 11 11 | — |

"—": for K ≤ 6 the crane is never binding / the simulation never reaches the crane limit. All checker tests pass (check_ok in `sites_w2.csv`).
