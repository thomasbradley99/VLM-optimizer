# What I know about this pipeline

### Established
- **`set` definition mismatch:** The ground truth predominantly contains sets that lead to kills (assists). Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully crashes the prediction count from 144 down to ~27, stopping these predictions from greedily matching and stealing real attacks/digs.
- **Serve vs. Receive is a visual, not logical, failure:** The model heavily confuses deep-court passes with serves, missing 72 real serves while inventing ~77. This is a visual perception issue, not a logical one.

### Ruled out
- **Sequence language causing serve/receive mixups:** I hypothesized that defining events by their sequence order ("first contact", "second contact") forced the model to label a receive as a serve if it missed the actual serve. Removing sequence language did not fix the serve over-prediction (130 -> 123) and actually worsened `receive_f1`.
- **Clips starting mid-rally causing serve over-prediction:** I hypothesized the model falsely assumes the first action in a clip is a serve. Explicitly warning it that clips start mid-rally and forbidding inside-court serves had no effect on serve over-prediction (123 -> 126) and harmed `receive_f1` (0.147 -> 0.121). The model cannot reliably use court lines to veto serves.

### Open
- Since spatial constraints (e.g., "behind the end line", "inside the court lines") and logical sequences fail, what visual cues CAN the model recognize to separate a serve from a receive/dig? 
- How does the model distinguish between `receive` (defending a serve) and `dig` (defending an attack) if it misses the preceding action, and can we give it a heuristic to fall back on?

### Current hypothesis
The model relies heavily on a player's general location in the backcourt to predict `serve`, ignoring court lines because it struggles to parse them spatially. Since spatial logic failed, the most promising next line of attack is defining events by their **kinematics** (body movements). 

A serve uniquely requires the player to toss the ball into the air before striking it with an overhead swing. A receive or dig is a reactive motion, typically an underhand bump with the forearms. By defining these actions strictly via the player's physical movements (e.g., "a toss and overhead strike" vs. "an underhand bump") rather than their logical purpose or location on the court, we can bypass the model's poor spatial reasoning and rely instead on its ability to recognize human poses.
