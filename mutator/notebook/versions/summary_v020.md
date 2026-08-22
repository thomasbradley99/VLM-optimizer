# What I know about this pipeline

# What I know about this pipeline

### Established
- **Shorter chunks improve recall up to a point:** Reducing clip length to 6s (30 frames) maximizes True Positives by limiting attention saturation. Moving to 10s chunks (50 frames) causes severe attention saturation, tanking recall (TPs dropped from 309 to 238).
- **Mechanical reduction of chunks suppresses hallucinations:** Slicing the video into fewer API calls mechanically starves the model of opportunities to invent events in dead time. 
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the 20-30 range (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Score logic decoupling:** Defining `point` logic to explicitly exclude erroring contacts helps reduce score attribution margin errors.
- **Clip boundary warnings for serves:** Explicitly warning the model that short clips often start mid-rally and strictly stating that defensive passes are never serves successfully reduces serve hallucinations.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes and back-row attacks with serves. This is a severe visual reflex that ignores descriptive text.
- **Strict negative vetoes reduce recall:** Adding intermediate JSON reasoning fields or strict negative visual vetoes causes the model to drop True Positives across the board. The model's visual perception is too fuzzy to handle rigid visual disqualifiers.
- **The top of the frame is critical:** The upper third of the video cannot be cropped, as it contains the ball in flight during high arcs. Losing sight of the ball breaks the model's ability to track the rally.
- **Verbose definitions inflate false positives:** Highly detailed text descriptions of physical actions cause the model to hallucinate events by matching partial visual cues. 

### Ruled out
- **Increasing chunk length to 10s+ to reduce hallucinations:** While 10s chunks mechanically reduce false positives, the 50-frame length induces unacceptable attention saturation and drops true positives massively. We cannot use clip length to solve hallucinations.
- **Semantic context vetoes ("Dead time veto"):** Telling the model to ignore warmups or dead time between points does not work. It cannot distinguish between casual practice hits and competitive rally hits.
- **Reasoning tokens (Thinking / CoT):** Giving the model `thinking: "medium"` to reason about background courts and dead-ball context before generating JSON failed to reduce the ~400 hallucinated events. 
- **10 FPS temporal resolution:** Requesting 10 fps causes massive API failures. We are strictly bound to 5 fps.
- **Minimalist prompt to increase recall:** Stripping event definitions down to bare class names did not cause the model to stop dropping true events. 
- **Hard cropping the background:** Physically cropping the top 330 pixels to hide background matches reduces false positives, but it ruins foreground recall by hiding the ball during high passes.
- **Sequence language causing serve/receive mixups:** Defining events by their global sequence order ("first contact", "second contact") does not help.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" failed to suppress hallucinated serves. 
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **Per-Team possession framework:** Reframing the logic to evaluate "per-team possessions" failed.
- **Explicit negative vetoes on state:** Telling the model that a serve "ONLY happens from a dead ball" failed entirely to drop serve predictions. 
- **JSON Chain-of-Thought for visual state:** Forcing the model to explicitly output whether the ball was "dead" or "in-flight" before the `type` field dropped recall and lowered F1.
- **2D screen topology for serves:** Restricting serves to the "extreme left or right edge of the video frame" failed to correct serve over-prediction and merely caused True Positives to drop. 
- **Local sequence logic / Structural flow:** Instructing the model to use the immediate natural transitions of a rally (Serve -> Receive) to disambiguate visual forms fails catastrophically, tanking recall due to cascade failures.
- **Relative pixel scale / Player size:** Instructing the model to only report "LARGE players" and ignore "TINY players" in the background failed to reduce hallucinated events.
- **Explicit spatial/screen-percentage background vetoes:** Instructing the model to ignore the "top 20% of the video frame" and only report events in the "lower 80%" backfires entirely, raising `invented` events. The model struggles with exact proportional boundaries.
- **Ignoring background constraints entirely:** Stripping all spatial and background vetoes from the prompt while keeping 6-second chunks causes `invented` events to surge from 412 to 458. The model needs a way to filter noise, but text-based spatial rules fail to provide it.

### Open
- Given that we must use short 6-second chunks to avoid attention saturation, how do we prevent the large overlap from duplicating fuzzy hallucinations?
- Can we tighten NMS parameters to merge jittery hallucinated timestamps across overlapping clips?

### Current hypothesis
We must keep `chunk_len` at 6.0 seconds to preserve high recall (30 frames avoids attention saturation). However, our previous 6s baseline used an `overlap` of 2.0 seconds. This means 33% of the match was processed twice. True positives in the overlap are cleanly merged by NMS because their visual timestamps are stable, but dead-time background hallucinations have jittery timestamps and often fail to merge, leading to double-counted false positives. Furthermore, a 2.0s overlap on a 6s chunk results in ~930 API calls. By reverting `chunk_len` to 6.0 but reducing `overlap` to 0.5 seconds, we will drop the number of independent clips to ~650 and dramatically shrink the double-exposure window. This will organically cut duplicate hallucinations and total prediction volume without triggering the attention saturation of 10-second chunks, preserving our True Positives.
