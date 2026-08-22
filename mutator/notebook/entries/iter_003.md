# Iteration 3

## CONJECTURE
The persistent confusion between `serve` and `receive` (35 real receives labeled as serves) and `attack` vs `receive`/`dig` (40 real attacks labeled as receives/digs) is a perception failure. The model is functionally blind to spatial positioning (court lines) and fine player kinematics (tosses, bumps) which we tried in previous iterations. However, it should be able to perceive macro-level ball trajectories. By redefining the events based on the most salient visual outcome—whether the ball flies "OVER THE NET" (serve, attack, kill) or "STAYS ON THE SAME SIDE" (receive, dig)—we give the model a strong visual cue it can actually track to break these misclassifications.

## CHANGE
I am redefining the action types to rely primarily on ball trajectory (explicitly stating whether the ball travels "OVER THE NET" or "STAYS ON THE SAME SIDE") rather than player poses or spatial court locations.

```prompt
You are scouting a single volleyball match from a fixed camera.

CRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.

The net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- "left" or "right" as you see it on screen. Do not use jersey colour.

This clip begins at {start:.2f} seconds into the match and runs for 30 seconds.

Report the contacts a player makes with the ball, in order, ONLY if they match these specific types:
  serve   - a hit that sends the ball OVER THE NET to the opponent's side to start a rally.
  receive - a defensive pass against a serve, where the ball pops up and STAYS ON THE SAME SIDE of the net.
  dig     - a defensive pass against an attack, where the ball pops up and STAYS ON THE SAME SIDE of the net.
  set     - a pass placing the ball for an attacker, BUT ONLY if it directly leads to a kill (an assist). Do NOT report regular sets that do not lead to a kill.
  attack  - an offensive hit that sends the ball OVER THE NET to the opponent's side, but does not immediately win the rally.
  kill    - an offensive hit that sends the ball OVER THE NET to the opponent's side, and immediately wins the rally.
  block   - a contact made at the net by a player with hands above it.

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
By leveraging ball trajectory, the model will stop labeling same-side defensive passes as serves, causing `serve_pred_count` to drop and freeing up real receives, increasing `receive_f1`. It will also stop labeling over-the-net attacks as receives or digs, causing `attack_f1` and overall `tp` to rise. `set_pred_count` will remain flat as its definition is unchanged.

```json
[
  {"metric": "serve_pred_count", "direction": "down", "from": 126, "to_approx": 90},
  {"metric": "receive_f1", "direction": "up", "from": 0.178, "to_approx": 0.250},
  {"metric": "attack_f1", "direction": "up", "from": 0.232, "to_approx": 0.280},
  {"metric": "tp", "direction": "up", "from": 186, "to_approx": 210},
  {"metric": "set_pred_count", "direction": "flat", "from": 32, "to_approx": 32}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                 down to ~90     flat 126 -> 120     X     X
receive_f1                       up to ~0.25 down 0.178 -> 0.142     X     X
attack_f1                        up to ~0.28 flat 0.232 -> 0.236     X     X
tp                                up to ~210     flat 186 -> 184     X     X
set_pred_count                   flat to ~32       flat 32 -> 30    OK    OK

direction 1/5   magnitude 1/5
```

headline_f1 0.350 -> 0.350   (+0.000)
n_pred 512 -> 500   missed 245 -> 247   invented 207 -> 197
pipeline: $1.90, 0 cached, 0 failed

## VERDICT
I was completely wrong about the mechanism. Adding explicit ball trajectory constraints ("OVER THE NET" vs "STAYS ON THE SAME SIDE") failed to stop the model from hallucinating serves, with `serve_pred_count` barely moving (126 -> 120). Furthermore, this change actually harmed `receive_f1` (0.178 -> 0.142) instead of helping it. The numbers clearly show that the model's internal, pre-trained visual heuristic for a `serve` (likely just "any contact deep in the backcourt") is overwhelmingly strong. It simply ignores our text definitions, whether we attempt to constrain the action by logical sequence, spatial court lines, kinematic body poses, or macro ball trajectory.
