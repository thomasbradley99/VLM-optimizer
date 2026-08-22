# Mutator lab notes

Each round: diagnose, commit a falsifiable prediction to disk, re-run the pipeline, grade
the prediction against computed numbers, write a verdict. Losing rounds are auto-reverted.

**TP** = events matched in time *and* typed correctly. F1 can rise while TP falls, simply
by predicting less — so TP is the number that says whether the model actually sees more.

| round | F1 | TP | predictions made | called right | kept |
|---|---|---|---|---|---|
| _base_ | 0.342 | **202** | 630 | – | – |
| 0 | 0.342 → 0.345 | 190 | 553 | 3/5 | yes |
| 1 | 0.345 → 0.339 | 179 | 507 | 2/4 | **reverted** |
| 2 | 0.345 → 0.350 | 186 | 512 | 2/4 | yes |
| 3 | 0.350 → 0.350 | 184 | 500 | 1/5 | yes |
| 4 | 0.350 → 0.351 | 190 | 532 | 1/5 | yes |
| 5 | 0.351 → 0.362 | 200 | 556 | 2/5 | yes |
| 6 | 0.362 → 0.336 | 178 | 510 | 2/4 | **reverted** |
| 7 | 0.362 → 0.340 | 181 | 515 | 1/5 | **reverted** |
| 8 | 0.349 → 0.333 | 171 | 476 | 2/5 | **reverted** |
| 9 | 0.349 → 0.319 | 165 | 483 | 1/5 | **reverted** |
| 10 | 0.349 → 0.358 | 190 | 511 | 0/5 | **reverted** |
| 11 | 0.349 → 0.277 | 124 | 346 | 1/5 | **reverted** |
| 12 | 0.349 → 0.391 | 239 | 673 | 4/5 | yes |
| 13 | 0.391 → 0.308 | 142 | 372 | 0/5 | **reverted** |
| 15 | 0.440 → 0.439 | 303 | 831 | 3/5 | **reverted** |
| 16 | 0.440 → 0.446 | 306 | 822 | 2/6 | **reverted** |
| 17 | 0.440 → 0.443 | 312 | 857 | 1/5 | **reverted** |
| 18 | 0.440 → 0.411 | 298 | 900 | 3/6 | **reverted** |
| 19 | 0.440 → 0.436 | 315 | 895 | 3/6 | **reverted** |
| 20 | 0.440 → 0.402 | 238 | 633 | 4/6 | **reverted** |
| 21 | 0.455 → 0.417 | 277 | 779 | 3/8 | **reverted** |
| 22 | 0.417 → 0.449 | 284 | 716 | 4/5 | yes |
| 23 | 0.449 → 0.463 | 300 | 745 | 3/9 | **reverted** |
| 24 | 0.463 → 0.445 | 279 | 704 | 2/6 | **reverted** |
| 25 | 0.445 → 0.460 | 281 | 671 | 3/6 | **reverted** |
| 26 | 0.460 → 0.440 | 267 | 664 | 1/5 | **reverted** |
| 27 | 0.440 → 0.410 | 248 | 660 | 0/5 | **reverted** |
| 28 | 0.410 → 0.452 | 283 | 701 | 3/5 | yes |

Best F1 round 23 (0.463, TP 300). Best TP 315 — against **202 for the original prompt**. Predictions right 57/150 (38%).

---

## Round 0 — kept · F1 0.342→0.345 · TP 190 · called 3/5

**Thought:** The model is failing due to two distinct mechanisms working together to scramble the labels: 1.
**Definitional (Set over-prediction):** The scout only recorded sets that lead to a kill
(`assist-2`, 47 real sets vs 52 kills).

**Changed:** Redefine `set` to strictly mean an assist (only reporting it if it leads to a kill) to match the
scout's protocol, and rewrite the event definitions to use visual descriptions rather than
sequence counters ("first", "second") to prevent a missed serve from causing an off-by-one
labeling cascade.

