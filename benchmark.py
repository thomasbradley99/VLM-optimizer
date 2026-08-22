"""Score several models on the same configuration, on the same video.

Subset mode is the point. Ranking eight models over the whole match costs ~$110; ranking them
on six two-minute blocks costs a tenth of that and orders them just as well. The blocks are
spread through the match rather than taken contiguously, because the first ten minutes are
warm-up-heavy and the last ten are decided sets -- a contiguous sample would flatter or punish
a model for reasons that have nothing to do with the model.

Ground truth is restricted to the sampled blocks. Scoring a partial run against all 550 events
would count every unwatched event as a miss and make every model look identical and terrible.
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "mutator"))
import evaluate as E, ingest, metrics, pipeline as P, results

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.7-flash",
          "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash-preview",
          "gemini-3.1-pro-preview", "gemini-2.5-pro"]
PRICES = {"gemini-3.1-pro-preview": (2.00, 12.00), "gemini-2.5-pro": (2.00, 12.00)}
SPAN = P.SPAN


def blocks(n_blocks, minutes):
    """n evenly spaced windows of `minutes` each, across the scored span."""
    lo, hi = SPAN
    step = (hi - lo) / n_blocks
    return [(lo + i * step, lo + i * step + minutes * 60) for i in range(n_blocks)]


def run_model(cfg, model, wins, gt, conc):
    c = P.normalise({**cfg, "model": model})
    starts = P.starts(c)
    keep = [i for i, s in enumerate(starts)
            if wins is None or any(a <= s < b for a, b in wins)]
    if wins is None:
        gtw = gt
    else:
        gtw = [g for g in gt if any(a <= g["t"] < b for a, b in wins)]
    t0 = time.time()
    pred, st = P.run({**cfg, "model": model}, concurrency=conc, only=keep)
    if wins is not None:
        pred = [p for p in pred if any(a <= p["t"] < b for a, b in wins)]
    tp = len(E.match(pred, gtw, 1.0, "+type"))
    f1 = 2 * tp / (len(pred) + len(gtw)) if (len(pred) + len(gtw)) else 0.0
    return {"model": model, "f1": round(f1, 4), "tp": tp, "n_pred": len(pred),
            "n_gt": len(gtw), "clips": len(keep), "cost": round(st["cost"], 2),
            "fail": st["fail"], "throttled": st.get("throttled", 0),
            "mins": round((time.time() - t0) / 60, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="whole match instead of sampled blocks")
    ap.add_argument("--blocks", type=int, default=6)
    ap.add_argument("--minutes", type=float, default=2.0)
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--concurrency", type=int, default=16)
    a = ap.parse_args()

    gt = ingest.load_events()
    cfg = json.load(open(os.path.join(HERE, "mutator/notebook/candidates/config_023.json")))
    cfg.pop("lever", None)
    wins = None if a.full else blocks(a.blocks, a.minutes)
    if wins:
        cov = sum(b - a_ for a_, b in wins)
        print(f"sampling {a.blocks} x {a.minutes:g} min = {cov/60:.0f} min "
              f"({100*cov/(SPAN[1]-SPAN[0]):.0f}% of the match)")
    else:
        print("whole match")
    P.PRICES.update(PRICES)

    out, spend = [], 0.0
    print(f"\n{'model':<26}{'F1':>7}{'TP':>6}{'said':>7}{'of':>6}{'$':>7}{'min':>6}  fails")
    for m in a.models.split(","):
        try:
            r = run_model(cfg, m, wins, gt, a.concurrency)
        except Exception as e:
            print(f"{m:<26}  ERROR {str(e).splitlines()[0][:60]}")
            continue
        out.append(r); spend += r["cost"]
        print(f"{r['model']:<26}{r['f1']:>7.3f}{r['tp']:>6}{r['n_pred']:>7}{r['n_gt']:>6}"
              f"{r['cost']:>7.2f}{r['mins']:>6.1f}  {r['fail']}"
              f"{' THROTTLED' if r['throttled'] else ''}")
    out.sort(key=lambda r: -r["f1"])
    tag = "full" if a.full else f"{a.blocks}x{a.minutes:g}min"
    p = os.path.join(HERE, f"benchmark_{tag}.json")
    json.dump({"config": "iter_023 prompt, 6s/2s, cropped, 5fps", "sample": tag,
               "windows": wins, "results": out}, open(p, "w"), indent=1)
    print(f"\ntotal ${spend:.2f} -> {p}")
    print(f"\nranked:")
    for r in out:
        print(f"  {r['f1']:.3f}  {r['model']}")


if __name__ == "__main__":
    main()
