# What I know about this pipeline

### Established
- The ground truth applies strict, outcome-dependent definitions to volleyball actions (e.g., a "set" is only recorded if it results in a kill, matching standard assist rules). Removing these constraints causes false positives to explode (predicting 172 sets vs. 47 actual, increasing invented events by 123).
- Instructing the model to focus on "DURING LIVE PLAY ONLY" successfully reduces dead-time ghost events.
- Background matches in the top half of the frame generate hundreds of false positives. Cropping them out (`crop="1920:620:0:330"`) drops `invented` events dramatically.
- The model can accurately track ball contacts high in the air, meaning overly aggressive top-cropping (e.g., cutting 330 pixels) clips legitimate high passes and costs true positives.

### Ruled out
- Using standard, outcome-independent definitions (e.g., "set = any intentional pass to an attacker"). This was tested and rejected in Iteration 2, as it resulted in massive over-prediction (invented events jumping from 286 to 409) because the ground truth uses official outcome-dependent stat rules.
- Assuming aggressive top-cropping is harmless to the main court. Cutting the top 330 pixels cost us 23 true positives in Iteration 1, proving the model relies on the upper frame to track high passes.
- Using strict conditional logic to align definitions *while using short temporal chunks*. The model cannot reliably evaluate outcome-based rules in a 6.0-second window because the necessary context (the ultimate result of the rally) often falls outside the chunk, causing it to drop the event entirely.

### Open
- Does the model drop events when chunk sizes increase due to information density, or can it handle a 12-to-15-second chunk flawlessly?
- Is there a "goldilocks" crop geometry (e.g., `y=200`) that obscures background matches without clipping high passes on the main court?

### Current hypothesis
The restrictive, outcome-dependent definitions (like "only report a set if it leads to a kill") are correctly aligned with the ground truth, but the model cannot apply them effectively because a 6.0-second `chunk_len` is too short to observe the outcome of a play. By reverting to the strict definitions and increasing the `chunk_len` to 15.0 seconds (with a larger overlap), the model will have sufficient temporal context to observe whether an attack scores a point, allowing it to correctly identify assists ("sets") and digs without falsely omitting events that resolve outside the chunk.
