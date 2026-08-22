# Iteration 1

## CONJECTURE
The current drop in F1 is driven by a definitional mismatch in Stage 2. In the previous round, relaxing the `set` rule to "puts the ball UP for a team-mate" was too broad compared to the scout's "assist-2". This caused `set` predictions to explode to 155 (against 47 real). The confusion matrix shows this overly broad definition absorbed 20 true attacks, 17 true digs, and 8 true receives, while generating 69 ghost sets. Additionally, instructing the model not to flag errors as points broke point attribution when a team scores off an opponent's error. This is a definitional failure: the model is seeing the contacts but misclassifying them because its prompt rules are looser than the scout's derivations.

## CHANGE
I am changing `prompt2` to tighten the definition of `set` to only contacts that "set up an attack", and redefining `point` to only contacts that directly score (like a kill or ace), reverting the semantic damage from the previous round.

```config
{"lever": "prompt2",
 "mode": "two_stage",
 "prompt": "You are watching a 10-second clip of a volleyball match from one fixed camera.\nA net runs vertically up the middle of the frame, dividing it into a LEFT court and a RIGHT court.\nOnly the foreground court matters -- the one with the referee on the raised stand.\n\nDo NOT name any volleyball actions. Report only what you can literally see, as a list of moments,\neach with a time in seconds from the start of this clip:\n\n  - the ball is on the LEFT or the RIGHT of the net\n  - the ball CROSSES the net, and in which direction\n  - a player MAKES CONTACT with the ball: the time, which side they stand on, their shirt colour,\n    their number if legible, and whether they were airborne or on the ground\n  - after that contact the ball goes UP (staying their side), OVER (across the net), DOWN (to the\n    floor), or OUT\n  - the ball HITS THE FLOOR, and on which side\n  - nobody is playing: the ball is being carried, rolled, held, or lying still\n\nBe precise about the times. If nothing is in play, say so in one line.\n\nThis clip begins at {start} seconds into the match.",
 "prompt2": "Below are literal observations from a 10-second volleyball clip that began at\n{start} seconds into the match. You cannot see the video. Work out which volleyball actions these observations correspond to.\n\nUse the sequence to reason:\n  a rally begins with a serve, struck from behind the back line\n  the first contact answering a serve is a receive\n  a contact answering an opponent's attack is a dig\n  any contact that sends the ball OVER the net is an attack\n  an attack after which the ball hits the opponent's floor is a kill\n  a contact at the net by an airborne player with hands high is a block\n  a contact that sets up an attack is a set\n\nReport one event per real contact:\n  t       {start} plus the observed offset, in absolute match seconds\n  side    \"left\" or \"right\" -- the half the contacting player was standing in\n  number  shirt number as a string, or null\n  error   true if the ball went into the net or out of bounds off this contact\n  point   true if this contact directly scored a point for the team making it (e.g., a kill, ace, or scoring block)\n\nDo not invent contacts the observations do not mention. If the observations describe no play, return an empty list.\n\nOBSERVATIONS:\n{obs}",
 "chunk_len": 10.0, "overlap": 3.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect the number of `set` predictions to drop sharply, restoring precision and reducing the denominator `n_pred`. True positives (TP) should increase because true digs and attacks will no longer be misclassified as sets. The score margin error should also fall. Serve F1 should remain roughly flat since its definition is unchanged.

```predictions
[{"metric": "set_pred_count", "direction": "down", "from": 155, "to_approx": 65},
 {"metric": "n_pred", "direction": "down", "from": 668, "to_approx": 580},
 {"metric": "tp", "direction": "up", "from": 229, "to_approx": 250},
 {"metric": "score_margin_err", "direction": "down", "from": 43, "to_approx": 25},
 {"metric": "serve_f1", "direction": "flat", "from": 0.320, "to_approx": 0.320}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                   down to ~65     flat 155 -> 149     X     X
n_pred                          down to ~580     flat 668 -> 681     X     X
tp                                up to ~250       up 229 -> 257    OK    OK
score_margin_err                 down to ~25       down 43 -> 29    OK    OK
serve_f1                       flat to ~0.32   up 0.447 -> 0.507     X     X

direction 2/5   magnitude 2/5
```

headline_f1 0.376 -> 0.418   (+0.042)
n_pred 668 -> 681   missed 185 -> 158   invented 303 -> 289
pipeline: $3.72, 0 cached, 0 failed

## VERDICT
I was right about the F1 improvement and the score margin recovery, but completely wrong about the mechanism constraining `set` predictions. 

The numbers show that changing the definition of `set` from "puts the ball UP for a team-mate" to "sets up an attack" did absolutely nothing to stem the flood of false sets (`set_pred_count` stayed flat at 149). The model interprets almost any intermediate contact as a set under either definition. 

However, `tp` increased to 257 and `score_margin_err` dropped to 29, exactly as predicted. By removing the confusing negative constraint about errors from the `point` definition, we successfully restored point attribution and improved overall accuracy. The biggest surprise was `serve_f1` jumping from 0.447 to 0.507 despite its definition remaining unchanged. This suggests that giving the model simpler, more coherent instructions for points and errors reduced its overall cognitive load, improving its reasoning across the board.

Because F1 improved significantly (0.376 -> 0.418), this is a good round. However, since semantic tweaks to `set` have definitively failed to stop hallucinations, the right move is to pivot to modifying the physical inputs (framerate or cropping) to prevent the model from inventing contacts to fill gaps in its vision.
