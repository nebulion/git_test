"""Stitch zoomed-in app screenshots into one high-resolution festival map.

Each screenshot is registered (SIFT + RANSAC similarity transform) against the reference
full-map image source/map/screenshots-stitched.png, so tiles don't need to overlap each other.
Output: source/map/hires.png at SCALE x the reference resolution, in the same frame as VIEW
in build_map.py (x 61..1577, y 19..1914 of the reference). Uncovered areas fall back to the
upscaled reference; covered areas use the sharpest (most zoomed) tile available.

Usage: python3 tools/stitch_zoom.py [--debug DIR]
"""
import glob
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "source", "map", "screenshots-stitched.png")
TILES = sorted(glob.glob(os.path.join(ROOT, "source", "zoom", "*.png")))
OUT = os.path.join(ROOT, "source", "map", "hires.png")
VIEW = (61, 19, 1516, 1895)
SCALE = 3
TOP, BOTTOM = 430, 2330          # app chrome (status bar, header, home bar) on 1080x2424 screenshots
# screenshots with the iOS screenshot thumbnail / share bar covering the lower part
BOTTOM_OVERRIDE = {"batch2-04.png": 1640, "batch2-10.png": 1640}


def main():
    debug = sys.argv[sys.argv.index("--debug") + 1] if "--debug" in sys.argv else None
    ref = cv2.imread(REF)
    sift = cv2.SIFT_create(nfeatures=40000)
    gref = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    kr, dr = sift.detectAndCompute(gref, None)
    matcher = cv2.FlannBasedMatcher({"algorithm": 1, "trees": 5}, {"checks": 64})

    vx, vy, vw, vh = VIEW
    W, H = vw * SCALE, vh * SCALE
    base = cv2.resize(ref[vy:vy + vh, vx:vx + vw], (W, H), interpolation=cv2.INTER_CUBIC)
    canvas = base.copy()
    best = np.zeros((H, W), np.float32)      # zoom level of the tile currently painted per pixel
    report = []
    for path in TILES:
        tile = cv2.imread(path)
        if tile is None:
            continue
        tile = tile[TOP:BOTTOM_OVERRIDE.get(os.path.basename(path), BOTTOM)]
        g = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
        # match at roughly reference scale for robustness, then refine nothing: similarity is enough
        small = cv2.resize(g, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        kt, dt = sift.detectAndCompute(small, None)
        name = os.path.basename(path)
        if dt is None or len(kt) < 20:
            report.append(f"{name}: too few features (plain background) - skipped")
            continue
        pairs = matcher.knnMatch(dt, dr, k=2)
        good = [m for m, n in (p for p in pairs if len(p) == 2) if m.distance < 0.72 * n.distance]
        if len(good) < 12:
            report.append(f"{name}: {len(good)} matches - skipped")
            continue
        src = np.float32([kt[m.queryIdx].pt for m in good]) * 2.0      # back to full tile pixels
        dst = np.float32([kr[m.trainIdx].pt for m in good])
        M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0,
                                             maxIters=5000, confidence=0.999)
        if M is None or inl.sum() < 12:
            report.append(f"{name}: no consistent transform - skipped")
            continue
        s = float(np.hypot(M[0, 0], M[1, 0]))       # reference px per tile px
        zoom = 1.0 / s
        # tile -> canvas: canvas = SCALE * (M @ tile - view origin)
        C = M.copy()
        C[:, 2] -= (vx, vy)
        C *= SCALE
        warped = cv2.warpAffine(tile, C, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
        mask = cv2.warpAffine(np.full(tile.shape[:2], 255, np.uint8), C, (W, H), flags=cv2.INTER_NEAREST)
        mask = cv2.erode(mask, np.ones((5, 5), np.uint8)) > 0
        take = mask & (zoom >= best - 0.05)
        canvas[take] = warped[take]
        best[take] = zoom
        report.append(f"{name}: {int(inl.sum())}/{len(good)} inliers, zoom {zoom:.2f}x, "
                      f"at ref ({M[0, 2]:.0f},{M[1, 2]:.0f})")
    cv2.imwrite(OUT, canvas)
    # gaps: uncovered blobs inside the poster (ignore thin seams)
    gap = ((best == 0) * 255).astype(np.uint8)
    gap = cv2.morphologyEx(gap, cv2.MORPH_OPEN, np.ones((9 * SCALE, 9 * SCALE), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(gap, 8)
    for i in range(1, n):
        x0, y0, w0, h0, a = st[i]
        if a < (40 * SCALE) ** 2:
            continue
        print(f"GAP ref x {x0 / SCALE + vx:.0f}-{(x0 + w0) / SCALE + vx:.0f}, y {y0 / SCALE + vy:.0f}-{(y0 + h0) / SCALE + vy:.0f}, "
              f"{a / SCALE / SCALE:.0f} px2")
    cov = (best > 0).mean()
    print("\n".join(report))
    print(f"coverage by zoomed tiles: {cov:.0%} of the poster; output {W}x{H} -> {OUT}")
    if debug:
        vis = cv2.resize(canvas, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        cov_img = cv2.resize(((best > 0) * 255).astype(np.uint8), (W // 4, H // 4))
        vis[cov_img == 0] = (vis[cov_img == 0] * 0.35).astype(np.uint8)
        cv2.imwrite(os.path.join(debug, "hires_coverage.png"), vis)


if __name__ == "__main__":
    main()
