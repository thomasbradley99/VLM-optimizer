"""The running lab notes: one file, rewritten after every round, kept short.

Regenerated rather than appended so the summary table at the top stays current. Everything comes
from what the rounds already wrote to disk -- no model calls, no pipeline runs, costs nothing.
"""
import glob
import json
import os
import re
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
import notebook as _nb
NB = _nb.NB      # follows MUTATOR_NB so a lineage writes into its own directory
OUT = os.path.join(NB, "labnotes.md")   # per-lineage, same reason as results.md
BASE_TP, BASE_F1, BASE_NPRED = 202, 0.342, 630


def _sec(text, name):
    m = re.search(rf"##\s*{name}\s*\n(.*?)(?=\n##\s|\Z)", text, re.S)
    return m.group(1).strip() if m else ""


def _brief(text, n=2, width=96):
    """First n sentences, code fences stripped, wrapped."""
    s = " ".join(re.sub(r"```.*?```", "", text, flags=re.S).split())
    s = " ".join(re.split(r"(?<=[.!?])\s+", s)[:n]).strip()
    return textwrap.fill(s, width)


def rounds():
    hist = {h["iter"]: h for h in json.load(open(os.path.join(NB, "history.json")))}
    out = []
    for p in sorted(glob.glob(os.path.join(NB, "entries", "iter_*.md"))):
        n = int(re.search(r"iter_(\d+)", p).group(1))
        t = open(p).read()
        g = re.search(r"direction (\d+)/(\d+)", t)
        f = re.search(r"headline_f1 ([\d.]+) -> ([\d.]+)", t)
        if n not in hist:
            # an entry with no history record is an abandoned round: the harness commits the
            # conjecture to disk before running the pipeline, so a run killed mid-round leaves
            # the proposal behind with no outcome. It is not a result and does not belong here.
            continue
        m = hist[n].get("metrics", {})
        out.append({"n": n, "t": t, "tp": m.get("tp"), "n_pred": m.get("n_pred"),
                    "kept": hist[n].get("improved"),
                    "dir": (int(g.group(1)), int(g.group(2))) if g else (0, 0),
                    "f1": (float(f.group(1)), float(f.group(2))) if f else (0.0, 0.0)})
    return out


def render():
    R = rounds()
    if not R:
        return "# Mutator lab notes\n\nNo rounds yet."
    tp_hits = sum(r["dir"][0] for r in R), sum(r["dir"][1] for r in R)
    best = max(R, key=lambda r: r["f1"][1])
    L = ["# Mutator lab notes", "",
         "Each round: diagnose, commit a falsifiable prediction to disk, re-run the pipeline, grade",
         "the prediction against computed numbers, write a verdict. Losing rounds are auto-reverted.",
         "",
         "**TP** = events matched in time *and* typed correctly. F1 can rise while TP falls, simply",
         "by predicting less — so TP is the number that says whether the model actually sees more.",
         "", "| round | F1 | TP | predictions made | called right | kept |",
         "|---|---|---|---|---|---|",
         f"| _base_ | {BASE_F1:.3f} | **{BASE_TP}** | {BASE_NPRED} | – | – |"]
    for r in R:
        L.append(f"| {r['n']} | {r['f1'][0]:.3f} → {r['f1'][1]:.3f} | {r['tp']} | {r['n_pred']} | "
                 f"{r['dir'][0]}/{r['dir'][1]} | {'yes' if r['kept'] else '**reverted**'} |")
    L += ["",
          f"Best F1 round {best['n']} ({best['f1'][1]:.3f}, TP {best['tp']}). "
          f"Best TP {max(r['tp'] for r in R)} — against **{BASE_TP} for the original prompt**. "
          f"Predictions right {tp_hits[0]}/{tp_hits[1]} ({100 * tp_hits[0] / tp_hits[1]:.0f}%).",
          "", "---", ""]
    for r in R:
        L += [f"## Round {r['n']} — {'kept' if r['kept'] else 'REVERTED'} · "
              f"F1 {r['f1'][0]:.3f}→{r['f1'][1]:.3f} · TP {r['tp']} · called {r['dir'][0]}/{r['dir'][1]}",
              "", f"**Thought:** {_brief(_sec(r['t'], 'CONJECTURE'), 2)}", "",
              f"**Changed:** {_brief(_sec(r['t'], 'CHANGE'), 1)}", "",
              f"**Learned:** {_brief(_sec(r['t'], 'VERDICT'), 2)}", ""]
    L += ["---", "", "## Current beliefs", "",
          (open(os.path.join(NB, "summary.md")).read().strip()
           if os.path.exists(os.path.join(NB, "summary.md")) else "(none yet)")]
    return "\n".join(L)


def write():
    text = render()
    open(OUT, "w").write(text)
    return OUT


if __name__ == "__main__":
    print(f"wrote {write()}")
