# Iteration 0

## CONJECTURE
This is a definitional mismatch. "set" is vastly over-predicted (151 predicted vs 47 real). The confusion matrix shows predicted "sets" incorrectly absorbing 24 attacks, 18 digs, and 4 receives, while also generating 85 ghosts (79 of them during live rallies). In the ground truth, the rule `ACTION == 'assist-2'` implies the scout only records a set if it is an assist that directly leads to a kill. However, the model is currently predicting "set" for every normal overhand pass. 

Additionally, "kill" is severely under-predicted (29 predicted vs 52 real) because the prompt does not differentiate it from "attack" (which is over-predicted). By explicitly defining "set" as an assist preceding a kill and explicitly telling the model to ignore normal passes and casual dead-time touches, we can aggressively cut `n_pred` (removing ghosts) without losing True Positives. We will also define "kill" to distinguish it from "attack".

## CHANGE
Redefine the event types in the prompt to match the scout's strict definitions, explicitly instructing the model to ignore normal passes and dead-time touches, and clearly separating attacks from kills.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start:.2f} seconds into the match.\n\nList only specific meaningful volleyball events in live play. Do NOT report every touch (e.g., ignore normal passes and casual touches between rallies). For each event give:\n  t       - the time of contact in absolute match seconds\n  type    - must be one of:\n            serve: initial hit from the baseline\n            receive: first contact defending a serve\n            dig: first contact defending an attack\n            set: ONLY an assist that directly precedes a 'kill' (ignore passes before a normal 'attack')\n            attack: any offensive hit sent over the net that does not score a point\n            kill: an attack that directly scores a point and ends the rally\n            block: deflecting an attack at the net\n  side    - \"left\" or \"right\": which half of the frame the player is standing in\n  number  - the player's jersey number as a string, or null if you cannot read it\n  error   - true if the touch was a mistake\n  point   - true if the rally ended here and a point was scored",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By stopping the model from reporting normal passes, the number of predicted sets and overall predictions will drop significantly, eliminating a huge chunk of ghosts. Because true sets only occur before kills in the ground truth, we won't lose TP. Differentiating kills from attacks will increase the kill predictions to match the 52 real kills.

```predictions
[{"metric": "set_pred_count", "direction": "down", "from": 151, "to_approx": 70},
 {"metric": "n_pred", "direction": "down", "from": 683, "to_approx": 580},
 {"metric": "kill_pred_count", "direction": "up", "from": 29, "to_approx": 50},
 {"metric": "headline_f1", "direction": "up", "from": 0.341, "to_approx": 0.380},
 {"metric": "tp", "direction": "flat", "from": 210, "to_approx": 210}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                   down to ~70      down 151 -> 43    OK    OK
n_pred                          down to ~580     down 683 -> 594    OK    OK
kill_pred_count                    up to ~50         up 29 -> 58    OK    OK
headline_f1                      up to ~0.38    up 0.341 -> 0.39    OK    OK
tp                              flat to ~210       up 210 -> 223     X     X

direction 4/5   magnitude 4/5
```

headline_f1 0.341 -> 0.390   (+0.049)
n_pred 683 -> 594   missed 179 -> 216   invented 312 -> 260
pipeline: $1.82, 0 cached, 0 failed

## VERDICT
Right about the mechanism, wrong about the size/direction of TP. I predicted TP would remain flat, but it actually went up (210 -> 223). 

The numbers show that aligning the definitions for "set" and "kill" worked exactly as intended: predicted sets plummeted (151 -> 43), predicted kills surged (29 -> 58), and overall ghost predictions dropped (invented 312 -> 260). This pushed the headline F1 from 0.341 to 0.390. The unexpected increase in TP suggests that by clearing out the noise of normal passes and dead-ball touches, the model was able to focus and correctly classify more of the valid events.

However, we still have a very noisy output. Out of 594 predictions, 260 are complete ghosts (invented), and of the 334 that match a ground truth timestamp, 111 have the wrong class (since TP is 223). We are also missing 216 ground truth events completely. I believe the right move is to keep this prompt but increase the temporal resolution so the model can actually see the split-second contacts it is missing or confusing.
