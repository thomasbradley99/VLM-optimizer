# Iteration 7

## CONJECTURE
The model is suffering from a massive DEFINITIONAL mismatch, predicting 871 events against 550 ground truth, generating 436 ghosts. The core issue is that the scout's rules are far stricter than standard volleyball definitions, particularly for `set`, `serve`, and `kill`:
1. `set`: The model predicts 192 sets, but the scout only recorded 47. Section 4 reveals a 100% consistent rule: the scout *only* records a set if it immediately leads to a kill. For normal attacks, the set is completely ignored. This accounts for ~120 in-rally ghosts.
2. `serve` and `receive`: The model predicts serves mid-rally (e.g., mistaking back-row attacks for serves) and during dead-time practice tosses (53 dead-time ghosts). 
3. `kill`: Real kills are missed because the model frequently labels them as a `dig` (9 times) by reporting the defender's failed touch instead of the attacker's scoring hit.

Because `chunk_len=6.0` and `overlap=2.0` guarantee that a 2.0-second sequence (like set -> kill) is fully enclosed in at least one chunk, we can safely instruct the model to evaluate these dependencies without changing the geometry.

## CHANGE
I am rewriting the prompt's type definitions to surgically align with the scout's strict constraints: enforcing exactly one serve/receive per rally, restricting `set` entirely to those that immediately precede a `kill`, and instructing the model to report scoring hits as `kill` rather than the defender's failed `dig`.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\nNote: Clips are short and often start in the middle of an ongoing rally. If the ball is already in play when the clip begins, DO NOT guess a 'serve' or 'receive' for that rally.\n\nList ball contacts you see DURING LIVE PLAY ONLY. Ignore all dead-time contacts (e.g., players celebrating, passing the ball back, or warming up between rallies).\n\nRules for types:\n- serve: One team tosses the ball and hits it over the net from out of bounds behind the baseline to start a point. A rally has exactly ONE serve. Never report a serve if the ball is already in play, and ignore practice tosses.\n- receive: The opposing team's first contact passing the serve. Usually a forearm pass inside the court. A rally has exactly ONE receive. Do not report receives mid-rally.\n- dig: A defensive pass saving an opponent's attack.\n- set: An overhead pass setting up an attack. DEFINITIONAL RULE: The scout only records sets that lead to a kill. ONLY report a 'set' if the VERY NEXT contact is a 'kill'. If it leads to a normal 'attack' or 'dig', DO NOT report the set.\n- attack: An offensive hit directing the ball across the net.\n- kill: An attack that immediately scores a point. Report the attacker's hit as a 'kill'. Do not report the defender's failed touch as a 'dig'.\n- block: A defensive jump at the net intercepting an opponent's attack.\n\nFor each contact give:\n  t       - time of contact in absolute match seconds\n  type    - serve, receive, dig, set, attack, kill or block\n  side    - \"left\" or \"right\": which half of the frame the player is in\n  number  - jersey number as a string, or null\n  error   - true if the contact was a mistake\n  point   - true if the rally ended here",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By matching the scout's strict conditions for recording a set, `set` predictions will plummet, directly removing roughly a hundred false positives. Adding constraints to serve and receive will further strip out dead-time and mid-rally hallucinations. Because these were never real events in the ground truth, `n_pred` will drop dramatically while `tp` remains mostly flat (losing some sets we were catching, but perhaps gaining a few kills), yielding a massive boost to headline F1.

```predictions
[{"metric": "set_pred_count", "direction": "down", "from": 192, "to_approx": 70},
 {"metric": "serve_pred_count", "direction": "down", "from": 174, "to_approx": 120},
 {"metric": "n_pred", "direction": "down", "from": 871, "to_approx": 680},
 {"metric": "tp", "direction": "flat", "from": 289, "to_approx": 280},
 {"metric": "headline_f1", "direction": "up", "from": 0.407, "to_approx": 0.445}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                   down to ~70      down 192 -> 53    OK    OK
serve_pred_count                down to ~120     flat 174 -> 180     X     X
n_pred                          down to ~680     down 871 -> 743    OK    OK
tp                              flat to ~280     flat 289 -> 292    OK    OK
headline_f1                     up to ~0.445   up 0.407 -> 0.452    OK    OK

direction 4/5   magnitude 4/5
```

headline_f1 0.407 -> 0.452   (+0.045)
n_pred 871 -> 743   missed 115 -> 131   invented 436 -> 324
pipeline: $2.89, 0 cached, 0 failed

## VERDICT
Right about the mechanism for `set` and the overall F1 boost, but wrong about the mechanism for `serve`. 

The strict instruction to only report a `set` if it immediately precedes a `kill` worked flawlessly. Because a set and a kill occur within ~1-2 seconds of each other, they easily fit inside a 6.0-second chunk. The model followed this local rule perfectly, surgically removing ~139 false positive sets, dropping total `invented` ghosts from 436 to 324, and pushing F1 to 0.452 without sacrificing True Positives.

However, `serve_pred_count` did not drop; it actually rose slightly (174 -> 180). This proves that clip-level conditional logic ("DO NOT guess a 'serve' if the ball is already in play") and rally-wide constraints ("exactly ONE serve") completely fail when `chunk_len=6.0`. The model simply lacks the temporal field of view in a 6-second window to know whether a rally is already ongoing, or if a toss is just a dead-time warmup. To the model, a 6s clip of practice looks exactly like a real serve. 

The right move is to keep these highly effective prompt definitions, but push the temporal window slightly wider (e.g., 10.0s chunks) so the model has the context required to identify dead time and suppress the remaining false serves.
