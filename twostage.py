"""Describe, then classify: split perception from taxonomy.

The single-call setup makes one request do three jobs at once -- watch the video, map what it saw
onto a seven-way taxonomy, and emit constrained JSON. Constrained decoding competes with the
reasoning. Here stage 1 watches and writes plain prose with no schema at all, and stage 2 turns
that prose into events with no video at all. Stage 2 is text-only so it costs almost nothing.

Scored on the same 5-minute block as benchmark.py, against the same ground truth, so the number
is directly comparable to the single-call table.
"""
import argparse, asyncio, hashlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "mutator"))
import detect, evaluate as E, ingest, pipeline as P, dedupe as dd
from google import genai
from google.genai import types

DESCRIBE = """You are watching a {L:g}-second clip of a volleyball match from a fixed camera.
Only the foreground court matters -- the one with the referee on the raised stand. The net runs
vertically up the middle of the frame.

Describe, in order, every time a player touches the ball. For each touch say roughly how many
seconds into the clip it happened, whether the player was on the left or right half of the frame,
their shirt colour and number if you can read it, and what the ball did next -- went over the net,
went up to a team-mate, hit the floor, went out.

Write plain sentences. Do not use any category names or jargon. If nothing happens, say so."""

CLASSIFY = """Below is a description of a {L:g}-second volleyball clip that began at {start:.2f}
seconds into the match. Convert it into events.

  serve   - the contact that starts a rally, struck from behind the back line
  receive - a defensive contact answering a serve; the ball stays on that side
  dig     - a defensive contact answering an attack; the ball stays on that side
  set     - a contact placing the ball for a team-mate, BUT ONLY when it leads to a kill
  attack  - any contact that sends the ball over the net to the opponents
  kill    - an attack that ends the rally immediately
  block   - a contact made at the net with hands above it

For each: t = {start:.2f} plus the offset in the description, in absolute match seconds.
side = "left" or "right", the half of the frame the player was in.
number = the shirt number as a string, or null. error = true if it was a mistake.
point = true if the rally ended there.

Report only contacts the description actually mentions. Do not invent structure.

DESCRIPTION:
{desc}"""

CACHE = os.path.join(HERE, "cache")


def _key(*parts):
    return os.path.join(CACHE, hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16] + ".json")


async def one(client, sem, c, gk, d, cid, start, model, cmodel, stats):
    L = c["chunk_len"]
    kd = _key("describe", cid, gk, model, DESCRIBE, L)
    async with sem:
        if os.path.exists(kd):
            desc = json.load(open(kd))["text"]; stats["hits"] += 1
        else:
            part = types.Part(inline_data=types.Blob(
                mime_type="video/mp4", data=open(os.path.join(d, f"{cid}.mp4"), "rb").read()),
                video_metadata=types.VideoMetadata(fps=c["fps"]))
            r = await client.aio.models.generate_content(
                model=model, contents=[part, DESCRIBE.format(L=L)],
                config=types.GenerateContentConfig(temperature=0.0))
            desc = r.text or ""
            u = r.usage_metadata
            stats["in"] += u.prompt_token_count or 0
            stats["out"] += (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
            json.dump({"text": desc}, open(kd, "w"))
        kc = _key("classify", cid, gk, cmodel, CLASSIFY, desc)
        if os.path.exists(kc):
            ev = json.load(open(kc))["events"]; stats["hits"] += 1
        else:
            r = await client.aio.models.generate_content(
                model=cmodel, contents=[CLASSIFY.format(L=L, start=start, desc=desc)],
                config=types.GenerateContentConfig(
                    temperature=0.0, response_mime_type="application/json",
                    response_schema=detect.SCHEMA))
            u = r.usage_metadata
            stats["in2"] += u.prompt_token_count or 0
            stats["out2"] += (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
            ev = json.loads(r.text).get("events", [])
            json.dump({"events": ev}, open(kc, "w"))
    for e in ev:
        e["chunk"] = cid; e["chunk_start"] = start
        e["team"] = {"left": "white", "right": "blue"}.get(e.get("side"), None)
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.7-flash", help="the describer -- sees the video")
    ap.add_argument("--classify", default=None, help="the classifier -- text only. "
                    "Splitting them lets the model with the best perception describe and the "
                    "model with the best discipline decide what counts.")
    ap.add_argument("--minutes", type=float, default=5.0)
    ap.add_argument("--concurrency", type=int, default=16)
    a = ap.parse_args()
    gt = ingest.load_events()
    cfg = json.load(open(os.path.join(HERE, "mutator/notebook/candidates/config_023.json")))
    cfg.pop("lever", None)
    cm = a.classify or a.model
    c = P.normalise({**cfg, "model": a.model})
    gk = P.geometry_key(c)
    d, index = P.build_chunks(c, verbose=False)
    lo = P.SPAN[0]; hi = lo + a.minutes * 60
    keep = {k: v for k, v in index.items() if lo <= v < hi}
    gtw = [g for g in gt if lo <= g["t"] < hi]
    print(f"describe: {a.model}  ->  classify: {cm}  ·  {len(keep)} clips · {len(gtw)} real events")

    async def go():
        cl = genai.Client(api_key=detect._api_key())
        sem = asyncio.Semaphore(a.concurrency)
        st = {"in": 0, "out": 0, "in2": 0, "out2": 0, "hits": 0}
        res = await asyncio.gather(*[one(cl, sem, c, gk, d, k, v, a.model, cm, st)
                                     for k, v in sorted(keep.items())],
                                   return_exceptions=True)
        return [e for r in res if isinstance(r, list) for e in r], st, \
               sum(1 for r in res if not isinstance(r, list))

    t0 = time.time()
    raw, st, fails = asyncio.run(go())
    pred = [p for p in dd.dedupe(raw, window=0.4) if lo <= p["t"] < hi]
    pin, pout = P.PRICES.get(a.model, (0.75, 3.75))
    cost = (st["in"] + st["in2"]) / 1e6 * pin + (st["out"] + st["out2"]) / 1e6 * pout
    tp = len(E.match(pred, gtw, 1.0, "+type"))
    f1 = 2 * tp / (len(pred) + len(gtw)) if pred or gtw else 0
    print(f"\n  F1 {f1:.3f}   TP {tp}   reported {len(pred)}   ratio 1:{len(pred)/max(tp,1):.1f}"
          f"   ${cost:.2f}   {(time.time()-t0)/60:.1f} min   {fails} failed")
    print(f"  single-call baseline on the same block:  F1 0.512  TP 33  reported 73  1:2.2")


if __name__ == "__main__":
    main()
