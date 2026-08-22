# Iteration 20

## CONJECTURE
The pipeline predicts 412 completely `invented` events largely as a structural artifact of processing the video in narrow 6-second chunks. By slicing the video into 930 independent API calls, we create hundreds of isolated temporal windows where casual dead-time shuffles or background court hits are mistaken for active rallies, because the model lacks the surrounding frames to see that the ball was out of play. This is a definitional/structural mismatch caused by over-segmentation. Since explicit text-based spatial and contextual vetoes have proven toxic to recall or completely ineffective, we must solve this mechanically. By increasing `chunk_len` to 10.0 seconds, we roughly halve the number of independent API calls (to ~465) and provide a wider temporal window per clip. This will structurally starve the model of hallucination opportunities and drastically cut `n_pred`, while 50 frames per clip is still short enough to avoid the severe attention saturation and massive true positive drops seen previously at 15-second chunks.

## CHANGE
I am changing `chunk_len` from 6.0 to 10.0 (while maintaining the baseline prompt except to update the text from "6 seconds" to "10 seconds" and `{start:.2f}` to `{start}`) to mechanically halve the number of clips and reduce the opportunities for hallucination.

```config
{"lever": "chunk_len",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start} seconds into the match and runs for 10 seconds.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit that starts a rally. CRITICAL VISUAL RULE: A serve ONLY happens from a dead ball. If a player hits a ball that just flew across the net to them, it is a response to an incoming ball and is NEVER a serve. Label it receive or dig instead.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true if the rally ended on this contact and a point was scored\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no play happens in this clip, return an empty list.",
 "chunk_len": 10.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By reducing the number of clips from 930 to ~465, the model will have ~50% fewer independent opportunities to hallucinate events during dead time or background play, causing `n_pred` and `invented` events to drop significantly. Because clips are longer, there are also fewer clip boundaries to trigger mid-rally "first contact" false serves, so `serve_pred_count` will fall. `tp` will drop slightly because 50 frames per clip induces more attention saturation than 30 frames, but this small loss will be massively outweighed by the shrinking denominator, driving `headline_f1` up. `set_pred_count` will remain effectively flat, as its strict text definition continues to gate it well.

```predictions
[
  {"metric": "n_pred", "direction": "down", "from": 856, "to_approx": 680},
  {"metric": "invented", "direction": "down", "from": 412, "to_approx": 250},
  {"metric": "serve_pred_count", "direction": "down", "from": 226, "to_approx": 170},
  {"metric": "tp", "direction": "down", "from": 309, "to_approx": 285},
  {"metric": "headline_f1", "direction": "up", "from": 0.440, "to_approx": 0.490},
  {"metric": "set_pred_count", "direction": "flat", "from": 38, "to_approx": 38}
]
```

## OUTCOME
_Computed by the harness. Not written by the mutator._

```
metric                             predicted              actual   dir   mag
n_pred                          down to ~680     down 856 -> 633    OK    OK
invented                        down to ~250     down 412 -> 257    OK    OK
serve_pred_count                down to ~170     down 226 -> 173    OK    OK
tp                              down to ~285     down 309 -> 238    OK     X
headline_f1                      up to ~0.49  down 0.44 -> 0.402     X     X
set_pred_count                   flat to ~38       down 38 -> 27     X     X

direction 4/6   magnitude 3/6
```

headline_f1 0.440 -> 0.402   (-0.037)
n_pred 856 -> 633   missed 106 -> 174   invented 412 -> 257
pipeline: $2.23, 0 cached, 0 failed

## VERDICT
Right about the mechanism, wrong about the size. 

I predicted that reducing the number of chunks would structurally starve the model of hallucination opportunities, and it did exactly that: `invented` events dropped massively from 412 to 257, and `serve_pred_count` fell from 226 to 173. However, I severely underestimated the attention saturation penalty of feeding the model 50 frames (10 seconds) per chunk. True positives didn't just drop slightly; they plummeted from 309 to 238. The model simply cannot maintain focus on quick, dense volleyball actions across a 10-second window while juggling our strict spatial and contextual veto rules. Because the True Positive crash was so severe, `headline_f1` dropped to 0.402. This change made things worse because the recall penalty outweighed the precision gains. It confirms we are trapped by attention saturation at longer clip lengths.
