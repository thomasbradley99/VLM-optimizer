# Iteration 6

## CONJECTURE
The model over-predicts `serve` because it suffers from a "lazy classification" reflex, relying on pre-trained visual bias (e.g., any backcourt pass looks like a serve) and ignoring our textual constraints. `serve` is predicted 131 times against 118 real, and the confusion matrix shows it absorbing 35 `receive`s and 13 `attack`s. As outlined in the notebook hypothesis, this is a perception gap compounded by an output generation flaw: the model commits to a classification before processing the visual state of the ball (dead vs incoming). Because no amount of capitalized text in the definitions alters this reflex, we must force the model to evaluate the ball's context first.

## CHANGE
I am changing the JSON schema to include an intermediate reasoning field, `ball_starting_state`, which forces the model to explicitly state whether the ball was "dead" or "in-flight" *before* it outputs the event `type`.

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
  ball_starting_state - "dead" if the ball was held by the player before striking, or "in-flight" if the ball was passed/hit to them. You MUST output this field before 'type'.
  type    - one of the seven above
  side    - "left" or "right": which half of the frame the contacting player is standing in
  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.
  error   - true if this contact was an error (into the net, out of bounds, mishandled)
  point   - true if the rally ended on this contact and a point was scored

Report only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.
```

## PREDICTION
By forcing the model to explicitly state that a ball is "in-flight" before choosing an event type, it will logically connect that context to the dead-ball rule and realize the action cannot be a serve. `serve_pred_count` will drop sharply. As real receives are no longer blindly absorbed by serve, `receive_f1` will rise. True positives (`tp`) will climb as misclassifications are resolved, while `set_pred_count` will remain perfectly flat since its assist-only constraint is completely unchanged.

```json
[
  {"metric": "serve_pred_count", "direction": "down", "from": 131, "to_approx": 90},
  {"metric": "receive_f1", "direction": "up", "from": 0.166, "to_approx": 0.250},
  {"metric": "set_pred_count", "direction": "flat", "from": 27, "to_approx": 27},
  {"metric": "tp", "direction": "up", "from": 200, "to_approx": 230}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                 down to ~90     down 131 -> 119    OK     X
receive_f1                       up to ~0.25     up 0.166 -> 0.2    OK     X
set_pred_count                   flat to ~27       down 27 -> 19     X     X
tp                                up to ~230     down 200 -> 178     X     X

direction 2/4   magnitude 0/4
```

headline_f1 0.362 -> 0.336   (-0.026)
n_pred 556 -> 510   missed 221 -> 233   invented 227 -> 193
pipeline: $1.86, 0 cached, 0 failed

## VERDICT
Right about the mechanism, wrong about the size and the severe side effects. 

The numbers show that adding the `ball_starting_state` field did shift the model's behavior in the predicted directions: `serve_pred_count` dropped (131 -> 119) and `receive_f1` rose (0.166 -> 0.200), confirming that forcing an explicit evaluation of the ball state intercepts the model's lazy reflex to label backcourt passes as serves. However, it severely degraded the model's overall sensitivity. Total predictions dropped from 556 to 510, and true positives fell sharply (200 -> 178). `set_pred_count` dropped from 27 to 19, moving in the wrong direction. 

Because evaluating the visual history of the ball (dead vs in-flight) is difficult on a frame-by-frame basis, making it a mandatory prerequisite for classification caused the model to hesitate. When it couldn't confidently determine the ball's starting state, it appears to have just dropped the event entirely rather than mapping it to `receive`. The Chain-of-Thought schema acted as a global dampener on recall rather than a precise classifier tool, leading to a worse F1 score.
