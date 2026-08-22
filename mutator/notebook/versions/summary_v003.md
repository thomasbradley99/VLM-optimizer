# What I know about this pipeline

### Established
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the low 30s (down from 144 originally), matching the ground truth's definition of assists and preventing them from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent perception failure:** The model heavily confuses deep-court passes with serves, over-predicting serves by ~75+ instances. This is a severe visual failure that resists logical, spatial, and kinematic corrections.

### Ruled out
- **Sequence language causing serve/receive mixups:** Defining events by their sequence order ("first contact", "second contact") does not help. Removing sequence language did not fix the serve over-prediction (130 -> 123) and actually worsened `receive_f1`.
- **Clips starting mid-rally causing serve over-prediction:** Explicitly warning the model that clips start mid-rally and forbidding inside-court serves had no effect on serve over-prediction (123 -> 126) and harmed `receive_f1` (0.147 -> 0.121). The model cannot reliably use court lines to veto serves.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" and a receive as an "underhand bump" failed to suppress hallucinated serves (126 -> 126). The model cannot parse fine-grained player poses well enough to use them as a negative filter.

### Open
- Since spatial constraints (court lines), logical sequence rules, and kinematic constraints (player body movements) all completely fail to stop the model from labeling deep-court passes as serves, what visual features *can* the model actually see at this resolution?
- Does the model track the ball's trajectory better than it tracks the player's body or position? 

### Current hypothesis
The model relies on a crude heuristic—"a player hitting the ball from the back of the court is a serve"—and is functionally blind to the court lines, game state logic, and fine player kinematics (tosses) that we have tried to use to break this heuristic. Since we cannot rely on the *player's location* or *player's body movement*, we must rely on the **ball's trajectory**.

While the model struggles with static lines and fast body poses, it generally tracks macro motion well. A serve is distinct in its outcome: the ball travels far and flat across the net to the opponent's side. A receive or dig is a defensive pass where the ball pops high into the air and stays on the *same* side of the net for a teammate. By redefining these events strictly by the resulting ball flight path (e.g., "serve: ball goes over the net", "receive: ball pops high up on the same side"), we can leverage the visual feature the model is most likely to actually perceive, finally splitting the serve/receive confusion.
