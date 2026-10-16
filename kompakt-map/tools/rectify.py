"""Warp the stitched screenshot into the map's grid space (u right, w down) for tracing.

Picture space from grid space: x = u - K*w, y = S*u + w.
"""
import sys
import cv2
import numpy as np

K, S = 0.2586, 0.044
U0, W0 = 100, 0          # grid-space origin of the output image
img = cv2.imread(sys.argv[1])
W, H = 1800, 1950
# output pixel (i, j) -> grid (u, w) = (U0 + i, W0 + j) -> picture (x, y)
M = np.float32([[1, -K, U0 - K * W0], [S, 1, S * U0 + W0]])
out = cv2.warpAffine(img, M, (W, H), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR, borderValue=(255, 255, 255))
for u in range(0, W + U0, 50):
    c = (255, 0, 0) if u % 100 == 0 else (255, 170, 170)
    cv2.line(out, (u - U0, 0), (u - U0, H), c, 1)
    if u % 100 == 0:
        for w in range(0, H, 200):
            cv2.putText(out, str(u), (u - U0 + 2, w + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
for w in range(0, H, 50):
    c = (0, 0, 255) if w % 100 == 0 else (170, 170, 255)
    cv2.line(out, (0, w), (W, w), c, 1)
    if w % 100 == 0:
        for u in range(0, W, 200):
            cv2.putText(out, str(w), (u + 2, w - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
cv2.imwrite(sys.argv[2], out)
