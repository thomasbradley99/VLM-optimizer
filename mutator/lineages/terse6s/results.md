# Every scored run

Ground truth is 550 events. **TP** = matched within +/-1.0s *and* typed correctly.
**spotted** = matched on timing alone, ignoring the label -- the gap between the two
columns is how often the model saw the event but called it the wrong thing.

Repeat-run noise measured on an identical config: +/-0.028 F1, +/-8 TP.
A gap smaller than that is not a result.

| run | src | config | prompt | F1 | TP | spotted | n_pred | missed | invented | team | kept | $ |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| iter_007 | mutator | 6s/2s crop | `f01e7d77` | **0.452** | 292 | 419 | 743 | 131 | 324 | 0.82 | yes | 3.16 |
| iter_001 | mutator | 6s/2s crop | `c8981858` | **0.414** | 250 | 371 | 657 | 179 | 286 | 0.77 | no | 2.91 |
| iter_006 | mutator | 6s/2s crop | `7d1ce2cb` | **0.407** | 289 | 435 | 871 | 115 | 436 | 0.80 | no | 3.21 |
| iter_002 | mutator | 6s/2s crop | `aafcf954` | **0.405** | 280 | 424 | 833 | 126 | 409 | 0.79 | no | 2.91 |
| iter_003 | mutator | 15s/2s crop | `aafcf954` | **0.402** | 235 | 373 | 618 | 177 | 245 | 0.82 | no | 1.81 |
| iter_004 | mutator | 15s/2s crop | `3c5df92e` | **0.399** | 207 | 317 | 488 | 233 | 171 | 0.68 | no | 1.77 |
| iter_000 | mutator | 6s/2s | `c8981858` | **0.394** | 273 | 406 | 836 | 144 | 430 | 0.78 | no | 3.30 |
| iter_005 | mutator | 15s/2s crop | `7d1ce2cb` | **0.380** | 218 | 359 | 596 | 191 | 237 | 0.77 | no | 1.82 |

Best: **iter_007** (6s/2s crop), F1 0.452, TP 292/550, spotted 419/550.

## Per-type — iter_007

| type | GT | predicted | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|
| serve | 118 | 180 | 0.383 | 0.585 | 0.463 |
| receive | 107 | 156 | 0.455 | 0.664 | 0.540 |
| dig | 86 | 104 | 0.413 | 0.500 | 0.453 |
| set | 47 | 53 | 0.321 | 0.362 | 0.340 |
| attack | 131 | 153 | 0.418 | 0.489 | 0.451 |
| kill | 52 | 74 | 0.338 | 0.481 | 0.397 |
| block | 9 | 23 | 0.130 | 0.333 | 0.188 |
