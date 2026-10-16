"""Trace each stage's parts (dance floor, roof, deck, screens, building) from the hi-res stitch.

Each part is grown by flood fill from hand-picked seed points on a colour-flattened copy of the
map, holes are filled, and the outline is simplified to a clean polygon. Result:
source/map/stage_parts.json  [{stage, part, style, pts:[[x,y],...]}] in reference coordinates.
Usage: python3 tools/trace_stages.py [--debug DIR]
"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIRES = os.path.join(ROOT, "source", "map", "hires.png")
OUT = os.path.join(ROOT, "source", "map", "stage_parts.json")
OX, OY, SC = 61, 19, 3

# stage, part, seeds (ref), colour tolerance, style (floor / roof / side / screen / struct)
PARTS = [
    ("sec3", "floor", [(940, 960), (900, 1060), (1000, 1050)], 40, "floor"),
    ("sec3", "roof", [(950, 1140), (1000, 1150), (900, 1160)], 52, "roof"),
    ("grand-central", "floor", [(1260, 1260), (1240, 1150), (1300, 1180)], 32, "floor"),
    ("grand-central", "stage", [(1140, 1195), (1140, 1225)], 40, "roof"),
    ("grand-central", "deck", [(1110, 1250)], 44, "side"),
    ("grand-central", "screen-l", [(1108, 1200)], 44, "screen"),
    ("grand-central", "screen-r", [(1170, 1250)], 44, "screen"),
    ("vertex", "floor", [(1270, 1000), (1320, 1040)], 36, "floor"),
    ("vertex", "top", [(1380, 990), (1295, 1057)], 40, "roof"),
    ("vertex", "side", [(1320, 1080), (1385, 1045)], 48, "side"),
    ("mind-melt", "body", [(1040, 470), (1100, 480), (960, 470), (1040, 420)], 44, "roof"),
    ("mind-melt", "screen-l", [(955, 440)], 40, "screen"),
    ("mind-melt", "screen-r", [(1145, 440)], 40, "screen"),
    ("isotropic", "floor", [(325, 940)], 40, "floor"),
    ("isotropic", "roof", [(280, 1020)], 48, "roof"),
    ("isotropic", "deck", [(240, 1060)], 44, "side"),
    ("halo-88", "building", [(415, 1075), (490, 1180)], 36, "struct"),
    ("fortune-row", "building", [(665, 1060), (590, 1160)], 40, "side"),
    ("iii-points-radio", "box", [(700, 940)], 44, "roof"),
    ("rc95", "floor", [(620, 1300)], 40, "floor"),
    ("rc95", "booth", [(560, 1380)], 44, "roof"),
    ("door-iv", "platform", [(850, 877)], 32, "struct"),
    ("door-iv", "building", [(890, 760)], 40, "side"),
    ("door-iv", "arch", [(940, 765), (1030, 765)], 32, "struct"),
    ("players-club", "building", [(855, 630)], 32, "struct"),
    ("444", "room", [(1290, 680)], 28, "struct"),
    ("s3qu3nce", "floor", [(530, 802)], 36, "roof"),
    ("s3qu3nce", "glass", [(530, 840)], 32, "struct"),
]
REACH = 130   # max distance (ref px) a part may extend from its seeds


def H(x, y):
    return int(round((x - OX) * SC)), int(round((y - OY) * SC))


def main():
    debug = sys.argv[sys.argv.index("--debug") + 1] if "--debug" in sys.argv else None
    cache = os.path.join(ROOT, "build", "hires_flat.png")
    if os.path.exists(cache):
        flat = cv2.imread(cache)
    else:
        img = cv2.imread(HIRES)
        flat = cv2.pyrMeanShiftFiltering(cv2.medianBlur(img, 7), 10, 16)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        cv2.imwrite(cache, flat)
    Hh, Ww = flat.shape[:2]
    out = []
    for stage, part, seeds, tol, style in PARTS:
        xs = [H(*s)[0] for s in seeds]
        ys = [H(*s)[1] for s in seeds]
        r = REACH * SC
        x0, y0 = max(min(xs) - r, 0), max(min(ys) - r, 0)
        x1, y1 = min(max(xs) + r, Ww), min(max(ys) + r, Hh)
        roi = flat[y0:y1, x0:x1].copy()
        mask = np.zeros((roi.shape[0] + 2, roi.shape[1] + 2), np.uint8)
        for sx, sy in zip(xs, ys):
            cv2.floodFill(roi, mask, (sx - x0, sy - y0), 0, (tol,) * 3, (tol,) * 3,
                          4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8))
        m = mask[1:-1, 1:-1]
        k = np.ones((9, 9), np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k, iterations=2)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cnts = [c for c in cnts if cv2.contourArea(c) > 400]
        if not cnts:
            print(f"{stage}/{part}: nothing traced")
            continue
        for c in cnts:
            ap = cv2.approxPolyDP(c, 1.4 * SC, True).reshape(-1, 2)
            pts = [[round((px + x0) / SC + OX, 1), round((py + y0) / SC + OY, 1)] for px, py in ap]
            out.append({"stage": stage, "part": part, "style": style, "pts": pts})
            print(f"{stage}/{part}: {len(pts)} pts, area {cv2.contourArea(c) / SC / SC:.0f} ref px2"
                  + ("  (hit reach limit?)" if (c[:, 0, 0].min() < 3 or c[:, 0, 1].min() < 3
                                                 or c[:, 0, 0].max() > roi.shape[1] - 4 or c[:, 0, 1].max() > roi.shape[0] - 4) else ""))
    json.dump(out, open(OUT, "w"), indent=0)


if __name__ == "__main__":
    main()
