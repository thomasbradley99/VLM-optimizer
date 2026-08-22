"""Brute-force the one lever with a monotonic trend, to find where it actually turns over.

30s/15s/10s/6s gave F1 .359/.391/.434/.455 with TP 195/239/238/315. Six seconds is not a measured
peak -- it is where the sweep stopped. Convergence toward an optimum cannot be demonstrated until
the optimum is located, so this locates it by hand before any lineage is asked to walk to it.

Prompt and every other setting held fixed at the current best. Only clip length moves.
"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "mutator"))
import evaluate as E, ingest, metrics, pipeline as P, results

gt = ingest.load_events()
best = json.load(open(os.path.join(HERE, "mutator/notebook/candidates/config_crop6s.json")))
CROP = "1920:620:0:330"
ARMS = [(8.0, 2.5), (5.0, 2.0), (4.0, 1.5), (3.0, 1.0)]

print(f"{'clip':>6}{'clips':>8}{'est $':>8}", flush=True)
for L, o in ARMS:
    c = P.normalise({**best, "chunk_len": L, "overlap": o, "crop": CROP})
    print(f"{L:>5}s{len(P.starts(c)):>8}{P.estimate_cost(c):>8.2f}", flush=True)

spent = 0.0
for L, o in ARMS:
    cfg = {**best, "chunk_len": L, "overlap": o, "crop": CROP}
    cfg.pop("lever", None)
    t0 = time.time()
    print(f"\n=== {L}s clips / {o}s overlap ===", flush=True)
    pred, st = P.run(cfg)
    m = metrics.compute(pred, gt)
    m["number_f1"] = E.f1_at(pred, gt, 1.0, "+number")
    results.record(cfg, m, run=f"sweep_{L:g}s", source="hand", cost=st["cost"],
                   note=f"clip-length sweep, prompt and crop held fixed")
    results.table()
    spent += st["cost"]
    print(f"{L:g}s  F1 {m['headline_f1']:.3f}  TP {m['tp']}  n_pred {m['n_pred']}  "
          f"invented {m['invented']}  missed {m['missed']}  ${st['cost']:.2f}  "
          f"{st['fail']} failed  {(time.time()-t0)/60:.0f} min   [running total ${spent:.2f}]",
          flush=True)

print("\n=== clip length, all measurements ===", flush=True)
R = [json.loads(l) for l in open(os.path.join(HERE, "results.jsonl"))]
import collections
by = collections.defaultdict(list)
for r in R:
    if r.get("headline_f1") is not None and (r.get("crop") or r.get("chunk_len") in (30.0, None)):
        by[r.get("chunk_len") or 30.0].append(r)
for k in sorted(by, reverse=True):
    print(f"  {k:>5g}s  best F1 {max(x['headline_f1'] for x in by[k]):.3f}  "
          f"best TP {max(x['tp'] for x in by[k]):>3}", flush=True)
