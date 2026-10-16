"""Find every facility icon on the hi-res map and identify it against the legend's own icons.

Writes source/map/icons_detected.json: [{type, x, y, r, dist}] in reference coordinates
(the space build_map.py uses). Usage: python3 tools/detect_icons.py [--debug DIR]
"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIRES = os.path.join(ROOT, "source", "map", "hires.png")
OUT = os.path.join(ROOT, "source", "map", "icons_detected.json")
F = 0.5                       # work at half the hi-res size (1.5 px per reference px)
OX, OY, SC = 61, 19, 3        # hires pixel = (ref - origin) * 3
LEGEND = [  # column-major, as printed
    "firstaid", "accessible", "lockers", "food",
    "water", "vipwater", "vipupgrade", "vipconcierge",
    "vipbar", "vipfood", "merch", "table",
    "info", "tickets", "willcall", "boxoffice",
    "lostfound", "restroom", "viprestroom", "gaplusrestroom",
]
N = 40


def descriptor(img, x, y, r):
    """Disc contents resampled to N x N in Lab, outside the disc zeroed."""
    r = r * 0.86
    M = np.float32([[2 * r / N, 0, x - r], [0, 2 * r / N, y - r]])
    patch = cv2.warpAffine(img, M, (N, N), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_AREA)
    lab = cv2.cvtColor(patch, cv2.COLOR_BGR2LAB).astype(np.float32)
    yy, xx = np.mgrid[:N, :N]
    mask = ((xx - N / 2 + .5) ** 2 + (yy - N / 2 + .5) ** 2) <= (N / 2) ** 2
    lab[~mask] = 0
    return lab, mask


def main():
    debug = sys.argv[sys.argv.index("--debug") + 1] if "--debug" in sys.argv else None
    s = cv2.resize(cv2.imread(HIRES), None, fx=F, fy=F, interpolation=cv2.INTER_AREA)
    g = cv2.medianBlur(cv2.cvtColor(s, cv2.COLOR_BGR2GRAY), 5)
    legend_top = int((1585 - OY) * SC * F)

    leg = cv2.HoughCircles(g[legend_top:], cv2.HOUGH_GRADIENT, dp=1, minDist=30, param1=120, param2=30,
                           minRadius=14, maxRadius=30)[0]
    leg[:, 1] += legend_top
    # 5 columns x 4 rows: sort by x into columns, then by y
    leg = leg[np.argsort(leg[:, 0])]
    if len(leg) != 20:
        print("legend circles found:", len(leg))
    cols = [leg[i * 4:(i + 1) * 4] for i in range(5)]
    tmpl = []
    for col in cols:
        for x, y, r in col[np.argsort(col[:, 1])]:
            tmpl.append(descriptor(s, x, y, r))

    found = cv2.HoughCircles(g[:legend_top], cv2.HOUGH_GRADIENT, dp=1, minDist=40, param1=120, param2=38,
                             minRadius=26, maxRadius=44)[0]
    out = []
    for x, y, r in found.tolist():
        d, m = descriptor(s, x, y, r)
        dists = [float(np.sqrt(((d - t) ** 2)[m].mean())) for t, _ in tmpl]
        order = np.argsort(dists)
        out.append({"type": LEGEND[order[0]], "alt": LEGEND[order[1]], "dist": round(dists[order[0]], 1),
                    "margin": round(dists[order[1]] - dists[order[0]], 1),
                    "x": round(x / F / SC + OX, 1), "y": round(y / F / SC + OY, 1), "r": round(r / F / SC, 1)})
    out.sort(key=lambda o: (o["y"], o["x"]))
    json.dump(out, open(OUT, "w"), indent=1)
    for o in out:
        print(f'{o["type"]:15s} ({o["x"]:7.1f},{o["y"]:7.1f}) d={o["dist"]:5.1f} next={o["alt"]} +{o["margin"]}')
    if debug:
        vis = s.copy()
        for o in out:
            X, Y = int((o["x"] - OX) * SC * F), int((o["y"] - OY) * SC * F)
            cv2.circle(vis, (X, Y), int(o["r"] * SC * F), (0, 0, 255) if o["dist"] > 28 else (0, 160, 0), 3)
            cv2.putText(vis, o["type"], (X - 40, Y + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 5)
            cv2.putText(vis, o["type"], (X - 40, Y + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(debug, "icons_labeled.jpg"), vis[:legend_top])


if __name__ == "__main__":
    main()
