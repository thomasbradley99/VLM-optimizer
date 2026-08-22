# Evaluation — crop6s (best run)

`6s clips · 2s overlap · 5fps · 640px · court-cropped · gemini-3.7-flash` · 738 predictions vs 550 ground-truth events

Sanity: ground truth scored against itself = **1.000 in all 12 cells**

## 1. The strictness ladder

Each row adds one requirement to the row above. Reading down a column shows what each
extra demand costs. A pair must match on time *and* everything above it to count.

| must match | ±0.5s | ±1.0s | ±2.0s | matched @1.0s | of 550 |
|---|---:|---:|---:|---:|---:|
| time only | 0.467 | **0.643** | 0.752 | 414 | 75% |
| + action type | 0.241 | **0.455** | 0.571 | 293 | 53% |
| + which team | 0.180 | **0.363** | 0.455 | 234 | 43% |
| + jersey number | 0.016 | **0.031** | 0.033 | 20 | 4% |

**Headline F1 is 0.455** — timing within ±1.0s and the right action type.

- The model **locates 414 of 550 events** (75%). Finding events is not the problem.
- Of those 414, only **293 get the right label** (71%). 121 are seen but misnamed.
- Of those 293, **234 also get the team right** (80%).
- Jersey numbers are effectively unreadable at this encoding (F1 0.031).

## 2. Per action type, at ±1.0s

| type | in truth | predicted | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|
| serve | 118 | 169 | 0.444 | 0.636 | **0.523** |
| receive | 107 | 171 | 0.363 | 0.579 | **0.446** |
| dig | 86 | 133 | 0.353 | 0.547 | **0.429** |
| set | 47 | 22 | 0.409 | 0.191 | **0.261** |
| attack | 131 | 181 | 0.409 | 0.565 | **0.474** |
| kill | 52 | 39 | 0.615 | 0.462 | **0.527** |
| block | 9 | 23 | 0.087 | 0.222 | **0.125** |

## 3. Where the labels go wrong

Rows are what the event really was; columns are what the model called it. Only
time-matched pairs appear — the 136 events never located are not here.

| truth \ called | serve | receive | dig | set | attack | kill | block | hit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| serve | **60** | 23 | 1 | 0 | 5 | 0 | 0 | 51% |
| receive | 18 | **44** | 1 | 0 | 9 | 1 | 2 | 41% |
| dig | 1 | 11 | **31** | 0 | 19 | 0 | 1 | 36% |
| set | 1 | 6 | 4 | **6** | 11 | 4 | 1 | 13% |
| attack | 7 | 22 | 19 | 1 | **44** | 5 | 2 | 34% |
| kill | 1 | 3 | 9 | 3 | 18 | **11** | 0 | 21% |
| block | 0 | 1 | 2 | 0 | 3 | 1 | **2** | 22% |

## 4. Two things that are *not* wrong

- **Clock alignment.** Best constant time shift is +0.00s, giving F1 0.455 against 0.455 at zero offset. There is no systematic lag to correct.
- **Team polarity.** F1 at +team is 0.363 as-is and 0.106 with the two teams swapped, so left/right is not inverted.

## 5. Every event accounted for

| outcome | count |
|---|---:|
| exactly right (time, type, team) | 151 |
| right action, wrong team | 47 |
| right moment, wrong action | 216 |
| real event, never spotted | 136 |
| reported, nothing there | 324 |

Total real events 550 · total predictions 738

