# What I know about this pipeline

### Established
- **`set` definition mismatch:** The ground truth predominantly contains sets that lead to kills (assists). Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully crashes the prediction count from 144 down to 27, stopping these predictions from greedily matching and stealing real attacks/digs.

### Ruled out
- **Sequence language causing serve/receive mixups:** I hypothesized that defining events by their sequence order ("first contact", "second contact") forced the model to label a receive as a serve if it missed the actual serve. Removing sequence language did not fix the serve over-prediction (130 -> 123) and actually worsened `receive_f1` (0.174 -> 0.147). The model is genuinely misclassifying these actions visually, not just blindly following a logical sequence counter.

### Open
- Why is the model predicting ~123 serves when there are only ~85 in reality? Is it classifying deep-court passes (receives/digs) as serves because of player positioning, or because it falsely assumes every clip begins with a serve?
- How does the model distinguish between `receive` (defending a serve) and `dig` (defending an attack) if it struggles to see the preceding event or misses the start of the rally?

### Current hypothesis
The model over-predicts serves and under-predicts receives because it misinterprets the start of the clip as the start of a rally. Clips are 30 seconds long and may begin mid-play; if the model assumes every rally starts with a serve, it will label the first deep-court action it sees (often a receive or dig) as a serve. 

The next step should be explicitly warning the model that clips may start mid-rally (so there might be no serve at all) and providing a strict visual kinematic description of a serve (a tossed ball hit from completely behind the back line) vs a receive (a passing motion, usually bumping with forearms, inside the court lines).
