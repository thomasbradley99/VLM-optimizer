"""Export VLM runs into the review viewer as a second event stream.

The viewer already carries the scout's sheet; this adds what the model said at the same moments,
so a phantom detection can be watched rather than counted. Pairing is the two passes the headline
score uses -- action-and-time first, then time alone for the remainder -- so the verdicts shown
here add up to the F1 in results.md.

Guarded: constructing a client is fine, calling it is not. Every run exported must already be in
the cache, or the export aborts rather than quietly spending money.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "mutator"))
import evaluate as E, ingest, pipeline as P
from google import genai

class _Dead:
    async def generate_content(self, **k):
        raise RuntimeError("live API call attempted during export")
class _DeadClient:
    def __init__(self, *a, **k): self.aio = type("A", (), {"models": _Dead()})()
genai.Client = _DeadClient

TOL = 1.0
ORIGIN = 995.0   # t=0 of match.mp4 is 995s of the source, where the scored span begins
VERDICT = {"ok": "ok", "team": "team", "action": "action", "miss": "miss", "ghost": "ghost"}


def pair(pred, gt):
    """Action-and-time first, then time alone. Same two passes as the headline metric."""
    m, used = {}, set()
    for i, j in E.match(pred, gt, TOL, "+type"):
        m[j] = (i, "type"); used.add(i)
    rp = [i for i in range(len(pred)) if i not in used]
    rg = [j for j in range(len(gt)) if j not in m]
    for a, b in E.match([pred[i] for i in rp], [gt[j] for j in rg], TOL, "timing"):
        m[rg[b]] = (rp[a], "time"); used.add(rp[a])
    return m, used


def export(cfg_path, name, gt, w0, dur):
    cfg = json.load(open(cfg_path))
    cfg.pop("lever", None)
    c = P.normalise(cfg)
    gk = P.geometry_key(c)
    ids = [f"c{i:03d}" for i in range(len(P.starts(c)))]
    missing = [i for i in ids if not os.path.exists(P._cache_path(c, i, gk))]
    if missing:
        return None, f"{len(missing)} of {len(ids)} clips not cached"
    pred, st = P.run(cfg)
    assert st["cost"] == 0.0, "export must not spend"

    gw = [e for e in gt if w0 <= e["t"] < w0 + dur]
    pw = [e for e in pred if w0 <= e["t"] < w0 + dur]
    m, used = pair(pw, gw)
    rows = []
    for j, g in enumerate(gw):
        if j in m:
            i, kind = m[j]
            p = pw[i]
            v = ("action" if kind == "time"
                 else ("ok" if (p.get("team") or "") == g["team"] else "team"))
            rows.append({"t": round(g["t"] - w0, 2), "v": v,
                         "gt": {"type": g["type"], "team": g["team"], "num": g.get("number")},
                         "ai": {"type": p.get("type"), "team": p.get("team"),
                                "num": p.get("number"), "dt": round(p["t"] - g["t"], 2)}})
        else:
            rows.append({"t": round(g["t"] - w0, 2), "v": "miss",
                         "gt": {"type": g["type"], "team": g["team"], "num": g.get("number")},
                         "ai": None})
    for i, p in enumerate(pw):
        if i not in used:
            rows.append({"t": round(p["t"] - w0, 2), "v": "ghost", "gt": None,
                         "ai": {"type": p.get("type"), "team": p.get("team"),
                                "num": p.get("number"), "dt": None}})
    rows.sort(key=lambda r: r["t"])
    n = {k: sum(1 for r in rows if r["v"] == k) for k in ("ok", "team", "action", "miss", "ghost")}

    M, U = pair(pred, gt)
    tp = sum(1 for j in M if M[j][1] == "type")
    allrows = []
    for j, g in enumerate(gt):
        if j in M:
            i, kind = M[j]; q = pred[i]
            v = ("action" if kind == "time"
                 else ("ok" if (q.get("team") or "") == g["team"] else "team"))
            allrows.append({"t": round(g["t"] - ORIGIN, 2), "v": v,
                            "gt": {"type": g["type"], "team": g["team"], "num": g.get("number")},
                            "ai": {"type": q.get("type"), "team": q.get("team"),
                                   "num": q.get("number"), "dt": round(q["t"] - g["t"], 2)}})
        else:
            allrows.append({"t": round(g["t"] - ORIGIN, 2), "v": "miss",
                            "gt": {"type": g["type"], "team": g["team"], "num": g.get("number")},
                            "ai": None})
    for i, q in enumerate(pred):
        if i not in U:
            allrows.append({"t": round(q["t"] - ORIGIN, 2), "v": "ghost", "gt": None,
                            "ai": {"type": q.get("type"), "team": q.get("team"),
                                   "num": q.get("number"), "dt": None}})
    allrows.sort(key=lambda r: r["t"])
    nall = {k: sum(1 for r in allrows if r["v"] == k)
            for k in ("ok", "team", "action", "miss", "ghost")}
    grid = E.grid(pred, gt)
    ladder = [{"level": lv, "f1": round(grid[lv]["1.0"][2], 3),
               "matched": len(E.match(pred, gt, TOL, lv))} for lv in E.LEVELS]
    pt = E.per_type(pred, gt, TOL)
    import collections
    gc = collections.Counter(g["type"] for g in gt)
    types = [{"type": t, "gt": gc[t],
              "ai": sum(1 for q in pred if q.get("type") == t),
              "p": round(pt[t][0], 3), "r": round(pt[t][1], 3), "f1": round(pt[t][2], 3)}
             for t in E.TYPES]
    return {"name": name, "rows": rows, "counts": n, "all": allrows, "allCounts": nall,
            "window": {"gt": len(gw), "ai": len(pw)},
            "ladder": ladder, "types": types,
            "match": {"f1": round(2 * tp / (len(pred) + len(gt)), 3), "tp": tp,
                      "n_pred": len(pred), "gt": len(gt)},
            "cfg": f"{c['chunk_len']:g}s/{c['overlap']:g}s · {c['fps']}fps · "
                   f"{'cropped' if c['crop'] else 'full frame'} · {c['model']}",
            # structured too, so the page can show what each lineage settled on and whether
            # two lineages agreed -- which is the whole convergence question
            # the prompt is the artefact -- a word count is not a result you can read
            "prompt": c["prompt"],
            "knobs": {"clip": c["chunk_len"], "overlap": c["overlap"], "fps": c["fps"],
                      "crop": bool(c["crop"]), "res": "HIGH" if c["media_resolution"] else "def",
                      "think": c["thinking"], "words": len(c["prompt"].split())}}, None


# Rules a lineage could arrive at on its own. Convergence in prose never happens -- the final
# prompts share 3-13% of their text -- so the question has to be asked at the level of the rule.
# Probes that any prompt satisfies trivially are worthless: "team by screen side" was dropped
# because the response schema forces left/right, so every prompt matched it.
PROBES = {
 "set = assist only":        r"assist|leads? to a kill|point-winning kill|SKIP ALL OTHER SETS",
 "attack = over the net":    r"over the net|OVER the net",
 "one label per contact":    r"EXACTLY ONE|ONE PER CONTACT|mutually exclusive|single best fit",
 "ignore dead time":         r"dead[- ]time|DEAD TIME|between rallies|casual",
 "don't assume a sequence":  r"mid-rally|do not assume|NEVER assume|sequence",
 "skip regular passes":      r"skip|DO NOT REPORT EVERY|not report every",
 "define by what is visible": r"visually|you can see|visible|trajectory|physically",
}
LEAKED = {"ignore background courts"}   # the crop description names them; not an inference

CAND = {"A main":    os.path.join(HERE, "mutator", "notebook", "candidates"),
        "B blind":   os.path.join(HERE, "mutator", "lineages", "basic", "candidates"),
        "C terse":   os.path.join(HERE, "mutator", "lineages", "terse6s", "candidates"),
        "D verbose": os.path.join(HERE, "mutator", "lineages", "verbose15", "candidates")}


def accumulation():
    """When each rule first appears in each lineage's prompt, round by round.

    The end-state table says four searches agreed; this says they agreed having started with
    none of it and picked the rules up in different orders at different rounds. That is the
    difference between a coincidence and a convergence.
    """
    import glob, re
    out = []
    for tag, d in (("B blind", CAND["B blind"]), ("C terse", CAND["C terse"]),
                   ("D verbose", CAND["D verbose"])):
        seed = os.path.join(d, "config_seed.json")
        if not os.path.exists(seed):
            continue
        fs = [seed] + sorted(glob.glob(os.path.join(d, "config_[0-9]*.json")))
        rounds = []
        for i, f in enumerate(fs):
            pr = json.load(open(f))["prompt"]
            rounds.append({"label": "seed" if i == 0 else f"{i-1:03d}",
                           "words": len(pr.split()),
                           "hit": {k: bool(re.search(rx, pr, re.I))
                                   for k, rx in PROBES.items()}})
        out.append({"lineage": tag, "rounds": rounds,
                    "seedWords": rounds[0]["words"],
                    "seedHas": sum(rounds[0]["hit"].values())})
    return {"rules": list(PROBES), "lineages": out}


def convergence(finals):
    """Which rules each lineage's final prompt ended up carrying, and how many agreed."""
    import re, difflib
    keys = list(finals)
    rows = []
    for name, rx in PROBES.items():
        hit = {k: bool(re.search(rx, finals[k], re.I)) for k in keys}
        rows.append({"rule": name, "hit": hit, "n": sum(hit.values())})
    rows.sort(key=lambda r: -r["n"])
    sim = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            sim.append({"a": keys[i], "b": keys[j],
                        "r": round(difflib.SequenceMatcher(
                            None, finals[keys[i]], finals[keys[j]]).ratio(), 3)})
    return {"lineages": keys, "rules": rows, "similarity": sim,
            "words": {k: len(finals[k].split()) for k in keys}}


