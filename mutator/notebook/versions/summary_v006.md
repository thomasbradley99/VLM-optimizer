# What I know about this pipeline

### Established
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable around ~30 (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes with serves, over-predicting serves by ~75+ instances. This is a severe visual reflex that ignores descriptive text.

### Ruled out
- **Sequence language causing serve/receive mixups:** Defining events by their sequence order ("first contact", "second contact") does not help. 
- **Clips starting mid-rally causing serve over-prediction:** Explicitly warning the model that clips start mid-rally and forbidding inside-court serves had no effect on serve over-prediction.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" and a receive as an "underhand bump" failed to suppress hallucinated serves. The model cannot parse fine-grained player poses well enough to use them as a negative filter.
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **Per-Team possession framework:** The theory that the model was suffering from an "off-by-one" global sequence cascade was wrong. Reframing the logic to evaluate "per-team possessions" failed to drop serve predictions.
- **Explicit negative vetoes on state:** Telling the model that a serve "ONLY happens from a dead ball" and hitting an incoming ball is "NEVER a serve" failed entirely to drop serve predictions (128 -> 131). The model completely ignores textual vetoes that contradict its visual bias.

### Open
- Can forcing the model to explicitly state the game state in the JSON output *before* classifying the action bypass its pre-trained visual biases?

### Current hypothesis
The model suffers from "lazy classification," relying purely on pre-trained visual bias (e.g., "backcourt hit = serve") and skimming right past textual constraints. Because no amount of capitalized text in the prompt alters this behavior, we must change the *JSON schema*. By adding an intermediate reasoning field (like `ball_starting_state`: "dead" or "in-flight from opponent") that the model must output *before* it outputs the `type` field, we will force a Chain-of-Thought that evaluates the context of the hit before the classification reflex kicks in. This structural speedbump is the only remaining way to stop it from reflexively outputting `serve` on every live-ball deep-court pass.
