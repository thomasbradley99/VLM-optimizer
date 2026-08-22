# What I know about this pipeline

### Established
- The ground truth applies strict, outcome-dependent definitions to volleyball actions. Removing these constraints without adequate temporal context causes false positives to explode.
- Background matches in the top half of the frame generate hundreds of false positives. Cropping them out drops `invented` events dramatically.
- The model can accurately track ball contacts high in the air; overly aggressive top-cropping (e.g., cutting 330 pixels) clips legitimate high passes and costs true positives.
- Increasing `chunk_len` from 6.0 to 15.0 seconds reduces hallucinated events (invented dropped 409 -> 245) but severely degrades exhaustive recall, causing `missed` events to jump from 126 to 177.
- Enforcing absolute limits on in-rally actions (e.g., "exactly one serve") causes the model to discard legitimate intermediate contacts rather than accurately reclassifying them, artificially inflating `missed` events to 233.

### Ruled out
- Using standard, outcome-independent definitions (e.g., "set = any intentional pass"). Tested and rejected in Iteration 2, resulting in massive over-prediction.
- Assuming aggressive top-cropping is harmless to the main court. Cutting the top 330 pixels cost 23 true positives in Iteration 1.
- Using very short (6.0s) chunk sizes. The model hallucinates wildly due to lacking context for dead-time balls.
- Using long (15.0s) chunk sizes. The model cannot exhaustively list all contacts in a long rally, causing it to summarize and skip intermediate events.
- Using hyper-strict prompt exclusions to force ground-truth alignment. Imposing strict outcome-dependent filters on a frame-by-frame tracker suppresses true positives rather than correcting category confusion.

### Open
- What is the optimal `chunk_len` and `overlap` combination that provides enough context to see rally outcomes without overwhelming the model's ability to recall every intermediate contact?
- Is there a "goldilocks" crop geometry (e.g., cutting only the top 150-200 pixels) that obscures the background matches without clipping high passes on the main court?

### Current hypothesis
The pipeline is restricted by compounding recall bottlenecks: excessive chunk duration and overly aggressive spatial cropping. Rolling back to standard prompt definitions while implementing a moderate `chunk_len` of 10.0 seconds (with a 4.0-second overlap) and relaxing the top-crop to `y=200` will restore exhaustive temporal reporting and spatial visibility without triggering the dead-time hallucinations of the baseline configuration.
