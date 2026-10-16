"""Build the black & white III Points 2026 festival map.

Outputs:
  app/assets/map.json   display list rendered by the Android app (MapView)
  mockup/map.svg        the same drawing as SVG (reference / mockup)
  app/assets/icons.json pictograms shared by both renderers

Geometry was traced from the official map (iiipoints.com/assets/campaign/festival-map-2026-1080.webp)
and full-resolution app screenshots. Coordinates are in the stitched-screenshot pixel space; the
official image maps into it as x*1.404+61, y*1.404+18.7. The ground plane is an oblique grid:
a ground point (u, w) sits at picture (u - K*w, S*u + w).
"""
import base64
import json
import math
import os
import sys

from PIL import ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from icons import ICONS, LEGEND  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "app", "assets", "fonts")
K, S = 0.2586, 0.044
STREET_ANGLE = -math.degrees(math.atan2(1, K))      # cross streets, about -75.5 degrees
AVENUE_ANGLE = math.degrees(math.atan(S))           # avenues, about 2.5 degrees
VIEW = (61, 19, 1516, 1895)                         # x, y, w, h of the whole poster
WALL = (7, 56)                                       # extrusion of the raised city blocks

FONT_FILES = {
    "bc8": "BarlowCondensed-800.ttf",
    "bc7": "BarlowCondensed-700.ttf",
    "bc6i": "BarlowCondensed-600i.ttf",
    "b6": "Barlow-600.ttf",
    "b7": "Barlow-700.ttf",
}
_fonts = {}


def text_width(text, font, size):
    key = (font, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONTS, FONT_FILES[font]), size=size * 4)
    return _fonts[key].getlength(text) / 4.0


def P(u, w):
    return (round(u - K * w, 1), round(S * u + w, 1))


def rect_uv(u0, w0, u1, w1):
    return [P(u0, w0), P(u1, w0), P(u1, w1), P(u0, w1)]


def flat(pts):
    out = []
    for x, y in pts:
        out += [round(x, 1), round(y, 1)]
    return out


ops = []        # display list
hits = []       # tap targets


def poly(pts, fill="w", stroke=0, color="b"):
    ops.append({"o": "poly", "p": flat(pts), "f": fill, "s": stroke, "c": color})


def line(pts, stroke=2, color="b", dash=None):
    op = {"o": "line", "p": flat(pts), "s": stroke, "c": color}
    if dash:
        op["d"] = dash
    ops.append(op)


def text(x, y, t, font="bc8", size=24, color="b", align="c", rot=0, fit=None):
    op = {"o": "text", "x": round(x, 1), "y": round(y, 1), "t": t, "font": font, "sz": size, "c": color, "a": align}
    if rot:
        op["r"] = round(rot, 2)
    if fit:
        op["fit"] = fit
    ops.append(op)


def circle(x, y, r, fill="b", stroke=0, color="b"):
    ops.append({"o": "circle", "x": round(x, 1), "y": round(y, 1), "r": r, "f": fill, "s": stroke, "c": color})


def rect(x, y, w, h, fill="w", stroke=0, color="b", rx=0, rot=0):
    op = {"o": "rect", "x": round(x, 1), "y": round(y, 1), "w": w, "h": h, "f": fill, "s": stroke, "c": color, "rx": rx}
    if rot:
        op["r"] = round(rot, 2)
    ops.append(op)


def icon(kind, x, y, style="ga", r=22, hit=None):
    ops.append({"o": "icon", "k": kind, "x": round(x, 1), "y": round(y, 1), "r": r, "st": style})
    if hit:
        hits.append({"id": hit, "x": round(x - r, 1), "y": round(y - r, 1), "w": 2 * r, "h": 2 * r})


def wall(pts):
    """Visible side walls of a raised block: sweep the outline along WALL."""
    ex, ey = WALL
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        poly([a, b, (b[0] + ex, b[1] + ey), (a[0] + ex, a[1] + ey)], fill="b")
    poly([(x + ex, y + ey) for x, y in pts], fill="b")


def street_text(x, y, t, on_street, rot):
    text(x, y + 8, t, font="bc6i", size=27, color="w" if on_street else "b", rot=rot)


