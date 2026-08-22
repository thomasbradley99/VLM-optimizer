# What I know about this pipeline

# What I know about this pipeline

### Established
- **Kinematic cues trump pure spatial rules for attacks/digs:** Defining an attack purely as "ANY contact that sends the ball OVER the net" causes the model to incorrectly log defensive free-ball overpasses as attacks. Providing kinematic cues (jumps/swings for attacks, low-to-the-ground reactions for digs) successfully fixes this confusion and reduces invented events.
- **Relaxing visual requirements for cut-off clips:** Because we use 6-second clips, actions like serve tosses often happen off-screen. Relaxing the strict requirement to see a "visible toss" significantly improves serve recall by allowing the model to infer the action from context.
- **Mutually exclusive events:** Forcing the model to output "EXACTLY ONE event type per physical ball contact" successfully stops it from outputting multiple labels for the exact same hit (e.g., `attack` and `kill`). This significantly drops `invented` events and improves F1.
- **Shorter chunks improve recall up to a point:** Reducing clip length to 6s (30 frames) maximizes True Positives by limiting attention saturation. Moving to 10s chunks (50 frames) causes severe attention saturation, tanking recall (TPs drop massively).
- **Mechanical reduction of chunks suppresses hallucinations:** Slicing the video into fewer API calls mechanically starves the model of opportunities to invent events in dead time. 
- **`set` definition mismatch:** Explicitly instructing the model to report `set` "ONLY if it directly leads to a kill" successfully keeps the prediction count stable in the 20-30 range (matching ground truth assists), preventing sets from greedily stealing real attacks/digs.
- **Serve vs. Receive is a persistent visual bias:** The model heavily confuses deep-court defensive passes and back-row attacks with serves. This is a severe visual reflex that ignores descriptive text.
- **Strict negative vetoes reduce recall:** Adding intermediate JSON reasoning fields, strict negative visual vetoes, or complex spatial rules causes the model to drop True Positives across the board. The model's visual perception is too fuzzy to handle rigid visual disqualifiers.
- **The top of the frame is critical:** The upper third of the video cannot be cropped, as it contains the ball in flight during high arcs. Losing sight of the ball breaks the model's ability to track the rally.
- **Verbose definitions inflate false positives:** Highly detailed text descriptions of physical actions cause the model to hallucinate events by matching partial visual cues.

### Ruled out
- **Toss vetoes:** Explicitly commanding the model "DO NOT log the ball toss as a contact" fails to shift serve timestamps forward. Serve predictions remain flat and overall recall drops. Negative visual vetoes ("Pink elephants") simply do not work.
- **Strict screen-based team attribution:** Forcing the model to strictly use the left/right half of the screen to determine the team `side` reduces true positives, likely because the camera angle isn't perfectly centered or players drift near the midline.
- **Explicit spatial attribution logic:** Adding complex instructions to "Log the side where the player HITS the ball, NOT where the ball lands" to fix team attribution backfires, tanking `kill_recall` and overall True Positives. 
- **Stationary hold & Defensive formation vetoes:** Attempting to stop serve hallucinations by requiring the server to start from a "stationary hold" or verifying the receiving team is in a "defensive formation" fails completely and actively drops recall.
- **"Pink Elephant" negative vetoes on serves:** Explicitly telling the model "If a player hits a ball that is already moving... it is NEVER a serve" failed completely, driving serve predictions UP.
- **Increasing chunk length to 10s+ to reduce hallucinations:** While 10s chunks mechanically reduce false positives, the 50-frame length induces unacceptable attention saturation and drops true positives massively. 
- **Semantic context vetoes ("Dead time veto"):** Telling the model to ignore warmups, dead time between points, or post-rally floor bounces does not work. Capitalized, verbose instructions actively increase false positives or destroy recall.
- **Reasoning tokens (Thinking / CoT):** Giving the model `thinking: "medium"` to reason about background courts and dead-ball context before generating JSON failed to reduce the ~400 hallucinated events. 
- **10 FPS temporal resolution:** Requesting 10 fps causes massive API failures. We are strictly bound to 5 fps.
- **Hard cropping the background:** Physically cropping the top 330 pixels to hide background matches reduces false positives, but it ruins foreground recall by hiding the ball during high passes.
- **Kinematic constraints (body poses):** Redefining a serve to require a "self-toss and overhead strike" failed to suppress hallucinated serves. 
- **Ball trajectory constraints:** Adding "OVER THE NET" for serves and "STAYS ON SAME SIDE" for receives/digs failed to drop serve predictions and actively worsened `receive_f1`.
- **JSON Chain-of-Thought for visual state:** Forcing the model to explicitly output whether the ball was "dead" or "in-flight" before the `type` field dropped recall and lowered F1.

### Open
- Given that we must use short 6-second chunks to avoid attention saturation, how much overlap is strictly necessary to prevent splitting contacts across chunks?
- Can we tighten NMS parameters to merge jittery hallucinated timestamps across overlapping clips?

### Current hypothesis
With prompt modifications yielding diminishing or negative returns, the focus must shift mechanically to overlapping windows. We are currently predicting ~664 events for ~435 actual ground truth events. A 6.0-second chunk with an `overlap` of 2.0 seconds means 33% of the match is processed twice. While True Positives merge cleanly via Non-Maximum Suppression (NMS), dead-time hallucinations often have jittery timestamps that fail to merge, creating double-counted false positives. By reverting the prompt and reducing `overlap` to 0.5 seconds for 6.0s chunks, we will shrink the double-exposure window and mechanically cut duplicate hallucinations without sacrificing recall.
