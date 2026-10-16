"""Build the black & white III Points 2026 map for the Mudita Kompakt (E Ink).

Hand-built vector map, checked against the hi-res stitch of the official map
(source/map/hires.png, see tools/stitch_zoom.py and tools/overlay_check.py):
  * raised city blocks and streets on the map's oblique street grid (3D, like the original)
  * stage buildings as extruded 3D boxes
  * icon positions and types from tools/detect_icons.py (matched against the official legend)
  * stage labels at the official tag positions
  * no sponsor logos, no trees, no poster title/legend (the legend is its own app screen)

Outputs:
  app/assets/map.json    display list rendered by the Android app (MapView)
  app/assets/icons.json  pictograms
  mockup/map.svg         the same drawing as a standalone SVG for review
Coordinates are "reference" pixels of the official map stitched from app screenshots
(hires.png pixel = (ref - (61, 19)) * 3).
"""
import base64
import json
import math
import os
import sys

from PIL import ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from icons import ICONS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "app", "assets", "fonts")
K, S = 0.2586, 0.044                               # oblique grid: ground (u, w) -> picture (u - K*w, S*u + w)
STREET_ANGLE = -math.degrees(math.atan2(1, K))     # cross streets, about -75.5 degrees
AVENUE_ANGLE = math.degrees(math.atan(S))          # avenues, about 2.5 degrees
VIEW = (130, 80, 1400, 1500)                       # x, y, w, h of the map area
WALL = (7, 56)                                     # extrusion of the raised city blocks
DETAIL = 1                                         # level of ops only shown when zoomed in

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


def UV(x, y):
    """Picture -> ground grid."""
    u = (x + K * y) / (1 + K * S)
    return u, y - S * u


def rect_uv(u0, w0, u1, w1):
    return [P(u0, w0), P(u1, w0), P(u1, w1), P(u0, w1)]


def around(x, y, du, dw):
    """Ground-aligned rectangle of size du x dw centred on picture point (x, y)."""
    u, w = UV(x, y)
    return rect_uv(u - du / 2, w - dw / 2, u + du / 2, w + dw / 2)


def flat(pts):
    out = []
    for x, y in pts:
        out += [round(x, 1), round(y, 1)]
    return out


ops = []
hits = []


def op(d, lvl=0):
    if lvl:
        d["lvl"] = lvl
    ops.append(d)


def poly(pts, fill="w", stroke=0, color="b", lvl=0):
    op({"o": "poly", "p": flat(pts), "f": fill, "s": stroke, "c": color}, lvl)


def line(pts, stroke=2, color="b", dash=None, lvl=0):
    d = {"o": "line", "p": flat(pts), "s": stroke, "c": color}
    if dash:
        d["d"] = dash
    op(d, lvl)


def text(x, y, t, font="bc8", size=24, color="b", align="c", rot=0, fit=None, lvl=0):
    d = {"o": "text", "x": round(x, 1), "y": round(y, 1), "t": t, "font": font, "sz": size, "c": color, "a": align}
    if rot:
        d["r"] = round(rot, 2)
    if fit:
        d["fit"] = fit
    op(d, lvl)


def rect(x, y, w, h, fill="w", stroke=0, color="b", rx=0, rot=0, lvl=0):
    d = {"o": "rect", "x": round(x, 1), "y": round(y, 1), "w": round(w, 1), "h": round(h, 1),
         "f": fill, "s": stroke, "c": color, "rx": rx}
    if rot:
        d["r"] = round(rot, 2)
    op(d, lvl)


def wall(pts):
    """Visible side walls of a raised block: sweep the outline along WALL."""
    ex, ey = WALL
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        poly([a, b, (b[0] + ex, b[1] + ey), (a[0] + ex, a[1] + ey)], fill="b")
    poly([(x + ex, y + ey) for x, y in pts], fill="b")


