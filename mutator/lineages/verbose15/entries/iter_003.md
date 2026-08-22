# Iteration 3

## CONJECTURE
The pipeline is suffering from massive definitional confusion and duplicate reporting. 
First, the model is ignoring ball trajectory in favor of perceived sequence: it classifies 36 true `receive`s as `serve`s (because it misses the real serve and thinks the first pass it sees is the start) and 22 true `attack`s as `receive`s. This is a definitional gap—the prompt never explicitly requires a serve or attack to cross the net, nor a receive to stay on the same side.
Second, the model generates 217 invented GHOSTs largely by outputting multiple overlapping labels for a single timestamp (e.g., at 16:46 predicting an attack, a block, and a kill simultaneously) and by logging dead-time ball bounces. We can fix both by adding strict trajectory requirements to the taxonomy and enforcing a single-label, live-play-only rule.

## CHANGE
I am updating the prompt to explicitly tie the taxonomy to ball trajectory (OVER the net vs TEAMMATE) and adding critical rules to forbid multiple rows per timestamp and dead-time reporting.

```config
{"lever": "prompt",
 "prompt": "You are an expert volleyball statistician scouting one match from a fixed camera.\n\nCONTEXT. Several courts are in use at once. Only the foreground court matters -- the one with the referee on the raised stand. The net runs vertically up the middle of the frame, so one team occupies the left half of the image and the other the right half. Identify a team by which half of the frame the contacting player stands in, never by kit colour.\n\nThis clip begins at {start} seconds into the match.\n\nTAXONOMY. Every contact belongs to exactly one of seven classes. Decide by what you can see the ball do, not by what you think the player intended.\n\n  serve    the single contact that begins a rally. Struck from behind the back line, sending the ball OVER the net. Never report a serve mid-rally.\n  receive  the first defensive contact answering a serve. The ball is passed to a TEAMMATE on the SAME side. Maximum one per rally.\n  dig      a defensive contact answering an attack. The ball is passed to a TEAMMATE on the SAME side.\n  set      a contact that places the ball for a team-mate to attack, BUT ONLY report it if the resulting attack is a kill (an assist).\n  attack   any contact that sends the ball OVER the net to the opponents.\n  kill     an attack that ends the rally immediately.\n  block    a contact made at the net by a player with hands above it.\n\nCRITICAL RULES:\n1. TRAJECTORY: Serves and attacks MUST cross the net. Receives and digs MUST stay on their own side.\n2. NO DEAD TIME: Ignore players bouncing or tossing the ball before a serve. Only report live rally contacts.\n3. EXACTLY ONE LABEL: Never output multiple rows for the same contact or timestamp. If an attack and block happen simultaneously, report the attack.\n\nREPORTING. Give one row per contact you actually observe:\n  t        time of contact in absolute match seconds, to a fraction of a second\n  type     one of the seven above\n  side     \"left\" or \"right\", the half of the frame the contacting player is in\n  number   the jersey number as a string, or null if you cannot read it\n  error    true if the contact was a mistake -- into the net, out of bounds, mishandled\n  point    true ONLY if the team making THIS contact won the rally. If this contact is an error that loses the rally, point MUST be false.\n\nIf nothing happens in this clip, return an empty list.",
 "chunk_len": 15.0, "overlap": 4.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By enforcing trajectory constraints, the model will stop classifying cross-net attacks as receives, and will stop calling same-side receives as serves. This will heavily reduce action mismatches, raising True Positives. The rule against multiple labels per timestamp and dead-time reporting will cleanly slice out a large portion of the 217 GHOSTs, dropping `n_pred` significantly. Since perception (what the model actually spots) remains unchanged, the `missed` count will stay completely flat.

```predictions
[{"metric": "serve_pred_count", "direction": "down", "from": 152, "to_approx": 115},
 {"metric": "n_pred", "direction": "down", "from": 565, "to_approx": 450},
 {"metric": "tp", "direction": "up", "from": 230, "to_approx": 255},
 {"metric": "attack_recall", "direction": "up", "from": 0.237, "to_approx": 0.330},
 {"metric": "missed", "direction": "flat", "from": 202, "to_approx": 202}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                down to ~115       up 152 -> 167     X     X
n_pred                          down to ~450     flat 565 -> 564     X     X
tp                                up to ~255     flat 230 -> 223     X     X
attack_recall                    up to ~0.33 down 0.374 -> 0.321     X    OK
missed                          flat to ~202     flat 202 -> 208    OK    OK

direction 1/5   magnitude 2/5
```

headline_f1 0.413 -> 0.400   (-0.012)
n_pred 565 -> 564   missed 202 -> 208   invented 217 -> 222
pipeline: $1.95, 0 cached, 0 failed

## VERDICT
Wrong. The text-based trajectory rules and single-label constraints failed to reduce ghosts or fix action confusion, and instead actively harmed `attack` detection. 

The numbers show that `serve_pred_count` went up (152 to 167) and `invented` contacts slightly increased (217 to 222), proving the model completely ignored the explicit prompt rules against multiple labels and dead-time reporting. More importantly, `attack_recall` dropped from 0.374 to 0.321, pulling `tp` down with it. 

I suspect this happened because I instructed the model to "Decide by what you can see the ball do, not by what you think the player intended" while enforcing a strict "MUST cross the net" rule. At 5fps and 640px width, the ball is often a blur or entirely invisible as it crosses the net. By forbidding the model from relying on player posture (intention) to classify an attack, it simply dropped valid attacks where the ball's trajectory wasn't perfectly clear. 

We should revert these overly strict prompt constraints. The model cannot reason its way out of a perceptual deficit. If we want it to understand fast actions, we either need to let it rely on player posture or improve its perception (e.g., by increasing the framerate).
