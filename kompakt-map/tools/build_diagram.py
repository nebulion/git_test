"""Diagram-style variant of the map (for comparison): the same layout with the oblique skew removed,
so blocks are plain rectangles and every line is horizontal or vertical, like a transit diagram.
Stages become hatched markers at their real position; buildings and dance floors are left out.
Output: mockup/map-diagram.svg
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_map as bm  # noqa: E402
from plan import PARTS, LABEL_AT  # noqa: E402

U0, W0, SC = 380, 60, 1.0


def Q(u, w):
    return ((u - U0) * SC, (w - W0) * SC)


def uv(x, y):
    return bm.UV(x, y)


out = []
ROOT = bm.ROOT
W, H = 1360, 1460
BLOCKS = {"iso": (458, 846, 612, 1106), "a": (660, 881, 980, 1383), "b": (1024, 881, 1319, 1383),
          "c": (1363, 881, 1700, 1383), "s3": (701, 654, 862, 840), "e": (911, 408, 1484, 840),
          "lounge": (1068, 128, 1276, 396)}
for u0, w0, u1, w1 in BLOCKS.values():
    x0, y0 = Q(u0, w0)
    x1, y1 = Q(u1, w1)
    out.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="14" fill="url(#lawn)" stroke="#000" stroke-width="4"/>')
# stages: bounding box of each stage's parts as a hatched marker
stages = {}
for sid, part, style, pts in PARTS:
    if style != "stage":
        continue
    us, ws = zip(*[uv(*p) for p in pts])
    b = stages.setdefault(sid, [1e9, 1e9, -1e9, -1e9])
    b[0], b[1], b[2], b[3] = min(b[0], min(us)), min(b[1], min(ws)), max(b[2], max(us)), max(b[3], max(ws))
for sid, (u0, w0, u1, w1) in stages.items():
    x0, y0 = Q(u0, w0)
    x1, y1 = Q(u1, w1)
    out.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" rx="6" fill="url(#hatch)" stroke="#000" stroke-width="2.5"/>')
# icons (GA only)
for o in bm.ops:
    if o["o"] == "icon" and o.get("cat") != "vip":
        x, y = Q(*uv(o["x"], o["y"]))
        out.append(bm.svg_icon(o["k"], round(x, 1), round(y, 1), 15, o["st"]))
# street names
for t, u, w, rot in [("NW 5th Ave", 1150, 861, 0), ("NW 6th Ave", 800, 1404, 0), ("NW 23rd St", 1002, 1250, -90),
                     ("NW 22nd St", 1341, 1250, -90), ("NW 24th St", 636, 1000, -90), ("NW 25th St", 427, 980, -90)]:
    x, y = Q(u, w)
    out.append(bm.svg_text(round(x + (8 if rot else 0), 1), round(y + (0 if rot else 8), 1), t, "b6", 22, "#000", rot=rot))
# labels
for lb in bm.LABELS:
    if lb["kind"] != "stage":
        continue
    x, y = Q(*LABEL_AT[lb["id"]])
    w = bm.text_width(lb["t"], "b7", 24) + 30
    out.append(f'<rect x="{x - w / 2:.1f}" y="{y - 19:.1f}" width="{w:.1f}" height="38" rx="19" fill="#fff" stroke="#000" stroke-width="2.2"/>')
    out.append(bm.svg_text(round(x, 1), round(y + 8.6, 1), lb["t"], "b7", 24, "#000"))
head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><style>']
for key, f in bm.FONT_FILES.items():
    import base64
    head.append(f'@font-face{{font-family:"{key.upper()}";src:url(data:font/ttf;base64,'
                f'{base64.b64encode(open(os.path.join(bm.FONTS, f), "rb").read()).decode()})}}')
head.append("</style>" + bm.svg_defs() + f'<rect width="{W}" height="{H}" fill="#fff"/>')
with open(os.path.join(ROOT, "mockup", "map-diagram.svg"), "w") as fh:
    fh.write("\n".join(head + out + ["</svg>"]))
print("diagram ok")
