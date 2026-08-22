# What I know about this pipeline

### Established
- **Definitional mismatches drive major errors:** The ground truth scout uses strict criteria where a "set" is only an assist preceding a kill, and a "kill" is specifically a point-scoring attack. Explaining this to the model fixed massive imbalances in early iterations.
- **Cropping the top of the frame destroys main-court context:** Attempting to hide background courts by physically cropping the top 330 pixels caused a massive loss in true positives (223 down to 173). The top area is strictly required to track the ball's high trajectory.
- **Semantic "background/foreground" filters suppress valid play:** Asking the model to ignore the background and focus on the "foreground court" causes it to ignore the far side of the main court entirely.
- **Explicitly defining full court boundaries mitigates some spatial blind spots:** Adding baselines and the far side back to the prompt recovers some missing serves, but complex geometric text definitions still confuse the model.
- **Spatial anchoring unlocks rare events:** Providing physical reference points in definitions (e.g., explicitly defining a block as happening "at the net") allows the model to identify classes it previously ignored.

### Ruled out
- **Generic volleyball definitions for "set" and "kill":** Using standard definitions without qualification causes the model to over-predict sets and under-predict kills, wrecking precision.
- **Strict spatial cropping to remove background courts:** We cannot blindly crop the top of the frame to hide the other matches, as the vertical space is required for the main match ball trajectory.
- **Prompting the model to ignore intermediate touches (passes/sets):** Asking the model to selectively skip mid-rally touches breaks its sequence understanding and drops true positives. (Tested in Iteration 4, accidentally re-confirmed in Iteration 6).
- **Imposing a rigid chronological sequence:** Instructing the model to expect a strict "Serve -> Receive -> Pass..." flow causes massive drops in recall. Because chunks start mid-rally, the model cannot map the required sequence and defaults to skipping valid events.
- **Using "background" or "foreground" terminology:** The model conflates depth with these terms, leading it to classify the far side of the main court as "background" and ignore it.

### Open
- **Separating the player from the ball:** If we cannot crop the frame or use semantic depth words, can we successfully filter based on where the *player* is standing (the bottom half/two-thirds of the screen) while allowing the ball to travel anywhere?
- **Uniform colors:** Could explicitly defining the jersey colors of the main match teams prevent the model from tracking players on adjacent courts?

### Current hypothesis
Complex spatial geometry (e.g., "bottom 3/4 of the screen") and depth terminology (e.g., "foreground") confuse the model and destroy recall because they inadvertently cause the model to ignore parts of the main match. However, while the ball flies high into the upper frame, the *player making contact with the ball* in the main match is always positioned in the lower portion of the screen (even when on the far side of the net). 

The single most promising next line of attack is to drop all court geometry terminology, restore clean class definitions (without asking it to skip passes), and add a simple, explicit rule: a valid event only occurs if the *player striking the ball* is physically located in the bottom two-thirds of the image, completely ignoring any players standing in the top third.
