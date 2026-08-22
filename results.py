"""The single results store. One schema, one file, append-only.

Every scored run lands here as one record, whatever produced it -- a mutator round, a manual
sweep, a one-off. Before this existed the mutator wrote history.json in one shape and three
hand-written experiment scripts each invented their own, so nothing could be compared without a
bespoke join. `record()` is the only writer; anything that scores a run calls it.

    import results
    results.record(config, metrics, cost=1.88, source="mutator", run="iter_014")
    results.table()          # -> results.md + results.csv
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
# Overridable so a blind lineage writes and reads only its own runs (see notebook.NB).
STORE = os.environ.get("RESULTS_STORE") or os.path.join(HERE, "results.jsonl")
TYPES = ["serve", "receive", "dig", "set", "attack", "kill", "block"]
GT_N = {"serve": 118, "receive": 107, "dig": 86, "set": 47, "attack": 131, "kill": 52, "block": 9}
N_GT = 550
NOISE_F1, NOISE_TP = 0.028, 8   # 5 replicate pairs: mean |dF1| 0.015, max 0.028

# the config fields that define a run. Kept explicit so a new pipeline knob cannot silently
# appear in some records and not others.
CFG_FIELDS = ["prompt_id", "chunk_len", "overlap", "fps", "width", "crop",
              "media_resolution", "model", "thinking"]
METRIC_FIELDS = (["headline_f1", "tp", "spotted", "n_pred", "missed", "invented",
                  "team_acc", "number_f1"]
                 + [f"{t}_{m}" for t in TYPES for m in ("pred_count", "precision", "recall", "f1")])
COLS = ["run", "source", "kept", "cost_usd"] + CFG_FIELDS + METRIC_FIELDS


def record(config, metrics, run, source, cost=None, kept=None, note=None):
    """Append one run. `config` is a pipeline config dict; its prompt is stored by hash, not
    inline, so the store stays readable -- the text itself lives in mutator/notebook/candidates."""
    import hashlib
    cfg = dict(config or {})
    pid = cfg.pop("prompt", None)
    row = {"run": run, "source": source, "kept": kept, "cost_usd": cost, "note": note,
           "prompt_id": hashlib.sha256(pid.encode()).hexdigest()[:8] if pid else None}
    for k in CFG_FIELDS[1:]:
        row[k] = cfg.get(k)
    for k in METRIC_FIELDS:
        row[k] = metrics.get(k)
    with open(STORE, "a") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def load():
    if not os.path.exists(STORE):
        return []
    return [json.loads(l) for l in open(STORE) if l.strip()]


def label(r):
    """Human-readable config, showing only what differs from the 30s/5fps/640px default."""
    p = []
    if r.get("chunk_len") not in (None, 30.0):
        p.append(f"{r['chunk_len']:g}s/{r.get('overlap') or 0:g}s")
    for k in ("fps", "width", "thinking", "model"):
        v = r.get(k)
        if v not in (None, {"fps": 5, "width": 640, "thinking": "low",
                            "model": "gemini-3.7-flash"}[k]):
            p.append(f"{k}={v}")
    if r.get("crop"):
        p.append("crop")
    if r.get("media_resolution"):
        p.append("HIGH")
    return " ".join(p) or "defaults"


def table():
    R = load()
    if not R:
        return None

    def f(r, k, nd=3):
        v = r.get(k)
        return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))

    with open(os.path.join(os.path.dirname(STORE), "results.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(R)

    L = ["# Every scored run", "",
         f"Ground truth is {N_GT} events. **TP** = matched within +/-1.0s *and* typed correctly.",
         "**spotted** = matched on timing alone, ignoring the label -- the gap between the two",
         "columns is how often the model saw the event but called it the wrong thing.", "",
         f"Repeat-run noise measured on an identical config: +/-{NOISE_F1} F1, +/-{NOISE_TP} TP.",
         "A gap smaller than that is not a result.", "",
         "| run | src | config | prompt | F1 | TP | spotted | n_pred | missed | invented "
         "| team | kept | $ |",
         "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
    for r in sorted(R, key=lambda r: -(r.get("headline_f1") or 0)):
        L.append(f"| {r['run']} | {r['source']} | {label(r)} | `{r.get('prompt_id') or '-'}` | "
                 f"**{f(r,'headline_f1')}** | {f(r,'tp')} | {f(r,'spotted')} | {f(r,'n_pred')} | "
                 f"{f(r,'missed')} | {f(r,'invented')} | {f(r,'team_acc',2)} | "
                 f"{r.get('kept') or '-'} | {f(r,'cost_usd',2)} |")
    best = max(R, key=lambda r: r.get("headline_f1") or 0)
    L += ["", f"Best: **{best['run']}** ({label(best)}), F1 {best['headline_f1']:.3f}, "
              f"TP {best['tp']}/{N_GT}, spotted {best['spotted']}/{N_GT}.", "",
          f"## Per-type — {best['run']}", "",
          "| type | GT | predicted | precision | recall | F1 |", "|---|---:|---:|---:|---:|---:|"]
    for t in TYPES:
        L.append(f"| {t} | {GT_N[t]} | {f(best, t+'_pred_count')} | {f(best, t+'_precision')} | "
                 f"{f(best, t+'_recall')} | {f(best, t+'_f1')} |")
    # next to the store, not next to this file -- a blind lineage must not overwrite
    # the project-wide table with its own eight runs.
    out = os.path.join(os.path.dirname(STORE), "results.md")
    open(out, "w").write("\n".join(L) + "\n")
    return out


if __name__ == "__main__":
    print(f"{len(load())} runs -> {table()}")