def label(x, y, t, w, h, kind="stage", hit=None, size=None, sub=None):
    """Stage tags: white box, black frame and offset shadow (the original's blue tags).
    Sponsor / attraction tags (yellow on the original) are inverted: black box, white type."""
    if kind == "stage":
        rect(x - w / 2 + 5, y - h / 2 + 5, w, h, fill="b")
        rect(x - w / 2, y - h / 2, w, h, fill="w", stroke=3)
        fg = "b"
    else:
        rect(x - w / 2, y - h / 2, w, h, fill="b", stroke=3, color="b")
        fg = "w"
    size = size or round(h * (0.46 if sub else 0.78))
    if sub:
        text(x, y - h * 0.04, t, size=size, color=fg, fit=w - 12)
        text(x, y + h * 0.34, sub, font="bc7", size=round(size * 0.8), color=fg, fit=w - 12)
    else:
        text(x, y + size * 0.36, t, size=size, color=fg, fit=w - 12)
    if hit:
        hits.append({"id": hit, "x": round(x - w / 2, 1), "y": round(y - h / 2, 1), "w": w, "h": h})


def arrow(x0, y0, x1, y1, color="w", width=3, head=9):
    line([(x0, y0), (x1, y1)], stroke=width, color=color)
    ang = math.atan2(y1 - y0, x1 - x0)
    a1, a2 = ang + math.radians(150), ang - math.radians(150)
    poly([(x1, y1), (x1 + head * math.cos(a1), y1 + head * math.sin(a1)),
          (x1 + head * math.cos(a2), y1 + head * math.sin(a2))], fill=color)


def tree(x, y, s=1.0):
    """Picture-space tree: trunk base at (x, y)."""
    line([(x, y), (x, y - 16 * s)], stroke=3.2 * s)
    circle(x, y - 24 * s, 12 * s, fill="b", stroke=2 * s, color="w")
    circle(x - 7 * s, y - 17 * s, 7.5 * s, fill="b", stroke=2 * s, color="w")
    circle(x + 7 * s, y - 18 * s, 7.5 * s, fill="b", stroke=2 * s, color="w")


def stage_box(pts_top, h):
    """A simple extruded stage structure drawn in outline."""
    base = [(x, y + h) for x, y in pts_top]
    for i in range(len(pts_top)):
        a, b = pts_top[i], pts_top[(i + 1) % len(pts_top)]
        poly([a, b, base[(i + 1) % len(pts_top)], base[i]], fill="w", stroke=2)
    poly(pts_top, fill="h", stroke=2)


# --------------------------------------------------------------------------------------------
# Ground plane
# --------------------------------------------------------------------------------------------
SOUTH = [P(612, 840), P(1700, 840), P(1700, 1425), P(612, 1425)]          # five south blocks + avenues
ISO = [P(452, 840), P(612, 840), P(612, 1112), P(452, 1112)]              # Isotropic corner lot
NORTH_S3 = [P(695, 648), P(868, 648), P(868, 840), P(695, 840)]           # S3QUENC3 lot
NORTH_E = [P(868, 402), P(1490, 402), P(1490, 840), P(868, 840)]          # Players Club / Mind Melt block
VIP_LOUNGE = [P(1062, 122), P(1282, 122), P(1282, 402), P(1062, 402)]
VIP_PLUS_PATH = [P(872, 191), P(918, 191), P(918, 402), P(872, 402)]

for shape in (SOUTH, ISO, NORTH_E, VIP_LOUNGE):
    wall(shape)

# streets (black) under the blocks (white)
for shape in (SOUTH, ISO, NORTH_S3, NORTH_E, VIP_LOUNGE, VIP_PLUS_PATH):
    poly(shape, fill="b")

BLOCKS = {
    "iso": [P(458, 846), P(612, 846), P(612, 1106), P(458, 1106)],
    "a": rect_uv(660, 881, 980, 1383),
    "b": rect_uv(1024, 881, 1319, 1383),
    "c": rect_uv(1363, 881, 1700, 1383),
    "s3": rect_uv(701, 654, 862, 840),
    "e": rect_uv(911, 408, 1484, 840),
    "lounge": rect_uv(1068, 128, 1276, 396),
}
for key, pts in BLOCKS.items():
    poly(pts, fill="w", stroke=3)

# thin street lines on the open lots north of NW 5th Ave
for u in (402, 450, 647, 694):
    line([P(u, 560), P(u, 840)], stroke=2.5)

