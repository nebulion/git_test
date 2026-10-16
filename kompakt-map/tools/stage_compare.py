"""Per-stage check sheet: official artwork (left) vs the B/W redraw (right), same area and scale."""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from stage_crops import AREAS  # noqa: E402
from build_map import VIEW  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
h = cv2.imread(os.path.join(ROOT, "source", "map", "hires.png"))
m = cv2.imread(os.path.join(ROOT, "build", "map@2x.png"))
Z = 2
rows = []
for name in sys.argv[2:] or list(AREAS):
    x0, y0, x1, y1 = AREAS[name]
    a = cv2.resize(h[(y0 - 19) * 3:(y1 - 19) * 3, (x0 - 61) * 3:(x1 - 61) * 3], ((x1 - x0) * Z, (y1 - y0) * Z), interpolation=cv2.INTER_AREA)
    b = m[(y0 - VIEW[1]) * 2:(y1 - VIEW[1]) * 2, (x0 - VIEW[0]) * 2:(x1 - VIEW[0]) * 2]
    b = cv2.resize(b, (a.shape[1], a.shape[0]))
    row = np.full((a.shape[0] + 30, a.shape[1] * 2 + 12, 3), 255, np.uint8)
    row[30:, :a.shape[1]] = a
    row[30:, a.shape[1] + 12:] = b
    cv2.putText(row, name, (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    rows.append(row)
W = max(r.shape[1] for r in rows)
sheet = np.full((sum(r.shape[0] + 14 for r in rows), W, 3), 255, np.uint8)
y = 0
for r in rows:
    sheet[y:y + r.shape[0], :r.shape[1]] = r
    y += r.shape[0] + 14
cv2.imwrite(sys.argv[1], sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
print(sheet.shape)
