# What I know about this pipeline

### Established
- **Definitional mismatches drive major errors:** The ground truth scout uses strict criteria where a "set" is only an assist preceding a kill, and a "kill" is specifically a point-scoring attack. Explaining this to the model fixed massive imbalances in early iterations.
- **Cropping the top of the frame destroys main-court context:** Attempting to hide background courts by cropping the top 330 pixels caused a massive loss in true positives (223 down to 173) and increased missed events (216 up to 255). The top area is strictly required to track the ball's high trajectory.
- **Spatial anchoring unlocks rare events:** Providing physical reference points in definitions (e.g., explicitly defining a block as happening "at the net") allows the model to identify classes it previously ignored, bringing `block_f1` from 0 up to 0.222.

### Ruled out
- **Generic volleyball definitions for "set" and "kill":** Using standard definitions without qualification causes the model to over-predict sets and under-predict kills, wrecking precision.
- **Strict spatial cropping to remove background courts:** We cannot blindly crop the top of the frame to hide the other matches, as the vertical space is required for the main match ball trajectory.
- **Prompting the model to ignore intermediate touches (passes/sets):** Asking the model to skip the second touch of a rally breaks its sequence understanding. Rather than reducing over-prediction, it increases hallucinated events (260 -> 282) because the model loses the logical chain linking a dig to an attack.
- **Imposing a rigid chronological sequence:** Instructing the model to expect a strict "Serve -> Receive -> Pass -> Attack -> Dig" flow causes massive drops in recall (True Positives falling to 163). Because the pipeline processes 30-second chunks that often start mid-rally, the model cannot map the required sequence and defaults to skipping valid events.

### Open
- **Source of remaining ghosts:** Even in the best runs, the model produces ~260 invented events. Are these players warming up, dead-ball touches, or simply perfect predictions of events happening on the adjacent background courts?
- **Class confusion vs missed events:** When a chunk starts mid-rally, does the model simply misclassify the first touch as a "serve", or does it drop the touch entirely?

### Current hypothesis
The attempt to filter out noise using rally logic (skipping touches, enforcing sequences) has consistently destroyed True Positives. The massive volume of invented events (~260-280) is most likely caused by the model diligently tracking the matches happening on the courts in the background. Since we proved in Iteration 3 that we cannot physically crop the background out, the single most promising next step is a semantic spatial filter. We should manually revert the prompt to the successful Iteration 2 baseline, and add a single, strong instruction for the model to entirely ignore the background courts and focus strictly on the players inside the prominent foreground court lines.
