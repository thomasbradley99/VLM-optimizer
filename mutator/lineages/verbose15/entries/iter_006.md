# Iteration 6

## CONJECTURE
The massive drop in True Positives (from 223 down to 186) and increase in missed events (up to 256) over the last two iterations was a perception failure caused by doubling the framerate to 10 fps, not by the prompt changes. At 15 seconds per chunk, 10 fps results in 150 frames per request. This dilutes the model's visual attention, overwhelming it and causing it to completely miss actions that are clearly visible at 5 fps. This visual overwhelm overpowered any definitional improvements we made in the prompt.

## CHANGE
I am decreasing the framerate back to 5 fps while leaving the prompt exactly as it is, to test whether the lower token count restores the model's ability to see contacts.

```config
{"lever": "fps",
 "prompt": "You are an expert volleyball statistician scouting one match from a fixed camera.\n\nCONTEXT. Several courts are in use at once. Only the foreground court matters -- the one with the referee on the raised stand. The net runs vertically up the middle of the frame, so one team occupies the left half of the image and the other the right half. Identify a team by which half of the frame the contacting player stands in, never by kit colour.\n\nThis clip begins at {start} seconds into the match.\n\nTAXONOMY. Every contact belongs to exactly one of seven classes. Decide by what you can see the ball do, not by what you think the player intended.\n\n  serve    starts the rally. A player stands behind the baseline, tosses the ball, and hits it OVER the net. If the ball is already in play, it is NOT a serve.\n  receive  the immediate response to a serve. The ball arrives from over the net and is passed to a TEAMMATE.\n  dig      the response to an opponent's attack. The ball arrives from over the net and is passed to a TEAMMATE.\n  set      a contact that places the ball for a team-mate to attack, BUT ONLY report it if the resulting attack is a kill (an assist).\n  attack   any contact mid-rally that sends the ball OVER the net to the opponents.\n  kill     an attack that ends the rally immediately.\n  block    a contact made at the net by a player with hands above it.\n\nCRITICAL RULES:\n1. TRAJECTORY: Serves and attacks MUST cross the net. Receives and digs MUST stay on their own side.\n2. NO DEAD TIME: Ignore players bouncing or tossing the ball before a serve. Only report live rally contacts.\n3. SERVE VS RECEIVE: A serve initiates the ball entering the opponent's side. A receive is when the opponent passes that serve to a teammate. Never confuse a deep court receive for a serve.\n4. EXACTLY ONE LABEL: Never output multiple rows for the same contact or timestamp.\n\nREPORTING. Give one row per contact you actually observe:\n  t        time of contact in absolute match seconds, to a fraction of a second\n  type     one of the seven above\n  side     \"left\" or \"right\", the half of the frame the contacting player is in\n  number   the jersey number as a string, or null if you cannot read it\n  error    true if the contact was a mistake -- into the net, out of bounds, mishandled\n  point    true ONLY if the team making THIS contact won the rally. If this contact is an error that loses the rally, point MUST be false.\n\nIf nothing happens in this clip, return an empty list.",
 "chunk_len": 15.0, "overlap": 4.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
True positives will increase substantially as the model's perception recovers, drawing the missed count back down near 200. F1 will correspondingly increase. Block precision and count will remain relatively unchanged as they are inherently hard to see.

```predictions
[{"metric": "tp", "direction": "up", "from": 186, "to_approx": 220},
 {"metric": "missed", "direction": "down", "from": 256, "to_approx": 210},
 {"metric": "headline_f1", "direction": "up", "from": 0.363, "to_approx": 0.395},
 {"metric": "n_pred", "direction": "up", "from": 474, "to_approx": 540},
 {"metric": "block_pred_count", "direction": "flat", "from": 14, "to_approx": 14}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~220       up 186 -> 231    OK    OK
missed                          down to ~210     down 256 -> 193    OK    OK
headline_f1                     up to ~0.395   up 0.363 -> 0.414    OK    OK
n_pred                            up to ~540       up 474 -> 566    OK    OK
block_pred_count                 flat to ~14        down 14 -> 9     X     X

direction 4/5   magnitude 4/5
```

headline_f1 0.363 -> 0.414   (+0.051)
n_pred 474 -> 566   missed 256 -> 193   invented 180 -> 209
pipeline: $1.96, 0 cached, 0 failed

## VERDICT
Right. The lower framerate (5 fps) restored the model's perception, driving True Positives from 186 back up to 231 and dropping missed events from 256 to 193. Headline F1 recovered to 0.414, fully validating the hypothesis that 150 frames per chunk was overwhelming the model's visual attention.

We predicted blocks would stay flat, but they dropped from 14 to 9. This just reinforces that blocking is difficult to see and inherently noisy, especially at lower framerates where the exact moment of net contact might fall between frames. However, the massive gain in overall recall and F1 proves that 75 frames (5 fps * 15s) is currently the sweet spot for this pipeline.

The right move now is to keep this 5 fps/15s configuration and shift back to prompt engineering. Specifically, since we know the model struggles to track the ball's exact trajectory or maintain a strict temporal sequence (like "starts the rally"), we should redefine the actions based on the one thing it can see clearly: player positioning and body mechanics.
