# Iteration 4

## CONJECTURE
The massive drop in TP (from 223 to 174) and rise in ghosts (invented) in iteration 3 was a definitional failure. By strictly commanding the model to "IGNORE the intermediate passes" and "Only report the first defensive contact and the hit over the net", we broke its ability to track the structural context of the rally. To compensate for the omitted intermediate touches, the model misclassified them as attacks or digs, causing action errors to remain high and increasing in-rally ghosts. 

Additionally, there is a perception/definition gap causing the model to confuse `receive` with `serve` (30 real receives were predicted as serves). Because a 30-second chunk often starts mid-rally, the model assumes the first touch it sees is a serve. Providing a clear chronological flow and anchoring the serve to a specific location ("behind the baseline") will prevent it from misclassifying court-interior receives as serves.

## CHANGE
I am changing the `prompt` to remove the destructive "only report the first contact" omission rule, restoring the model's ability to track the rally. I am replacing it with a chronological flow guide (Serve -> Receive -> Pass -> Attack -> Dig) to teach causal context, explicitly defining a serve as coming from "behind the baseline" to fix the receive/serve confusion, and clarifying the `side` definition to anchor on the net.

```config
{"lever": "prompt",
 "prompt": "You are watching a volleyball match from a fixed camera.\n\nThis clip begins at {start} seconds into the match.\n\nList ONLY specific meaningful volleyball events in live play.\n1. A live rally strictly begins with a 'serve' and ends when the ball is dead. IGNORE all casual touches, practice hits, and dead-ball passing between points.\n2. Volleyball rallies follow a logical flow: Serve -> Receive -> Pass -> Attack -> Dig. Use this sequence to classify events accurately. A 'receive' defends a serve; a 'dig' defends an attack.\n3. Skip routine intermediate passes. Only report an event if it clearly matches a definition below.\n\nFor each event give:\n  t       - the precise time the player physically strikes the ball\n  type    - must be one of:\n            serve: the initial hit from behind the baseline that starts a rally\n            receive: the first contact defending a serve\n            dig: the first contact defending an attack\n            set: an assist pass that directly leads to a kill\n            attack: an offensive hit sent over the net that does not score a point\n            kill: an attack that directly scores a point and ends the rally\n            block: deflecting an attack at the net\n  side    - \"left\" or \"right\": which side of the net the player is on (left half or right half of the screen)\n  number  - the player's jersey number as a string, or null if you cannot read it\n  error   - true if the touch was a mistake\n  point   - true if the rally ended here and a point was scored",
 "chunk_len": 30.0, "overlap": 8.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By removing the rule that forced the model to ignore intermediate rally structure, True Positives will rebound to baseline levels. By defining the serve location and causal flow, the 30 receive->serve confusions will drop, raising both `serve_precision` and `receive_recall`. By clearly bounding a live rally, dead-time ghosts will decrease. Rare events like blocks will remain unaffected.

```predictions
[{"metric": "tp", "direction": "up", "from": 174, "to_approx": 215},
 {"metric": "invented", "direction": "down", "from": 282, "to_approx": 240},
 {"metric": "serve_precision", "direction": "up", "from": 0.286, "to_approx": 0.380},
 {"metric": "receive_recall", "direction": "up", "from": 0.140, "to_approx": 0.250},
 {"metric": "block_f1", "direction": "flat", "from": 0.000, "to_approx": 0.000}]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
tp                                up to ~215     down 174 -> 163     X     X
invented                        down to ~240     down 282 -> 259    OK    OK
serve_precision                  up to ~0.38 flat 0.365 -> 0.357     X     X
receive_recall                   up to ~0.25 down 0.215 -> 0.187     X     X
block_f1                        flat to ~0.0       up 0 -> 0.222     X     X

direction 1/5   magnitude 1/5
```

headline_f1 0.307 -> 0.305   (-0.002)
n_pred 583 -> 518   missed 249 -> 291   invented 282 -> 259
pipeline: $1.86, 0 cached, 0 failed

## VERDICT
I was completely wrong. Instead of rebounding to previous highs, True Positives fell even further (174 to 163) and Missed events climbed (249 to 291). 

The numbers show that my attempt to teach the model a rigid chronological flow paralyzed it. I explicitly told the model the sequence was "Serve -> Receive -> Pass -> Attack -> Dig", but "pass" was not an allowed output `type` in the schema. Furthermore, I retained the instruction to "Skip routine intermediate passes." By forcing the model to map plays to a rigid sequence that contained unreportable steps, it likely failed to parse rallies starting mid-chunk, skipping valid events entirely (which explains `receive_recall` dropping from 0.215 to 0.187). 

The most informative movement was the unpredicted jump in `block_f1` from 0.0 to 0.222. Adding the specific spatial anchor "at the net" to the block definition finally gave the model the physical reference point it needed to identify that rare class. 

My changes made the core performance worse because teaching rigid causal logic backfires when video chunks arbitrarily slice through that logic. The right move is to abandon this line of attack, manually restore the prompt to the Iteration 2 configuration (which achieved 223 TP), and attack the false-positive problem from a completely different angle: the background courts.
