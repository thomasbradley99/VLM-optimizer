# Iteration 10

## CONJECTURE
The pipeline is suffering from instruction overload. Every time we add explicit text heuristics (whether sequence flows, negative vetoes, spatial limits, or dead-ball rules) to solve the serve/receive/attack confusion, True Positives drop or stay flat, while overall F1 only rises due to predicting fewer events. The model rigidly misapplies these logical rules to fuzzy 5fps video; when it is unsure if a complex condition (like "dead ball" or "handling opponent's serve") is met, it simply drops the event, resulting in 229 missed events. This is a perception/instruction gap. We need to stop fighting the model's visual perception with logic. By replacing the heavily engineered definitions with a minimalist prompt that provides only the bare class names (keeping only the definitional mapping rule for `set`), we can allow the model to rely entirely on its pre-trained visual priors for standard volleyball actions, which should increase recall and True Positives.

## CHANGE
I am removing all descriptive definitions and logical constraints for the event types (except the `set` = assist rule), presenting just the bare class names so the model relies purely on its pre-trained visual recognition.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start:.2f} seconds into the match and runs for 30 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve\n  receive\n  dig\n  set - ONLY report a set if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack\n  kill\n  block\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start:.2f}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true if the rally ended on this contact and a point was scored\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By removing the strict textual rules that previously caused the model to second-guess its visual perception or drop events entirely, the model will classify events more naturally. The total number of predictions (`n_pred`) will rise, which will cause `missed` events to fall and True Positives (`tp`) to climb. Relieved of complex sequence logic, the model's baseline understanding will perform better, raising `receive_f1`. `set_pred_count` will remain flat because its explicit definitional constraint is retained.

```predictions
[
  {"metric": "tp", "direction": "up", "from": 191, "to_approx": 215},
  {"metric": "missed", "direction": "down", "from": 229, "to_approx": 205},
  {"metric": "n_pred", "direction": "up", "from": 545, "to_approx": 570},
  {"metric": "receive_f1", "direction": "up", "from": 0.196, "to_approx": 0.220},
  {"metric": "set_pred_count", "direction": "flat", "from": 23, "to_approx": 23}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~215     flat 191 -> 190     X     X
missed                          down to ~205     flat 229 -> 221     X     X
n_pred                            up to ~570     down 545 -> 511     X     X
receive_f1                       up to ~0.22 flat 0.196 -> 0.183     X     X
set_pred_count                   flat to ~23       down 23 -> 16     X     X

direction 0/5   magnitude 0/5
```

headline_f1 0.349 -> 0.358   (+0.009)
n_pred 545 -> 511   missed 229 -> 221   invented 224 -> 182
pipeline: $1.88, 0 cached, 0 failed

## VERDICT
Wrong about the mechanism, though lucky with a small F1 gain. I predicted that removing descriptive constraints would cause total predictions (`n_pred`) and True Positives (`tp`) to rise as the model stopped artificially suppressing events. Instead, `n_pred` dropped significantly (545 -> 511) and `tp` stayed completely flat (191 -> 190). 

The F1 gain was driven entirely by a massive drop in `invented` events (224 -> 182). This shows that our previous verbose definitions were actually causing the model to over-predict—force-fitting visual noise into categories based on text descriptions. Stripping the prompt to the bare minimum made the model more conservative, relying purely on its pre-trained visual confidence. However, it did absolutely nothing to fix the ~220 missed events, proving that the low recall is not caused by text-based rule suppression.