# --------------------------------------------------------------------------------------------
# Stage structures and features (outline drawings)
# --------------------------------------------------------------------------------------------
# Sector 3 stage field (orange blob on the original) - dashed outline
poly([P(1105, 890), P(1290, 890), P(1305, 1000), P(1290, 1100), P(1175, 1112), P(1110, 1050)], fill="w", stroke=0)
line([P(1105, 890), P(1290, 890), P(1305, 1000), P(1290, 1100), P(1175, 1112), P(1110, 1050), P(1105, 890)],
     stroke=2.5, dash=[10, 7])
stage_box([P(1150, 1075), P(1290, 1075), P(1290, 1100), P(1150, 1100)], 28)
# Grand Central dance floor (light ellipse) - dashed ring and stage screen
ops.append({"o": "ellipse", "x": P(1560, 1150)[0], "y": P(1560, 1150)[1], "rx": 130, "ry": 72, "f": "n", "s": 2.5, "c": "b", "d": [10, 7]})
stage_box([P(1460, 1150), P(1512, 1150), P(1512, 1185), P(1460, 1185)], 50)
# Vertex L-shaped stage
stage_box([P(1600, 912), P(1655, 912), P(1655, 1042), P(1540, 1042), P(1540, 992), P(1600, 992)], 34)
# RC95 booth
stage_box([P(905, 1325), P(960, 1325), P(960, 1365), P(905, 1365)], 26)
# Halo 88 building
stage_box([P(668, 1020), P(830, 1020), P(830, 1140), P(668, 1140)], 0)
# Mind Melt stage roof
stage_box([P(1080, 330), P(1300, 330), P(1300, 420), P(1080, 420)], 40)
# ::444:: room
stage_box([P(1340, 590), P(1470, 590), P(1470, 700), P(1340, 700)], 0)

# lane arrows on NW 24th St (in/out of the VIP entrance) and the ones into the VIP+ lounge
for w0 in (900, 990, 1080, 1180, 1270):
    a = P(626, w0 + 10)
    b = P(626, w0 + 50)
    arrow(a[0], a[1], b[0], b[1])
    a = P(647, w0 + 60)
    b = P(647, w0 + 20)
    arrow(a[0], a[1], b[0], b[1])
for u0 in (700, 780):
    a, b = P(u0 + 60, 860), P(u0, 860)
    arrow(a[0], a[1], b[0], b[1])
for u0 in (1040, 1100):
    a, b = P(u0, 330), P(u0 + 35, 330)
    arrow(a[0], a[1], b[0], b[1], color="b")

# trees (ground anchored)
TREES = [  # picture space, trunk base
    (241, 848), (346, 848), (391, 850), (541, 664), (616, 668), (736, 898), (806, 938), (1030, 937),
    (1136, 937), (1426, 937), (1442, 913), (1111, 1075), (1086, 1127), (1081, 1175), (1056, 1225),
    (1076, 1280), (1346, 1253), (1281, 1314), (1146, 1350), (1216, 1380), (1251, 1362), (1291, 1355),
    (1321, 1340), (1086, 1360), (1051, 1395), (1111, 1405), (1156, 1420), (991, 1180), (986, 1240),
    (961, 1310), (951, 1395), (1466, 865), (1376, 1290)]
for x, y in TREES:
    tree(x, y, 1.25)

# --------------------------------------------------------------------------------------------
# Street names
# --------------------------------------------------------------------------------------------
for (u, w, t, on) in [(425, 690, "NW 25th ST", False), (668, 720, "NW 24th ST", False),
                      (895, 300, "NW 23rd ST", False), (1035, 250, "NW 22nd LN", False),
                      (1000, 1270, "NW 23rd ST", True), (1340, 1280, "NW 22nd ST", True)]:
    x, y = P(u, w)
    street_text(x, y, t, on, STREET_ANGLE)
for (u, w, t) in [(1140, 862, "NW 5th AVE"), (765, 1405, "NW 6th AVE")]:
    x, y = P(u, w)
    street_text(x, y - 2, t, True, AVENUE_ANGLE)

