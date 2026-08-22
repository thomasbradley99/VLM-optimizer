# What I know about this pipeline

### Established
- 15-second chunks stabilize recall at ~230 TP. 
- Assist-only definitions for `set` align with the taxonomy, successfully dropping raw predictions from 130 to 44. 
- The model cannot reliably track the ball's physical trajectory. Forcing it to ignore player intention and rely purely on ball trajectory harms attack recall (dropping it from 0.374 to 0.321).
- Text-based negative constraints ("EXACTLY ONE LABEL", "NO DEAD TIME") fail to reduce the ~220 invented contacts.

### Ruled out
- `chunk_len` of 30.0s. Tested and rejected; temporal dilution drops TP by 81 and destroys F1.
- Forcing `point: false` on rally-ending errors. Tested and rejected; disrupts parser and doubles `score_margin_err`.
- Text-only mid-rally serve warnings and trajectory rules. Tested and rejected; models fail to parse global timeline position at chunk boundaries and cannot physically see the ball well enough at 5fps to satisfy strict "over the net" requirements.

### Open
- Are the remaining 222 invented contacts caused by cross-chunk overlap that evades the harness deduplication (e.g., timestamps differing by 0.5s), or are they pure within-chunk hallucinations?
- Will increasing the framerate allow the model to actually see the ball and resolve the action confusion naturally, without needing rigid prompt text?

### Current hypothesis
The pipeline is fundamentally bottlenecked by perception, not taxonomy. At 5fps, the model cannot distinguish between a serve, receive, or attack using just the ball's flight path, and it hallucinates extra contacts in the gaps between frames. The single most promising next line of attack is to revert the restrictive prompt text and increase the framerate to 10fps. This will give the model the temporal resolution it needs to read player body mechanics and ball flight, naturally improving classification accuracy and reducing hallucinated guesses.
