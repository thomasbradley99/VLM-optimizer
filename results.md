# Every scored run

Ground truth is 550 events. **TP** = matched within +/-1.0s *and* typed correctly.
**spotted** = matched on timing alone, ignoring the label -- the gap between the two
columns is how often the model saw the event but called it the wrong thing.

Repeat-run noise measured on an identical config: +/-0.028 F1, +/-8 TP.
A gap smaller than that is not a result.

| run | src | config | prompt | F1 | TP | spotted | n_pred | missed | invented | team | kept | $ |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| iter_023 | mutator | 6s/2s crop | `4a6041a2` | **0.463** | 300 | 424 | 745 | 126 | 321 | 0.80 | no | 3.28 |
| iter_025 | mutator | 6s/2s crop | `aa1bf308` | **0.460** | 281 | 395 | 671 | 155 | 276 | 0.78 | no | 3.41 |
| crop6s | hand | 6s/2s crop | `60eec175` | **0.455** | 293 | 414 | 738 | 136 | 324 | 0.76 | - | 2.93 |
| iter_028 | mutator | 6s/2s crop | `8a79e290` | **0.452** | 283 | 402 | 701 | 148 | 299 | 0.83 | yes | 3.30 |
| iter_022 | mutator | 6s/2s crop | `fb6740e1` | **0.449** | 284 | 407 | 716 | 143 | 309 | 0.82 | yes | 3.23 |
| iter_016 | mutator | 6s/2s thinking=medium | `0409f1b6` | **0.446** | 306 | 426 | 822 | 124 | 396 | 0.79 | no | 4.64 |
| iter_024 | mutator | 6s/2s crop | `b978be18` | **0.445** | 279 | 392 | 704 | 158 | 312 | 0.82 | no | 3.36 |
| iter_017 | mutator | 6s/2s | `31c62577` | **0.443** | 312 | 430 | 857 | 120 | 427 | 0.75 | no | 3.34 |
| armH | hand | 6s/2s | `959889fd` | **0.441** | 288 | 421 | 756 | 129 | 335 | 0.73 | - | 3.21 |
| iter_026 | mutator | 6s/2s crop | `e2b786b0` | **0.440** | 267 | 380 | 664 | 170 | 284 | 0.71 | no | 3.33 |
| seed6s | hand | 6s/2s | `60eec175` | **0.440** | 309 | 444 | 856 | 106 | 412 | 0.73 | - | 4.87 |
| iter_015 | mutator | 6s/2s | `f3ad2279` | **0.439** | 303 | 427 | 831 | 123 | 404 | 0.78 | no | 3.51 |
| iter_019 | mutator | 6s/2s | `fc4ced84` | **0.436** | 315 | 437 | 895 | 113 | 458 | 0.80 | no | 3.63 |
| armE | hand | 10s/3s crop | `959889fd` | **0.434** | 237 | 344 | 543 | 206 | 199 | 0.71 | - | 2.30 |
| sweep_8s | hand | 8s/2.5s crop | `60eec175` | **0.427** | 260 | 380 | 667 | 170 | 287 | 0.82 | - | 2.55 |
| armF | hand | 10s/3s crop HIGH | `959889fd` | **0.418** | 206 | 273 | 435 | 277 | 162 | 0.95 | - | 4.38 |
| iter_021 | mutator | 6s/2s crop | `089c1884` | **0.417** | 277 | 413 | 779 | 137 | 366 | 0.85 | no | 3.32 |
| iter_018 | mutator | 6s/2s | `d7faa287` | **0.411** | 298 | 446 | 900 | 104 | 454 | 0.82 | no | 3.63 |
| iter_027 | mutator | 6s/2s crop | `f1c27f70` | **0.410** | 248 | 386 | 660 | 164 | 274 | 0.78 | no | 3.27 |
| iter_020 | mutator | 10s/2s | `13a16337` | **0.402** | 238 | 376 | 633 | 174 | 257 | 0.81 | no | 2.49 |
| armG | hand | 10s/3s | `959889fd` | **0.400** | 238 | 369 | 640 | 181 | 271 | 0.76 | - | 2.37 |
| iter_012 | mutator | 15s/4s | `cfdf2df9` | **0.391** | 239 | 381 | 673 | 169 | 292 | 0.75 | yes | - |
| iter_000 | mutator | defaults | `527f03e9` | **0.359** | 195 | 321 | 535 | 229 | 214 | 0.70 | yes | - |
| iter_010 | mutator | defaults | `f1a259f9` | **0.358** | 190 | 329 | 511 | 221 | 182 | 0.80 | no | - |
| iter_003 | mutator | defaults | `7a48d0cd` | **0.350** | 184 | 303 | 500 | 247 | 197 | 0.70 | yes | - |
| iter_005 | mutator | defaults | `959889fd` | **0.349** | 191 | 321 | 545 | 229 | 224 | 0.70 | yes | - |
| armA | hand | defaults | `959889fd` | **0.349** | 191 | 321 | 545 | 229 | 224 | 0.70 | - | 1.88 |
| iter_007 | mutator | defaults | `72b4c3ee` | **0.340** | 181 | 315 | 515 | 235 | 200 | 0.70 | no | - |
| iter_001 | mutator | defaults | `7c3809be` | **0.337** | 181 | 313 | 525 | 237 | 212 | 0.71 | no | - |
| iter_006 | mutator | defaults | `8eb68e95` | **0.336** | 178 | 317 | 510 | 233 | 193 | 0.74 | no | - |
| iter_008 | mutator | crop | `959889fd` | **0.333** | 171 | 287 | 476 | 263 | 189 | 0.72 | no | - |
| armC | hand | crop | `959889fd` | **0.333** | 171 | 287 | 476 | 263 | 189 | 0.72 | - | 1.63 |
| iter_002 | mutator | defaults | `a2fb839f` | **0.332** | 179 | 310 | 528 | 240 | 218 | 0.73 | yes | - |
| iter_004 | mutator | defaults | `a66dc050` | **0.323** | 169 | 317 | 496 | 233 | 179 | 0.75 | yes | - |
| iter_009 | mutator | defaults | `77b92678` | **0.319** | 165 | 293 | 483 | 257 | 190 | 0.71 | no | - |
| iter_013 | mutator | 15s/4s fps=10 | `cfdf2df9` | **0.308** | 142 | 228 | 372 | 322 | 144 | 0.69 | no | - |
| armB | hand | HIGH | `959889fd` | **0.293** | 122 | 188 | 282 | 362 | 94 | 0.83 | - | 3.17 |
| iter_011 | mutator | fps=10 | `959889fd` | **0.277** | 124 | 211 | 346 | 339 | 135 | 0.67 | no | - |
| armD | hand | crop HIGH | `959889fd` | **0.276** | 113 | 164 | 268 | 386 | 104 | 0.85 | - | 2.79 |

Best: **iter_023** (6s/2s crop), F1 0.463, TP 300/550, spotted 424/550.

## Per-type — iter_023

| type | GT | predicted | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|
| serve | 118 | 162 | 0.407 | 0.559 | 0.471 |
| receive | 107 | 157 | 0.389 | 0.570 | 0.462 |
| dig | 86 | 133 | 0.361 | 0.558 | 0.438 |
| set | 47 | 34 | 0.441 | 0.319 | 0.370 |
| attack | 131 | 185 | 0.432 | 0.611 | 0.506 |
| kill | 52 | 67 | 0.433 | 0.558 | 0.487 |
| block | 9 | 7 | 0.143 | 0.111 | 0.125 |
