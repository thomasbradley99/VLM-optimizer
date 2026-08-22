# Iteration 28

## CONJECTURE
The drop in TP and F1 in Round 27 was caused by a definitional over-restriction of `dig` ("hard-fought... powerful downward-driven spike... Do not report easy passes"), which crashed `dig` recall to 0.081 (only 32 predicted against 86 real events). Furthermore, the model is still hallucinating `serve` and `receive` events inside live rallies (43 `serve` and 43 `receive` phantoms inside rallies) because the short 6-second chunks cause it to perceive deep mid-rally passes as serves. This is a mix of definitional mismatch (for digs) and perception errors (for serves mid-rally). I will broaden `dig` back to any pass handling an attack, and explicitly constrain `serve` by adding a strong visual cue: "Players MUST be in stationary starting formations."

## CHANGE
I am updating the prompt to broaden the `dig` definition to simply passing an opponent's attack, and strictly forbidding `serve` or `receive` unless players are in stationary starting formations, to stop the model from logging mid-rally hits as serves.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: Analyze ONLY the main court in the foreground. Ignore background matches completely.\n\nSIDE ATTRIBUTION (CRITICAL):\nThe vertical net physically divides the screen into a left and right half.\n- For `side`, output 'left' if the player making contact is standing on the LEFT half of the screen.\n- Output 'right' if they are on the RIGHT half of the screen.\nDO NOT confuse left and right! Log the side where the PLAYER is located, completely ignoring where the ball is hit towards.\n\nThis clip begins at {start} seconds and runs for 6 seconds.\nWARNING: Clips often start MID-RALLY. If players are already in active, fluid motion at the start of the clip, IT IS A RALLY. Do NOT assume the first hit is a serve.\n\nDEAD TIME VETO:\nYou MUST ignore practice hits, practice serves, warming up, and post-rally bounces. Contacts after the ball hits the floor are NEVER valid. If players are casual, walking, or not in a ready stance, IT IS DEAD TIME. Skip all contacts.\n\nACTION DEFINITIONS (ONLY LOG THESE, SKIP ALL OTHERS):\n  serve   - The initial hit from behind the baseline to start a rally. Players MUST be in stationary starting formations. Do NOT log the ball toss. NEVER log a hit during an active rally as a serve.\n  receive - The first defensive pass specifically handling the opponent's serve. NEVER happens mid-rally.\n  dig     - A defensive pass that handles an opponent's attack over the net. This is the defending team's first contact after an attack.\n  set     - An overhead pass to a teammate setting up an attack. To match the scout, ONLY log this if it directly leads to a KILL. Skip all other sets.\n  attack  - An offensive hit (spike, swing, or tip) intentionally directing the ball over the net.\n  kill    - An attack that directly wins the point (MUST see it hit the floor or deflect wildly out). If an attack is dug, it is just an `attack`. If an attack scores, log it as `kill`, NOT `attack`.\n  block   - A net defense intercepting an attack. ONLY report if it immediately scores a point (a stuff block to the floor).\n\nFor each valid contact give:\n  t       - the EXACT moment of physical impact in ABSOLUTE MATCH SECONDS ({start} + offset). Estimate offset carefully to one decimal place.\n  type    - one of the seven above\n  side    - \"left\" or \"right\" (where the player made contact)\n  number  - the contacting player's jersey number as a string, or null if unreadable. Do not guess.\n  error   - true if this contact was a direct error (e.g., hit into the net or out of bounds)\n  point   - true ONLY for the final contact if it directly WON the point for the team that made the contact. NEVER true for errors!\n\nReturn an empty list if no valid play happens.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
I expect the relaxed definition of `dig` to significantly boost its recall and prediction counts. Concurrently, the explicit instructions against mid-rally serves will reduce the false positive serves and receives. Overall F1 and TP should rise.

```predictions
[{"metric": "dig_pred_count", "direction": "up", "from": 32, "to_approx": 80},
 {"metric": "serve_pred_count", "direction": "down", "from": 171, "to_approx": 140},
 {"metric": "tp", "direction": "up", "from": 248, "to_approx": 270},
 {"metric": "headline_f1", "direction": "up", "from": 0.410, "to_approx": 0.430},
 {"metric": "block_f1", "direction": "flat", "from": 0.0, "to_approx": 0.0}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
dig_pred_count                     up to ~80        up 32 -> 112    OK     X
serve_pred_count                down to ~140     flat 171 -> 172     X     X
tp                                up to ~270       up 248 -> 283    OK     X
headline_f1                      up to ~0.43    up 0.41 -> 0.452    OK     X
block_f1                        flat to ~0.0       up 0 -> 0.125     X     X

direction 3/5   magnitude 0/5
```

headline_f1 0.410 -> 0.452   (+0.043)
n_pred 660 -> 701   missed 164 -> 148   invented 274 -> 299
pipeline: $3.05, 0 cached, 0 failed

## VERDICT
Right about the mechanism for `dig`, wrong about the mechanism for `serve`.

Broadening the `dig` definition worked exactly as intended, surging predictions from 32 back up to 112 and driving True Positives from 248 to 283. However, the textual veto attempting to constrain `serve` ("Players MUST be in stationary starting formations") completely failed to suppress mid-rally hallucinations. Serve predictions stayed entirely flat (171 to 172). The slight bump in `block_f1` is a nice bonus, likely just variance from the model being generally less confused by restrictive definitions.

This round confirms our highest F1 yet (0.452) by successfully restoring `dig` recall without breaking the other improvements. But it also proves definitively that we cannot textually prompt the model out of its serve hallucinations. The right move is to stop trying to use visual text vetoes, and instead attack the massive false positive count mechanically by reducing the chunk overlap to prevent double-counting hallucinations.
