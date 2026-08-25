"""Render the README's charts as SVG, one pair per figure for light and dark.

GitHub serves a README on either a light or a dark background and gives the image no say
in it, so each figure is emitted twice and selected with <picture media="...">. A single
image that assumes one background is unreadable on the other.

Colours are the validated categorical palette; the four-series set passes CVD separation,
the normal-vision floor and the lightness band in both modes (worst adjacent pair
ΔE 9.1 light / 8.4 dark). On light, aqua and yellow fall under 3:1 against the surface,
which obliges visible direct labels rather than a legend — every series is labelled at its
own line end, so identity never rests on colour alone.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VLM = os.path.join(HERE, "viewer", "vlm.json")
OUT = os.path.join(HERE, "docs")

NOISE = 0.028          # repeat-run F1 spread on an identical config

THEME = {
    "light": dict(surface="#fcfcfb", primary="#0b0b0b", secondary="#52514e",
                  muted="#898781", grid="#e1e0d9", axis="#c3c2b7",
                  series=["#2a78d6", "#eb6834", "#1baf7a", "#eda100"],
                  bar="#2a78d6", band="rgba(42,120,214,0.10)"),
    # GitHub's dark canvas is #0d1117, not the palette's default dark surface, and the
    # contrast checks are only meaningful against the surface actually rendered on.
    "dark": dict(surface="#0d1117", primary="#ffffff", secondary="#c3c2b7",
                 muted="#898781", grid="#2c2c2a", axis="#383835",
                 series=["#3987e5", "#d95926", "#199e70", "#c98500"],
                 bar="#3987e5", band="rgba(57,135,229,0.14)"),
}
FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif")


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def head(w, h, t):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}">'
            f'<rect width="{w}" height="{h}" fill="{t["surface"]}"/>')


def title(t, x, y, text, sub=None):
    s = (f'<text x="{x}" y="{y}" font-size="15" font-weight="600" '
         f'fill="{t["primary"]}">{esc(text)}</text>')
    if sub:
        s += (f'<text x="{x}" y="{y+19}" font-size="12" fill="{t["secondary"]}">'
              f'{esc(sub)}</text>')
    return s


def lineage_chart(data, mode):
    """Four optimiser lineages, F1 by round. The point is that they run independently,
    so each is its own series and each is labelled where it ends.

    x is the round's position within its own lineage, not the run's `n`. `n` is the
    mutator's iteration counter and carries sentinels — -1 for the seed, 99 for the
    hand-built runs that belong to no lineage — so plotting against it stretched the axis
    to 99 and drew lines between runs that never followed one another.
    """
    t = THEME[mode]
    W, H = 900, 430
    L, R, T, B = 62, 200, 78, 52
    runs = {}
    for r in data["runs"]:
        if r["n"] == 99:                 # hand-built, not a step in any lineage
            continue
        runs.setdefault(r["lineage"], []).append((r["n"], r["match"]["f1"]))
    order = ["main", "terse", "verbose", "blind"]
    names = {"main": "A \u00b7 main", "terse": "C \u00b7 terse",
             "verbose": "D \u00b7 verbose", "blind": "B \u00b7 blind"}
    seq = {k: [f for _, f in sorted(v)] for k, v in runs.items()}
    xmax = max(len(v) for v in seq.values()) - 1
    ylo, yhi = 0.26, 0.50

    def X(i):
        return L + i / xmax * (W - L - R)

    def Y(f):
        return T + (yhi - f) / (yhi - ylo) * (H - T - B)

    s = [head(W, H, t),
         title(t, L - 14, 28, "Four optimiser lineages, run blind of one another",
               "F1 after each round. Only 11 of 33 rounds moved the score by more than "
               "repeat-run noise \u2014 6 up, 5 down.")]
    for g in range(6):
        f = ylo + g * (yhi - ylo) / 5
        s.append(f'<line x1="{L}" y1="{Y(f):.1f}" x2="{W-R}" y2="{Y(f):.1f}" '
                 f'stroke="{t["grid"]}" stroke-width="1"/>')
        s.append(f'<text x="{L-10}" y="{Y(f)+4:.1f}" font-size="11" text-anchor="end" '
                 f'fill="{t["muted"]}">{f:.2f}</text>')
    # The noise band drawn to scale on the same axis: a gap shorter than this rectangle
    # is not a result. Stating that in a caption is weaker than showing the height.
    bh = Y(0) - Y(NOISE)
    by = Y(0.283)
    s.append(f'<rect x="{L}" y="{by-bh:.1f}" width="{W-L-R}" height="{bh:.1f}" '
             f'fill="{t["band"]}"/>')
    s.append(f'<text x="{W-R-8}" y="{by-bh-7:.1f}" font-size="11" text-anchor="end" '
             f'fill="{t["secondary"]}">repeat-run noise, \u00b1{NOISE:g} F1</text>')
    s.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" '
             f'stroke="{t["axis"]}" stroke-width="1"/>')
    for n in range(0, xmax + 1, 2):
        s.append(f'<text x="{X(n):.1f}" y="{H-B+18}" font-size="11" '
                 f'text-anchor="middle" fill="{t["muted"]}">{n}</text>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-14}" font-size="11" '
             f'text-anchor="middle" fill="{t["secondary"]}">round within its lineage</text>')

    # A legend in the right margin, plus a single letter at each line's end. Long labels
    # placed at the end of a short lineage land on top of the lineage that keeps going,
    # so the identity text lives outside the plot and only the letter sits on the data.
    for i, key in enumerate(order):
        pts = seq[key]
        col = t["series"][i]
        d = " ".join(("M" if j == 0 else "L") + f"{X(j):.1f},{Y(f):.1f}"
                     for j, f in enumerate(pts))
        s.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
        for j, f in enumerate(pts):
            s.append(f'<circle cx="{X(j):.1f}" cy="{Y(f):.1f}" r="4" fill="{col}" '
                     f'stroke="{t["surface"]}" stroke-width="2"/>')
        ex, ey = X(len(pts) - 1), Y(pts[-1])
        s.append(f'<text x="{ex+9:.1f}" y="{ey+4:.1f}" font-size="12" font-weight="700" '
                 f'fill="{t["primary"]}">{names[key][0]}</text>')

        ly = T + 6 + i * 46
        lx = W - R + 18
        s.append(f'<rect x="{lx}" y="{ly-9}" width="11" height="11" rx="2" fill="{col}"/>')
        s.append(f'<text x="{lx+18}" y="{ly:.0f}" font-size="12" font-weight="600" '
                 f'fill="{t["primary"]}">{names[key]}</text>')
        s.append(f'<text x="{lx+18}" y="{ly+16:.0f}" font-size="11" '
                 f'fill="{t["secondary"]}">{pts[0]:.3f} \u2192 {pts[-1]:.3f}'
                 f'{"  best " + format(max(pts), ".3f") if key == "main" else ""}</text>')
    return "".join(s) + "</svg>"


def bars(rows, mode, head_text, sub, note=None, fmt="{:.3f}"):
    """Horizontal bars, one hue: magnitude is carried by length, not colour."""
    t = THEME[mode]
    W = 900
    rowh, gap = 34, 8
    T, B, L, R = 74, 40, 156, 208
    H = T + len(rows) * (rowh + gap) + B
    vmax = max(v for _, v, _ in rows)
    s = [head(W, H, t), title(t, L - 108, 28, head_text, sub)]
    for i, (label, v, note2) in enumerate(rows):
        y = T + i * (rowh + gap)
        wpx = (W - L - R) * v / vmax
        s.append(f'<text x="{L-12}" y="{y+rowh/2+4:.0f}" font-size="13" '
                 f'text-anchor="end" fill="{t["primary"]}">{esc(label)}</text>')
        s.append(f'<rect x="{L}" y="{y}" width="{max(wpx,3):.1f}" height="{rowh}" '
                 f'rx="4" fill="{t["bar"]}"/>')
        s.append(f'<text x="{L+wpx+12:.1f}" y="{y+rowh/2+4:.0f}" font-size="13" '
                 f'font-weight="600" fill="{t["primary"]}">{fmt.format(v)}</text>')
        if note2:
            s.append(f'<text x="{L+wpx+60:.1f}" y="{y+rowh/2+4:.0f}" font-size="11" '
                     f'fill="{t["secondary"]}">{esc(note2)}</text>')
    if note:
        s.append(f'<text x="{L-108}" y="{H-14}" font-size="11" '
                 f'fill="{t["secondary"]}">{esc(note)}</text>')
    return "".join(s) + "</svg>"


def main():
    d = json.load(open(VLM))
    best = max(d["runs"], key=lambda r: r["match"]["f1"])
    os.makedirs(OUT, exist_ok=True)

    for mode in ("light", "dark"):
        w = lambda n, s: open(os.path.join(OUT, f"{n}-{mode}.svg"), "w").write(s)
        w("lineages", lineage_chart(d, mode))

        ladder = [(x["level"].replace("+", "and "), x["f1"], f'{x["matched"]} of 550')
                  for x in best["ladder"]]
        ladder[0] = ("time only", ladder[0][1], ladder[0][2])
        w("ladder", bars(ladder, mode,
                         "Where the pipeline actually fails",
                         f'Best run ({best["name"]}), each rung adding one more thing '
                         f'the model has to get right.',
                         "It finds the events. It cannot read the jersey."))

        types = sorted(best["types"], key=lambda x: -x["f1"])
        w("types", bars([(x["type"], x["f1"], f'{x["gt"]} events')
                         for x in types], mode,
                        "F1 by action type",
                        f'Best run ({best["name"]}), matched within 1.0 s and typed '
                        f'correctly.',
                        "Block is 9 events out of 550 — that bar is noise, not a finding."))
    print("wrote", len(os.listdir(OUT)), "svgs to docs/")


if __name__ == "__main__":
    main()
