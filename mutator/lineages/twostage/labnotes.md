# Mutator lab notes

Each round: diagnose, commit a falsifiable prediction to disk, re-run the pipeline, grade
the prediction against computed numbers, write a verdict. Losing rounds are auto-reverted.

**TP** = events matched in time *and* typed correctly. F1 can rise while TP falls, simply
by predicting less — so TP is the number that says whether the model actually sees more.

| round | F1 | TP | predictions made | called right | kept |
|---|---|---|---|---|---|
| _base_ | 0.342 | **202** | 630 | – | – |
| 0 | 0.434 → 0.376 | 229 | 668 | 3/6 | **reverted** |
| 1 | 0.376 → 0.418 | 257 | 681 | 2/5 | yes |

Best F1 round 1 (0.418, TP 257). Best TP 257 — against **202 for the original prompt**. Predictions right 5/11 (45%).

---

## Round 0 — REVERTED · F1 0.434→0.376 · TP 229 · called 3/6

**Thought:** The current Stage 2 prompt suffers from two clear definitional mismatches with the ground truth.
First, it explicitly instructs the model to report a `set` "ONLY when the next contact is a
kill".

**Changed:** I am changing `prompt2` to remove the restrictive kill condition from the `set` definition, and
redefining `point` so that errors are not flagged as points for the team making them.

**Learned:** Right about the mechanism for sets, but drastically wrong about the size, and completely wrong
about the score margin. Removing the restriction on sets caused an explosion in predictions
(from 37 up to 155, where ground truth is only 47), which successfully drove up recall but
destroyed precision, causing a massive spike in invented events (up to 303) and dropping the F1
score.

## Round 1 — kept · F1 0.376→0.418 · TP 257 · called 2/5

**Thought:** The current drop in F1 is driven by a definitional mismatch in Stage 2. In the previous round,
relaxing the `set` rule to "puts the ball UP for a team-mate" was too broad compared to the
scout's "assist-2".

**Changed:** I am changing `prompt2` to tighten the definition of `set` to only contacts that "set up an
attack", and redefining `point` to only contacts that directly score (like a kill or ace),
reverting the semantic damage from the previous round.

**Learned:** I was right about the F1 improvement and the score margin recovery, but completely wrong about
the mechanism constraining `set` predictions. The numbers show that changing the definition of
`set` from "puts the ball UP for a team-mate" to "sets up an attack" did absolutely nothing to
stem the flood of false sets (`set_pred_count` stayed flat at 149).

---

## Current beliefs

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