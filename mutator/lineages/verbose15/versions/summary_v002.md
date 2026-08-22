# What I know about this pipeline

### Established
- Defining `set` strictly as an assist (a set leading to a kill) successfully aligns the model with the scout's taxonomy. `set_pred_count` dropped from 130 to 44 (in the 15s baseline), eliminating phantom sets and improving F1.
- The model suffers from "clip-start bias" at shorter chunk lengths, hallucinating serves when chunks begin mid-rally. A simple text warning ("Never report a serve mid-rally") fails because the model doesn't realize the video starts mid-rally.
- The model's recall degrades severely if asked to process too many events in one chunk. Moving from 15s to 30s chunks caused True Positives to drop by ~35% (230 -> 149).
- The scoring parser relies on the final contact of a rally having `point: true`. If that contact is a mistake, it must also have `error: true` for the parser to award the point to the opposing team. Forcing `point: false` on errors destroys score tracking (score_margin_err spiked).

### Ruled out
- **Telling the model "never report a serve mid-rally".** This fails because the model equates the start of a video chunk with the start of a rally.
- **Forcing `point: false` on rally-ending errors.** Tested in iteration 1 and firmly rejected. This prevents the parser from awarding points for opponent errors, doubling the `score_margin_err`.
- **Increasing `chunk_len` to 30s to fix boundary hallucination.** Tested in iteration 2 and rejected. While it reduces false boundaries, it overwhelms the model's extraction capacity, causing a massive drop in recall (TP dropped by 81) and destroying F1.

### Open
- Can we cure the "clip-start bias" false serves at a 15s chunk length by demanding strict visual evidence (e.g., explicitly seeing the player toss the ball from completely out of bounds)?
- Will instructing the model to simultaneously flag `error: true` and `point: true` on failed contacts correctly distribute points to the opponent and heal the `score_margin_err`?

### Current hypothesis
The most promising next attack is to revert to 15-second chunks to recover our lost recall, while fixing the definition of `serve` and correcting the `point`/`error` interaction in the prompt. For serves, we must mandate seeing the ball tossed from completely out of bounds, explicitly warning the model that if a clip starts with a player already hitting the ball mid-air on the court, it is an attack or dig, never a serve. For points, we will instruct the model that `point` marks the rally's final contact; if the rally ends on a mistake (like an attack out of bounds), it must output BOTH `error: true` and `point: true` so the parser can award the point to the correct team.
