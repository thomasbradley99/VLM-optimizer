# Iteration 19

## CONJECTURE
The pipeline is suffering from two pure definitional gaps that inflate `n_pred` and skew score attribution. First, because 6-second clips often start mid-rally, the model mistakenly labels the first defensive pass it sees as a `serve` (predicting 226 serves vs 118 real) because it lacks the preceding context to know the ball wasn't dead. Second, the model artificially inflates `score_margin_err` (+46 ours vs -11 real) because it incorrectly flags `point=true` on errors, awarding the point to the offending team. In Iteration 18, we proved that explicitly warning about mid-rally clip boundaries and redefining `point` to exclude errors successfully fixed both these issues (dropping serve predictions to 187 and margin error to 35). However, Iteration 18 failed overall because it also included a toxic "Background Spatial Rule" that caused `invented` events to explode and F1 to tank. This is a definitional translation fix. By applying ONLY the proven boundary warning and point logic, and abandoning all spatial/dead-time vetoes, we will strictly cut `n_pred` and fix score attribution while maintaining our peak True Positives (309).

## CHANGE
I am updating the prompt to embed a strict clip boundary warning directly into the `serve` definition to suppress mid-rally hallucinated serves, and redefining the `point` flag to strictly exclude errors. All spatial and background vetoes are kept out to preserve our high recall.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start} seconds into the match and runs for 6 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: Because clips are 6 seconds, they often start mid-rally. Do NOT assume the first hit you see is a serve. A serve is strictly the initial hit from a dead ball behind the baseline. Defensive mid-rally passes are never serves.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true ONLY if this exact contact actively WON the rally for the team making it (e.g., a kill or ace). If the contact was an error that LOST the point, point MUST be false.\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By warning the model that clips often start mid-rally, it will stop greedily assigning `serve` to the first defensive pass it sees, dropping `serve_pred_count` and overall `n_pred`. By redefining `point` to exclude errors, it will stop awarding points to the team that made the mistake, significantly fixing `score_margin_err`. Because we have removed the toxic spatial and dead-time vetoes that previously confused the model, it will not drop real foreground events, keeping `tp` and `invented` completely flat. As the denominator shrinks with stable TP, `headline_f1` will rise.

```predictions
[
  {"metric": "serve_pred_count", "direction": "down", "from": 226, "to_approx": 185},
  {"metric": "n_pred", "direction": "down", "from": 856, "to_approx": 815},
  {"metric": "score_margin_err", "direction": "down", "from": 57, "to_approx": 35},
  {"metric": "tp", "direction": "flat", "from": 309, "to_approx": 309},
  {"metric": "invented", "direction": "flat", "from": 412, "to_approx": 412},
  {"metric": "headline_f1", "direction": "up", "from": 0.440, "to_approx": 0.455}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                down to ~185     down 226 -> 202    OK    OK
n_pred                          down to ~815     flat 856 -> 895     X     X
score_margin_err                 down to ~35       down 57 -> 49    OK     X
tp                              flat to ~309     flat 309 -> 315    OK    OK
invented                        flat to ~412       up 412 -> 458     X     X
headline_f1                     up to ~0.455  flat 0.44 -> 0.436     X    OK

direction 3/6   magnitude 3/6
```

headline_f1 0.440 -> 0.436   (-0.004)
n_pred 856 -> 895   missed 106 -> 113   invented 412 -> 458
pipeline: $3.31, 0 cached, 0 failed

## VERDICT
Right about the mechanism for serves and scores, wrong about the stability of the overall noise. 

The boundary warnings for serves and the strict logic excluding errors from `point` successfully pushed `serve_pred_count` (226 -> 202) and `score_margin_err` (57 -> 49) in the correct directions. However, I was completely wrong that removing the background spatial vetoes would keep `invented` events flat. Instead, `invented` surged from 412 to 458, which drove up `n_pred` and slightly degraded F1. While the explicit spatial rules tested in Iteration 18 were toxic to recall, stripping them out completely leaves the model highly susceptible to hallucinating background or dead-time events.
