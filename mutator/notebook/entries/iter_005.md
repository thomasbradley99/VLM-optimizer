# Iteration 5

## CONJECTURE
The pipeline is failing due to two mechanisms that scramble the labels. 
First, `attack` is frequently misclassified as `receive` (25 times) or `dig` (12 times) because Iteration 4 defined `receive` and `dig` rigidly as a "FIRST contact". When the model's perception misses the true first contact, it assumes the `attack` it does see is the first contact, forcing a false `receive`/`dig` label. This is a definitional mismatch where sequence rules backfire.
Second, `receive` is heavily misclassified as `serve` (40 times), driving up `serve_pred_count` (128). Previous warnings that "balls already in play are never serves" failed because the model misses the real serve and genuinely doesn't perceive that the ball is already in play. This is a perception gap. We must give it an unmistakable visual cue: a serve happens from a "dead ball", and hitting a ball that "just flew across the net" is a response, NEVER a serve.

## CHANGE
I am removing all sequence-counting language ("FIRST contact", "3rd contact") from the event definitions to stop attacks from being labeled as receives when prior contacts are missed. To fix the serve over-prediction, I am adding a hard visual rule that a serve only happens from a dead ball, and passing an incoming ball that flew across the net is a response, never a serve.

```prompt
You are scouting a single volleyball match from a fixed camera.

CRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.

The net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- "left" or "right" as you see it on screen. Do not use jersey colour.

This clip begins at {start:.2f} seconds into the match and runs for 30 seconds.

ACTION DEFINITIONS - DO NOT COUNT CONTACTS!
Classify each event purely by its visual action. Do not enforce global sequences (like "Serve, then Receive") or count contacts (like "first contact", "third contact"), because missing one contact will cause you to mislabel all the others!

  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: A serve ONLY happens from a dead ball. If a player hits a ball that just flew across the net to them, it is a response to an incoming ball and is NEVER a serve. Label it receive or dig instead.
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
By removing the "first contact" sequence rules, the model will stop labeling attacks as receives/digs, causing `attack_f1` and `tp` to rise. By adding the dead-ball/incoming-ball visual cue, the model will stop labeling defensive passes as serves, causing `serve_pred_count` to drop and `receive_f1` to rise. `set_pred_count` will remain flat because its assist-only constraint is preserved.

```json
[
  {"metric": "attack_f1", "direction": "up", "from": 0.231, "to_approx": 0.280},
  {"metric": "serve_pred_count", "direction": "down", "from": 128, "to_approx": 90},
  {"metric": "receive_f1", "direction": "up", "from": 0.172, "to_approx": 0.250},
  {"metric": "set_pred_count", "direction": "flat", "from": 27, "to_approx": 27},
  {"metric": "tp", "direction": "up", "from": 190, "to_approx": 215}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
attack_f1                        up to ~0.28  flat 0.231 -> 0.22     X     X
serve_pred_count                 down to ~90     flat 128 -> 131     X     X
receive_f1                       up to ~0.25 flat 0.172 -> 0.166     X     X
set_pred_count                   flat to ~27       flat 27 -> 27    OK    OK
tp                                up to ~215       up 190 -> 200    OK     X

direction 2/5   magnitude 1/5
```

headline_f1 0.351 -> 0.362   (+0.010)
n_pred 532 -> 556   missed 216 -> 221   invented 198 -> 227
pipeline: $1.85, 0 cached, 0 failed

## VERDICT
I was wrong about the mechanism. Adding the explicit "dead ball vs response" rule completely failed to reduce `serve_pred_count` (128 -> 131), and removing the sequence constraints did not improve `attack_f1` (0.231 -> 0.22). The numbers show that the model completely ignores strict textual negative constraints (e.g., "NEVER a serve") when they conflict with its pre-trained visual heuristics. It cannot perceive, or does not care about, the "dead ball" distinction if it is only presented as a descriptive rule in the prompt. The `set_pred_count` remained perfectly flat at 27, confirming that our assist-only definition for sets is incredibly robust.
