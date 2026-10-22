# Table 7 with diameter column

| Monopile | Length m | Diameter m | Passes 10 m single lane (D ≤ w) | Passes 12 m single lane | Road width for an empty vehicle to pass a loaded one ≥ | Road width for two loaded vehicles to pass ≥ |
|---|---:|---:|---|---|---:|---:|
| 85 m class | 85 | 9.5 | yes | yes | 15.36 | 20.00 |
| 100 m class | 100 | 9.5 | yes | yes | 15.36 | 20.00 |
| 110 m class | 110 | 11.5 | no | yes | 17.36 | 24.00 |
| 120 m class | 120 | 12 | no | yes | 17.86 | 25.00 |

Width rule of the model: resource capacity = road width + c_lat, and a loaded vehicle occupies min(capacity, D + c_lat), so a load whose diameter exceeds the road width occupies the road exclusively; the model does not judge feasibility. E7 uses a 12 m single lane, and all four classes satisfy D ≤ 12 m.
