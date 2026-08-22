# Iteration 18

## CONJECTURE
The pipeline is suffering from two major contextual/definitional failures that massively inflate `n_pred` and tank F1. First, the model predicts 412 completely invented events because it cannot map the abstract semantic instruction "main court" to its visual field, leading it to eagerly log hits from the other matches in the background. Second, because 6-second clips often start mid-rally, the model frequently mislabels the first defensive pass it sees as a `serve` because it lacks preceding context (driving `serve` predictions to 226 vs 118 real). Separately, `score_margin_err` is heavily skewed (+46 ours vs -11 real) because the model incorrectly marks `point=true` on errors, awarding the point to the offending team. 

This is a definitional/translation gap. Text reasoning failed, but vision models natively understand 2D coordinates. By explicitly defining the background matches via a rigid spatial boundary ("top 20% of the screen"), adding a clip boundary warning, and restricting `point` to winning actions, we can massively cut false positives and fix point attribution without losing our peak temporal recall.

## CHANGE
I am modifying the prompt to introduce a strict `BACKGROUND SPATIAL RULE` (filtering events in the top 20% of the screen), a `CLIP BOUNDARIES` warning to suppress mid-rally serve hallucinations, and explicitly redefining the `point` flag to be false on errors. I am leaving all other config levers untouched to preserve our high `TP`.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nBACKGROUND SPATIAL RULE: The background matches are located in the top 20% of the video frame. You MUST ignore them. ONLY report an event if the PLAYER making contact is standing in the lower 80% of the screen.\n\nCLIP BOUNDARIES: Because clips are only 6 seconds, they often start mid-rally. Do NOT assume the first hit you see is a serve. A serve is strictly the initial hit from behind the baseline to start a point. Defensive passes are never serves.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start} seconds into the match and runs for 6 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: A serve ONLY happens from a dead ball. If a player hits a ball that just flew across the net to them, it is a response to an incoming ball and is NEVER a serve. Label it receive or dig instead.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true ONLY if this exact contact actively WON the rally for the team making it (like a kill or ace). If the contact was an error that LOST the point, point MUST be false.\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By mapping the background court veto to a concrete 2D spatial plane, the model will successfully drop hallucinated hits from other matches, dropping `invented` events. The boundary warning will stop it from greedily predicting `serve` at `t=0`. The tighter `point` definition will stop erroring teams from being awarded points, fixing `score_margin_err`. True Positives (`tp`) will remain completely flat since we are only filtering noise, causing `headline_f1` to rise significantly as the denominator shrinks.

```predictions
[
  {"metric": "n_pred", "direction": "down", "from": 856, "to_approx": 720},
  {"metric": "invented", "direction": "down", "from": 412, "to_approx": 300},
  {"metric": "serve_pred_count", "direction": "down", "from": 226, "to_approx": 170},
  {"metric": "score_margin_err", "direction": "down", "from": 57, "to_approx": 30},
  {"metric": "tp", "direction": "flat", "from": 309, "to_approx": 309},
  {"metric": "headline_f1", "direction": "up", "from": 0.440, "to_approx": 0.470}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
n_pred                          down to ~720       up 856 -> 900     X     X
invented                        down to ~300       up 412 -> 454     X     X
serve_pred_count                down to ~170     down 226 -> 187    OK    OK
score_margin_err                 down to ~30       down 57 -> 35    OK    OK
tp                              flat to ~309     flat 309 -> 298    OK    OK
headline_f1                      up to ~0.47  down 0.44 -> 0.411     X     X

direction 3/6   magnitude 3/6
```

headline_f1 0.440 -> 0.411   (-0.029)
n_pred 856 -> 900   missed 106 -> 104   invented 412 -> 454
pipeline: $3.35, 0 cached, 0 failed

## VERDICT
Right about the mechanism for serves and score logic, wrong about the size and direction of the spatial rule. The numbers show that the clip boundary warning and error-logic decoupling successfully dropped `serve` predictions (226 down to 187) and `score_margin_err` (57 down to 35), validating those specific translation fixes. However, defining a strict spatial boundary ("top 20%") for background courts actively backfired, causing `n_pred` and `invented` events to rise (412 to 454) and tanking F1. Giving the model spatial coordinate percentages to ignore seems to draw its attention to those areas or confuse its tracking in the remaining 80%. Because the false positives exploded, the overall metric got worse.
