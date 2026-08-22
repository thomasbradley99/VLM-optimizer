# Iteration 27

## CONJECTURE
The high number of invented events (284 ghosts) dragging down F1 is caused by a severe definitional bug in the prompt: the instruction "Output EXACTLY ONE event type per physical ball contact." The model interprets this as a mandate to exhaustively label almost every contact it sees, forcing it to misclassify normal passes and free-ball bumps as `receive` or `dig`, and mid-rally back-row hits as `serve`. This explains why 83% of the phantom events (230) occur inside live rallies, including a massive 46 `serve` ghosts mid-rally. It is a definitional failure where the model is obediently following an unintended command to act as a play-by-play logger rather than a highlight filter.

## CHANGE
I am replacing the command that forced exhaustive labeling with a strict filter ("DO NOT log every ball contact... MUST BE SKIPPED"), explicitly instructing the model to ignore non-pivotal contacts, and refining the definitions to prevent failed defensive touches from being logged as `kill`s.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: Analyze ONLY the main court in the foreground. Ignore background matches completely.\n\nThe vertical net divides the screen into a left court and a right court. For the `side` field, output 'left' if the player making contact is physically standing on the left side of the screen, and 'right' if they are on the right side. CRITICAL: Log the side where the PLAYER is, completely ignoring where the ball is hit towards.\n\nThis clip begins at {start:.2f} seconds and runs for 6 seconds.\nWARNING: Clips often start MID-RALLY. DO NOT assume the first contact is a serve just because it is early in the clip.\n\nONLY LOG SPECIFIC ACTIONS (SKIP THE REST):\nDO NOT log every ball contact! Most contacts (regular passes, normal sets, free-ball bumps) MUST BE SKIPPED. Only output an event if it perfectly matches one of the critical actions defined below. If in doubt, SKIP IT.\n\nACTION DEFINITIONS:\n  serve   - A hit from behind the BACK BASELINE that initiates play. Do NOT log the ball toss. Back-row hits during a live rally are attacks, NEVER serves.\n  receive - A defensive pass specifically handling an opponent's serve (a ball traveling a long distance from their baseline). Do not use for passes mid-rally.\n  dig     - A hard-fought defensive pass against an opponent's powerful ATTACK (a fast, downward-driven spike). Do not report easy passes.\n  set     - An assist. ONLY report if it directly sets up a point-winning kill. SKIP ALL OTHER SETS.\n  attack  - An offensive swing or spike intentionally directing the ball over the net.\n  kill    - An attack that immediately wins the point (hits the floor or deflects wildly out). Log the ATTACK as the kill, NOT the opponent's failed dig!\n  block   - A net defense. ONLY report if it immediately scores a point (a stuff block to the floor).\n\nDEAD TIME VETO: You MUST ignore practice hits, practice serves, and post-rally bounces. Contacts after the ball hits the floor are NEVER valid. If players are standing around casually, walking, or not in a ready defensive stance, IT IS DEAD TIME. Skip all contacts.\n\nFor each contact give:\n  t       - the EXACT moment of physical impact in ABSOLUTE MATCH SECONDS ({start:.2f} + offset). Estimate the offset carefully to one decimal place (e.g. 2.3). Deduplication relies on precise timing!\n  type    - one of the seven above\n  side    - \"left\" or \"right\" (where the player made contact)\n  number  - the contacting player's jersey number as a string, or null if unreadable. Do not guess.\n  error   - true if this contact was a direct error (e.g., hit into the net or out of bounds)\n  point   - true ONLY for the final contact if it directly WON the point for the team that made the contact (e.g., a kill or stuff block). NEVER true for regular passes, failed digs, or errors!\n\nReturn an empty list if no valid play happens.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": "1920:620:0:330", "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
The model will stop feeling obligated to assign a label to every contact, dramatically reducing the denominator bloat. `serve` mid-rally guesses and `receive` mid-rally guesses will crash, raising headline F1.

```predictions
[{"metric": "n_pred", "direction": "down", "from": 664, "to_approx": 560},
 {"metric": "invented", "direction": "down", "from": 284, "to_approx": 190},
 {"metric": "tp", "direction": "flat", "from": 267, "to_approx": 267},
 {"metric": "serve_pred_count", "direction": "down", "from": 174, "to_approx": 125},
 {"metric": "headline_f1", "direction": "up", "from": 0.440, "to_approx": 0.465}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
n_pred                          down to ~560     flat 664 -> 660     X     X
invented                        down to ~190     flat 284 -> 274     X     X
tp                              flat to ~267     down 267 -> 248     X     X
serve_pred_count                down to ~125     flat 174 -> 171     X     X
headline_f1                     up to ~0.465   down 0.44 -> 0.41     X     X

direction 0/5   magnitude 0/5
```

headline_f1 0.440 -> 0.410   (-0.030)
n_pred 664 -> 660   missed 170 -> 164   invented 284 -> 274
pipeline: $3.04, 0 cached, 0 failed

## VERDICT
I was completely wrong. The numbers show that explicitly commanding the model to "SKIP THE REST" and "DO NOT log every ball contact" had almost zero effect on the hallucinated events (`invented` barely moved from 284 to 274), but it actively suppressed real events, dropping True Positives by 19 and tanking the F1 score. 

This reinforces a hard lesson: textual negative vetoes ("do not log X", "skip Y") are practically invisible to this model when it comes to suppressing hallucinations it thinks it "sees", but they introduce enough doubt to make it drop valid ground-truth actions. Our prompt tuning has hit a wall for precision. We must accept the model's baseline visual over-generation and attack it mechanically. The right move is to revert to a cleaner prompt and aggressively reduce the clip overlap to prevent duplicate hallucinations from stacking up.
