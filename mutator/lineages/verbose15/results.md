# Every scored run

Ground truth is 550 events. **TP** = matched within +/-1.0s *and* typed correctly.
**spotted** = matched on timing alone, ignoring the label -- the gap between the two
columns is how often the model saw the event but called it the wrong thing.

Repeat-run noise measured on an identical config: +/-0.028 F1, +/-8 TP.
A gap smaller than that is not a result.

| run | src | config | prompt | F1 | TP | spotted | n_pred | missed | invented | team | kept | $ |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| iter_006 | mutator | 15s/4s crop | `26cf2965` | **0.414** | 231 | 357 | 566 | 193 | 209 | 0.79 | yes | 2.25 |
| iter_000 | mutator | 15s/4s crop | `c1de4b05` | **0.413** | 230 | 348 | 565 | 202 | 217 | 0.80 | no | 2.27 |
| iter_002 | mutator | 15s/4s crop | `c1de4b05` | **0.413** | 230 | 348 | 565 | 202 | 217 | 0.80 | yes | 0.36 |
| iter_003 | mutator | 15s/4s crop | `c86e1ca2` | **0.400** | 223 | 342 | 564 | 208 | 222 | 0.73 | no | 2.22 |
| iter_007 | mutator | 15s/4s crop | `43477fa4` | **0.394** | 221 | 360 | 572 | 190 | 212 | 0.77 | no | 2.27 |
| iter_004 | mutator | 15s/4s fps=10 crop | `c86e1ca2` | **0.366** | 187 | 299 | 473 | 251 | 174 | 0.77 | no | 3.42 |
| iter_005 | mutator | 15s/4s fps=10 crop | `26cf2965` | **0.363** | 186 | 294 | 474 | 256 | 180 | 0.82 | no | 3.61 |
| iter_001 | mutator | crop | `c1de4b05` | **0.309** | 149 | 270 | 414 | 280 | 144 | 0.82 | no | 1.54 |

Best: **iter_006** (15s/4s crop), F1 0.414, TP 231/550, spotted 357/550.

## Per-type — iter_006

| type | GT | predicted | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|
| serve | 118 | 149 | 0.477 | 0.602 | 0.532 |
| receive | 107 | 122 | 0.311 | 0.355 | 0.332 |
| dig | 86 | 78 | 0.397 | 0.360 | 0.378 |
| set | 47 | 38 | 0.395 | 0.319 | 0.353 |
| attack | 131 | 112 | 0.464 | 0.397 | 0.428 |
| kill | 52 | 58 | 0.379 | 0.423 | 0.400 |
| block | 9 | 9 | 0.222 | 0.222 | 0.222 |
