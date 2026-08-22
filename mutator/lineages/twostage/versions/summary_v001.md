# What I know about this pipeline

### Established
- Forcing the vision model to directly classify specific volleyball events (serve, receive, dig, etc.) using strict definitions causes catastrophic recall collapse (TP down to 47, misses up to 459). The model requires physical/trajectory descriptions to detect contacts.
- Asking the vision model to apply complex conditional sports logic drops true positives by 22% compared to a prior baseline, but reverting this logic does not recover those lost detections.
- Prompting Stage 1 with explicit trajectory categorizations heavily inflates set predictions (peaking at 112). 

### Ruled out
- Solving action confusion by directly prompting the vision model with the exact 7 event types. The model lacks the zero-shot capability to accurately map fast-moving visual data to strict sports terminology, and attempting it destroys baseline detection sensitivity.
- Filtering out presumed "over-predicted" events by having Stage 1 evaluate conditional logic on future events within a rally. 
- The hypothesis that complex conditional logic was the sole cause of the massive drop in true positives in previous rounds.

### Open
- Why does the model persistently miss over 260 events in standard configurations? 
- Is `fps: 5` too slow to capture fast volleyball actions (like blocks and spikes), causing them to become invisible motion blur or fall between frames?
- Does the vertical crop (`y: 330`, `height: 620`) chop off the top of the court, causing the model to lose track of the ball during high passes and sets?
- Would longer continuous context (`chunk_len: 30.0` instead of `10.0`) reduce edge-case ghost detections by encapsulating full rallies within single inferences?

### Current hypothesis
The primary bottleneck limiting recall and driving hallucinations is the physical video input, not the prompt semantics. Low temporal resolution (`fps: 5`) allows high-speed contacts to fall entirely between frames, while the aggressive vertical crop (`crop: "1920:620:0:330"`) decapitates the court's airspace and causes tracking loss on high balls. The single most promising next line of attack is to revert the prompt to an earlier state and increase `fps` (e.g., to 10) or remove the vertical crop to ensure the model has the spatial and temporal data required to actually see the events.
