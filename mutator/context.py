"""Assemble everything the mutator is allowed to see.

Deliberately withholds any natural-language interpretation of the ground-truth schema. The mutator
gets the mechanical derivation rules and the counts; inferring what `assist-2` implies about the
annotator's definition is the diagnosis we are testing for, so handing it over would make the test
unfailable.

Reads the baseline modules only. Nothing outside mutator/ is written.
"""
import asyncio
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import detect          # noqa: E402
import dedupe as dd    # noqa: E402
import evaluate as E   # noqa: E402
import ingest          # noqa: E402
import metrics         # noqa: E402
import report          # noqa: E402

TOL = 1.0

# Mechanical rules only. No sentence explaining what any of these MEAN -- see module docstring.
SCHEMA_BLOCK = """Ground-truth events derive from a human scout's CSV. The scout recorded a PLAYER,
NUMBER, COLOR, ACTION, QUALIFIERS and TIME per row; the seven event types are derived from ACTION
and QUALIFIERS by these rules, applied in this order:

  block    = ACTION == 'block'                (9 events)
  set      = ACTION == 'assist-2'             (47 events)
  serve    = 'serve' in QUALIFIERS            (118 events)
  receive  = ACTION == 'receive'              (107 events)
  dig      = 'dig' in QUALIFIERS              (86 events)
  kill     = 'kill' in QUALIFIERS             (52 events)
  attack   = 'attack' in QUALIFIERS           (131 events)

550 events total, spanning 62 minutes. Predictions are matched to ground truth greedily by nearest
timestamp, one-to-one, within 1.0s."""


def current_results():
    """Run the pipeline with whatever detect.PROMPT currently holds. Fully cached => instant, $0."""
    gt = ingest.load_events()
    index = json.load(open(os.path.join(ROOT, "chunks", "index.json")))
    raw, stats = asyncio.run(detect.run(index, concurrency=32))
    return gt, dd.dedupe(raw), stats


def _scoreline_block(pred, gt):
    """What the match result looks like if you believe the predictions.

    Detecting contacts is the means; the score is the end. Without this the mutator optimises
    event counts and never learns that its team attribution is skewed enough to hand the match to
    the wrong side.
    """
    m = metrics.scoreline(pred, gt)
    tw = sum(1 for e in gt if e.get("point") and e["team"] == "white")
    tb = sum(1 for e in gt if e.get("point") and e["team"] == "blue")
    won = lambda w, b: "white" if w > b else ("blue" if b > w else "tied")
    L = ["Every point-flagged event is a point for the team that made it.", "",
         f"{'':<10}{'white':>8}{'blue':>7}{'total':>8}   winner",
         f"{'REAL':<10}{tw:>8}{tb:>7}{tw + tb:>8}   {won(tw, tb)}",
         f"{'YOURS':<10}{m['score_white']:>8}{m['score_blue']:>7}"
         f"{m['point_pred_count']:>8}   {won(m['score_white'], m['score_blue'])}",
         "",
         f"point_f1 {m['point_f1']:.3f}  (point events matched on time AND team AND the point flag; "
         f"{m['point_tp']} of {tw + tb} found)",
         f"score_margin_err {m['score_margin_err']:.0f}  (real margin {tw - tb:+d}, "
         f"yours {m['score_white'] - m['score_blue']:+d})",
         f"winner_correct {m['winner_correct']:.0f}", "",
         "point_f1 cannot be gamed by predicting fewer points -- it needs the right moment, the",
         "right team and the flag. score_margin_err is what a person checks. Both are in your",
         "metric vocabulary and both are fair game to predict."]
    return "\n".join(L)


