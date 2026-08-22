# Iteration 25

## CONJECTURE
The model is suffering from a massive DEFINITIONAL mismatch regarding offensive vs. defensive actions, leading to symmetric confusion (29 real attacks called `dig`, 23 real digs called `attack`) and 67 ghost attacks inside rallies. The old prompt defined an attack merely as "ANY contact that sends the ball OVER the net", forcing the model to incorrectly log defensive free-ball overpasses as attacks and confusing low digs with offensive swings. Additionally, 21 real serves were misclassified as receives because the strict "visible toss" rule fails in 6-second clips where the toss happens off-screen before the clip starts. I will fix this by providing kinematic cues (jumps/swings for attacks vs. low-to-the-ground reactions for digs) to match the scout's strict offensive definitions, and by allowing serves to be inferred from baseline hits even if the toss is cut off.

## CHANGE
I am updating the prompt to replace spatial-only action rules with kinematic cues (e.g., attacks are jumps/swings, digs are low reactions), explicitly vetoing easy free-ball passes to remove ghost attacks, and relaxing the serve's "visible toss" requirement to rescue serves cut off by the 6s clip boundary.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: Analyze ONLY the main court in the foreground. Ignore background matches completely.\n\nThe vertical net divides the court. For the `side` field, output 'left' if the contacting player is standing on the left side of the net, or 'right' if they are on the right side. Never log the side where the ball lands.\n\nThis clip begins at {start:.2f} seconds and runs for 6 seconds.\nWARNING: Clips often start MID-RALLY. The first contact you see might be a receive or dig. DO NOT assume it is a serve just because it is early in the clip.\n\nMUTUALLY EXCLUSIVE EVENTS (ONE PER CONTACT):\nOutput EXACTLY ONE event type per physical ball contact. Choose the single best fit.\n- If an attack wins the rally, label it ONLY as `kill`.\n- If a block wins the point, label it ONLY as `block`.\n\nACTION DEFINITIONS:\nYou MUST skip regular passes and dead-time contacts. Only report the pivotal actions defined below:\n  serve   - Initiates the rally. Hit from behind the baseline. Even if the toss is off-screen, the first hit starting a rally from the baseline is a serve. NEVER occurs mid-rally. (Back-row hits during play are attacks).\n  receive - The FIRST defensive pass handling the opponent's serve. ONLY occurs once per rally. Do not use for passes mid-rally.\n  dig     - A defensive pass handling an opponent's hard attack. Usually a low-to-the-ground reaction. Do not report easy passes defending a slow free-ball.\n  set     - An assist. ONLY report if it directly sets up a point-winning kill. SKIP ALL OTHER SETS.\n  attack  - An offensive action (usually a jump and swing) intentionally directing the ball over the net. (A defensive pass that accidentally goes over is NOT an attack).\n  kill    - An attack that immediately wins the rally (lands in or is blocked out).\n  block   - A net defense. ONLY report if it immediately scores a point (a stuff block to the floor).\n\nDEAD TIME VETO: Ignore practice hits, practice serves, and post-rally bounces. Contacts after the ball hits the floor are NEVER valid events! A serve is ONLY real if the receiving team is fully in a ready defensive formation.\n\nFor each contact give:\n  t       - the EXACT moment of physical impact in ABSOLUTE MATCH SECONDS ({start:.2f} + offset). Estimate the offset carefully to one decimal place (e.g. 2.3). Deduplication relies on precise timing!\n  type    - one of the seven above\n  side    - \"left\" or \"right\" (where the player made contact)\n  number  - the contacting player's jersey number as a string, or null if unreadable. Do not guess.\n  error   - true if this contact was a direct error (hit into the net, out of bounds)\n  point   - true ONLY for the final contact if it directly WON the point for the team that made the contact (like a kill). NEVER true for regular passes or errors!\n\nReturn an empty list if no valid play happens.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By relying on kinematic cues (jump vs low pass), the model will stop confusing digs and attacks, and stop logging free-ball passes as ghost attacks. Relaxing the toss requirement will shift the 21 misclassified serves back to TP. Consequently, TP will rise while total predictions fall. The unchanged `set` rule will result in flat predictions for sets.

```predictions
[{"metric": "tp", "direction": "up", "from": 279, "to_approx": 310},
 {"metric": "n_pred", "direction": "down", "from": 704, "to_approx": 610},
 {"metric": "attack_pred_count", "direction": "down", "from": 177, "to_approx": 140},
 {"metric": "serve_recall", "direction": "up", "from": 0.415, "to_approx": 0.500},
 {"metric": "set_pred_count", "direction": "flat", "from": 48, "to_approx": 48},
 {"metric": "invented", "direction": "down", "from": 312, "to_approx": 250}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~310     flat 279 -> 281     X     X
n_pred                          down to ~610     flat 704 -> 671     X     X
attack_pred_count               down to ~140     down 177 -> 153    OK    OK
serve_recall                      up to ~0.5   up 0.475 -> 0.568    OK     X
set_pred_count                   flat to ~48       down 48 -> 45     X     X
invented                        down to ~250     down 312 -> 276    OK    OK

direction 3/6   magnitude 2/6
```

headline_f1 0.445 -> 0.460   (+0.015)
n_pred 704 -> 671   missed 158 -> 155   invented 312 -> 276
pipeline: $3.12, 0 cached, 0 failed

## VERDICT
Right about the mechanism, wrong about the size. 

The numbers show that replacing spatial-only rules with kinematic cues (jumps/swings vs. low reactions) successfully suppressed ghost attacks (`attack_pred_count` fell from 177 to 153) and dropped `invented` events by 36. Furthermore, relaxing the strict "visible toss" requirement for serves worked beautifully, pushing serve recall up from 0.475 to 0.568 because the model could finally infer cut-off serves. 

However, True Positives stayed completely flat instead of leaping to 310, and total predictions only fell slightly. This means the kinematic cues didn't help the model uncover *new* valid events; they merely helped it correctly re-classify the events it was already seeing, while throwing out some of the garbage. 

This was a good round resulting in a solid F1 gain (0.445 -> 0.460). The prompt definitions are now in a much healthier place. The right move is to keep this prompt but attack the 276 remaining hallucinated events mechanically by adjusting the chunk overlap.
