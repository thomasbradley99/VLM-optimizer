# Iteration 5

## CONJECTURE
The model is severely misclassifying deep-court `receive` events and mid-rally contacts as `serve`. The numbers show `serve` is predicted 144 times against 118 real events, and the confusion matrix reveals it is absorbing 42 `receive`s and 11 `attack`s, plus generating 38 in-rally ghosts. This is a definitional mismatch: the model is seeing a deep court contact and labeling it "serve" based purely on spatial location behind the line, ignoring the causal sequence of the rally.

## CHANGE
I am adding kinematic cues (the toss) and sequence rules (arriving from over the net) to the definitions of `serve` and `receive`, along with a specific critical rule explicitly prohibiting the confusion of deep receives with serves, to force the model to use causal sequence rather than just spatial location.

```config
{"lever": "prompt",
 "prompt": "You are an expert volleyball statistician scouting one match from a fixed camera.\n\nCONTEXT. Several courts are in use at once. Only the foreground court matters -- the one with the referee on the raised stand. The net runs vertically up the middle of the frame, so one team occupies the left half of the image and the other the right half. Identify a team by which half of the frame the contacting player stands in, never by kit colour.\n\nThis clip begins at {start} seconds into the match.\n\nTAXONOMY. Every contact belongs to exactly one of seven classes. Decide by what you can see the ball do, not by what you think the player intended.\n\n  serve    starts the rally. A player stands behind the baseline, tosses the ball, and hits it OVER the net. If the ball is already in play, it is NOT a serve.\n  receive  the immediate response to a serve. The ball arrives from over the net and is passed to a TEAMMATE.\n  dig      the response to an opponent's attack. The ball arrives from over the net and is passed to a TEAMMATE.\n  set      a contact that places the ball for a team-mate to attack, BUT ONLY report it if the resulting attack is a kill (an assist).\n  attack   any contact mid-rally that sends the ball OVER the net to the opponents.\n  kill     an attack that ends the rally immediately.\n  block    a contact made at the net by a player with hands above it.\n\nCRITICAL RULES:\n1. TRAJECTORY: Serves and attacks MUST cross the net. Receives and digs MUST stay on their own side.\n2. NO DEAD TIME: Ignore players bouncing or tossing the ball before a serve. Only report live rally contacts.\n3. SERVE VS RECEIVE: A serve initiates the ball entering the opponent's side. A receive is when the opponent passes that serve to a teammate. Never confuse a deep court receive for a serve.\n4. EXACTLY ONE LABEL: Never output multiple rows for the same contact or timestamp.\n\nREPORTING. Give one row per contact you actually observe:\n  t        time of contact in absolute match seconds, to a fraction of a second\n  type     one of the seven above\n  side     \"left\" or \"right\", the half of the frame the contacting player is in\n  number   the jersey number as a string, or null if you cannot read it\n  error    true if the contact was a mistake -- into the net, out of bounds, mishandled\n  point    true ONLY if the team making THIS contact won the rally. If this contact is an error that loses the rally, point MUST be false.\n\nIf nothing happens in this clip, return an empty list.",
 "chunk_len": 15.0, "overlap": 4.0, "fps": 10, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect the massive over-prediction of serves to collapse because the "toss" requirement and Rule 3 will reject mid-rally defensive passes. This will shift the 42 misclassified `receive` events back to their correct label, raising `receive` recall and count. Overall true positives and headline F1 should rise as the correct labels are matched.

```predictions
[{"metric": "serve_pred_count", "direction": "down", "from": 144, "to_approx": 95},
 {"metric": "receive_pred_count", "direction": "up", "from": 92, "to_approx": 125},
 {"metric": "tp", "direction": "up", "from": 187, "to_approx": 215},
 {"metric": "headline_f1", "direction": "up", "from": 0.366, "to_approx": 0.395},
 {"metric": "set_f1", "direction": "flat", "from": 0.253, "to_approx": 0.253}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                 down to ~95     down 144 -> 129    OK     X
receive_pred_count                up to ~125       flat 92 -> 96     X     X
tp                                up to ~215     flat 187 -> 186     X     X
headline_f1                     up to ~0.395 flat 0.366 -> 0.363     X     X
set_f1                        flat to ~0.253  down 0.38 -> 0.357     X     X

direction 1/5   magnitude 0/5
```

headline_f1 0.366 -> 0.363   (-0.002)
n_pred 473 -> 474   missed 251 -> 256   invented 174 -> 180
pipeline: $3.21, 0 cached, 0 failed

## VERDICT
Right about the mechanism for serve reduction, but entirely wrong about the size and downstream effects. 

The numbers show that explicitly requiring a toss and forbidding deep-receive confusion did suppress `serve` predictions (144 -> 129), but it completely failed to reallocate those contacts to `receive` (which barely moved, 92 -> 96). Consequently, true positives and headline F1 stayed flat, and the model continued to invent 180 ghost contacts. 

This change failed because I applied complex logical sequence rules ("If the ball is already in play, it is NOT a serve") while leaving the framerate at 10 fps. We already established in the previous iteration that 150 frames per chunk causes severe attention dilution. When the model is visually overwhelmed, adding strict text-based causal constraints just causes it to miss contacts entirely or hallucinate rather than correctly reclassify them. 

The right move is to revert to 5 fps immediately to restore our baseline recall, abandon strict logical sequence or trajectory rules, and instead define the taxonomy purely by gross player posture and court position, which the vision model can actually see.