def _scores_block(pred, gt):
    g = E.grid(pred, gt)
    rows = report.build(pred, gt, TOL)
    tp = len(E.match(pred, gt, TOL, "+type"))
    L = [f"Headline F1 (+/-{TOL}s, timing+type): {g['+type'][str(TOL)][2]:.3f}",
         f"TRUE POSITIVES: {tp}   (events matched in time AND given the right type)",
         "",
         f"F1 = 2*TP / (n_pred + n_gt) = 2*{tp} / ({len(pred)} + {len(gt)}). Note what this means:",
         "predicting FEWER events raises F1 even when TP falls, because the denominator shrinks.",
         "TP is the only number that measures whether the model actually sees more. Watch it.",
         "",
         f"F1 timing only: {g['timing'][str(TOL)][2]:.3f}   "
         f"+team: {g['+team'][str(TOL)][2]:.3f}   +number: {g['+number'][str(TOL)][2]:.3f}",
         f"\nTotal: {len(gt)} real events, {len(pred)} predicted.", "",
         f"{'type':<9}{'REAL':>6}{'PREDICTED':>11}{'precision':>11}{'recall':>9}{'F1':>7}"]
    for ty in E.TYPES:
        real = sum(x["type"] == ty for x in gt)
        said = sum(x.get("type") == ty for x in pred)
        hit = sum(1 for _, gg, pp, v in rows
                  if gg and gg["type"] == ty and v in (report.CORRECT, report.TEAM))
        p, r, f = E.prf(hit, said, real)
        L.append(f"{ty:<9}{real:>6}{said:>11}{p:>11.3f}{r:>9.3f}{f:>7.3f}")
    return "\n".join(L)


def _confusion_block(pred, gt):
    rows = report.build(pred, gt, TOL)
    cm = collections.Counter((g["type"], p.get("type")) for _, g, p, _ in rows if g and p)
    L = ["Rows = what the event really was. Columns = what the model called it.",
         "Only time-matched pairs appear; events the model missed entirely are not in this table.",
         "",
         "real \\ predicted".ljust(18) + "".join(f"{t[:7]:>8}" for t in E.TYPES) + f"{'TOTAL':>8}"]
    for gty in E.TYPES:
        tot = sum(cm[(gty, p)] for p in E.TYPES)
        L.append(f"{gty:<18}" + "".join(f"{cm[(gty, p)]:>8}" for p in E.TYPES) + f"{tot:>8}")
    L.append(f"{'TOTAL':<18}" + "".join(f"{sum(cm[(g, p)] for g in E.TYPES):>8}" for p in E.TYPES))
    n = collections.Counter(v for *_, v in rows)
    L += ["", f"Of {len(gt)} real events, {len(gt) - n[report.MISSED]} were spotted within {TOL}s "
              f"and {n[report.MISSED]} were missed entirely.",
          f"The model also reported {n[report.INVENTED]} events with no real event nearby."]
    return "\n".join(L)


def _trend_block(history):
    """Round-over-round movement. Without this the mutator cannot see that it has been trading
    recall for precision -- each round looks like progress in isolation."""
    if not history:
        return "No completed rounds yet."
    L = [f"{'round':>6}{'F1':>8}{'TP':>6}{'n_pred':>8}{'missed':>8}{'invented':>10}{'kept':>10}"]
    for h in history:
        m, kept = h["metrics"], ("yes" if h["improved"] else "REVERTED")
        L.append(f"{h['iter']:>6}{m['headline_f1']:>8.3f}{m['tp']:>6}{m['n_pred']:>8}"
                 f"{m['missed']:>8}{m['invented']:>10}{kept:>10}")
    first, last = history[0]["metrics"], history[-1]["metrics"]
    L += ["", f"Across all rounds: TP {first['tp']} -> {last['tp']}, "
              f"n_pred {first['n_pred']} -> {last['n_pred']}, "
              f"missed {first['missed']} -> {last['missed']}, "
              f"invented {first['invented']} -> {last['invented']}.",
          "If TP is flat or falling while F1 rises, you are not improving perception -- you are "
          "only making the model guess less. That is not the goal."]
    return "\n".join(L)


def _pair(pred, gt):
    """Pair predictions to events the same way the headline is scored: action-and-time first,
    then time alone for what is left. report.build pairs on time only, which credits fewer
    correct rows than the headline claims and made the two disagree by 78 events."""
    pair, usedp = {}, set()
    for i, j in E.match(pred, gt, TOL, "+type"):
        pair[j] = (i, "type"); usedp.add(i)
    rest_pi = [i for i in range(len(pred)) if i not in usedp]
    rest_g = [j for j in range(len(gt)) if j not in pair]
    for a, b in E.match([pred[i] for i in rest_pi], [gt[j] for j in rest_g], TOL, "timing"):
        pair[rest_g[b]] = (rest_pi[a], "time"); usedp.add(rest_pi[a])
    return pair, usedp


