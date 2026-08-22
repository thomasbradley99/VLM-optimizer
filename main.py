"""Baseline: can a VLM detect volleyball events from video? Run it, print one table."""
import asyncio
import json
import os
import time

import chunk as chunker
import detect
import dedupe as dd
import evaluate as E
import ingest
import report

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = float(os.environ.get("TOL", 1.0))
TIMELINE_ROWS = None if os.environ.get("FULL") else 40


def main(concurrency=int(os.environ.get("CONCURRENCY", 32))):
    t0 = time.time()
    gt = ingest.load_events()

    bad = E.selftest(gt)                      # gate: nothing downstream is valid without this
    print("sanity: gt-vs-gt = " + ("1.000 across all cells  [PASS]" if not bad
                                   else "FAILED: " + "; ".join(bad)))
    if bad:
        raise SystemExit(1)
    print(f"ground truth: 553 parsed, {len(gt)} scored\n")

    t1 = time.time()
    index, made = chunker.build()
    t2 = time.time()
    raw, st = asyncio.run(detect.run(index, concurrency))
    pred = dd.dedupe(raw)

    g, pt = E.grid(pred, gt), E.per_type(pred, gt)
    print(E.render(g, pt, len(pred), len(gt), types=False))

    d, best = E.sweep_offset(pred, gt)
    zero = g["+type"]["1.0"][2]
    asis, swapped = E.team_swap_gain(pred, gt)
    print(f"\noffset sweep:  best delta {d:+.2f}s -> F1 {best:.3f}  (vs {zero:.3f} at zero)")
    print(f"team labels:   as-is {asis:.3f}  |  blue/white swapped {swapped:.3f}")
    print(f"tokens:        {st['in']:,} in / {st['out']:,} out    cost ${st['cost']:.2f}"
          f"    cache {st['hits']}/{len(index)}    failed {st['fail']}")
    print(f"wall:          extract {t2-t1:.0f}s ({made} new)   detect {st['wall']:.0f}s"
          f"   total {time.time()-t0:.0f}s")

    full = report.render(pred, gt, TOL, max_timeline=None)
    open(os.path.join(HERE, "report.txt"), "w").write(full)
    print("\n" + report.render(pred, gt, TOL, max_timeline=TIMELINE_ROWS))

    json.dump({"predicted": pred, "raw_count": len(raw)},
              open(os.path.join(HERE, "events.json"), "w"), indent=1)
    json.dump({"grid": g, "per_type": pt, "offset": {"best_delta": d, "f1_at_best": best,
               "f1_at_zero": zero}, "team": {"as_is": asis, "swapped": swapped},
               "headline_f1_1.0s_type": zero, "cost_usd": round(st["cost"], 3),
               "n_pred": len(pred), "n_gt": len(gt)},
              open(os.path.join(HERE, "scores.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
