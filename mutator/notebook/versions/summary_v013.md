# What I know about this pipeline

# What I know about this pipeline

### Established
- **Shorter chunks drastically improve recall (attention saturation):** Reducing clip length from 30s to 15s at 5fps (75 frames per call vs 150) caused True Positives to jump from 191 to 239 and `missed` to drop from 229 to 169. The model loses track of events when processing longer videos with more frames, demonstrating a strict attention/context bottleneck.
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the 20-30 range (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes and back-row attacks with serves. This is a severe visual reflex that ignores descriptive text.
- **Strict negative vetoes reduce recall:** Adding intermediate JSON reasoning fields or strict negative visual vetoes (like "NEVER a serve if inward" or "ONLY happens from a dead ball") causes the model to drop True Positives across the board. The model's visual perception is too fuzzy to handle rigid visual disqualifiers.
- **The top of the frame is critical:** The upper third of the video cannot be cropped, as it contains the ball in flight during high arcs. Losing sight of the ball breaks the model's ability to track the rally.
- **Logical dependencies cause cascade failures:** Defining events by structural flow (e.g., "a receive handles a serve") causes massive drops in recall. If the model misses the antecedent event in 5fps video, the logical dependency forces it to suppress valid subsequent events.
- **Verbose definitions inflate false positives:** Highly detailed text descriptions of physical actions cause the model to hallucinate events by matching partial visual cues. Removing them drops `invented` events significantly, though it does not improve recall.

### Ruled out
- **10 FPS at 30-second chunks:** Doubling the frame rate to 10 fps while keeping the chunk length at 30 seconds results in 300 frames per API call. This causes catastrophic system failures (39 failed chunks), likely due to payload size limits or token constraints, resulting in a massive drop in total predictions and recall.
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
- Now that we know 15-second chunks improve recall, will doubling the frame rate to 10fps in a 15-second chunk (150 frames) improve perception of fast actions, or will it cause the same attention saturation we saw with 30-second 5fps chunks (which also had 150 frames)?

### Current hypothesis
We can now safely test 10 fps to see if it fixes the temporal blurring of fast volleyball strikes. By changing `fps: 10` on our new `chunk_len: 15.0` baseline, we will send the model exactly 150 frames per chunk. This will test a crucial distinction: whether the attention saturation at 30s/5fps was caused by the *absolute number of frames* (150 frames overloading the context window) or by the *duration of the action* (30 seconds of highly dense gameplay being too much to remember). If recall drops, we know the model has a strict frame-count bottleneck; if recall rises, we know higher temporal resolution successfully clarifies fast kinematic actions.