def _phantom_block(pred, gt):
    """Where the phantoms actually are.

    Five separate rounds have conjectured that phantoms are casual contacts during dead time and
    tried to veto them from the prompt; all five failed. The reason is one number that no aggregate
    in this report carried: the large majority of phantoms fall INSIDE live rallies, not between
    them. The full event list contains this, but only for a reader willing to scan 869 rows and
    reason about the gaps -- so it went unread. Stating it directly is the difference.
    """
    pair, usedp = _pair(pred, gt)
    ev = sorted(gt, key=lambda g: g["t"])
    rallies, cur = [], [ev[0]]
    for g in ev[1:]:
        if g["t"] - cur[-1]["t"] > 10.0:
            rallies.append(cur); cur = [g]
        else:
            cur.append(g)
    rallies.append(cur)
    spans = [(r[0]["t"] - 2.0, r[-1]["t"] + 2.0) for r in rallies]
    ph = [p for i, p in enumerate(pred) if i not in usedp]
    inside = [p for p in ph if any(a <= p["t"] <= b for a, b in spans)]
    dead = [p for p in ph if p not in inside]
    ci = collections.Counter(p.get("type") for p in inside)
    cd = collections.Counter(p.get("type") for p in dead)
    n = len(ph) or 1
    L = [f"The {len(ph)} predictions that matched no real event, split by WHEN they happened.",
         f"A rally here is a run of real events with no gap longer than 10s; there are "
         f"{len(rallies)} of them against {sum(1 for g in gt if g.get('point'))} scored points.", "",
         f"  inside a live rally .......... {len(inside):>4}  ({100*len(inside)/n:.0f}%)",
         f"  in dead time between rallies . {len(dead):>4}  ({100*len(dead)/n:.0f}%)", "",
         f"  {'type':<9}{'in rally':>10}{'dead time':>11}"]
    for ty in E.TYPES:
        L.append(f"  {ty:<9}{ci[ty]:>10}{cd[ty]:>11}")
    L += ["", "Read this before conjecturing about phantoms. If most of them are inside rallies, a",
          "prompt rule telling the model to ignore casual dead-time contacts cannot remove them --",
          "the model is over-reporting contacts during play that is genuinely happening."]
    return "\n".join(L)


def _events_block(pred, gt):
    """Every event, both sides, in order.

    The aggregates cannot show where the errors sit in time, and that has cost real rounds: four
    consecutive rounds attacked phantoms believed to be casual dead-time contacts, when 83% of
    them fall inside live rallies. That was visible in this list and in nothing else.
    """
    pair, usedp = _pair(pred, gt)
    def verdict(j):
        if j not in pair: return "MISS"
        i, kind = pair[j]
        if kind == "time": return "action"
        return "ok" if (pred[i].get("team") or "") == gt[j]["team"] else "team"
    rows = [(g["t"], g, pred[pair[j][0]] if j in pair else None, verdict(j))
            for j, g in enumerate(gt)]
    rows += [(p["t"], None, p, "GHOST") for i, p in enumerate(pred) if i not in usedp]
    rows.sort(key=lambda r: r[0])
    n = collections.Counter(v for *_, v in rows)
    L = ["Every real event and every prediction, in order. Left is what the scout recorded,",
         "right is what the model said. Verdicts:",
         "  ok     right moment, right action, right team",
         "  team   right action, wrong team",
         "  action right moment, wrong action",
         "  MISS   real event, the model reported nothing within 1.0s",
         "  GHOST  the model reported a contact with no real event near it", "",
         f"  ok {n['ok']}   team {n['team']}   action {n['action']}   MISS {n['MISS']}   "
         f"GHOST {n['GHOST']}", "",
         f"  {'time':<7}{'REALLY WAS':<22}{'MODEL SAID':<22}verdict"]
    for t, g, p, v in rows:
        real = (f"{g['team']} {g['type']}" if g else "--")
        said = (f"{p.get('team')} {p.get('type')}" if p else "--")
        L.append(f"  {report.mmss(t):<7}{real:<22}{said:<22}{v}")
    return "\n".join(L)


def _elide_prompt(text):
    """Drop the embedded candidate prompt from an entry -- section 1 already carries the live one,
    and reverted prompts are not in play. Keeps context from tripling as rounds accumulate."""
    return re.sub(r"```prompt\n.*?```", "```\n[full candidate prompt omitted]\n```", text, flags=re.S)


