# Iteration 26

## CONJECTURE
The model is systematically predicting serves 1-2 seconds before they actually happen (e.g., 20:56 GHOST, 20:57 MISS; 24:07 GHOST, 24:08 MISS). This is a definitional mismatch: the model considers the ball toss to be a valid physical contact and logs it as the `serve` event, which falls outside the greedy 1.0s matching window for the actual hit, resulting in both a GHOST and a MISS. Additionally, the model is misattributing the team `side` for serves (causing 53 team errors and a huge score margin error) because "left side of the net" is ambiguous when a player is far behind the baseline. This is a perception issue that can be solved by grounding the spatial rule entirely in the 2D screen topology.

## CHANGE
I am explicitly vetoing the serve toss in the prompt ("DO NOT log the ball toss as a contact") so the model waits for the actual hit, and I am rewriting the `side` definition to strictly use the left/right "side of the screen" to prevent perspective confusion during deep serves and kills.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: Analyze ONLY the main court in the foreground. Ignore background matches completely.\n\nThe vertical net divides the screen into a left court and a right court. For the `side` field, output 'left' if the player making contact is physically on the left side of the screen, and 'right' if they are on the right side of the screen. Log the side where the player IS, not where the ball goes.\n\nThis clip begins at {start:.2f} seconds and runs for 6 seconds.\nWARNING: Clips often start MID-RALLY. The first contact you see might be a receive or dig. DO NOT assume it is a serve just because it is early in the clip.\n\nMUTUALLY EXCLUSIVE EVENTS (ONE PER CONTACT):\nOutput EXACTLY ONE event type per physical ball contact. Choose the single best fit.\n- If an attack wins the rally, label it ONLY as `kill`.\n- If a block wins the point, label it ONLY as `block`.\n\nACTION DEFINITIONS:\nYou MUST skip regular passes and dead-time contacts. Only report the pivotal actions defined below:\n  serve   - Initiates the rally. Hit from behind the baseline. DO NOT log the ball toss as a contact! The serve ONLY occurs at the exact moment the server strikes the ball over the net. (Back-row hits during play are attacks, NEVER serves).\n  receive - The FIRST defensive pass handling the opponent's serve. ONLY occurs once per rally. Do not use for passes mid-rally.\n  dig     - A defensive pass handling an opponent's hard attack. Usually a low-to-the-ground reaction. Do not report easy passes defending a slow free-ball.\n  set     - An assist. ONLY report if it directly sets up a point-winning kill. SKIP ALL OTHER SETS.\n  attack  - An offensive action (usually a jump and swing) intentionally directing the ball over the net. (A defensive pass that accidentally goes over is NOT an attack).\n  kill    - An attack that immediately wins the rally (lands in or is blocked out).\n  block   - A net defense. ONLY report if it immediately scores a point (a stuff block to the floor).\n\nDEAD TIME VETO: Ignore practice hits, practice serves, and post-rally bounces. Contacts after the ball hits the floor are NEVER valid events! A serve is ONLY real if the receiving team is fully in a ready defensive formation.\n\nFor each contact give:\n  t       - the EXACT moment of physical impact in ABSOLUTE MATCH SECONDS ({start:.2f} + offset). Estimate the offset carefully to one decimal place (e.g. 2.3). Deduplication relies on precise timing!\n  type    - one of the seven above\n  side    - \"left\" or \"right\" (where the player made contact)\n  number  - the contacting player's jersey number as a string, or null if unreadable. Do not guess.\n  error   - true if this contact was a direct error (hit into the net, out of bounds)\n  point   - true ONLY for the final contact if it directly WON the point for the team that made the contact (like a kill). NEVER true for regular passes or errors!\n\nReturn an empty list if no valid play happens.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By ignoring the toss, the model will shift its serve timestamps forward to match the ground truth, converting MISS/GHOST pairs directly into True Positives. This will sharply drop `serve_pred_count` and overall `n_pred`, while driving `tp` up. The screen-based team definition will reduce side-swapping, lifting `team_acc`. The `set` F1 should remain flat as its rule was untouched.

```predictions
[{"metric": "serve_pred_count", "direction": "down", "from": 174, "to_approx": 130},
 {"metric": "tp", "direction": "up", "from": 281, "to_approx": 305},
 {"metric": "n_pred", "direction": "down", "from": 671, "to_approx": 610},
 {"metric": "missed", "direction": "down", "from": 155, "to_approx": 130},
 {"metric": "set_f1", "direction": "flat", "from": 0.239, "to_approx": 0.239}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                down to ~130     flat 174 -> 174     X     X
tp                                up to ~305     flat 281 -> 267     X     X
n_pred                          down to ~610     flat 671 -> 664     X     X
missed                          down to ~130       up 155 -> 170     X     X
set_f1                        flat to ~0.239  flat 0.37 -> 0.387    OK     X

direction 1/5   magnitude 0/5
```

headline_f1 0.460 -> 0.440   (-0.020)
n_pred 671 -> 664   missed 155 -> 170   invented 276 -> 284
pipeline: $3.04, 0 cached, 0 failed

## VERDICT
Wrong. 

I predicted that explicitly forbidding the model from logging the serve toss would shift its timestamps forward, converting MISS/GHOST pairs into True Positives and dropping overall serve predictions. Instead, serve predictions remained completely flat (174 -> 174), True Positives dropped from 281 to 267, and missed events climbed from 155 to 170. 

This confirms yet again that the model cannot process negative visual constraints. Screaming "DO NOT log the ball toss" at it acts as a "Pink Elephant" veto; it doesn't fix the timing issue, and the added noise in the prompt degraded its overall recall. Furthermore, the attempt to strictly enforce team `side` based on the left/right geometry of the screen likely backfired because the camera is not perfectly centered, causing the model to drop or misattribute events when players drift near the middle.

The right move is to abandon negative vetoes in the prompt, go back to the previous stable prompt, and attack the hallucination issue mechanically via the pipeline's overlap settings.
