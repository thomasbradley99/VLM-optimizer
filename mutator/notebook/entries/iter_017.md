# Iteration 17

## CONJECTURE
The model hallucinates 412 events because it cannot reliably map the semantic concepts of "foreground" vs "background" (or identifying the referee's stand) to what it sees, causing it to eagerly report hits from other matches visible in the distance. However, vision-language models are highly sensitive to relative 2D object size. By changing the definitional constraint to a direct pixel-scale rule—instructing the model to "ONLY report contacts made by LARGE players" and "ignore tiny/small players"—we translate an abstract depth-of-field concept into a reliable 2D visual attribute. This is a definitional/perception translation that should drastically cut `invented` background events without sacrificing our high foreground recall.

## CHANGE
I am updating the background veto in the prompt to define the target court purely by player size on screen ("LARGE" vs "TINY"), ordering the model to filter events purely by relative visual scale. I am also replacing `{start:.2f}` with `{start}` to comply with the harness's strict syntax rule.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. The players on our main court appear LARGE. The players on the other courts in the background appear TINY. ONLY report contacts made by the LARGE players. Ignore all contacts by tiny/small players in the background completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start} seconds into the match and runs for 6 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: A serve ONLY happens from a dead ball. If a player hits a ball that just flew across the net to them, it is a response to an incoming ball and is NEVER a serve. Label it receive or dig instead.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true if the rally ended on this contact and a point was scored\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By defining the foreground strictly by player size rather than spatial orientation, the model will successfully identify and dismiss contacts happening on the background courts. This will cause `invented` events to drop significantly. Because it no longer outputs these hallucinated background hits, total predictions (`n_pred`) will fall. True Positives (`tp`) and `missed` events will remain completely flat since the model is simply filtering out noise rather than changing its perception of foreground actions. As the denominator shrinks, `headline_f1` will rise.

```predictions
[
  {"metric": "invented", "direction": "down", "from": 412, "to_approx": 250},
  {"metric": "n_pred", "direction": "down", "from": 856, "to_approx": 700},
  {"metric": "tp", "direction": "flat", "from": 309, "to_approx": 309},
  {"metric": "missed", "direction": "flat", "from": 106, "to_approx": 106},
  {"metric": "headline_f1", "direction": "up", "from": 0.440, "to_approx": 0.490}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
invented                        down to ~250     flat 412 -> 427     X     X
n_pred                          down to ~700     flat 856 -> 857     X     X
tp                              flat to ~309     flat 309 -> 312    OK    OK
missed                          flat to ~106       up 106 -> 120     X     X
headline_f1                      up to ~0.49  flat 0.44 -> 0.443     X     X

direction 1/5   magnitude 1/5
```

headline_f1 0.440 -> 0.443   (+0.004)
n_pred 856 -> 857   missed 106 -> 120   invented 412 -> 427
pipeline: $3.19, 0 cached, 0 failed

## VERDICT
I was wrong. The relative player size constraint failed completely to reduce `invented` events, which remained stubbornly flat (412 -> 427), and instead it actively harmed our recall (`missed` rose from 106 to 120). 

The numbers show that instructing the model to filter events based on "LARGE" vs "TINY" player sizes does not successfully translate to discarding background matches. Instead, the model likely applied this rule to the main court itself, doubting actual contacts made by players on the far side of the net (who naturally appear smaller than those on the near side), leading to the increase in missed events. Vision-language models may recognize size differences, but they cannot use relative size as a hard categorical boundary without unintended friendly-fire on legitimate foreground actions.
