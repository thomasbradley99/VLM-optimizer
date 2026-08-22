"""One prompt, one Gemini call per chunk, fully parallel, cached on disk. Chunks go inline rather
than via the Files API -- at ~500 KB they are well under the request cap, and it avoids 169 uploads
plus ACTIVE-state polling. `fps=5` is explicit: Gemini samples video at 1 fps by default, which
would put a floor under the +/-0.5s column that has nothing to do with the model."""
import asyncio
import hashlib
import json
import os
import time

from google import genai
from google.genai import types

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
MODEL = "gemini-3.7-flash"   # 2.5-flash is retired for new API keys
FPS = 5
THINKING = "low"
# How the model is asked to identify a team. "colour" was the baseline; "side" asks for court
# position instead, which is far coarser to perceive at 640px than a jersey hue. Verified by eye
# at t=1100/2500/4200 (one sample per set): white plays left, blue plays right, no end swap.
TEAM_MODE = os.environ.get("TEAM_MODE", "side")
SIDE_TO_TEAM = {"left": "white", "right": "blue"}
PRICES = {"gemini-3.7-flash": (0.75, 3.75), "gemini-3.6-flash": (0.75, 3.75),
          "gemini-3.5-flash": (1.50, 9.00)}  # $/M in, out (paid tier, to 2026-12-31)

PROMPT = """You are scouting a single volleyball match from a fixed camera.

CRITICAL: This is a convention hall with several courts running at once. Analyse ONLY the main
court in the foreground -- the one with the referee standing on the elevated stand at the centre
of the frame. Other matches are visible in the background; ignore them completely.

The net runs up the middle of the frame, so each team occupies one half of the image. Identify a
team ONLY by which half of the frame they are standing in -- "left" or "right" as you see it on
screen. Do not use jersey colour.

This clip begins at {start:.2f} seconds into the match and runs for 30 seconds.

Report every contact a player makes with the ball, in order, using these types:
  serve   - the contact that puts the ball in play from behind the end line
  receive - first contact by the receiving team off a serve
  dig     - defensive contact off an attack (not off a serve)
  set     - the second contact, placing the ball for an attacker
  attack  - an attacking hit that does NOT immediately end the rally
  kill    - an attacking hit that immediately ends the rally in that team's favour
  block   - a contact made at the net by a player with hands above it

For each contact give:
  t       - the time of contact in ABSOLUTE MATCH SECONDS. Add the offset within this clip to
            the clip start of {start:.2f}. Be precise to a fraction of a second.
  type    - one of the seven above
  side    - "left" or "right": which half of the frame the contacting player is standing in
  number  - the contacting player's jersey number as a string, or null if you cannot read it.
            Do not guess.
  error   - true if this contact was an error (into the net, out of bounds, mishandled)
  point   - true if the rally ended on this contact and a point was scored

Report only contacts you actually observe. Do not invent a full rally structure. If no play
happens in this clip, return an empty list."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {"events": {"type": "ARRAY", "items": {
        "type": "OBJECT",
        "properties": {
            "t": {"type": "NUMBER"},
            "type": {"type": "STRING",
                     "enum": ["serve", "receive", "dig", "set", "attack", "kill", "block"]},
            "side": {"type": "STRING", "enum": ["left", "right"]},
            "number": {"type": "STRING", "nullable": True},
            "error": {"type": "BOOLEAN"},
            "point": {"type": "BOOLEAN"},
        },
        "required": ["t", "type", "side", "error", "point"]}}},
    "required": ["events"],
}


def _api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        with open(os.path.join(HERE, ".env")) as fh:
            for line in fh:
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        raise SystemExit("GEMINI_API_KEY not found in environment or .env")
    return key


def _cache_path(prompt, cid):
    h = hashlib.sha256(f"{prompt}|{cid}|{MODEL}|{FPS}|{TEAM_MODE}".encode()).hexdigest()[:16]
    return os.path.join(CACHE, f"{h}.json")


async def _one(client, sem, cid, start, stats):
    prompt = PROMPT.format(start=start)
    path = _cache_path(prompt, cid)
    if os.path.exists(path):
        stats["hits"] += 1
        return json.load(open(path))["events"]

    async with sem:
        part = types.Part(
            inline_data=types.Blob(mime_type="video/mp4",
                                   data=open(os.path.join(HERE, "chunks", f"{cid}.mp4"), "rb").read()),
            video_metadata=types.VideoMetadata(fps=FPS))
        cfg = types.GenerateContentConfig(
            temperature=0.0, response_mime_type="application/json", response_schema=SCHEMA,
            thinking_config=types.ThinkingConfig(thinking_level=THINKING))
        for attempt in range(3):
            try:
                r = await client.aio.models.generate_content(
                    model=MODEL, contents=[part, prompt], config=cfg)
                break
            except Exception as e:
                if attempt == 2:
                    stats["fail"] += 1
                    print(f"  {cid} failed: {type(e).__name__}: {str(e)[:90]}")
                    return []
                await asyncio.sleep(2 * (attempt + 1))

    u = r.usage_metadata
    stats["in"] += u.prompt_token_count or 0
    stats["out"] += (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
    try:
        events = json.loads(r.text)["events"]
    except Exception as e:
        stats["fail"] += 1
        print(f"  {cid} unparseable: {type(e).__name__}")
        return []
    for e in events:
        if TEAM_MODE == "side":
            e["team"] = SIDE_TO_TEAM.get(e.pop("side", None))
        e["chunk"] = cid
        e["chunk_start"] = start
    json.dump({"events": events}, open(path, "w"))
    return events


async def run(index, concurrency=20):
    os.makedirs(CACHE, exist_ok=True)
    client = genai.Client(api_key=_api_key())
    sem = asyncio.Semaphore(concurrency)
    stats = {"in": 0, "out": 0, "hits": 0, "fail": 0}
    t0 = time.time()
    out = await asyncio.gather(*[_one(client, sem, cid, s, stats)
                                 for cid, s in sorted(index.items())])
    pin, pout = PRICES[MODEL]
    stats["cost"] = stats["in"] / 1e6 * pin + stats["out"] / 1e6 * pout
    stats["wall"] = time.time() - t0
    return [e for chunk in out for e in chunk], stats


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--concurrency", type=int, default=20)
    a = ap.parse_args()
    idx = json.load(open(os.path.join(HERE, "chunks", "index.json")))
    if a.limit:
        idx = dict(sorted(idx.items())[:a.limit])
    ev, st = asyncio.run(run(idx, a.concurrency))
    print(json.dumps(ev[:20], indent=1))
    print(f"{len(ev)} events from {len(idx)} chunks | {st['in']} in / {st['out']} out "
          f"| ${st['cost']:.3f} | {st['hits']} cached | {st['fail']} failed | {st['wall']:.1f}s")
