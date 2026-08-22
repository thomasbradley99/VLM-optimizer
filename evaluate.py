"""Greedy one-to-one matching of predictions to ground truth at four strictness levels. Pairs are
considered in ascending |dt|, so an event claims its closest still-free partner; that makes the
diagonal exact, which is what lets ground truth score 1.000 against itself."""
import bisect
import json

TOLERANCES = [0.5, 1.0, 2.0]
LEVELS = ["timing", "+type", "+team", "+number"]
TYPES = ["serve", "receive", "dig", "set", "attack", "kill", "block"]


def _ok(p, g, level):
    if level == "timing":
        return True
    if p.get("type") != g["type"]:
        return False
    if level == "+type":
        return True
    if (p.get("team") or "") != g["team"]:
        return False
    if level == "+team":
        return True
    return str(p.get("number") or "") == str(g["number"])


def match(pred, gt, tol, level):
    """(pred_idx, gt_idx) pairs, one-to-one, nearest-first. Candidates come from a bisect window
    rather than the full cross product -- only a couple of gt events fall inside `tol` of any
    prediction, and the sweep calls this 101 times."""
    order = sorted(range(len(gt)), key=lambda j: gt[j]["t"])
    times = [gt[j]["t"] for j in order]
    cand = []
    for i, p in enumerate(pred):
        lo = bisect.bisect_left(times, p["t"] - tol)
        hi = bisect.bisect_right(times, p["t"] + tol)
        for k in range(lo, hi):
            j = order[k]
            if _ok(p, gt[j], level):
                cand.append((abs(p["t"] - gt[j]["t"]), i, j))
    cand.sort()
    used_p, used_g, pairs = set(), set(), []
    for _, i, j in cand:
        if i not in used_p and j not in used_g:
            used_p.add(i); used_g.add(j); pairs.append((i, j))
    return pairs


def prf(n_match, n_pred, n_gt):
    p = n_match / n_pred if n_pred else 0.0
    r = n_match / n_gt if n_gt else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def f1_at(pred, gt, tol, level):
    return prf(len(match(pred, gt, tol, level)), len(pred), len(gt))[2]


def grid(pred, gt):
    return {lv: {str(t): prf(len(match(pred, gt, t, lv)), len(pred), len(gt))
                 for t in TOLERANCES} for lv in LEVELS}


def per_type(pred, gt, tol=1.0):
    pairs = match(pred, gt, tol, "+type")
    matched = {g for _, g in pairs}
    out = {}
    for ty in TYPES:
        n_g = sum(g["type"] == ty for g in gt)
        n_p = sum(p.get("type") == ty for p in pred)
        n_m = sum(gt[j]["type"] == ty for _, j in pairs)
        out[ty] = prf(n_m, n_p, n_g) + (n_g,)
    # flag agreement is only meaningful where identity is already established
    strict = match(pred, gt, tol, "+team")
    for flag in ("error", "point"):
        agree = sum(bool(pred[i].get(flag)) == gt[j][flag] for i, j in strict)
        out[flag] = (agree / len(strict) if strict else 0.0, len(strict))
    return out


def team_swap_gain(pred, gt, tol=1.0):
    """F1 at +team as-is, and with blue/white swapped. A large gain means the model located the
    right players and mislabelled the colour -- a different problem from not seeing the event."""
    flip = {"blue": "white", "white": "blue"}
    swapped = [{**p, "team": flip.get(p.get("team"), p.get("team"))} for p in pred]
    return f1_at(pred, gt, tol, "+team"), f1_at(swapped, gt, tol, "+team")


def sweep_offset(pred, gt, lo=-5.0, hi=5.0, step=0.1, tol=1.0, level="+type"):
    """Best constant shift applied to predictions -- diagnostic only, reported alongside the
    zero-offset number and never in place of it. F1 saturates across a plateau of deltas (anything
    inside `tol` matches equally), so ties break on mean residual: that picks the plateau's centre,
    which is the actual offset, not whichever edge the scan reached first."""
    def score(d):
        sh = [{**p, "t": p["t"] + d} for p in pred]
        pairs = match(sh, gt, tol, level)
        f = prf(len(pairs), len(pred), len(gt))[2]
        resid = (sum(abs(sh[i]["t"] - gt[j]["t"]) for i, j in pairs) / len(pairs)
                 if pairs else float("inf"))
        return f, -resid

    best_d, best = 0.0, score(0.0)
    for k in range(int(round((hi - lo) / step)) + 1):
        d = round(lo + k * step, 2)
        sc = score(d)
        if sc[0] > best[0] + 1e-9 or (abs(sc[0] - best[0]) <= 1e-9 and sc[1] > best[1] + 1e-9):
            best_d, best = d, sc
    return best_d, best[0]


def selftest(gt):
    """Ground truth against itself must be exactly 1.0 in every cell."""
    bad = []
    g = grid(gt, gt)
    for lv in LEVELS:
        for t in TOLERANCES:
            if abs(g[lv][str(t)][2] - 1.0) > 1e-9:
                bad.append(f"{lv}@{t}={g[lv][str(t)][2]:.3f}")
    for ty, row in per_type(gt, gt).items():
        if abs(row[0] - 1.0) > 1e-9 or (len(row) == 4 and abs(row[2] - 1.0) > 1e-9):
            bad.append(f"per-type {ty}={row}")
    return bad


def render(g, pt, n_pred, n_gt, types=True):
    L = [f"F1{'':<14}" + "".join(f"{'+/-' + str(t) + 's':>10}" for t in TOLERANCES)]
    for lv in LEVELS:
        L.append(f"{lv:<16}" + "".join(f"{g[lv][str(t)][2]:>10.3f}" for t in TOLERANCES))
    if not types:                    # report.py prints a strictly richer per-type table
        return "\n".join(L + [f"\npredicted {n_pred} events vs {n_gt} ground truth"])
    L += ["", f"per type @1.0s, +type{'P':>10}{'R':>8}{'F1':>8}{'n':>6}"]
    for ty in TYPES:
        p, r, f, n = pt[ty]
        L.append(f"  {ty:<19}{p:>10.3f}{r:>8.3f}{f:>8.3f}{n:>6}")
    for flag in ("error", "point"):
        a, n = pt[flag]
        L.append(f"  {flag + ' flag agree':<19}{a:>10.3f}{'':>8}{'':>8}{n:>6}")
    L.append(f"\npredicted {n_pred} events vs {n_gt} ground truth")
    return "\n".join(L)


if __name__ == "__main__":
    import ingest
    gt = ingest.load_events()
    bad = selftest(gt)
    print(render(grid(gt, gt), per_type(gt, gt), len(gt), len(gt)))
    print("\nsanity: gt-vs-gt = " + ("1.000 across all cells  [PASS]" if not bad
                                     else "FAILED: " + "; ".join(bad)))
    raise SystemExit(1 if bad else 0)
