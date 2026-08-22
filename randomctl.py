"""The control the whole project rests on: does reasoning beat picking at random?

Identical harness, identical starting point, identical budget -- only the proposer changes. Here
it draws a legal move uniformly instead of forming an account of what is wrong. If the language
model's rounds do not beat this, the diagnoses are decoration.

The move set is deliberately what the optimiser actually uses: a geometry change, or one of a
handful of mechanical prompt edits. It cannot write new prose, which is the one advantage the
real proposer keeps -- so this is a floor, not an equal contest.
"""
import json, os, random, sys, time
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); sys.path.insert(0,HERE+"/mutator")
import evaluate as E, ingest, metrics, pipeline as P, results

SEED=20260822
CLIPS=[(30.0,8.0),(15.0,4.0),(10.0,3.0),(8.0,2.5),(6.0,2.0)]
SENTENCES=[
 "Report only contacts you are confident about.",
 "Ignore any contact where the player is not clearly visible.",
 "A rally begins with a serve from behind the back line.",
 "Do not report the same contact twice.",
 "Prefer fewer, more certain events over many uncertain ones.",
 "Describe only what the ball does, not what the player intended.",
]
def mutate(cfg, rng):
    m=rng.choice(["clip","crop","fps","add","drop"])
    c=dict(cfg)
    if m=="clip":
        L,o=rng.choice(CLIPS); c["chunk_len"],c["overlap"]=L,o; return c,f"clip -> {L:g}s"
    if m=="crop":
        c["crop"]=None if c.get("crop") else "1920:620:0:330"
        return c,f"crop -> {'on' if c['crop'] else 'off'}"
    if m=="fps":
        c["fps"]=rng.choice([3,5,8]); return c,f"fps -> {c['fps']}"
    lines=[l for l in c["prompt"].split("\n")]
    if m=="add":
        s=rng.choice(SENTENCES); lines.insert(rng.randrange(len(lines)), s)
        c["prompt"]="\n".join(lines); return c,f"add: {s[:44]}"
    cand=[i for i,l in enumerate(lines) if l.strip() and "{start" not in l and len(l)>25]
    if cand:
        i=rng.choice(cand); killed=lines.pop(i)[:44]; c["prompt"]="\n".join(lines)
        return c,f"drop: {killed}"
    return c,"no-op"

def main():
    rng=random.Random(SEED)
    gt=ingest.load_events()
    cfg=json.load(open(HERE+"/mutator/notebook/candidates/config_seed_armH.json"))
    cfg.pop("lever",None); cfg["crop"]=None
    pred,st=P.run(cfg, verbose=False)
    m=metrics.compute(pred,gt); cur=m["headline_f1"]
    print(f"start  F1 {cur:.3f}  TP {m['tp']}  n_pred {m['n_pred']}", flush=True)
    spend=0.0
    for n in range(8):
        cand,desc=mutate(cfg,rng)
        est=P.estimate_cost(P.normalise(cand))
        if est>9.0:
            print(f"  {n}: {desc}  -- rejected, ${est:.2f} over cap", flush=True); continue
        t0=time.time(); pred,st=P.run(cand, verbose=False)
        mm=metrics.compute(pred,gt); spend+=st["cost"]
        results.record(P.normalise(cand), mm, run=f"rand_{n:03d}", source="random-control",
                       cost=st["cost"], note=f"random control: {desc}")
        print(f"  {n}: {desc:<50} F1 {mm['headline_f1']:.3f} ({mm['headline_f1']-cur:+.3f})  "
              f"TP {mm['tp']:>3}  ${st['cost']:.2f}  {(time.time()-t0)/60:.1f}m", flush=True)
        cfg, cur = cand, mm["headline_f1"]      # a walk, exactly like the real one
    print(f"\nend    F1 {cur:.3f}   total ${spend:.2f}", flush=True)
    print("real optimiser on the same walk rules: 0.402 -> 0.452 over 8 rounds", flush=True)

if __name__=="__main__": main()
