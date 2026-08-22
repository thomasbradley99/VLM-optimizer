# What I know about this pipeline

# What I know about this pipeline

### Established
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the 20-30 range (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes and back-row attacks with serves. This is a severe visual reflex that ignores descriptive text.
- **Strict negative vetoes reduce recall:** Adding intermediate JSON reasoning fields or strict negative visual vetoes (like "NEVER a serve if inward" or "ONLY happens from a dead ball") causes the model to drop True Positives across the board. The model's visual perception is too fuzzy to handle rigid visual disqualifiers.
- **The top of the frame is critical:** The upper third of the video cannot be cropped, as it contains the ball in flight during high arcs. Losing sight of the ball breaks the model's ability to track the rally.
- **Logical dependencies cause cascade failures:** Defining events by structural flow (e.g., "a receive handles a serve") causes massive drops in recall. If the model misses the antecedent event in 5fps video, the logical dependency forces it to suppress valid subsequent events.
- **Verbose definitions inflate false positives:** Highly detailed text descriptions of physical actions cause the model to hallucinate events by matching partial visual cues. Removing them drops `invented` events significantly, though it does not improve recall.

### Ruled out
- **Minimalist prompt to increase recall:** Stripping event definitions down to bare class names did not cause the model to stop dropping true events. True Positives stayed flat, proving that low recall is a perceptual failure, not a text-based rule suppression issue.
- **Hard cropping the background:** Physically cropping the top 330 pixels to hide background matches reduces false positives, but it ruins foreground recall by hiding the ball during high passes.
- **Sequence language causing serve/receive mixups:** Defining events by their global sequence order ("first contact", "second contact") does not help.
- **Clips starting mid-rally causing serve over-prediction:** Explicitly warning the model that clips start mid-rally and forbidding inside-court serves had no effect on serve over-prediction.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" failed to suppress hallucinated serves. The model cannot parse fine-grained player poses well enough to use them as a negative filter.
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **Per-Team possession framework:** The theory that the model was suffering from an "off-by-one" global sequence cascade was wrong. Reframing the logic to evaluate "per-team possessions" failed.
- **Explicit negative vetoes on state:** Telling the model that a serve "ONLY happens from a dead ball" failed entirely to drop serve predictions. The model ignores textual vetoes that contradict its visual bias.
- **JSON Chain-of-Thought for visual state:** Forcing the model to explicitly output whether the ball was "dead" or "in-flight" before the `type` field dropped some hallucinated serves, but it ruined overall recall and lowered F1 because the visual state of the ball is too ambiguous.
- **2D screen topology:** Restricting serves to the "extreme left or right edge of the video frame" failed to correct serve over-prediction and merely caused True Positives to drop. The model cannot reliably map 2D frame anchors to the action.
- **Local sequence logic / Structural flow:** Instructing the model to use the immediate natural transitions of a rally (Serve -> Receive) to disambiguate visual forms fails catastrophically, tanking recall due to cascade failures when antecedent events are missed.

### Open
- If neither highly engineered logical rules nor a bare minimalist prompt can push True Positives above the ~190 mark, is the model's perception fundamentally bottlenecked by the 5fps temporal resolution?

### Current hypothesis
We have exhausted text-based prompt engineering. Whether we use strict spatial bounds, kinematic poses, sequential logic, or absolutely no definitions at all, the model hits a hard ceiling of ~190 True Positives and ~220 missed events. The bottleneck is not instruction overload; it is visual resolution. 

Volleyball is a highly kinetic sport. At 5fps (200ms gaps between frames), fast actions like bullet serves, rapid digs, and quick blocks are likely occurring entirely between frames or are reduced to illegible motion blur. The model cannot accurately classify what it physically cannot see. The most promising next step is to improve the baseline visual signal by increasing the temporal resolution, changing the configuration to `fps: 10`.
