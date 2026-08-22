# What I know about this pipeline

# What I know about this pipeline

### Established
- **Shorter chunks improve recall up to a point:** Reducing clip length from 30s to 15s at 5fps drastically improved recall by limiting attention saturation, but dropping further to 6s chunks causes True Positives to slightly drop and `missed` to rise, likely because natural actions are truncated across boundaries.
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the 20-30 range (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Score logic decoupling:** Defining `point` logic to explicitly exclude erroring contacts helps reduce score attribution margin errors.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes and back-row attacks with serves. This is a severe visual reflex that ignores descriptive text.
- **Strict negative vetoes reduce recall:** Adding intermediate JSON reasoning fields or strict negative visual vetoes causes the model to drop True Positives across the board. The model's visual perception is too fuzzy to handle rigid visual disqualifiers.
- **The top of the frame is critical:** The upper third of the video cannot be cropped, as it contains the ball in flight during high arcs. Losing sight of the ball breaks the model's ability to track the rally.
- **Verbose definitions inflate false positives:** Highly detailed text descriptions of physical actions cause the model to hallucinate events by matching partial visual cues. 

### Ruled out
- **Semantic context vetoes ("Dead time veto"):** Telling the model to ignore warmups or dead time between points does not work. It cannot distinguish between casual practice hits and competitive rally hits; a bump is a bump to the vision encoder.
- **Reasoning tokens (Thinking / CoT):** Giving the model `thinking: "medium"` to reason about background courts and dead-ball context before generating JSON failed to reduce the ~400 hallucinated events. The model uses the reasoning space to rationalize background actions as valid foreground events, proving this is a visual segregation issue, not a reasoning deficit.
- **10 FPS temporal resolution:** Requesting 10 fps causes massive API failures. The system cannot reliably handle 10 fps video extraction. We are strictly bound to 5 fps.
- **Minimalist prompt to increase recall:** Stripping event definitions down to bare class names did not cause the model to stop dropping true events. 
- **Hard cropping the background:** Physically cropping the top 330 pixels to hide background matches reduces false positives, but it ruins foreground recall by hiding the ball during high passes.
- **Sequence language causing serve/receive mixups:** Defining events by their global sequence order ("first contact", "second contact") does not help.
- **Clips starting mid-rally causing serve over-prediction:** Explicitly warning the model that clips start mid-rally and forbidding inside-court serves had only marginal effect on serve over-prediction.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" failed to suppress hallucinated serves. 
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **Per-Team possession framework:** Reframing the logic to evaluate "per-team possessions" failed.
- **Explicit negative vetoes on state:** Telling the model that a serve "ONLY happens from a dead ball" failed entirely to drop serve predictions. 
- **JSON Chain-of-Thought for visual state:** Forcing the model to explicitly output whether the ball was "dead" or "in-flight" before the `type` field dropped recall and lowered F1.
- **2D screen topology:** Restricting serves to the "extreme left or right edge of the video frame" failed to correct serve over-prediction and merely caused True Positives to drop. 
- **Local sequence logic / Structural flow:** Instructing the model to use the immediate natural transitions of a rally (Serve -> Receive) to disambiguate visual forms fails catastrophically, tanking recall due to cascade failures.

### Open
- How can we stop the massive over-prediction of events (`invented` ~400) if semantic vetoes ("is it warmup?"), strict visual constraints, and reasoning tokens all fail?
- Given the strict limit of 5 fps, can explicit text instructions to look for indirect cues (like sudden trajectory changes) compensate for the missing kinetic frames of attacks and digs?

### Current hypothesis
The model hallucinates ~400 events because it cannot conceptually map spatial descriptors like "foreground" vs "background" or "main court" vs "other courts" well enough to ignore background matches. However, vision-language models are highly sensitive to relative object size in 2D space. We can suppress background hallucinations by defining the main court purely by pixel scale. By instructing the model to "ONLY report contacts made by LARGE players" and to "ignore all contacts by tiny/small players in the background," we translate an abstract depth-of-field concept into a direct 2D visual attribute. This should drastically cut `invented` events and boost Precision/F1 without relying on failed semantic logic or reasoning tokens.
