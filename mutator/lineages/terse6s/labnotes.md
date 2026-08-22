# Mutator lab notes

Each round: diagnose, commit a falsifiable prediction to disk, re-run the pipeline, grade
the prediction against computed numbers, write a verdict. Losing rounds are auto-reverted.

**TP** = events matched in time *and* typed correctly. F1 can rise while TP falls, simply
by predicting less — so TP is the number that says whether the model actually sees more.

| round | F1 | TP | predictions made | called right | kept |
|---|---|---|---|---|---|
| _base_ | 0.342 | **202** | 630 | – | – |
| 0 | 0.383 → 0.394 | 273 | 836 | 2/5 | **reverted** |
| 1 | 0.394 → 0.414 | 250 | 657 | 3/5 | **reverted** |
| 2 | 0.414 → 0.405 | 280 | 833 | 4/4 | **reverted** |
| 3 | 0.405 → 0.402 | 235 | 618 | 3/5 | **reverted** |
| 4 | 0.402 → 0.399 | 207 | 488 | 2/6 | **reverted** |
| 5 | 0.399 → 0.380 | 218 | 596 | 4/5 | **reverted** |
| 6 | 0.380 → 0.407 | 289 | 871 | 5/6 | **reverted** |
| 7 | 0.407 → 0.452 | 292 | 743 | 4/5 | yes |

Best F1 round 7 (0.452, TP 292). Best TP 292 — against **202 for the original prompt**. Predictions right 27/41 (66%).

---

## Round 0 — REVERTED · F1 0.383→0.394 · TP 273 · called 2/5

**Thought:** The model is dramatically over-predicting events (1080 predicted vs 550 real), resulting in 609
ghost events. This is largely a definitional mismatch rather than a perception failure.

**Changed:** I am rewriting the prompt to fix these definitional gaps by strictly limiting "set" to assists
that lead to a "kill", restricting "receive" to serve returns, and explicitly forbidding the
reporting of dead-time contacts.

**Learned:** Right about the mechanism for reducing ghost events, but completely wrong about true positives.
The predictions for `set_pred_count` and `n_pred` were accurate, as explicitly banning dead-time
contacts and narrowing the definition of a "set" successfully purged nearly 200 invented events.

## Round 1 — REVERTED · F1 0.394→0.414 · TP 250 · called 3/5

**Thought:** The model is generating 430 `invented` ghost events, including 174 phantom serves. Tellingly, 62
of these phantom serves happen *inside* a live rally on the main court, and 112 occur during
dead time.

**Changed:** I am setting the `crop` parameter to "1920:620:0:330" to isolate the main court and eliminate
false positives originating from the background matches.

**Learned:** Right about the mechanism, wrong about the size. The crop worked exactly as intended to blind
the model to background matches: `invented` fell by a massive 144 events (430 -> 286) and
phantom serves dropped by 67.

## Round 2 — REVERTED · F1 0.414→0.405 · TP 280 · called 4/4

**Thought:** The model is suffering from a massive definitional mismatch regarding the "set" action. The
current prompt instructs the model to "ONLY report a 'set' if the subsequent attack results in a
'kill'", whereas the ground truth definition assigns a set to any assist-2, regardless of the
rally's outcome.

**Changed:** I am rewriting the definitions block in the prompt to match standard, outcome-independent
volleyball terminology (e.g., removing the rule that sets must result in a kill), which aligns
with how the ground truth was derived.

**Learned:** I was right about the mechanism, but completely wrong about the ground truth. The removal of the
outcome-dependent constraints caused the model to stop suppressing events—which is exactly what
I predicted—but the numbers reveal that those strict rules were actually correct.

## Round 3 — REVERTED · F1 0.405→0.402 · TP 235 · called 3/5

**Thought:** The model is inventing a massive number of events (408 ghosts in total), including 56 phantom
serves during dead time and 330 phantoms during live rallies. This is a perception issue caused
by the very short 6.0-second `chunk_len`.

**Changed:** I am increasing the `chunk_len` from 6.0 to 15.0 seconds to give the model the temporal context
it needs to distinguish real plays from dead-time actions and fragmented fragments of rallies,
leaving all other settings exactly as they are.

**Learned:** Right about the mechanism for reducing hallucinations, wrong about the impact on true positives.
Increasing the `chunk_len` to 15.0 seconds successfully gave the model the temporal context to
recognize dead-time and discard fragmentary plays: `invented` events plummeted from 409 to 245,
and `serve_pred_count` dropped as the model learned to ignore dead-time bouncing.

## Round 4 — REVERTED · F1 0.402→0.399 · TP 207 · called 2/6

**Thought:** The model is suffering from a massive definitional mismatch for `set`, `receive`, and `serve`,
generating 134 in-rally phantoms across these three classes. `set` is predicted 125 times
against 47 real; the confusion matrix shows it absorbing 32 real attacks and 15 real digs.

**Changed:** I am rewriting the prompt definitions to enforce exactly one serve/receive per rally, explicitly
instruct the model to ignore serves if the clip starts mid-rally, and strictly limit `set` to
kill-assists.

**Learned:** Wrong about the mechanism. Initial logic regarding the reduction of phantom predictions held
true, as `invented` events dropped from 245 to 171 and overall `n_pred` fell precisely to
target.

