"""Cut the annotated span into overlapping chunks; an existing file is never re-extracted.
640x360 at 5 fps is what we send the model anyway. Audio is dropped -- three other games are
audible at this venue and none of it is signal."""
import concurrent.futures as cf
import json
import os
import subprocess

VIDEO = os.path.join(os.path.dirname(__file__), "..", "volleyball-annotated", "full-001.mp4")
DIR = os.path.join(os.path.dirname(__file__), "chunks")
SPAN = (995.0, 4715.0)   # annotated span, padded; the 81.5 min recording is mostly warmup
LEN, OVERLAP = 30.0, 8.0
STRIDE = LEN - OVERLAP
FPS, WIDTH = 5, 640


def starts():
    """Stepping by STRIDE, extended until the last chunk's end covers SPAN[1]."""
    out, t = [], SPAN[0]
    while True:
        out.append(round(t, 3))
        if t + LEN >= SPAN[1]:
            return out
        t += STRIDE


def _extract(args):
    cid, start = args
    path = os.path.join(DIR, f"c{cid:03d}.mp4")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return False
    subprocess.run(["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-ss", str(start),
                    "-i", VIDEO, "-t", str(LEN), "-an",
                    "-vf", f"scale={WIDTH}:-2,fps={FPS}", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "30", path], check=True)
    return True


def build(workers=4):
    os.makedirs(DIR, exist_ok=True)
    index = {f"c{i:03d}": s for i, s in enumerate(starts())}
    with cf.ThreadPoolExecutor(workers) as ex:
        made = sum(ex.map(_extract, [(i, s) for i, s in enumerate(starts())]))
    with open(os.path.join(DIR, "index.json"), "w") as fh:
        json.dump(index, fh, indent=1)
    return index, made


if __name__ == "__main__":
    idx, made = build()
    print(f"{len(idx)} chunks ({made} extracted, {len(idx) - made} cached) in {DIR}")
