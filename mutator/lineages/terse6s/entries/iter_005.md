# Iteration 5

## CONJECTURE
The steep drop in True Positives (from 235 to 207) and particularly `set` recall (falling to 14.9%) was caused by a definitional mismatch: the scout recorded setups broadly as `assist-2`, but the prompt falsely forced the model to ignore sets unless they led to a kill. 

Simultaneously, we have a major perception/context error driving down precision: the confusion matrix shows 38 real `receive` events were misclassified as `serve`. Because the 15-second chunks frequently start mid-rally, the model often misses the true serve and wrongly assumes the very first touch it sees must be a serve or receive, which also explains the 58 in-rally phantoms for those two types. 

This is fixed by reverting `set` and `dig` to standard definitions to recover TP, while explicitly describing the physical appearance of a serve (tossed from out of bounds) and strictly instructing the model not to guess `serve` or `receive` if the clip starts with the ball already in play.

## CHANGE
Revert to standard, broad definitions for event types to recover recall, but add explicit physical descriptions for `serve` and `receive` alongside a strict rule to ignore mid-rally clip starts for those two classes.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\nNote: Clips are short and often start in the middle of an ongoing rally. If the ball is already in play when the clip begins, DO NOT guess a 'serve' or 'receive' for that rally.\n\nList ball contacts you see DURING LIVE PLAY ONLY. Ignore all dead-time contacts (e.g., players celebrating, passing the ball back, or warming up between rallies).\n\nRules for types:\n- serve: One team tosses the ball and hits it over the net from out of bounds behind the baseline to start a point.\n- receive: The opposing team's first contact passing the serve. Usually a forearm pass inside the court.\n- dig: A defensive pass saving an opponent's attack.\n- set: An overhead pass setting up an attack.\n- attack: An offensive hit directing the ball across the net.\n- kill: An attack that immediately scores a point.\n- block: A defensive jump at the net intercepting an opponent's attack.\n\nFor each contact give:\n  t       - time of contact in absolute match seconds\n  type    - serve, receive, dig, set, attack, kill or block\n  side    - \"left\" or \"right\": which half of the frame the player is in\n  number  - jersey number as a string, or null\n  error   - true if the contact was a mistake\n  point   - true if the rally ended here",
 "chunk_len": 15.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By defining `serve` physically ("tosses and hits from out of bounds") and preventing mid-rally guesses, the misclassification of receives as serves will plummet, raising serve precision and dropping overall serve predictions. Meanwhile, standardizing `set` will significantly boost its recall, lifting overall TP. Because receives will stop being called serves but will also lose their mid-clip phantom occurrences, receive prediction count will remain relatively flat.

```predictions
[{"metric": "set_recall", "direction": "up", "from": 0.149, "to_approx": 0.350},
 {"metric": "tp", "direction": "up", "from": 207, "to_approx": 245},
 {"metric": "serve_pred_count", "direction": "down", "from": 139, "to_approx": 100},
 {"metric": "serve_precision", "direction": "up", "from": 0.396, "to_approx": 0.600},
 {"metric": "receive_pred_count", "direction": "flat", "from": 107, "to_approx": 110}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_recall                       up to ~0.35   up 0.213 -> 0.383    OK    OK
tp                                up to ~245       up 207 -> 218    OK     X
serve_pred_count                down to ~100     down 139 -> 132    OK     X
serve_precision                   up to ~0.6 down 0.547 -> 0.508     X     X
receive_pred_count              flat to ~110     flat 107 -> 103    OK     X

direction 4/5   magnitude 1/5
```

headline_f1 0.399 -> 0.380   (-0.018)
n_pred 488 -> 596   missed 233 -> 191   invented 171 -> 237
pipeline: $1.61, 0 cached, 0 failed

## VERDICT
Right about the mechanism for set recall, wrong about serve precision. The numbers show that reverting to standard, broad definitions for `set` and `dig` successfully recovered `set_recall` (jumping from 0.213 to 0.383). However, it also caused total predictions to surge (488 to 596) and `invented` events to spike (171 to 237). 

The attempt to suppress false serves using conditional prompt logic ("DO NOT guess a 'serve'... if the ball is already in play") was a complete failure. `serve_precision` moved in the opposite direction of my prediction, dropping from 0.547 to 0.508. This tells us the model cannot reliably judge the historical state of the rally at the exact boundary of an isolated video chunk. It ended up misclassifying or ignoring legitimate serves without actually solving the phantom mid-rally serve problem. Because the massive influx of false positives dwarfed the minor gain in true positives (+11), the overall F1 score degraded.

This change made things worse because we relied on fragile, LLM-interpreted edge-case rules to patch structural context problems. The right move is to abandon this line of conditional prompt engineering, roll back to a cleaner configuration, and attack the actual structural bottlenecks: chunk duration and crop geometry.
