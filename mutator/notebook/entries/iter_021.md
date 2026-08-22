# Iteration 21

## CONJECTURE
The pipeline is suffering from massive over-prediction (324 ghosts) and type confusion due to four specific definitional mismatches between the model and the scout:
1. **Team attribution of errors:** The model flags `point=true` for errors (like spiking into the net). The scorer awards these points to the team making the error, causing a massive +33 `score_margin_err`.
2. **Serve hallucinations:** The model flags casual dead-time bounces as serves (35 dead-time serve ghosts) and mislabels mid-rally hits on moving balls as serves (46 live-rally serve ghosts).
3. **Over-segmentation of rallies:** The model feels compelled to label every contact. Because it is told not to report regular sets, it mislabels them as digs or receives. It also records non-point-scoring continuation block touches (17 block ghosts). 
4. **Trajectory confusion:** The model classifies freeball/overpass attacks as digs or receives (41 real attacks misclassified), and often calls real serves "receives" (23 times) because it misses the initial dead ball in a 6-second chunk. 

These are **definitional** gaps, not perception failures. We can cut `n_pred` dramatically and fix the score margin without losing TP by clarifying trajectory intent, vetoing dead time, instructing the model to completely ignore (rather than mislabel) sets/blocks that don't directly score, and explaining the logic behind the `point` flag.

## CHANGE
I am updating the prompt to fix these definitional mismatches by explicitly vetoing dead-time contacts, instructing the model to completely skip continuation block touches and regular sets (rather than mislabeling them), distinguishing attacks from digs by their over-the-net trajectory, and explaining the logic for the `point` flag to stop awarding points for opponent errors.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start:.2f} seconds into the match and runs for 6 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences or count contacts, because missing one contact will cause you to mislabel all others!\n\n  serve   - starts a rally. Hit from behind the back line OVER the net from a stationary start. Clips often start mid-rally; striking a moving ball that was already in play is NEVER a serve.\n  receive - a defensive pass handling the opponent's serve, directed to a teammate.\n  dig     - a defensive pass handling the opponent's attack, directed to a teammate.\n  set     - a pass placing the ball for an attacker. ONLY report if it directly leads to a kill (an assist). DO NOT report regular sets. Skip them entirely; do not mislabel them as digs/receives!\n  attack  - an offensive hit aimed to score by sending the ball OVER the net. Includes freeballs. If a pass goes intentionally over the net, it is an attack, not a dig or receive.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a block AT THE NET. ONLY report if it immediately wins the point (a stuff block). Ignore all other block touches that keep the rally going!\n\nDEAD TIME VETO: Between rallies, players casually pass the ball under the net, practice, or bounce it. IGNORE ALL DEAD TIME CONTACTS. Only report competitive live rally play.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start:.2f}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true ONLY if the team making this contact WON the point (e.g., a kill, stuff block, or ace). Do NOT set point to true for errors, as that incorrectly awards the point to the team making the error!\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By vetoing dead time, restricting blocks to point-scoring actions, and stopping the model from forcing labels onto regular sets, `n_pred` and `invented` will drop significantly. Clarifying trajectory intent (over the net vs to a teammate) will re-classify dozens of `dig`/`receive` errors back into `attack` and `serve` True Positives, causing overall `tp` to rise. Explaining the error logic for the point flag will drastically reduce `score_margin_err`. `missed` should remain mostly flat since the discarded events were already ghosts.

```predictions
[{"metric": "n_pred", "direction": "down", "from": 738, "to_approx": 500},
 {"metric": "tp", "direction": "up", "from": 293, "to_approx": 315},
 {"metric": "invented", "direction": "down", "from": 324, "to_approx": 180},
 {"metric": "serve_pred_count", "direction": "down", "from": 169, "to_approx": 95},
 {"metric": "block_pred_count", "direction": "down", "from": 23, "to_approx": 10},
 {"metric": "score_margin_err", "direction": "down", "from": 33, "to_approx": 10},
 {"metric": "point_f1", "direction": "up", "from": 0.295, "to_approx": 0.380},
 {"metric": "missed", "direction": "flat", "from": 131, "to_approx": 131}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
n_pred                          down to ~500       up 738 -> 779     X     X
tp                                up to ~315     down 293 -> 277     X     X
invented                        down to ~180       up 324 -> 366     X     X
serve_pred_count                 down to ~95     down 169 -> 160    OK     X
block_pred_count                 down to ~10        down 23 -> 7    OK    OK
score_margin_err                 down to ~10         up 33 -> 39     X     X
point_f1                         up to ~0.38 down 0.295 -> 0.257     X     X
missed                          flat to ~131     flat 136 -> 137    OK    OK

direction 3/8   magnitude 2/8
```

headline_f1 0.455 -> 0.417   (-0.038)
n_pred 738 -> 779   missed 136 -> 137   invented 324 -> 366
pipeline: $3.04, 0 cached, 0 failed

## VERDICT
I was completely wrong. The numbers show a severe regression across the board: instead of dropping, `n_pred` and `invented` surged (up to 779 and 366, respectively), while True Positives dropped from 293 to 277. Adding highly explicit negative constraints ("DEAD TIME VETO", "DO NOT COUNT", "Do NOT set point to true for errors") completely backfired. Rather than filtering out noise, the verbose text caused the model to hyper-fixate on the vetoed concepts, generating even more hallucinations. Notably, `score_margin_err` actually increased from 33 to 39; this proves that giving the model complex conditional logic for score attribution ("if it's an error, don't award the point to the contacting team") fails because it cannot reliably map that abstract logic onto fuzzy visual tracking. Only the strict `block` veto worked (dropping block predictions from 23 to 7), but it was overshadowed by overall degradation. 

This change made things worse because we hit the limit of text-based behavioral modification; the model lacks the visual precision to apply complex negative constraints without its basic perception degrading. The right move is to abandon this line of aggressive prompt engineering, go back to an earlier, simpler prompt configuration, and attack the hallucination problem mechanically by shrinking the chunk overlap.
