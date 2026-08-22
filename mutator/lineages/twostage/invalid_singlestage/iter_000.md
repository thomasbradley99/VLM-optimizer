# Iteration 0

## CONJECTURE
The model generates 204 GHOST events (predictions matching no ground truth), with 190 occurring during live rallies. This is a definitional mismatch driven by over-reporting. The human scout recorded the first contact (receive/dig) and the third contact (attack/kill), but only recorded the intermediate second contact (the set) if it directly resulted in a kill (the `assist-2` rule, yielding just 47 sets against 183 attacks). 

However, Stage 2's prompt explicitly forces the model to "Report one event per real contact". When Stage 1 correctly perceives the ~136 non-assist intermediate passes and passes them to Stage 2, Stage 2 is obligated to output an event. Because they don't qualify as sets, Stage 2 misclassifies them as digs, receives, or attacks (e.g., 114 predicted digs vs 86 real, 154 predicted attacks vs 131 real). By explicitly instructing Stage 1 to ignore a team's intermediate pass unless it leads to a floor hit, we will starve Stage 2 of these unrecorded contacts, drastically cutting `n_pred` (and ghosts) without losing `tp`.

## CHANGE
Modify the Stage 1 prompt to explicitly instruct the vision model to omit a team's intermediate second contact unless it directly leads to the ball hitting the opponent's floor, while also generalizing the hardcoded "10-second" video length.

```config
{"lever": "prompt",
 "prompt": "You are watching a short clip of a volleyball match from one fixed camera.\nA net runs vertically up the middle of the frame, dividing it into a LEFT court and a RIGHT court.\nOnly the foreground court matters -- the one with the referee on the raised stand.\n\nDo NOT name any volleyball actions. Report only what you can literally see, as a list of moments,\neach with a time in seconds from the start of this clip:\n\n  - the ball is on the LEFT or the RIGHT of the net\n  - the ball CROSSES the net, and in which direction\n  - a player MAKES CONTACT with the ball: the time, which side they stand on, their shirt colour,\n    their number if legible, and whether they were airborne or on the ground\n  - after that contact the ball goes UP (staying their side), OVER (across the net), DOWN (to the\n    floor), or OUT\n  - the ball HITS THE FLOOR, and on which side\n  - nobody is playing: the ball is being carried, rolled, held, or lying still\n\nCRITICAL: Do not report every contact. You MUST omit and ignore a team's second contact during their possession (an intermediate pass that merely puts the ball UP for a teammate) UNLESS the team's next contact sends the ball OVER the net AND hits the opponent's floor.\n\nBe precise about the times. If nothing is in play, say so in one line.\n\nThis clip begins at {start} seconds into the match.",
 "chunk_len": 10.0, "overlap": 3.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect the overall number of predictions (`n_pred`) and invented ghosts to drop significantly as the intermediate passes are filtered out before reaching Stage 2. Because these contacts were never in the ground truth, `tp` will remain roughly flat, leading to a strong increase in `headline_f1`. The artificial inflation of `dig`, `receive`, and `attack` predictions will subside.

```predictions
[{"metric": "n_pred", "direction": "down", "from": 555, "to_approx": 430},
 {"metric": "invented", "direction": "down", "from": 214, "to_approx": 120},
 {"metric": "tp", "direction": "flat", "from": 240, "to_approx": 235},
 {"metric": "headline_f1", "direction": "up", "from": 0.434, "to_approx": 0.485},
 {"metric": "dig_pred_count", "direction": "down", "from": 114, "to_approx": 85},
 {"metric": "attack_pred_count", "direction": "down", "from": 154, "to_approx": 125},
 {"metric": "receive_pred_count", "direction": "down", "from": 85, "to_approx": 70},
 {"metric": "set_pred_count", "direction": "flat", "from": 37, "to_approx": 35}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
n_pred                          down to ~430     flat 555 -> 546     X     X
invented                        down to ~120       up 214 -> 268     X     X
tp                              flat to ~235     down 240 -> 187     X     X
headline_f1                     up to ~0.485 down 0.434 -> 0.341     X     X
dig_pred_count                   down to ~85      down 114 -> 80    OK    OK
attack_pred_count               down to ~125     down 154 -> 130    OK    OK
receive_pred_count               down to ~70         up 85 -> 97     X     X
set_pred_count                   flat to ~35         up 37 -> 88     X     X

direction 2/8   magnitude 2/8
```

headline_f1 0.434 -> 0.341   (-0.093)
n_pred 555 -> 546   missed 209 -> 272   invented 214 -> 268
pipeline: $2.23, 0 cached, 0 failed

## VERDICT
Wrong about the mechanism, and completely wrong about the solution. 

The numbers show a catastrophic failure: true positives plummeted (240 -> 187) while invented "ghost" events spiked (214 -> 268), dragging the F1 score down from 0.434 to 0.341. My conjecture that the model was accurately detecting intermediate passes and that we just needed to suppress them was incorrect. By instructing the vision model (Stage 1) to apply complex, multi-step sports rules ("omit contact 2 unless contact 3 is a kill"), I forced it to evaluate conditional logic that requires foresight within the rally. This confused the model into dropping valid events. Furthermore, injecting terminology like "intermediate pass" and "putting the ball UP" into the Stage 1 prompt caused a massive backfire: `set_pred_count` more than doubled (37 -> 88). Stage 1 likely outputted this terminology in its visual descriptions to explain its filtering logic, which Stage 2 then blindly misread as affirmative set detections.

The change made things worse because it violated the fundamental separation of concerns in the pipeline. Stage 1 must remain a dumb, literal describer of visual facts; sports logic and event filtering belong exclusively in Stage 2. 

The right move is to abandon this line of attack, revert the prompt entirely back to the baseline configuration, and attack the ghost/miss problem from an architectural angle, specifically the chunking parameters.
