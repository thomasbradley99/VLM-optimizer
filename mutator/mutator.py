"""The diagnostic loop: conjecture, commit, run, grade, verdict, repeat.

    python3 mutator/mutator.py --dry-run     # think only: print, write nothing, run nothing
    python3 mutator/mutator.py               # one full round   (~$2.20)
    python3 mutator/mutator.py --rounds 5    # five full rounds (~$11)

The ordering constraint that matters: the conjecture, the change and the prediction are written to
disk and fsynced BEFORE the pipeline is invoked. A mutator that sees results before committing to a
prediction will rationalise, and the whole exercise becomes theatre.

The OUTCOME section is filled by the harness from computed numbers. The mutator never reports its
own result -- it only comments on facts it cannot edit.
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from google import genai        # noqa: E402
from google.genai import types  # noqa: E402

import context                  # noqa: E402
import dedupe as dd             # noqa: E402
import detect                   # noqa: E402
import ingest                   # noqa: E402
import metrics                  # noqa: E402
import notebook                 # noqa: E402
import pipeline as P            # noqa: E402
import labreport              # noqa: E402
import results                 # noqa: E402

MODEL = "gemini-3.1-pro-preview"
THINKING = "high"
PRICES = {"gemini-3.1-pro-preview": (2.00, 12.00)}  # $/M in, out

SYSTEM = open(os.path.join(HERE, "prompts", "system.txt")).read()
VERDICT_SYSTEM = open(os.path.join(HERE, "prompts", "verdict.txt")).read()
BEST = os.path.join(notebook.NB, "best.json")
LIVE = os.path.join(notebook.NB, "live.json")        # where the walk currently stands
HISTORY = os.path.join(notebook.NB, "history.json")
CONFIGS = notebook.CANDIDATES
MAX_ROUND_COST = 9.00   # refuse a candidate that would cost more than this to evaluate.
                        # 9 not 8 so 3-second clips ($8.36) stay reachable. Clip length is the
                        # only lever with a consistent trend across four measurements --
                        # 30s/15s/10s/6s gave F1 .359/.391/.434/.455 and TP 195/239/238/315 --
                        # and 6s is where the sweep stopped, not a measured peak. The cap must
                        # not be the reason the one working direction goes untested.
NOISE_FLOOR = 0.028     # measured on five replicate pairs -- the same config scored twice moved
                        # F1 by +0.014, +0.002, +0.018, +0.028, +0.013. The floor is the worst of
                        # those, not the mean: elitism must reject anything a re-run could produce.
BASE_PROMPT = os.path.join(CONFIGS, "prompt_base.txt")


# ---------------------------------------------------------------- the walk

def load_live():
    """Where the search currently stands: the LAST config tried, not the best-scoring one.

    There is no snap-back. Elitism meant a round that scored worse was thrown away and the next
    round restarted from the incumbent -- so rounds 15-20 each stepped away from the same
    438-word prompt and were yanked straight back to it. Six rounds, no movement. A search that
    can only accept immediate improvements cannot cross a valley to reach anything behind it.

    The best run is still recorded and is put in front of the mutator every round, so returning
    to it stays available -- as a decision it makes deliberately, not one the harness makes for it.
    """
    os.makedirs(CONFIGS, exist_ok=True)
    if os.path.exists(LIVE):
        rec = json.load(open(LIVE))
        if os.path.exists(rec.get("config_path", "")):
            return rec
    return load_best()


def save_live(rec):
    json.dump(rec, open(LIVE, "w"), indent=1)


def load_best():
    """The best-scoring config so far. Kept for the record and shown in context; no longer used
    to reset the search."""
    os.makedirs(CONFIGS, exist_ok=True)
    if os.path.exists(BEST):
        b = json.load(open(BEST))
        if "config_path" in b:
            return b
        # migrate a prompt-only best record into a full config
        cfg = dict(P.DEFAULTS, prompt=open(b.get("prompt_path", BASE_PROMPT)).read())
        path = os.path.join(CONFIGS, "config_seed.json")
        json.dump(cfg, open(path, "w"), indent=1)
        return {"iter": b.get("iter"), "headline_f1": b.get("headline_f1"), "config_path": path}
    seed = os.path.join(CONFIGS, "config_seed.json")
    if not os.path.exists(seed):
        json.dump(dict(P.DEFAULTS, prompt=detect.PROMPT), open(seed, "w"), indent=1)
    return {"iter": None, "headline_f1": None, "config_path": seed}


def save_best(rec):
    json.dump(rec, open(BEST, "w"), indent=1)


def load_history():
    return json.load(open(HISTORY)) if os.path.exists(HISTORY) else []


def record(n, metrics_after, improved, cfg=None, cost=None):
    """Writes twice on purpose: history.json is the mutator's own working memory (it is fed back
    into the next round's context), results.jsonl is the project-wide store every scored run shares
    so runs from different sources stay comparable."""
    h = load_history()
    knobs = {k: cfg[k] for k in ("chunk_len", "overlap", "fps", "crop", "media_resolution", "model")
             } if cfg else {}
    h.append({"iter": n, "improved": improved, "metrics": metrics_after, "config": knobs})
    json.dump(h, open(HISTORY, "w"), indent=1)
    results.record(cfg or {}, metrics_after, run=f"iter_{n:03d}", source="mutator",
                   cost=cost, kept="yes" if improved else "no")
    results.table()
    labreport.write()      # regenerate the running lab notes so the report is current mid-batch
    return h


# ---------------------------------------------------------------- model calls

def _call(system, body):
    client = genai.Client(api_key=detect._api_key())
    r = client.models.generate_content(
        model=MODEL, contents=[body],
        config=types.GenerateContentConfig(
            system_instruction=system, temperature=1.0,
            thinking_config=types.ThinkingConfig(thinking_level=THINKING)))
    u = r.usage_metadata
    pin, pout = PRICES.get(MODEL, (0.0, 0.0))
    cost = ((u.prompt_token_count or 0) / 1e6 * pin
            + ((u.candidates_token_count or 0) + (u.thoughts_token_count or 0)) / 1e6 * pout)
    return r.text, cost


def _fence(text, tag):
    m = re.search(rf"```{tag}\s*\n(.*?)```", text, re.S)
    return m.group(1).strip() if m else None


def _section(text, name):
    m = re.search(rf"##+\s*{name}\s*\n(.*?)(?=\n##\s|\Z)", text, re.S)
    return m.group(1).strip() if m else None


ALLOWED = {"prompt", "prompt2", "mode", "chunk_len", "overlap", "fps", "width", "crop",
           "media_resolution", "model", "thinking", "lever", "reason"}


def validate_candidate(cfg, live=None):
    """Reject an unusable config before it is committed, not after the money is spent."""
    if not isinstance(cfg, dict):
        return "no ```json config block found"
    unknown = set(cfg) - ALLOWED
    if unknown:
        return f"unknown config keys {sorted(unknown)}; allowed: {sorted(ALLOWED)}"
    p = cfg.get("prompt")
    if not p:
        return "config has no prompt"
    if "{start" not in p:
        return "prompt does not contain the {start} placeholder"
    try:
        p.format(start=1234.5, obs="")
    except Exception as e:
        return f"prompt breaks .format(): {type(e).__name__}: {e} -- literal braces not allowed"
    # A candidate that simply omits `mode` and `prompt2` silently drops the pipeline back to a
    # single call, and the round then measures something else entirely. The whole first
    # two-stage lineage ran that way -- three rounds, none of them two-stage -- because this
    # check keyed off the CANDIDATE's mode rather than the one in play.
    if live is not None and P.normalise(live).get("mode") == "two_stage" \
            and cfg.get("mode") != "two_stage":
        return ("the pipeline in play is two_stage; your config must keep \"mode\": \"two_stage\" "
                "and a prompt2. Omitting them silently reverts to a single call.")
    if cfg.get("mode") == "two_stage":
        # stage 2 never sees the video. If it does not carry the observations through, it is
        # reasoning about nothing, and the round would score zero for a reason unrelated to
        # whatever was being tested.
        p2 = cfg.get("prompt2")
        if not p2:
            return "mode is two_stage but there is no prompt2"
        if "{obs}" not in p2:
            return "prompt2 must contain {obs} -- that is where stage 1's observations are inserted"
        if "{start" not in p2:
            return "prompt2 must contain {start} so events get absolute match times"
        try:
            p2.format(start=1234.5, obs="x")
        except Exception as e:
            return f"prompt2 breaks .format(): {type(e).__name__}: {e}"
    if cfg.get("chunk_len", 30) <= cfg.get("overlap", 8):
        return "overlap must be smaller than chunk_len"
    if not 2.0 <= cfg.get("chunk_len", 30) <= 60.0:
        return "chunk_len must be between 2 and 60 seconds"
    est = P.estimate_cost(P.normalise(cfg))
    if est > MAX_ROUND_COST:
        return f"this config would cost ${est:.2f} to evaluate, over the ${MAX_ROUND_COST:.2f} cap"
    # One change per round is the rule and it cannot be policed inside prose -- but a round that
    # rewrites the prompt AND moves a pipeline lever is unattributable no matter how the prose
    # reads, and that IS checkable. Rounds 21-28 each changed several things at once; when the
    # score moved there was no way to say which change moved it.
    if live is not None:
        a, b = P.normalise(live), P.normalise(cfg)
        knobs = [k for k in ("chunk_len", "overlap", "fps", "width", "crop", "media_resolution",
                             "model", "thinking") if a[k] != b[k]]
        if knobs and a["prompt"].strip() != b["prompt"].strip():
            return (f"this changes the prompt AND {', '.join(knobs)} in one round, so nothing "
                    f"could be attributed to either. Change the prompt or the settings, not both.")
        if len(knobs) > 1:
            return f"this moves {len(knobs)} settings at once ({', '.join(knobs)}). Move one."
    return None


def parse(text):
    def _j(tag):
        raw = _fence(text, tag)
        try:
            return json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return None
    preds = _j("predictions")
    return {"conjecture": _section(text, "CONJECTURE"), "change": _section(text, "CHANGE"),
            "prediction": _section(text, "PREDICTION"), "candidate": _j("config"),
            "predictions": preds if isinstance(preds, list) else []}


def propose(ctx, live=None, retries=1):
    """Ask for a proposal; re-ask once with the validator's complaint if the prompt is unusable."""
    body, cost = ctx, 0.0
    for attempt in range(retries + 1):
        text, c = _call(SYSTEM, body)
        cost += c
        p = parse(text)
        err = validate_candidate(p["candidate"], live)
        if not err:
            return text, p, cost, None
        if attempt == retries:
            return text, p, cost, err
        body = (f"{ctx}\n\n{'=' * 92}\nYour previous reply was rejected: {err}\n"
                f"Reply again in full, fixing only that.")


