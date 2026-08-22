# Iteration 2

## CONJECTURE
The crop `1920:620:0:330` applied in iter 001 caused a severe loss of perception. It chopped off 330 pixels from the top of the frame, which likely removed the ball during high arcs (like serves and sets) or completely cut out players on the far side of the court. The numbers confirm this perception failure: true positives plummeted from 223 (iter 000) to 173 (iter 001), and missed events spiked from 216 to 255. The crop actively prevents the model from seeing the game. We must abandon this crop and revert to the full frame to restore our baseline visibility, so we can tackle the background ghosts via the prompt in a future round.

## CHANGE
I am changing the `crop` back to `null` to restore the full 1920x1080 frame, keeping the prompt and all other settings exactly as they are.

```config
{"lever": "crop",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start:.2f} seconds into the match.\n\nList only specific meaningful volleyball events in live play. Do NOT report every touch (e.g., ignore normal passes and casual touches between rallies). For each event give:\n  t       - the time of contact in absolute match seconds\n  type    - must be one of:\n            serve: initial hit from the baseline\n            receive: first contact defending a serve\n            dig: first contact defending an attack\n            set: ONLY an assist that directly precedes a 'kill' (ignore passes before a normal 'attack')\n            attack: any offensive hit sent over the net that does not score a point\n            kill: an attack that directly scores a point and ends the rally\n            block: deflecting an attack at the net\n  side    - \"left\" or \"right\": which half of the frame the player is standing in\n  number  - the player's jersey number as a string, or null if you cannot read it\n  error   - true if the touch was a mistake\n  point   - true if the rally ended here and a point was scored",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect headline F1 and true positives to return to their iter 000 levels (~0.390 F1, ~223 TP). Because we are removing the crop, the model will see the whole court again, which will lower missed events but increase `n_pred` and invented events as the background matches become visible again. Block F1 will remain flat at 0 because blocks are intrinsically hard to detect and were likely zero in the baseline as well.

```predictions
[{"metric": "headline_f1", "direction": "up", "from": 0.330, "to_approx": 0.390},
 {"metric": "tp", "direction": "up", "from": 173, "to_approx": 223},
 {"metric": "n_pred", "direction": "up", "from": 499, "to_approx": 594},
 {"metric": "missed", "direction": "down", "from": 255, "to_approx": 216},
 {"metric": "invented", "direction": "up", "from": 204, "to_approx": 260},
 {"metric": "block_f1", "direction": "flat", "from": 0.000, "to_approx": 0.000}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
headline_f1                      up to ~0.39     up 0.33 -> 0.39    OK    OK
tp                                up to ~223       up 173 -> 223    OK    OK
n_pred                            up to ~594       up 499 -> 594    OK    OK
missed                          down to ~216     down 255 -> 216    OK    OK
invented                          up to ~260       up 204 -> 260    OK    OK
block_f1                        flat to ~0.0    down 0.2 -> 0.08     X    OK

direction 5/6   magnitude 6/6
```

headline_f1 0.330 -> 0.390   (+0.060)
n_pred 499 -> 594   missed 255 -> 216   invented 204 -> 260
pipeline: $0.00, 169 cached, 0 failed

## VERDICT
Right. Reverting the crop perfectly restored the baseline performance exactly as predicted (F1 returned to 0.390, TP back to 223, invented back to 260). This definitively confirms that the aggressive top crop in Iteration 1 was physically removing the ball trajectory or far-court players from the main match. 

The only metric that moved unexpectedly was `block_f1`. I missed that it had actually improved during the cropped iteration (to ~0.20), and reverting the crop dropped it back down to 0.08. This is a very interesting signal: it suggests that while the top crop blinded the model to high arcs (losing serves and digs), it removed distracting background noise and forced the model to focus on net-level interactions for the main court, improving block detection. 

We will keep the full frame because the loss of 50 TPs is unacceptable, but our next move is to attack the background courts via prompting to try and get the best of both worlds.
