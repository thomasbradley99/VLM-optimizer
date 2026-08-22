# Iteration 0

## CONJECTURE
The model suffers from three major definitional mismatches that cause rampant over-prediction and team attribution errors. This is a definitional failure, not a perception issue. 
1. `set` is massively over-predicted (130 predicted vs 47 real) because the scout's rule (`ACTION == 'assist-2'`) only records a set if it leads directly to a kill, whereas the prompt asks the model to report all sets. The confusion matrix shows these phantom sets absorbing 30 attacks and 14 digs.
2. `serve` has 33 in-rally ghosts and incorrectly matches 45 real `receive`s because the model frequently misinterprets the first contact it sees in a mid-rally clip as a serve.
3. The match result is skewed (+15 score_margin_err for White) because the model assigns `point: true` to a player making a rally-ending error (like a failed dig), which inadvertently awards the point to the team making the mistake rather than the team that won the rally.

## CHANGE
Update the prompt's taxonomy to tightly align with the scout's rules: restrict `set` to only those that lead to a kill (assists), explicitly forbid mid-rally `serve` and `receive` predictions, and clarify that the `point` flag must only be true if the contacting team won the rally. 

```config
{"lever": "prompt",
 "prompt": "You are an expert volleyball statistician scouting one match from a fixed camera.\n\nCONTEXT. Several courts are in use at once. Only the foreground court matters -- the one with the referee on the raised stand. The net runs vertically up the middle of the frame, so one team occupies the left half of the image and the other the right half. Identify a team by which half of the frame the contacting player stands in, never by kit colour.\n\nThis clip begins at {start} seconds into the match.\n\nTAXONOMY. Every contact belongs to exactly one of seven classes. Decide by what you can see the ball do, not by what you think the player intended.\n\n  serve    the single contact that begins a rally, struck from behind the back line. Never report a serve mid-rally.\n  receive  the first defensive contact answering a serve. Maximum one per rally.\n  dig      a defensive contact answering an attack; the ball stays on that side\n  set      a contact that places the ball for a team-mate to attack, BUT ONLY report it if the resulting attack is a kill (an assist).\n  attack   any contact that sends the ball over the net to the opponents\n  kill     an attack that ends the rally immediately\n  block    a contact made at the net by a player with hands above it\n\nREPORTING. Give one row per contact you actually observe:\n  t        time of contact in absolute match seconds, to a fraction of a second\n  type     one of the seven above\n  side     \"left\" or \"right\", the half of the frame the contacting player is in\n  number   the jersey number as a string, or null if you cannot read it\n  error    true if the contact was a mistake -- into the net, out of bounds, mishandled\n  point    true ONLY if the team making THIS contact won the rally. If this contact is an error that loses the rally, point MUST be false.\n\nIf nothing happens in this clip, return an empty list.",
 "chunk_len": 15.0, "overlap": 4.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect the total number of predictions to drop significantly as the model stops hallucinating mid-rally serves and non-assist sets. The F1 for `set` and `serve` will rise because the denominator shrinks, while overall TP holds steady. The `score_margin_err` will drastically decrease because error-making players will no longer be credited with points.

```predictions
[{"metric": "set_pred_count", "direction": "down", "from": 130, "to_approx": 50},
 {"metric": "serve_pred_count", "direction": "down", "from": 151, "to_approx": 115},
 {"metric": "n_pred", "direction": "down", "from": 649, "to_approx": 500},
 {"metric": "score_margin_err", "direction": "down", "from": 26, "to_approx": 8},
 {"metric": "tp", "direction": "flat", "from": 237, "to_approx": 235}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                   down to ~50      down 130 -> 44    OK    OK
serve_pred_count                down to ~115     flat 151 -> 152     X     X
n_pred                          down to ~500     down 649 -> 565    OK    OK
score_margin_err                  down to ~8         up 26 -> 54     X     X
tp                              flat to ~235     flat 237 -> 230    OK    OK

direction 3/5   magnitude 3/5
```

headline_f1 0.395 -> 0.413   (+0.017)
n_pred 649 -> 565   missed 167 -> 202   invented 266 -> 217
pipeline: $1.93, 0 cached, 0 failed

## VERDICT
Right about the mechanism for `set`, but completely wrong about `serve` and `score_margin_err`. 

The numbers show a definitive success on `set`: `set_pred_count` dropped perfectly from 130 to 44, matching the true assist count, which also drove the overall `n_pred` drop. 

However, `serve_pred_count` stubbornly stayed flat at 152. My instruction ("Never report a serve mid-rally") failed because a 15-second chunk often starts mid-rally; the model sees a clip start, sees an overhead hit (like a back-row attack or free ball), assumes it is the beginning of the rally, and flags it as a serve. 

My change made `score_margin_err` much worse, doubling it from 26 to 54. By forcing `point: false` on rally-ending errors, I inadvertently starved the scoring parser. The parser clearly expects `point: true` to mark the *end of the rally*, and uses the combination of `point: true` and `error: true` to award the point to the opposing team. By suppressing the `point` flag on errors, points won by opponent mistakes were completely dropped from the match score, causing massive divergence in the score margin. 

The right move is to revert the `point` logic to flag the end of the rally, explicitly enforce the `error` flag on those ending events, and aggressively redefine the visual requirements for a `serve`.
