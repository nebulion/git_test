"""Trace the official III Points map into a pure black & white SVG.

Pipeline
  1. take the full-resolution source (stitched app screenshots, same art as the official map)
  2. flatten print texture/grain (mean-shift + median)
  3. classify every pixel black or white with colour rules
       dark ink, walls, yellow streets, small colourful discs (icons) -> black
       pink paper, green blocks, white/light fills, big colourful zones -> white
       big colourful zones keep their outline as a thin black edge
       inside tag boxes (stage names, sponsor signs) only dark ink stays black
  4. clean specks, upsample, vectorise with potrace
Outputs mockup/map-traced.svg, mockup/map-traced.png and app/assets/map_traced.json (path data).

Usage: python3 tools/trace_map.py [--debug DIR]
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source", "map", "hires.png")   # stitched zoom tiles, already cropped to VIEW
VIEW = (61, 19, 1516, 1895)       # same space as build_map.py
UP = 3                            # hires.png is 3x the reference resolution

# Tag boxes (picture space, x0, y0, x1, y1): fills turn white, ink stays black.
TAGS = []


def P(u, w, K=0.2586, S=0.044):
    return (u - K * w, S * u + w)


def tag(u, w, bw, bh, pad=4):
    x, y = P(u, w)
    TAGS.append((x - bw / 2 - pad, y - bh / 2 - pad, x + bw / 2 + pad, y + bh / 2 + pad))


for u, w, bw, bh in [(535, 938, 130, 36), (870, 957, 182, 36), (715, 1095, 104, 38), (895, 1285, 96, 38),
                     (1190, 962, 126, 38), (1515, 910, 104, 38), (1565, 1120, 178, 38), (752, 725, 132, 40),
                     (955, 540, 162, 36), (1055, 792, 104, 36), (1225, 470, 142, 40), (1395, 567, 84, 36),
                     (880, 1055, 166, 38), (1315, 800, 200, 64), (1255, 530, 164, 56), (1432, 718, 74, 58),
                     (1155, 155, 156, 38)]:
    tag(u, w, bw, bh)
# poster furniture in official-image coordinates -> map space
O = lambda x, y: (x * 1.404 + 61, y * 1.404 + 18.7)  # noqa: E731
for (x0, y0, x1, y1) in [(318, 42, 495, 75), (60, 48, 140, 76), (160, 186, 250, 212),     # date / MIAMI / 2026 tags
                         (370, 1035, 550, 1095)]:                                           # ENTRANCE sign
    a, b = O(x0, y0), O(x1, y1)
    TAGS.append((a[0], a[1], b[0], b[1]))


def street_mask(shape):
    """Street areas (255) from the grid geometry in build_map.py: block plates minus the blocks."""
    import runpy
    g = runpy.run_path(os.path.join(os.path.dirname(__file__), "build_map.py"), run_name="geometry")
    ox, oy = VIEW[0], VIEW[1]
    to = lambda pts: np.int32([[(px - ox) * UP, (py - oy) * UP] for px, py in pts])  # noqa: E731
    m = np.zeros(shape, np.uint8)
    for plate in ("SOUTH", "ISO", "NORTH_S3", "NORTH_E", "VIP_LOUNGE", "VIP_PLUS_PATH"):
        cv2.fillPoly(m, [to(g[plate])], 255)
    for pts in g["BLOCKS"].values():
        cv2.fillPoly(m, [to(pts)], 0)
    return cv2.dilate(m, np.ones((5 * UP, 5 * UP), np.uint8))


def classify(img):
    """Return a uint8 mask, 255 = black ink."""
    f = img.astype(np.float32)
    b, g, r = f[..., 0], f[..., 1], f[..., 2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    dark = lum < 95
    grey_wall = (s < 0.28) & (lum < 135)
    yellow = (h >= 40) & (h <= 66) & (s > 0.30) & (v > 140)                 # streets, sign boards
    pink = ((h >= 285) | (h <= 10)) & (s < 0.62) & (v > 175)                 # poster paper + halftone
    green = (h > 66) & (h < 165) & (v > 100) & ~((h > 150) & (s > 0.55))     # block lawns
    light = (s < 0.16) & (lum > 150)
    colourful = ~(dark | grey_wall | yellow | pink | green | light) & (s > 0.16)

    off = yellow & ~(street_mask(yellow.shape) > 0)  # yellow is a street only on the street grid ...
    n, lab, st, _ = cv2.connectedComponentsWithStats(off.astype(np.uint8), 8)
    keep = np.zeros(n, bool)
    keep[1:] = (st[1:, cv2.CC_STAT_AREA] < 5200 * UP * UP) & (st[1:, cv2.CC_STAT_AREA] > 900 * UP * UP) \
        & (np.abs(st[1:, cv2.CC_STAT_WIDTH] - st[1:, cv2.CC_STAT_HEIGHT]) < 0.25 * st[1:, cv2.CC_STAT_WIDTH])
    yellow = (yellow & ~off) | (keep[lab] & off)     # ... or a round icon disc (Lost & Found)
    ink = dark | grey_wall | yellow

    # colourful: small blobs are icon discs (black); big ones are zones/buildings (white, outlined)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(colourful.astype(np.uint8), 8)
    area = stats[:, cv2.CC_STAT_AREA]
    small = np.zeros(n, bool)
    small[1:] = area[1:] < 5200 * UP * UP
    disc = small[lab] & colourful
    zone = (~small[lab]) & colourful & (lab > 0)
    ink |= disc
    edge = cv2.morphologyEx(zone.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    ink |= edge & ~disc

    # tag boxes: fills (blue, yellow, white) go white, only real ink stays
    tagmask = np.zeros(ink.shape, bool)
    ox, oy = VIEW[0], VIEW[1]
    for x0, y0, x1, y1 in TAGS:
        X0, Y0 = int((x0 - ox) * UP), int((y0 - oy) * UP)
        X1, Y1 = int((x1 - ox) * UP), int((y1 - oy) * UP)
        tagmask[max(Y0, 0):Y1, max(X0, 0):X1] = True
    ink[tagmask] = (lum < 105)[tagmask]
    return (ink * 255).astype(np.uint8)


def clean(mask):
    k = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    # drop isolated specks of either colour
    for target in (255, 0):
        m = (mask == target).astype(np.uint8)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
        tiny = np.zeros(n, bool)
        tiny[1:] = stats[1:, cv2.CC_STAT_AREA] < 14 * UP * UP
        mask[tiny[lab] & (m > 0)] = 255 - target
    return mask


def potrace(mask):
    with tempfile.TemporaryDirectory() as td:
        pbm = os.path.join(td, "in.pbm")
        svg = os.path.join(td, "out.svg")
        cv2.imwrite(pbm, mask)  # potrace traces black pixels of the bitmap
        subprocess.run(["potrace", pbm, "-b", "svg", "--flat", "-t", "4", "-a", "1.0", "-O", "0.4",
                        "-u", "10", "-o", svg], check=True)
        return open(svg).read()


def main():
    debug = sys.argv[sys.argv.index("--debug") + 1] if "--debug" in sys.argv else None
    big = cv2.imread(SRC)
    x, y, w, hgt = VIEW
    big = cv2.medianBlur(big, 5)                      # kill the print grain
    big = cv2.pyrMeanShiftFiltering(big, 8, 20)       # flatten colour fields
    ink = clean(classify(big))
    ink = cv2.GaussianBlur(ink, (0, 0), 1.2)
    ink = (ink > 127).astype(np.uint8) * 255
    if debug:
        cv2.imwrite(os.path.join(debug, "trace_mask.png"), 255 - ink)
    bitmap = 255 - ink  # black ink on white paper for potrace
    raw = potrace(bitmap)

    # potrace path data, in units of 0.1 px of the 2x bitmap, with a flipped y transform
    m = re.search(r'<g transform="translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.]+),([-\d.]+)\)"', raw)
    tx, ty, sx, sy = map(float, m.groups())
    d = " ".join(re.findall(r' d="([^"]+)"', raw))
    # map path units -> picture space: X = x + (tx + sx*px)/UP, Y = y + (ty + sy*py)/UP
    a, b = sx / UP, sy / UP
    c, f = x + tx / UP, y + ty / UP
    doc = {"view": VIEW, "transform": [a, b, c, f], "d": d}
    with open(os.path.join(ROOT, "app", "assets", "map_traced.json"), "w") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {hgt}" width="{w}" height="{hgt}">'
           f'<rect x="{x}" y="{y}" width="{w}" height="{hgt}" fill="#fff"/>'
           f'<path transform="matrix({a} 0 0 {b} {c} {f})" fill="#000" fill-rule="nonzero" d="{d}"/></svg>')
    with open(os.path.join(ROOT, "mockup", "map-traced.svg"), "w") as fh:
        fh.write(svg)
    print(f"path data {len(d) // 1024} KB")


if __name__ == "__main__":
    main()
