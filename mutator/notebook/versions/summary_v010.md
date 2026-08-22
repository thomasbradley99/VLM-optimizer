# What I know about this pipeline

### Established
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the 20-30 range (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes and back-row attacks with serves. This is a severe visual reflex that ignores descriptive text.
- **Strict negative vetoes reduce recall:** Adding intermediate JSON reasoning fields or strict negative visual vetoes (like "NEVER a serve if inward" or "ONLY happens from a dead ball") causes the model to drop True Positives across the board. The model's visual perception is too fuzzy to handle rigid visual disqualifiers.
- **The top of the frame is critical:** The upper third of the video cannot be cropped, as it contains the ball in flight during high arcs. Losing sight of the ball breaks the model's ability to track the rally.
- **Logical dependencies cause cascade failures:** Defining events by structural flow (e.g., "a receive handles a serve") causes massive drops in recall. If the model misses the antecedent event in 5fps video, the logical dependency forces it to suppress valid subsequent events.

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
- **Local sequence logic / Structural flow:** Instructing the model to use the immediate natural transitions of a rally (Serve -> Receive) to disambiguate visual forms fails catastrophically, tanking recall due to cascade failures when antecedent events are missed.

### Open
- If all manual heuristics (spatial, temporal, kinematic, and sequential) fail or actively harm recall, how can we improve the model's accuracy on visually similar classes like serve/receive?
- Will stripping away all our complex textual constraints paradoxically improve performance by letting the model rely purely on its pre-trained visual priors?

### Current hypothesis
The prompt has become overly engineered. We have hit a wall attempting to constrain the model's visual errors using text-based heuristics (spatial boundaries, kinematic poses, dead ball logic, sequence flow). Every constraint we add lowers True Positives because the model misapplies these strict logical rules to fuzzy 5fps video.

The most promising next step is a "Minimalist Prompt". We should strip away all logical, sequential, and descriptive constraints for `serve`, `receive`, `dig`, `attack`, `kill`, and `block`—providing only the bare class names and relying entirely on Gemini's pre-trained visual priors for what these actions look like. The only constraint we will keep is the `set` = "assist" rule, as that is a definitional mapping issue rather than a visual one, and has empirically proven to stabilize predictions without hurting recall.
