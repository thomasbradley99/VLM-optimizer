# What I know about this pipeline

### Established
- **Definitional mismatches drive major errors:** The ground truth scout uses a strict criteria where a "set" is only an assist preceding a kill, and a "kill" is specifically a point-scoring attack. Explaining this to the model fixes massive imbalances (sets dropped from 151 to 43; kills rose from 29 to 58).
- **Prompting away casual touches works:** Instructing the model to ignore normal passes and dead-time touches successfully removes a large chunk of ghost predictions (invented dropped from 312 to 260).

### Ruled out
- **Generic volleyball definitions for "set" and "kill":** Using standard definitions without qualification causes the model to over-predict sets (by reporting every overhand pass) and under-predict kills (by lumping them in with attacks), wrecking precision.

### Open
- **Source of remaining ghosts:** We still have 260 invented events. Are these players warming up, dead-ball touches the model refused to ignore, or hallucinations during live rallies?
- **Cause of class confusion:** We have 111 predictions that match a ground truth timestamp but have the wrong class. Is it confusing digs vs receives, or attacks vs blocks?
- **Cause of false negatives:** We are missing 216 real events. Are they obscured by the camera angle, or simply invisible because they happen too fast for the current frame rate?

### Current hypothesis
The low frame rate (5 FPS) is the primary bottleneck preventing the model from seeing rapid contacts like digs, receives, and blocks. Split-second touches are likely falling between frames or appearing as a blur, causing the model to miss them entirely (216 missed) or misclassify them (111 class errors). Increasing the FPS to 10 should provide the temporal resolution needed to catch these events, lowering the `missed` count and improving classification accuracy.
