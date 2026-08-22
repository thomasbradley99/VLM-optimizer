# What I know about this pipeline

### Established
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the 20-30 range (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes with serves, consistently over-predicting serves. This is a severe visual reflex that ignores descriptive text.
- **Visual reasoning fields reduce recall:** Adding intermediate JSON fields to force Chain-of-Thought reasoning on ambiguous visual cues (like ball trajectory/state) causes the model to drop events entirely if it lacks confidence, severely hurting True Positives across all classes.

### Ruled out
- **Sequence language causing serve/receive mixups:** Defining events by their sequence order ("first contact", "second contact") does not help.
- **Clips starting mid-rally causing serve over-prediction:** Explicitly warning the model that clips start mid-rally and forbidding inside-court serves had no effect on serve over-prediction.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" failed to suppress hallucinated serves. The model cannot parse fine-grained player poses well enough to use them as a negative filter.
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **Per-Team possession framework:** The theory that the model was suffering from an "off-by-one" global sequence cascade was wrong. Reframing the logic to evaluate "per-team possessions" failed.
- **Explicit negative vetoes on state:** Telling the model that a serve "ONLY happens from a dead ball" failed entirely to drop serve predictions. The model ignores textual vetoes that contradict its visual bias.
- **JSON Chain-of-Thought for visual state:** Forcing the model to explicitly output whether the ball was "dead" or "in-flight" before the `type` field successfully dropped some hallucinated serves, but it ruined overall recall and lowered F1 because the visual state of the ball is too ambiguous to reliably evaluate as a strict prerequisite.

### Open
- Since the model struggles to parse the ball's historical state (dead vs in-flight) and ignores negative textual vetoes, what visual proxy can reliably disambiguate a serve from a deep-court pass without forcing a costly reasoning step?
- Can we leverage 2D screen topology (zoning) given the fixed camera angle?

### Current hypothesis
The model cannot reliably evaluate the ball's kinematic state, but a static camera provides highly reliable spatial framing. Serves have a strict, absolute spatial property in this frame: they only occur at the extreme baseline (the far left or far right edges of the screen). By contrast, receives occur visibly further inward, inside the court lines. Since the model struggles with state-based and trajectory-based rules, we should shift to a purely spatial constraint. We can define `serve` as an action occurring at the "extreme left or right edge of the frame," and `receive` as an action occurring "inside the court lines." Spatial anchoring is an immediate, single-frame visual cue that avoids the temporal ambiguity of "was the ball dead?" and shouldn't require complex JSON reasoning fields.
