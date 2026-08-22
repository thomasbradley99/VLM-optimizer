# What I know about this pipeline

### Established
- The ground truth applies strict, outcome-dependent definitions to volleyball actions. Removing these constraints without adequate temporal context causes false positives to explode. 
- Background matches in the top half of the frame generate hundreds of false positives. Cropping them out drops `invented` events dramatically.
- The model can accurately track ball contacts high in the air; overly aggressive top-cropping (e.g., cutting 330 pixels) clips legitimate high passes and costs true positives.
- Temporal context vs. Granularity: Long chunks (15.0s) suppress hallucinations (invented ~245) but cause the model to summarize rallies, skipping intermediate contacts and entirely missing rapid, compound events like blocks. Short chunks (6.0s) force high temporal granularity—restoring true positives (289) and unlocking block detection (block_f1 = 0.333)—but they completely destroy the model's ability to distinguish live play from dead-time, causing `invented` events to explode (>430).
- Enforcing absolute limits on in-rally actions (e.g., "exactly one serve") causes the model to discard legitimate intermediate contacts rather than accurately reclassifying them.
- Asking the model to conditionally ignore events based on clip boundaries (e.g. "if the ball is already in play") fails; it decreases precision and fails to suppress mid-rally phantoms.

### Ruled out
- Using standard, outcome-independent definitions (e.g., "set = any intentional pass"). Tested and rejected in Iterations 2 and 5, resulting in massive over-prediction.
- Assuming aggressive top-cropping is harmless to the main court. Cutting the top 330 pixels cost 23 true positives in Iteration 1.
- Using very short (6.0s) chunk sizes. The model hallucinates wildly due to lacking context for dead-time balls.
- Using long (15.0s) chunk sizes. The model cannot exhaustively list all contacts in a long rally, causing it to summarize and skip intermediate events and blocks.
- Using hyper-strict prompt exclusions to force ground-truth alignment. Imposing strict outcome-dependent filters on a frame-by-frame tracker suppresses true positives rather than correcting category confusion.
- Using conditional logic around clip boundaries. Asking the model to determine if a rally is already in progress at chunk-start just degrades classification precision.

### Open
- What is the exact optimal `chunk_len` and `overlap` combination that provides enough context to see rally boundaries without overwhelming the model's granular ability to spot blocks?
- Is there a "goldilocks" crop geometry (e.g., cutting only the top 150-200 pixels) that obscures the background matches without clipping high passes on the main court?

### Current hypothesis
The pipeline is currently caught in a tug-of-war between temporal granularity (which needs short chunks to see blocks) and contextual awareness (which needs long chunks to ignore dead-time warmups). Implementing an intermediate `chunk_len` of 10.0 seconds with a high `overlap` of 4.0 seconds will provide enough temporal context to suppress dead-ball hallucinations while keeping the chunk size small enough to maintain the granular focus needed to detect blocks. Concurrently, relaxing the overly aggressive 330-pixel top-crop down to 200 pixels will restore spatial visibility for high passes without letting the background matches back in.
