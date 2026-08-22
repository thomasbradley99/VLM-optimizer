# Iteration 4

## CONJECTURE
The model is failing to identify fast actions because at 5 frames per second, the ball's trajectory is often lost between frames. This perception deficit directly conflicts with the strict trajectory rules added in the last round. At 5 fps, the model frequently misses the initial serve entirely, leading it to mistakenly classify the subsequent receive as a serve (the confusion matrix shows 46 real receives misclassified as serves). This inflates `serve` predictions (167 vs 118 real). Fast attacks are also a blur, causing 45 real attacks to be missed completely and resulting in a terrible `attack` recall of 0.206. Doubling the framerate to 10 fps gives the model the temporal resolution it needs to track the ball across the net, which should fix this perception gap without needing to weaken the prompt rules.

## CHANGE
I am increasing the framerate from 5 fps to 10 fps to give the model the temporal evidence required by the strict trajectory rules, leaving the prompt exactly as it is.

```config
{"lever": "fps",
 "prompt": "You are an expert volleyball statistician scouting one match from a fixed camera.\n\nCONTEXT. Several courts are in use at once. Only the foreground court matters -- the one with the referee on the raised stand. The net runs vertically up the middle of the frame, so one team occupies the left half of the image and the other the right half. Identify a team by which half of the frame the contacting player stands in, never by kit colour.\n\nThis clip begins at {start} seconds into the match.\n\nTAXONOMY. Every contact belongs to exactly one of seven classes. Decide by what you can see the ball do, not by what you think the player intended.\n\n  serve    the single contact that begins a rally. Struck from behind the back line, sending the ball OVER the net. Never report a serve mid-rally.\n  receive  the first defensive contact answering a serve. The ball is passed to a TEAMMATE on the SAME side. Maximum one per rally.\n  dig      a defensive contact answering an attack. The ball is passed to a TEAMMATE on the SAME side.\n  set      a contact that places the ball for a team-mate to attack, BUT ONLY report it if the resulting attack is a kill (an assist).\n  attack   any contact that sends the ball OVER the net to the opponents.\n  kill     an attack that ends the rally immediately.\n  block    a contact made at the net by a player with hands above it.\n\nCRITICAL RULES:\n1. TRAJECTORY: Serves and attacks MUST cross the net. Receives and digs MUST stay on their own side.\n2. NO DEAD TIME: Ignore players bouncing or tossing the ball before a serve. Only report live rally contacts.\n3. EXACTLY ONE LABEL: Never output multiple rows for the same contact or timestamp. If an attack and block happen simultaneously, report the attack.\n\nREPORTING. Give one row per contact you actually observe:\n  t        time of contact in absolute match seconds, to a fraction of a second\n  type     one of the seven above\n  side     \"left\" or \"right\", the half of the frame the contacting player is in\n  number   the jersey number as a string, or null if you cannot read it\n  error    true if the contact was a mistake -- into the net, out of bounds, mishandled\n  point    true ONLY if the team making THIS contact won the rally. If this contact is an error that loses the rally, point MUST be false.\n\nIf nothing happens in this clip, return an empty list.",
 "chunk_len": 15.0,
 "overlap": 4.0,
 "fps": 10,
 "width": 640,
 "crop": "1920:620:0:330",
 "media_resolution": null,
 "model": "gemini-3.7-flash",
 "thinking": "low"}
```

## PREDICTION
I expect true positives to rise as the model successfully detects fast events that were previously invisible. Attack recall will rise because the trajectory across the net can now be visually confirmed. Serve over-prediction will drop as the model starts spotting the actual serve and correctly labels the following contact as a receive, rather than mislabeling the receive as the start of the rally. Set F1 will remain flat, as sets are slower, high-arcing passes that were already visible at 5 fps.

```predictions
[{"metric": "tp", "direction": "up", "from": 223, "to_approx": 250},
 {"metric": "attack_recall", "direction": "up", "from": 0.206, "to_approx": 0.300},
 {"metric": "serve_pred_count", "direction": "down", "from": 167, "to_approx": 135},
 {"metric": "set_f1", "direction": "flat", "from": 0.167, "to_approx": 0.167}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~250     down 223 -> 187     X     X
attack_recall                     up to ~0.3   up 0.321 -> 0.359    OK     X
serve_pred_count                down to ~135     down 167 -> 144    OK    OK
set_f1                        flat to ~0.167  flat 0.381 -> 0.38    OK     X

direction 3/4   magnitude 1/4
```

headline_f1 0.400 -> 0.366   (-0.035)
n_pred 564 -> 473   missed 208 -> 251   invented 222 -> 174
pipeline: $3.24, 0 cached, 0 failed

## VERDICT
I was right about the mechanism of serve reduction, but completely wrong about the overall impact on recall. The numbers show that increasing the framerate caused a general suppression of output: total predictions plummeted from 564 to 473, which dragged true positives down from 223 to 187 and increased missed events from 208 to 251. While serve over-prediction dropped and attack recall eked out a small gain, this was merely a side effect of the model predicting far fewer events overall, rather than a genuine improvement in precision. 

Feeding the model 150 frames per chunk (15s at 10 fps) overwhelmed its temporal attention. Instead of using the extra frames to track the ball's trajectory, the model became fatigued or conservative and skipped over dozens of valid contacts. The extra resolution did not solve the perception gap; it just diluted the model's focus. 

Because this change made things substantially worse (F1 dropped to 0.366), the right move is to abandon 10 fps. We should go back to the 5 fps configuration (75 frames per chunk) which gave us 223 true positives, and attack the misclassification problem by removing the strict ball trajectory rules and replacing them with heuristics based on player body mechanics, which the model can see clearly at 5 fps.
