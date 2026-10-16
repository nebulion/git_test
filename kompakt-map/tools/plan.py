"""Flat plan drawings of the stages and other structures (v4).

Everything is defined in ground-grid coordinates (u along the avenues, w along the cross streets),
so every edge runs parallel to the streets; curves are true ellipses/arcs on the grid. Sizes and
positions were measured from the official map (tools/stage_crops.py close-ups and the earlier
traces in tools/stages.py). Footprints only: vertical faces and screens are drawn as their base.

Styles: floor (white, dashed edge), roof (dense grid hatch), side (light grid hatch),
struct (white, medium outline), detail (thin line), tri (small white triangle).
"""
import math

K, S = 0.2586, 0.044


def P(u, w):
    return (round(u - K * w, 1), round(S * u + w, 1))


def rect(u0, w0, u1, w1):
    return [P(u0, w0), P(u1, w0), P(u1, w1), P(u0, w1)]


def ellipse(cu, cw, ru, rw, n=48):
    return [P(cu + ru * math.cos(2 * math.pi * i / n), cw + rw * math.sin(2 * math.pi * i / n)) for i in range(n)]


def stadium_top(u0, w0, u1, w1, n=24):
    """Rectangle whose top (small w) side is a half ellipse: the Sector 3 teardrop field."""
    cu, ru = (u0 + u1) / 2, (u1 - u0) / 2
    rw = ru * 0.85
    pts = [P(u1, w1)]
    for i in range(n + 1):
        a = math.pi * i / n
        pts.append(P(cu + ru * math.cos(a), w0 + rw - rw * math.sin(a)))
    pts.append(P(u0, w1))
    return pts


def arch(u0, w0, u1, w1, au0, au1, rise, n=16):
    """Rectangle with a round bump on its top side (arched stage roofs)."""
    pts = [P(u0, w1), P(u0, w0), P(au0, w0)]
    cu, ru = (au0 + au1) / 2, (au1 - au0) / 2
    for i in range(1, n):
        a = math.pi - math.pi * i / n
        pts.append(P(cu + ru * math.cos(a), w0 - rise * math.sin(a)))
    pts += [P(au1, w0), P(u1, w0), P(u1, w1)]
    return pts


def line(u0, w0, u1, w1):
    return [P(u0, w0), P(u1, w1)]


def tri(cu, cw, s=14):
    return [P(cu - s, cw + s * 0.45), P(cu, cw - s * 0.55), P(cu + s, cw + s * 0.45)]


# (stage or structure id, part, style, points)
PARTS = [
    # Mind Melt: open front floor, low deck, roof, two side screens
    ("mind-melt", "floor", "floor", rect(1045, 462, 1285, 560)),
    ("mind-melt", "deck", "side", rect(1035, 420, 1292, 462)),
    ("mind-melt", "roof", "roof", rect(1088, 348, 1212, 440)),
    ("mind-melt", "screen-l", "struct", rect(1034, 372, 1080, 418)),
    ("mind-melt", "screen-r", "struct", rect(1220, 372, 1284, 418)),
    # Player's Club building and its scaffold tower
    ("players-club", "building", "struct", rect(906, 563, 1046, 624)),
    ("players-club", "scaffold", "struct", rect(1052, 572, 1099, 622)),
    ("players-club", "x1", "detail", line(1052, 572, 1099, 622)),
    ("players-club", "x2", "detail", line(1099, 572, 1052, 622)),
    # Mokiworld seating, Digital Gallery building with the ::444:: room and Unforeseen
    ("mokiworld", "floor", "floor", rect(1205, 553, 1288, 640)),
    ("digital-gallery", "building", "struct", [P(1292, 545), P(1478, 545), P(1478, 822), P(1232, 822),
                                                P(1232, 652), P(1292, 652)]),
    ("444", "room", "struct", rect(1336, 550, 1472, 690)),
    ("unforeseen", "triangle", "struct", tri(1421, 645, 30)),
    # Door IV: platform, building, two towers joined by a bridge
    ("door-iv", "platform", "struct", rect(1016, 814, 1108, 838)),
    ("door-iv", "building", "side", rect(1042, 700, 1098, 772)),
    ("door-iv", "tower-l", "struct", rect(1102, 728, 1140, 772)),
    ("door-iv", "bridge", "side", rect(1140, 742, 1190, 758)),
    ("door-iv", "tower-r", "struct", rect(1190, 728, 1232, 768)),
    # S3QUENC3 glass cube with the dance floor inside
    ("s3qu3nce", "cube", "struct", rect(694, 749, 785, 830)),
    ("s3qu3nce", "floor", "roof", rect(700, 754, 754, 790)),
    # Isotropic: paved floor and arched roof
    ("isotropic", "floor", "floor", rect(507, 872, 612, 968)),
    ("isotropic", "roof", "roof", arch(466, 990, 600, 1028, 500, 562, 22)),
    # Halo 88 building, Fortune Row structure, III Points Radio booth
    ("halo-88", "building", "struct", rect(663, 996, 822, 1123)),
    ("fortune-row", "structure", "side", rect(824, 991, 959, 1158)),
    ("iii-points-radio", "booth", "roof", rect(905, 876, 960, 900)),
    # VIP area west of RC95: bar tent, VIP floor, viewing platform; RC95 floor and booth
    ("vip-area", "tent", "struct", rect(652, 1196, 848, 1252)),
    ("vip-area", "floor", "floor", rect(660, 1262, 836, 1385)),
    ("vip-area", "viewing", "struct", rect(803, 1320, 836, 1360)),
    ("rc95", "floor", "floor", rect(842, 1245, 980, 1345)),
    ("rc95", "booth", "roof", rect(868, 1345, 950, 1382)),
    # Sector 3: teardrop field and arched stage roof; small booth at the block corner
    ("sec3", "floor", "floor", stadium_top(1100, 885, 1302, 1068)),
    ("sec3", "roof", "roof", arch(1150, 1068, 1310, 1122, 1188, 1262, 16)),
    # Entrance security lanes: fenced box, fence posts, gates
    ("lanes", "box", "struct", rect(1040, 1293, 1172, 1440)),
    *[("lanes", f"fence{i}", "detail", line(1056 + 10 * i, 1300, 1056 + 10 * i, 1330)) for i in range(9)],
    *[("lanes", f"gate{r}{c}", "tri", tri(1086 + 30 * c, 1386 + 18 * r, 11)) for r in range(3) for c in range(3)],
    # Vertex: round floor and the L-shaped wall
    ("vertex", "floor", "floor", ellipse(1556, 960, 84, 66)),
    ("vertex", "wall-h", "roof", rect(1508, 970, 1648, 1000)),
    ("vertex", "wall-v", "roof", rect(1616, 904, 1648, 970)),
    # Grand Central: oval floor, stage with deck and side screens
    ("grand-central", "floor", "floor", ellipse(1497, 1146, 118, 66)),
    ("grand-central", "deck", "side", rect(1392, 1166, 1452, 1188)),
    ("grand-central", "stage", "roof", rect(1398, 1118, 1446, 1166)),
    ("grand-central", "screen-l", "struct", rect(1386, 1112, 1396, 1172)),
    ("grand-central", "screen-r", "struct", rect(1448, 1112, 1458, 1172)),
]


def shapes():
    order = {"floor": 0, "struct": 1, "side": 2, "roof": 2, "detail": 3, "tri": 3}
    return sorted(PARTS, key=lambda p: order[p[2]])
