# Iteration 3

## CONJECTURE
The pipeline just experienced a massive perception failure. By changing the prompt in iter_002 to demand direct classification into specific volleyball terminology ("serve", "receive", "dig"), True Positives collapsed from 191 to 47. The vision model struggles to reliably map raw visual motion directly to strict sport-specific taxonomy in one zero-shot step. When stripped of its ability to describe physical motions (like a player making contact and the ball going UP/OVER), it became effectively blind to 75% of the real events it previously caught (missed events spiked from 266 to 459). This is a perception issue introduced by the prompt semantics, not a definitional one.

## CHANGE
Revert the prompt exactly to the best-scoring physical description version (fixing only the formatting of the `{start}` token to comply with schema constraints) while keeping all video and model parameters identical to iter_002.

```config
{"lever": "prompt",
 "prompt": "You are watching a 10-second clip of a volleyball match from one fixed camera.\nA net runs vertically up the middle of the frame, dividing it into a LEFT court and a RIGHT court.\nOnly the foreground court matters -- the one with the referee on the raised stand.\n\nDo NOT name any volleyball actions. Report only what you can literally see, as a list of moments,\neach with a time in seconds from the start of this clip:\n\n  - the ball is on the LEFT or the RIGHT of the net\n  - the ball CROSSES the net, and in which direction\n  - a player MAKES CONTACT with the ball: the time, which side they stand on, their shirt colour,\n    their number if legible, and whether they were airborne or on the ground\n  - after that contact the ball goes UP (staying their side), OVER (across the net), DOWN (to the\n    floor), or OUT\n  - the ball HITS THE FLOOR, and on which side\n  - nobody is playing: the ball is being carried, rolled, held, or lying still\n\nBe precise about the times. If nothing is in play, say so in one line.\n\nThis clip begins at {start} seconds into the match.",
 "chunk_len": 10.0,
 "overlap": 3.0,
 "fps": 5,
 "width": 640,
 "crop": "1920:620:0:330",
 "media_resolution": null,
 "model": "gemini-3.7-flash",
 "thinking": "low"}
```

## PREDICTION
Reverting the prompt will restore the model's ability to see physical events, driving True Positives and overall predictions back up to their previous baseline levels while we isolate the cause of the drop.

```predictions
[
  {"metric": "headline_f1", "direction": "up", "from": 0.118, "to_approx": 0.337},
  {"metric": "tp", "direction": "up", "from": 47, "to_approx": 190},
  {"metric": "n_pred", "direction": "up", "from": 244, "to_approx": 550},
  {"metric": "kill_f1", "direction": "flat", "from": 0.000, "to_approx": 0.000},
  {"metric": "missed", "direction": "down", "from": 459, "to_approx": 270}
]
```
