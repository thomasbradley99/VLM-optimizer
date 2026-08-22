# Iteration 0

## CONJECTURE
The model is dramatically over-predicting events (1080 predicted vs 550 real), resulting in 609 ghost events. This is largely a definitional mismatch rather than a perception failure. 

First, the ground truth strongly implies the scout only logged a "set" when it resulted in a point (there are exactly 47 sets against 52 kills, but 131 attacks). Because the prompt broadly asks for "every ball contact", the model predicts 239 sets, causing 145 ghosts inside live rallies and actively stealing matches from real attacks and receives (as seen in the confusion matrix where 31 real attacks were mislabelled as sets).

Second, the model is reporting contacts during dead time between rallies (e.g., players bouncing the ball before a serve), generating 183 dead-time ghosts, including 109 false serves.

## CHANGE
I am rewriting the prompt to fix these definitional gaps by strictly limiting "set" to assists that lead to a "kill", restricting "receive" to serve returns, and explicitly forbidding the reporting of dead-time contacts.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\n\nList ball contacts you see DURING LIVE PLAY ONLY. Ignore all dead-time contacts (e.g., players bouncing or passing the ball between rallies).\n\nRules for types:\n- serve: The hit from behind the baseline that starts a rally.\n- receive: ONLY the first contact returning a serve.\n- dig: A defensive pass saving an opponent's attack. (Do not report easy freeball passes).\n- set: ONLY report a 'set' if the subsequent attack results in a 'kill'. If it leads to a normal 'attack' or an error, DO NOT report the set.\n- attack: An offensive hit. If it goes out or into the net, set error=true.\n- kill: An offensive hit that immediately scores a point (hits the opponent's floor or is unplayable).\n- block: A defensive block at the net.\n\nFor each contact give:\n  t       - time of contact in absolute match seconds\n  type    - serve, receive, dig, set, attack, kill or block\n  side    - \"left\" or \"right\": which half of the frame the player is in\n  number  - jersey number as a string, or null\n  error   - true if the contact was a mistake\n  point   - true if the rally ended here",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect the total number of predicted events (`n_pred`) to plummet as dead-time ghosts and excess sets are filtered out. Consequently, `set_pred_count` will drop sharply. With the model no longer incorrectly labelling tips or mid-rally passes as "set", many of those contacts will now be correctly classified as "attack" or "dig", driving True Positives (`tp`) and `attack_recall` up. Because true serves are unaffected by the dead-time rule, `serve_recall` will remain flat even as `serve_pred_count` falls.

```predictions
[{"metric": "set_pred_count", "direction": "down", "from": 239, "to_approx": 80},
 {"metric": "n_pred", "direction": "down", "from": 1080, "to_approx": 750},
 {"metric": "tp", "direction": "up", "from": 312, "to_approx": 350},
 {"metric": "attack_recall", "direction": "up", "from": 0.344, "to_approx": 0.450},
 {"metric": "serve_recall", "direction": "flat", "from": 0.492, "to_approx": 0.492}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                   down to ~80      down 239 -> 51    OK    OK
n_pred                          down to ~750down 1.08e+03 -> 836    OK    OK
tp                                up to ~350     down 312 -> 273     X     X
attack_recall                    up to ~0.45 down 0.588 -> 0.481     X    OK
serve_recall                  flat to ~0.492    up 0.585 -> 0.61     X     X

direction 2/5   magnitude 3/5
```

headline_f1 0.383 -> 0.394   (+0.011)
n_pred 1080 -> 836   missed 81 -> 144   invented 611 -> 430
pipeline: $3.04, 0 cached, 0 failed

## VERDICT
Right about the mechanism for reducing ghost events, but completely wrong about true positives. The predictions for `set_pred_count` and `n_pred` were accurate, as explicitly banning dead-time contacts and narrowing the definition of a "set" successfully purged nearly 200 invented events. However, I expected that clearing out false sets would cause those contacts to be correctly reclassified as attacks or digs, boosting True Positives. Instead, `tp` fell from 312 to 273 and `attack_recall` dropped significantly (0.588 to 0.481). 

The numbers show that complex, outcome-dependent constraints (like "ONLY report a 'set' if the subsequent attack results in a 'kill'") cause the model to hesitate and drop real events rather than reclassify them. The model likely struggled to resolve these cross-dependencies within the 6-second chunk window, leading to a massive spike in missed events (81 to 144). The slight F1 bump (0.383 to 0.394) is a hollow victory, bought entirely by shedding false positives at the expense of recall. 

The right move is to back off the overly strict conditional logic. We should retain the general instruction to ignore dead-time play, but restore straightforward, independent definitions for the event types.
