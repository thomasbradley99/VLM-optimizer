# Iteration 2

## CONJECTURE
The model is suffering from a massive definitional mismatch regarding the "set" action. The current prompt instructs the model to "ONLY report a 'set' if the subsequent attack results in a 'kill'", whereas the ground truth definition assigns a set to any assist-2, regardless of the rally's outcome. Because of this artificial constraint, the model only reported 40 sets against 47 real ones, achieving a dismal recall of 0.255 (identifying just 12 real sets as sets). Furthermore, similar overly strict constraints exist on other types like "dig" (ignoring freeballs) and "receive". By stripping away these confusing outcome-dependent instructions and providing standard volleyball definitions, the model will accurately classify these intermediate touches, boosting true positives.

## CHANGE
I am rewriting the definitions block in the prompt to match standard, outcome-independent volleyball terminology (e.g., removing the rule that sets must result in a kill), which aligns with how the ground truth was derived.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\n\nList ball contacts you see DURING LIVE PLAY ONLY. Ignore all dead-time contacts (e.g., players bouncing or passing the ball between rallies).\n\nRules for types:\n- serve: The hit from behind the baseline that starts a rally.\n- receive: The first contact returning a serve.\n- dig: A defensive pass saving an opponent's attack.\n- set: An overhead pass setting up an attack.\n- attack: An offensive hit directing the ball across the net.\n- kill: An attack that immediately scores a point.\n- block: A defensive play at the net.\n\nFor each contact give:\n  t       - time of contact in absolute match seconds\n  type    - serve, receive, dig, set, attack, kill or block\n  side    - \"left\" or \"right\": which half of the frame the player is in\n  number  - jersey number as a string, or null\n  error   - true if the contact was a mistake\n  point   - true if the rally ended here",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By defining a set simply as an overhead pass setting up an attack (rather than predicting outcomes), the model will identify significantly more sets. True positives will rise as we stop actively instructing the model to ignore real contacts. Serve metrics should remain essentially unchanged as its definition was not meaningfully modified.

```predictions
[{"metric": "set_pred_count", "direction": "up", "from": 40, "to_approx": 70},
 {"metric": "set_recall", "direction": "up", "from": 0.255, "to_approx": 0.450},
 {"metric": "tp", "direction": "up", "from": 250, "to_approx": 275},
 {"metric": "serve_f1", "direction": "flat", "from": 0.379, "to_approx": 0.379}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                     up to ~70        up 40 -> 172    OK     X
set_recall                       up to ~0.45   up 0.298 -> 0.596    OK     X
tp                                up to ~275       up 250 -> 280    OK    OK
serve_f1                      flat to ~0.379  flat 0.447 -> 0.44    OK     X

direction 4/4   magnitude 1/4
```

headline_f1 0.414 -> 0.405   (-0.009)
n_pred 657 -> 833   missed 179 -> 126   invented 286 -> 409
pipeline: $2.75, 0 cached, 0 failed

## VERDICT
I was right about the mechanism, but completely wrong about the ground truth. The removal of the outcome-dependent constraints caused the model to stop suppressing events—which is exactly what I predicted—but the numbers reveal that those strict rules were actually correct. 

By defining a set simply as an "overhead pass," the model predicted 172 sets. Since the ground truth only contains 47 sets, our false positives exploded, driving `invented` events up by 123 (from 286 to 409) and dropping the headline F1 score to 0.405. This tells us unequivocally that the ground truth follows official volleyball stat rules: a "set" is an *assist*, meaning it is only recorded if the subsequent attack scores a kill. 

The previous configuration was right to include the strict rules, but wrong to expect the model to evaluate them accurately within a tiny 6.0-second chunk. When the model can't see the kill at the end of a 10-second rally, it conservatively drops the set. 

This change made things worse because it sacrificed precision for recall by misunderstanding the labeling schema. The right move is to revert to the strict definitions from Iteration 0, but pair them with a much larger `chunk_len` (e.g., 15.0 seconds) so the model has the temporal context to actually see the outcomes of the plays it is evaluating.
