# Iteration 8

## CONJECTURE
The model is suffering from a massive perception failure caused by visual distraction, not a definitional gap. It missed 229 real events entirely while inventing 224 fake events. Because this is a convention hall with other matches in the background, the model is likely time-sharing its attention—watching the background courts and reporting their events (hence the 224 false positives) while completely ignoring the play on the main court (hence the 229 missed true positives). Instructing the model in text to "ignore other matches" has failed because the visual presence of active play in the background is too salient. By physically cropping the video to remove the background matches, we can force the model to focus exclusively on the main court.

## CHANGE
I am changing the `crop` parameter to physically strip away the top 330 pixels of the video before scaling, completely removing the background matches from the image the model sees.

```config
{"lever": "crop",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start:.2f} seconds into the match and runs for 30 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: A serve ONLY happens from a dead ball. If a player hits a ball that just flew across the net to them, it is a response to an incoming ball and is NEVER a serve. Label it receive or dig instead.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start:.2f}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true if the rally ended on this contact and a point was scored\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 30.0,
 "overlap": 8.0,
 "fps": 5,
 "width": 640,
 "crop": "1920:620:0:330",
 "media_resolution": null,
 "model": "gemini-3.7-flash",
 "thinking": "low"}
```

## PREDICTION
By removing the background matches from the image entirely, the model will stop reporting hallucinated actions from those courts, causing `invented` events to drop sharply. With its attention fully constrained to the main court, it will catch far more of the foreground action, causing `missed` events to drop and `tp` to rise. `set_pred_count` will remain flat because its strict assist-only definition limits how many sets can logically be reported, even with better visibility.

```predictions
[
  {"metric": "tp", "direction": "up", "from": 191, "to_approx": 240},
  {"metric": "invented", "direction": "down", "from": 224, "to_approx": 120},
  {"metric": "missed", "direction": "down", "from": 229, "to_approx": 160},
  {"metric": "n_pred", "direction": "down", "from": 545, "to_approx": 480},
  {"metric": "set_pred_count", "direction": "flat", "from": 23, "to_approx": 23}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~240     down 191 -> 171     X     X
invented                        down to ~120     down 224 -> 189    OK     X
missed                          down to ~160       up 229 -> 263     X     X
n_pred                          down to ~480     down 545 -> 476    OK    OK
set_pred_count                   flat to ~23       down 23 -> 19     X     X

direction 2/5   magnitude 1/5
```

headline_f1 0.349 -> 0.333   (-0.016)
n_pred 545 -> 476   missed 229 -> 263   invented 224 -> 189
pipeline: $0.00, 169 cached, 0 failed

## VERDICT
I was right about the mechanism reducing false positives, but completely wrong about the side effects on recall. 

The physical crop did remove background distraction, successfully dropping `invented` events from 224 to 189. However, I failed to account for the ball's trajectory: chopping off the top 330 pixels (roughly 30% of a 1080p frame) hides the ball during high arcs on serves, passes, and sets. Blind to the ball in flight, the model lost track of the foreground rallies, causing `tp` to drop (191 -> 171) and `missed` events to spike (229 -> 263). The F1 dropped because sacrificing the top of the frame costs far more in lost foreground action than it saves in reduced background hallucination. 

This change made things worse because it physically erased the ball from the model's vision.
