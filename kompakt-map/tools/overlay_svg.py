"""Overlay the B/W map's edges (red) on the faded official map, per region, for review.
Usage: overlay_svg.py OUTDIR   (expects build/map@2x.png from render_svg.js ... 2)"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from build_map import VIEW  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = {
    "1-lounge-vip-plus": (820, 100, 1330, 430), "2-players-mind-melt": (720, 380, 1340, 700),
    "3-s3quenc3-door-iv": (440, 560, 1100, 900), "4-444-gallery": (1060, 560, 1520, 920),
    "5-isotropic-halo": (140, 860, 780, 1240), "6-rc95-entrances": (140, 1200, 900, 1580),
    "7-sector3": (740, 860, 1120, 1460), "8-vertex-grand-central": (1080, 860, 1520, 1460),
}
h = cv2.imread(os.path.join(ROOT, "source", "map", "hires.png"))
m = cv2.imread(os.path.join(ROOT, "build", "map@2x.png"), cv2.IMREAD_GRAYSCALE)
edges = cv2.Canny(m, 50, 150)
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
for name, (x0, y0, x1, y1) in REGIONS.items():
    Z = 2
    a = cv2.resize(h[(y0 - 19) * 3:(y1 - 19) * 3, (x0 - 61) * 3:(x1 - 61) * 3], ((x1 - x0) * Z, (y1 - y0) * Z), interpolation=cv2.INTER_AREA)
    a = (a * 0.55 + 115).astype(np.uint8)
    e = np.zeros((y1 - y0) * 2 * (x1 - x0) * 2, np.uint8).reshape((y1 - y0) * 2, (x1 - x0) * 2)
    sy0, sx0 = (y0 - VIEW[1]) * 2, (x0 - VIEW[0]) * 2
    src = edges[max(sy0, 0):max(sy0 + e.shape[0], 0), max(sx0, 0):max(sx0 + e.shape[1], 0)]
    e[max(-sy0, 0):max(-sy0, 0) + src.shape[0], max(-sx0, 0):max(-sx0, 0) + src.shape[1]] = src
    e = cv2.dilate(e, np.ones((2, 2), np.uint8)) > 0
    a[e[:a.shape[0], :a.shape[1]]] = (0, 0, 235)
    cv2.imwrite(os.path.join(out, name + ".jpg"), a, [cv2.IMWRITE_JPEG_QUALITY, 85])
print("ok")