## Round 5 — REVERTED · F1 0.399→0.380 · TP 218 · called 4/5

**Thought:** The steep drop in True Positives (from 235 to 207) and particularly `set` recall (falling to
14.9%) was caused by a definitional mismatch: the scout recorded setups broadly as `assist-2`,
but the prompt falsely forced the model to ignore sets unless they led to a kill.
Simultaneously, we have a major perception/context error driving down precision: the confusion
matrix shows 38 real `receive` events were misclassified as `serve`.

**Changed:** Revert to standard, broad definitions for event types to recover recall, but add explicit
physical descriptions for `serve` and `receive` alongside a strict rule to ignore mid-rally clip
starts for those two classes.

**Learned:** Right about the mechanism for set recall, wrong about serve precision. The numbers show that
reverting to standard, broad definitions for `set` and `dig` successfully recovered `set_recall`
(jumping from 0.213 to 0.383).

## Round 6 — REVERTED · F1 0.380→0.407 · TP 289 · called 5/6

**Thought:** The primary bottleneck for true positives (TP) is the perception degradation caused by longer
chunk lengths. When `chunk_len` was increased from 6.0 to 15.0 in iter 003, TP dropped
significantly from 280 to 235, and missed events climbed.

**Changed:** I am changing `chunk_len` back to 6.0 seconds to improve the model's perception and event
recall, while leaving the prompt unchanged.

**Learned:** I was right about the mechanism, though the magnitude of the effects was larger than I
anticipated. Returning to 6.0-second chunks massively boosted raw perception, just as expected:
true positives jumped 218 -> 289, and missed events plunged 191 -> 115.

## Round 7 — kept · F1 0.407→0.452 · TP 292 · called 4/5

**Thought:** The model is suffering from a massive DEFINITIONAL mismatch, predicting 871 events against 550
ground truth, generating 436 ghosts. The core issue is that the scout's rules are far stricter
than standard volleyball definitions, particularly for `set`, `serve`, and `kill`: 1.

**Changed:** I am rewriting the prompt's type definitions to surgically align with the scout's strict
constraints: enforcing exactly one serve/receive per rally, restricting `set` entirely to those
that immediately precede a `kill`, and instructing the model to report scoring hits as `kill`
rather than the defender's failed `dig`.

**Learned:** Right about the mechanism for `set` and the overall F1 boost, but wrong about the mechanism for
`serve`. The strict instruction to only report a `set` if it immediately precedes a `kill`
worked flawlessly.

---

## Current beliefs

# What I know about this pipeline

### Established
- The ground truth applies strict, outcome-dependent definitions to volleyball actions. Specifically, a `set` is only recorded if it immediately leads to a `kill`. Enforcing this strict temporal dependency in the prompt reduces false-positive sets dramatically (192 -> 53) while maintaining true positives, driving F1 above 0.450.
- Background matches in the top half of the frame generate hundreds of false positives. Cropping them out drops `invented` events dramatically.
- The model can accurately track ball contacts high in the air; overly aggressive top-cropping (e.g., cutting 330 pixels) clips legitimate high passes and costs true positives.
- Temporal Context vs. Granularity: Short chunks (6.0s) force high temporal granularity—maximizing true positives (292) and unlocking block detection—but they completely destroy the model's ability to distinguish live play from dead-time. At 6.0s, the model cannot evaluate rally-wide constraints (like "one serve per rally") because it cannot see rally boundaries.
- Long chunks (15.0s) suppress dead-time hallucinations but cause the model to summarize rallies, skipping intermediate contacts and missing rapid, compound events like blocks.

### Ruled out
- Using standard, outcome-independent definitions for `set` (e.g., "any intentional pass"). The scout does not record these, leading to massive over-prediction.
- Assuming aggressive top-cropping is harmless to the main court. Cutting the top 330 pixels cost 23 true positives in Iteration 1.
- Using long (15.0s) chunk sizes. The model cannot exhaustively list all contacts in a long rally, causing it to summarize and skip intermediate events and blocks.
- Expecting the model to enforce rally-wide rules or conditional logic around clip boundaries (e.g., "if the ball is already in play") inside a 6.0s chunk. The limited temporal window makes it blind to the broader context, causing dead-time practice to look like real serves.

### Open
- What is the exact optimal `chunk_len` and `overlap` combination that provides enough context to see rally boundaries and dead-time, without overwhelming the model's granular ability to spot blocks?
- Is there a "goldilocks" crop geometry (e.g., cutting only the top 150-200 pixels) that obscures the background matches without clipping high passes on the main court?

### Current hypothesis
The pipeline is currently caught in a tug-of-war between temporal granularity (which needs short chunks to see blocks) and contextual awareness (which needs longer chunks to spot dead-time practice and mid-rally serves). Now that we have perfectly aligned our `set` definitions with the scout, the remaining 324 ghosts are primarily false serves and dead-time hallucinations. Implementing an intermediate `chunk_len` of 10.0 seconds with a high `overlap` of 4.0 seconds will provide enough temporal context to suppress dead-ball hallucinations while keeping the chunk size small enough to maintain block detection. Simultaneously, relaxing the overly aggressive 330-pixel top-crop down to 200 pixels will restore spatial visibility for high passes without letting the background matches back in.