**Learned:** I was right about the mechanism for the `set` over-prediction, but wrong about the sequence fix
for serves and receives. The prompt successfully slashed `set` predictions (from 144 down to 27)
by narrowing the definition to assists.

## Round 1 — REVERTED · F1 0.345→0.339 · TP 179 · called 2/4

**Thought:** The model over-predicts `serve` and cannibalizes `receive` because it relies on a false prior
that every video clip must begin with a serve. When a 30-second clip starts mid-rally, the model
takes the very first contact it sees—often a defensive pass made well inside the court—and
forces a `serve` label onto it.

**Changed:** I am explicitly warning the model that clips often start mid-rally (so the first contact is
often not a serve) and reinforcing the negative constraint that passes made from inside the
court lines are NEVER serves.

**Learned:** I was completely wrong. The explicit instruction that clips start mid-rally and the hard
constraint that "passes inside the court are NEVER serves" completely failed to reduce
`serve_pred_count`, which stayed flat (actually rising from 123 to 126).

## Round 2 — kept · F1 0.345→0.350 · TP 186 · called 2/4

**Thought:** The model's failure to distinguish `serve` from `receive` is a visual perception issue; spatial
constraints (like "behind the end line" or "inside the court") failed because the model
struggles to parse depth and court boundaries. The confusion matrix shows 34 real `receive`s and
10 real `attack`s misclassified as `serve`.

**Changed:** I am replacing the spatial definitions of `serve`, `receive`, and `dig` with kinematic ones,
requiring a `serve` to have a self-toss and overhead strike, while labeling defensive passes as
underhand forearm bumps.

**Learned:** Wrong about the mechanism. The assumption that the model could use fine-grained kinematic
features (like a "self-toss" before a strike) to veto bad serves completely failed;
`serve_pred_count` remained stubbornly flat at 126 rather than dropping to the predicted ~80.

## Round 3 — kept · F1 0.350→0.350 · TP 184 · called 1/5

**Thought:** The persistent confusion between `serve` and `receive` (35 real receives labeled as serves) and
`attack` vs `receive`/`dig` (40 real attacks labeled as receives/digs) is a perception failure.
The model is functionally blind to spatial positioning (court lines) and fine player kinematics
(tosses, bumps) which we tried in previous iterations.

**Changed:** I am redefining the action types to rely primarily on ball trajectory (explicitly stating
whether the ball travels "OVER THE NET" or "STAYS ON THE SAME SIDE") rather than player poses or
spatial court locations.

