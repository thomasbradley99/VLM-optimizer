# What I know about this pipeline

### Established
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the low 30s (down from 144 originally), matching the ground truth's definition of assists and preventing them from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent perception failure:** The model heavily confuses deep-court defensive passes with serves, over-predicting serves by ~75+ instances. This is a severe visual and conceptual failure.

### Ruled out
- **Sequence language causing serve/receive mixups:** Defining events by their sequence order ("first contact", "second contact") does not help. Removing sequence language did not fix the serve over-prediction (130 -> 123) and actually worsened `receive_f1`.
- **Clips starting mid-rally causing serve over-prediction:** Explicitly warning the model that clips start mid-rally and forbidding inside-court serves had no effect on serve over-prediction (123 -> 126) and harmed `receive_f1` (0.147 -> 0.121). The model cannot reliably use court lines to veto serves.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" and a receive as an "underhand bump" failed to suppress hallucinated serves (126 -> 126). The model cannot parse fine-grained player poses well enough to use them as a negative filter.
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions (126 -> 120) and actively worsened `receive_f1` (0.178 -> 0.142). The model's reflexive classification ignores macro-trajectory rules.

### Open
- How do we override a pre-trained visual heuristic that ignores all definition-based constraints?
- Will forcing the model to output a reasoning step or a game-state flag (like `is_dead_ball`) before classifying the action force it to apply logic over visual bias?

### Current hypothesis
The model is engaging in "lazy classification", relying purely on its pre-trained visual bias (e.g., "backcourt hit = serve") and skimming right past our definitional constraints (spatial, kinematic, and trajectory). To break this, we must change the *instruction architecture* rather than just tweaking the definitions. By forcing an intermediate reasoning step or classification flag *before* it outputs the `type` (for example, asking it to explicitly evaluate a `prior_state` flag to note if the ball was dead or alive before the contact), we can force the model to evaluate the game state sequentially. This Chain-of-Thought approach will act as a cognitive speedbump, preventing it from reflexively outputting `serve` on every live-ball deep-court pass.