# ---------------------------------------------------------------- one round

def run_pipeline(cfg, concurrency=32):
    """Every lever, not just the prompt: crop, resolution, fps, clip length, model."""
    return P.run(cfg, concurrency=concurrency)


def entry_head(n, p):
    return (f"# Iteration {n}\n\n## CONJECTURE\n{p['conjecture']}\n\n"
            f"## CHANGE\n{p['change']}\n\n## PREDICTION\n{p['prediction']}\n")


def outcome_block(before, after, rows, summ, stats):
    L = ["\n## OUTCOME", "_Computed by the harness. Not written by the mutator._\n", "```",
         metrics.render(rows, summ), "```", "",
         f"headline_f1 {before['headline_f1']:.3f} -> {after['headline_f1']:.3f}"
         f"   ({after['headline_f1'] - before['headline_f1']:+.3f})",
         f"n_pred {before['n_pred']} -> {after['n_pred']}   "
         f"missed {before['missed']} -> {after['missed']}   "
         f"invented {before['invented']} -> {after['invented']}",
         f"pipeline: ${stats['cost']:.2f}, {stats['hits']} cached, {stats['fail']} failed"]
    # A round that lost chunks to rate limiting produced fewer predictions for a reason that has
    # nothing to do with the config. Saying so here stops the verdict reading a throttled round as
    # evidence -- that is how "10 fps crashes the API" became a permanent belief about frame rate.
    if stats.get("throttled"):
        share = stats["throttled"] / max(stats["n_chunks"], 1)
        L += ["", f"WARNING: {stats['throttled']} of {stats['n_chunks']} chunks ({share:.0%}) were "
                  "rejected by rate limiting, not by the model. Those clips returned no events, so "
                  "tp and n_pred are understated by roughly that share. This round is NOT evidence "
                  "about the config you changed -- say so in your verdict and do not add a belief "
                  "to the notebook based on it."]
    return "\n".join(L) + "\n" 


