# Iteration 12

## CONJECTURE
The model misses 229 real events entirely. In Iteration 11, we hypothesized this was due to low temporal resolution and doubled the frame rate to 10 fps, but this crashed the API because 30-second clips at 10 fps generated 300 frames per call. The notebook suggests testing 15-second clips at 10 fps. However, to isolate variables and follow the "change one thing" rule, we must first test the effect of shorter chunks at the baseline 5 fps. Processing 30 seconds of highly kinetic action (150 frames) may exceed the model's temporal attention span, causing it to drop events mid-clip. By halving the `chunk_len` to 15.0 seconds, we reduce the video length and cognitive load per call. If `missed` events drop and True Positives (`tp`) rise, we will know that attention saturation is a bottleneck, and we will establish a stable baseline for testing 10 fps in the next round. This is a perception failure related to context limits.

## CHANGE
I am decreasing the `chunk_len` to 15.0 seconds and `overlap` to 4.0 seconds (updating the prompt text to match) to test if a shorter attention window improves event recall before we introduce higher frame rates.

```config
{"lever": "chunk_len",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start:.2f} seconds into the match and runs for 15 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: A serve ONLY happens from a dead ball. If a player hits a ball that just flew across the net to them, it is a response to an incoming ball and is NEVER a serve. Label it receive or dig instead.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start:.2f}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true if the rally ended on this contact and a point was scored\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 15.0,
 "overlap": 4.0,
 "fps": 5,
 "width": 640,
 "crop": null,
 "media_resolution": null,
 "model": "gemini-3.7-flash",
 "thinking": "low"}
```

## PREDICTION
By reducing the chunk length to 15 seconds, the model will have less temporal distance to track per API call, mitigating attention-based forgetting. `missed` events will drop as it spots more actions in the shorter windows, causing True Positives (`tp`) to rise. Total predictions (`n_pred`) will increase. `invented` events will likely rise slightly because doubling the number of clips creates more clip boundaries where hallucinated edge-case overlaps can occur. `set_pred_count` will remain perfectly flat because its strict text-based assist definition restricts its usage regardless of chunk length.

```predictions
[
  {"metric": "tp", "direction": "up", "from": 191, "to_approx": 210},
  {"metric": "missed", "direction": "down", "from": 229, "to_approx": 205},
  {"metric": "n_pred", "direction": "up", "from": 545, "to_approx": 580},
  {"metric": "invented", "direction": "up", "from": 224, "to_approx": 240},
  {"metric": "set_pred_count", "direction": "flat", "from": 23, "to_approx": 23}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~210       up 191 -> 239    OK     X
missed                          down to ~205     down 229 -> 169    OK     X
n_pred                            up to ~580       up 545 -> 673    OK     X
invented                          up to ~240       up 224 -> 292    OK     X
set_pred_count                   flat to ~23         up 23 -> 34     X     X

direction 4/5   magnitude 0/5
```

headline_f1 0.349 -> 0.391   (+0.042)
n_pred 545 -> 673   missed 229 -> 169   invented 224 -> 292
pipeline: $2.16, 0 cached, 0 failed

## VERDICT
Right about the mechanism, wrong about the size. The numbers clearly show that shrinking the temporal window significantly improves the model's ability to spot events, proving that it suffers from attention saturation over long video clips. `tp` jumped by 48 and `missed` dropped by 60, far exceeding my predictions. However, doubling the number of API calls meant creating more clip boundaries and fragmented context windows, causing `invented` events to rise by 68. `set_pred_count` also went up (from 23 to 34); although the strict text definition remained in place, the model's overall event recall skyrocketed so much that it naturally found more valid (or borderline) sets.
