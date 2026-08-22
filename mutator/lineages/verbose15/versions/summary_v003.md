# What I know about this pipeline

### Established
15-second chunks stabilize recall at ~230 TP. 
Assist-only definitions for `set` align with taxonomy, dropping raw predictions from 130 to 44. 
Standard point attribution logic is dependent on specific terminal contact boolean combinations.

### Ruled out
`chunk_len` of 30.0s. Tested and rejected; temporal dilution drops TP by 81 and destroys F1.
Forcing `point: false` on rally-ending errors. Tested and rejected; disrupts parser and doubles `score_margin_err`.
Text-only mid-rally serve warnings. Tested and rejected; models fail to parse global timeline position at chunk boundaries.

### Open
Can strict visual bounding constraints eliminate the "clip-start bias" for serves?
Will dual-true boolean forcing resolve parser alignment for terminal errors?

### Current hypothesis
We will modify the prompt to enforce `serve` visual constraints and `point`/`error` boolean logic. Baseline extraction is validated. We demand explicit out-of-bounds visibility for all `serve` classifications. We demand simultaneous true values (`error: true`, `point: true`) for terminal mistakes.
