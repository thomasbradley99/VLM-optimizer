# Mutator lab notes

Each round: diagnose, commit a falsifiable prediction to disk, re-run the pipeline, grade
the prediction against computed numbers, write a verdict. Losing rounds are auto-reverted.

**TP** = events matched in time *and* typed correctly. F1 can rise while TP falls, simply
by predicting less — so TP is the number that says whether the model actually sees more.

| round | F1 | TP | predictions made | called right | kept |
|---|---|---|---|---|---|
| _base_ | 0.342 | **202** | 630 | – | – |
| 0 | 0.341 → 0.390 | 223 | 594 | 4/5 | yes |
| 1 | 0.390 → 0.330 | 173 | 499 | 2/4 | **reverted** |
| 2 | 0.330 → 0.390 | 223 | 594 | 5/6 | yes |
| 3 | 0.390 → 0.307 | 174 | 583 | 0/6 | **reverted** |
| 4 | 0.307 → 0.305 | 163 | 518 | 1/5 | **reverted** |
| 5 | 0.305 → 0.288 | 148 | 479 | 2/6 | **reverted** |
| 6 | 0.288 → 0.314 | 167 | 514 | 5/6 | **reverted** |
| 7 | 0.314 → 0.297 | 150 | 460 | 1/5 | **reverted** |

Best F1 round 0 (0.390, TP 223). Best TP 223 — against **202 for the original prompt**. Predictions right 20/43 (47%).

---

## Round 0 — kept · F1 0.341→0.390 · TP 223 · called 4/5

**Thought:** This is a definitional mismatch. "set" is vastly over-predicted (151 predicted vs 47 real).

**Changed:** Redefine the event types in the prompt to match the scout's strict definitions, explicitly
instructing the model to ignore normal passes and dead-time touches, and clearly separating
attacks from kills.

**Learned:** Right about the mechanism, wrong about the size/direction of TP. I predicted TP would remain
flat, but it actually went up (210 -> 223).

## Round 1 — REVERTED · F1 0.390→0.330 · TP 173 · called 2/4

**Thought:** The model is predicting events from the three other volleyball matches occurring simultaneously
in the background. This is evidenced by strings of ghost predictions that look exactly like
complete rallies happening in dead time or simultaneously with main-court rallies.

**Changed:** Apply a crop to the video to isolate the main court and completely remove the crowd and the
three other matches in progress at the top of the frame.

**Learned:** Right about the mechanism of reducing predictions, but completely wrong about the true positives
holding steady. The crop successfully reduced the number of invented events (260 down to 204),
but it severely damaged the model's ability to detect real events on the main court, causing
true positives to plummet from 223 to 173 and missed events to spike (216 to 255).

## Round 2 — kept · F1 0.330→0.390 · TP 223 · called 5/6

**Thought:** The crop `1920:620:0:330` applied in iter 001 caused a severe loss of perception. It chopped off
330 pixels from the top of the frame, which likely removed the ball during high arcs (like
serves and sets) or completely cut out players on the far side of the court.

**Changed:** I am changing the `crop` back to `null` to restore the full 1920x1080 frame, keeping the prompt
and all other settings exactly as they are.

**Learned:** Right. Reverting the crop perfectly restored the baseline performance exactly as predicted (F1
returned to 0.390, TP back to 223, invented back to 260).

## Round 3 — REVERTED · F1 0.390→0.307 · TP 174 · called 0/6

**Thought:** The model is drastically over-reporting events during live play, causing 202 of its 250 "ghost"
predictions to fall inside live rallies. This is a DEFINITIONAL mismatch: volleyball features 3
touches per side, but the scout's ground truth explicitly ignores the intermediate passes unless
they are assists leading to a kill.

**Changed:** I am rewriting the prompt to explicitly define the 3-touch structure and command the model to
ignore intermediate passes and dead-ball touches, while also clarifying that `t` must be the
exact moment of physical contact to fix the serve timing.

**Learned:** I was completely wrong. Rather than fixing precision, instructing the model to ignore
intermediate touches destroyed recall across the board, dropping Headline F1 from 0.390 to
0.307.

## Round 4 — REVERTED · F1 0.307→0.305 · TP 163 · called 1/5

**Thought:** The massive drop in TP (from 223 to 174) and rise in ghosts (invented) in iteration 3 was a
definitional failure. By strictly commanding the model to "IGNORE the intermediate passes" and
"Only report the first defensive contact and the hit over the net", we broke its ability to
track the structural context of the rally.

**Changed:** I am changing the `prompt` to remove the destructive "only report the first contact" omission
rule, restoring the model's ability to track the rally.

**Learned:** I was completely wrong. Instead of rebounding to previous highs, True Positives fell even
further (174 to 163) and Missed events climbed (249 to 291).

## Round 5 — REVERTED · F1 0.305→0.288 · TP 148 · called 2/6

**Thought:** The model is hallucinating hundreds of events because it is correctly perceiving the three
background matches and the pre-match warm-ups (there are over 70 ghost predictions between 00:00
and 16:37 before the real match even begins), and it is reporting them as main-court play. This
is a perception/context failure, not a definitional one.

**Changed:** I am restoring a clean prompt (removing the destructive causal sequencing rules to recover our
lost True Positives) and adding a critical, explicit command instructing the model to completely
ignore the background courts and pre-match warm-ups to surgically eliminate the false positives.

**Learned:** Wrong. I predicted that removing the strict sequencing rules and adding a semantic filter
("ignore the background", "focus on the foreground") would restore True Positives and cleanly
strip away the hallucinated background matches.

## Round 6 — REVERTED · F1 0.288→0.314 · TP 167 · called 5/6

**Thought:** The previous prompt's instruction to focus ONLY on the "MAIN FOREGROUND COURT" created a severe
spatial blind spot. The model physically ignored the far side of the court and the serving areas
behind the baselines, causing it to completely miss 77 real serves.

**Changed:** I am changing the `prompt` to explicitly include the far side and baselines in the main court
definition to restore missed serves, while adding strict filters against dead-time passing and
normal intermediate passes to cut phantoms.

**Learned:** Right about the mechanism, wrong about the size. Explicitly defining the baselines and far side
restored some spatial awareness, lifting true positives (148 -> 167) and dropping missed events
(304 -> 254).

## Round 7 — REVERTED · F1 0.314→0.297 · TP 150 · called 1/5

**Thought:** The model is systematically breaking rally sequences when it misses a serve or when a clip
starts mid-rally. Because it assumes the first contact it sees in a sequence is the start of a
rally, it misclassifies subsequent hits.

**Changed:** Rewrite the prompt to explicitly warn the model against sequence-assumption cascades, defining a
serve strictly by physical location rather than sequence order, and remove the destructive
geometric "bottom 3/4" rules to restore raw perception.

**Learned:** Right about the mechanism for receive precision, but completely wrong about the overall impact
on perception and recall. The explicit warning to stop assuming the first contact is a serve
worked exactly as intended for `receive_precision`, pulling it up from 0.160 to 0.208.

---

## Current beliefs

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