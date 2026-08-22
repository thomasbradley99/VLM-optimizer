# Can an AI improve its own video pipeline?

An experiment on volleyball event detection.

---

## The question

Give a vision-language model 30 seconds of volleyball and ask it what happened. It gets some of it right.

Now let a second model look at exactly what it got wrong, form a theory about why, rewrite the prompt, and try again. Twenty times.

**Does it get better? And more interestingly: does it understand why?**

That second question is the experiment. Anyone can run a search loop and report a higher number. What we want to know is whether the model that proposes the changes is actually reasoning about the system, or just shuffling words until something sticks.

So we make it commit. Before every run it writes down what it thinks is wrong, what it's changing, and what it expects to happen. Then we run it, and it has to say whether it was right.

That record is the result.

---

## Why volleyball

Because it's the cleanest team sport there is.

Contacts are discrete. Rallies have rules — you serve, you get at most three touches, the ball crosses, someone wins the point. Outcomes are unambiguous. And unlike football, where an interesting moment is a matter of opinion, in volleyball every single ball contact is an event.

We have one match: **62 minutes, 553 human-annotated events, 118 rallies.** Median gap between events is under two seconds, so the timing has to be tight.

Nine event types: serve, receive, dig, set, attack, kill, block, error, point.

---

## The apparatus

Deliberately dull. All the interest is in the mutator, so the thing being mutated should be as simple as it can be.

```
video
  → cut into 30-second chunks, 8 seconds of overlap
  → ONE PROMPT per chunk, all chunks in parallel
  → parse JSON
  → merge the overlaps
  → events
```

One prompt. That's the entire pipeline. It sees a chunk and its start time; it returns a list of events with timestamps.

124 chunks, run concurrently, under two minutes per full pass. Responses cached by prompt hash, so nothing is ever computed twice.

**The prompt is the only thing that changes.** Everything else — the chunking, the parsing, the merging, the scoring — is fixed code that the mutator cannot touch.

---

## How we measure

Match predicted events to true events, nearest first, one-to-one, within a time tolerance.

**Three tolerances:** ±0.5s, ±1.0s (the headline), ±2.0s
**Four levels of strictness:**

1. right event at the right time
2. and the right type
3. and the right team
4. and the right player number

Fixed before the first run. Never adjusted afterwards.

**Split by rally, not by frame.** 70 rallies to optimise on, 24 to select on, 24 sealed until the very end.

**One extra measure, and it needs no labels at all.** Volleyball has rules. A rally starts with a serve. At most three touches per side. A block only follows an attack. Exactly one point ends it. Count how often the predicted sequence breaks these rules — that's a coherence score computable on any footage, labelled or not.

---

## The loop

```
read notebook
    ↓
write CONJECTURE, CHANGE, PREDICTION      ← committed to disk first
    ↓
run the pipeline
    ↓
score it
    ↓
write OUTCOME and VERDICT
    ↓
update the notebook
    ↓
keep the best prompt, not the latest
```

The prediction is written before the run. That's the one design decision that makes this an experiment rather than a search — the model cannot retrofit an explanation to a result it has already seen.

Keeping the best rather than the latest matters too. Without it, one bad round poisons everything after it.

---

## The notebook

The mutator has one thing the pipeline doesn't: memory. It keeps a running record.

**Its current beliefs**, rewritten each round:

> **Established.** Serves are detected almost perfectly. Timing runs about 1.2s late on everything. Events near the end of a chunk are missed three times as often.
>
> **Ruled out.** Asking for higher confidence hurt recall and bought no precision. Listing all nine types in the header changed nothing.
>
> **Open.** Are digs missed because they aren't seen, or seen and called something else?

**And one entry per round:**

> **Conjecture.** Digs recall is 0.44 against 0.81 for attacks. The missed ones are mostly the second or third touch in long rallies. I think the model is summarising long rallies rather than listing every contact.
>
> **Change.** Told it to enumerate every contact in order and state the count first.
>
> **Prediction.** Dig recall above 0.60. Serves and attacks unaffected. Maybe slightly more false positives.
>
> **Outcome.** Digs 0.44 → 0.71. Serves unchanged. **Attacks 0.81 → 0.68.** False positives 34 → 41.
>
> **Verdict.** Right about digs, wrong about the cost. Forcing enumeration made it split single attacks into two events. The mechanism is real, the instruction is too blunt.

That verdict is worth more than the score. A wrong prediction with a correct diagnosis is a model that understands the system.

---

## What the mutator can and cannot do

**Can change:** the prompt, the chunk length, the overlap. And it may propose splitting the single call into two — describe first, classify second — if it works out that's the problem.

**Cannot touch:** the metric, the splits, the merging rule, or any of the scoring code.

**Sees each round:** its running beliefs, the last five entries in full, headlines of everything older, and the error report.

---

## The error report

Generated by code, not by a model. This is the mutator's only window onto reality, so it has to be honest and specific.

Not "F1 was 0.66." Instead:

- every missed event, with its type, its position in the rally, how long that rally was, and how close it sat to a chunk boundary
- every false positive, with the nearest true event
- timing error, overall and per type
- precision and recall per event type
- rule violations

And then the part that does the work — **patterns**, computed as simple aggregations over that list:

> digs missed at 2.4× the rate of attacks
> 83% of misses fall in rallies longer than five contacts
> events in the last five seconds of a chunk are missed 3.1× more often
> timing runs late on every type without exception

Those sentences are what let the mutator say something intelligent. Without them it has nothing to reason about and will fall back on rewording.

---

## What we will report

The accuracy number is the least interesting output.

**Did its predictions come true?** Track this across rounds. If prediction accuracy improves, the model is learning about the system, not just about the task. That is a measurable thing and nobody reports it.

**Did it find the split on its own?** Earlier work on football showed that separating description from classification was worth more than any prompt change — it took F1 from 36% to 82%. We have deliberately not built that in. If the mutator arrives at it unaided, that's the result.

**Where did it go round in circles?** Failure modes of self-directed experimentation are underreported and more useful than another success story.

**Does rule-violation rate track accuracy?** If it does, there's an unsupervised proxy for correctness — which matters, because the partner has 100,000 games and only 30,000 are labelled.

---

## Scale

| | |
|---|---|
| video | 62 minutes, one fixed camera |
| ground truth | 553 events, 118 rallies |
| chunks | 124, run in parallel |
| time per run | under 2 minutes |
| cost per round | ~$2 |
| rounds | 20, repeated across 3 seeds |

Small enough to run in an afternoon. Clean enough to explain in a paragraph.

---

## Where it sits

Prompt optimisation is established: OPRO showed language models can act as optimisers, DSPy made it a framework, GEPA showed reflective evolution beating reinforcement learning. All of it evaluated on text — maths problems, question answering.

Sports video work runs the other way. Fixed pipelines, careful engineering, no self-improvement.

Nobody has put the two together. And nobody has asked whether the optimiser understands what it's doing, which is the question that actually interests us.

---

## Rules

1. The sealed split is opened once, at the end.
2. Tolerances fixed before the first run.
3. The prediction is written before the run. Always.
4. Keep the best, not the latest.
5. Selection on the dev split, never on training.
6. Scoring code is never mutated.
7. The baseline number is recorded before anything is optimised.