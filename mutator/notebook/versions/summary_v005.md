# What I know about this pipeline

### Established
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable around ~30 (down from 144 originally), matching the ground truth's definition of assists and preventing them from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent perception failure:** The model heavily confuses deep-court defensive passes with serves, over-predicting serves by ~75+ instances. This is a severe visual and conceptual failure that ignores all descriptive text.

### Ruled out
- **Sequence language causing serve/receive mixups:** Defining events by their sequence order ("first contact", "second contact") does not help. Removing sequence language did not fix the serve over-prediction and worsened `receive_f1`.
- **Clips starting mid-rally causing serve over-prediction:** Explicitly warning the model that clips start mid-rally and forbidding inside-court serves had no effect on serve over-prediction. The model cannot reliably use court lines to veto serves.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" and a receive as an "underhand bump" failed to suppress hallucinated serves. The model cannot parse fine-grained player poses well enough to use them as a negative filter.
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **Per-Team possession framework / Sequence cascade:** The theory that the model was suffering from an "off-by-one" global sequence cascade was wrong. Reframing the logic to evaluate "per-team possessions" failed to drop serve predictions (120 -> 128) and did not fix the downstream `attack` labels.

### Open
- How do we override a pre-trained visual heuristic that ignores all definition-based constraints?
- Will forcing the model to output a reasoning step or a game-state flag (like `is_dead_ball`) before classifying the action force it to apply logic over visual bias?

### Current hypothesis
The model is engaging in "lazy classification", relying purely on its pre-trained visual bias (e.g., "backcourt hit = serve") and skimming right past our definitional constraints (spatial, kinematic, trajectory, and possession). To break this, we must change the *instruction architecture* rather than just tweaking the definitions. By forcing an intermediate reasoning step or classification flag *before* it outputs the `type` (for example, asking it to explicitly evaluate a `prior_state` or `action_reason` flag to note if the ball was dead or alive before the contact), we can force the model to evaluate the game state logically rather than visually. This Chain-of-Thought approach will act as a cognitive speedbump, preventing it from reflexively outputting `serve` on every live-ball deep-court pass.