def _change_line(text):
    """One line saying what a round actually changed, taken from its CHANGE section.

    The record of what was tried belongs in the context; the essay about what it meant does not.
    Five rounds in full plus a rewritten beliefs document came to ~11,000 tokens against ~400 of
    evidence about the match -- three quarters of the report was the mutator reading itself, and
    a false belief written in round 13 steered six later rounds because nothing could dislodge it.
    """
    m = re.search(r"##\s*CHANGE\s*\n(.+?)(?:\n\s*```|\n##|\Z)", text, re.S)
    body = " ".join(m.group(1).split()) if m else ""
    return (body[:130] + "...") if len(body) > 130 else (body or "(no change recorded)")


def _prompt_diffs(nb):
    """What actually changed in the prompt each round, as a diff against the round before.

    Without this the run table shows rounds with identical settings and F1 from 0.297 to 0.390
    and no visible cause, because the prompt is stored as a hash. Fourteen of sixteen rounds
    changed the prompt; none of them could compare two. Full prompts would cost ~15k tokens for
    thirty rounds, a diff costs ~150.
    """
    import difflib
    import notebook as NB
    out, prev, prev_n = [], None, None
    for e in nb["entries"]:
        f = os.path.join(NB.CANDIDATES, f"config_{e['n']:03d}.json")
        if not os.path.exists(f):
            continue
        try:
            cur = json.load(open(f)).get("prompt") or ""
        except Exception:
            continue
        if prev is not None and cur.strip() != prev.strip():
            d = [l for l in difflib.unified_diff(prev.split("\n"), cur.split("\n"),
                                                 lineterm="", n=0)
                 if l[:1] in "+-" and not l.startswith(("+++", "---"))]
            if d:
                out.append(f"  iter {prev_n:03d} -> {e['n']:03d}:")
                for l in d[:14]:
                    out.append(f"    {l[:150]}")
                if len(d) > 14:
                    out.append(f"    ... {len(d) - 14} more changed lines")
        prev, prev_n = cur, e["n"]
    if not out:
        return None
    return ("How the prompt changed each round. Lines starting - were removed, + were added.\n"
            "Pair these with the scores in the table above: that is the only way to tell which\n"
            "wording moved the number.\n\n" + "\n".join(out))


def _notebook_block(nb, live=None):
    L = []
    if live:
        L += [f"THE CONFIG IN PLAY IS {live['name']}. Section 1 above is that config and section 2",
              "is how it scored. You are continuing from it.", ""]
        b = (live.get("best") or {})
        if b.get("headline_f1") is not None:
            L += ["THERE IS NO AUTOMATIC REVERT. Whatever you try, the next round starts from it --",
                  "worse scores included. Going downhill for a round to reach something better is",
                  "allowed and is sometimes the only way past a plateau.", "",
                  f"The best run so far scored {b['headline_f1']:.3f} (iter {b['iter']}). To return to",
                  "it, copy the prompt printed at the end of this section verbatim and pair it with",
                  "the settings shown there. That is the only way back: nothing reverts for you.", ""]
        if live.get("drift"):
            L += [f"YOU ARE {live['drift']:.3f} BELOW YOUR OWN BEST and drifting. That is larger than",
                  "the +/-0.028 repeat-run noise, so it is a real loss, not a wobble. Either say why",
                  "this line is still worth following, or go back to the best config and change",
                  "something else from there.", ""]
    if nb is None or not nb.get("entries"):
        return "\n".join(L + ["No rounds yet."]) if L else "No rounds yet. There is no prior work."
    last = nb["entries"][-1]
    v = re.search(r"##\s*VERDICT\s*\n(.+?)(?=\n##\s|\Z)", last["text"], re.S)
    if v:
        # Round 21 ended "abandon this line of prompt engineering and attack it mechanically by
        # shrinking the overlap". Round 22 changed the prompt. So did 23, 24, 25, 26, 27 and 28 --
        # eight rounds, no lever touched but one, because the plan was written to a file that
        # nothing read again. What a round decides to do next is the only part of its reasoning
        # that has to survive into the next round.
        L += ["WHAT YOU CONCLUDED LAST ROUND, in full. You wrote this after seeing the numbers.",
              "If it names a next move, either take it or say why you are not taking it.", "",
              "  " + "\n  ".join(" ".join(v.group(1).split("\n")).split("\n")), "", ""]
    # This block used to say the full prompt of any round was "on disk if you need it". It is --
    # but the mutator is a single text call with no tools and no filesystem, so it could not fetch
    # anything. Lineage B spent rounds 4, 5 and 6 trying to restore a prompt it could not see;
    # round 5 announced it was "restoring a clean prompt" and emitted one 44% similar to the
    # target. Elitism used to hide this by restoring the champion FILE on a bad round. With the
    # revert removed, the only way back is to put the text in front of it.
    L += ["WHAT YOU HAVE TRIED, one line per round. You cannot read files -- everything you get is",
          "in this report, so a prompt you want to go back to has to be copied from below.", ""]
    for e in nb["entries"]:
        L.append(f"  iter {e['n']:03d}: {_change_line(e['text'])}")
    dd_ = _prompt_diffs(nb)
    if dd_:
        L += ["", "=" * 88, "WHAT YOU CHANGED IN THE PROMPT, ROUND BY ROUND", "=" * 88, "", dd_]
    bp = (live or {}).get("best_prompt")
    if bp:
        L += ["", "=" * 88,
              f"THE BEST-SCORING PROMPT SO FAR, in full, for copying. Settings: {(live or {}).get('best_cfg','')}",
              "=" * 88, "", bp, "", "=" * 88]
    return "\n".join(L)


