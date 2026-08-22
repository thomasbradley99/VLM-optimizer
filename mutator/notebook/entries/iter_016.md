# Iteration 16

## CONJECTURE
The model is predicting 412 completely hallucinated events because it accurately perceives physical ball contacts but fails to apply the prompt's spatial and semantic constraints. When the vision encoder detects a bump from a background match or a casual dead-time toss, it immediately outputs it as a JSON event. This is a definitional/contextual failure: zero-shot JSON generation causes the model to bypass negative textual rules (like "ignore background completely" and "If no play happens... return empty list") because it lacks the reasoning space to evaluate the scene's macro-context. By changing `thinking` to "medium", we give the model a reasoning scratchpad to explicitly evaluate whether a perceived action is in the foreground and part of a competitive rally before it generates the JSON, which will suppress these hallucinated out-of-bounds events without sacrificing our peak temporal recall.

## CHANGE
I am changing the `thinking` lever from "low" to "medium" to allow the model to use reasoning tokens to evaluate context and apply negative constraints (ignoring background matches and dead time) before outputting predictions. (Note: `{start:.2f}` was updated to `{start}` to comply with the harness syntax requirement).

```config
{"lever": "thinking",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start} seconds into the match and runs for 6 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: A serve ONLY happens from a dead ball. If a player hits a ball that just flew across the net to them, it is a response to an incoming ball and is NEVER a serve. Label it receive or dig instead.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true if the rally ended on this contact and a point was scored\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "medium"}
```

## PREDICTION
By forcing the model to explicitly reason about what it sees, it will identify and dismiss background match hits and dead-time bumps before outputting them, causing `invented` events and `n_pred` to drop drastically. True Positives (`tp`) will remain stable because the model will still correctly log foreground rally actions. `headline_f1` will rise as the denominator shrinks. `serve_pred_count` will fall as it reasons that mid-rally hits are not from a dead ball. `set_pred_count` will remain flat because its strict text definition is already effectively gating its prediction.

```predictions
[
  {"metric": "n_pred", "direction": "down", "from": 856, "to_approx": 650},
  {"metric": "invented", "direction": "down", "from": 412, "to_approx": 250},
  {"metric": "tp", "direction": "flat", "from": 309, "to_approx": 305},
  {"metric": "headline_f1", "direction": "up", "from": 0.440, "to_approx": 0.500},
  {"metric": "serve_pred_count", "direction": "down", "from": 226, "to_approx": 170},
  {"metric": "set_pred_count", "direction": "flat", "from": 38, "to_approx": 38}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
n_pred                          down to ~650     flat 856 -> 822     X     X
invented                        down to ~250     flat 412 -> 396     X     X
tp                              flat to ~305     flat 309 -> 306    OK    OK
headline_f1                       up to ~0.5  flat 0.44 -> 0.446     X     X
serve_pred_count                down to ~170     down 226 -> 201    OK     X
set_pred_count                   flat to ~38       down 38 -> 27     X     X

direction 2/6   magnitude 1/6
```

headline_f1 0.440 -> 0.446   (+0.007)
n_pred 856 -> 822   missed 106 -> 124   invented 412 -> 396
pipeline: $4.27, 0 cached, 0 failed

## VERDICT
Wrong. The `thinking` mechanism completely failed to suppress hallucinated events. 

Allowing the model reasoning tokens (`thinking: "medium"`) did not cause `n_pred` or `invented` to drop drastically as predicted. They remained effectively flat (`invented` 412 -> 396). This shows that the model's failure to ignore background courts and dead-ball casual hits is not a lack of reasoning space, but a fundamental limitation in its visual perception and spatial grouping. It simply uses the reasoning tokens to rationalize background hits as valid foreground events because it cannot reliably segregate depth planes based on semantic labels like "main court". `serve_pred_count` dropped slightly (226 -> 201) but remains massively overpredicted, further confirming that textual reasoning cannot easily override its visual reflex of categorizing any deep-court bump as a serve. 

The change made no meaningful difference to F1 while likely increasing API latency/cost, so it should be reverted.
