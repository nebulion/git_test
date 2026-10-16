"""Find the long black outline segments (block/street borders) in the stitched map."""
import sys
import cv2
import numpy as np

img = cv2.imread(sys.argv[1])
dark = (img.max(axis=2) < 70).astype(np.uint8) * 255
lines = cv2.HoughLinesP(dark, 1, np.pi / 720, threshold=120, minLineLength=int(sys.argv[3]), maxLineGap=12)
vis = img.copy()
segs = []
for l in lines.reshape(-1, 4):
    x1, y1, x2, y2 = map(int, l)
    segs.append((x1, y1, x2, y2))
    cv2.line(vis, (x1, y1), (x2, y2), (0, 0, 255), 3)
for s in sorted(segs, key=lambda s: -np.hypot(s[2] - s[0], s[3] - s[1])):
    print(s, round(float(np.degrees(np.arctan2(s[3] - s[1], s[2] - s[0]))), 1))
cv2.imwrite(sys.argv[2], vis)
