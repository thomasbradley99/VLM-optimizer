# Iteration 2

## CONJECTURE
The model's failure to distinguish `serve` from `receive` is a visual perception issue; spatial constraints (like "behind the end line" or "inside the court") failed because the model struggles to parse depth and court boundaries. The confusion matrix shows 34 real `receive`s and 10 real `attack`s misclassified as `serve`. By redefining these events using kinematics (body movements) rather than spatial position—specifically requiring that a serve involves the player "tossing the ball into the air themselves," while describing a receive/dig as "typically an underhand forearm bump"—the model will have reliable human-pose cues to differentiate a serve from a reactive defensive pass.

## CHANGE
I am replacing the spatial definitions of `serve`, `receive`, and `dig` with kinematic ones, requiring a `serve` to have a self-toss and overhead strike, while labeling defensive passes as underhand forearm bumps.

```prompt
You are scouting a single volleyball match from a fixed camera.

CRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.

The net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- "left" or "right" as you see it on screen. Do not use jersey colour.

This clip begins at {start:.2f} seconds into the match and runs for 30 seconds.

Report the contacts a player makes with the ball, in order, ONLY if they match these specific types:
  serve   - an overhead strike where the player first tosses the ball into the air themselves.
  receive - a reactive defensive pass (typically an underhand forearm bump) defending against the opponent's serve.
  dig     - a reactive defensive pass (typically an underhand forearm bump) defending against the opponent's attack.
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
By relying on the distinct visual of a ball toss, the model will stop labeling deep-court bumps as serves. `serve_pred_count` will fall sharply, reducing the hallucinated serves and freeing up the real receives it was absorbing, which will cause `receive_f1` to increase. Since we did not touch the definitions of `attack` or `set`, their performance will remain steady.

```json
[
  {"metric": "serve_pred_count", "direction": "down", "from": 126, "to_approx": 80},
  {"metric": "receive_f1", "direction": "up", "from": 0.121, "to_approx": 0.250},
  {"metric": "set_pred_count", "direction": "flat", "from": 26, "to_approx": 26},
  {"metric": "attack_f1", "direction": "flat", "from": 0.228, "to_approx": 0.228}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                 down to ~80     flat 123 -> 126     X     X
receive_f1                       up to ~0.25   up 0.147 -> 0.178    OK     X
set_pred_count                   flat to ~26         up 27 -> 32     X     X
attack_f1                     flat to ~0.228 flat 0.227 -> 0.232    OK    OK

direction 2/4   magnitude 1/4
```

headline_f1 0.345 -> 0.350   (+0.006)
n_pred 553 -> 512   missed 227 -> 245   invented 230 -> 207
pipeline: $1.90, 0 cached, 0 failed

## VERDICT
Wrong about the mechanism. The assumption that the model could use fine-grained kinematic features (like a "self-toss" before a strike) to veto bad serves completely failed; `serve_pred_count` remained stubbornly flat at 126 rather than dropping to the predicted ~80. The model simply cannot perceive or apply human-pose mechanics reliably enough at this resolution to filter out false serves. `receive_f1` did increase slightly (0.147 to 0.178), likely because the "underhand forearm bump" phrasing provided a recognizable positive cue for a few genuine receives, but it did not solve the core serve-bleeding issue. The drop in total invented predictions (230 down to 207) indicates the prompt changes tightened up the model's overall trigger-happiness, but `serve` remains fundamentally broken.
