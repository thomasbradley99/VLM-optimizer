# Iteration 4

## CONJECTURE
The model is suffering from a massive definitional mismatch for `set`, `receive`, and `serve`, generating 134 in-rally phantoms across these three classes. `set` is predicted 125 times against 47 real; the confusion matrix shows it absorbing 32 real attacks and 15 real digs. This happens because the scout likely only marked point-scoring assists, while the model flags any setup pass. Furthermore, the model predicts multiple serves and receives per rally (35 and 34 in-rally phantoms, respectively) and misclassifies 26 real attacks as receives. This is a definitional error, combined with a perception issue at clip boundaries where mid-rally contacts are mistaken for serves. Because we are currently using 15-second chunks, the model has enough temporal context to follow strict, rally-level rules to eliminate these false positives.

## CHANGE
I am rewriting the prompt definitions to enforce exactly one serve/receive per rally, explicitly instruct the model to ignore serves if the clip starts mid-rally, and strictly limit `set` to kill-assists.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\n\nList ball contacts you see DURING LIVE PLAY ONLY. Ignore all dead-time contacts (e.g., players bouncing or passing the ball between rallies).\n\nRules for types:\n- serve: The hit from behind the baseline that starts a rally. A rally has exactly ONE serve. If the clip starts with the ball already in play, DO NOT report a serve.\n- receive: ONLY the single first contact returning a serve. Never report multiple receives in one rally.\n- dig: A defensive pass saving an opponent's attack. (Do not report easy freeball passes).\n- set: ONLY report a 'set' if the subsequent attack results in a 'kill'. If it leads to a normal 'attack', DO NOT report the set.\n- attack: An offensive hit directing the ball across the net.\n- kill: An offensive hit that immediately scores a point (hits the opponent's floor or is unplayable).\n- block: A defensive play at the net.\n\nFor each contact give:\n  t       - time of contact in absolute match seconds\n  type    - serve, receive, dig, set, attack, kill or block\n  side    - \"left\" or \"right\": which half of the frame the player is in\n  number  - jersey number as a string, or null\n  error   - true if the contact was a mistake\n  point   - true if the rally ended here",
 "chunk_len": 15.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
Enforcing strict definitional constraints will drastically cut the number of phantom predictions for `set`, `receive`, and `serve`, dropping the overall `n_pred` and naturally raising F1. Because misclassified real attacks (which were previously absorbed by `set` and `receive`) will now be correctly forced into the `attack` category, we should see `attack_recall` and overall True Positives (`tp`) increase.

```predictions
[{"metric": "set_pred_count", "direction": "down", "from": 125, "to_approx": 65},
 {"metric": "receive_pred_count", "direction": "down", "from": 112, "to_approx": 85},
 {"metric": "attack_recall", "direction": "up", "from": 0.145, "to_approx": 0.250},
 {"metric": "n_pred", "direction": "down", "from": 618, "to_approx": 500},
 {"metric": "tp", "direction": "up", "from": 235, "to_approx": 255},
 {"metric": "block_f1", "direction": "flat", "from": 0.231, "to_approx": 0.231}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                   down to ~65      down 125 -> 36    OK    OK
receive_pred_count               down to ~85     flat 112 -> 107     X     X
attack_recall                    up to ~0.25 down 0.412 -> 0.321     X    OK
n_pred                          down to ~500     down 618 -> 488    OK    OK
tp                                up to ~255     down 235 -> 207     X     X
block_f1                      flat to ~0.231  down 0.308 -> 0.25     X    OK

direction 2/6   magnitude 4/6
```

headline_f1 0.402 -> 0.399   (-0.004)
n_pred 618 -> 488   missed 177 -> 233   invented 245 -> 171
pipeline: $1.55, 0 cached, 0 failed

## VERDICT
Wrong about the mechanism. Initial logic regarding the reduction of phantom predictions held true, as `invented` events dropped from 245 to 171 and overall `n_pred` fell precisely to target. However, the anticipated reclassification leap failed. Instead of shifting misclassified setups and receives into the `attack` category, the strict prompt constraints caused the model to indiscriminately discard intermediate contacts. This drove `missed` events from 177 up to 233 and bled 28 true positives, dropping `attack_recall` sharply. The rigid rally logic forces silence rather than accuracy. The right move is to abandon this hyper-strict prompt configuration, roll back to standard definitions, and solve the recall bottleneck through geometric and temporal adjustments instead.