# --------------------------------------------------------------------------------------------
# Ground: raised plates (streets, black) carrying the city blocks (white)
# --------------------------------------------------------------------------------------------
SOUTH = [P(612, 840), P(1700, 840), P(1700, 1425), P(612, 1425)]    # 3 south blocks + NW 5th / 6th Ave
ISO = [P(452, 840), P(612, 840), P(612, 1112), P(452, 1112)]        # Isotropic lot
NORTH_S3 = [P(695, 648), P(868, 648), P(868, 840), P(695, 840)]     # S3QUENC3 lot
NORTH_E = [P(868, 402), P(1490, 402), P(1490, 840), P(868, 840)]    # Players Club / Mind Melt block
VIP_LOUNGE = [P(1062, 122), P(1282, 122), P(1282, 402), P(1062, 402)]
CHECK_SHAPES = ["SOUTH", "ISO", "NORTH_S3", "NORTH_E", "VIP_LOUNGE"]

for shape in (SOUTH, ISO, NORTH_E, VIP_LOUNGE):
    wall(shape)
for shape in (SOUTH, ISO, NORTH_S3, NORTH_E, VIP_LOUNGE):
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
for pts in BLOCKS.values():
    poly(pts, fill="w")

# streets drawn as outlines on open ground north of the blocks
for u0, u1, w0, w1 in [(403, 451, 560, 840), (647, 694, 560, 840), (868, 911, 150, 402), (1020, 1062, 150, 402)]:
    line([P(u0, w0), P(u0, w1)], stroke=3)
    line([P(u1, w0), P(u1, w1)], stroke=3)

# --------------------------------------------------------------------------------------------
# Street names (big, on the black streets)
# --------------------------------------------------------------------------------------------
for (u, w, t) in [(1150, 861, "NW 5th AVE"), (800, 1404, "NW 6th AVE")]:
    x, y = P(u, w)
    text(x, y + 11, t, font="bc6i", size=32, color="w", rot=AVENUE_ANGLE)
for (u, w, t, on) in [(1002, 1290, "NW 23rd ST", True), (1341, 1290, "NW 22nd ST", True), (636, 1000, "NW 24th ST", True),
                      (427, 700, "NW 25th ST", False), (670, 700, "NW 24th ST", False),
                      (889, 260, "NW 23rd ST", False), (1041, 260, "NW 22nd LN", False)]:
    x, y = P(u, w)
    text(x + 11, y, t, font="bc6i", size=32 if on else 28, color="w" if on else "b", rot=STREET_ANGLE)

# --------------------------------------------------------------------------------------------
# Stages: flat drawings recreated from the official artwork (tools/stages.py)
# --------------------------------------------------------------------------------------------
from stages import shapes  # noqa: E402

PART_STYLE = {  # style -> (fill, stroke width, stroke colour, dash)
    "floor": ("w", 3, "b", [12, 8]), "roof": ("b", 2, "w", None), "side": ("h", 2.5, "b", None),
    "screen": ("w", 2.5, "b", None), "struct": ("w", 3, "b", None), "wline": (None, 2.5, "w", None),
}
FOOTPRINTS = {}
for stage, part, style, shape in shapes():
    fill, sw, sc, dash = PART_STYLE[style]
    if isinstance(shape, tuple) and shape and shape[0] == "ellipse":
        _, cx, cy, rx, ry = shape
        d = {"o": "ellipse", "x": cx, "y": cy, "rx": rx, "ry": ry, "f": fill, "s": sw, "c": sc}
        if dash:
            d["d"] = dash
        op(d)
        continue
    FOOTPRINTS[f"{stage}/{part}"] = shape
    if fill is None:
        line(shape, stroke=sw, color=sc)
    elif dash:
        poly(shape, fill=fill)
        line(list(shape) + [shape[0]], stroke=sw, color=sc, dash=dash)
    else:
        poly(shape, fill=fill, stroke=sw, color=sc)