# --------------------------------------------------------------------------------------------
# Facilities (billboard icons anchored on the ground)
# --------------------------------------------------------------------------------------------
FACILITIES = [
    # Isotropic lot
    ("bar", 450, 938, "vip"), ("restroom", 435, 1005, "vip"), ("table", 462, 1065, "ga"), ("bar", 528, 1062, "vip"),
    ("accessible", 584, 890, "ga"),
    # Halo 88 / RC95 block
    ("firstaid", 690, 898, "ga"), ("restroom", 692, 986, "ga"), ("restroom", 738, 986, "gaplus"), ("food", 906, 1007, "ga"),
    ("accessible", 852, 1145, "ga"), ("vip", 862, 1215, "vip"), ("vip", 738, 1255, "vipring"), ("restroom", 693, 1293, "vip"),
    ("vip", 812, 1293, "vip"), ("food", 735, 1358, "vip"), ("bar", 782, 1358, "vip"), ("bar", 847, 1358, "vip"),
    ("bar", 962, 1350, "vip"), ("tickets", 633, 1370, "ga"),
    # Sector 3 block
    ("food", 1030, 920, "ga"), ("merch", 1085, 958, "ga"), ("photo", 1088, 1070, "vip"), ("bar", 1092, 1120, "vip"),
    ("restroom", 1165, 1120, "vip"), ("lockers", 1162, 1212, "ga"), ("info", 1175, 1262, "ga"),
    ("lostfound", 1225, 1262, "ga"), ("boxoffice", 1188, 1327, "vip"), ("willcall", 1255, 1327, "ga"),
    ("firstaid", 1282, 933, "ga"), ("water", 1330, 930, "ga"), ("accessible", 1272, 1007, "ga"), ("tickets", 1040, 1350, "ga"),
    # Grand Central / Vertex block
    ("restroom", 1390, 920, "ga"), ("food", 1447, 987, "ga"), ("food", 1530, 1060, "ga"),
    # S3QUENC3 lot
    ("food", 790, 637, "ga"), ("food", 837, 780, "ga"),
    # Players Club / Mind Melt block
    ("restroom", 888, 445, "vip"), ("vip", 925, 420, "vipring"), ("photo", 970, 420, "vip"), ("water", 1020, 425, "vip"),
    ("food", 922, 490, "vip"), ("bar", 977, 490, "vip"), ("food", 1020, 478, "vip"), ("firstaid", 940, 592, "ga"),
    ("vip", 1005, 628, "vip"), ("water", 1055, 640, "ga"), ("accessible", 1100, 640, "ga"), ("restroom", 938, 740, "gaplus"),
    ("vip", 1105, 515, "vip"), ("bar", 1065, 548, "vip"), ("restroom", 1348, 505, "ga"), ("table", 1180, 588, "ga"),
    ("photo", 1300, 592, "vip"), ("merch", 1257, 682, "ga"), ("restroom", 1285, 730, "ga"), ("restroom", 1462, 818, "ga"),
    # VIP+ lounge
    ("vipplus", 1245, 262, "vip"),
]
for kind, u, w, style in FACILITIES:
    x, y = P(u, w)
    icon(kind, x, y, style)

# small captions next to facilities
for (u, w, t, dy) in [(462, 1065, "speakeasy", 38), (1180, 588, "speakeasy", 38), (812, 1293, "VIEWING AREA", 34),
                      (1105, 515, "EXIT", 34)]:
    x, y = P(u, w)
    cw = text_width(t, "bc7", 17) + 14
    rect(x - cw / 2, y + dy - 14, cw, 22, fill="b")
    text(x, y + dy + 3, t, font="bc7", size=17, color="w")

# Access Center pill
x, y = P(1120, 1165)
rect(x - 62, y - 22, 124, 44, fill="b", rx=22)
icon("accessible", x - 40, y, "ga", r=18)
text(x + 14, y - 3, "ACCESS", font="bc8", size=16, color="w")
text(x + 14, y + 14, "CENTER", font="bc8", size=16, color="w")

