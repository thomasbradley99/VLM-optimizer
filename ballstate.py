"""Two stages, split at the seam where the pipeline actually breaks.

The earlier two-stage attempt failed because stage 1 was still asked to describe "touches" --
already a taxonomy commitment, so both stages were doing volleyball and the split bought nothing.
Here stage 1 may only report what is observable without knowing the sport: which side of the net
the ball is on, when it crosses, who makes contact, where the ball goes next. Stage 2 never sees
the video and does all of the naming.

The seam matters because perception is not the bottleneck: the detector locates 76% of real events
and names only 53% of those correctly. Splitting perception from taxonomy puts the second model
exactly on the failing half, with the sequence in front of it -- which a single call watching six
seconds can never have.
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "mutator"))

import dedupe as dd          # noqa: E402
import detect                # noqa: E402
import evaluate as E         # noqa: E402
import ingest                # noqa: E402
import pipeline as P         # noqa: E402
from google import genai     # noqa: E402
from google.genai import types  # noqa: E402

OBSERVE = """You are watching a {L:g}-second clip of a volleyball match from one fixed camera.
A net runs vertically up the middle of the frame, dividing it into a LEFT court and a RIGHT court.
Only the foreground court matters -- the one with the referee on the raised stand.

Do NOT name any volleyball actions. Report only what you can literally see, as a list of moments,
each with a time in seconds from the start of this clip:

  - the ball is on the LEFT or the RIGHT of the net
  - the ball CROSSES the net, and in which direction
  - a player MAKES CONTACT with the ball: the time, which side they stand on, their shirt colour,
    their number if legible, and whether they were airborne or on the ground
  - after that contact the ball goes UP (staying their side), OVER (across the net), DOWN (to the
    floor), or OUT
  - the ball HITS THE FLOOR, and on which side
  - nobody is playing: the ball is being carried, rolled, held, or lying still

Be precise about the times. If nothing is in play, say so in one line."""

REASON = """Below are literal observations from a {L:g}-second volleyball clip that began at
{start:.2f} seconds into the match. You cannot see the video. Work out which volleyball actions
these observations correspond to.

Use the sequence to reason:
  a rally begins with a serve, struck from behind the back line
  the first contact answering a serve is a receive
  a contact answering an opponent's attack is a dig
  any contact that sends the ball OVER the net is an attack
  an attack after which the ball hits the opponent's floor is a kill
  a contact at the net by an airborne player with hands high is a block
  a contact that puts the ball UP for a team-mate is a set, but report it ONLY when the next
    contact is a kill

Report one event per real contact:
  t       {start:.2f} plus the observed offset, in absolute match seconds
  side    "left" or "right" -- the half the contacting player was standing in
  number  shirt number as a string, or null
  error   true if the ball went into the net or out of bounds off this contact
  point   true if the rally ended on this contact

Do not invent contacts the observations do not mention. If the observations describe no play,
return an empty list.

OBSERVATIONS:
{obs}"""

CACHE = os.path.join(HERE, "cache")
OVERLAP = {30: 8.0, 15: 4.0, 10: 3.0, 8: 2.5, 6: 2.0, 5: 2.0, 4: 1.5, 3: 1.0}


def _k(*parts):
    h = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]
    return os.path.join(CACHE, h + ".json")


async def one(cl, sem, c, gk, d, cid, start, m1, m2, st):
    L = c["chunk_len"]
    ko = _k("obs2", cid, gk, m1, OBSERVE, L)
    async with sem:
        if os.path.exists(ko):
            obs = json.load(open(ko))["t"]
            st["hits"] += 1
        else:
            part = types.Part(
                inline_data=types.Blob(mime_type="video/mp4",
                                       data=open(os.path.join(d, f"{cid}.mp4"), "rb").read()),
                video_metadata=types.VideoMetadata(fps=c["fps"]))
            r = await cl.aio.models.generate_content(
                model=m1, contents=[part, OBSERVE.format(L=L)],
                config=types.GenerateContentConfig(temperature=0.0))
            obs = r.text or ""
            u = r.usage_metadata
            st["in"] += u.prompt_token_count or 0
            st["out"] += (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
            json.dump({"t": obs}, open(ko, "w"))

        kr = _k("reason2", cid, gk, m2, REASON, obs)
        if os.path.exists(kr):
            ev = json.load(open(kr))["e"]
            st["hits"] += 1
        else:
            r = await cl.aio.models.generate_content(
                model=m2, contents=[REASON.format(L=L, start=start, obs=obs)],
                config=types.GenerateContentConfig(
                    temperature=0.0, response_mime_type="application/json",
                    response_schema=detect.SCHEMA))
            u = r.usage_metadata
            st["in"] += u.prompt_token_count or 0
            st["out"] += (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
            ev = json.loads(r.text).get("events", [])
            json.dump({"e": ev}, open(kr, "w"))

    for e in ev:
        e["chunk"] = cid
        e["chunk_start"] = start
        e["team"] = {"left": "white", "right": "blue"}.get(e.get("side"))
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", default="10,6,4")
    ap.add_argument("--observe", default="gemini-3.7-flash")
    ap.add_argument("--reason", default="gemini-3.7-flash")
    ap.add_argument("--minutes", type=float, default=5.0)
    ap.add_argument("--concurrency", type=int, default=20)
    a = ap.parse_args()

    gt = ingest.load_events()
    base = json.load(open(os.path.join(HERE, "mutator/notebook/candidates/config_023.json")))
    base.pop("lever", None)
    print(f"observe: {a.observe}  ->  reason: {a.reason}   first {a.minutes:g} min\n")
    print(f"{'clip':>6}{'F1':>8}{'TP':>6}{'said':>7}{'of':>5}{'$':>7}{'min':>6}  fails")

    for cl_ in [float(x) for x in a.clips.split(",")]:
        c = P.normalise({**base, "chunk_len": cl_, "overlap": OVERLAP[int(cl_)],
                         "model": a.observe})
        gk = P.geometry_key(c)
        d, index = P.build_chunks(c, verbose=False)
        lo = P.SPAN[0]
        hi = lo + a.minutes * 60
        keep = {k: v for k, v in index.items() if lo <= v < hi}
        gtw = [g for g in gt if lo <= g["t"] < hi]

        async def go():
            client = genai.Client(api_key=detect._api_key())
            sem = asyncio.Semaphore(a.concurrency)
            st = {"in": 0, "out": 0, "hits": 0}
            res = await asyncio.gather(
                *[one(client, sem, c, gk, d, k, v, a.observe, a.reason, st)
                  for k, v in sorted(keep.items())], return_exceptions=True)
            return ([e for r in res if isinstance(r, list) for e in r], st,
                    sum(1 for r in res if not isinstance(r, list)))

        t0 = time.time()
        raw, st, fails = asyncio.run(go())
        pred = [p for p in dd.dedupe(raw, window=0.4) if lo <= p["t"] < hi]
        pin, pout = P.PRICES.get(a.observe, (0.75, 3.75))
        cost = st["in"] / 1e6 * pin + st["out"] / 1e6 * pout
        tp = len(E.match(pred, gtw, 1.0, "+type"))
        f1 = 2 * tp / (len(pred) + len(gtw)) if (pred or gtw) else 0.0
        print(f"{cl_:>5g}s{f1:>8.3f}{tp:>6}{len(pred):>7}{len(gtw):>5}{cost:>7.2f}"
              f"{(time.time() - t0) / 60:>6.1f}  {fails}", flush=True)

    print("\nsingle-call baseline, 6s clips, same block:  F1 0.512  TP 33  said 73")


if __name__ == "__main__":
    main()
