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
from proj import MODE, K, S, STREET_ANGLE, AVENUE_ANGLE, P, from_pic  # noqa: E402
VIEW = (60, 115, 1450, 1520) if MODE == "oblique" else (360, 60, 1400, 1540)   # x, y, w, h (tight to the venue)
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


# Line weights: blocks heavy, stages/buildings medium, details thin
W_BLOCK, W_EDGE, W_STRUCT, W_DETAIL, W_FLOOR = 4.5, 1.5, 2.5, 1.5, 2.2

# --------------------------------------------------------------------------------------------
# Ground (flat): white paper, streets are the gaps between the blocks, blocks carry a fine texture
# --------------------------------------------------------------------------------------------
SOUTH = [P(612, 840), P(1700, 840), P(1700, 1425), P(612, 1425)]    # 3 south blocks + NW 5th / 6th Ave
ISO = [P(452, 840), P(612, 840), P(612, 1112), P(452, 1112)]        # Isotropic lot
NORTH_S3 = [P(695, 648), P(868, 648), P(868, 840), P(695, 840)]     # S3QUENC3 lot
NORTH_E = [P(868, 402), P(1490, 402), P(1490, 840), P(868, 840)]    # Players Club / Mind Melt block
VIP_LOUNGE = [P(1062, 122), P(1282, 122), P(1282, 402), P(1062, 402)]
CHECK_SHAPES = ["SOUTH", "ISO", "NORTH_S3", "NORTH_E", "VIP_LOUNGE"]
# the outer edge of the avenues (festival perimeter): one thin line. Blocks that front a street
# directly get no plate, so no line ever runs right beside a block outline.
for shape in (SOUTH, [P(868, 408), P(1484, 408), P(1484, 840), P(868, 840)]):
    poly(shape, fill="w", stroke=W_EDGE)
# short street stubs leaving the site (open ends); their inner side is the block edge
STREETS = [(410, 458, 770, 1106), (654, 701, 590, 843), (868, 911, 150, 410), (1026, 1068, 150, 410)]
for u0, u1, w0, w1 in STREETS:
    poly(rect_uv(u0 + 1, w0, u1 - 1, w1), fill="w")
    line([P(u0, w0), P(u0, w1)], stroke=W_EDGE)
    line([P(u1, w0), P(u1, w1)], stroke=W_EDGE)

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
    poly(pts, fill="lawn", stroke=W_BLOCK)

# --------------------------------------------------------------------------------------------
# Street names: Barlow semibold, quieter than the labels
# --------------------------------------------------------------------------------------------
for (u, w, t) in [(1152, 861, "NW 5th Ave"), (745, 1404, "NW 6th Ave")]:
    x, y = P(u, w)
    text(x, y + 8, t, font="b6", size=22, color="b", rot=AVENUE_ANGLE)
for (u, w, t) in [(1002, 1290, "NW 23rd St"), (1341, 1300, "NW 22nd St"), (636, 1000, "NW 24th St"),
                  (427, 960, "NW 25th St"), (670, 645, "NW 24th St"), (889, 260, "NW 23rd St"), (1041, 260, "NW 22nd Ln")]:
    x, y = P(u, w)
    text(x + 8, y, t, font="b6", size=22, color="b", rot=STREET_ANGLE)

# --------------------------------------------------------------------------------------------
# Stages and structures: one language on the street grid (tools/plan.py)
# --------------------------------------------------------------------------------------------
from plan import shapes, LABEL_AT, ZONES  # noqa: E402

PART_STYLE = {  # style -> (fill, stroke width, dash)
    "floor": ("w", W_FLOOR, [11, 7]), "court": ("w", W_FLOOR, [11, 7]), "stage": ("h", W_STRUCT, None),
    "bldg": ("w", W_STRUCT * 0.8, None), "detail": (None, W_DETAIL, None), "zone": ("vipz", 1.6, [5, 4]),
}
FOOTPRINTS = {}
for stage, part, style, shape in shapes():
    fill, sw, dash = PART_STYLE[style]
    FOOTPRINTS[f"{stage}/{part}"] = shape
    if fill is None:
        line(shape, stroke=sw)
    elif dash:
        poly(shape, fill=fill)
        line(list(shape) + [shape[0]], stroke=sw, dash=dash)
        if style == "zone":
            FOOTPRINTS.pop(f"{stage}/{part}")
    else:
        poly(shape, fill=fill, stroke=sw)

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
ICON_R = 15
CHECK_POINTS = []
for d in detected:
    t = FIX.get((d["x"], d["y"]), d["type"])
    if t is None:
        continue
    glyph, style, cat = STYLE[t]
    CHECK_POINTS.append((d["x"], d["y"]))
    ix, iy = from_pic(d["x"], d["y"])
    op({"o": "icon", "k": glyph, "x": ix, "y": iy, "r": ICON_R, "st": style, "cat": cat}, DETAIL)
# Access Center (a pill on the original)
ACCESS = from_pic(790, 1217)
op({"o": "icon", "k": "accessible", "x": ACCESS[0], "y": ACCESS[1], "r": ICON_R, "st": "ga", "cat": "access"}, DETAIL)