# --------------------------------------------------------------------------------------------
# Brand / venue lettering (outline-free, plain type)
# --------------------------------------------------------------------------------------------
for (u, w, t, font, size) in [(855, 905, "lyft", "b7", 40), (898, 1100, "SPIKED ADE", "bc8", 22),
                              (790, 1185, "Cafetera", "bc6i", 18), (760, 1318, "400 CONEJOS", "bc7", 14),
                              (685, 1362, "VIP", "bc8", 26), (1063, 1005, "EARGASM", "bc8", 16),
                              (1215, 1165, "END OVERDOSE", "bc8", 18), (1110, 1045, "VIP", "bc8", 30),
                              (856, 678, "spicy", "b6", 20), (856, 700, "pie", "b6", 20), (815, 820, "four", "b7", 26),
                              (970, 675, "Hennessy", "b6", 24), (950, 785, "BEATBOX", "bc8", 18),
                              (1330, 690, "Electrolit", "bc6i", 24), (1105, 210, "TAM TAM", "bc8", 20),
                              (1215, 205, "Foogs", "bc6i", 24), (1172, 262, "Ghee", "bc6i", 26),
                              (1100, 285, "STRANGE WATER", "bc7", 14), (1225, 322, "Grape Coast", "bc6i", 20)]:
    x, y = P(u, w)
    text(x, y + size * 0.35, t, font=font, size=size)

hx, hy = P(850, 650)
ops.append({"o": "path", "d": f"M{hx} {hy + 6}c-7-5-9-8-9-11 0-3 4-5 9-1 5-4 9-2 9 1 0 3-2 6-9 11z", "f": "b"})
text(hx - 12, hy + 7, "I", font="b6", size=20)

# --------------------------------------------------------------------------------------------
# Stage tags (tap targets) and attraction tags
# --------------------------------------------------------------------------------------------
STAGE_TAGS = [
    ("isotropic", "ISOTROPIC", 535, 938, 130, 36), ("iii-points-radio", "III POINTS RADIO", 870, 957, 182, 36),
    ("halo-88", "HALO 88", 715, 1095, 104, 38), ("rc95", "RC95", 895, 1285, 96, 38),
    ("sec3", "SECTOR 3", 1190, 962, 126, 38), ("vertex", "VERTEX", 1515, 910, 104, 38),
    ("grand-central", "GRAND CENTRAL", 1565, 1120, 178, 38), ("s3qu3nce", "S3QUENC3", 745, 725, 118, 36),
    ("players-club", "PLAYER'S CLUB", 955, 540, 162, 36), ("door-iv", "DOOR IV", 1055, 792, 104, 36),
    ("mind-melt", "MIND MELT", 1225, 470, 142, 40), ("444", "::444::", 1395, 567, 84, 36),
    ("unforeseen", "UNFORESEEN", 1420, 640, 112, 32),
]
for sid, t, u, w, bw, bh in STAGE_TAGS:
    x, y = P(u, w)
    label(x, y, t, bw, bh, hit="stage:" + sid)

for t, sub, u, w, bw, bh in [("FORTUNE ROW", None, 880, 1055, 162, 36), ("DIGITAL GALLERY", "LIT BY THE FLOWERY", 1315, 800, 196, 62),
                             ("MOKIWORLD", "IGNITE", 1255, 530, 160, 54), ("SKATE", "SPACE", 1432, 718, 72, 54),
                             ("VIP+ LOUNGE", None, 1155, 155, 152, 36)]:
    x, y = P(u, w)
    label(x, y, t, bw, bh, kind="attraction", sub=sub)

# Entrances
x, y = 708, 1514
rect(x - 128, y - 43, 256, 86, fill="b")
rect(x - 122, y - 37, 244, 74, fill="w", stroke=3)
text(x, y + 22, "ENTRANCE", font="bc8", size=64, fit=228)
hits.append({"id": "place:entrance", "x": x - 128, "y": y - 43, "w": 256, "h": 86})
for (u, w, t, bw, bh) in [(565, 1265, "VIP ENTRANCE", 62, 300), (968, 240, "VIP+ ENTRANCE", 66, 300)]:
    x, y = P(u, w)
    rect(x - bh / 2, y - bw / 2, bh, bw, fill="b", rot=STREET_ANGLE, rx=0)
    text(x, y + bw * 0.3, t, font="bc8", size=round(bw * 0.8), color="w", rot=STREET_ANGLE, fit=bh - 16)

# --------------------------------------------------------------------------------------------
# Poster furniture: title block, highways, legend
# --------------------------------------------------------------------------------------------
def O(x, y):
    """Official-image coordinates to map space."""
    return (x * 1.404 + 61, y * 1.404 + 18.7)


