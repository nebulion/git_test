"""Warp the official map (hi-res stitch) into the transit-diagram frame: undo its slant so avenues
run horizontally and streets vertically. Output matches mockup/map-diagram.png pixel for pixel
(diagram VIEW at 2x), plus a side-by-side and an overlay.
Note: anything drawn with height in the original (stages, signs, lettering) leans after unslanting;
only the ground plane is straightened."""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from proj import K0, S0  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VX, VY, VW, VH = 360, 60, 1400, 1540   # diagram view (build_map.VIEW in diagram mode)
Z = 2                                   # output px per ground unit (same as the 2x diagram render)

h = cv2.imread(os.path.join(ROOT, "source", "map", "hires.png"))
# output pixel (i, j) -> ground (U, W) = (VX + i/Z, VY + j/Z) -> picture (U - K0 W, S0 U + W) -> hires 3*(p - (61, 19))
M = np.float32([[3 / Z, -3 * K0 / Z, 3 * VX - 3 * K0 * VY - 183],
                [3 * S0 / Z, 3 / Z, 3 * S0 * VX + 3 * VY - 57]])
out = cv2.warpAffine(h, M, (VW * Z, VH * Z), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_AREA,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
cv2.imwrite(os.path.join(ROOT, "mockup", "original-unslanted.jpg"), out, [cv2.IMWRITE_JPEG_QUALITY, 90])

d = cv2.imread(os.path.join(ROOT, "build", "diagram@2x.png"))
if d is not None:
    d = cv2.resize(d, (out.shape[1], out.shape[0]))
    side = np.full((out.shape[0], out.shape[1] * 2 + 60, 3), 255, np.uint8)
    side[:, :out.shape[1]] = out
    side[:, out.shape[1] + 60:] = d
    side = cv2.resize(side, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(ROOT, "mockup", "original-unslanted-vs-diagram.jpg"), side, [cv2.IMWRITE_JPEG_QUALITY, 88])
    blend = cv2.addWeighted(out, 0.45, d, 0.55, 0)
    cv2.imwrite(os.path.join(ROOT, "mockup", "original-unslanted-overlay.jpg"),
                cv2.resize(blend, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 86])
print(out.shape)
