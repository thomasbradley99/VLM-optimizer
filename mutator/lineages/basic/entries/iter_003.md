# Iteration 3

## CONJECTURE
The model is drastically over-reporting events during live play, causing 202 of its 250 "ghost" predictions to fall inside live rallies. This is a DEFINITIONAL mismatch: volleyball features 3 touches per side, but the scout's ground truth explicitly ignores the intermediate passes unless they are assists leading to a kill. Because the prompt does not strictly forbid reporting these intermediate touches, the model transcribes them, bloating `n_pred` (594 vs 550 real). Additionally, the confusion matrix shows 34 real receives misclassified as serves. The model is seeing the serve but timestamping it late—often at the exact moment the ball reaches the receiver—causing greedy matching to consume the receive and leave the real serve as a MISS.

## CHANGE
I am rewriting the prompt to explicitly define the 3-touch structure and command the model to ignore intermediate passes and dead-ball touches, while also clarifying that `t` must be the exact moment of physical contact to fix the serve timing.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\n\nList ONLY specific meaningful volleyball events in live play. Be extremely strict to avoid over-reporting.\n1. IGNORE all dead-ball touches, practice hits, and casual returns between points.\n2. In volleyball, a team typically touches the ball 3 times (defend -> pass -> attack). You MUST IGNORE the intermediate passes and normal sets. Only report the first defensive contact and the hit over the net.\n\nFor each event give:\n  t       - the precise time the player physically strikes the ball\n  type    - must be one of:\n            serve: the initial hit from the baseline that starts a rally\n            receive: the first contact defending a serve\n            dig: the first contact defending an attack\n            set: ONLY an assist that directly precedes a 'kill' (IGNORE ALL OTHER PASSES)\n            attack: an offensive hit sent over the net that does not score a point\n            kill: an attack that directly scores a point and ends the rally\n            block: deflecting an attack at the net\n  side    - \"left\" or \"right\": which half of the frame the player is standing in\n  number  - the player's jersey number as a string, or null if you cannot read it\n  error   - true if the touch was a mistake\n  point   - true if the rally ended here and a point was scored",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By defining the intermediate touches as non-events, the model will stop inventing phantom contacts in the middle of rallies, significantly dropping `n_pred` and `invented`. Furthermore, forcing the timestamp to be the exact moment of physical contact will stop serves from being timestamped at the moment of the receive, increasing True Positives and serve recall, thus raising Headline F1 from both the numerator and the denominator.

```predictions
[{"metric": "n_pred", "direction": "down", "from": 594, "to_approx": 480},
 {"metric": "invented", "direction": "down", "from": 260, "to_approx": 160},
 {"metric": "tp", "direction": "up", "from": 223, "to_approx": 235},
 {"metric": "serve_recall", "direction": "up", "from": 0.415, "to_approx": 0.480},
 {"metric": "headline_f1", "direction": "up", "from": 0.390, "to_approx": 0.430},
 {"metric": "block_f1", "direction": "flat", "from": 0.000, "to_approx": 0.000}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
n_pred                          down to ~480     flat 594 -> 583     X     X
invented                        down to ~160       up 260 -> 282     X     X
tp                                up to ~235     down 223 -> 174     X     X
serve_recall                     up to ~0.48  down 0.542 -> 0.39     X     X
headline_f1                      up to ~0.43  down 0.39 -> 0.307     X     X
block_f1                        flat to ~0.0      down 0.08 -> 0     X    OK

direction 0/6   magnitude 1/6
```

headline_f1 0.390 -> 0.307   (-0.083)
n_pred 594 -> 583   missed 216 -> 249   invented 260 -> 282
pipeline: $1.81, 0 cached, 0 failed

## VERDICT
I was completely wrong. Rather than fixing precision, instructing the model to ignore intermediate touches destroyed recall across the board, dropping Headline F1 from 0.390 to 0.307. 

The numbers show a total collapse in correct detections: True Positives plummeted from 223 to 174, and serve recall collapsed from 0.542 to 0.39. Most informatively, the `invented` metric moved in the exact opposite direction to my prediction, rising from 260 to 282. By ordering the model to mentally or textually skip the middle step of a volleyball 3-touch sequence (the set/pass), it lost the structural context needed to understand the rally. If the model ignores the set, a subsequent jump looks disconnected, leading it to hallucinate weird touches or misclassify attacks and digs, which explains why ghosts went up instead of down.

This change made things fundamentally worse because an action recognition model needs to track the full causal chain of a rally to correctly classify the start and end of it. It should NOT be reverted -- wait, the system prompt says "It will NOT be reverted -- the next round starts from where you just landed. Say whether you think the right move is to keep pushing this line, or to go back to an earlier configuration and attack from there." My mistake. I cannot revert the pipeline automatically, but my strategic move is to go back to the Iteration 2 configuration manually and attack the background courts issue. Pushing this "ignore intermediate touches" line is a dead end.