def manifest():
    """Every cached run, in the order it was actually run, tagged by lineage.

    Order is the point: the page is for watching what the model said at the same moment as the
    optimiser changed things round by round. A set of runs with no sequence cannot show that.
    """
    import glob, re
    out = []
    A, B = CAND["A main"], CAND["B blind"]
    C, Dd = CAND["C terse"], CAND["D verbose"]
    seed = os.path.join(A, "config_seed.json")
    if os.path.exists(seed):
        out.append(("main", -1, seed, "seed — the starting config"))
    for f in sorted(glob.glob(os.path.join(A, "config_[0-9]*.json"))):
        n = int(re.search(r"config_(\d+)", f).group(1))
        out.append(("main", n, f, f"iter {n:03d}"))
    for tag, dirp, pre in (("blind", B, "blind"), ("terse", C, "terse"), ("verbose", Dd, "verbose")):
        for f in sorted(glob.glob(os.path.join(dirp, "config_[0-9]*.json"))):
            n = int(re.search(r"config_(\d+)", f).group(1))
            out.append((tag, n, f, f"{pre} iter {n:03d}"))
    for extra, lab in (("config_seed_armH.json", "armH — 6s clips"),
                       ("config_crop6s.json", "crop6s — 6s + crop")):
        f = os.path.join(A, extra)
        if os.path.exists(f):
            out.append(("main", 99, f, lab))
    return out


