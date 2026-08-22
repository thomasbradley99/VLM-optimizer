# Iteration 2

## CONJECTURE
The high number of action confusion errors (97 action errors) and phantom predictions (298 invented) stems from a DEFINITIONAL mismatch. The current prompt explicitly forbids the model from naming volleyball actions ("Do NOT name any volleyball actions") and asks for non-contact observations like "ball HITS THE FLOOR" or "goes UP". However, the response schema strictly requires one of seven specific event types (serve, receive, dig, set, attack, kill, block). This conflict forces the model to guess the enum values and causes downstream logic to incorrectly map non-contact descriptions to player events, generating both massive misclassification (e.g., 73 real attacks scattered across 6 predicted types) and phantom timing ghosts.

## CHANGE
Change the prompt to directly request the seven required event types and provide explicit definitions for each (matching the scout's rules), completely removing the instruction that banned naming actions.

```config
{"lever": "prompt",
 "prompt": "You are an expert volleyball scout watching a video clip from one fixed camera.\nA net runs vertically up the middle of the frame, dividing it into a left court and a right court.\nOnly the foreground court matters (the one with the referee on the raised stand).\n\nLog every ball contact made by a player in the foreground match. Ignore dead time between rallies.\nFor each contact, report the exact time in seconds from the start of this clip, which side of the net the player is on (left or right), and the exact event type from this list:\n- serve: a player starts the rally by hitting the ball over the net.\n- receive: the first contact returning a serve.\n- dig: the first contact defending against an opponent's attack.\n- set: an intermediate contact (usually the team's second) that sets up an attack.\n- attack: any ball intentionally hit across the net (other than a serve).\n- kill: an attack that immediately scores a point.\n- block: a player at the net intercepts the ball coming from the opponent.\n\nThis clip begins at {start} seconds into the match.",
 "chunk_len": 10.0, "overlap": 3.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect this definitional fix to significantly reduce action misclassification (boosting TP as events now match timing and type) and to drastically cut phantom predictions because the model will no longer report non-contact moments (like the ball hitting the floor). The number of missed events should remain mostly flat, as this does not change the physical perception (fps/crop) of the clip.

```predictions
[
 {"metric": "tp", "direction": "up", "from": 191, "to_approx": 240},
 {"metric": "n_pred", "direction": "down", "from": 582, "to_approx": 450},
 {"metric": "invented", "direction": "down", "from": 298, "to_approx": 150},
 {"metric": "set_pred_count", "direction": "down", "from": 112, "to_approx": 60},
 {"metric": "missed", "direction": "flat", "from": 266, "to_approx": 266}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~240      down 191 -> 47     X     X
n_pred                          down to ~450     down 582 -> 244    OK     X
invented                        down to ~150     down 298 -> 153    OK    OK
set_pred_count                   down to ~60      down 112 -> 49    OK    OK
missed                          flat to ~266       up 266 -> 459     X     X

direction 3/5   magnitude 2/5
```

headline_f1 0.337 -> 0.118   (-0.219)
n_pred 582 -> 244   missed 266 -> 459   invented 298 -> 153
pipeline: $2.16, 0 cached, 0 failed

## VERDICT
Right about the mechanism reducing hallucinations, completely wrong about it boosting true positives. The numbers show that forcing strict semantic definitions successfully halved phantom predictions (298 to 153) and overall predictions (582 to 244), but caused a catastrophic recall collapse where TP plummeted to 47 and missed events spiked to 459. The vision model cannot accurately classify complex volleyball terminology (like "dig" vs. "receive") directly from raw frames; stripping its ability to describe physical motions blindfolded its detection capabilities. This change made things significantly worse. The correct move is to go back to an earlier configuration (Iteration 0 or 1) and attack the physical video parameters rather than fighting prompt semantics.
