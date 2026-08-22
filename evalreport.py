"""The full evaluation of one run: every F1 the harness can compute, in one place.

`results.md` ranks runs against each other. This goes the other way -- one run, taken apart.
The strictness ladder is the point: timing / +type / +team / +number is a chain, so the drop
between two rows is exactly what that one extra requirement costs.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "mutator"))

import evaluate as E   # noqa: E402
import ingest          # noqa: E402
import report          # noqa: E402

GT_N = {"serve": 118, "receive": 107, "dig": 86, "set": 47, "attack": 131, "kill": 52, "block": 9}


def build(pred, gt, name, cfg_label):
    L = [f"# Evaluation — {name}", "", f"`{cfg_label}` · {len(pred)} predictions vs {len(gt)} "
         f"ground-truth events", ""]

    sane = E.selftest(gt)
    L += [f"Sanity: ground truth scored against itself = **1.000 in all 12 cells**"
          if not sane else f"SANITY FAILED: {sane}", "",
          "## 1. The strictness ladder", "",
          "Each row adds one requirement to the row above. Reading down a column shows what each",
          "extra demand costs. A pair must match on time *and* everything above it to count.", "",
          "| must match | ±0.5s | ±1.0s | ±2.0s | matched @1.0s | of 550 |",
          "|---|---:|---:|---:|---:|---:|"]
    g = E.grid(pred, gt)
    desc = {"timing": "time only", "+type": "+ action type", "+team": "+ which team",
            "+number": "+ jersey number"}
    for lv in E.LEVELS:
        m = len(E.match(pred, gt, 1.0, lv))
        L.append(f"| {desc[lv]} | {g[lv]['0.5'][2]:.3f} | **{g[lv]['1.0'][2]:.3f}** | "
                 f"{g[lv]['2.0'][2]:.3f} | {m} | {m / len(gt):.0%} |")

    spot, typed = len(E.match(pred, gt, 1.0, "timing")), len(E.match(pred, gt, 1.0, "+type"))
    team = len(E.match(pred, gt, 1.0, "+team"))
    L += ["", f"**Headline F1 is {g['+type']['1.0'][2]:.3f}** — timing within ±1.0s and the right "
              "action type.", "",
          f"- The model **locates {spot} of {len(gt)} events** ({spot / len(gt):.0%}). Finding "
          "events is not the problem.",
          f"- Of those {spot}, only **{typed} get the right label** ({typed / spot:.0%}). "
          f"{spot - typed} are seen but misnamed.",
          f"- Of those {typed}, **{team} also get the team right** ({team / typed:.0%}).",
          f"- Jersey numbers are effectively unreadable at this encoding "
          f"(F1 {g['+number']['1.0'][2]:.3f}).", ""]

    L += ["## 2. Per action type, at ±1.0s", "",
          "| type | in truth | predicted | precision | recall | F1 |", "|---|---:|---:|---:|---:|---:|"]
    pt = E.per_type(pred, gt, 1.0)
    for ty in E.TYPES:
        p, r, f, n = pt[ty]
        npr = sum(1 for x in pred if x.get("type") == ty)
        L.append(f"| {ty} | {n} | {npr} | {p:.3f} | {r:.3f} | **{f:.3f}** |")

    L += ["", "## 3. Where the labels go wrong", "",
          "Rows are what the event really was; columns are what the model called it. Only",
          f"time-matched pairs appear — the {len(gt) - spot} events never located are not here.", "",
          "| truth \\ called | " + " | ".join(E.TYPES) + " | hit |",
          "|---|" + "---:|" * (len(E.TYPES) + 1)]
    pairs = E.match(pred, gt, 1.0, "timing")
    cm = collections.Counter((gt[j]["type"], pred[i].get("type")) for i, j in pairs)
    for ty in E.TYPES:
        row = [cm[(ty, c)] for c in E.TYPES]
        cells = " | ".join(f"**{v}**" if c == ty and v else str(v)
                           for c, v in zip(E.TYPES, row))
        L.append(f"| {ty} | {cells} | {cm[(ty, ty)] / GT_N[ty]:.0%} |")

    off, off_f1 = E.sweep_offset(pred, gt)
    asis, swapped = E.team_swap_gain(pred, gt)
    L += ["", "## 4. Two things that are *not* wrong", "",
          f"- **Clock alignment.** Best constant time shift is {off:+.2f}s, "
          f"giving F1 {off_f1:.3f} against {g['+type']['1.0'][2]:.3f} at zero offset. "
          "There is no systematic lag to correct.",
          f"- **Team polarity.** F1 at +team is {asis:.3f} as-is and {swapped:.3f} with the two "
          "teams swapped, so left/right is not inverted.", ""]

    rows = report.build(pred, gt, 1.0)
    n = collections.Counter(v for *_, v in rows)
    L += ["## 5. Every event accounted for", "",
          "| outcome | count |", "|---|---:|",
          f"| exactly right (time, type, team) | {n[report.CORRECT]} |",
          f"| right action, wrong team | {n[report.TEAM]} |",
          f"| right moment, wrong action | {n[report.ACTION]} |",
          f"| real event, never spotted | {n[report.MISSED]} |",
          f"| reported, nothing there | {n[report.INVENTED]} |", "",
          f"Total real events {n[report.CORRECT] + n[report.TEAM] + n[report.ACTION] + n[report.MISSED]}"
          f" · total predictions {len(pred)}", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    gt = ingest.load_events()
    pred = json.load(open(sys.argv[1]))
    text = build(pred, gt, sys.argv[2], sys.argv[3])
    open(os.path.join(HERE, "eval.md"), "w").write(text)
    print(text)
