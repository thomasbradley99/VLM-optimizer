# Iteration 1

## CONJECTURE
The model is generating 430 `invented` ghost events, including 174 phantom serves. Tellingly, 62 of these phantom serves happen *inside* a live rally on the main court, and 112 occur during dead time. This is a perception issue: the instructions note that the uncropped video includes "three other matches in progress" in the upper half of the frame. The model is correctly identifying serves, attacks, and digs, but it is watching the wrong courts and attributing background match events to our timeline. By cropping out everything above the main court, we will blind the model to these adjacent games. This should drastically cut `n_pred` and `invented` without sacrificing our `tp` on the main court.

## CHANGE
I am setting the `crop` parameter to "1920:620:0:330" to isolate the main court and eliminate false positives originating from the background matches.

```config
{"lever": "crop",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\n\nList ball contacts you see DURING LIVE PLAY ONLY. Ignore all dead-time contacts (e.g., players bouncing or passing the ball between rallies).\n\nRules for types:\n- serve: The hit from behind the baseline that starts a rally.\n- receive: ONLY the first contact returning a serve.\n- dig: A defensive pass saving an opponent's attack. (Do not report easy freeball passes).\n- set: ONLY report a 'set' if the subsequent attack results in a 'kill'. If it leads to a normal 'attack' or an error, DO NOT report the set.\n- attack: An offensive hit. If it goes out or into the net, set error=true.\n- kill: An offensive hit that immediately scores a point (hits the opponent's floor or is unplayable).\n- block: A defensive block at the net.\n\nFor each contact give:\n  t       - time of contact in absolute match seconds\n  type    - serve, receive, dig, set, attack, kill or block\n  side    - \"left\" or \"right\": which half of the frame the player is in\n  number  - jersey number as a string, or null\n  error   - true if the contact was a mistake\n  point   - true if the rally ended here",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
The model will stop reporting events from the other matches, leading to a steep drop in total predictions and invented events, particularly serves. Because we haven't changed how it perceives the main court, true positives and missed events will remain roughly the same, driving headline F1 significantly higher due to the reduced denominator.

```predictions
[{"metric": "invented", "direction": "down", "from": 430, "to_approx": 250},
 {"metric": "n_pred", "direction": "down", "from": 836, "to_approx": 600},
 {"metric": "serve_pred_count", "direction": "down", "from": 271, "to_approx": 150},
 {"metric": "tp", "direction": "flat", "from": 273, "to_approx": 273},
 {"metric": "missed", "direction": "flat", "from": 144, "to_approx": 144}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
invented                        down to ~250     down 430 -> 286    OK    OK
n_pred                          down to ~600     down 836 -> 657    OK    OK
serve_pred_count                down to ~150     down 271 -> 204    OK    OK
tp                              flat to ~273     down 273 -> 250     X     X
missed                          flat to ~144       up 144 -> 179     X     X

direction 3/5   magnitude 3/5
```

headline_f1 0.394 -> 0.414   (+0.020)
n_pred 836 -> 657   missed 144 -> 179   invented 430 -> 286
pipeline: $2.78, 0 cached, 0 failed

## VERDICT
Right about the mechanism, wrong about the size. The crop worked exactly as intended to blind the model to background matches: `invented` fell by a massive 144 events (430 -> 286) and phantom serves dropped by 67. This drove a solid gain in headline F1. However, I incorrectly predicted that true positives would remain flat. Instead, `tp` fell from 273 to 250, and `missed` rose accordingly. 

The likely reason for the dropped true positives is that by cutting the top 330 pixels off the video frame (`y=330`), we clipped the airspace above the main court. Volleyball is an aerial game; when a ball goes high into the air during a dig, receive, or set, it exits our new cropped frame, causing the model to lose track of the play and miss the contact. 

Because the precision gains outweighed the recall losses, we will keep the current pipeline state rather than reverting. However, instead of immediately tweaking the crop geometry, the right move is to pivot back to the prompt text. We are still carrying the outcome-dependent definition of "set" from Iteration 0, which we already know is actively sabotaging recall. Fixing that definition is the highest-ROI next move.