def _best_prompt(best):
    """The best config's prompt text, verbatim, so going back means copying rather than recalling."""
    try:
        return json.load(open(best["config_path"]))["prompt"]
    except Exception:
        return None


def _best_cfg(best):
    try:
        c = P.normalise(json.load(open(best["config_path"])))
        return "  ".join(f"{k}={c[k]}" for k in ("chunk_len", "overlap", "fps", "width", "crop",
                                                 "media_resolution", "model", "thinking"))
    except Exception:
        return ""


def one_round(dry_run=False, verbose=True):
    t0 = time.time()
    nb = notebook.read()
    n = notebook.next_iteration()
    live = load_live()
    best = load_best()

    live_cfg = json.load(open(live["config_path"]))
    gt = ingest.load_events()
    pred, _ = run_pipeline(live_cfg)
    before = metrics.compute(pred, gt)
    hist = load_history()
    # Removing elitism let the search cross a valley -- rounds 21-23 reached a new best only by
    # passing through a config that scored 0.038 worse. It also let it wander: 0.463 -> 0.410 over
    # four rounds with no return. The guard is a prompt, not a revert; going back stays its call.
    drift = (best.get("headline_f1") or 0) - before["headline_f1"]
    ctx = context.build(pred, gt, nb, history=hist, config=live_cfg,
                        live={"name": os.path.basename(live["config_path"]),
                              "best": best, "walk": True,
                              "best_prompt": _best_prompt(best),
                              "best_cfg": _best_cfg(best),
                              "drift": drift if drift > NOISE_FLOOR else None})

    if verbose:
        lc = P.normalise(live_cfg)
        print(f"\n{'#' * 92}\n# ITERATION {n}   |   in play: {os.path.basename(live['config_path'])}"
              f"   |   headline_f1 {before['headline_f1']:.3f}\n"
              f"# clip {lc['chunk_len']}s/{lc['overlap']}s overlap · {lc['fps']}fps · "
              f"crop={lc['crop']} · res={lc['media_resolution'] or 'default'} · {lc['model']}\n"
              f"{'#' * 92}\n")

    text, p, cost, err = propose(ctx, live_cfg)
    if verbose:
        print(text)
    if err:
        print(f"\n!! candidate rejected after retry: {err}\n!! round abandoned, nothing written.")
        return None
    if dry_run:
        print("\n--dry-run: nothing written, pipeline not run.")
        return None

    # commit BEFORE running -- this ordering is the design
    cfg_path = os.path.join(CONFIGS, f"config_{n:03d}.json")
    entry_path = notebook.commit_entry(n, entry_head(n, p))
    with open(cfg_path, "w") as fh:
        json.dump(p["candidate"], fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    if verbose:
        print(f"\ncommitted {os.path.relpath(entry_path, ROOT)} and the candidate prompt. "
              f"Running the pipeline...")

    after_pred, stats = run_pipeline(p["candidate"])
    after = metrics.compute(after_pred, gt)
    rows, summ = metrics.score(p["predictions"], before, after)
    notebook.append_entry(n, outcome_block(before, after, rows, summ, stats))

    if verbose:
        print("\n" + metrics.render(rows, summ))
        print(f"\nheadline_f1 {before['headline_f1']:.3f} -> {after['headline_f1']:.3f} "
              f"({after['headline_f1'] - before['headline_f1']:+.3f})")

    verdict_body = (f"{entry_head(n, p)}\n{outcome_block(before, after, rows, summ, stats)}\n"
                    f"Your previous summary:\n{(nb or {}).get('summary') or '(none -- first round)'}")
    vtext, vcost = _call(VERDICT_SYSTEM, verdict_body)
    cost += vcost
    verdict, summary = _section(vtext, "VERDICT"), _section(vtext, "SUMMARY")
    notebook.append_entry(n, f"\n## VERDICT\n{verdict or vtext}\n")
    if summary:
        notebook.write_summary(f"# What I know about this pipeline\n\n{summary}\n")

    improved = after["headline_f1"] > before["headline_f1"] + NOISE_FLOOR
    record(n, after, improved, P.normalise(p["candidate"]), cost=cost + stats["cost"])
    # The walk always continues from where it just landed, better or worse. `improved` is now a
    # label on the record, not a gate on the search.
    save_live({"iter": n, "headline_f1": after["headline_f1"], "config_path": cfg_path})
    # On a fresh lineage best.json carries no score, so round 0 would be recorded as "best"
    # however badly it did -- and the walk would then treat a worse config as home. The seed's
    # own score is the bar to beat, and `before` is exactly that on round 0.
    bar = best.get("headline_f1")
    if bar is None:
        bar = before["headline_f1"]
    is_best = after["headline_f1"] > bar
    if is_best:
        save_best({"iter": n, "headline_f1": after["headline_f1"], "config_path": cfg_path})
    if verbose:
        print(f"\n## VERDICT\n{verdict or vtext}")
        b = "NEW BEST" if is_best else f"best is still {best['headline_f1']:.3f} (iter {best['iter']})"
        print(f"\nnext round continues from iter {n} ({after['headline_f1']:.3f}) -- {b}")
        print(f"round {n}: ${cost + stats['cost']:.2f} total "
              f"(mutator ${cost:.2f} + pipeline ${stats['cost']:.2f}), {time.time() - t0:.0f}s")
    return {"iter": n, "before": before["headline_f1"], "after": after["headline_f1"],
            "improved": improved, "cost": cost + stats["cost"],
            "direction_hits": summ["direction_hits"], "n_claims": summ["n"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="think only: print the proposal, write nothing, run nothing")
    ap.add_argument("--rounds", type=int, default=1, help="how many full rounds to run")
    ap.add_argument("--budget", type=float, default=None,
                    help="stop once cumulative spend reaches this many dollars")
    a = ap.parse_args()

    history = []
    for i in range(1 if a.dry_run else a.rounds):
        spent = sum(h["cost"] for h in history)
        if a.budget is not None and spent >= a.budget:
            print(f"\nbudget reached: ${spent:.2f} of ${a.budget:.2f} after {i} rounds. Stopping.")
            break
        r = one_round(dry_run=a.dry_run)
        if r is None:
            break
        history.append(r)

    if len(history) > 1:
        print(f"\n{'=' * 92}\nLOOP SUMMARY\n{'=' * 92}")
        print(f"{'round':>6}{'F1 before':>11}{'F1 after':>10}{'kept':>7}"
              f"{'predictions':>13}{'cost':>8}")
        for r in history:
            hits = f"{r['direction_hits']}/{r['n_claims']}"
            kept = "yes" if r["improved"] else "no"
            print(f"{r['iter']:>6}{r['before']:>11.3f}{r['after']:>10.3f}{kept:>7}"
                  f"{hits:>13}{r['cost']:>8.2f}")
        print(f"\ntotal ${sum(r['cost'] for r in history):.2f}")


if __name__ == "__main__":
    main()
