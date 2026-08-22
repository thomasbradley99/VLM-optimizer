# What I know about this pipeline

### Established
- **Definitional mismatches drive major errors:** The ground truth scout uses strict criteria where a "set" is only an assist preceding a kill, and a "kill" is specifically a point-scoring attack. Explaining this to the model fixed massive imbalances in an earlier iteration (sets dropped from 151 to 43; kills rose from 29 to 58).
- **Cropping the top of the frame destroys main-court context:** Attempting to hide background courts by cropping the top 330 pixels caused a massive loss in true positives (223 down to 173) and increased missed events (216 up to 255). The top area is strictly required to track the ball's high trajectory and the far-side players.
- **The model needs full rally context to classify hits:** Instructing the model to ignore intermediate passes/sets destroys its ability to track a play. Doing so caused True Positives to tank (223 -> 174) and serve recall to drop (0.542 -> 0.39).

### Ruled out
- **Generic volleyball definitions for "set" and "kill":** Using standard definitions without qualification causes the model to over-predict sets (by reporting every overhand pass) and under-predict kills (by lumping them in with attacks), wrecking precision.
- **Strict spatial cropping to remove background courts:** We cannot blindly crop the top of the frame to hide the other matches, as the vertical space is required to track the ball during the main match.
- **Prompting the model to ignore intermediate touches (passes/sets):** Asking the model to skip the second touch of a rally breaks its understanding of the sequence. Rather than reducing over-prediction, it increases hallucinated/invented events (260 -> 282) because the model loses the logical chain linking a dig to an attack.

### Open
- **Source of remaining ghosts:** Even without the broken "ignore touches" instruction, the baseline produces ~260 invented events. Are these players warming up, dead-ball touches, or events correctly identified but belonging to the background matches?
- **Cause of class confusion:** We have over 100 predictions that match a ground truth timestamp but have the wrong class. Is it confusing digs vs. receives, or attacks vs. blocks?
- **The block anomaly:** `block_f1` actually improved during the top-crop (from 0.08 to 0.20) but fell to 0 in this run. Does limiting the vertical field of view help the model identify net play? If so, can we achieve this without losing the ball trajectory?

### Current hypothesis
The catastrophic failure of the intermediate-touch filter means we need to manually restore the Iteration 2 prompt configuration and attack the precision problem from a different angle. The background matches are likely generating massive amounts of invented ghost events. Since we cannot crop them out physically without losing the ball, we should explicitly instruct the model in the prompt to focus ONLY on the main volleyball court in the foreground and completely ignore the matches happening on the courts in the background. This semantic spatial filter should achieve the desired reduction in invented events without breaking the model's understanding of rally sequences.