# --------------------------------------------------------------------------------------------
# Facilities: positions/types detected on the official map, a few fixed by hand
# --------------------------------------------------------------------------------------------
STYLE = {  # detected type -> (glyph, disc style, filter category)
    "firstaid": ("firstaid", "ga", "firstaid"), "water": ("water", "ga", "water"),
    "vipwater": ("water", "vip", "vip"), "restroom": ("restroom", "ga", "restroom"),
    "viprestroom": ("restroom", "vip", "vip"), "gaplusrestroom": ("restroom", "gaplus", "gaplus"),
    "food": ("food", "ga", "food"), "vipfood": ("food", "vip", "vip"), "vipbar": ("bar", "vip", "vip"),
    "merch": ("merch", "ga", "merch"), "accessible": ("accessible", "ga", "access"),
    "lockers": ("lockers", "ga", "help"), "info": ("info", "ga", "help"), "lostfound": ("lostfound", "ga", "help"),
    "tickets": ("tickets", "ga", "help"), "willcall": ("willcall", "ga", "help"),
    "boxoffice": ("boxoffice", "ga", "help"), "vipupgrade": ("vip", "vip", "help"),
    "vipconcierge": ("vip", "vipring", "vip"), "table": ("table", "ga", "vip"),
    "photo": ("photo", "ga", "photo"), "vipplus": ("vipplus", "vip", "vip"), "vipexit": ("vip", "vip", "vip"),
}
FIX = {  # (x, y) of a detection -> corrected type (None drops it)
    (1177.3, 316.0): "vipplus", (863.3, 463.3): "photo", (1150.7, 650.7): "photo", (810.7, 1117.3): "photo",
    (1244.0, 708.0): None, (973.3, 563.3): "vipexit", (484.0, 1326.7): "vipconcierge",
}
detected = json.load(open(os.path.join(ROOT, "source", "map", "icons_detected.json")))
ICON_R = 21
CHECK_POINTS = []
for d in detected:
    t = FIX.get((d["x"], d["y"]), d["type"])
    if t is None:
        continue
    glyph, style, cat = STYLE[t]
    CHECK_POINTS.append((d["x"], d["y"]))
    op({"o": "icon", "k": glyph, "x": d["x"], "y": d["y"], "r": ICON_R, "st": style, "cat": cat}, DETAIL)
# Access Center (a pill on the original)
op({"o": "icon", "k": "accessible", "x": 790, "y": 1217, "r": ICON_R, "st": "ga", "cat": "access"}, DETAIL)
text(814, 1213, "ACCESS", font="bc8", size=19, align="l", lvl=DETAIL)
text(814, 1231, "CENTER", font="bc8", size=19, align="l", lvl=DETAIL)

# --------------------------------------------------------------------------------------------
# Attractions (smaller boxed labels, zoomed in) and stages (big labels, tap targets)
# --------------------------------------------------------------------------------------------
for t, x, y in [("MOKIWORLD", 1113, 583), ("SKATE SPACE", 1238, 794), ("FORTUNE ROW", 611, 1093),
                ("DIGITAL GALLERY", 1105, 867), ("VIP+ LOUNGE", 1119, 206)]:
    w = text_width(t, "bc8", 22) + 16
    rect(x - w / 2, y - 14, w, 28, fill="w", stroke=2.5, lvl=DETAIL)
    text(x, y + 8, t, font="bc8", size=22, lvl=DETAIL)

STAGES = [  # id, label, tag centre (from the official map)
    ("mind-melt", "MIND MELT", 1103.5, 529), ("players-club", "PLAYER'S CLUB", 815, 581),
    ("444", "::444::", 1248.5, 627), ("unforeseen", "UNFORESEEN", 1247, 762),
    ("s3qu3nce", "S3QUENC3", 578, 758), ("door-iv", "DOOR IV", 853.5, 840),
    ("isotropic", "ISOTROPIC", 294, 963), ("vertex", "VERTEX", 1280, 979),
    ("iii-points-radio", "III POINTS RADIO", 624, 997), ("sec3", "SECTOR 3", 938, 1014),
    ("halo-88", "HALO 88", 433, 1126), ("grand-central", "GRAND CENTRAL", 1274, 1188),
    ("rc95", "RC95", 560, 1325),
]
STAGE_SIZE = 30
for sid, t, x, y in STAGES:
    w = text_width(t, "bc8", STAGE_SIZE) + 20
    h = STAGE_SIZE * 1.25
    op({"o": "stage", "id": sid, "t": t, "x": x, "y": y, "sz": STAGE_SIZE, "w": round(w, 1), "h": round(h, 1)})
    hits.append({"id": "stage:" + sid, "x": round(x - w / 2, 1), "y": round(y - h / 2, 1), "w": round(w, 1), "h": round(h, 1)})

