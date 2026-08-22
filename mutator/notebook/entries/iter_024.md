# Iteration 24

## CONJECTURE
The model is severely misattributing terminal contacts (kills) to the wrong team, as evidenced by the implied match result where Blue's points plummeted (REAL: 64, YOURS: 18) and White's surged. When Blue hits a winner that lands on White's side, the model erroneously logs a contact (often a `dig` or `kill`) for White because it tracks where the ball LANDS on the floor, not where it was HIT. This converts Blue kills into White action errors or GHOSTs. This is a DEFINITIONAL mismatch—the model can see the play but applies the wrong spatial attribution rule. 

Additionally, the 6-second chunking creates a perception/definition issue: because clips often start mid-rally, the model assumes the first contact it sees must be a `serve`. This causes massive over-prediction of serves (162 predicted vs 118 real), with 19 real `receives` misclassified as `serves` and 36 `serves` hallucinated during dead time. Lastly, the physical bounce of the ball on the floor is being logged as a player contact, creating end-of-rally GHOSTs.

## CHANGE
I am updating the prompt to explicitly define spatial attribution ("Log the side where the player HITS the ball, NOT where the ball lands"), warning the model that 6s clips often start mid-rally so the first contact is rarely a serve, and vetoing ball bounces on the floor as valid events.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: Analyze ONLY the main court in the foreground. Ignore background matches completely.\n\nThe vertical net divides the court. For the `side` field, output 'left' if the contacting player is on the left side of the net, or 'right' if they are on the right side.\nIMPORTANT: Log the side where the player HITS the ball, NOT where the ball lands! If a right-side player hits a winner that lands on the left floor, log a `kill` for the RIGHT side.\n\nThis clip begins at {start:.2f} seconds and runs for 6 seconds.\nWARNING: Clips often start MID-RALLY. The first contact you see might be a receive or dig. DO NOT assume it is a serve. A serve requires a visible toss.\n\nMUTUALLY EXCLUSIVE EVENTS (ONE PER CONTACT):\nOutput EXACTLY ONE event type per physical ball contact. Choose the single best fit.\n- If an attack wins the rally, label it ONLY as `kill`.\n- If a block wins the point, label it ONLY as `block`.\n\nACTION DEFINITIONS:\nDO NOT REPORT EVERY CONTACT. You MUST skip regular sets, non-scoring blocks, and dead-time passing.\n  serve   - STARTS a rally. ONLY report if you clearly see the player toss the ball from a stationary hold behind the back line. If the ball is already flying over the net, it is NEVER a serve.\n  receive - a defensive pass handling the opponent's serve, keeping the ball on the SAME side of the net.\n  dig     - a defensive pass handling the opponent's attack, keeping the ball on the SAME side of the net.\n  set     - an assist pass. ONLY report if it directly sets up a point-winning kill (even if the kill itself happens just after the clip ends). SKIP ALL OTHER SETS.\n  attack  - ANY contact that sends the ball OVER the net to the opponent's side. Digs and receives MUST NOT go over the net.\n  kill    - an offensive hit that wins the rally. Logged for the attacker who hit it.\n  block   - a block AT THE NET. ONLY report if it immediately wins the point (a stuff block).\n\nDEAD TIME VETO: Ignore practice hits, practice serves, and post-rally bounces. Contacts after the ball hits the floor are NEVER valid events! A serve is ONLY real if the receiving team is fully in a ready defensive formation.\n\nFor each contact give:\n  t       - the EXACT moment of physical impact in ABSOLUTE MATCH SECONDS ({start:.2f} + offset). Estimate the offset carefully to one decimal place (e.g. 2.3). Deduplication relies on precise timing!\n  type    - one of the seven above\n  side    - \"left\" or \"right\" (where the player made contact)\n  number  - the contacting player's jersey number as a string, or null if unreadable. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds)\n  point   - true ONLY for the final contact if it directly WON the point for the team that made the contact (like a kill or unreturnable serve). NEVER true for regular passes!\n\nReturn an empty list if no valid play happens.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By correcting the attribution logic, the model will recover Blue kills that were incorrectly logged as White digs or action errors, directly raising `kill_recall`, `team_acc`, and `tp`. The explicit mid-rally warning and floor bounce veto will prevent hallucinated serves and end-of-rally ghost contacts, slashing `n_pred` and `serve_pred_count`. 

```json
```predictions
[{"metric": "serve_pred_count", "direction": "down", "from": 162, "to_approx": 120},
 {"metric": "team_acc", "direction": "up", "from": 0.374, "to_approx": 0.440},
 {"metric": "kill_recall", "direction": "up", "from": 0.385, "to_approx": 0.460},
 {"metric": "tp", "direction": "up", "from": 300, "to_approx": 325},
 {"metric": "n_pred", "direction": "down", "from": 745, "to_approx": 650},
 {"metric": "block_f1", "direction": "flat", "from": 0.125, "to_approx": 0.125}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
serve_pred_count                down to ~120     down 162 -> 129    OK    OK
team_acc                         up to ~0.44 flat 0.801 -> 0.816     X     X
kill_recall                      up to ~0.46 down 0.558 -> 0.442     X    OK
tp                                up to ~325     down 300 -> 279     X     X
n_pred                          down to ~650     down 745 -> 704    OK     X
block_f1                      flat to ~0.125   up 0.125 -> 0.235     X     X

direction 2/6   magnitude 2/6
```

headline_f1 0.463 -> 0.445   (-0.018)
n_pred 745 -> 704   missed 126 -> 158   invented 321 -> 312
pipeline: $3.09, 0 cached, 0 failed

## VERDICT
I was wrong. The attempt to fix spatial attribution logic and veto end-of-rally bounces backfired, tanking `kill_recall` (0.558 -> 0.442) and dropping True Positives (300 -> 279). 

I misread the baseline metrics in my conjecture—`team_acc` was actually already strong at 80.1%, so my complex "where it lands vs where it was hit" instruction was trying to solve a problem that didn't exist at scale. By adding this dense logical constraint, I just confused the model. Furthermore, I accidentally re-introduced a "defensive formation" requirement for serves in the prompt, a constraint I had explicitly proven harmful in earlier iterations. This clearly contributed to the drop in recall and the spike in missed events (126 -> 158). 

The prompt bloat from this iteration made things worse and should be discarded. The right move is to revert these text changes to restore our 300 TP baseline, and attack the false positive problem mechanically by adjusting chunk overlap.
