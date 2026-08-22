# Iteration 15

## CONJECTURE
The model predicts 412 completely invented events because it misinterprets casual, non-competitive contacts during the dead time between points as active rally events. In a narrow 6-second clip, players warming up or tossing the ball to the referee looks like a valid event unless the model is explicitly told to evaluate the competitive context. Furthermore, `score_margin_err` is artificially inflated (+46 ours vs -11 real) because the model often marks `point=true` on errors, incorrectly awarding the point to the team that made the error. This is a definitional mismatch: the scout only logs active rallies and credits points to the winning team. By adding a strict "Dead Time Veto" to suppress casual contacts, a "Clip Boundary" warning for mid-rally serves, and redefining `point` to explicitly exclude errors, we can drastically reduce `n_pred` and fix score attribution without losing our high True Positives.

## CHANGE
I am adding explicit prompt rules for "DEAD TIME VETO" and "CLIP BOUNDARIES" to stop the model from hallucinating events between points or mislabeling boundary contacts as serves, and I am redefining the `point` flag so it is never awarded on an error.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start} seconds into the match and runs for 6 seconds.\n\nDEAD TIME VETO: Most of a match is dead time between points. Players casually walking, celebrating, or bouncing/tossing the ball back and forth between rallies are NOT making reportable events. ONLY report contacts during an active, competitively played rally. If the clip shows dead time, return an empty list.\n\nCLIP BOUNDARIES: Clips are only 6 seconds and often start mid-rally. Do not assume the first contact you see is a \"serve\". A serve is strictly a hit from behind the baseline to start a point.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: A serve ONLY happens from a dead ball behind the baseline. If a player hits a ball that just flew across the net to them, it is a response to an incoming ball and is NEVER a serve. Label it receive or dig instead.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true ONLY if this specific contact actively WON the point for the team making it (e.g., a kill or ace). If the contact was an error that LOST the rally, point must be FALSE.\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no active play happens in this clip, return an empty list.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By aggressively filtering out dead time, the model will stop inventing events during warmups and between points, causing total predictions to plummet. The clip boundary warning will stop it from greedily assigning `serve` to mid-rally passes caught at the start of a clip. The tighter `point` definition will stop erroring teams from being incorrectly awarded points, drastically fixing the `score_margin_err`. True Positives will remain stable because the model is merely refraining from guessing, rather than losing its ability to see active events.

```predictions
[
  {"metric": "n_pred", "direction": "down", "from": 856, "to_approx": 650},
  {"metric": "invented", "direction": "down", "from": 412, "to_approx": 250},
  {"metric": "serve_pred_count", "direction": "down", "from": 226, "to_approx": 160},
  {"metric": "score_margin_err", "direction": "down", "from": 57, "to_approx": 25},
  {"metric": "tp", "direction": "flat", "from": 309, "to_approx": 309}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
n_pred                          down to ~650     flat 856 -> 831     X     X
invented                        down to ~250     flat 412 -> 404     X     X
serve_pred_count                down to ~160     down 226 -> 197    OK     X
score_margin_err                 down to ~25       down 57 -> 42    OK     X
tp                              flat to ~309     flat 309 -> 303    OK    OK

direction 3/5   magnitude 1/5
```

headline_f1 0.440 -> 0.439   (-0.001)
n_pred 856 -> 831   missed 106 -> 123   invented 412 -> 404
pipeline: $3.30, 0 cached, 0 failed

## VERDICT
Right about the mechanism for fixing the score margin, but wrong about the dead time veto. The numbers show that explicitly redefining `point` to exclude `error` contacts successfully reduced the `score_margin_err` (57 down to 42) and the clip boundary warning slightly reduced false serves. However, my aggressive "DEAD TIME VETO" prompt instruction failed completely to reduce the massive number of `invented` events (412 to 404). The model is incapable of judging the macro-context of "warmup" versus "active rally"; if it sees a player bump a ball between plays, it will eagerly classify it as a dig or receive regardless of the competitive context. Additionally, reducing the chunk size to 6 seconds (down from 15s previously) did not improve recall (TP dropped slightly, misses rose), showing we have hit the floor on attention saturation and are now suffering from actions being severed across tight clip boundaries.
