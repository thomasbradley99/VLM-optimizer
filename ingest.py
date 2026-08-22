"""Parse the scout's CSV into canonical events. ACTION is mostly the generic `shooting`; the real
type lives in QUALIFIERS. Precedence below yields mutually exclusive types -- the asserts pin that
down. `error`/`point` are never standalone here, so they ride as flags rather than types."""
import csv
import os

CSV = os.path.join(os.path.dirname(__file__), "..", "volleyball-annotated",
                   "VEVA Impact 17-Blue (KE)-vs-TVC 17-Royal (OV)-05_31_2026 8_49 PM Actions.csv")

TYPES = ["serve", "receive", "dig", "set", "attack", "kill", "block"]
EXPECTED = {"serve": 118, "receive": 107, "dig": 86, "set": 47,
            "attack": 131, "kill": 52, "block": 9}


def timecode_to_seconds(tc):
    """HH:MM:SS:FF -> real elapsed seconds, frame field at 30 fps."""
    h, m, s, f = (int(x) for x in tc.split(":"))
    return h * 3600 + m * 60 + s + f / 30.0


def _event_type(action, quals):
    if action == "block":
        return "block"
    if action == "assist-2":
        return "set"
    if "serve" in quals:
        return "serve"
    if action == "receive":
        return "receive"
    if "dig" in quals:
        return "dig"
    if "kill" in quals:
        return "kill"
    if "attack" in quals:
        return "attack"
    return None


def load_events(path=CSV):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 553, f"expected 553 rows, got {len(rows)}"

    events = []
    for r in rows:
        if r["PLAYER"] == "ClockEvent":  # set-boundary marker, not a touch
            continue
        quals = {q for q in (r["QUALIFIERS"] or "").split(";") if q}
        etype = _event_type(r["ACTION"], quals)
        assert etype, f"unclassified row: {r}"
        events.append({"t": timecode_to_seconds(r["TIME"]), "type": etype,
                       "team": r["COLOR"], "number": r["NUMBER"],
                       "error": "error" in quals, "point": "1-point" in quals})

    assert len(events) == 550, f"expected 550 scored events, got {len(events)}"
    for t, n in EXPECTED.items():
        got = sum(e["type"] == t for e in events)
        assert got == n, f"{t}: expected {n}, got {got}"
    assert sum(e["error"] for e in events) == 66
    assert sum(e["point"] for e in events) == 117
    assert all(e["number"] and e["team"] in ("blue", "white") for e in events)
    events.sort(key=lambda e: e["t"])
    return events


if __name__ == "__main__":
    ev = load_events()
    print(f"553 parsed, {len(ev)} scored, span {ev[0]['t']:.2f}s -> {ev[-1]['t']:.2f}s")
    for t in TYPES:
        print(f"  {t:<8} {sum(e['type'] == t for e in ev):>4}")
    print(f"  {'error*':<8} {sum(e['error'] for e in ev):>4}\n  {'point*':<8} {sum(e['point'] for e in ev):>4}")
