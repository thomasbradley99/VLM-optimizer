# What I know about this pipeline

### Established
- **Definitional mismatches drive major errors:** The ground truth scout uses strict criteria where a "set" is only an assist preceding a kill, and a "kill" is specifically a point-scoring attack. Explaining this to the model fixed massive imbalances in an earlier iteration (sets dropped from 151 to 43; kills rose from 29 to 58).
- **Prompting away casual touches works:** Instructing the model to ignore normal passes and dead-time touches successfully removes a large chunk of ghost predictions.
- **Cropping the top of the frame destroys main-court context:** Attempting to hide background courts by cropping the top 330 pixels caused a massive loss in true positives (223 down to 173) and increased missed events (216 up to 255). The top area is strictly required to track the ball's high trajectory and the far-side players. Reverting to full 1920x1080 immediately restored our baseline (TP 223).

### Ruled out
- **Generic volleyball definitions for "set" and "kill":** Using standard definitions without qualification causes the model to over-predict sets (by reporting every overhand pass) and under-predict kills (by lumping them in with attacks), wrecking precision.
- **Strict spatial cropping to remove background courts:** We cannot blindly crop the top of the frame to hide the other matches, as the vertical space is required to track the ball during the main match.

### Open
- **Source of remaining ghosts:** With the uncropped frame, we have 260 invented events. Are these players warming up, dead-ball touches, or events correctly identified but belonging to the background matches?
- **Cause of class confusion:** We have over 100 predictions that match a ground truth timestamp but have the wrong class. Is it confusing digs vs. receives, or attacks vs. blocks?
- **The block anomaly:** `block_f1` actually improved during the top-crop (from 0.08 to 0.20). Does limiting the vertical field of view help the model identify net play? If so, can we achieve this without losing the ball trajectory?

### Current hypothesis
The background matches are still generating massive amounts of invented ghost events, but we cannot crop them out physically without losing the ball. We should explicitly instruct the model in the prompt to focus ONLY on the main volleyball court in the foreground and completely ignore the matches happening on the courts in the background. This semantic filter should achieve the desired reduction in invented events (cutting down the 260 ghosts) while keeping the full frame intact so we don't sacrifice true positives.
