"""A fully configurable pipeline, so the mutator can change the machine and not just the wording.

The baseline in ../ stays untouched: this owns its own chunk variants and its own cache keys.

The cache-key hazard that made this necessary: detect.py keys responses on the prompt alone, so
re-extracting chunks under the same filenames would silently serve answers from the old video.
Here the chunk geometry is hashed into the directory name AND into the response key, so a config
change can never collide with a previous one.
"""
import asyncio
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from google import genai        # noqa: E402
from google.genai import types  # noqa: E402

import dedupe as dd             # noqa: E402
import detect                   # noqa: E402

VIDEO = os.path.join(ROOT, "..", "volleyball-annotated", "full-001.mp4")
VARIANTS = os.path.join(HERE, "variants")
SPAN = (995.0, 4715.0)
PRICES = {"gemini-3.7-flash": (0.75, 3.75), "gemini-3.1-pro-preview": (2.00, 12.00)}
RETRIES = 5              # 429 needs patience, not persistence
CONCURRENCY = 24         # 32 tripped the rate limiter; 12 made a 930-clip round take 75 min.
                         # 24 with the long 429 backoff below is the compromise -- a throttled
                         # call now waits instead of burning its retries in six seconds.
# measured: 66 tokens/frame at default resolution, 264 at HIGH
TOKENS_PER_FRAME = {None: 66, "MEDIA_RESOLUTION_LOW": 66, "MEDIA_RESOLUTION_MEDIUM": 66,
                    "MEDIA_RESOLUTION_HIGH": 264}

DEFAULTS = {
    "mode": "single",          # "single" = one call per clip; "two_stage" = observe, then reason
    "prompt": None,            # required. In two_stage this is the OBSERVE prompt (sees video)
    "prompt2": None,           # two_stage only: the REASON prompt (text in, events out, no video)
    "chunk_len": 30.0,         # seconds of video per call
    "overlap": 8.0,            # seconds shared between neighbouring chunks
    "fps": 5,                  # frames per second sampled, both in the encode and in the request
    "width": 640,              # encoded width; the model re-samples to its own token budget anyway
    "crop": None,              # ffmpeg crop "w:h:x:y", applied before scaling. Full frame is 1920x1080
    "media_resolution": None,  # None (=66 tok/frame) or MEDIA_RESOLUTION_HIGH (=264, 4x the cost)
    "model": "gemini-3.7-flash",
    "thinking": "low",
}


def normalise(cfg):
    c = dict(DEFAULTS)
    c.update({k: v for k, v in (cfg or {}).items() if k in DEFAULTS})
    return c


def geometry_key(c):
    """Hash of everything that changes the pixels. Names the chunk directory."""
    s = f"{c['chunk_len']}|{c['overlap']}|{c['fps']}|{c['width']}|{c['crop']}"
    return hashlib.sha256(s.encode()).hexdigest()[:8]


def starts(c):
    out, t, stride = [], SPAN[0], c["chunk_len"] - c["overlap"]
    while True:
        out.append(round(t, 3))
        if t + c["chunk_len"] >= SPAN[1]:
            return out
        t += stride


def build_chunks(c, workers=4, verbose=True):
    """Extract this geometry's chunks if they don't exist. One-time per geometry, then cached."""
    d = os.path.join(VARIANTS, geometry_key(c))
    os.makedirs(d, exist_ok=True)
    index = {f"c{i:03d}": s for i, s in enumerate(starts(c))}
    todo = [(cid, s) for cid, s in index.items()
            if not os.path.exists(os.path.join(d, f"{cid}.mp4"))]
    if todo and verbose:
        print(f"  extracting {len(todo)} chunks for geometry {geometry_key(c)} "
              f"(crop={c['crop']}, {c['width']}px, {c['fps']}fps, {c['chunk_len']}s)...")

    vf = ([f"crop={c['crop']}"] if c["crop"] else []) + [f"scale={c['width']}:-2", f"fps={c['fps']}"]

    def one(item):
        cid, s = item
        subprocess.run(["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-ss", str(s),
                        "-i", VIDEO, "-t", str(c["chunk_len"]), "-an", "-vf", ",".join(vf),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
                        os.path.join(d, f"{cid}.mp4")], check=True)

    if todo:
        with cf.ThreadPoolExecutor(workers) as ex:
            list(ex.map(one, todo))
    json.dump(index, open(os.path.join(d, "index.json"), "w"), indent=1)
    return d, index


def estimate_cost(c):
    n = len(starts(c))
    frames = c["chunk_len"] * c["fps"]
    tok = frames * TOKENS_PER_FRAME.get(c["media_resolution"], 66) + 500
    pin, pout = PRICES.get(c["model"], (0.75, 3.75))
    cost = n * tok / 1e6 * pin + n * 900 / 1e6 * pout
    if c.get("mode") == "two_stage":
        # stage 2 is text-only: no frames in, but a second reply out
        cost += n * 900 / 1e6 * pin + n * 900 / 1e6 * pout
    return cost


def _cache_path(c, cid, gkey):
    """Keyed on the prompt AND the pixels AND the request settings -- no silent collisions."""
    s = (f"{c['prompt'].format(start=0.0)}|{cid}|{gkey}|{c['model']}|{c['fps']}"
         f"|{c['media_resolution']}|{c['thinking']}|{c['mode']}|{c.get('prompt2') or ''}")
    return os.path.join(detect.CACHE, hashlib.sha256(s.encode()).hexdigest()[:16] + ".json")


