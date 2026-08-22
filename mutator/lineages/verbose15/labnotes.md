# Mutator lab notes

Each round: diagnose, commit a falsifiable prediction to disk, re-run the pipeline, grade
the prediction against computed numbers, write a verdict. Losing rounds are auto-reverted.

**TP** = events matched in time *and* typed correctly. F1 can rise while TP falls, simply
by predicting less — so TP is the number that says whether the model actually sees more.

| round | F1 | TP | predictions made | called right | kept |
|---|---|---|---|---|---|
| _base_ | 0.342 | **202** | 630 | – | – |
| 0 | 0.395 → 0.413 | 230 | 565 | 3/5 | **reverted** |
| 1 | 0.413 → 0.309 | 149 | 414 | 3/5 | **reverted** |
| 2 | 0.309 → 0.413 | 230 | 565 | 5/6 | yes |
| 3 | 0.413 → 0.400 | 223 | 564 | 1/5 | **reverted** |
| 4 | 0.400 → 0.366 | 187 | 473 | 3/4 | **reverted** |
| 5 | 0.366 → 0.363 | 186 | 474 | 1/5 | **reverted** |
| 6 | 0.363 → 0.414 | 231 | 566 | 4/5 | yes |
| 7 | 0.414 → 0.394 | 221 | 572 | 0/6 | **reverted** |

Best F1 round 6 (0.414, TP 231). Best TP 231 — against **202 for the original prompt**. Predictions right 20/41 (49%).

---

## Round 0 — REVERTED · F1 0.395→0.413 · TP 230 · called 3/5

**Thought:** The model suffers from three major definitional mismatches that cause rampant over-prediction
and team attribution errors. This is a definitional failure, not a perception issue.

**Changed:** Update the prompt's taxonomy to tightly align with the scout's rules: restrict `set` to only
those that lead to a kill (assists), explicitly forbid mid-rally `serve` and `receive`
predictions, and clarify that the `point` flag must only be true if the contacting team won the
rally.

**Learned:** Right about the mechanism for `set`, but completely wrong about `serve` and `score_margin_err`.
The numbers show a definitive success on `set`: `set_pred_count` dropped perfectly from 130 to
44, matching the true assist count, which also drove the overall `n_pred` drop.

## Round 1 — REVERTED · F1 0.413→0.309 · TP 149 · called 3/5

**Thought:** The model is over-predicting events across the pipeline (565 predicted vs 550 real, with 206
entirely hallucinated ghosts). Most of these ghosts (176) occur inside live rallies, including
29 phantom serves and 41 phantom receives.

**Changed:** I am changing `chunk_len` from 15.0 to 30.0 to provide enough temporal context to see full
rallies and reduce boundary-related hallucination artifacts.

**Learned:** I was right about the mechanism (reducing chunk boundaries and adding context reduced false
positives), but dead wrong about the size and direction of the true positives. The numbers show
a disastrous drop in recall: while `invented` fell from 217 to 144, `missed` events spiked from
202 to 280, dragging True Positives down from 230 to 149 and tanking the F1 score.

## Round 2 — kept · F1 0.309→0.413 · TP 230 · called 5/6

**Thought:** Increasing `chunk_len` from 15.0s to 30.0s caused a catastrophic perception failure. The numbers
clearly show True Positives dropping from 230 to 149, and `missed` events spiking from 202 to
280, dragging F1 down to 0.309.

**Changed:** Reverting `chunk_len` back to 15.0 to exactly restore the iter_000 configuration and regain our
lost True Positives.

**Learned:** Right. Reverting to 15-second chunks successfully reversed temporal dilution, confirming the
baseline parameters.

## Round 3 — REVERTED · F1 0.413→0.400 · TP 223 · called 1/5

**Thought:** The pipeline is suffering from massive definitional confusion and duplicate reporting. First,
the model is ignoring ball trajectory in favor of perceived sequence: it classifies 36 true
`receive`s as `serve`s (because it misses the real serve and thinks the first pass it sees is
the start) and 22 true `attack`s as `receive`s.

**Changed:** I am updating the prompt to explicitly tie the taxonomy to ball trajectory (OVER the net vs
TEAMMATE) and adding critical rules to forbid multiple rows per timestamp and dead-time
reporting.

**Learned:** Wrong. The text-based trajectory rules and single-label constraints failed to reduce ghosts or
fix action confusion, and instead actively harmed `attack` detection.

## Round 4 — REVERTED · F1 0.400→0.366 · TP 187 · called 3/4

**Thought:** The model is failing to identify fast actions because at 5 frames per second, the ball's
trajectory is often lost between frames. This perception deficit directly conflicts with the
strict trajectory rules added in the last round.

**Changed:** I am increasing the framerate from 5 fps to 10 fps to give the model the temporal evidence
required by the strict trajectory rules, leaving the prompt exactly as it is.

**Learned:** I was right about the mechanism of serve reduction, but completely wrong about the overall
impact on recall. The numbers show that increasing the framerate caused a general suppression of
output: total predictions plummeted from 564 to 473, which dragged true positives down from 223
to 187 and increased missed events from 208 to 251.

## Round 5 — REVERTED · F1 0.366→0.363 · TP 186 · called 1/5