def _allruns_block():
    """Every scored run, not just this loop's own rounds.

    The trend table below covers only rounds the mutator itself ran. Configurations tested outside
    the loop were invisible to it, so it has formed beliefs from a partial view -- most importantly
    it ruled out cropping on a single 30s measurement while the 10s measurement, which points the
    other way, sat in a file it never read.
    """
    try:
        import results
        R = [r for r in results.load() if r.get("headline_f1") is not None]
    except Exception:
        return "No cross-run results available."
    if not R:
        return "No cross-run results available."
    L = ["Every configuration ever scored, by anyone, on the same 550 ground-truth events.",
         "Runs named arm* and seed* were run outside this loop -- they are evidence you have not",
         "seen before. Compare configurations that differ in ONE setting to isolate its effect.", "",
         f"{'run':<10}{'clip':>9}{'crop':>6}{'res':>6}{'fps':>5}{'F1':>8}{'TP':>6}"
         f"{'n_pred':>8}{'invented':>10}"]
    for r in sorted(R, key=lambda r: -r["headline_f1"]):
        clip = f"{r.get('chunk_len') or 0:g}/{r.get('overlap') or 0:g}s"
        L.append(f"{r['run']:<10}{clip:>9}{('yes' if r.get('crop') else '-'):>6}"
                 f"{('HIGH' if r.get('media_resolution') else 'def'):>6}{r.get('fps') or 0:>5}"
                 f"{r['headline_f1']:>8.3f}{r.get('tp') or 0:>6}{r.get('n_pred') or 0:>8}"
                 f"{r.get('invented') or 0:>10}")
    L += ["", "Repeat-run noise on an identical config is +/-0.028 F1 and +/-8 TP. A difference",
          "smaller than that is not a result. A belief formed at one clip length is not evidence",
          "at another -- check whether the run that convinced you shares the geometry you are in."]
    return "\n".join(L)


def _levers_block():
    """Every knob, and what has actually been tried on it.

    Eight consecutive rounds changed nothing but the prompt while the run table sat there showing
    clip length 30s/15s/10s/6s giving F1 .359/.391/.434/.455 -- a monotonic trend, stopped at the
    shortest value ever tested rather than at a measured peak. An aggregate of runs does not make
    an untouched lever visible; a list of the values tried per lever does.
    """
    try:
        import results
        R = [r for r in results.load() if r.get("headline_f1") is not None]
    except Exception:
        R = []
    if not R:
        return "Nothing scored yet."
    import pipeline as P
    L = ["For each setting: the values that have been scored, best F1 at each. A setting with one",
         "value has never been tested. A trend across values is stronger evidence than any single",
         "run, because it cannot be a fluke of one measurement.", ""]
    for k in ("chunk_len", "overlap", "fps", "crop", "media_resolution", "thinking", "model"):
        vals = {}
        for r in R:
            v = r.get(k)
            v = P.DEFAULTS[k] if v is None and k not in ("crop", "media_resolution") else v
            key = str(v)
            vals[key] = max(vals.get(key, 0.0), r["headline_f1"])
        cells = "  ".join(f"{v}={f:.3f}" for v, f in sorted(vals.items(), key=lambda x: -x[1]))
        flag = "   <- ONE VALUE ONLY, never tested" if len(vals) == 1 else ""
        L.append(f"  {k:<18}{cells}{flag}")
    return "\n".join(L)


