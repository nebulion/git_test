"""Draw geometry from build_map.py (red) over the hi-res stitch for checking. Usage: overlay_check.py OUT.jpg [x0 y0 x1 y1 in ref coords]"""
import os
import runpy
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
g = runpy.run_path(os.path.join(ROOT, "tools", "build_map.py"), run_name="geometry")
h = cv2.imread(os.path.join(ROOT, "source", "map", "hires.png"))
F = 0.5
s = cv2.resize(h, None, fx=F, fy=F, interpolation=cv2.INTER_AREA)
s = (s * 0.55 + 255 * 0.45).astype(np.uint8)       # fade the artwork so the overlay stands out
to = lambda pts: np.int32([[(x - 61) * 3 * F, (y - 19) * 3 * F] for x, y in pts])  # noqa: E731
for name in g.get("CHECK_SHAPES", []):
    cv2.polylines(s, [to(g[name])], True, (0, 0, 255), 3)
for pts in g.get("BLOCKS", {}).values():
    cv2.polylines(s, [to(pts)], True, (0, 0, 255), 2)
for pts in g.get("FOOTPRINTS", {}).values():
    cv2.polylines(s, [to(pts)], True, (255, 0, 160), 3)
for x, y, *_ in g.get("CHECK_POINTS", []):
    X, Y = to([(x, y)])[0]
    cv2.circle(s, (int(X), int(Y)), 6, (0, 160, 0), -1)
# reference-coordinate grid every 50
for v in range(0, 1600, 50):
    X = int((v - 61) * 3 * F); Y = int((v - 19) * 3 * F)
    cv2.line(s, (X, 0), (X, s.shape[0]), (255, 180, 0) if v % 100 else (255, 120, 0), 1)
    cv2.line(s, (0, Y), (s.shape[1], Y), (255, 180, 0) if v % 100 else (255, 120, 0), 1)
    if v % 100 == 0:
        for k in range(0, 1600, 200):
            cv2.putText(s, str(v), (X + 3, int((k - 19) * 3 * F) + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 60, 0), 2)
            cv2.putText(s, str(v), (int((k - 61) * 3 * F) + 3, Y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 60, 0), 2)
if len(sys.argv) > 2:
    x0, y0, x1, y1 = [float(a) for a in sys.argv[2:6]]
    s = s[int((y0 - 19) * 1.5):int((y1 - 19) * 1.5), int((x0 - 61) * 1.5):int((x1 - 61) * 1.5)]
cv2.imwrite(sys.argv[1], s, [cv2.IMWRITE_JPEG_QUALITY, 85])
