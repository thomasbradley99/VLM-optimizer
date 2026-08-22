# What I know about this pipeline

### Established
- The pipeline's scoring logic ("point for the team that made the point-flagged contact") cannot correctly handle unforced errors. Instructing the model to withhold the point flag on errors deletes the point from the match entirely, destroying the score margin. Reverting to "true if this contact directly scored a point" improved score margin error from 43 to 29.
- Removing strict structural restrictions on `set` causes the LLM to over-index on them massively, inflating set predictions to ~150 (vs 47 ground truth) and dragging down precision.
- Modifying prompt definitions has cascading effects on other classes. Simplifying the instructions for points/errors caused `serve_f1` to improve from 0.447 to 0.507, likely by reducing the reasoning engine's overall cognitive load.

### Ruled out
- Solving action confusion by directly prompting the vision model with the exact 7 event types in Stage 1. It destroys baseline detection sensitivity.
- Filtering out presumed "over-predicted" events by having Stage 1 evaluate conditional logic on future events within a rally.
- Attempting to fix the match score attribution by tweaking the definition of `point` to handle opponent errors, because the underlying metric evaluation logic binds points strictly to the contacting team.
- Constraining `set` predictions by requiring the contact to "set up an attack" instead of "put the ball UP for a team-mate". The model treats both definitions as functionally identical, continuing to predict ~150 sets either way.

### Open
- Why does the model persistently invent ~289 contacts and miss ~158 in standard configurations?
- Is `fps: 5` too slow to capture fast volleyball actions (like blocks and spikes), causing them to become invisible motion blur or fall between frames?
- Does the vertical crop (`y: 330`, `height: 620`) chop off the top of the court, causing the model to lose track of the ball during high passes and sets?
- Would longer continuous context (`chunk_len: 30.0` instead of `10.0`) reduce edge-case ghost detections by encapsulating full rallies within single inferences?

### Current hypothesis
The primary bottleneck limiting precision and recall is the physical video input, not the prompt semantics. Semantic attempts to constrain hallucinated sets have failed entirely. Low temporal resolution (`fps: 5`) likely allows high-speed contacts to fall entirely between frames, while the aggressive vertical crop (`crop: "1920:620:0:330"`) decapitates the court's airspace and causes tracking loss on high balls. This forces the model to invent intermediate contacts to make logical sense of what happened. The single most promising next line of attack is to increase `fps` (e.g., to 10) or alter the vertical crop to ensure the model has the spatial and temporal data required to actually see the events.
