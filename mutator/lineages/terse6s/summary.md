# What I know about this pipeline

### Established
- The ground truth applies strict, outcome-dependent definitions to volleyball actions. Specifically, a `set` is only recorded if it immediately leads to a `kill`. Enforcing this strict temporal dependency in the prompt reduces false-positive sets dramatically (192 -> 53) while maintaining true positives, driving F1 above 0.450.
- Background matches in the top half of the frame generate hundreds of false positives. Cropping them out drops `invented` events dramatically.
- The model can accurately track ball contacts high in the air; overly aggressive top-cropping (e.g., cutting 330 pixels) clips legitimate high passes and costs true positives.
- Temporal Context vs. Granularity: Short chunks (6.0s) force high temporal granularity—maximizing true positives (292) and unlocking block detection—but they completely destroy the model's ability to distinguish live play from dead-time. At 6.0s, the model cannot evaluate rally-wide constraints (like "one serve per rally") because it cannot see rally boundaries.
- Long chunks (15.0s) suppress dead-time hallucinations but cause the model to summarize rallies, skipping intermediate contacts and missing rapid, compound events like blocks.

### Ruled out
- Using standard, outcome-independent definitions for `set` (e.g., "any intentional pass"). The scout does not record these, leading to massive over-prediction.
- Assuming aggressive top-cropping is harmless to the main court. Cutting the top 330 pixels cost 23 true positives in Iteration 1.
- Using long (15.0s) chunk sizes. The model cannot exhaustively list all contacts in a long rally, causing it to summarize and skip intermediate events and blocks.
- Expecting the model to enforce rally-wide rules or conditional logic around clip boundaries (e.g., "if the ball is already in play") inside a 6.0s chunk. The limited temporal window makes it blind to the broader context, causing dead-time practice to look like real serves.

### Open
- What is the exact optimal `chunk_len` and `overlap` combination that provides enough context to see rally boundaries and dead-time, without overwhelming the model's granular ability to spot blocks?
- Is there a "goldilocks" crop geometry (e.g., cutting only the top 150-200 pixels) that obscures the background matches without clipping high passes on the main court?

### Current hypothesis
The pipeline is currently caught in a tug-of-war between temporal granularity (which needs short chunks to see blocks) and contextual awareness (which needs longer chunks to spot dead-time practice and mid-rally serves). Now that we have perfectly aligned our `set` definitions with the scout, the remaining 324 ghosts are primarily false serves and dead-time hallucinations. Implementing an intermediate `chunk_len` of 10.0 seconds with a high `overlap` of 4.0 seconds will provide enough temporal context to suppress dead-ball hallucinations while keeping the chunk size small enough to maintain block detection. Simultaneously, relaxing the overly aggressive 330-pixel top-crop down to 200 pixels will restore spatial visibility for high passes without letting the background matches back in.
