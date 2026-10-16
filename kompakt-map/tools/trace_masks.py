"""Exploratory tracing: extract coarse polygons from the stitched map screenshot."""
import sys
import cv2
import numpy as np

src = sys.argv[1]
out = sys.argv[2]
img = cv2.imread(src)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
b, g, r = [img[:, :, i].astype(int) for i in range(3)]

pink = (r > 200) & (b > 170) & (g < 215) & (r - g > 30)
white = (r > 235) & (g > 235) & (b > 235)
yellow = (r > 170) & (g > 165) & (b < 150) & (abs(r - g) < 45)

def clean(m, k=9):
    m = m.astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    return m

site = clean(~(pink | white), 15)
ys = clean(yellow, 7)
vis = img.copy()
for name, m, col, mina in (("site", site, (0, 0, 255), 200000), ("street", ys, (255, 0, 0), 3000)):
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in sorted(cnts, key=cv2.contourArea, reverse=True):
        a = cv2.contourArea(c)
        if a < mina:
            continue
        ap = cv2.approxPolyDP(c, 6, True)
        print(name, int(a), ap.reshape(-1, 2).tolist())
        cv2.polylines(vis, [ap], True, col, 3)
cv2.imwrite(out, vis)
