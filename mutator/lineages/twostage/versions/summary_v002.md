# What I know about this pipeline

### Established
- Removing strict conditional restrictions on `set` (like requiring a subsequent kill) causes the LLM to over-index on them massively, inflating set predictions to 155 (vs 47 ground truth) and destroying precision.
- Forcing the vision model to directly classify specific volleyball events (serve, receive, dig, etc.) using strict definitions in Stage 1 causes catastrophic recall collapse. The model requires physical/trajectory descriptions to detect contacts.
- The pipeline's scoring logic ("point for the team that made the point-flagged contact") cannot correctly handle unforced errors. Instructing the model to withhold the point flag on errors just deletes the point from the match entirely, worsening the score margin error.

### Ruled out
- Solving action confusion by directly prompting the vision model with the exact 7 event types. The model lacks the zero-shot capability to accurately map fast-moving visual data to strict sports terminology, and attempting it destroys baseline detection sensitivity.
- Filtering out presumed "over-predicted" events by having Stage 1 evaluate conditional logic on future events within a rally. 
- Attempting to fix the match score attribution by tweaking the definition of `point` in the prompt, because the underlying metric evaluation logic binds points strictly to the contacting team.

### Open
- Why does the model persistently miss over 180-260 events in standard configurations? 
- Is `fps: 5` too slow to capture fast volleyball actions (like blocks and spikes), causing them to become invisible motion blur or fall between frames?
- Does the vertical crop (`y: 330`, `height: 620`) chop off the top of the court, causing the model to lose track of the ball during high passes and sets?
- Would longer continuous context (`chunk_len: 30.0` instead of `10.0`) reduce edge-case ghost detections by encapsulating full rallies within single inferences?

### Current hypothesis
The primary bottleneck limiting recall and driving hallucinations is the physical video input, not the prompt semantics. Low temporal resolution (`fps: 5`) allows high-speed contacts to fall entirely between frames, while the aggressive vertical crop (`crop: "1920:620:0:330"`) decapitates the court's airspace and causes tracking loss on high balls. Semantic prompt tuning is now just trading one type of hallucination for another. The single most promising next line of attack is to revert the prompt changes and increase `fps` (e.g., to 10) or alter the vertical crop to ensure the model has the spatial and temporal data required to actually see the events.
