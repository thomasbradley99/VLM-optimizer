"""Plain-text timeline of one run: every ground-truth event and every AI event, side by side.

Pairing is the SAME two passes the headline uses -- action-and-time first, then time alone for
what is left -- so the counts here reconcile with the F1 in results.md. report.py pairs on time
alone, which credits fewer correct rows than the headline claims.
"""
import collections, json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "mutator"))
import evaluate as E, ingest, report

TOL = 1.0
NAME = sys.argv[2] if len(sys.argv) > 2 else "best run"
CFG = sys.argv[3] if len(sys.argv) > 3 else ""

gt = ingest.load_events()
pred = json.load(open(sys.argv[1]))

pair, usedp = {}, set()
for i, j in E.match(pred, gt, TOL, "+type"):
    pair[j] = (i, "type"); usedp.add(i)
rest_pi = [i for i in range(len(pred)) if i not in usedp]
rest_g = [j for j in range(len(gt)) if j not in pair]
for a, b in E.match([pred[i] for i in rest_pi], [gt[j] for j in rest_g], TOL, "timing"):
    pair[rest_g[b]] = (rest_pi[a], "time"); usedp.add(rest_pi[a])

def verdict(j):
    if j not in pair: return "missed"
    i, kind = pair[j]
    if kind == "time": return "wrong action"
    return "correct" if (pred[i].get("team") or "") == gt[j]["team"] else "wrong team"

rows = [(g["t"], g, pred[pair[j][0]] if j in pair else None, verdict(j))
        for j, g in enumerate(gt)]
rows += [(p["t"], None, p, "invented") for i, p in enumerate(pred) if i not in usedp]
rows.sort(key=lambda r: r[0])
n = collections.Counter(v for *_, v in rows)
tp = n["correct"] + n["wrong team"]
located = len(gt) - n["missed"]
MARK = {"correct": "[ok]", "wrong team": "[team]", "wrong action": "[action]",
        "missed": "[MISS]", "invented": "[GHOST]"}

W = 96
L = ["=" * W, f"{NAME.upper()}   --   what the AI said vs what actually happened", "=" * W, ""]
if CFG: L += [CFG, ""]
L += [f"There were {len(gt)} real events. The AI reported {len(pred)}.", "",
      f"  Put something within {TOL}s of a real event ....... {located:>4} / {len(gt)}"
      f"   ({100*located/len(gt):.0f}%)",
      f"  ...and named the action correctly ................ {tp:>4} / {located}"
      f"   ({100*tp/located:.0f}%)",
      f"  ...and got the team right too .................... {n['correct']:>4} / {tp}"
      f"   ({100*n['correct']/tp:.0f}%)",
      f"  Reported events that never happened .............. {n['invented']:>4}", "",
      f"  headline F1 (time + action) ......... {2*tp/(len(pred)+len(gt)):.3f}",
      f"  F1 if the team must be right too .... "
      f"{2*n['correct']/(len(pred)+len(gt)):.3f}", "",
      "-" * W, "EVERY EVENT, COUNTED", "-" * W,
      f"  {'':<9}{'verdict':<14}{'count':>7}{'share':>8}   meaning"]
for v in ["correct", "wrong team", "wrong action", "missed", "invented"]:
    base = len(pred) if v == "invented" else len(gt)
    L.append(f"  {MARK[v]:<9}{v:<14}{n[v]:>7}{100*n[v]/base:>7.0f}%   {report.BLURB.get(v,'')}")
L += [f"  {'':<9}{'':<14}{'':>7}{'':>8}   (share of 550 real events; of "
      f"{len(pred)} AI events for invented)", "",
      "-" * W, "PER ACTION", "-" * W,
      f"  {'action':<10}{'real':>6}{'AI said':>9}{'located':>9}{'right action':>14}"
      f"{'+right team':>13}"]
for ty in E.TYPES:
    real = sum(x["type"] == ty for x in gt)
    said = sum(x.get("type") == ty for x in pred)
    loc = sum(1 for _, g, p, v in rows if g and g["type"] == ty and p)
    ok = sum(1 for _, g, p, v in rows if g and g["type"] == ty and v in ("correct", "wrong team"))
    okt = sum(1 for _, g, p, v in rows if g and g["type"] == ty and v == "correct")
    L.append(f"  {ty:<10}{real:>6}{said:>9}{loc:>9}{ok:>8} ({100*ok/real:>3.0f}%)"
             f"{okt:>7} ({100*okt/real:>3.0f}%)")
L += ["", "-" * W, "WHEN IT NAMED THE WRONG ACTION, WHAT DID IT SAY INSTEAD?", "-" * W, "",
      "  real \\ AI said" + "".join(f"{t[:7]:>8}" for t in E.TYPES)]
cm = collections.Counter((g["type"], p.get("type")) for _, g, p, _ in rows if g and p)
for gty in E.TYPES:
    L.append(f"  {gty:<14}" + "".join(
        (f"[{cm[(gty,p)]}]".rjust(8) if p == gty else f"{cm[(gty,p)]:>8}") for p in E.TYPES))
L += ["  [n] on the diagonal = got it right. Everything off it is a mix-up.", "",
      "-" * W, "TIMELINE -- every event, in order", "-" * W, "",
      f"  {'TIME':<8}{'WHAT ACTUALLY HAPPENED':<28}{'WHAT THE AI SAID':<28}{'VERDICT':<11}{'off by':>8}",
      "  " + "-" * (W - 2)]
for t, g, p, v in rows:
    real = f"{g['team']} {g['type']}" + (f" #{g['number']}" if g.get("number") else "") if g \
        else "-- nothing happened --"
    said = f"{p.get('team')} {p.get('type')}" if p else "-- nothing --"
    off = f"{p['t']-g['t']:+.1f}s" if (g and p) else ""
    L.append(f"  {report.mmss(t):<8}{real:<28}{said:<28}{MARK[v]:<11}{off:>8}")
out = os.path.join(HERE, "best_run.txt")
open(out, "w").write("\n".join(L) + "\n")
print("\n".join(L[:34]))
print(f"\n... written to {out} ({len(rows)} rows)")
