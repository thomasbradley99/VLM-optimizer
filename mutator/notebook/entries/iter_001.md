# Iteration 1

## CONJECTURE
The model over-predicts `serve` and cannibalizes `receive` because it relies on a false prior that every video clip must begin with a serve. When a 30-second clip starts mid-rally, the model takes the very first contact it sees—often a defensive pass made well inside the court—and forces a `serve` label onto it. This is a perception/prior failure: the model's visual perception of a player passing from inside the court is being overridden by its assumption that the first event must be the start of a rally. This is supported by the confusion matrix, which shows 34 real `receive`s and 10 real `attack`s being misclassified as `serve`s, contributing to a massive over-prediction of serves (123 predicted vs. 118 real, with 72 real serves missed entirely).

## CHANGE
I am explicitly warning the model that clips often start mid-rally (so the first contact is often not a serve) and reinforcing the negative constraint that passes made from inside the court lines are NEVER serves. 

```prompt
You are scouting a single volleyball match from a fixed camera.

CRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.

The net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- "left" or "right" as you see it on screen. Do not use jersey colour.

This clip begins at {start:.2f} seconds into the match and runs for 30 seconds. Clips often start mid-rally, so do NOT assume the first contact you see is a serve.

Report the contacts a player makes with the ball, in order, ONLY if they match these specific types:
  serve   - a hit from behind the court's end line to start a rally. Because clips may start mid-play, the first contact is often NOT a serve. Passes made from inside the court lines are NEVER serves.
  receive - a defensive pass defending against the opponent's serve
  dig     - a defensive pass defending against the opponent's attack
  set     - a pass placing the ball for an attacker, BUT ONLY if it directly leads to a kill (an assist). Do NOT report regular sets that do not lead to a kill.
  attack  - an offensive hit over the net that does NOT immediately win the rally
  kill    - an offensive hit over the net that immediately wins the rally
  block   - a contact made at the net by a player with hands above it

For each contact give:
  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start:.2f}. Be precise to a fraction of a second.
  type    - one of the seven above
  side    - "left" or "right": which half of the frame the contacting player is standing in
  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.
  error   - true if this contact was an error (into the net, out of bounds, mishandled)
  point   - true if the rally ended on this contact and a point was scored

Report only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.
```

## PREDICTION
By destroying the false assumption that clips start with a serve, `serve_pred_count` will drop sharply as it stops labeling first-contact passes as serves. The 34 real `receive`s previously misclassified as serves will now be correctly labeled, causing `receive_f1` to rise. Because we have not changed the definition of `attack`, its F1 score will remain roughly flat, leaving its own confusion with `receive`/`dig` (free balls) untouched for now.

```json
[
  {"metric": "serve_pred_count", "direction": "down", "from": 123, "to_approx": 80},
  {"metric": "receive_f1", "direction": "up", "from": 0.147, "to_approx": 0.250},
  {"metric": "attack_f1", "direction": "flat", "from": 0.227, "to_approx": 0.227},
  {"metric": "set_pred_count", "direction": "flat", "from": 27, "to_approx": 27}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                 down to ~80     flat 123 -> 126     X     X
receive_f1                       up to ~0.25 down 0.147 -> 0.121     X     X
attack_f1                     flat to ~0.227 flat 0.227 -> 0.228    OK    OK
set_pred_count                   flat to ~27       flat 27 -> 26    OK    OK

direction 2/4   magnitude 2/4
```

headline_f1 0.345 -> 0.339   (-0.006)
n_pred 553 -> 507   missed 227 -> 246   invented 230 -> 203
pipeline: $1.86, 0 cached, 0 failed

## VERDICT
I was completely wrong. The explicit instruction that clips start mid-rally and the hard constraint that "passes inside the court are NEVER serves" completely failed to reduce `serve_pred_count`, which stayed flat (actually rising from 123 to 126). It also actively harmed `receive` performance, driving `receive_f1` down from 0.147 to 0.121. 

The numbers show that the model's over-prediction of serves is not driven by a logical assumption about the start of the video. It is a fundamental visual perception failure: the model genuinely cannot distinguish a serve from a deep-court pass based on spatial rules alone. It likely struggles to accurately perceive the court lines or depth perspective. Adding complex logic caveats about clip boundaries just made the model more hesitant overall (total predictions dropped 553 -> 507), causing it to miss more real receives while continuing to hallucinate serves at the same rate. This change made things worse and the logical caveats should be rolled back in favor of a different approach.
