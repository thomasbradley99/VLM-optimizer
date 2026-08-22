# Iteration 14

## CONJECTURE
The 6.0s chunk length successfully maximizes visual perception (missing only 106 events while spotting 444), but it causes severe definitional failures due to a lack of temporal context. First, the model predicts 412 entirely hallucinated events because it misinterprets casual bouncing and passing during "dead time" between points as active rallies. Second, because 6s clips often start mid-action, a player digging or receiving at the very start of a clip is falsely labeled a `serve` because the model didn't see the ball arrive (driving `serve` predictions to 226 against 118 real). Separately, the `point` flag is currently being awarded on errors, which artificially inflates the score margin (real -11, ours +46) because it credits a point to the team making the error rather than the team that actually won the rally. This is a definitional gap. By introducing explicit "Dead Time" and "Clip Boundary" vetoes, and strictly limiting the `point` flag to winning contacts, we can massively cut `n_pred` and fix the score margin without losing True Positives.

## CHANGE
I am adding explicit rules for "DEAD TIME VETO" and "CLIP BOUNDARIES" to stop the model from hallucinating events between rallies or mislabeling boundary contacts as serves, and I am redefining `point` so it is never awarded on an error.

```config
{"lever": "prompt",
 "prompt": "You are scouting a single volleyball match from a fixed camera.\n\nCRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main court in the foreground -- the one with the referee standing on the elevated stand at the centre of the frame. Other matches are visible in the background; ignore them completely.\n\nThe net runs up the middle of the frame, so each team occupies one half of the image. Identify a team ONLY by which half of the frame they are standing in -- \"left\" or \"right\" as you see it on screen. Do not use jersey colour.\n\nThis clip begins at {start} seconds into the match and runs for 6 seconds.\n\nDEAD TIME VETO: Over half the match is dead time between points. Players casually passing, standing, or bouncing the ball before a serve is NOT a rally. ONLY report contacts during an active rally. If players are casually moving or the ball is not actively contested, report NOTHING.\n\nCLIP BOUNDARIES: Since clips are only 6 seconds, a clip may start mid-rally. Do NOT assume a contact at the very start of a clip is a serve just because you didn't see the prior action. A serve is specifically a structured hit from behind the baseline to start a point. Defensive passes and spikes are never serves, even if they are the first thing you see.\n\nACTION DEFINITIONS - DO NOT COUNT CONTACTS!\nClassify each event purely by its visual action. Do not enforce global sequences (like \"Serve, then Receive\") or count contacts (like \"first contact\", \"third contact\"), because missing one contact will cause you to mislabel all the others!\n\n  serve   - the hit from behind the baseline that starts a rally.\n  receive - a defensive pass handling the opponent's serve.\n  dig     - a defensive pass handling the opponent's attack.\n  set     - a pass placing the ball for an attacker, BUT ONLY report it if it directly leads to a kill (an assist). Do NOT report regular sets.\n  attack  - an offensive hit aimed to score by sending the ball over the net.\n  kill    - an offensive hit that immediately wins the rally.\n  block   - a defensive contact made AT THE NET by a player jumping with hands above it.\n\nFor each contact give:\n  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to the clip start of {start}. Be precise to a fraction of a second.\n  type    - one of the seven above\n  side    - \"left\" or \"right\": which half of the frame the contacting player is standing in\n  number  - the contacting player's jersey number as a string, or null if you cannot read it. Do not guess.\n  error   - true if this contact was an error (into the net, out of bounds, mishandled)\n  point   - true ONLY if THIS exact contact actively won the rally (e.g. a kill or service ace). NEVER flag point=true for an error, as the team making the error loses the point.\n\nReport only contacts you actually observe. Do not invent a full rally structure based on assumptions. If no active play happens in this clip, return an empty list.",
 "chunk_len": 6.0, "overlap": 2.0, "fps": 5, "width": 640,
 "crop": null, "media_resolution": null,
 "model": "gemini-3.7-flash", "thinking": "low"}
```

## PREDICTION
By aggressively filtering out dead time, the model will stop inventing events out of thin air, causing total predictions to plummet. The clip boundary warning will stop it from greedily assigning `serve` to mid-rally passes caught at the start of a clip. The tighter `point` definition will stop erroring teams from being awarded points, drastically fixing the `score_margin_err`. True Positives will remain stable because the model is merely refraining from guessing, rather than losing its ability to see active events.

```predictions
[
  {"metric": "n_pred", "direction": "down", "from": 856, "to_approx": 650},
  {"metric": "invented", "direction": "down", "from": 412, "to_approx": 250},
  {"metric": "serve_pred_count", "direction": "down", "from": 226, "to_approx": 150},
  {"metric": "score_margin_err", "direction": "down", "from": 57, "to_approx": 20},
  {"metric": "tp", "direction": "flat", "from": 309, "to_approx": 300},
  {"metric": "missed", "direction": "flat", "from": 106, "to_approx": 110}
]
```
