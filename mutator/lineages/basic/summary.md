# What I know about this pipeline

### Established
- **Definitional mismatches drive major errors:** The ground truth scout uses strict criteria where a "set" is only an assist preceding a kill, and a "kill" is specifically a point-scoring attack. Explaining this to the model fixed massive imbalances in early iterations.
- **Cropping the top of the frame destroys main-court context:** Attempting to hide background courts by physically cropping the top 330 pixels caused a massive loss in true positives (223 down to 173). The top area is strictly required to track the ball's high trajectory.
- **Semantic "background/foreground" filters suppress valid play:** Asking the model to ignore the background and focus on the "foreground court" causes it to ignore the far side of the main court entirely.
- **Explicitly defining full court boundaries mitigates some spatial blind spots:** Adding baselines and the far side back to the prompt recovers some missing serves, but complex geometric text definitions still confuse the model.
- **Spatial anchoring unlocks rare events:** Providing physical reference points in definitions (e.g., explicitly defining a block as happening "at the net") allows the model to identify classes it previously ignored.
- **Sequence logic is a necessary crutch:** Decoupling the model's predictions from sequential context (by telling it to ignore "order in the clip") destroys recall. Left with only raw, isolated physical action, the model loses confidence and misses spike heavily (missed events jumped from 254 to 301, TP fell to 150).

### Ruled out
- **Generic volleyball definitions for "set" and "kill":** Using standard definitions without qualification causes the model to over-predict sets and under-predict kills, wrecking precision.
- **Strict spatial cropping to remove background courts:** We cannot blindly crop the top of the frame to hide the other matches, as the vertical space is required for the main match ball trajectory.
- **Prompting the model to ignore intermediate touches (passes/sets):** Asking the model to selectively skip mid-rally touches breaks its sequence understanding and drops true positives. 
- **Imposing a rigid chronological sequence:** Instructing the model to expect a strict "Serve -> Receive -> Pass..." flow causes massive drops in recall. Because chunks start mid-rally, the model cannot map the required sequence and defaults to skipping valid events.
- **Using "background" or "foreground" terminology:** The model conflates depth with these terms, leading it to classify the far side of the main court as "background" and ignore it.
- **Explicitly warning against sequence assumptions:** Telling the model "DO NOT assume the first contact... label based on physical action, not its order" slightly helps receive precision but crushes overall F1 by making the model too hesitant to label ambiguous touches.

### Open
- **Uniform colors:** Could explicitly defining the jersey colors of the main match teams prevent the model from tracking players on adjacent courts without requiring destructive spatial rules?
- **Separating the player from the ball:** If semantic depth and rigid geometry fail, is there a simpler way to enforce that valid players reside in the lower half of the frame without triggering the model to ignore high ball trajectories?

### Current hypothesis
Every attempt to manipulate the model's sequential logic or enforce spatial geometry (via cropping or text) has resulted in severe drops in True Positives. The model needs a clean, simple prompt that allows it to use its natural event-tracking flow without being burdened by complex exclusion rules.

The single most promising next line of attack is to revert to our strongest clean baseline (Iteration 5) and attack the background noise strictly through visual subject filtering: explicitly defining the jersey colors of the primary court teams. Identifying teams by color is a native strength of vision models and avoids the catastrophic recall drops caused by temporal and spatial prompt hacking.
