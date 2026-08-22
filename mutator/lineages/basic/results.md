# Every scored run

Ground truth is 550 events. **TP** = matched within +/-1.0s *and* typed correctly.
**spotted** = matched on timing alone, ignoring the label -- the gap between the two
columns is how often the model saw the event but called it the wrong thing.

Repeat-run noise measured on an identical config: +/-0.028 F1, +/-8 TP.
A gap smaller than that is not a result.

| run | src | config | prompt | F1 | TP | spotted | n_pred | missed | invented | team | kept | $ |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| iter_000 | mutator | defaults | `381afab8` | **0.390** | 223 | 334 | 594 | 216 | 260 | 0.74 | yes | 2.03 |
| iter_002 | mutator | defaults | `381afab8` | **0.390** | 223 | 334 | 594 | 216 | 260 | 0.74 | yes | 0.29 |
| iter_001 | mutator | crop | `381afab8` | **0.330** | 173 | 295 | 499 | 255 | 204 | 0.76 | no | 1.71 |
| iter_006 | mutator | defaults | `4404e4ae` | **0.314** | 167 | 296 | 514 | 254 | 218 | 0.76 | no | 2.15 |
| iter_003 | mutator | defaults | `58efd7cd` | **0.307** | 174 | 301 | 583 | 249 | 282 | 0.70 | no | 2.05 |
| iter_004 | mutator | defaults | `6a259bd9` | **0.305** | 163 | 259 | 518 | 291 | 259 | 0.72 | no | 2.14 |
| iter_007 | mutator | defaults | `7fe53f4e` | **0.297** | 150 | 249 | 460 | 301 | 211 | 0.74 | no | 2.10 |
| iter_005 | mutator | defaults | `f854184c` | **0.288** | 148 | 246 | 479 | 304 | 233 | 0.74 | no | 2.01 |

Best: **iter_000** (defaults), F1 0.390, TP 223/550, spotted 334/550.

## Per-type — iter_000

| type | GT | predicted | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|
| serve | 118 | 131 | 0.489 | 0.542 | 0.514 |
| receive | 107 | 108 | 0.259 | 0.262 | 0.260 |
| dig | 86 | 103 | 0.379 | 0.453 | 0.413 |
| set | 47 | 43 | 0.349 | 0.319 | 0.333 |
| attack | 131 | 135 | 0.415 | 0.427 | 0.421 |
| kill | 52 | 58 | 0.345 | 0.385 | 0.364 |
| block | 9 | 16 | 0.062 | 0.111 | 0.080 |
