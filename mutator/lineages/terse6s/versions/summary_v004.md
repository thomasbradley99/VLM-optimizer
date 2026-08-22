# What I know about this pipeline

### Established
- The ground truth applies strict, outcome-dependent definitions to volleyball actions (e.g., a "set" is only recorded if it results in a kill, matching standard assist rules). Removing these constraints without adequate temporal context causes false positives to explode.
- Background matches in the top half of the frame generate hundreds of false positives. Cropping them out drops `invented` events dramatically.
- The model can accurately track ball contacts high in the air, meaning overly aggressive top-cropping (e.g., cutting 330 pixels) clips legitimate high passes and costs true positives.
- Increasing `chunk_len` from 6.0 to 15.0 seconds dramatically reduces hallucinated events (invented dropped 409 -> 245) by providing context to distinguish dead-time from live rallies.
- Longer `chunk_len` improves outcome-dependent classification (`kill_f1` rose to 0.44) but severely degrades exhaustive recall. In 15-second chunks, the model fails to list every contact, causing `missed` events to jump from 126 to 177.

### Ruled out
- Using standard, outcome-independent definitions (e.g., "set = any intentional pass"). Tested and rejected in Iteration 2, resulting in massive over-prediction because the ground truth uses official outcome-dependent stat rules.
- Assuming aggressive top-cropping is harmless to the main court. Cutting the top 330 pixels cost 23 true positives in Iteration 1 because the model relies on the upper frame to track high passes.
- Using very short (6.0s) chunk sizes. The model hallucinates wildly (over 400 invented events) because it lacks the context to tell if an action is part of a live rally or a dead-time ball bounce.
- Using long (15.0s) chunk sizes. The model's recall drops. It cannot exhaustively list all 10+ contacts in a long rally, causing it to summarize and skip intermediate events.

### Open
- What is the optimal `chunk_len` and `overlap` combination that provides enough context to see rally outcomes without overwhelming the model's ability to recall every intermediate contact?
- Is there a "goldilocks" crop geometry (e.g., cutting only the top 150-200 pixels) that obscures the background matches without clipping high passes on the main court?

### Current hypothesis
The pipeline is currently suffering from two distinct recall bottlenecks: the 15-second chunk length is too long (causing the model to skip intermediate contacts), and the `y=330` top-crop is too aggressive (clipping high passes off-screen). The most promising next step is a two-pronged adjustment: backing off to a middle-ground 10.0-second `chunk_len` (with a large 4.0-second `overlap` to ensure events aren't lost at boundaries), and easing the top-crop to restore visibility of the upper main court. This should preserve the model's newfound ability to ignore dead-time while recovering the true positives we have bled over the last two iterations.
