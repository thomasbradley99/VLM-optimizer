# Iteration 1

## CONJECTURE
The model is failing due to a definitional mismatch introduced in the prompt. By instructing the vision model to apply complex conditional logic ("omit and ignore a team's second contact... UNLESS the team's next contact sends the ball OVER"), we forced it to predict the future of a rally to decide whether to report a current event. This breaks the separation of concerns, confusing the model into dropping valid events (TP fell to 187, misses spiked to 272) while hallucinating others as it attempts to output its filtering logic (set predictions spiked to 88). Stage 1 must remain a literal describer of visual facts.

## CHANGE
Remove the conditional instruction entirely, returning the prompt to a pure visual description task so the model reports exactly what it sees without applying sports logic.

```config
{"lever": "prompt",
 "prompt": "You are watching a short clip of a volleyball match from one fixed camera.\nA net runs vertically up the middle of the frame, dividing it into a LEFT court and a RIGHT court.\nOnly the foreground court matters -- the one with the referee on the raised stand.\n\nDo NOT name any volleyball actions. Report only what you can literally see, as a list of moments,\neach with a time in seconds from the start of this clip:\n\n  - the ball is on the LEFT or the RIGHT of the net\n  - the ball CROSSES the net, and in which direction\n  - a player MAKES CONTACT with the ball: the time, which side they stand on, their shirt colour,\n    their number if legible, and whether they were airborne or on the ground\n  - after that contact the ball goes UP (staying their side), OVER (across the net), DOWN (to the\n    floor), or OUT\n  - the ball HITS THE FLOOR, and on which side\n  - nobody is playing: the ball is being carried, rolled, held, or lying still\n\nBe precise about the times. If nothing is in play, say so in one line.\n\nThis clip begins at {start} seconds into the match.",
 "chunk_len": 10.0, "overlap": 3.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
Removing the complex filtering rule will cause the model to report all contacts again. True positives will recover substantially, and the artificial spike in "set" predictions (caused by the model trying to describe intermediate passes to satisfy the prompt) will disappear. Total predictions will remain roughly flat as the gain in true positives replaces the loss in hallucinated filtering events.

```predictions
[{"metric": "set_pred_count", "direction": "down", "from": 88, "to_approx": 40},
 {"metric": "tp", "direction": "up", "from": 187, "to_approx": 240},
 {"metric": "missed", "direction": "down", "from": 272, "to_approx": 219},
 {"metric": "n_pred", "direction": "flat", "from": 546, "to_approx": 556},
 {"metric": "headline_f1", "direction": "up", "from": 0.341, "to_approx": 0.434}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                   down to ~40        up 88 -> 112     X     X
tp                                up to ~240     flat 187 -> 191     X     X
missed                          down to ~219     flat 272 -> 266     X     X
n_pred                          flat to ~556       up 546 -> 582     X    OK
headline_f1                     up to ~0.434 flat 0.341 -> 0.337     X     X

direction 0/5   magnitude 1/5
```

headline_f1 0.341 -> 0.337   (-0.004)
n_pred 546 -> 582   missed 272 -> 266   invented 268 -> 298
pipeline: $2.14, 0 cached, 0 failed

## VERDICT
I was completely wrong. The numbers show that removing the conditional rule did not recover the true positives (which stayed flat at 191) and actually exacerbated the hallucinated sets (which jumped from 88 to 112). 

This proves that the complex sports logic was not the primary cause of the missing detections or the hallucinated sets. The fact that `set_pred_count` spiked even higher under the "purely visual" prompt indicates that explicitly instructing the model to label post-contact trajectories ("goes UP", "goes OVER") forces it to over-report upward ball movements. Stage 2 then blindly parses these as sets. Furthermore, the failure to recover true positives (misses stubbornly sitting at 266) strongly implies the model physically cannot see the events it is being asked to describe. 

We should abandon tweaking this prompt's wording for now. The right move is to attack the physical video parameters. The combination of `fps: 5` (which allows fast spikes to fall between frames) and the vertical `crop` (y=330, height=620, which likely cuts off the top of the screen where high sets occur) is almost certainly blinding the model.
