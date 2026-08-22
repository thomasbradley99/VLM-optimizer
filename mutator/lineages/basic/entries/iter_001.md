# Iteration 1

## CONJECTURE
The model is predicting events from the three other volleyball matches occurring simultaneously in the background. This is evidenced by strings of ghost predictions that look exactly like complete rallies happening in dead time or simultaneously with main-court rallies. For example, between 17:42 and 17:48, the model predicts a full ghost sequence: serve, receive, attack, dig, attack. Because these events are genuine volleyball actions but not from the scouted match, they massively inflate `n_pred` (260 invented events) without contributing to `TP`. This is a perception issue—the model is looking at too much of the frame.

## CHANGE
Apply a crop to the video to isolate the main court and completely remove the crowd and the three other matches in progress at the top of the frame.

```config
{"lever": "crop",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start:.2f} seconds into the match.\n\nList only specific meaningful volleyball events in live play. Do NOT report every touch (e.g., ignore normal passes and casual touches between rallies). For each event give:\n  t       - the time of contact in absolute match seconds\n  type    - must be one of:\n            serve: initial hit from the baseline\n            receive: first contact defending a serve\n            dig: first contact defending an attack\n            set: ONLY an assist that directly precedes a 'kill' (ignore passes before a normal 'attack')\n            attack: any offensive hit sent over the net that does not score a point\n            kill: an attack that directly scores a point and ends the rally\n            block: deflecting an attack at the net\n  side    - \"left\" or \"right\": which half of the frame the player is standing in\n  number  - the player's jersey number as a string, or null if you cannot read it\n  error   - true if the touch was a mistake\n  point   - true if the rally ended here and a point was scored",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
Cropping out the background courts will cause a massive drop in invented ghost events and overall predictions, without hurting the true positive count on the main court. Because the denominator `n_pred` will shrink substantially while `TP` holds steady, the headline F1 will increase significantly.

```predictions
[{"metric": "invented", "direction": "down", "from": 260, "to_approx": 130},
 {"metric": "n_pred", "direction": "down", "from": 594, "to_approx": 450},
 {"metric": "tp", "direction": "flat", "from": 223, "to_approx": 223},
 {"metric": "headline_f1", "direction": "up", "from": 0.390, "to_approx": 0.440}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
invented                        down to ~130     down 260 -> 204    OK     X
n_pred                          down to ~450     down 594 -> 499    OK    OK
tp                              flat to ~223     down 223 -> 173     X     X
headline_f1                      up to ~0.44   down 0.39 -> 0.33     X     X

direction 2/4   magnitude 1/4
```

headline_f1 0.390 -> 0.330   (-0.060)
n_pred 594 -> 499   missed 216 -> 255   invented 260 -> 204
pipeline: $1.61, 0 cached, 0 failed

## VERDICT
Right about the mechanism of reducing predictions, but completely wrong about the true positives holding steady. The crop successfully reduced the number of invented events (260 down to 204), but it severely damaged the model's ability to detect real events on the main court, causing true positives to plummet from 223 to 173 and missed events to spike (216 to 255). 

The crop made things worse because cutting 330 pixels from the top of the frame likely chopped off the ball during high arcs (like serves, sets, and looping passes) or entirely removed the players standing on the far side of the court. Without seeing the ball's full trajectory or the back-court players, the model lost the context of the rally. We should abandon this crop, return to the full-frame configuration, and attack the background-court ghosts via prompting instead.