**Learned:** I was completely wrong about the mechanism. Adding explicit ball trajectory constraints ("OVER
THE NET" vs "STAYS ON THE SAME SIDE") failed to stop the model from hallucinating serves, with
`serve_pred_count` barely moving (126 -> 120).

## Round 4 — kept · F1 0.350→0.351 · TP 190 · called 1/5

**Thought:** The model is suffering from a massive "off-by-one" labeling cascade caused by a rigid global
sequence bias. It expects every rally to follow a global order: Serve, Receive, Set, Attack,
Dig.

**Changed:** I am replacing the event definitions with a "Per-Team Possession" framework.

**Learned:** Wrong. The "off-by-one sequence cascade" hypothesis was completely incorrect.

## Round 5 — kept · F1 0.351→0.362 · TP 200 · called 2/5

**Thought:** The pipeline is failing due to two mechanisms that scramble the labels. First, `attack` is
frequently misclassified as `receive` (25 times) or `dig` (12 times) because Iteration 4 defined
`receive` and `dig` rigidly as a "FIRST contact".

**Changed:** I am removing all sequence-counting language ("FIRST contact", "3rd contact") from the event
definitions to stop attacks from being labeled as receives when prior contacts are missed.

**Learned:** I was wrong about the mechanism. Adding the explicit "dead ball vs response" rule completely
failed to reduce `serve_pred_count` (128 -> 131), and removing the sequence constraints did not
improve `attack_f1` (0.231 -> 0.22).

## Round 6 — REVERTED · F1 0.362→0.336 · TP 178 · called 2/4

**Thought:** The model over-predicts `serve` because it suffers from a "lazy classification" reflex, relying
on pre-trained visual bias (e.g., any backcourt pass looks like a serve) and ignoring our
textual constraints. `serve` is predicted 131 times against 118 real, and the confusion matrix
shows it absorbing 35 `receive`s and 13 `attack`s.

**Changed:** I am changing the JSON schema to include an intermediate reasoning field, `ball_starting_state`,
which forces the model to explicitly state whether the ball was "dead" or "in-flight" *before*
it outputs the event `type`.

**Learned:** Right about the mechanism, wrong about the size and the severe side effects. The numbers show
that adding the `ball_starting_state` field did shift the model's behavior in the predicted
directions: `serve_pred_count` dropped (131 -> 119) and `receive_f1` rose (0.166 -> 0.200),
confirming that forcing an explicit evaluation of the ball state intercepts the model's lazy
reflex to label backcourt passes as serves.

## Round 7 — REVERTED · F1 0.362→0.340 · TP 181 · called 1/5

**Thought:** The model over-predicts `serve` because it suffers from a visual bias, mistaking deep-court
passes for serves. It ignores logical rules, kinematics, trajectory, and 3D court geometry.

**Changed:** I am changing the `serve` definition to rely purely on 2D screen topology, restricting it to the
"extreme left or right edge of the video frame" and forbidding actions "further inward" from
being labeled as serves.

**Learned:** Wrong. The spatial 2D framing constraint completely failed.

## Round 8 — REVERTED · F1 0.349→0.333 · TP 171 · called 2/5

**Thought:** The model is suffering from a massive perception failure caused by visual distraction, not a
definitional gap. It missed 229 real events entirely while inventing 224 fake events.

**Changed:** I am changing the `crop` parameter to physically strip away the top 330 pixels of the video
before scaling, completely removing the background matches from the image the model sees.

**Learned:** I was right about the mechanism reducing false positives, but completely wrong about the side
effects on recall. The physical crop did remove background distraction, successfully dropping
`invented` events from 224 to 189.

## Round 9 — REVERTED · F1 0.349→0.319 · TP 165 · called 1/5

**Thought:** The model over-predicts `serve` (133 vs 118 real), absorbing 33 receives and 12 attacks, because
the current prompt actively forbids sequence logic ("Classify each event purely by its visual
action. Do not enforce global sequences").

**Changed:** I am removing the anti-sequence vetoes and the ineffective "dead ball" visual rule, replacing
them with explicit instructions to use structural flow (e.g., classifying a pass as a receive if
it handles a serve, or a dig if it handles an attack) to disambiguate visually similar actions.

**Learned:** I was wrong. Re-introducing sequence logic and structural flow did not help the model
disambiguate actions; instead, it caused a severe drop in `receive_f1` (0.196 down to 0.124) and
overall recall (TPs dropped from 191 to 165).

## Round 10 — REVERTED · F1 0.349→0.358 · TP 190 · called 0/5

**Thought:** The pipeline is suffering from instruction overload. Every time we add explicit text heuristics
(whether sequence flows, negative vetoes, spatial limits, or dead-ball rules) to solve the
serve/receive/attack confusion, True Positives drop or stay flat, while overall F1 only rises
due to predicting fewer events.

**Changed:** I am removing all descriptive definitions and logical constraints for the event types (except
the `set` = assist rule), presenting just the bare class names so the model relies purely on its
pre-trained visual recognition.

**Learned:** Wrong about the mechanism, though lucky with a small F1 gain. I predicted that removing
descriptive constraints would cause total predictions (`n_pred`) and True Positives (`tp`) to
rise as the model stopped artificially suppressing events.

## Round 11 — REVERTED · F1 0.349→0.277 · TP 124 · called 1/5

**Thought:** The pipeline has hit a hard perception ceiling where 229 true events are missed entirely because
5 fps (one frame every 200ms) is too slow to capture fast volleyball contacts. Volleyball is
highly kinetic; split-second actions like attacks and digs often occur entirely between frames
or appear as illegible motion blur at low frame rates, forcing the model to either guess or miss
them.

**Changed:** I am changing the `fps` parameter from 5 to 10 to give the model twice the temporal resolution,
allowing it to see fast actions that currently fall between frames.

**Learned:** Wrong. The metrics moved exactly opposite to my prediction, but the numbers show a mechanical
failure rather than a perceptual one: the harness reports "39 failed" chunks.

## Round 12 — kept · F1 0.349→0.391 · TP 239 · called 4/5

**Thought:** The model misses 229 real events entirely. In Iteration 11, we hypothesized this was due to low
temporal resolution and doubled the frame rate to 10 fps, but this crashed the API because
30-second clips at 10 fps generated 300 frames per call.

**Changed:** I am decreasing the `chunk_len` to 15.0 seconds and `overlap` to 4.0 seconds (updating the
prompt text to match) to test if a shorter attention window improves event recall before we
introduce higher frame rates.

**Learned:** Right about the mechanism, wrong about the size. The numbers clearly show that shrinking the
temporal window significantly improves the model's ability to spot events, proving that it
suffers from attention saturation over long video clips.

## Round 13 — REVERTED · F1 0.391→0.308 · TP 142 · called 0/5

**Thought:** The model is still missing 169 real events entirely, indicating a persistent perception gap for
fast actions. While reducing clip length to 15 seconds successfully eliminated attention
saturation (raising TP from 191 to 239), the model is still limited by the baseline 5 fps
temporal resolution (one frame every 200ms).

**Changed:** I am changing the `fps` to 10 to double the temporal resolution, allowing the model to see fast
kinematic actions without exceeding the 150-frame payload size limit we implicitly rely upon.

**Learned:** Wrong. The numbers show a massive drop across the board, but this is entirely because the API
crashed: 105 chunks failed to process.

## Round 15 — REVERTED · F1 0.440→0.439 · TP 303 · called 3/5

**Thought:** The model predicts 412 completely invented events because it misinterprets casual, non-
competitive contacts during the dead time between points as active rally events. In a narrow
6-second clip, players warming up or tossing the ball to the referee looks like a valid event
unless the model is explicitly told to evaluate the competitive context.

**Changed:** I am adding explicit prompt rules for "DEAD TIME VETO" and "CLIP BOUNDARIES" to stop the model
from hallucinating events between points or mislabeling boundary contacts as serves, and I am
redefining the `point` flag so it is never awarded on an error.

**Learned:** Right about the mechanism for fixing the score margin, but wrong about the dead time veto. The
numbers show that explicitly redefining `point` to exclude `error` contacts successfully reduced
the `score_margin_err` (57 down to 42) and the clip boundary warning slightly reduced false
serves.

## Round 16 — REVERTED · F1 0.440→0.446 · TP 306 · called 2/6

**Thought:** The model is predicting 412 completely hallucinated events because it accurately perceives
physical ball contacts but fails to apply the prompt's spatial and semantic constraints. When
the vision encoder detects a bump from a background match or a casual dead-time toss, it
immediately outputs it as a JSON event.

**Changed:** I am changing the `thinking` lever from "low" to "medium" to allow the model to use reasoning
tokens to evaluate context and apply negative constraints (ignoring background matches and dead
time) before outputting predictions.

**Learned:** Wrong. The `thinking` mechanism completely failed to suppress hallucinated events.

## Round 17 — REVERTED · F1 0.440→0.443 · TP 312 · called 1/5

**Thought:** The model hallucinates 412 events because it cannot reliably map the semantic concepts of
"foreground" vs "background" (or identifying the referee's stand) to what it sees, causing it to
eagerly report hits from other matches visible in the distance. However, vision-language models
are highly sensitive to relative 2D object size.

**Changed:** I am updating the background veto in the prompt to define the target court purely by player size
on screen ("LARGE" vs "TINY"), ordering the model to filter events purely by relative visual
scale.

**Learned:** I was wrong. The relative player size constraint failed completely to reduce `invented` events,
which remained stubbornly flat (412 -> 427), and instead it actively harmed our recall (`missed`
rose from 106 to 120).

## Round 18 — REVERTED · F1 0.440→0.411 · TP 298 · called 3/6

**Thought:** The pipeline is suffering from two major contextual/definitional failures that massively inflate
`n_pred` and tank F1. First, the model predicts 412 completely invented events because it cannot
map the abstract semantic instruction "main court" to its visual field, leading it to eagerly
log hits from the other matches in the background.

**Changed:** I am modifying the prompt to introduce a strict `BACKGROUND SPATIAL RULE` (filtering events in
the top 20% of the screen), a `CLIP BOUNDARIES` warning to suppress mid-rally serve
hallucinations, and explicitly redefining the `point` flag to be false on errors.

**Learned:** Right about the mechanism for serves and score logic, wrong about the size and direction of the
spatial rule. The numbers show that the clip boundary warning and error-logic decoupling
successfully dropped `serve` predictions (226 down to 187) and `score_margin_err` (57 down to
35), validating those specific translation fixes.

## Round 19 — REVERTED · F1 0.440→0.436 · TP 315 · called 3/6

**Thought:** The pipeline is suffering from two pure definitional gaps that inflate `n_pred` and skew score
attribution. First, because 6-second clips often start mid-rally, the model mistakenly labels
the first defensive pass it sees as a `serve` (predicting 226 serves vs 118 real) because it
lacks the preceding context to know the ball wasn't dead.

**Changed:** I am updating the prompt to embed a strict clip boundary warning directly into the `serve`
definition to suppress mid-rally hallucinated serves, and redefining the `point` flag to
strictly exclude errors.

**Learned:** Right about the mechanism for serves and scores, wrong about the stability of the overall noise.
The boundary warnings for serves and the strict logic excluding errors from `point` successfully
pushed `serve_pred_count` (226 -> 202) and `score_margin_err` (57 -> 49) in the correct
directions.

## Round 20 — REVERTED · F1 0.440→0.402 · TP 238 · called 4/6

**Thought:** The pipeline predicts 412 completely `invented` events largely as a structural artifact of
processing the video in narrow 6-second chunks. By slicing the video into 930 independent API
calls, we create hundreds of isolated temporal windows where casual dead-time shuffles or
background court hits are mistaken for active rallies, because the model lacks the surrounding
frames to see that the ball was out of play.

**Changed:** I am changing `chunk_len` from 6.0 to 10.0 (while maintaining the baseline prompt except to
update the text from "6 seconds" to "10 seconds" and `{start:.2f}` to `{start}`) to mechanically
halve the number of clips and reduce the opportunities for hallucination.

**Learned:** Right about the mechanism, wrong about the size. I predicted that reducing the number of chunks
would structurally starve the model of hallucination opportunities, and it did exactly that:
`invented` events dropped massively from 412 to 257, and `serve_pred_count` fell from 226 to
173.

## Round 21 — REVERTED · F1 0.455→0.417 · TP 277 · called 3/8

**Thought:** The pipeline is suffering from massive over-prediction (324 ghosts) and type confusion due to
four specific definitional mismatches between the model and the scout: 1. **Team attribution of
errors:** The model flags `point=true` for errors (like spiking into the net).

**Changed:** I am updating the prompt to fix these definitional mismatches by explicitly vetoing dead-time
contacts, instructing the model to completely skip continuation block touches and regular sets
(rather than mislabeling them), distinguishing attacks from digs by their over-the-net
trajectory, and explaining the logic for the `point` flag to stop awarding points for opponent
errors.

**Learned:** I was completely wrong. The numbers show a severe regression across the board: instead of
dropping, `n_pred` and `invented` surged (up to 779 and 366, respectively), while True Positives
dropped from 293 to 277.

## Round 22 — kept · F1 0.417→0.449 · TP 284 · called 4/5

**Thought:** The pipeline is suffering from a definitional mismatch where the model assigns multiple event
types to the exact same physical ball contact, generating dozens of "ghost" predictions inside
rallies. Because the deduplication step only merges events of the SAME type, outputting an
`attack` and a `kill` for the same hit (e.g., at 21:18) bypasses deduplication and creates an
immediate ghost.

**Changed:** I am updating the prompt to explicitly forbid multiple event types for the same timestamp,
instructing the model to output exactly one type per physical contact, and tightening the
`serve` and `point` definitions to prevent short-clip hallucinations.

**Learned:** Right about the mechanism for deduplication (mutually exclusive events), but wrong about the
serve negative veto. The numbers show that forbidding multiple event types for the same contact
successfully closed a definitional loophole.

## Round 23 — REVERTED · F1 0.449→0.463 · TP 300 · called 3/9

**Thought:** The pipeline is suffering from two major definitional gaps that inflate `n_pred` with ghosts and
reduce `TP` through misclassification. 1.

**Changed:** I am updating the prompt to explicitly define an `attack` strictly by spatial outcome ("sends
the ball OVER the net"), require serves to start from a "stationary hold" (banning mid-flight
hits), enforce a dead-time veto requiring defensive formation for a real serve, and anchor the
`side` variable strictly to the left/right of the physical net.

**Learned:** I was right about the mechanism for fixing attacks, but wrong about the vetoes for serves and
the baseline for team accuracy. Redefining `attack` strictly by spatial outcome ("sends the ball
OVER the net") correctly stripped the model's bias toward "defensive intent," successfully
converting misclassified digs and receives into true positives.

## Round 24 — REVERTED · F1 0.463→0.445 · TP 279 · called 2/6

**Thought:** The model is severely misattributing terminal contacts (kills) to the wrong team, as evidenced
by the implied match result where Blue's points plummeted (REAL: 64, YOURS: 18) and White's
surged. When Blue hits a winner that lands on White's side, the model erroneously logs a contact
(often a `dig` or `kill`) for White because it tracks where the ball LANDS on the floor, not
where it was HIT.

**Changed:** I am updating the prompt to explicitly define spatial attribution ("Log the side where the
player HITS the ball, NOT where the ball lands"), warning the model that 6s clips often start
mid-rally so the first contact is rarely a serve, and vetoing ball bounces on the floor as valid
events.

**Learned:** I was wrong. The attempt to fix spatial attribution logic and veto end-of-rally bounces
backfired, tanking `kill_recall` (0.558 -> 0.442) and dropping True Positives (300 -> 279).

## Round 25 — REVERTED · F1 0.445→0.460 · TP 281 · called 3/6

**Thought:** The model is suffering from a massive DEFINITIONAL mismatch regarding offensive vs. defensive
actions, leading to symmetric confusion (29 real attacks called `dig`, 23 real digs called
`attack`) and 67 ghost attacks inside rallies.

**Changed:** I am updating the prompt to replace spatial-only action rules with kinematic cues (e.g., attacks
are jumps/swings, digs are low reactions), explicitly vetoing easy free-ball passes to remove
ghost attacks, and relaxing the serve's "visible toss" requirement to rescue serves cut off by
the 6s clip boundary.

**Learned:** Right about the mechanism, wrong about the size. The numbers show that replacing spatial-only
rules with kinematic cues (jumps/swings vs.

## Round 26 — REVERTED · F1 0.460→0.440 · TP 267 · called 1/5

**Thought:** The model is systematically predicting serves 1-2 seconds before they actually happen (e.g.,
20:56 GHOST, 20:57 MISS; 24:07 GHOST, 24:08 MISS). This is a definitional mismatch: the model
considers the ball toss to be a valid physical contact and logs it as the `serve` event, which
falls outside the greedy 1.0s matching window for the actual hit, resulting in both a GHOST and
a MISS.

**Changed:** I am explicitly vetoing the serve toss in the prompt ("DO NOT log the ball toss as a contact")
so the model waits for the actual hit, and I am rewriting the `side` definition to strictly use
the left/right "side of the screen" to prevent perspective confusion during deep serves and
kills.

**Learned:** Wrong. I predicted that explicitly forbidding the model from logging the serve toss would shift
its timestamps forward, converting MISS/GHOST pairs into True Positives and dropping overall
serve predictions.

## Round 27 — REVERTED · F1 0.440→0.410 · TP 248 · called 0/5

**Thought:** The high number of invented events (284 ghosts) dragging down F1 is caused by a severe
definitional bug in the prompt: the instruction "Output EXACTLY ONE event type per physical ball
contact." The model interprets this as a mandate to exhaustively label almost every contact it
sees, forcing it to misclassify normal passes and free-ball bumps as `receive` or `dig`, and
mid-rally back-row hits as `serve`. This explains why 83% of the phantom events (230) occur
inside live rallies, including a massive 46 `serve` ghosts mid-rally.

**Changed:** I am replacing the command that forced exhaustive labeling with a strict filter ("DO NOT log
every ball contact...

**Learned:** I was completely wrong. The numbers show that explicitly commanding the model to "SKIP THE REST"
and "DO NOT log every ball contact" had almost zero effect on the hallucinated events
(`invented` barely moved from 284 to 274), but it actively suppressed real events, dropping True
Positives by 19 and tanking the F1 score.

## Round 28 — kept · F1 0.410→0.452 · TP 283 · called 3/5

**Thought:** The drop in TP and F1 in Round 27 was caused by a definitional over-restriction of `dig` ("hard-
fought... powerful downward-driven spike...

**Changed:** I am updating the prompt to broaden the `dig` definition to simply passing an opponent's attack,
and strictly forbidding `serve` or `receive` unless players are in stationary starting
formations, to stop the model from logging mid-rally hits as serves.

**Learned:** Right about the mechanism for `dig`, wrong about the mechanism for `serve`. Broadening the `dig`
definition worked exactly as intended, surging predictions from 32 back up to 112 and driving
True Positives from 248 to 283.

---

## Current beliefs

# What I know about this pipeline

# What I know about this pipeline

### Established
- **Restrictive definitions crash recall:** Defining actions too strictly (e.g., describing a `dig` as handling a "downward-driven spike") crashes recall (TPs dropped by ~35) because the model misses softer attacks or tips. Broad, functional definitions ("defensive pass handling an opponent's attack") are required to capture the full spectrum of the event.
- **Kinematic cues trump pure spatial rules for attacks/digs:** Defining an attack purely as "ANY contact that sends the ball OVER the net" causes the model to incorrectly log defensive free-ball overpasses as attacks. Providing kinematic cues (jumps/swings for attacks, low-to-the-ground reactions for digs) successfully fixes this confusion and reduces invented events.
- **Relaxing visual requirements for cut-off clips:** Because we use 6-second clips, actions like serve tosses often happen off-screen. Relaxing the strict requirement to see a "visible toss" significantly improves serve recall by allowing the model to infer the action from context.
- **Mutually exclusive events:** Forcing the model to output "EXACTLY ONE event type per physical ball contact" successfully stops it from outputting multiple labels for the exact same hit (e.g., `attack` and `kill`). This significantly drops `invented` events and improves F1.
- **Shorter chunks improve recall up to a point:** Reducing clip length to 6s (30 frames) maximizes True Positives by limiting attention saturation. Moving to 10s chunks (50 frames) causes severe attention saturation, tanking recall (TPs drop massively).
- **Mechanical reduction of chunks suppresses hallucinations:** Slicing the video into fewer API calls mechanically starves the model of opportunities to invent events in dead time. 
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the 20-30 range (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes and back-row attacks with serves. This is a severe visual reflex that ignores descriptive text.
- **Strict negative vetoes reduce recall:** Adding intermediate JSON reasoning fields, strict negative visual vetoes, or complex spatial rules causes the model to drop True Positives across the board. The model's visual perception is too fuzzy to handle rigid visual disqualifiers.
- **The top of the frame is critical:** The upper third of the video cannot be cropped, as it contains the ball in flight during high arcs. Losing sight of the ball breaks the model's ability to track the rally.
- **Verbose definitions inflate false positives:** Highly detailed text descriptions of physical actions cause the model to hallucinate events by matching partial visual cues.

### Ruled out
- **Stationary hold & Defensive formation vetoes:** Attempting to stop serve hallucinations by requiring the server to start from a "stationary hold", verifying the receiving team is in a "defensive formation", or stating "Players MUST be in stationary starting formations" fails completely. Serve predictions remain flat and hallucinations persist.
- **Exhaustive filtering instructions:** Explicit commands to ignore non-pivotal contacts ("DO NOT log every ball contact", "SKIP THE REST") dropped True Positives from 267 to 248 but failed to reduce `invented` events (which only moved from 284 to 274). The model cannot textually filter its own over-generation without collateral damage to real recall.
- **Toss vetoes:** Explicitly commanding the model "DO NOT log the ball toss as a contact" fails to shift serve timestamps forward. Serve predictions remain flat and overall recall drops. Negative visual vetoes ("Pink elephants") simply do not work.
- **Strict screen-based team attribution:** Forcing the model to strictly use the left/right half of the screen to determine the team `side` reduces true positives, likely because the camera angle isn't perfectly centered or players drift near the midline.
- **Explicit spatial attribution logic:** Adding complex instructions to "Log the side where the player HITS the ball, NOT where the ball lands" to fix team attribution backfires, tanking `kill_recall` and overall True Positives. 
- **"Pink Elephant" negative vetoes on serves:** Explicitly telling the model "If a player hits a ball that is already moving... it is NEVER a serve" failed completely, driving serve predictions UP.
- **Increasing chunk length to 10s+ to reduce hallucinations:** While 10s chunks mechanically reduce false positives, the 50-frame length induces unacceptable attention saturation and drops true positives massively. 
- **Semantic context vetoes ("Dead time veto"):** Telling the model to ignore warmups, dead time between points, or post-rally floor bounces does not work. Capitalized, verbose instructions actively increase false positives or destroy recall.
- **Reasoning tokens (Thinking / CoT):** Giving the model `thinking: "medium"` to reason about background courts and dead-ball context before generating JSON failed to reduce the ~400 hallucinated events. 
- **10 FPS temporal resolution:** Requesting 10 fps causes massive API failures. We are strictly bound to 5 fps.
- **Hard cropping the background:** Physically cropping the top 330 pixels to hide background matches reduces false positives, but it ruins foreground recall by hiding the ball during high passes.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" failed to suppress hallucinated serves. 
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **JSON Chain-of-Thought for visual state:** Forcing the model to explicitly output whether the ball was "dead" or "in-flight" before the `type` field dropped recall and lowered F1.

### Open
- Given that textual vetoes fail to suppress hallucinations, what is the optimal NMS window to merge jittery hallucinated duplicates across overlapping chunks?
- Can we safely eliminate chunk overlap entirely if we are using short 6-second clips?

### Current hypothesis
With prompt modifications yielding negative returns on precision and visual vetoes repeatedly failing, the focus must shift mechanically to overlapping windows. We are currently predicting ~700 events for ~435 actual ground truth events. A 6.0-second chunk with an `overlap` of 2.0 seconds means 33% of the match is processed twice. While True Positives merge cleanly via Non-Maximum Suppression (NMS) because their timestamps are accurate across both chunks, dead-time hallucinations often have jittery, inexact timestamps that fail to merge. This creates double-counted false positives. By reducing `overlap` to 0.5 seconds for 6.0s chunks, we will shrink the double-exposure window and mechanically cut duplicate hallucinations without sacrificing real recall.