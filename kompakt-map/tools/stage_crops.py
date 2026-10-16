"""Close-up crops of each stage area from the hi-res stitch with a labelled reference grid (every 20 px)."""
import os
import sys

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AREAS = {
    "mind-melt": (880, 370, 1220, 570), "players-club": (740, 520, 960, 690), "444-unforeseen": (1170, 590, 1320, 760),
    "s3quenc3": (500, 710, 680, 870), "door-iv": (760, 690, 1080, 890), "isotropic": (160, 890, 380, 1120),
    "radio-fortune-halo": (340, 900, 800, 1230), "rc95": (470, 1270, 680, 1440),
    "sector3": (800, 900, 1100, 1200), "vertex": (1220, 920, 1440, 1100), "grand-central": (1060, 1080, 1360, 1320),
}
h = cv2.imread(os.path.join(ROOT, "source", "map", "hires.png"))
out = sys.argv[1]
Z = 2.0  # output px per ref px
for name, (x0, y0, x1, y1) in AREAS.items():
    c = h[(y0 - 19) * 3:(y1 - 19) * 3, (x0 - 61) * 3:(x1 - 61) * 3]
    c = cv2.resize(c, ((x1 - x0) * int(Z), (y1 - y0) * int(Z)), interpolation=cv2.INTER_AREA)
    for v in range((x0 // 20 + 1) * 20, x1, 20):
        X = int((v - x0) * Z)
        cv2.line(c, (X, 0), (X, c.shape[0]), (255, 255, 255) if v % 100 else (0, 0, 255), 1)
        cv2.putText(c, str(v), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
    for v in range((y0 // 20 + 1) * 20, y1, 20):
        Y = int((v - y0) * Z)
        cv2.line(c, (0, Y), (c.shape[1], Y), (255, 255, 255) if v % 100 else (0, 0, 255), 1)
        cv2.putText(c, str(v), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
    cv2.imwrite(os.path.join(out, name + ".jpg"), c, [cv2.IMWRITE_JPEG_QUALITY, 88])
