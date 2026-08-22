# Iteration 22

## CONJECTURE
The pipeline is suffering from a definitional mismatch where the model assigns multiple event types to the exact same physical ball contact, generating dozens of "ghost" predictions inside rallies. Because the deduplication step only merges events of the SAME type, outputting an `attack` and a `kill` for the same hit (e.g., at 21:18) bypasses deduplication and creates an immediate ghost. Secondly, because of the short 6s chunk length, the model misperceives mid-rally hits as a `serve` simply because they are the first action it sees in a new clip, resulting in 88 hallucinated serves (160 predicted vs 118 real). I am fixing these definitional gaps by adding a strict "MUTUALLY EXCLUSIVE EVENTS" rule to force one label per contact, explicitly instructing it to skip non-scoring sets rather than mislabel them, and adding a rule that striking an already-moving ball is NEVER a serve.

## CHANGE
I am updating the prompt to explicitly forbid multiple event types for the same timestamp, instructing the model to output exactly one type per physical contact, and tightening the `serve` and `point` definitions to prevent short-clip hallucinations.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start:.2f} seconds into the match and runs for 6 seconds.\n\nMUTUALLY EXCLUSIVE EVENTS (ONE PER CONTACT):\nOutput EXACTLY ONE event type per physical ball contact. Never output multiple events for the exact same contact. Choose the single best fit:\n- If an attack wins the rally, label it ONLY as `kill` (do not also output `attack`).\n- If a block wins the point, label it ONLY as `block`.\n- Never output both a `dig` and a `receive` for the same pass.\n\nACTION DEFINITIONS:\nDO NOT REPORT EVERY CONTACT. You MUST skip regular sets, non-scoring blocks, and dead-time passing.\n  serve   - starts a rally. Hit from behind the back line OVER the net from a stationary toss. If a player hits a ball that is already moving, or jumps to hit a pass, it is NEVER a serve. Do not guess \"serve\" just because it is the first action in a clip.\n  receive - a defensive pass handling the opponent's serve, directed to a teammate.\n  dig     - a defensive pass handling the opponent's attack, directed to a teammate.\n  set     - a pass placing the ball for an attacker. ONLY report if it directly leads to a kill (an assist). SKIP ALL OTHER SETS. Do not mislabel skipped sets as digs or receives.\n  attack  - an offensive hit aimed to score by sending the ball OVER the net. Includes freeballs. If a pass goes intentionally over the net, it is an attack, not a dig or receive.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a block AT THE NET. ONLY report if it immediately wins the point (a stuff block). Skip all other block touches!\n\nDEAD TIME VETO: Between rallies, players casually pass the ball under the net, practice, or bounce it. IGNORE ALL DEAD TIME CONTACTS. If players are standing casually or walking around, it is dead time. Only report competitive live rally play.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start:.2f}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true ONLY for the final contact of a rally if it directly WON the point (like a kill, stuff block, or unreturnable serve). NEVER set true for regular digs, receives, or errors!\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 6.0,
 "overlap": 2.0,
 "fps": 5,
 "width": 640,
 "crop": "1920:620:0:330",
 "media_resolution": null,
 "model": "gemini-3.7-flash",
 "thinking": "low"}
```

## PREDICTION
I expect the overall number of predictions to fall significantly because the model will stop outputting overlapping labels for a single touch and stop guessing "serve" mid-rally. Because these removed events were mostly ghosts that bypassed deduplication, TP should remain flat or even increase slightly by forcing a single correct match, raising headline F1.

```predictions
[{"metric": "n_pred", "direction": "down", "from": 779, "to_approx": 650},
 {"metric": "tp", "direction": "flat", "from": 277, "to_approx": 277},
 {"metric": "serve_pred_count", "direction": "down", "from": 160, "to_approx": 115},
 {"metric": "attack_pred_count", "direction": "down", "from": 197, "to_approx": 160},
 {"metric": "headline_f1", "direction": "up", "from": 0.417, "to_approx": 0.450}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
n_pred                          down to ~650     down 779 -> 716    OK     X
tp                              flat to ~277     flat 277 -> 284    OK    OK
serve_pred_count                down to ~115       up 160 -> 169     X     X
attack_pred_count               down to ~160     down 197 -> 175    OK    OK
headline_f1                      up to ~0.45   up 0.417 -> 0.449    OK    OK

direction 4/5   magnitude 3/5
```

headline_f1 0.417 -> 0.449   (+0.032)
n_pred 779 -> 716   missed 137 -> 143   invented 366 -> 309
pipeline: $2.98, 0 cached, 0 failed

## VERDICT
Right about the mechanism for deduplication (mutually exclusive events), but wrong about the serve negative veto. 

The numbers show that forbidding multiple event types for the same contact successfully closed a definitional loophole. By preventing the model from outputting both an `attack` and a `kill` for a single hit, we stopped those labels from bypassing deduplication. This cleanly slashed `invented` predictions from 366 to 309, lowered total predictions, and gave a nice bump to True Positives (277 to 284), raising headline F1 to 0.449. 

However, `serve_pred_count` moved in the exact opposite direction of my prediction, rising from 160 to 169. The verbose negative constraints ("If a player hits a ball that is already moving... it is NEVER a serve. Do not guess 'serve' just because it is the first action") triggered a classic "pink elephant" effect. Warning the model about specific edge cases caused it to hallucinate serves even more frequently when it saw those edge cases.

The mutually exclusive rule is a major success and should be kept. The backfiring negative serve text must be stripped. The right move now is to accept that text-based hallucination filters have reached their limit, and test mechanical overlapping reductions as proposed.
