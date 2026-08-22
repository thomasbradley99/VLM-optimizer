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
- **10 FPS temporal resolution:** Whether at 30-second chunks or 15-second chunks, requesting 10 fps causes massive API failures. The system cannot reliably handle 10 fps video extraction. We are strictly bound to 5 fps.
- **Minimalist prompt to increase recall:** Stripping event definitions down to bare class names did not cause the model to stop dropping true events. 
- **Hard cropping the background:** Physically cropping the top 330 pixels to hide background matches reduces false positives, but it ruins foreground recall by hiding the ball during high passes.
- **Sequence language causing serve/receive mixups:** Defining events by their global sequence order ("first contact", "second contact") does not help.
- **Clips starting mid-rally causing serve over-prediction:** Explicitly warning the model that clips start mid-rally and forbidding inside-court serves had only marginal effect on serve over-prediction.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" failed to suppress hallucinated serves. 
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **Per-Team possession framework:** Reframing the logic to evaluate "per-team possessions" failed.
- **Explicit negative vetoes on state:** Telling the model that a serve "ONLY happens from a dead ball" failed entirely to drop serve predictions. 
- **JSON Chain-of-Thought for visual state:** Forcing the model to explicitly output whether the ball was "dead" or "in-flight" before the `type` field dropped recall and lowered F1 because the visual state of the ball is too ambiguous.
- **2D screen topology:** Restricting serves to the "extreme left or right edge of the video frame" failed to correct serve over-prediction and merely caused True Positives to drop. 
- **Local sequence logic / Structural flow:** Instructing the model to use the immediate natural transitions of a rally (Serve -> Receive) to disambiguate visual forms fails catastrophically, tanking recall due to cascade failures when antecedent events are missed.

### Open
- Given the strict limit of 5 fps, how can we help the model detect fast actions (like spikes and digs) that fall entirely between the 200ms frame gaps? Can explicit text instructions to look for indirect cues compensate for low temporal resolution?
- How can we stop the massive over-prediction of events (`invented` > 400) if semantic vetoes ("is it warmup?") and strict visual constraints both fail?

### Current hypothesis
Since we are permanently limited to 5 fps, the model will continue to miss fast kinetic contacts (attacks, digs) because they often fall entirely between frames. We must compensate for this missing visual data via the prompt. By explicitly instructing the model to *infer* fast contacts from secondary cues—such as a sudden change in ball trajectory, a player swinging their arm in mid-air, or a defender lunging—we can train it to spot the "ghosts" of these actions. This should increase recall for fast events like `attack` and `dig` without requiring higher frame rates or triggering cascade failures.