x0, y0 = O(25, 75)
x1, y1 = O(505, 180)
rect(x0 + 6, y0 + 6, x1 - x0, y1 - y0, fill="b", rx=14)
rect(x0, y0, x1 - x0, y1 - y0, fill="w", stroke=5, rx=14)
text((x0 + x1) / 2, y1 - 26, "III POINTS", font="bc8", size=150, fit=(x1 - x0) - 40)
for (c, t, w, h, size) in [(O(100, 62), "MIAMI", 120, 36, 30), (O(405, 58), "OCTOBER 16 & 17", 252, 42, 32),
                           (O(205, 198), "2026", 112, 34, 30)]:
    rect(c[0] - w / 2, c[1] - h / 2, w, h, fill="b")
    text(c[0], c[1] + size * 0.36, t, font="bc8", size=size, color="w", fit=w - 10)
tx, ty = O(262, 285)
text(tx, ty + 38, "FESTIVAL MAP", font="bc8", size=118, fit=430)
tx, ty = O(265, 350)
text(tx, ty + 12, "13 STAGES  |  150+ ARTISTS  |  5 CITY BLOCKS", font="bc7", size=33, fit=432)

for (lx, ly0, ly1, t, up) in [(25, 250, 1150, "I-95", True), (1050, 330, 1150, "I-195", True)]:
    a, b = O(lx, ly0), O(lx, ly1)
    line([a, b], stroke=3)
    poly([(a[0], a[1] - 4), (a[0] - 9, a[1] + 18), (a[0] + 9, a[1] + 18)], fill="b")
    mx, my = O(lx, (ly0 + ly1) / 2)
    rect(mx - 22, my - 50, 44, 100, fill="w")
    text(mx + 10, my, t, font="bc8", size=30, rot=90 if lx > 500 else -90)

lx0, ly0 = O(150, 1118)
lx1, ly1 = O(935, 1298)
rect(lx0 + 8, ly0 + 8, lx1 - lx0, ly1 - ly0, fill="b")
rect(lx0, ly0, lx1 - lx0, ly1 - ly0, fill="w", stroke=6)
cols = [202, 352, 498, 657, 798]
rows = [1146, 1188, 1230, 1272]
for ci, col in enumerate(LEGEND):
    for ri, (name, kind, style) in enumerate(col):
        ix, iy = O(cols[ci], rows[ri])
        icon(kind, ix, iy, style, r=21)
        words = name.split(" ")
        if len(name) > 11 and len(words) > 1:
            split = len(words) // 2 if len(words) > 2 else 1
            l1, l2 = " ".join(words[:split]), " ".join(words[split:])
            text(ix + 30, iy - 2, l1, font="bc7", size=23, align="l")
            text(ix + 30, iy + 20, l2, font="bc7", size=23, align="l")
        else:
            text(ix + 30, iy + 8, name, font="bc7", size=23, align="l")


# --------------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------------
def svg_path_icon(kind, x, y, r, style):
    s = r / 12.0 * 0.82
    fg, bg = ("#fff", "#000") if style in ("ga", "gaplus") else ("#000", "#fff")
    out = [f'<circle cx="{x}" cy="{y}" r="{r}" fill="{bg}" stroke="#000" stroke-width="{3 if bg == "#fff" else 0}"/>']
    if style == "gaplus":
        out.append(f'<circle cx="{x}" cy="{y}" r="{r - 4}" fill="none" stroke="#fff" stroke-width="1.6"/>')
    if style == "vipring":
        out.append(f'<circle cx="{x}" cy="{y}" r="{r - 5.5}" fill="none" stroke="#000" stroke-width="1.6"/>')
    out.append(f'<g transform="translate({x - 12 * s} {y - 12 * s}) scale({s})">')
    for op in ICONS[kind]:
        col = bg if op[-1] == "bg" else fg
        if op[0] == "p":
            out.append(f'<path d="{op[1]}" fill="{col}"/>')
        elif op[0] == "c":
            out.append(f'<circle cx="{op[1]}" cy="{op[2]}" r="{op[3]}" fill="{col}"/>')
        elif op[0] == "t":
            out.append(f'<text x="12" y="{12 + op[2] * 0.36}" font-family="BC8" font-size="{op[2]}" text-anchor="middle" fill="{col}">{op[1]}</text>')
    out.append("</g>")
    return "".join(out)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;")