# --------------------------------------------------------------------------------------------
# Entrances: arrow + label
# --------------------------------------------------------------------------------------------
ENTRANCES = [  # id, label, label centre, arrow tip, arrow direction (degrees, screen)
    ("main", "ENTRANCE", (705, 1530), (725, 1440), -80),
    ("vip", "VIP ENTRANCE", (220, 1285), (296, 1260), -10),
    ("vipplus", "VIP+ ENTRANCE", (935, 175), (930, 260), 95),
]
for eid, t, (lx, ly), (ax, ay), ang in ENTRANCES:
    op({"o": "entrance", "id": eid, "t": t, "x": lx, "y": ly, "ax": ax, "ay": ay, "ang": ang, "sz": 26})
    w = text_width(t, "bc8", 26) + 20
    hits.append({"id": "entrance:" + eid, "x": lx - w / 2, "y": ly - 18, "w": w, "h": 36})


# --------------------------------------------------------------------------------------------
# SVG output
# --------------------------------------------------------------------------------------------
def svg_icon(kind, x, y, r, style):
    s = r / 12.0 * 0.82
    dark = style in ("ga", "gaplus")
    fg, bg = ("#fff", "#000") if dark else ("#000", "#fff")
    out = [f'<circle cx="{x}" cy="{y}" r="{r + 3}" fill="#fff"/>',
           f'<circle cx="{x}" cy="{y}" r="{r}" fill="{bg}" stroke="#000" stroke-width="{0 if dark else 3}"/>']
    if style == "gaplus":
        out.append(f'<circle cx="{x}" cy="{y}" r="{r - 4}" fill="none" stroke="#fff" stroke-width="1.6"/>')
    if style == "vipring":
        out.append(f'<circle cx="{x}" cy="{y}" r="{r - 5.5}" fill="none" stroke="#000" stroke-width="1.6"/>')
    out.append(f'<g transform="translate({x - 12 * s} {y - 12 * s}) scale({s})">')
    for o in ICONS[kind]:
        col = bg if o[-1] == "bg" else fg
        if o[0] == "p":
            out.append(f'<path d="{o[1]}" fill="{col}"/>')
        elif o[0] == "c":
            out.append(f'<circle cx="{o[1]}" cy="{o[2]}" r="{o[3]}" fill="{col}"/>')
        elif o[0] == "t":
            out.append(f'<text x="12" y="{12 + o[2] * 0.36}" font-family="BC8" font-size="{o[2]}" text-anchor="middle" fill="{col}">{o[1]}</text>')
    out.append("</g>")
    return "".join(out)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;")


def svg_text(x, y, t, font, size, color, anchor="middle", rot=0, fit=None):
    fitattr = ""
    if fit and text_width(t, font, size) > fit:
        fitattr = f' textLength="{fit}" lengthAdjust="spacingAndGlyphs"'
    tr = f' transform="rotate({rot} {x} {y})"' if rot else ""
    return (f'<text x="{x}" y="{y}" font-family="{font.upper()}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{color}"{fitattr}{tr}>{esc(t)}</text>')


