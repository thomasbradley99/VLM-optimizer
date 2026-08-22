# What I know about this pipeline

### Established
- **Definitional mismatches drive major errors:** The ground truth scout uses strict criteria where a "set" is only an assist preceding a kill, and a "kill" is specifically a point-scoring attack. Explaining this to the model fixed massive imbalances in an earlier iteration (sets dropped from 151 to 43; kills rose from 29 to 58).
- **Prompting away casual touches works:** Instructing the model to ignore normal passes and dead-time touches successfully removes a large chunk of ghost predictions.
- **Cropping the top of the frame destroys main-court context:** Attempting to hide background courts by cropping the top 330 pixels caused a massive loss in true positives (223 down to 173) and increased missed events (216 up to 255), likely because it cut off the ball's high trajectory or obscured players on the far side of the net.

### Ruled out
- **Generic volleyball definitions for "set" and "kill":** Using standard definitions without qualification causes the model to over-predict sets (by reporting every overhand pass) and under-predict kills (by lumping them in with attacks), wrecking precision.
- **Strict spatial cropping to remove background courts:** We cannot blindly crop the top of the frame to hide the other matches, as the vertical space is required to track the ball during the main match.

### Open
- **Source of remaining ghosts:** In the uncropped state, we have 260 invented events. Are these players warming up, dead-ball touches, or events correctly identified but belonging to the background matches?
- **Cause of class confusion:** We have over 100 predictions that match a ground truth timestamp but have the wrong class. Is it confusing digs vs. receives, or attacks vs. blocks?
- **Cause of false negatives:** In the uncropped state, we are missing 216 real events. Are they obscured by the camera angle, or simply invisible because they happen too fast for the 5 FPS frame rate?

### Current hypothesis
The background matches are still generating massive amounts of invented ghost events, but we cannot crop them out physically. We should revert to the uncropped video and explicitly instruct the model in the prompt to "focus ONLY on the main volleyball court in the foreground and completely ignore the matches happening on the courts in the background at the top of the frame." This should achieve the desired reduction in invented events without sacrificing the true positives on the main court.