# --------------------------------------------------------------------------------------------
# Labels: data only. The app draws them (Mudita-style), the SVG doesn't.
#   kind: stage | attraction | entrance | place;  x, y: anchor;  tag: where the official map put its tag
# --------------------------------------------------------------------------------------------
LABELS = []


def centroid(stage_id):
    pts = [p for k, v in FOOTPRINTS.items() if k.split("/")[0] == stage_id for p in v]
    return (round(sum(p[0] for p in pts) / len(pts), 1), round(sum(p[1] for p in pts) / len(pts), 1)) if pts else None


STAGES = [  # id, name, official tag centre
    ("mind-melt", "Mind Melt", 1103.5, 529), ("players-club", "Players Club", 815, 581),
    ("444", "::444::", 1248.5, 627), ("unforeseen", "Unforeseen", 1247, 700),
    ("s3qu3nce", "S3QUENC3", 578, 758), ("door-iv", "Door IV", 853.5, 840),
    ("isotropic", "Isotropic", 294, 963), ("vertex", "Vertex", 1280, 979),
    ("iii-points-radio", "III Points Radio", 624, 997), ("sec3", "Sector 3", 938, 1014),
    ("halo-88", "Halo 88", 433, 1126), ("grand-central", "Grand Central", 1274, 1188),
    ("rc95", "RC95", 560, 1325),
]
for sid, name, tx, ty in STAGES:
    c = centroid(sid) or (tx, ty)
    lx, ly = P(*LABEL_AT[sid])
    LABELS.append({"kind": "stage", "id": sid, "t": name, "x": c[0], "y": c[1], "lx": lx, "ly": ly})
for name, x, y in [("Mokiworld", *P(1246, 570)), ("Skate Space", *from_pic(1238, 794)), ("Fortune Row", *P(880, 1095)),
                   ("Digital Gallery", *P(1300, 760)), ("VIP+ Lounge", *P(1172, 170))]:
    LABELS.append({"kind": "attraction", "id": name.lower().replace(" ", "-"), "t": name, "x": x, "y": y})
for eid, name, (x, y), ang in [("main", "Entrance", P(1106, 1428), STREET_ANGLE), ("vip", "VIP Entrance", P(612, 1300), AVENUE_ANGLE),
                               ("vipplus", "VIP+ Entrance", P(1062, 365), AVENUE_ANGLE)]:
    LABELS.append({"kind": "entrance", "id": eid, "t": name, "x": x, "y": y, "dir": ang})
LABELS.append({"kind": "place", "id": "access-center", "t": "Access Center", "x": ACCESS[0], "y": ACCESS[1]})
for zid, _, spot in ZONES:
    if spot is None:
        continue
    x, y = P(*spot)
    LABELS.append({"kind": "zone", "id": zid, "t": "VIP", "x": x, "y": y})

