# What I know about this pipeline

### Established
- The model naturally over-predicts events, largely by logging contacts during dead time and watching background matches.
- Instructing the model to focus on "DURING LIVE PLAY ONLY" successfully reduces dead-time ghost events.
- Background matches in the top half of the frame generate hundreds of false positives. Cropping them out (e.g., `crop="1920:620:0:330"`) drops `invented` events dramatically (430 -> 286).
- Outcome-dependent prompt rules (e.g., classifying a set based on a future kill) destroy recall. Applying these rules previously caused true positives to drop by ~40 events.

### Ruled out
- Using strict conditional logic to align definitions (e.g., "only log a set if it leads to a kill"). The model cannot reliably evaluate these rules because the necessary context (the ultimate result of the attack) often falls outside the current temporal chunk, causing it to drop the event entirely.
- Assuming aggressive top-cropping is harmless to the main court. Cutting the top 330 pixels cost us 23 true positives, proving that the model relies on tracking the ball high into the air to identify events. 

### Open
- Is there a "goldilocks" crop geometry (e.g., `y=200`) that obscures background matches without clipping high passes on the main court?
- Can we fully recover our lost recall just by rewriting the prompt, or is a wider field of view strictly necessary?

### Current hypothesis
The single most promising next line of attack is to rewrite the prompt to use standard, causally independent definitions of events (e.g., "set: an intentional pass directed to an attacker"). We are currently paying a severe recall penalty for the outcome-dependent definition of "set" introduced in Iteration 0. By reverting to simple, observable definitions, we can recover the true positives lost in earlier rounds, relying on the new crop configuration to keep background ghost events suppressed.