def to_svg(ops_list):
    col = {"b": "#000", "w": "#fff", "n": "none", "h": "url(#hatch)"}
    vx, vy, vw, vh = VIEW
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx} {vy} {vw} {vh}" width="{vw}" height="{vh}">', "<style>"]
    for key, f in FONT_FILES.items():
        with open(os.path.join(FONTS, f), "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        out.append(f'@font-face{{font-family:"{key.upper()}";src:url(data:font/ttf;base64,{b64})}}')
    out.append("</style>")
    out.append('<defs><pattern id="hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               '<rect width="9" height="9" fill="#fff"/><rect width="2.5" height="9" fill="#000"/></pattern></defs>')
    out.append(f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" fill="#fff"/>')
    for o in ops_list:
        k = o["o"]
        if k == "poly":
            pts = " ".join(f"{o['p'][i]},{o['p'][i + 1]}" for i in range(0, len(o["p"]), 2))
            st = f' stroke="{col[o["c"]]}" stroke-width="{o["s"]}" stroke-linejoin="round"' if o["s"] else ""
            out.append(f'<polygon points="{pts}" fill="{col[o["f"]]}"{st}/>')
        elif k == "line":
            pts = " ".join(f"{o['p'][i]},{o['p'][i + 1]}" for i in range(0, len(o["p"]), 2))
            dash = f' stroke-dasharray="{o["d"][0]} {o["d"][1]}"' if "d" in o else ""
            out.append(f'<polyline points="{pts}" fill="none" stroke="{col[o["c"]]}" stroke-width="{o["s"]}" '
                       f'stroke-linecap="round"{dash}/>')
        elif k == "ellipse":
            dash = f' stroke-dasharray="{o["d"][0]} {o["d"][1]}"' if "d" in o else ""
            out.append(f'<ellipse cx="{o["x"]}" cy="{o["y"]}" rx="{o["rx"]}" ry="{o["ry"]}" fill="{col[o.get("f", "n")]}" '
                       f'stroke="{col[o.get("c", "b")]}" stroke-width="{o["s"]}"{dash}/>')
        elif k == "rect":
            st = f' stroke="{col[o["c"]]}" stroke-width="{o["s"]}"' if o["s"] else ""
            tr = ""
            if o.get("r"):
                tr = f' transform="rotate({o["r"]} {o["x"] + o["w"] / 2} {o["y"] + o["h"] / 2})"'
            out.append(f'<rect x="{o["x"]}" y="{o["y"]}" width="{o["w"]}" height="{o["h"]}" rx="{o["rx"]}" '
                       f'fill="{col[o["f"]]}"{st}{tr}/>')
        elif k == "text":
            anchor = {"l": "start", "c": "middle", "r": "end"}[o["a"]]
            out.append(svg_text(o["x"], o["y"], o["t"], o["font"], o["sz"], col[o["c"]], anchor, o.get("r", 0), o.get("fit")))
        elif k == "icon":
            out.append(svg_icon(o["k"], o["x"], o["y"], o["r"], o["st"]))
        elif k == "stage":
            x, y, w, h = o["x"], o["y"], o["w"], o["h"]
            out.append(f'<rect x="{x - w / 2 + 5}" y="{y - h / 2 + 5}" width="{w}" height="{h}" fill="#000"/>')
            out.append(f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" fill="#fff" stroke="#000" stroke-width="3.5"/>')
            out.append(svg_text(x, y + o["sz"] * 0.36, o["t"], "bc8", o["sz"], "#000"))
        elif k == "entrance":
            x, y, s = o["x"], o["y"], o["sz"]
            w = text_width(o["t"], "bc8", s) + 20
            a = math.radians(o["ang"])
            tx, ty = o["ax"], o["ay"]
            L = 70
            bx, by = tx - L * math.cos(a), ty - L * math.sin(a)
            hx1, hy1 = tx - 22 * math.cos(a - 0.5), ty - 22 * math.sin(a - 0.5)
            hx2, hy2 = tx - 22 * math.cos(a + 0.5), ty - 22 * math.sin(a + 0.5)
            out.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{tx}" y2="{ty}" stroke="#fff" stroke-width="15" stroke-linecap="round"/>')
            out.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{tx}" y2="{ty}" stroke="#000" stroke-width="8" stroke-linecap="round"/>')
            out.append(f'<polygon points="{tx},{ty} {hx1:.1f},{hy1:.1f} {hx2:.1f},{hy2:.1f}" fill="#000" stroke="#fff" stroke-width="3"/>')
            out.append(f'<rect x="{x - w / 2}" y="{y - s * 0.7}" width="{w}" height="{s * 1.4}" rx="{s * 0.7}" fill="#000" stroke="#fff" stroke-width="3"/>')
            out.append(svg_text(x, y + s * 0.36, o["t"], "bc8", s, "#fff"))
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