# --------------------------------------------------------------------------------------------
# SVG output
# --------------------------------------------------------------------------------------------
def svg_icon(kind, x, y, r, style):
    """White disc, black glyph. GA: solid ring; GA+: double ring; VIP: dashed ring (VIP concierge: + inner ring)."""
    s = r / 12.0 * 0.82
    vip = style in ("vip", "vipring")
    ring = 'stroke-dasharray="5 3.5" stroke-width="2.5"' if vip else 'stroke-width="3.5"'
    out = [f'<circle cx="{x}" cy="{y}" r="{r + 3}" fill="#fff"/>',
           f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" stroke="#000" {ring}/>']
    if style in ("gaplus", "vipring"):
        out.append(f'<circle cx="{x}" cy="{y}" r="{r - 5}" fill="none" stroke="#000" stroke-width="1.6"/>')
    out.append(f'<g transform="translate({x - 12 * s} {y - 12 * s}) scale({s})">')
    for o in ICONS[kind]:
        col = "#fff" if o[-1] == "bg" else "#000"
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


# Fill patterns, shared with the app (MapView reads PATTERNS from map.json)
PATTERNS = {
    "h": {"kind": "lines", "gap": 8, "width": 2.0, "angle": 180 + STREET_ANGLE},  # dense, along the cross streets
    "h2": {"kind": "lines", "gap": 10, "width": 1.4, "angle": AVENUE_ANGLE},  # light, along the avenues
    "dots": {"kind": "dots", "gap": 5, "r": 1.05},                             # background screen
    "lawn": {"kind": "dots", "gap": 14, "r": 0.8, "stagger": True},            # blocks: fine texture
    "vipz": {"kind": "lines", "gap": 12, "width": 0.9, "angle": 45},            # VIP-only areas
}


def svg_defs():
    out = ["<defs>"]
    for key, p in PATTERNS.items():
        pid = {"h": "hatch", "h2": "hatch2"}.get(key, key)
        g = p["gap"]
        if p["kind"] == "lines":
            # vertical stripe rotated to the requested angle (0 deg = horizontal lines)
            out.append(f'<pattern id="{pid}" width="{g}" height="{g}" patternUnits="userSpaceOnUse" '
                       f'patternTransform="rotate({p["angle"] - 90})"><rect width="{g}" height="{g}" fill="#fff"/>'
                       f'<rect width="{p["width"]}" height="{g}" fill="#000"/></pattern>')
        else:
            h = g * 2 if p.get("stagger") else g
            dots = f'<circle cx="{g / 2}" cy="{g / 2}" r="{p["r"]}" fill="#000"/>'
            if p.get("stagger"):
                dots += f'<circle cx="0" cy="{g * 1.5}" r="{p["r"]}" fill="#000"/><circle cx="{g}" cy="{g * 1.5}" r="{p["r"]}" fill="#000"/>'
            out.append(f'<pattern id="{pid}" width="{g}" height="{h}" patternUnits="userSpaceOnUse">'
                       f'<rect width="{g}" height="{h}" fill="#fff"/>{dots}</pattern>')
    out.append("</defs>")
    return "".join(out)


def to_svg(ops_list, show_vip=False):
    col = {"b": "#000", "w": "#fff", "n": "none", "h": "url(#hatch)", "h2": "url(#hatch2)",
           "dots": "url(#dots)", "lawn": "url(#lawn)", "vipz": "url(#vipz)"}
    vx, vy, vw, vh = VIEW
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx} {vy} {vw} {vh}" width="{vw}" height="{vh}">', "<style>"]
    for key, f in FONT_FILES.items():
        with open(os.path.join(FONTS, f), "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        out.append(f'@font-face{{font-family:"{key.upper()}";src:url(data:font/ttf;base64,{b64})}}')
    out.append("</style>")
    out.append(svg_defs())
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
            if o.get("cat") == "vip" and not show_vip:
                continue
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


def svg_labels(labels):
    """Preview of the app's Mudita-style labels: white pill, thin black outline, Barlow."""
    out = []
    for lb in labels:
        k = lb["kind"]
        if k == "stage":
            x, y = lb["lx"], lb["ly"]
            size, font, h = 24, "b7", 38
        elif k == "entrance":
            a = math.radians(lb["dir"])
            tx, ty = lb["x"], lb["y"]
            x, y = tx - 120 * math.cos(a), ty - 120 * math.sin(a)
            bx, by = tx - 92 * math.cos(a), ty - 92 * math.sin(a)
            out.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{tx}" y2="{ty}" stroke="#fff" stroke-width="9"/>')
            out.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{tx}" y2="{ty}" stroke="#000" stroke-width="5"/>')
            hx1, hy1 = tx - 20 * math.cos(a - 0.5), ty - 20 * math.sin(a - 0.5)
            hx2, hy2 = tx - 20 * math.cos(a + 0.5), ty - 20 * math.sin(a + 0.5)
            out.append(f'<polygon points="{tx},{ty} {hx1:.1f},{hy1:.1f} {hx2:.1f},{hy2:.1f}" fill="#000"/>')
            size, font, h = 24, "b7", 40
        else:
            x, y = lb["x"], lb["y"]
            anchor = "middle"
            if k == "zone":
                out.append(svg_text(round(x, 1), round(y + 6, 1), "VIP", "b7", 17, "#000").replace(
                    "<text ", '<text letter-spacing="1.5" stroke="#fff" stroke-width="6" paint-order="stroke" '))
                continue
            if k == "place":  # beside its icon
                x, anchor = x + 27, "start"
            out.append(svg_text(x, y + 6, lb["t"], "b6", 18, "#000", anchor).replace(
                "<text ", '<text stroke="#fff" stroke-width="5" paint-order="stroke" stroke-linejoin="round" '))
            continue
        w = text_width(lb["t"], font, size) + h * 0.8
        out.append(f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" '
                   f'fill="#fff" stroke="#000" stroke-width="{3 if k == "entrance" else 2.2}"/>')
        out.append(svg_text(round(x, 1), round(y + size * 0.36, 1), lb["t"], font, size, "#000"))
    return "\n".join(out)


def main():
    """diagram mode writes the app assets and mockup/map*.svg; oblique mode only mockup/map-oblique*.svg."""
    assets = os.path.join(ROOT, "app", "assets")
    os.makedirs(os.path.join(ROOT, "mockup"), exist_ok=True)
    svg = to_svg(ops)
    labeled = svg.replace("</svg>", svg_labels(LABELS) + "\n</svg>")
    suffix = "" if MODE == "diagram" else "-oblique"
    with open(os.path.join(ROOT, "mockup", f"map{suffix}.svg"), "w") as f:
        f.write(svg)
    with open(os.path.join(ROOT, "mockup", f"map{suffix}-labeled.svg"), "w") as f:
        f.write(labeled)
    if MODE == "diagram":
        doc = {"view": VIEW, "ops": ops, "labels": LABELS, "patterns": PATTERNS, "fonts": FONT_FILES}
        with open(os.path.join(assets, "map.json"), "w") as f:
            json.dump(doc, f, separators=(",", ":"))
        with open(os.path.join(assets, "icons.json"), "w") as f:
            json.dump(ICONS, f, separators=(",", ":"))
    print(f"{MODE}: {len(ops)} ops, {len(LABELS)} labels")


if __name__ == "__main__":
    main()