def _config_block(cfg):
    """The pipeline settings, not just the prompt -- these are all mutable now."""
    import pipeline as P
    c = P.normalise(cfg or {})
    L = ["The pipeline settings that produced the scores below:", ""]
    for k in ("chunk_len", "overlap", "fps", "width", "crop", "media_resolution",
              "model", "thinking"):
        L.append(f"  {k:<18}{c[k]}")
    L += ["", f"  {'clips per run':<18}{len(P.starts(c))}",
          f"  {'cost to evaluate':<18}${P.estimate_cost(c):.2f}", ""]
    # Without this the mutator reasons about a pipeline it cannot see and invents missing stages --
    # it has already proposed prompt-level fixes for deduplication that the harness already does.
    L += ["What the harness does to the model's raw output BEFORE it is scored, so you do not",
          "propose a fix for something already handled:", "",
          "  1. Every clip's events are concatenated across all clips.",
          f"  2. DEDUPLICATION: two events of the SAME TYPE within {dd.WINDOW}s of each other are",
          "     merged into one. This already removes the double-reporting caused by clip overlap;",
          "     it is not a gap you need to close from the prompt. The survivor is whichever was",
          "     seen further from its own clip's edge.",
          "  3. Scoring is greedy one-to-one on nearest timestamp, so a prediction can never be",
          "     matched to a ground-truth event that another prediction already claimed.", "",
          "You can change the dedupe window only by changing chunk geometry; it is not a knob.", ""]
    if c.get("mode") == "two_stage":
        L += ["This pipeline runs in TWO STAGES per clip.", "",
              "  STAGE 1 sees the video and replies in free text. No schema, no taxonomy.",
              "  STAGE 2 sees ONLY that text -- never the video -- and emits the events.",
              "",
              "Splitting them is not cosmetic: the detector locates about 76% of real events and",
              "names only 53% of those, so perception is not the bottleneck. Stage 2 sits on the",
              "failing half and has the whole sequence in front of it, which a single call",
              "watching six seconds cannot.", "",
              "You may change either prompt, but only ONE of them per round.", "",
              "STAGE 1 -- the observer (gets the video):", "", c["prompt"], "",
              "STAGE 2 -- the reasoner ({obs} is where stage 1's text is inserted):", "",
              c.get("prompt2") or "(none)"]
    else:
        L += ["The prompt sent with each clip:", "", c["prompt"]]
    return "\n".join(L)


def build(pred=None, gt=None, notebook=None, live=None, history=None, config=None):
    if pred is None:
        gt, pred, _ = current_results()
    parts = [
        ("1. THE CONFIG CURRENTLY IN PLAY", _config_block(config)),
        ("2. HOW IT SCORED", _scores_block(pred, gt)),
        ("2b. THE MATCH RESULT YOUR EVENTS IMPLY", _scoreline_block(pred, gt)),
        ("3. CONFUSION MATRIX", _confusion_block(pred, gt)),
        ("3b. WHERE THE PHANTOMS ARE", _phantom_block(pred, gt)),
        ("4. EVERY EVENT, BOTH SIDES", _events_block(pred, gt)),
        ("5. HOW GROUND TRUTH WAS DERIVED", SCHEMA_BLOCK),
        ("6. WHAT YOUR CHANGES HAVE DONE SO FAR", _trend_block(history or [])),
        ("6b. EVERY CONFIGURATION EVER SCORED", _allruns_block()),
        ("6c. WHICH SETTINGS YOU HAVE ACTUALLY MOVED", _levers_block()),
        ("7. YOUR NOTEBOOK", _notebook_block(notebook, live)),
    ]
    return "\n\n".join(f"{'=' * 92}\n{title}\n{'=' * 92}\n\n{body}" for title, body in parts)


if __name__ == "__main__":
    print(build())
