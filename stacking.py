"""Did improvements COMPOUND, or did each one just replace the last?

The walk is linear -- every round starts from the previous round's config -- so a run of
consecutive rounds that each improve on their predecessor means each change survived into the
next result. That is the definition of stacking used here, and it is the thing that separates
evolution from search: a hill climber that trades one gain for another never produces a chain
longer than one.

TP must rise across the chain too. F1 alone can rise from the denominator shrinking, which is
the model predicting fewer events rather than better ones.
"""
import json, os, sys

store = sys.argv[1] if len(sys.argv) > 1 else "mutator/lineages/basic/results.jsonl"
nb = os.path.dirname(store)
R = [json.loads(l) for l in open(store)]
R.sort(key=lambda r: r["run"])

def change(run):
    p = os.path.join(nb, "entries", f"{run}.md")
    if not os.path.exists(p):
        return ""
    t = open(p).read()
    i = t.find("## CHANGE")
    if i < 0: return ""
    seg = t[i + 9:t.find("```config", i) if "```config" in t[i:] else i + 400]
    return " ".join(seg.split())[:95]

print(f"{'run':<10}{'F1':>8}{'dF1':>8}{'TP':>6}{'dTP':>6}   what changed")
chains, cur = [], []
prev = None
for r in R:
    d = None if prev is None else r["headline_f1"] - prev["headline_f1"]
    dt = None if prev is None else r["tp"] - prev["tp"]
    mark = ""
    if d is not None and d > 0:
        cur.append(r); mark = "  ^"
    else:
        if len(cur) >= 2: chains.append(cur)
        cur = [r] if d is None else []
    print(f"{r['run']:<10}{r['headline_f1']:>8.3f}"
          f"{('' if d is None else f'{d:+.3f}'):>8}{r['tp']:>6}"
          f"{('' if dt is None else f'{dt:+d}'):>6}{mark}   {change(r['run'])}")
    prev = r
if len(cur) >= 2: chains.append(cur)

print()
if not chains:
    print("NOTHING STACKED. No two consecutive rounds both improved -- every gain was")
    print("followed by a loss, which is search, not accumulation.")
for c in chains:
    f0 = c[0]["headline_f1"] - (R[R.index(c[0]) - 1]["headline_f1"] if R.index(c[0]) else 0)
    a, b = R[R.index(c[0]) - 1], c[-1]
    print(f"STACKED: {len(c)} consecutive improvements, {a['run']} -> {b['run']}")
    print(f"  F1 {a['headline_f1']:.3f} -> {b['headline_f1']:.3f}  ({b['headline_f1']-a['headline_f1']:+.3f})"
          f"   TP {a['tp']} -> {b['tp']}  ({b['tp']-a['tp']:+d})")
    for r in c:
        print(f"    {r['run']}: {change(r['run'])}")
