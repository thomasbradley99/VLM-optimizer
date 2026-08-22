# Iteration 1

## CONJECTURE
The model is over-predicting events across the pipeline (565 predicted vs 550 real, with 206 entirely hallucinated ghosts). Most of these ghosts (176) occur inside live rallies, including 29 phantom serves and 41 phantom receives. This is a perception issue caused by the short 15-second `chunk_len`, which frequently truncates mid-rally. When a clip begins mid-rally, the model misinterprets back-row hits as new serves, and boundary-straddling events get reported twice with slight timing variations that evade the 0.4s deduplication window. Increasing the chunk length to 30 seconds will halve the number of clip boundaries, encapsulating entire rallies in single clips and sharply reducing these contextual and duplication errors.

## CHANGE
I am changing `chunk_len` from 15.0 to 30.0 to provide enough temporal context to see full rallies and reduce boundary-related hallucination artifacts.

```config
{"lever": "chunk_len",
 "prompt": "You are an expert volleyball statistician scouting one match from a fixed camera.\n\nCONTEXT. Several courts are in use at once. Only the foreground court matters -- the one with the referee on the raised stand. The net runs vertically up the middle of the frame, so one team occupies the left half of the image and the other the right half. Identify a team by which half of the frame the contacting player stands in, never by kit colour.\n\nThis clip begins at {start} seconds into the match.\n\nTAXONOMY. Every contact belongs to exactly one of seven classes. Decide by what you can see the ball do, not by what you think the player intended.\n\n  serve    the single contact that begins a rally, struck from behind the back line. Never report a serve mid-rally.\n  receive  the first defensive contact answering a serve. Maximum one per rally.\n  dig      a defensive contact answering an attack; the ball stays on that side\n  set      a contact that places the ball for a team-mate to attack, BUT ONLY report it if the resulting attack is a kill (an assist).\n  attack   any contact that sends the ball over the net to the opponents\n  kill     an attack that ends the rally immediately\n  block    a contact made at the net by a player with hands above it\n\nREPORTING. Give one row per contact you actually observe:\n  t        time of contact in absolute match seconds, to a fraction of a second\n  type     one of the seven above\n  side     \"left\" or \"right\", the half of the frame the contacting player is in\n  number   the jersey number as a string, or null if you cannot read it\n  error    true if the contact was a mistake -- into the net, out of bounds, mishandled\n  point    true ONLY if the team making THIS contact won the rally. If this contact is an error that loses the rally, point MUST be false.\n\nIf nothing happens in this clip, return an empty list.",
 "chunk_len": 30.0, "overlap": 4.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect overall predictions to drop significantly as boundary duplication and mid-rally contextual errors disappear. Specifically, false serves and receives should decrease as the model correctly identifies them as continuations of an existing rally rather than a new one. The number of true positives should remain largely flat since the underlying recognition capability hasn't changed, while the F1 score will rise due to the denominator shrinking. `set` predictions should stay flat since they are already constrained perfectly by the definition rule.

```predictions
[{"metric": "serve_pred_count", "direction": "down", "from": 152, "to_approx": 125},
 {"metric": "receive_pred_count", "direction": "down", "from": 120, "to_approx": 105},
 {"metric": "n_pred", "direction": "down", "from": 565, "to_approx": 500},
 {"metric": "tp", "direction": "flat", "from": 230, "to_approx": 230},
 {"metric": "set_pred_count", "direction": "flat", "from": 44, "to_approx": 44}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                down to ~125     down 152 -> 104    OK     X
receive_pred_count              down to ~105      down 120 -> 88    OK     X
n_pred                          down to ~500     down 565 -> 414    OK     X
tp                              flat to ~230     down 230 -> 149     X     X
set_pred_count                   flat to ~44       down 44 -> 35     X     X

direction 3/5   magnitude 0/5
```

headline_f1 0.413 -> 0.309   (-0.103)
n_pred 565 -> 414   missed 202 -> 280   invented 217 -> 144
pipeline: $1.38, 0 cached, 0 failed

## VERDICT
I was right about the mechanism (reducing chunk boundaries and adding context reduced false positives), but dead wrong about the size and direction of the true positives. The numbers show a disastrous drop in recall: while `invented` fell from 217 to 144, `missed` events spiked from 202 to 280, dragging True Positives down from 230 to 149 and tanking the F1 score. 

The longer 30-second chunks caused the model to simply skip over many valid events. `gemini-3.7-flash` (especially in "low" thinking mode) struggles with dense event extraction over longer temporal windows. When asked to annotate a full 10-20 second rally containing 10+ contacts within a 150-frame clip, it suffers from attention dilution and drops events it was previously catching. 

This change made things significantly worse because preserving recall is critical. The right move is to immediately revert to 15-second chunks to restore our True Positives, and attack the clip-start hallucination problem through strict visual criteria in the prompt instead of manipulating the temporal window.
