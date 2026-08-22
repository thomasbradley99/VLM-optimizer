# What I know about this pipeline

### Established
- 15-second chunks at 5 fps stabilize recall at ~220-230 TP. 
- Assist-only definitions for `set` align with the taxonomy, successfully dropping raw predictions from 130 to 44. 
- The model cannot reliably track the ball's physical trajectory. Forcing it to ignore player intention and rely purely on ball trajectory harms attack recall.
- Text-based negative constraints ("EXACTLY ONE LABEL", "NO DEAD TIME") fail to reduce the ~220 invented contacts.
- Increasing framerate to 10 fps over 15-second chunks (150 frames) hurts recall, dropping true positives from 223 to 187 due to attention dilution.

### Ruled out
- `chunk_len` of 30.0s. Tested and rejected; temporal dilution drops TP by 81 and destroys F1.
- Forcing `point: false` on rally-ending errors. Tested and rejected; disrupts parser and doubles `score_margin_err`.
- Text-only mid-rally serve warnings and strict trajectory rules. Tested and rejected; models fail to parse global timeline position at chunk boundaries and cannot physically see the ball well enough to satisfy strict "over the net" requirements.
- Increasing framerate to 10 fps to fix fast-action perception. Tested and rejected; it suppresses overall prediction volume, worsening recall and headline F1 (0.400 -> 0.366) because the model struggles to parse 150 frames per chunk.

### Open
- Are the remaining invented contacts caused by cross-chunk overlap that evades the harness deduplication (e.g., timestamps differing by 0.5s), or are they pure within-chunk hallucinations?
- Can we improve action classification at 5 fps by teaching the model to read player body mechanics (e.g., jumping at the net vs. standing at the baseline) rather than trying to track the ball?
- Will reducing the chunk length further (e.g., 10 seconds) at 5 fps improve temporal attention without severing rallies too often?

### Current hypothesis
The pipeline is fundamentally bottlenecked by the model's inability to track a fast-moving ball, and increasing frame density only causes attention dilution. The single most promising next line of attack is to revert to 5 fps (which safely maximizes recall) and completely rewrite the prompt's taxonomy definitions. Instead of relying on strict ball trajectory rules ("must cross the net"), we should instruct the model to classify actions based on player positioning and body mechanics—e.g., a player swinging near the net is an attack, a player bumping the ball from the backcourt is a receive/dig. The model can see bodies much better than it can see the ball.
