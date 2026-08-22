# What I know about this pipeline

### Established
- Defining `set` strictly as an assist (a set leading to a kill) successfully aligns the model with the scout's taxonomy. `set_pred_count` dropped from 130 to 44, eliminating phantom sets and improving F1.
- The model suffers from "clip-start bias", hallucinating serves when chunks begin mid-rally. A simple text warning ("Never report a serve mid-rally") is ignored because the model doesn't know it's mid-rally; `serve_pred_count` remained at 152 against ~93 true serves.
- The scoring parser relies on the final contact of a rally having `point: true`. If that contact is a mistake, it must also have `error: true` for the parser to award the point to the opposing team. Forcing `point: false` on errors destroys score tracking (score_margin_err spiked to 54).

### Ruled out
- **Telling the model "never report a serve mid-rally".** This fails because the model equates the start of a video chunk with the start of a rally.
- **Forcing `point: false` on rally-ending errors.** Tested in iteration 1 and firmly rejected. This prevents the parser from awarding points for opponent errors, doubling the `score_margin_err`.

### Open
- Can the model correctly reject false serves if we demand strict visual evidence (e.g., seeing the player toss the ball from completely out of bounds)?
- Will instructing the model to simultaneously flag `error: true` and `point: true` on failed contacts correctly distribute points to the opponent and heal the `score_margin_err`?

### Current hypothesis
The most promising next attack is to fix the visual definition of `serve` and correct the `point`/`error` interaction. For serves, we must mandate seeing the ball tossed from completely out of bounds, explicitly warning the model not to trust the first contact in a clip. For points, we will instruct the model that `point` marks the rally's final contact; if the rally ends on a mistake (like an attack out of bounds or a shanked dig), it must output BOTH `error: true` and `point: true` so the parser can award the point to the correct team.
