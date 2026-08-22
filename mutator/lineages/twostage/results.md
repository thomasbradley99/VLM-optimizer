# Every scored run

Ground truth is 550 events. **TP** = matched within +/-1.0s *and* typed correctly.
**spotted** = matched on timing alone, ignoring the label -- the gap between the two
columns is how often the model saw the event but called it the wrong thing.

Repeat-run noise measured on an identical config: +/-0.028 F1, +/-8 TP.
A gap smaller than that is not a result.

| run | src | config | prompt | F1 | TP | spotted | n_pred | missed | invented | team | kept | $ |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| iter_001 | mutator | 10s/3s crop | `1eaae0a7` | **0.418** | 257 | 392 | 681 | 158 | 289 | 0.80 | yes | 4.19 |
| iter_000 | mutator | 10s/3s crop | `6edf357c` | **0.376** | 229 | 365 | 668 | 185 | 303 | 0.81 | no | 4.17 |

Best: **iter_001** (10s/3s crop), F1 0.418, TP 257/550, spotted 392/550.

## Per-type — iter_001

| type | GT | predicted | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|
| serve | 118 | 95 | 0.568 | 0.458 | 0.507 |
| receive | 107 | 86 | 0.384 | 0.308 | 0.342 |
| dig | 86 | 124 | 0.363 | 0.523 | 0.429 |
| set | 47 | 149 | 0.201 | 0.638 | 0.306 |
| attack | 131 | 152 | 0.467 | 0.542 | 0.502 |
| kill | 52 | 49 | 0.429 | 0.404 | 0.416 |
| block | 9 | 26 | 0.115 | 0.333 | 0.171 |
