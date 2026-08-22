# Iteration 6

## CONJECTURE
The previous prompt's instruction to focus ONLY on the "MAIN FOREGROUND COURT" created a severe spatial blind spot. The model physically ignored the far side of the court and the serving areas behind the baselines, causing it to completely miss 77 real serves. This triggered a cascading definitional error: because the model missed the actual serve, it perceived the first contact it *did* see (the receive) as the start of the rally, mislabeling real `receive` events as `serve` (which happened 28 times). This destroyed True Positives (dropping to 148). 

Additionally, the model is still hallucinating heavily outside of live play (103 of the 232 invented phantoms occurred during dead time). This is a definitional/prompt failure. We can fix it by explicitly defining the main court to include both sides and baselines to restore serves, while strengthening the rules against dead-time touches and intermediate passes to strip away the phantoms.

## CHANGE
I am changing the `prompt` to explicitly include the far side and baselines in the main court definition to restore missed serves, while adding strict filters against dead-time passing and normal intermediate passes to cut phantoms.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\n\nCRITICAL INSTRUCTION: There are other matches in progress in the distant background (at the top of the screen). Completely IGNORE them. Focus ONLY on the main match taking place on the large court that occupies the bottom 3/4 of the screen. IMPORTANT: The main match includes BOTH the near side and far side of the net, AND the serving areas behind both baselines. You must track players on both sides and not miss serves from behind the court.\n\nOnly report events during a LIVE RALLY. A rally starts with a serve and ends when a point is scored. Ignore all dead-time passing, bouncing, celebrations, and pre-match warm-ups. Explicitly ignore normal intermediate passes; only report a pass if it is a 'receive', 'dig', or a 'set' that directly leads to a kill.\n\nFor each event give:\n  t       - the precise time the player physically strikes the ball\n  type    - must be one of:\n            serve: the initial hit from behind the baseline that starts a rally\n            receive: the first contact defending a serve\n            dig: the first contact defending an attack\n            set: an assist pass that directly leads to a kill\n            attack: any hit sent over the net to the opponent's side that does not score a point\n            kill: an attack that directly scores a point and ends the rally\n            block: deflecting an attack at the net\n  side    - \"left\" or \"right\": which side of the net the player is on (left half or right half of the screen)\n  number  - the player's jersey number as a string, or null if you cannot read it\n  error   - true if the touch was a mistake\n  point   - true if the rally ended here and a point was scored",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect the explicit inclusion of the baselines and far side to restore the model's ability to see serves, significantly raising `serve_recall` and total `tp`. Because it will see the real serves again, it will stop mislabeling receives as serves, which should improve precision for both categories. At the same time, the strict rule against dead-time and normal intermediate passes will cause `invented` events to drop.

```predictions
[{"metric": "tp", "direction": "up", "from": 148, "to_approx": 210},
 {"metric": "missed", "direction": "down", "from": 304, "to_approx": 240},
 {"metric": "serve_recall", "direction": "up", "from": 0.322, "to_approx": 0.450},
 {"metric": "invented", "direction": "down", "from": 233, "to_approx": 190},
 {"metric": "headline_f1", "direction": "up", "from": 0.288, "to_approx": 0.370},
 {"metric": "set_pred_count", "direction": "flat", "from": 37, "to_approx": 37}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~210       up 148 -> 167    OK     X
missed                          down to ~240     down 304 -> 254    OK    OK
serve_recall                     up to ~0.45   up 0.415 -> 0.466    OK    OK
invented                        down to ~190     down 233 -> 218    OK     X
headline_f1                      up to ~0.37   up 0.288 -> 0.314    OK     X
set_pred_count                   flat to ~37       down 37 -> 32     X     X

direction 5/6   magnitude 2/6
```

headline_f1 0.288 -> 0.314   (+0.026)
n_pred 479 -> 514   missed 304 -> 254   invented 233 -> 218
pipeline: $1.91, 0 cached, 0 failed

## VERDICT
Right about the mechanism, wrong about the size. Explicitly defining the baselines and far side restored some spatial awareness, lifting true positives (148 -> 167) and dropping missed events (304 -> 254). The strict dead-time language also successfully shaved off some hallucinated phantoms (233 -> 218). 

However, the recovery was anemic compared to the 223 true positives we had before we started messing with spatial filtering. This happened because I inadvertently re-introduced a ruled-out instruction: telling the model to "Explicitly ignore normal intermediate passes." As established in previous iterations, asking the model to selectively ignore mid-rally touches breaks its sequence understanding and causes it to drop valid events (which is why `set_pred_count` dropped unexpectedly). 

The right move is to keep pushing on spatial filtering but cleanly abandon the complex "bottom 3/4 court" geometry and the intermediate pass skipping. We should move to the hypothesis proposed in the last round: filtering based strictly on the location of the *player* making contact, rather than trying to define the dimensions of the court.
