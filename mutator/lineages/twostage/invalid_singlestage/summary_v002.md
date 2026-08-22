# What I know about this pipeline

### Established
- Asking the vision model to apply complex conditional sports logic drops true positives by 22% (from 240 down to 187) compared to a prior baseline, but reverting this logic does *not* recover those lost detections (TP stayed flat at 191).
- Prompting Stage 1 with explicit trajectory categorizations (like "after that contact the ball goes UP") heavily inflates set predictions (peaking at 112). The model diligently reports every minor upward deflection, which Stage 2 translates into an excess of sets.
- The model consistently misses a massive volume of events (266 to 272 misses) regardless of how the prompt is structured.

### Ruled out
- Filtering out presumed "over-predicted" events by having Stage 1 evaluate conditional logic on future events within a rally. The vision model cannot reliably execute rules like "if contact 3 is a kill, keep contact 2".
- The hypothesis that the complex conditional logic was the sole or primary cause of the massive drop in true positives. Reverting to a purely visual description failed to restore performance, proving the core issue lies elsewhere.

### Open
- Why does the model persistently miss over 260 events? Is `fps: 5` too slow to capture fast volleyball actions (like blocks and spikes), causing them to become invisible motion blur or fall between frames?
- Does the vertical crop (`y: 330`, `height: 620`) chop off the top of the court, causing the model to lose track of the ball during high passes and sets?
- Would longer continuous context (`chunk_len: 30.0` instead of `10.0`) reduce edge-case ghost detections by encapsulating full rallies within single inferences?

### Current hypothesis
The persistently low recall (191 TP, 266 missed) and the hallucinated sets are fundamentally caused by inadequate video input parameters, not just prompt phrasing. At `fps: 5`, high-speed volleyball contacts last for a fraction of a second and easily fall entirely between frames. Furthermore, the aggressive vertical crop (`crop: "1920:620:0:330"`) likely decapitates the court's airspace. When a ball is passed high, it leaves the cropped frame, causing the model to lose track of the play. When the ball falls back into frame, the model misinterprets it, leading to missed attacks or hallucinated touches. The single most promising next line of attack is to increase `fps` (e.g., to 10) or remove the vertical crop to ensure the model has the temporal resolution and full visual field required to track the ball.
