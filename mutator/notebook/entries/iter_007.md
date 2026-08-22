# Iteration 7

## CONJECTURE
The model over-predicts `serve` because it suffers from a visual bias, mistaking deep-court passes for serves. It ignores logical rules, kinematics, trajectory, and 3D court geometry. The confusion matrix shows 35 receives and 13 attacks misclassified as serves, leading to 131 `serve` predictions against 118 real. This is a perception gap. Since the camera is fixed, we can leverage 2D screen topology: serves only occur at the absolute extremes of the frame (the baselines). By anchoring the `serve` definition to the 2D video frame edges rather than 3D depth or complex visual states like a "dead ball", we provide an immediate, single-frame visual cue that the model can reliably perceive.

## CHANGE
I am changing the `serve` definition to rely purely on 2D screen topology, restricting it to the "extreme left or right edge of the video frame" and forbidding actions "further inward" from being labeled as serves.

```prompt
You are scouting a single volleyball match from a fixed camera.

CRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.

The net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- "left" or "right" as you see it on screen. Do not use jersey colour.

This clip begins at {start:.2f} seconds into the match and runs for 30 seconds.

ACTION DEFINITIONS - DO NOT COUNT CONTACTS!
Classify each event purely by its visual action. Do not enforce global sequences (like "Serve, then Receive") or count contacts (like "first contact", "third contact"), because missing one contact will cause you to mislabel all the others!

  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: Serves ONLY happen at the extreme left or right edge of the video frame. If a player hits the ball from further inward (away from the extreme edges), it is NEVER a serve. Label it receive, dig, or attack instead.
  receive - a defensive pass handling the opponent's serve.
  dig     - a defensive pass handling the opponent's attack.
  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.
  attack  - an offensive hit aimed to score by sending the ball over the net.
  kill    - an offensive hit that immediately wins the rally.
  block   - a defensive contact made AT THE NET by a player jumping with hands above it.

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
By using a simple 2D spatial constraint, the model will stop labeling inward court actions as serves. `serve_pred_count` will fall sharply. Real receives and attacks will no longer be absorbed by `serve`, causing `receive_f1` and `attack_f1` to rise. Overall `tp` will increase as these labels shift to their correct classes. `set_pred_count` will remain perfectly flat because its assist-only rule is untouched.

```json
[
  {"metric": "serve_pred_count", "direction": "down", "from": 131, "to_approx": 95},
  {"metric": "receive_f1", "direction": "up", "from": 0.166, "to_approx": 0.220},
  {"metric": "attack_f1", "direction": "up", "from": 0.220, "to_approx": 0.250},
  {"metric": "tp", "direction": "up", "from": 200, "to_approx": 225},
  {"metric": "set_pred_count", "direction": "flat", "from": 27, "to_approx": 27}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                 down to ~95     flat 131 -> 125     X     X
receive_f1                       up to ~0.22 flat 0.166 -> 0.147     X     X
attack_f1                        up to ~0.25  flat 0.22 -> 0.221     X     X
tp                                up to ~225     down 200 -> 181     X     X
set_pred_count                   flat to ~27       flat 27 -> 25    OK    OK

direction 1/5   magnitude 1/5
```

headline_f1 0.362 -> 0.340   (-0.022)
n_pred 556 -> 515   missed 221 -> 235   invented 227 -> 200
pipeline: $1.87, 0 cached, 0 failed

## VERDICT
Wrong. The spatial 2D framing constraint completely failed. `serve_pred_count` barely moved (131 -> 125), while `receive_f1` dropped (0.166 -> 0.147) and overall True Positives fell sharply from 200 to 181. The numbers show that the model cannot reliably map the concept of the "extreme edge of the video frame" to the action to act as a negative filter. Instead of correctly shifting inward actions from `serve` to `receive` or `attack`, the strict negative veto ("NEVER a serve") just made the model more conservative, causing it to drop real events entirely. Visual proxy constraints continue to hurt overall recall without fixing the fundamental misclassification bias.
