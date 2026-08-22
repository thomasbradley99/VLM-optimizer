# Iteration 11

## CONJECTURE
The pipeline has hit a hard perception ceiling where 229 true events are missed entirely because 5 fps (one frame every 200ms) is too slow to capture fast volleyball contacts. Volleyball is highly kinetic; split-second actions like attacks and digs often occur entirely between frames or appear as illegible motion blur at low frame rates, forcing the model to either guess or miss them. This is a perception gap caused by low temporal resolution. By doubling the sampling rate to 10 fps, we provide the model with 100ms temporal resolution, making fast kinetic actions visible.

## CHANGE
I am changing the `fps` parameter from 5 to 10 to give the model twice the temporal resolution, allowing it to see fast actions that currently fall between frames.

```config
{"lever": "fps",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start:.2f} seconds into the match and runs for 30 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: A serve ONLY happens from a dead ball. If a player hits a ball that just flew across the net to them, it is a response to an incoming ball and is NEVER a serve. Label it receive or dig instead.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start:.2f}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true if the rally ended on this contact and a point was scored\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 10, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By increasing the frame rate to 10 fps, the model will see the split-second contacts that were previously blurred or missed between 5fps frames. True Positives (`tp`) will rise as fast events like attacks and digs become visible. `missed` events will drop significantly. `n_pred` will increase as the model spots more contacts. Because the model still relies on the strict, unchanged textual definitions for `set` (which mandates an assist leading to a kill), `set_pred_count` will remain perfectly flat.

```predictions
[
  {"metric": "tp", "direction": "up", "from": 191, "to_approx": 230},
  {"metric": "missed", "direction": "down", "from": 229, "to_approx": 190},
  {"metric": "n_pred", "direction": "up", "from": 545, "to_approx": 600},
  {"metric": "set_pred_count", "direction": "flat", "from": 23, "to_approx": 23},
  {"metric": "dig_recall", "direction": "up", "from": 0.267, "to_approx": 0.320}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~230     down 191 -> 124     X     X
missed                          down to ~190       up 229 -> 339     X     X
n_pred                            up to ~600     down 545 -> 346     X     X
set_pred_count                   flat to ~23       flat 23 -> 21    OK    OK
dig_recall                       up to ~0.32 down 0.267 -> 0.151     X     X

direction 1/5   magnitude 1/5
```

headline_f1 0.349 -> 0.277   (-0.072)
n_pred 545 -> 346   missed 229 -> 339   invented 224 -> 135
pipeline: $2.49, 0 cached, 39 failed

## VERDICT
Wrong. The metrics moved exactly opposite to my prediction, but the numbers show a mechanical failure rather than a perceptual one: the harness reports "39 failed" chunks. By doubling the frame rate to 10 fps, a 30-second chunk now contains 300 frames. This massive payload likely exceeded the Gemini model's token limits, payload size constraints, or caused timeouts, causing those 39 API calls to fail entirely and return zero predictions. This explains the severe drop in total predictions (`n_pred` dropped from 545 to 346) and the corresponding crash in True Positives (`tp` from 191 to 124). We didn't test perception; we broke the context window.
