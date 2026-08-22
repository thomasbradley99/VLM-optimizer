# Iteration 7

## CONJECTURE
The model is severely mistiming serves, timestamping them 1 to 2 seconds late (when the ball crosses the net or lands, rather than at contact). This is a definitional misunderstanding of what the "time of contact" means for a serve. For example, at 19:54 the real serve is missed, and at 19:55 the model outputs a ghost serve at the exact same moment as the real receive. This late timestamping pushes serves outside the 1.0s matching window (causing 65 completely missed serves) and frequently overlaps them with the subsequent receive (causing 44 "action" errors where a real receive is predicted as a serve). 

Additionally, the model hallucinates 27 serves inside live rallies. Because the 15s chunks often start mid-rally, the model sees a deep-court hit with the ball in the air and mistakenly assumes it is a serve, lacking the context that the point is already underway. This is a perception gap caused by chunk boundaries.

## CHANGE
Update the prompt's CRITICAL RULES to explicitly define the timing of a serve ("do not wait for the ball to cross the net") and to instruct the model not to guess a serve if the clip begins with the ball already in flight.

```config
{"lever": "prompt",
 "prompt": "You are an expert volleyball statistician scouting one match from a fixed camera.\n\nCONTEXT. Several courts are in use at once. Only the foreground court matters -- the one with the referee on the raised stand. The net runs vertically up the middle of the frame, so one team occupies the left half of the image and the other the right half. Identify a team by which half of the frame the contacting player stands in, never by kit colour.\n\nThis clip begins at {start} seconds into the match.\n\nTAXONOMY. Every contact belongs to exactly one of seven classes. Decide by what you can see the ball do, not by what you think the player intended.\n\n  serve    starts the rally. A player stands behind the baseline, tosses the ball, and hits it OVER the net. If the ball is already in play, it is NOT a serve.\n  receive  the immediate response to a serve. The ball arrives from over the net and is passed to a TEAMMATE.\n  dig      the response to an opponent's attack. The ball arrives from over the net and is passed to a TEAMMATE.\n  set      a contact that places the ball for a team-mate to attack, BUT ONLY report it if the resulting attack is a kill (an assist).\n  attack   any contact mid-rally that sends the ball OVER the net to the opponents.\n  kill     an attack that ends the rally immediately.\n  block    a contact made at the net by a player with hands above it.\n\nCRITICAL RULES:\n1. TRAJECTORY: Serves and attacks MUST cross the net. Receives and digs MUST stay on their own side.\n2. TIMING & DEAD TIME: Ignore pre-serve bouncing. Timestamp the EXACT moment the player STRIKES the ball. For serves, do not wait for the ball to cross the net.\n3. MID-RALLY CLIPS: Clips are 15s and may start mid-rally. If the ball is already flying at the start, DO NOT guess a serve. Never confuse a deep court receive for a serve.\n4. EXACTLY ONE LABEL: Never output multiple rows for the same contact or timestamp.\n\nREPORTING. Give one row per contact you actually observe:\n  t        time of contact in absolute match seconds, to a fraction of a second\n  type     one of the seven above\n  side     \"left\" or \"right\", the half of the frame the contacting player is in\n  number   the jersey number as a string, or null if you cannot read it\n  error    true if the contact was a mistake -- into the net, out of bounds, mishandled\n  point    true ONLY if the team making THIS contact won the rally. If this contact is an error that loses the rally, point MUST be false.\n\nIf nothing happens in this clip, return an empty list.",
 "chunk_len": 15.0, "overlap": 4.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By pulling the serve timestamps back to the actual moment of contact, many of the 65 missed serves will fall into the matching window and become True Positives. This will simultaneously free up the receive timestamps, converting many of the 44 action errors back into correctly matched receives. The mid-rally rule will drop the hallucinated serve count, shrinking n_pred.

```predictions
[{"metric": "serve_f1", "direction": "up", "from": 0.367, "to_approx": 0.500},
 {"metric": "serve_pred_count", "direction": "down", "from": 149, "to_approx": 120},
 {"metric": "tp", "direction": "up", "from": 231, "to_approx": 250},
 {"metric": "n_pred", "direction": "down", "from": 566, "to_approx": 530},
 {"metric": "invented", "direction": "down", "from": 209, "to_approx": 180},
 {"metric": "block_pred_count", "direction": "flat", "from": 9, "to_approx": 9}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_f1                          up to ~0.5 down 0.532 -> 0.496     X    OK
serve_pred_count                down to ~120       up 149 -> 160     X     X
tp                                up to ~250     flat 231 -> 221     X     X
n_pred                          down to ~530     flat 566 -> 572     X     X
invented                        down to ~180     flat 209 -> 212     X     X
block_pred_count                  flat to ~9          up 9 -> 18     X     X

direction 0/6   magnitude 1/6
```

headline_f1 0.414 -> 0.394   (-0.020)
n_pred 566 -> 572   missed 193 -> 190   invented 209 -> 212
pipeline: $1.97, 0 cached, 0 failed

## VERDICT
I was completely wrong. Every metric moved in the opposite direction of my prediction.

The numbers show that adding explicit, aggressive negative constraints ("do not wait", "DO NOT guess a serve", "Never confuse") completely backfired. Instead of reducing hallucinated serves, the model fixated on them, driving `serve_pred_count` up from 149 to 160. Because the model was over-indexing on these negative rules, overall True Positives fell from 231 to 221, and headline F1 dropped from 0.414 to 0.394. Curiously, `block_pred_count` also doubled (9 to 18), indicating that the prompt changes destabilized the model's general classification boundaries.

My change made things worse because LLMs notoriously struggle with negative instructions—telling a model "DO NOT guess a serve" brings serves to the forefront of its attention and often increases the behavior you want to suppress. 

The right move is to abandon this branch, revert to the Iteration 6 configuration, and attack from a completely different angle: abandoning negative rules and sequence logic in favor of positive, observable body mechanics.
