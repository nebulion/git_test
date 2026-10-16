"""Review sheet: each stage close-up (left) next to the same crop with traced parts drawn on it (right)."""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from stage_crops import AREAS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COL = {"floor": (0, 170, 0), "roof": (0, 0, 230), "side": (220, 0, 200), "screen": (230, 140, 0), "struct": (0, 140, 230)}
parts = json.load(open(os.path.join(ROOT, "source", "map", "stage_parts.json")))
h = cv2.imread(os.path.join(ROOT, "source", "map", "hires.png"))
only = sys.argv[2:] or list(AREAS)
Z = 2
tiles = []
for name in only:
    x0, y0, x1, y1 = AREAS[name]
    c = cv2.resize(h[(y0 - 19) * 3:(y1 - 19) * 3, (x0 - 61) * 3:(x1 - 61) * 3], ((x1 - x0) * Z, (y1 - y0) * Z), interpolation=cv2.INTER_AREA)
    d = (c * 0.45 + 140).astype(np.uint8)
    for p in parts:
        pts = np.int32([[(x - x0) * Z, (y - y0) * Z] for x, y in p["pts"]])
        cv2.polylines(d, [pts], True, COL[p["style"]], 3)
    cv2.putText(d, name, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    t = np.full((max(c.shape[0], 1), c.shape[1] * 2 + 10, 3), 255, np.uint8)
    t[:, :c.shape[1]] = c
    t[:, c.shape[1] + 10:] = d
    tiles.append(t)
W = max(t.shape[1] for t in tiles)
sheet = np.full((sum(t.shape[0] + 10 for t in tiles), W, 3), 255, np.uint8)
y = 0
for t in tiles:
    sheet[y:y + t.shape[0], :t.shape[1]] = t
    y += t.shape[0] + 10
cv2.imwrite(sys.argv[1], sheet, [cv2.IMWRITE_JPEG_QUALITY, 82])