def to_svg(ops_list):
    col = {"b": "#000", "w": "#fff", "n": "none", "h": "url(#hatch)"}
    vx, vy, vw, vh = VIEW
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx} {vy} {vw} {vh}" width="{vw}" height="{vh}">',
           "<style>"]
    for key, f in FONT_FILES.items():
        with open(os.path.join(FONTS, f), "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        out.append(f'@font-face{{font-family:"{key.upper()}";src:url(data:font/ttf;base64,{b64})}}')
    out.append("</style>")
    out.append('<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               '<rect width="8" height="8" fill="#fff"/><rect width="2" height="8" fill="#000"/></pattern></defs>')
    out.append(f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" fill="#fff"/>')
    for op in ops_list:
        o = op["o"]
        if o == "poly":
            pts = " ".join(f"{op['p'][i]},{op['p'][i + 1]}" for i in range(0, len(op["p"]), 2))
            st = f' stroke="{col[op["c"]]}" stroke-width="{op["s"]}" stroke-linejoin="round"' if op["s"] else ""
            out.append(f'<polygon points="{pts}" fill="{col[op["f"]]}"{st}/>')
        elif o == "line":
            pts = " ".join(f"{op['p'][i]},{op['p'][i + 1]}" for i in range(0, len(op["p"]), 2))
            dash = f' stroke-dasharray="{op["d"][0]} {op["d"][1]}"' if "d" in op else ""
            out.append(f'<polyline points="{pts}" fill="none" stroke="{col[op["c"]]}" stroke-width="{op["s"]}" stroke-linecap="round" stroke-linejoin="round"{dash}/>')
        elif o == "circle":
            st = f' stroke="{col[op["c"]]}" stroke-width="{op["s"]}"' if op["s"] else ""
            out.append(f'<circle cx="{op["x"]}" cy="{op["y"]}" r="{op["r"]}" fill="{col[op["f"]]}"{st}/>')
        elif o == "ellipse":
            dash = f' stroke-dasharray="{op["d"][0]} {op["d"][1]}"' if "d" in op else ""
            out.append(f'<ellipse cx="{op["x"]}" cy="{op["y"]}" rx="{op["rx"]}" ry="{op["ry"]}" fill="{col[op["f"]]}" stroke="{col[op["c"]]}" stroke-width="{op["s"]}"{dash}/>')
        elif o == "rect":
            st = f' stroke="{col[op["c"]]}" stroke-width="{op["s"]}"' if op["s"] else ""
            tr = ""
            if op.get("r"):
                cx, cy = op["x"] + op["w"] / 2, op["y"] + op["h"] / 2
                tr = f' transform="rotate({op["r"]} {cx} {cy})"'
            out.append(f'<rect x="{op["x"]}" y="{op["y"]}" width="{op["w"]}" height="{op["h"]}" rx="{op["rx"]}" fill="{col[op["f"]]}"{st}{tr}/>')
        elif o == "text":
            anchor = {"l": "start", "c": "middle", "r": "end"}[op["a"]]
            fit = ""
            if op.get("fit") and text_width(op["t"], op["font"], op["sz"]) > op["fit"]:
                fit = f' textLength="{op["fit"]}" lengthAdjust="spacingAndGlyphs"'
            tr = f' transform="rotate({op["r"]} {op["x"]} {op["y"]})"' if op.get("r") else ""
            out.append(f'<text x="{op["x"]}" y="{op["y"]}" font-family="{op["font"].upper()}" font-size="{op["sz"]}" '
                       f'text-anchor="{anchor}" fill="{col[op["c"]]}"{fit}{tr}>{esc(op["t"])}</text>')
        elif o == "path":
            out.append(f'<path d="{op["d"]}" fill="{col[op["f"]]}"/>')
        elif o == "icon":
            out.append(svg_path_icon(op["k"], op["x"], op["y"], op["r"], op["st"]))
    out.append("</svg>")
    return "\n".join(out)


def main():
    assets = os.path.join(ROOT, "app", "assets")
    doc = {"view": VIEW, "ops": ops, "hits": hits, "fonts": FONT_FILES}
    with open(os.path.join(assets, "map.json"), "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    with open(os.path.join(assets, "icons.json"), "w") as f:
        json.dump(ICONS, f, separators=(",", ":"))
    os.makedirs(os.path.join(ROOT, "mockup"), exist_ok=True)
    with open(os.path.join(ROOT, "mockup", "map.svg"), "w") as f:
        f.write(to_svg(ops))
    print(f"{len(ops)} ops, {len(hits)} tap targets")


if __name__ == "__main__":
    main()
