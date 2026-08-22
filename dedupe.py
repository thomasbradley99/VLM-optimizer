"""Merge chunk overlaps: two events of the same type within 0.4s are one event seen twice. The
survivor is the one furthest from its chunk's edge -- an event seen 12s in had context on both
sides; the same event seen 0.3s in was caught mid-motion at the boundary."""
LEN = 30.0
WINDOW = 0.4


def _margin(e):
    off = e["t"] - e.get("chunk_start", e["t"])
    return min(off, LEN - off)


def dedupe(events, window=WINDOW):
    out = []
    for e in sorted(events, key=lambda x: x["t"]):
        prior = next((o for o in reversed(out)
                      if e["t"] - o["t"] <= window and o["type"] == e["type"]), None)
        if prior is None:
            out.append(e)
        elif _margin(e) > _margin(prior):
            out[out.index(prior)] = e
    return out
