"""Classify detected border segments into the map's oblique grid (u along avenues, v along streets)."""
import sys
import cv2
import numpy as np

K = 0.2586   # dx per unit of -dy along cross streets (75.5 degrees)
S = 0.044    # dy per dx along avenues (2.5 degrees)

def uv(x, y):
    u = (x + K * y) / (1 + K * S)
    return u, S * u - y

img = cv2.imread(sys.argv[1])
dark = (img.max(axis=2) < 70).astype(np.uint8) * 255
lines = cv2.HoughLinesP(dark, 1, np.pi / 720, threshold=60, minLineLength=int(sys.argv[2]), maxLineGap=8).reshape(-1, 4)
us, vs = [], []
for x1, y1, x2, y2 in lines:
    ang = np.degrees(np.arctan2(y2 - y1, x2 - x1))
    a, b = uv(x1, y1), uv(x2, y2)
    L = np.hypot(x2 - x1, y2 - y1)
    if -79 < ang < -72 or 101 < ang < 108:
        us.append((round((a[0] + b[0]) / 2), round(min(a[1], b[1])), round(max(a[1], b[1])), int(L)))
    elif abs(ang) < 5 and y1 < 1600:
        vs.append((round((a[1] + b[1]) / 2), round(min(a[0], b[0])), round(max(a[0], b[0])), int(L)))
print("constant-u (cross-street edges): u, v-range, len")
for r in sorted(us):
    print("  ", r)
print("constant-v (avenue edges): v, u-range, len")
for r in sorted(vs):
    print("  ", r)
