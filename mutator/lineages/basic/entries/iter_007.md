# Iteration 7

## CONJECTURE
The model is systematically breaking rally sequences when it misses a serve or when a clip starts mid-rally. Because it assumes the first contact it sees in a sequence is the start of a rally, it misclassifies subsequent hits. This is a contextual/definitional error. The evidence is overwhelming: 36 real receives and 10 real attacks were misclassified as serves, and 25 attacks were called receives. The cascade is visible in the logs (e.g., at 60:44 a serve is MISSED, and the immediate receive at 60:45 is mislabeled as a "serve"; at 22:31-22:35 the model offsets an entire 4-touch rally, calling a receive a serve, and an attack a receive). By explicitly warning the model not to assume the first contact is a serve and to classify strictly based on the physical action (baseline hit vs. court bump), we can stop this misclassification cascade. We also revert the complex spatial filtering that blinded the model and cost us 50+ True Positives in the last round.

## CHANGE
Rewrite the prompt to explicitly warn the model against sequence-assumption cascades, defining a serve strictly by physical location rather than sequence order, and remove the destructive geometric "bottom 3/4" rules to restore raw perception.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\n\nCRITICAL INSTRUCTION: Clips may start mid-rally, or you might miss the actual serve. DO NOT assume the first contact you see is a serve. A 'serve' must strictly be a hit from behind the baseline. If the first contact you see is a player bumping, setting, or spiking on the court, label it correctly (e.g., receive, dig, or attack) based on the physical action, not its order in the clip.\n\nFocus ONLY on the main match taking place on the primary court. Ignore other matches in the background.\n\nFor each event give:\n  t       - the precise time the player physically strikes the ball\n  type    - must be one of:\n            serve: the initial hit from behind the baseline that starts a rally\n            receive: the first contact defending a serve\n            dig: the first contact defending an attack\n            set: an assist pass that directly leads to a kill\n            attack: any hit sent over the net to the opponent's side that does not score a point\n            kill: an attack that directly scores a point and ends the rally\n            block: deflecting an attack at the net\n  side    - \"left\" or \"right\": which side of the net the player making contact is physically on\n  number  - the player's jersey number as a string, or null if you cannot read it\n  error   - true if the touch was a mistake\n  point   - true if the rally ended here and a point was scored\n\nOnly report touches that fit these specific definitions during a LIVE RALLY. Ignore all dead-time passing, bouncing, celebrations, and pre-match warm-ups.",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
The model will stop aggressively labeling mid-rally contacts as serves, sharply increasing `receive_precision`. By removing the blinding geometric filter, overall perception will recover, raising True Positives and overall F1.

```predictions
[{"metric": "receive_precision", "direction": "up", "from": 0.132, "to_approx": 0.220},
 {"metric": "serve_pred_count", "direction": "down", "from": 126, "to_approx": 105},
 {"metric": "tp", "direction": "up", "from": 167, "to_approx": 200},
 {"metric": "n_pred", "direction": "up", "from": 514, "to_approx": 560},
 {"metric": "block_pred_count", "direction": "flat", "from": 15, "to_approx": 15}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
receive_precision                up to ~0.22    up 0.16 -> 0.208    OK    OK
serve_pred_count                down to ~105     flat 126 -> 120     X     X
tp                                up to ~200     down 167 -> 150     X     X
n_pred                            up to ~560     down 514 -> 460     X     X
block_pred_count                 flat to ~15        down 15 -> 8     X     X

direction 1/5   magnitude 1/5
```

headline_f1 0.314 -> 0.297   (-0.017)
n_pred 514 -> 460   missed 254 -> 301   invented 218 -> 211
pipeline: $1.87, 0 cached, 0 failed

## VERDICT
Right about the mechanism for receive precision, but completely wrong about the overall impact on perception and recall. 

The explicit warning to stop assuming the first contact is a serve worked exactly as intended for `receive_precision`, pulling it up from 0.160 to 0.208. However, predicting that removing the previous round's geometric filters would cause True Positives to recover to ~200 was dead wrong. Instead, `tp` fell even further to 150, overall predictions plummeted (514 -> 460), and missed events spiked (254 -> 301). 

The change made things worse because it stripped the model of a vital heuristic. By instructing the model to classify strictly based on isolated "physical action, not its order in the clip," we accidentally disabled its ability to use sequential context to identify blurry or ambiguous touches. It turns out the sequence assumption wasn't just causing cascades; it was acting as a necessary crutch for the model's raw perception. Without chronological expectations to guide it, the model became deeply hesitant and simply skipped events it couldn't perfectly see.

The right move is to abandon this line entirely, revert to the pre-Iteration 6 configuration (where True Positives were much higher), and attack the background-court noise from a completely different angle.
