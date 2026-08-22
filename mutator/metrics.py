"""The closed vocabulary of things the mutator may predict, and the scoring of those predictions.

Predictions are auto-scored so the mutator never reports its own outcome. It writes a falsifiable
claim, the harness computes what actually happened, and only then does the mutator get to comment.
Scoring is on two axes: direction (did it call the sign) and magnitude (did it land near the number
it named). Direction is the one that matters -- a right mechanism with a wrong size is still a
right mechanism.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import evaluate as E   # noqa: E402
import report          # noqa: E402

TOL = 1.0
RATE_BAND = 0.02        # a rate moving less than this counts as flat
COUNT_BAND_FRAC = 0.05  # a count moving less than 5% (min 2) counts as flat


def vocabulary():
    v = ["headline_f1", "tp", "n_pred", "spotted", "missed", "invented", "team_acc",
         "point_f1", "point_tp", "point_pred_count", "score_white", "score_blue",
         "score_margin_err", "winner_correct"]
    for t in E.TYPES:
        v += [f"{t}_pred_count", f"{t}_precision", f"{t}_recall", f"{t}_f1"]
    return v


def scoreline(pred, gt):
    """The match result as the events imply it, and how far off it is.

    Every point-flagged event is a point to the team that made it. This is what the pipeline is
    actually for -- detecting contacts is the means, not the end -- so it belongs in the objective
    rather than being computed once at the end and admired.

    Two numbers, because they fail differently. `point_f1` is a detection score on point events
    (right moment, right team, flagged as a point) and cannot be gamed by predicting fewer.
    `score_margin_err` is the thing a person would check: how wrong is the final margin.
    """
    m = {}
    for tag, evs in (("", pred), ("_gt", gt)):
        for side in ("white", "blue"):
            m[f"{side}{tag}"] = sum(1 for e in evs if e.get("point") and e.get("team") == side)
    m["score_white"], m["score_blue"] = m["white"], m["blue"]
    m["point_pred_count"] = sum(1 for e in pred if e.get("point"))

    # a point event is only "found" if the moment, the team and the point flag are all right
    pp = [dict(e, type="point") for e in pred if e.get("point")]
    gp = [dict(e, type="point") for e in gt if e.get("point")]
    m["point_tp"] = len(E.match(pp, gp, TOL, "+team"))
    m["point_f1"] = E.prf(m["point_tp"], len(pp), len(gp))[2]

    pred_margin = m["white"] - m["blue"]
    gt_margin = m["white_gt"] - m["blue_gt"]
    m["score_margin_err"] = abs(pred_margin - gt_margin)
    m["winner_correct"] = 1.0 if (pred_margin > 0) == (gt_margin > 0) else 0.0
    for k in ("white", "blue", "white_gt", "blue_gt"):
        m.pop(k)
    return m


def compute(pred, gt):
    """Every metric the mutator is allowed to name, from one (pred, gt) pair."""
    rows = report.build(pred, gt, TOL)
    m = {"headline_f1": E.f1_at(pred, gt, TOL, "+type"), "n_pred": len(pred),
         "tp": len(E.match(pred, gt, TOL, "+type"))}
    verdicts = [v for *_, v in rows]
    m["missed"] = verdicts.count(report.MISSED)
    m["invented"] = verdicts.count(report.INVENTED)
    m["spotted"] = len(gt) - m["missed"]
    right_action = verdicts.count(report.CORRECT) + verdicts.count(report.TEAM)
    m["team_acc"] = verdicts.count(report.CORRECT) / right_action if right_action else 0.0
    # per-type counts come from evaluate.per_type, which matches at +type exactly as the headline
    # does. Deriving them from report.build instead would match on timing alone -- a serve whose
    # nearest neighbour is a receive would score wrong even with a matching serve slightly further
    # off -- and the per-type hits would then sum to less than tp.
    m.update(scoreline(pred, gt))
    pt = E.per_type(pred, gt, TOL)
    for ty in E.TYPES:
        p_, r_, f_, _ = pt[ty]
        m[f"{ty}_pred_count"] = sum(p.get("type") == ty for p in pred)
        m[f"{ty}_precision"], m[f"{ty}_recall"], m[f"{ty}_f1"] = p_, r_, f_
    return m


def _band(metric, before):
    return (max(2.0, abs(before) * COUNT_BAND_FRAC)
            if metric.endswith(("_pred_count", "n_pred", "spotted", "missed", "invented", "tp"))
            else RATE_BAND)


def _direction(metric, before, after):
    d = after - before
    b = _band(metric, before)
    return "flat" if abs(d) <= b else ("up" if d > 0 else "down")


def score(predictions, before, after):
    """Grade each prediction. Returns rows plus a summary the notebook can quote."""
    rows = []
    for p in predictions:
        metric = p.get("metric")
        if metric not in before or metric not in after:
            rows.append({**p, "valid": False, "note": f"unknown metric {metric!r}"})
            continue
        b, a = before[metric], after[metric]
        actual_dir = _direction(metric, b, a)
        dir_ok = actual_dir == p.get("direction")
        target = p.get("to_approx")
        # landed within half the move it predicted (floored so tiny predicted moves stay gradeable)
        tol = max(abs(target - b) * 0.5, _band(metric, b)) if target is not None else None
        mag_ok = target is not None and abs(a - target) <= tol
        rows.append({**p, "valid": True, "actual_before": b, "actual_after": a,
                     "actual_direction": actual_dir, "direction_ok": dir_ok, "magnitude_ok": mag_ok})
    good = [r for r in rows if r.get("valid")]
    return rows, {"n": len(good),
                  "direction_hits": sum(r["direction_ok"] for r in good),
                  "magnitude_hits": sum(r["magnitude_ok"] for r in good)}


def render(rows, summary):
    L = [f"{'metric':<22}{'predicted':>22}{'actual':>20}{'dir':>6}{'mag':>6}"]
    for r in rows:
        if not r.get("valid"):
            L.append(f"{str(r.get('metric')):<22}{r['note']:>54}")
            continue
        pred_s = f"{r['direction']} to ~{r['to_approx']}"
        act_s = f"{r['actual_direction']} {r['actual_before']:.3g} -> {r['actual_after']:.3g}"
        L.append(f"{r['metric']:<22}{pred_s:>22}{act_s:>20}"
                 f"{('OK' if r['direction_ok'] else 'X'):>6}{('OK' if r['magnitude_ok'] else 'X'):>6}")
    L.append(f"\ndirection {summary['direction_hits']}/{summary['n']}   "
             f"magnitude {summary['magnitude_hits']}/{summary['n']}")
    return "\n".join(L)


if __name__ == "__main__":
    # Self-test on the real current run plus a known perturbation of it. (The earlier colour-prompt
    # run cannot be replayed: its prompt text was replaced in detect.py, so its cache key is
    # unreachable -- which is exactly why mutator/notebook/candidates/ keeps every prompt from now on.)
    import asyncio
    import json
    import dedupe as dd
    import detect
    import ingest

    gt = ingest.load_events()
    index = json.load(open(os.path.join(os.path.dirname(HERE), "chunks", "index.json")))
    raw, st = asyncio.run(detect.run(index, 32))
    assert st["hits"] == len(index) and st["cost"] == 0.0, "self-test must not spend money"
    pred = dd.dedupe(raw)
    before = compute(pred, gt)
    print(f"real run: headline_f1 {before['headline_f1']:.3f}, "
          f"set_pred_count {before['set_pred_count']}, n_pred {before['n_pred']}")

    # Known perturbation: delete every predicted `set`. set_pred_count must go to 0, set recall to
    # 0, n_pred must drop by exactly that many, and serve must not move at all.
    after = compute([p for p in pred if p.get("type") != "set"], gt)
    assert after["set_pred_count"] == 0
    assert after["n_pred"] == before["n_pred"] - before["set_pred_count"]
    assert after["serve_f1"] == before["serve_f1"], "removing sets must not touch serve"
    print(f"perturbed: set_pred_count {before['set_pred_count']} -> 0, "
          f"n_pred {before['n_pred']} -> {after['n_pred']}, serve_f1 unchanged\n")

    rows, summ = score([
        {"metric": "set_pred_count", "direction": "down", "from": before["set_pred_count"],
         "to_approx": 10},
        {"metric": "serve_f1", "direction": "flat", "from": before["serve_f1"],
         "to_approx": before["serve_f1"]},
        {"metric": "set_recall", "direction": "up", "from": before["set_recall"], "to_approx": 0.5},
        {"metric": "nonsense_metric", "direction": "up", "from": 0, "to_approx": 1},
    ], before, after)
    print(render(rows, summ))
    assert rows[0]["direction_ok"] and rows[0]["magnitude_ok"], "a well-called drop must score"
    assert rows[1]["direction_ok"] and rows[1]["magnitude_ok"], "a correct flat call must score"
    assert not rows[2]["direction_ok"], "set_recall fell; predicting a rise must fail"
    assert not rows[3]["valid"], "unknown metrics must be rejected, not silently scored"
    assert summ == {"n": 3, "direction_hits": 2, "magnitude_hits": 2}, summ
    print("\nmetrics self-test PASS")
