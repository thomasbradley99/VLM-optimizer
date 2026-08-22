# Iteration 4

## CONJECTURE
The model is suffering from a massive "off-by-one" labeling cascade caused by a rigid global sequence bias. It expects every rally to follow a global order: Serve, Receive, Set, Attack, Dig. Because the actual serve is often hard to see (missed) and we explicitly instructed it to skip regular sets, the model takes the remaining visible contacts (Receive, Attack, Dig) and forcibly applies its expected sequence labels to them. This causes the real Receive to be labeled "serve" (43 times), the real Attack to be labeled "receive" (28 times), and the real Dig to be labeled "attack" (15 times), perfectly matching the diagonal shift in the confusion matrix. Iterations 1-3 failed because physical descriptors (lines, kinematics, trajectory) cannot override this internal sequence counter. This is a definitional/framework mismatch where the model's global sequence counting overrides its visual perception.

## CHANGE
I am replacing the event definitions with a "Per-Team Possession" framework. By instructing the model to evaluate sequences *per team* during a possession (1st contact = receive/dig, 2nd = set, 3rd = attack), we hijack its sequence-counting bias and align it with the actual rules of volleyball, preventing a missed serve from cascading and shifting the labels of the entire rally.

```prompt
You are scouting a single volleyball match from a fixed camera.

CRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.

The net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- "left" or "right" as you see it on screen. Do not use jersey colour.

This clip begins at {start:.2f} seconds into the match and runs for 30 seconds.

CRITICAL REFRAME - PER-TEAM POSSESSION:
Do not assume a global sequence like "Serve, then Receive, then Attack". If you miss the serve, this will cause you to mislabel the entire rally! Instead, evaluate events based on TEAM POSSESSIONS. Every time a team receives the ball, they have up to 3 contacts:
  receive - a team's FIRST contact when receiving the opponent's serve. 
  dig     - a team's FIRST contact when receiving the opponent's attack.
  set     - a team's SECOND contact placing the ball for an attacker, BUT ONLY if it directly leads to a kill (an assist). Do NOT report regular sets that do not lead to a kill.
  attack  - a team's offensive hit (often the 3rd contact) that sends the ball OVER THE NET to the opponent's side, but does not win the rally.
  kill    - a team's offensive hit that sends the ball OVER THE NET and immediately wins the rally.

Independent actions outside the 3-contact possession:
  serve   - the single initial hit from the back line that starts a rally. A team's first contact of a ball *already in play* is NEVER a serve.
  block   - a defensive contact made AT THE NET by a player with hands above it.

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
By breaking the global sequence cascade, the model will stop assigning "serve" to a team's first contact (receive), causing `serve_pred_count` to drop sharply. Real receives will be correctly labeled, and real attacks will no longer be labeled as receives, causing `receive_f1` and `attack_f1` to increase significantly. Because the suppression of regular sets remains untouched, `set_pred_count` will remain flat. Overall True Positives will rise as labels finally align with the timestamps.

```json
[
  {"metric": "serve_pred_count", "direction": "down", "from": 120, "to_approx": 85},
  {"metric": "receive_f1", "direction": "up", "from": 0.142, "to_approx": 0.300},
  {"metric": "attack_f1", "direction": "up", "from": 0.236, "to_approx": 0.320},
  {"metric": "tp", "direction": "up", "from": 184, "to_approx": 220},
  {"metric": "set_pred_count", "direction": "flat", "from": 30, "to_approx": 30}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                 down to ~85       up 120 -> 128     X     X
receive_f1                        up to ~0.3   up 0.142 -> 0.172    OK     X
attack_f1                        up to ~0.32 flat 0.236 -> 0.231     X     X
tp                                up to ~220     flat 184 -> 190     X     X
set_pred_count                   flat to ~30       down 30 -> 27     X     X

direction 1/5   magnitude 0/5
```

headline_f1 0.350 -> 0.351   (+0.001)
n_pred 500 -> 532   missed 247 -> 216   invented 197 -> 198
pipeline: $1.90, 0 cached, 0 failed

## VERDICT
Wrong. The "off-by-one sequence cascade" hypothesis was completely incorrect. I predicted that replacing the global sequence with a per-team possession framework would fix the sequence mismatch and sharply drop serve predictions. Instead, `serve_pred_count` actually went up (120 to 128) and `attack_f1` stayed entirely flat (0.236 to 0.231). 

The numbers show that the model's confusion between serves and receives is not an artifact of an internal sequence counter shifting labels down the line. It is a deeply ingrained, reflexive visual misclassification. The model sees a backcourt hit and calls it a serve, regardless of whether we frame the logic around physical constraints, trajectories, or per-team possessions. Our textual frameworks are being ignored in favor of a lazy pre-trained visual bias.
