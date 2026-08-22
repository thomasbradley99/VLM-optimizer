# Iteration 5

## CONJECTURE
The model is hallucinating hundreds of events because it is correctly perceiving the three background matches and the pre-match warm-ups (there are over 70 ghost predictions between 00:00 and 16:37 before the real match even begins), and it is reporting them as main-court play. This is a perception/context failure, not a definitional one. Iteration 1 attempted to solve this by applying a rigid visual `crop`, but that cut off the ball's high trajectory during main-court rallies, blinding the model and costing 50 True Positives. Iteration 3/4 tried to suppress these false positives with rigid logical flow rules ("Serve -> Receive -> Pass..."), but that paralyzed the model when clips sliced through a rally, further dropping TP to 163. I need to attack the background matches purely through language.

## CHANGE
I am restoring a clean prompt (removing the destructive causal sequencing rules to recover our lost True Positives) and adding a critical, explicit command instructing the model to completely ignore the background courts and pre-match warm-ups to surgically eliminate the false positives.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\n\nCRITICAL INSTRUCTION: There are three other matches in progress in the background at the top of the screen. You must completely IGNORE all events, players, and matches in the background. ONLY report events happening on the MAIN FOREGROUND COURT. Ignore all pre-match warm-ups and dead-ball passing.\n\nList ONLY specific meaningful volleyball events in live play on the main foreground court.\nFor each event give:\n  t       - the precise time the player physically strikes the ball\n  type    - must be one of:\n            serve: the initial hit from behind the baseline that starts a rally\n            receive: the first contact defending a serve\n            dig: the first contact defending an attack\n            set: an assist pass that directly leads to a kill\n            attack: an offensive hit sent over the net that does not score a point\n            kill: an attack that directly scores a point and ends the rally\n            block: deflecting an attack at the net\n  side    - \"left\" or \"right\": which side of the net the player is on (left half or right half of the screen)\n  number  - the player's jersey number as a string, or null if you cannot read it\n  error   - true if the touch was a mistake\n  point   - true if the rally ended here and a point was scored",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect removing the rigid causal logic will unparalyze the model and restore its ability to spot valid events, driving True Positives back up toward the baseline. Simultaneously, the explicit instruction to ignore the background courts and warm-ups will cleanly remove dozens of ghosts (especially the 70+ predicted before 16:37), substantially lowering `n_pred` without harming `tp`. `point_f1` will remain relatively flat as point attribution rules have not changed.

```predictions
[
  {"metric": "tp", "direction": "up", "from": 163, "to_approx": 215},
  {"metric": "n_pred", "direction": "down", "from": 518, "to_approx": 450},
  {"metric": "invented", "direction": "down", "from": 259, "to_approx": 160},
  {"metric": "missed", "direction": "down", "from": 291, "to_approx": 220},
  {"metric": "headline_f1", "direction": "up", "from": 0.305, "to_approx": 0.395},
  {"metric": "point_f1", "direction": "flat", "from": 0.222, "to_approx": 0.222}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~215     down 163 -> 148     X     X
n_pred                          down to ~450     down 518 -> 479    OK    OK
invented                        down to ~160     down 259 -> 233    OK     X
missed                          down to ~220     flat 291 -> 304     X     X
headline_f1                     up to ~0.395 flat 0.305 -> 0.288     X     X
point_f1                      flat to ~0.222   up 0.222 -> 0.297     X     X

direction 2/6   magnitude 1/6
```

headline_f1 0.305 -> 0.288   (-0.018)
n_pred 518 -> 479   missed 291 -> 304   invented 259 -> 233
pipeline: $1.82, 0 cached, 0 failed

## VERDICT
Wrong. I predicted that removing the strict sequencing rules and adding a semantic filter ("ignore the background", "focus on the foreground") would restore True Positives and cleanly strip away the hallucinated background matches. Instead, True Positives dropped even further (163 -> 148), missed events went up (291 -> 304), and headline_f1 fell to 0.288. 

The numbers show that this semantic filter was highly destructive. Why? In a fixed camera angle, the far side of the main court is physically higher in the frame and visually smaller, which models routinely conflate with "background". By aggressively instructing the model to ignore the "background" and focus ONLY on the "foreground court", it is highly likely the model simply ignored the team on the far side of the net, shedding dozens of valid events. This mimics the exact recall failure we saw with the physical crop in Iteration 1. 

The only bright spot was `point_f1` moving against my prediction (up to 0.297), suggesting that when the model actually retained an event, its ability to identify the rally-ending touch was quite accurate. But the recall cost is unacceptable. 

This change made things worse. We have now proven that attempting to erase the adjacent matches by either physically cropping the frame (which hides the ball) or semantically filtering by "foreground" (which hides the far-side team) both fail. The right move is to revert to a clean prompt without these spatial or sequential blinders, and instead filter by the location of the *player* (whose feet are always lower in the frame) rather than the court as a whole.