**Thought:** The model is severely misclassifying deep-court `receive` events and mid-rally contacts as
`serve`. The numbers show `serve` is predicted 144 times against 118 real events, and the
confusion matrix reveals it is absorbing 42 `receive`s and 11 `attack`s, plus generating 38 in-
rally ghosts.

**Changed:** I am adding kinematic cues (the toss) and sequence rules (arriving from over the net) to the
definitions of `serve` and `receive`, along with a specific critical rule explicitly prohibiting
the confusion of deep receives with serves, to force the model to use causal sequence rather
than just spatial location.

**Learned:** Right about the mechanism for serve reduction, but entirely wrong about the size and downstream
effects. The numbers show that explicitly requiring a toss and forbidding deep-receive confusion
did suppress `serve` predictions (144 -> 129), but it completely failed to reallocate those
contacts to `receive` (which barely moved, 92 -> 96).

## Round 6 — kept · F1 0.363→0.414 · TP 231 · called 4/5

**Thought:** The massive drop in True Positives (from 223 down to 186) and increase in missed events (up to
256) over the last two iterations was a perception failure caused by doubling the framerate to
10 fps, not by the prompt changes. At 15 seconds per chunk, 10 fps results in 150 frames per
request.

**Changed:** I am decreasing the framerate back to 5 fps while leaving the prompt exactly as it is, to test
whether the lower token count restores the model's ability to see contacts.

**Learned:** Right. The lower framerate (5 fps) restored the model's perception, driving True Positives from
186 back up to 231 and dropping missed events from 256 to 193.

## Round 7 — REVERTED · F1 0.414→0.394 · TP 221 · called 0/6

**Thought:** The model is severely mistiming serves, timestamping them 1 to 2 seconds late (when the ball
crosses the net or lands, rather than at contact). This is a definitional misunderstanding of
what the "time of contact" means for a serve.

**Changed:** Update the prompt's CRITICAL RULES to explicitly define the timing of a serve ("do not wait for
the ball to cross the net") and to instruct the model not to guess a serve if the clip begins
with the ball already in flight.

**Learned:** I was completely wrong. Every metric moved in the opposite direction of my prediction.

---

## Current beliefs

# What I know about this pipeline

### Established
- 15-second chunks at 5 fps (75 frames) maximize recall and headline F1 (0.414), stabilizing True Positives at ~230.
- Increasing framerate to 10 fps over 15-second chunks (150 frames) hurts recall due to attention dilution, dropping true positives significantly and increasing missed contacts.
- Assist-only definitions for `set` align with the taxonomy, successfully dropping raw predictions from 130 to 44. 
- The model cannot reliably track the ball's physical trajectory. Forcing it to ignore player intention and rely purely on ball trajectory harms attack recall.
- Text-based negative constraints ("EXACTLY ONE LABEL", "NO DEAD TIME", "DO NOT guess") fail to reduce invented contacts and actively backfire by causing the model to fixate on the suppressed classes (e.g., driving serve predictions up).
- Complex sequence rules (e.g., "If the ball is already in play, it is NOT a serve") fail to prevent misclassifications like receives being labeled as serves, especially at chunk boundaries.

### Ruled out
- `chunk_len` of 30.0s. Tested and rejected; temporal dilution drops TP by 81 and destroys F1.
- Forcing `point: false` on rally-ending errors. Tested and rejected; disrupts parser and doubles `score_margin_err`.
- Text-only mid-rally serve warnings and strict trajectory rules. Tested and rejected; models fail to parse global timeline position at chunk boundaries and cannot physically see the ball well enough to satisfy strict "over the net" requirements.
- Increasing framerate to 10 fps to fix fast-action perception. Tested and rejected; it suppresses overall prediction volume, worsening recall and headline F1 (0.400 -> 0.366) because the model struggles to parse 150 frames per chunk.
- Fixing deep-court misclassifications with logical sequence constraints. Tested and rejected; models fail to apply temporal rally logic to correct their spatial biases.
- Fixing serve timing and hallucinations via explicit negative constraints ("Timestamp the EXACT moment", "DO NOT guess"). Tested and rejected; it decreases True Positives, increases hallucinated serves, and destabilizes other classes like blocks.

### Open
- Are the remaining invented contacts caused by cross-chunk overlap that evades the harness deduplication (e.g., timestamps differing by 0.5s), or are they pure within-chunk hallucinations?
- Will reducing the chunk length further (e.g., 10 seconds) at 5 fps improve temporal attention without severing rallies too often?
- Can we improve action classification and bypass the need for temporal sequence logic by teaching the model to rely purely on player body mechanics and court positioning?

### Current hypothesis
The pipeline is bottlenecked by the model's inability to track a fast-moving ball, infer causal rally sequences across chunk boundaries, and obey negative constraints. The single most promising next line of attack is to rewrite the prompt's taxonomy definitions to focus almost entirely on positive descriptions of player positioning and body mechanics. For instance, a player jumping and swinging above the net is an attack; a player bumping the ball low from the backcourt is a receive/dig; a player standing alone behind the far baseline tossing the ball is a serve. Since the model can see static player bodies much better than it can track the ball's physical path or reason about what "should" logically happen next, body-mechanics-based heuristics should improve classification accuracy and lower hallucination rates.