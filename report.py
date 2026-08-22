"""Plain-language evaluation report: for each moment, what the AI thought, what actually happened,
and whether it was right.

Every ground-truth event and every AI event falls into exactly one of five verdicts, so the counts
partition both sets and nothing hides. Matching is done ONCE on time -- a pair that disagrees on
type still survives to be shown, which is what makes the confusion matrix and the timeline possible.
"""
import collections

import evaluate as E

CORRECT, TEAM, ACTION, MISSED, INVENTED = "correct", "wrong team", "wrong action", "missed", "invented"
VERDICTS = [CORRECT, TEAM, ACTION, MISSED, INVENTED]
MARK = {CORRECT: "\U0001f7e9", TEAM: "\U0001f7e8", ACTION: "\U0001f7e8",
        MISSED: "\U0001f7e5", INVENTED: "\U0001f7e5"}
BLURB = {CORRECT: "right action, right team", TEAM: "right action, WRONG TEAM",
         ACTION: "wrong action", MISSED: "AI saw nothing here", INVENTED: "no such event"}


def mmss(t):
    return f"{int(t) // 60:02d}:{int(t) % 60:02d}"


def _verdict(g, p):
    if g is None:
        return INVENTED
    if p is None:
        return MISSED
    if p.get("type") != g["type"]:
        return ACTION
    return CORRECT if (p.get("team") or "") == g["team"] else TEAM


def build(pred, gt, tol):
    """Rows of (time, gt_event_or_None, pred_event_or_None, verdict), in match order."""
    by_gt = {j: i for i, j in E.match(pred, gt, tol, "timing")}
    paired = set(by_gt.values())
    rows = [(g["t"], g, pred[by_gt[j]] if j in by_gt else None) for j, g in enumerate(gt)]
    rows += [(p["t"], None, p) for i, p in enumerate(pred) if i not in paired]
    rows.sort(key=lambda r: r[0])
    return [(t, g, p, _verdict(g, p)) for t, g, p in rows]


def render(pred, gt, tol=1.0, max_timeline=40):
    rows = build(pred, gt, tol)
    n = collections.Counter(v for *_, v in rows)
    spotted = len(gt) - n[MISSED]
    right_action = n[CORRECT] + n[TEAM]
    L = ["=" * 92, f"WHAT THE AI SAW vs WHAT ACTUALLY HAPPENED   (matched within {tol}s)", "=" * 92, "",
         f"There were {len(gt)} real events. The AI reported {len(pred)}.", "",
         f"  It spotted something at the right moment ......... {spotted:>4} / {len(gt)}"
         f"  ({100*spotted/len(gt):.0f}%)",
         f"  ...and named the right action .................... {right_action:>4} / {spotted}"
         f"  ({100*right_action/spotted:.0f}% of those)",
         f"  ...and got the team right too .................... {n[CORRECT]:>4} / {right_action}"
         f"  ({100*n[CORRECT]/right_action:.0f}% of those)",
         f"  It also invented events that never happened ...... {n[INVENTED]:>4}", "",
         "VERDICT ON EVERY EVENT", f"  {'verdict':<24}{'count':>7}{'share':>8}   meaning"]
    for v in VERDICTS:
        base = len(pred) if v == INVENTED else len(gt)
        L.append(f"  {MARK[v]} {v:<22}{n[v]:>7}{100*n[v]/base:>7.0f}%   {BLURB[v]}")
    L.append(f"  {'':<24}{'':>7}{'':>8}   (share is of {len(gt)} real events, or {len(pred)} AI events for 'invented')")

    L += ["", "HOW GOOD IS IT, PER ACTION",
          f"  {'action':<10}{'real':>6}{'AI said':>9}{'spotted':>9}{'right action':>14}{'+right team':>13}"]
    for ty in E.TYPES:
        real = sum(g["type"] == ty for g in gt)
        said = sum(p.get("type") == ty for p in pred)
        sp = sum(1 for _, g, p, v in rows if g and g["type"] == ty and v != MISSED)
        ra = sum(1 for _, g, p, v in rows if g and g["type"] == ty and v in (CORRECT, TEAM))
        ct = sum(1 for _, g, p, v in rows if g and g["type"] == ty and v == CORRECT)
        L.append(f"  {ty:<10}{real:>6}{said:>9}{sp:>9}{ra:>9} ({100*ra/real if real else 0:>3.0f}%)"
                 f"{ct:>8} ({100*ct/real if real else 0:>3.0f}%)")

    L += ["", "WHEN IT NAMED THE WRONG ACTION, WHAT DID IT SAY INSTEAD?",
          "  " + "real \\ AI said".ljust(14) + "".join(f"{t[:7]:>8}" for t in E.TYPES)]
    cm = collections.Counter((g["type"], p.get("type")) for _, g, p, v in rows if g and p)
    for gty in E.TYPES:
        cells = "".join((f"{cm[(gty, pty)]:>8}" if gty != pty else f"{'[' + str(cm[(gty, pty)]) + ']':>8}")
                        for pty in E.TYPES)
        L.append(f"  {gty:<14}{cells}")
    L.append("  [n] on the diagonal = got it right. Everything off-diagonal is a mix-up.")

    L += ["", "TIMELINE", f"  {'TIME':<8}{'WHAT THE AI THOUGHT':<28}{'WHAT ACTUALLY HAPPENED':<28}{'VERDICT':<26}{'off by':>8}",
          "  " + "-" * 96]
    shown = rows if max_timeline is None else rows[:max_timeline]
    for t, g, p, v in shown:
        ai = f"{p.get('team')} {p.get('type')}" if p else "-- nothing --"
        truth = f"{g['team']} {g['type']}" if g else "-- nothing happened --"
        off = f"{p['t'] - g['t']:+.1f}s" if (g and p) else ""
        L.append(f"  {mmss(t):<8}{ai:<28}{truth:<28}{MARK[v] + ' ' + v:<25}{off:>8}")
    if max_timeline is not None and len(rows) > max_timeline:
        L.append(f"  ... {len(rows) - max_timeline} more rows -- full timeline in report.txt")
    return "\n".join(L)
