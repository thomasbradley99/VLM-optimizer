# What I know about this pipeline

### Established
- Asking the vision model (Stage 1) to apply complex, conditional sports logic ("omit contact 2 unless contact 3 is a kill") is highly destructive. It confuses the model, dropping true positives by 22% (240 -> 187) and increasing invented events by 25% (214 -> 268).
- Prompting Stage 1 with rule-specific terminology (like "intermediate pass") poisons its raw visual output. It regurgitates these terms, causing massive false-positive classifications in Stage 2 (predicted sets jumped from 37 to 88). Stage 1 must remain strictly visual.

### Ruled out
- Filtering out presumed "over-predicted" events by having Stage 1 evaluate conditional logic on future events within a rally. The vision model cannot reliably execute rules like "if contact 3 is a kill, keep contact 2", and trying to force it to do so destroys recall.

### Open
- Why does the baseline configuration invent 214 events and miss 209 events? Are these errors caused by temporal boundary artifacts from the 10-second video chunks, or by the 5 FPS frame rate causing fast contacts to blur into invisibility?
- Will giving the model longer continuous context (e.g., longer chunk lengths) improve its ability to track the flow of the rally and reduce duplicate detections?

### Current hypothesis
The high volume of both missed (209) and invented/ghost (214) events in the baseline is heavily driven by boundary artifacts resulting from the short 10-second `chunk_len`. Volleyball rallies typically last 5 to 20 seconds. With 10-second chunks and a 3-second overlap, the majority of rallies are chopped in half. This fragmentation likely causes the exact same contact to be detected twice across adjacent chunks with slightly different inferred timestamps, bypassing deduplication logic and creating an "invented" ghost. Conversely, context-dependent contacts occurring right on a boundary may be missed altogether. The most promising next step is to revert the prompt to its pure, baseline state and increase the `chunk_len` to 30 seconds (with a 5-second overlap) to encapsulate entire rallies within single inferences, naturally eliminating edge artifacts.