if __name__ == "__main__":
    view = os.path.join(ROOT, "viewer")
    w = json.load(open(os.path.join(view, "data.json")))["window"]
    w0, dur = w["start_s"], w["duration_s"]
    gt = ingest.load_events()
    runs = []
    for lineage, n, path, label in manifest():
        r, err = export(path, label, gt, w0, dur)
        if err:
            print(f"  {label:<26} skip ({err})"); continue
        r["lineage"] = lineage; r["n"] = n
        runs.append(r)
        print(f"  {label:<26} F1 {r['match']['f1']:.3f}  "
              f"tp {r['match']['tp']:>3}  n_pred {r['match']['n_pred']:>4}")
    rig = {"selftest": E.selftest(gt) or "1.000 in all 12 cells",
           "offset": E.sweep_offset(json.load(open(os.path.join(HERE, "predictions_best.json"))),
                                    gt, lo=-5.0, hi=5.0, step=0.1)[0],
           "swap": [round(x, 3) for x in E.team_swap_gain(
               json.load(open(os.path.join(HERE, "predictions_best.json"))), gt)],
           "n_gt": len(gt), "span": [round(gt[0]["t"], 1), round(gt[-1]["t"], 1)]}
    out = os.path.join(view, "vlm.json")
    import difflib as _dl
    prevp = {}
    for r in runs:
        pv = prevp.get(r["lineage"])
        if pv is not None and pv.strip() != r["prompt"].strip():
            d = [l for l in _dl.unified_diff(pv.split("\n"), r["prompt"].split("\n"),
                                             lineterm="", n=0)
                 if l[:1] in "+-" and not l.startswith(("+++", "---"))]
            r["diff"] = d[:40]
        else:
            r["diff"] = []
        prevp[r["lineage"]] = r["prompt"]

    import glob as _g
    finals = {}
    for tag, dirp in CAND.items():
        fs = sorted(_g.glob(os.path.join(dirp, "config_[0-9]*.json")))
        if fs:
            finals[tag] = json.load(open(fs[-1]))["prompt"]
    conv = convergence(finals) if len(finals) > 1 else None

    LIN = {"main":  {"label": "Lineage A — main",
                     "desc": "started from the hand-tuned prompt at 30s clips; elitism for "
                             "rounds 0-14, then a free walk"},
           "blind": {"label": "Lineage B — blind",
                     "desc": "104-word plain prompt, 30s clips, full frame"},
           "terse": {"label": "Lineage C — terse",
                     "desc": "88-word plain prompt, 6s clips, full frame"},
           "verbose": {"label": "Lineage D — verbose",
                       "desc": "300-word taxonomy-first prompt, 15s clips, cropped"}}
    for k, v in LIN.items():
        rs = [r for r in runs if r["lineage"] == k]
        if not rs: continue
        v["n"] = len(rs)
        v["start"] = rs[0]["match"]["f1"]
        v["end"] = rs[-1]["match"]["f1"]
        b = max(rs, key=lambda r: r["match"]["f1"])
        v["best"] = b["match"]["f1"]; v["bestName"] = b["name"]
        v["final"] = rs[-1]["knobs"]
    json.dump({"window": {"start_s": w0, "duration_s": dur}, "origin": ORIGIN,
               "match_video": "match.mp4", "rigour": rig,
               "lineages": LIN, "convergence": conv,
               "accumulation": accumulation(), "runs": runs}, open(out, "w"))
    print(f"\n{len(runs)} runs -> {out}  ({os.path.getsize(out)/1e6:.1f} MB)")
