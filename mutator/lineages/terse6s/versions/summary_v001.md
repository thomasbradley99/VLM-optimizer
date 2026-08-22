# What I know about this pipeline

### Established
- The model naturally over-predicts events (1080 raw predictions vs ~550 real events), largely driven by logging contacts during dead time and misclassifying basic mid-rally passes as sets. 
- Instructing the model to focus on "DURING LIVE PLAY ONLY" and explicitly ignore bouncing/passing between rallies successfully reduces ghost events (invented dropped 611 -> 430).
- Outcome-dependent prompt rules (e.g., classifying an action based on the result of the *next* action) destroy recall. Applying these rules caused true positives to drop (312 -> 273) and misses to spike (81 -> 144).

### Ruled out
- Using strict conditional logic to align definitions (e.g., "only log a set if it leads to a kill"). The model cannot reliably evaluate these rules, likely because the necessary context (the ultimate result of the attack) often falls outside the current temporal chunk, causing it to drop the event entirely.

### Open
- How to properly define a "set" in the scout's ontology so the model doesn't over-report them, without relying on the ultimate outcome of the rally. 
- Why `serve_recall` slightly improved (0.585 -> 0.610) despite the overall drop in recall (perhaps purging false dead-time events reduced confusion at the immediate start of rallies?).

### Current hypothesis
The model performs best with simple, causally independent definitions of events. We can recover the lost true positives while keeping ghost events low by rewriting the prompt to use standard, observable volleyball definitions (e.g., "set: an intentional pass directed to an attacker") while retaining the strong structural constraint to ignore dead-time play.
