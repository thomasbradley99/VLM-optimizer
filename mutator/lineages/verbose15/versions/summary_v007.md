# What I know about this pipeline

### Established
- 15-second chunks at 5 fps (75 frames) maximize recall and headline F1 (0.414), stabilizing True Positives at ~230.
- Increasing framerate to 10 fps over 15-second chunks (150 frames) hurts recall due to attention dilution, dropping true positives significantly and increasing missed contacts.
- Assist-only definitions for `set` align with the taxonomy, successfully dropping raw predictions from 130 to 44. 
- The model cannot reliably track the ball's physical trajectory. Forcing it to ignore player intention and rely purely on ball trajectory harms attack recall.
- Text-based negative constraints ("EXACTLY ONE LABEL", "NO DEAD TIME") fail to reduce the ~200 invented contacts.
- Complex sequence rules (e.g., "If the ball is already in play, it is NOT a serve") fail to prevent misclassifications like receives being labeled as serves, especially at high frame densities.

### Ruled out
- `chunk_len` of 30.0s. Tested and rejected; temporal dilution drops TP by 81 and destroys F1.
- Forcing `point: false` on rally-ending errors. Tested and rejected; disrupts parser and doubles `score_margin_err`.
- Text-only mid-rally serve warnings and strict trajectory rules. Tested and rejected; models fail to parse global timeline position at chunk boundaries and cannot physically see the ball well enough to satisfy strict "over the net" requirements.
- Increasing framerate to 10 fps to fix fast-action perception. Tested and rejected; it suppresses overall prediction volume, worsening recall and headline F1 (0.400 -> 0.366) because the model struggles to parse 150 frames per chunk.
- Fixing deep-court misclassifications with logical sequence constraints. Tested and rejected; models fail to apply temporal rally logic to correct their spatial biases, resulting in dropped contacts rather than corrected labels.

### Open
- Are the remaining invented contacts caused by cross-chunk overlap that evades the harness deduplication (e.g., timestamps differing by 0.5s), or are they pure within-chunk hallucinations?
- Can we improve action classification at 5 fps by teaching the model to read player body mechanics (e.g., jumping at the net vs. standing at the baseline) rather than trying to track the ball or follow sequence logic?
- Will reducing the chunk length further (e.g., 10 seconds) at 5 fps improve temporal attention without severing rallies too often?

### Current hypothesis
The pipeline is bottlenecked by the model's inability to track a fast-moving ball and reliably infer causal rally sequences across chunk boundaries. The single most promising next line of attack is to rewrite the prompt's taxonomy definitions to focus almost entirely on player positioning and body mechanics. For instance, a player jumping and swinging above the net is an attack; a player bumping the ball low from the backcourt is a receive/dig; a player standing behind the far baseline tossing the ball is a serve. Since the model can see player bodies much better than it can track the ball's physical path or reason about the rally's logical sequence, body-mechanics-based heuristics should improve classification accuracy and lower the hallucination rate.
