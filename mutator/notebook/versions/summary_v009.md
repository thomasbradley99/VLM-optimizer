# What I know about this pipeline

### Established
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the 20-30 range (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes and back-row attacks with serves. This is a severe visual reflex that ignores descriptive text.
- **Strict negative vetoes reduce recall:** Adding intermediate JSON reasoning fields or strict negative visual vetoes (like "NEVER a serve if inward" or "ONLY happens from a dead ball") causes the model to drop True Positives across the board. The model's visual perception is too fuzzy to handle rigid visual disqualifiers.
- **The top of the frame is critical:** The upper third of the video cannot be cropped, as it contains the ball in flight during high arcs. Losing sight of the ball breaks the model's ability to track the rally.

### Ruled out
- **Hard cropping the background:** Physically cropping the top 330 pixels to hide background matches reduces false positives, but it ruins foreground recall by hiding the ball during high passes.
- **Sequence language causing serve/receive mixups:** Defining events by their global sequence order ("first contact", "second contact") does not help.
- **Clips starting mid-rally causing serve over-prediction:** Explicitly warning the model that clips start mid-rally and forbidding inside-court serves had no effect on serve over-prediction.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" failed to suppress hallucinated serves. The model cannot parse fine-grained player poses well enough to use them as a negative filter.
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **Per-Team possession framework:** The theory that the model was suffering from an "off-by-one" global sequence cascade was wrong. Reframing the logic to evaluate "per-team possessions" failed.
- **Explicit negative vetoes on state:** Telling the model that a serve "ONLY happens from a dead ball" failed entirely to drop serve predictions. The model ignores textual vetoes that contradict its visual bias.
- **JSON Chain-of-Thought for visual state:** Forcing the model to explicitly output whether the ball was "dead" or "in-flight" before the `type` field dropped some hallucinated serves, but it ruined overall recall and lowered F1 because the visual state of the ball is too ambiguous.
- **2D screen topology:** Restricting serves to the "extreme left or right edge of the video frame" failed to correct serve over-prediction and merely caused True Positives to drop. The model cannot reliably map 2D frame anchors to the action.

### Open
- How can we distinguish visually identical actions (like jump serves vs. back-row attacks, or receives vs. digs) without relying on fine-grained kinematics or strict negative visual vetoes, which we know hurt recall?
- Can the model successfully track the flow of a rally using local transitions (e.g., Action A leads to Action B) if we explicitly teach it those transitions instead of explicitly forbidding them?

### Current hypothesis
The prompt currently forbids the model from using sequence logic ("Do not enforce global sequences... Classify each event purely by its visual action"). However, volleyball event classes are defined by their structural context—where the ball just came from—not just how the player moves. A receive is defined by handling a serve; a dig handles an attack; a back-row attack is hit from a teammate's pass, while a serve is unassisted. By stripping away natural sequence logic and forcing pure visual classification, we actively blind the model to the only logical way to distinguish a bump pass (receive vs dig) or a back-row jump (serve vs attack). 

We must remove the anti-sequence instructions and explicitly encourage the model to use the immediate local context (the natural transitions of a rally, such as Serve -> Receive or Attack -> Dig/Block) as its primary discriminator, allowing it to classify based on structural flow rather than ambiguous visual forms.