async def _one(client, sem, c, gkey, d, cid, start, stats):
    path = _cache_path(c, cid, gkey)
    if os.path.exists(path):
        stats["hits"] += 1
        return json.load(open(path))["events"]
    async with sem:
        kw = dict(temperature=0.0, response_mime_type="application/json",
                  response_schema=detect.SCHEMA)
        # thinking_level is a 3.x parameter. The 2.5 family rejects it outright with a 400, and
        # every clip fails -- which looks exactly like a model that cannot see, rather than a
        # request we built wrong. Send it only where it is supported.
        if not c["model"].startswith("gemini-2.5"):
            kw["thinking_config"] = types.ThinkingConfig(thinking_level=c["thinking"])
        if c["media_resolution"]:
            kw["media_resolution"] = c["media_resolution"]
        part = types.Part(
            inline_data=types.Blob(mime_type="video/mp4",
                                   data=open(os.path.join(d, f"{cid}.mp4"), "rb").read()),
            video_metadata=types.VideoMetadata(fps=c["fps"]))
        # 429s are the failure mode that matters here: three tries two seconds apart is far too
        # impatient for a quota reset, and a round that loses 100 chunks to rate limiting looks
        # exactly like a round whose config destroyed recall. Separating the two is the point --
        # a throttled round is not evidence about the config.
        for attempt in range(RETRIES):
            try:
                if c["mode"] == "two_stage":
                    # stage 1 sees the video and is deliberately unconstrained: no schema, no
                    # taxonomy. stage 2 sees only that text and does all the naming.
                    o = await client.aio.models.generate_content(
                        model=c["model"], contents=[part, c["prompt"].format(start=start)],
                        config=types.GenerateContentConfig(temperature=0.0))
                    ou = o.usage_metadata
                    stats["in"] += ou.prompt_token_count or 0
                    stats["out"] += ((ou.candidates_token_count or 0)
                                     + (ou.thoughts_token_count or 0))
                    r = await client.aio.models.generate_content(
                        model=c["model"],
                        contents=[c["prompt2"].format(start=start, obs=o.text or "")],
                        config=types.GenerateContentConfig(**kw))
                else:
                    r = await client.aio.models.generate_content(
                        model=c["model"], contents=[part, c["prompt"].format(start=start)],
                        config=types.GenerateContentConfig(**kw))
                break
            except Exception as e:
                throttled = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                if attempt == RETRIES - 1:
                    stats["fail"] += 1
                    stats["throttled"] += throttled
                    print(f"  {cid} failed: {type(e).__name__}: {str(e)[:80]}")
                    return []
                await asyncio.sleep(min(60.0, (8.0 if throttled else 2.0) * 2 ** attempt))
    u = r.usage_metadata
    stats["in"] += u.prompt_token_count or 0
    stats["out"] += (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
    try:
        events = json.loads(r.text)["events"]
    except Exception:
        stats["fail"] += 1
        return []
    for e in events:
        e["team"] = detect.SIDE_TO_TEAM.get(e.pop("side", None))
        e["chunk"], e["chunk_start"] = cid, start
    json.dump({"events": events}, open(path, "w"))
    return events


def run(cfg, concurrency=CONCURRENCY, verbose=True, only=None):
    """`only` is a list of chunk indices to send; the rest are skipped.

    Ranking several models over the whole match costs an order of magnitude more than ranking
    them on a sample, and orders them the same. The chunks are still cut for the whole match --
    extraction is cheap and cached -- only the API calls are restricted.
    """
    c = normalise(cfg)
    gkey = geometry_key(c)
    d, index = build_chunks(c, verbose=verbose)
    if only is not None:
        keep = {f"c{i:03d}" for i in only}
        index = {k: v for k, v in index.items() if k in keep}

    async def go():
        client = genai.Client(api_key=detect._api_key())
        sem = asyncio.Semaphore(concurrency)
        stats = {"in": 0, "out": 0, "hits": 0, "fail": 0, "throttled": 0}
        res = await asyncio.gather(*[_one(client, sem, c, gkey, d, cid, s, stats)
                                     for cid, s in sorted(index.items())])
        return [e for chunk in res for e in chunk], stats

    raw, stats = asyncio.run(go())
    pin, pout = PRICES.get(c["model"], (0.75, 3.75))
    stats["cost"] = stats["in"] / 1e6 * pin + stats["out"] / 1e6 * pout
    stats["n_chunks"] = len(index)
    stats["geometry"] = gkey
    # dedupe window must scale with chunk length, not stay pinned to the 30s default
    return dd.dedupe(raw, window=0.4), stats


if __name__ == "__main__":
    import ingest
    import metrics
    base = open(os.path.join(HERE, "notebook", "candidates", "prompt_005.txt")).read()
    for name, cfg in (("current", {"prompt": base}),
                      ("crop+HIGH", {"prompt": base, "crop": "1920:620:0:330",
                                     "media_resolution": "MEDIA_RESOLUTION_HIGH"})):
        c = normalise(cfg)
        print(f"{name:<12} geometry {geometry_key(c)}  {len(starts(c))} chunks  "
              f"est ${estimate_cost(c):.2f}")
