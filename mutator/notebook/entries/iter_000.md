# Iteration 0

## CONJECTURE
The model is failing due to two distinct mechanisms working together to scramble the labels:

1. **Definitional (Set over-prediction):** The scout only recorded sets that lead to a kill (`assist-2`, 47 real sets vs 52 kills). However, the prompt instructed the model to label "the second contact" as a set, causing a massive over-prediction (144 predicted). Because the real regular sets are missing from the ground truth, these extra predicted sets greedily match adjacent real events in the timestamp window, absorbing 34 real `attack`s and 16 `dig`s. 
2. **Perception/Sequence (Off-by-one labeling):** The model often misses the serve entirely (likely because the server is at the extreme edge of the frame or blending into the background matches). Because the original definitions rely heavily on sequence logic ("puts ball in play", "first contact", "second contact"), the model applies a rigid sequence to the contacts it *does* see. It falsely labels the first visible contact (the real receive) as `serve` (39 times!), and cascades this shift to call real sets `receive`, real attacks `set` (34 times), and real digs `attack` (19 times).

## CHANGE
Redefine `set` to strictly mean an assist (only reporting it if it leads to a kill) to match the scout's protocol, and rewrite the event definitions to use visual descriptions rather than sequence counters ("first", "second") to prevent a missed serve from causing an off-by-one labeling cascade.

```prompt
You are scouting a single volleyball match from a fixed camera.

CRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.

The net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- "left" or "right" as you see it on screen. Do not use jersey colour.

This clip begins at {start:.2f} seconds into the match and runs for 30 seconds.

Report the contacts a player makes with the ball, in order, ONLY if they match these specific types:
  serve   - a hit from behind the court's end line to start a rally. Look closely at the far edges; do not mistake a pass inside the court for a serve.
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
By matching the scout's `set` definition, `set_pred_count` will plummet to match the actual kills, reducing the hallucinated events that cannibalize attacks. By removing sequence constraints, a missed serve will result in a skipped serve rather than falsely labeling the receive as a serve, causing `serve_pred_count` to drop and `receive_f1` to rise. Blocks are largely unaffected by these sequence issues and will remain flat.

```json
[
  {"metric": "set_pred_count", "direction": "down", "from": 144, "to_approx": 50},
  {"metric": "serve_pred_count", "direction": "down", "from": 130, "to_approx": 85},
  {"metric": "receive_f1", "direction": "up", "from": 0.174, "to_approx": 0.350},
  {"metric": "attack_f1", "direction": "up", "from": 0.189, "to_approx": 0.400},
  {"metric": "block_f1", "direction": "flat", "from": 0.095, "to_approx": 0.095}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
set_pred_count                   down to ~50      down 144 -> 27    OK    OK
serve_pred_count                 down to ~85     down 130 -> 123    OK     X
receive_f1                       up to ~0.35 down 0.174 -> 0.147     X     X
attack_f1                         up to ~0.4   up 0.189 -> 0.227    OK     X
block_f1                      flat to ~0.095  up 0.0952 -> 0.138     X     X

direction 3/5   magnitude 1/5
```

headline_f1 0.342 -> 0.345   (+0.002)
n_pred 630 -> 553   missed 192 -> 227   invented 272 -> 230
pipeline: $1.89, 0 cached, 0 failed

## VERDICT
I was right about the mechanism for the `set` over-prediction, but wrong about the sequence fix for serves and receives. 

The prompt successfully slashed `set` predictions (from 144 down to 27) by narrowing the definition to assists. This removed a massive source of hallucinated events and slightly boosted `attack_f1` (0.189 -> 0.227) as they stopped cannibalizing real attacks in the matching window. However, the attempt to stop off-by-one errors by removing sequence language ("first", "second" contact) failed. `serve_pred_count` barely dropped (130 -> 123), and `receive_f1` actually worsened (0.174 -> 0.147). The model is still drastically over-predicting serves and missing receives, indicating it's not a sequence-enforcement issue, but a fundamental visual misclassification where it actively sees receives and thinks they are serves.
