# Iteration 0

## CONJECTURE
The current Stage 2 prompt suffers from two clear definitional mismatches with the ground truth. First, it explicitly instructs the model to report a `set` "ONLY when the next contact is a kill". The scout's ground truth for set is `ACTION == 'assist-2'` (47 events), which is not restricted to kills. This forces the model to suppress sets or misclassify them (e.g., as digs), predicting only 37 sets. Second, the prompt flags `point` as "true if the rally ended on this contact". Because the scoring rule is "Every point-flagged event is a point for the team that made it", this instruction forces the model to flag a team's errors (like serving out of bounds) as points for that same team, deeply corrupting the implied match result (predicting a white win +18 instead of a blue win -11, score margin err 29). This is a definitional failure.

## CHANGE
I am changing `prompt2` to remove the restrictive kill condition from the `set` definition, and redefining `point` so that errors are not flagged as points for the team making them.

```config
{"lever": "prompt2",
 "prompt": "You are watching a 10-second clip of a volleyball match from one fixed camera.\nA net runs vertically up the middle of the frame, dividing it into a LEFT court and a RIGHT court.\nOnly the foreground court matters -- the one with the referee on the raised stand.\n\nDo NOT name any volleyball actions. Report only what you can literally see, as a list of moments, each with a time in seconds from the start of this clip:\n\n  - the ball is on the LEFT or the RIGHT of the net\n  - the ball CROSSES the net, and in which direction\n  - a player MAKES CONTACT with the ball: the time, which side they stand on, their shirt colour, their number if legible, and whether they were airborne or on the ground\n  - after that contact the ball goes UP (staying their side), OVER (across the net), DOWN (to the floor), or OUT\n  - the ball HITS THE FLOOR, and on which side\n  - nobody is playing: the ball is being carried, rolled, held, or lying still\n\nBe precise about the times. If nothing is in play, say so in one line.\n\nThis clip begins at {start:.2f} seconds into the match.",
 "prompt2": "Below are literal observations from a 10-second volleyball clip that began at\n{start:.2f} seconds into the match. You cannot see the video. Work out which volleyball actions these observations correspond to.\n\nUse the sequence to reason:\n  a rally begins with a serve, struck from behind the back line\n  the first contact answering a serve is a receive\n  a contact answering an opponent's attack is a dig\n  any contact that sends the ball OVER the net is an attack\n  an attack after which the ball hits the opponent's floor is a kill\n  a contact at the net by an airborne player with hands high is a block\n  a contact that puts the ball UP for a team-mate is a set\n\nReport one event per real contact:\n  t       {start:.2f} plus the observed offset, in absolute match seconds\n  side    \"left\" or \"right\" -- the half the contacting player was standing in\n  number  shirt number as a string, or null\n  error   true if the ball went into the net or out of bounds off this contact\n  point   true if this contact directly won the rally for the team making it (do not flag errors as points)\n\nDo not invent contacts the observations do not mention. If the observations describe no play, return an empty list.\n\nOBSERVATIONS:\n{obs}",
 "mode": "two_stage",
 "chunk_len": 10.0, "overlap": 3.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
Removing the set constraint will directly increase the number of predicted sets, and fixing the point definition will dramatically fix the team attribution in the match score.

```predictions
[{"metric": "set_pred_count", "direction": "up", "from": 37, "to_approx": 50},
 {"metric": "set_recall", "direction": "up", "from": 0.234, "to_approx": 0.350},
 {"metric": "score_margin_err", "direction": "down", "from": 29, "to_approx": 10},
 {"metric": "tp", "direction": "up", "from": 240, "to_approx": 248},
 {"metric": "n_pred", "direction": "up", "from": 555, "to_approx": 565},
 {"metric": "serve_pred_count", "direction": "flat", "from": 96, "to_approx": 96}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                     up to ~50        up 37 -> 155    OK     X
set_recall                       up to ~0.35    up 0.34 -> 0.596    OK     X
score_margin_err                 down to ~10         up 29 -> 43     X     X
tp                                up to ~248     flat 240 -> 229     X     X
n_pred                            up to ~565       up 555 -> 668    OK     X
serve_pred_count                 flat to ~96       down 96 -> 88     X     X

direction 3/6   magnitude 0/6
```

headline_f1 0.434 -> 0.376   (-0.058)
n_pred 555 -> 668   missed 209 -> 185   invented 214 -> 303
pipeline: $3.61, 0 cached, 0 failed

## VERDICT
Right about the mechanism for sets, but drastically wrong about the size, and completely wrong about the score margin. 

Removing the restriction on sets caused an explosion in predictions (from 37 up to 155, where ground truth is only 47), which successfully drove up recall but destroyed precision, causing a massive spike in invented events (up to 303) and dropping the F1 score. 

On the score margin, my attempt to redefine points made the error worse (jumping from 29 to 43). Because the harness scoring rule is strictly "Every point-flagged event is a point for the team that made it", instructing the model *not* to flag a team's errors as points just means no one gets the point when a team serves out of bounds. The schema is structurally incapable of correctly attributing a point to Team B on Team A's unforced error unless Team B is falsely credited with a contact. 

This change made things significantly worse by unleashing a flood of false-positive sets and breaking the point counting further. The right move is to abandon this semantic tweaking, revert to the previous configuration, and attack the physical video parameters (FPS/crop) as hypothesized at the end of the previous round.
