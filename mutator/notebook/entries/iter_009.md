# Iteration 9

## CONJECTURE
The model over-predicts `serve` (133 vs 118 real), absorbing 33 receives and 12 attacks, because the current prompt actively forbids sequence logic ("Classify each event purely by its visual action. Do not enforce global sequences"). Volleyball event classes are fundamentally defined by their structural context—a receive handles a serve, a dig handles an attack. By stripping away this natural sequence logic, we force the model to rely on ambiguous visual forms (such as back-court passes) and blind it to the only logical way to distinguish them. This is a definitional mismatch. Our anti-sequence instruction actively prevents the model from using the rally's flow. We must replace the anti-sequence instructions with explicit encouragement to use local transitions (structural flow) to classify actions.

## CHANGE
I am removing the anti-sequence vetoes and the ineffective "dead ball" visual rule, replacing them with explicit instructions to use structural flow (e.g., classifying a pass as a receive if it handles a serve, or a dig if it handles an attack) to disambiguate visually similar actions.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start:.2f} seconds into the match and runs for 30 seconds.\n\nACTION DEFINITIONS\nVolleyball events are defined by their structural flow in the rally. Use the sequence of actions to distinguish visually similar moves. For example, a hit from the back is a 'serve' if it starts the rally, but an 'attack' if it happens mid-rally. A defensive pass is a 'receive' if it handles a serve, but a 'dig' if it handles an attack.\n\n  serve   - the hit that starts a rally.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start:.2f}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true if the rally ended on this contact and a point was scored\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 30.0,
 "overlap": 8.0,
 "fps": 5,
 "width": 640,
 "crop": null,
 "media_resolution": null,
 "model": "gemini-3.7-flash",
 "thinking": "low"}
```

## PREDICTION
By encouraging the model to track the flow of the rally, it will realize that actions immediately following a serve are receives, and mid-rally back-court hits are attacks. `serve_pred_count` will fall as it stops absorbing these events. `receive_f1` and `attack_f1` will rise. True positives (`tp`) will increase as actions are correctly classified based on context rather than purely ambiguous visual form. `set_pred_count` will remain flat because the strict assist-only constraint limits its usage regardless of structural flow.

```predictions
[
  {"metric": "serve_pred_count", "direction": "down", "from": 133, "to_approx": 105},
  {"metric": "receive_f1", "direction": "up", "from": 0.196, "to_approx": 0.250},
  {"metric": "attack_f1", "direction": "up", "from": 0.211, "to_approx": 0.260},
  {"metric": "tp", "direction": "up", "from": 191, "to_approx": 220},
  {"metric": "set_pred_count", "direction": "flat", "from": 23, "to_approx": 23}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                down to ~105     down 133 -> 126    OK     X
receive_f1                       up to ~0.25 down 0.196 -> 0.124     X     X
attack_f1                        up to ~0.26  flat 0.211 -> 0.21     X     X
tp                                up to ~220     down 191 -> 165     X     X
set_pred_count                   flat to ~23       down 23 -> 19     X     X

direction 1/5   magnitude 0/5
```

headline_f1 0.349 -> 0.319   (-0.029)
n_pred 545 -> 483   missed 229 -> 257   invented 224 -> 190
pipeline: $1.91, 0 cached, 0 failed

## VERDICT
I was wrong. Re-introducing sequence logic and structural flow did not help the model disambiguate actions; instead, it caused a severe drop in `receive_f1` (0.196 down to 0.124) and overall recall (TPs dropped from 191 to 165). 

The numbers show a classic cascade failure. By telling the model that a receive is defined as "handling the opponent's serve," we inadvertently created a hard logical dependency. Because the model's baseline recall is imperfect, if it visually misses the serve (the antecedent), it is now logically blocked from predicting the receive (the consequent). This proves why the original anti-sequence veto was in place: enforcing sequence rules on a low-FPS, low-recall vision model actively suppresses valid downstream predictions. The minor drop in `serve_pred_count` (133 to 126) was nowhere near the prediction and not worth the massive damage to overall F1 (0.349 to 0.319).
