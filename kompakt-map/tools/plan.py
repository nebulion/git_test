"""Flat plan drawings of the stages and other structures (v5).

Everything is defined in ground-grid coordinates (u along the avenues, w along the cross streets),
so every edge runs parallel to the streets; curves are true ellipses/arcs on the grid. Sizes and
positions were measured from the official map (tools/stage_crops.py close-ups).

One visual language:
  stage   the stage itself: dense grid hatch (sized like the real stage, so Mind Melt is biggest)
  floor   its dance floor: white with a dashed edge
  bldg    any other building, tent or structure: plain outline, no fill pattern
  detail  thin line
LABEL_AT gives each stage a label spot (inside its dance floor or in clear space next to it).
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


# (stage or structure id, part, style, points)
PARTS = [
    # Mind Melt (main stage): big stage, wide open floor in front
    ("mind-melt", "floor", "floor", rect(1045, 450, 1285, 560)),
    ("mind-melt", "stage", "stage", [P(1088, 348), P(1212, 348), P(1212, 400), P(1284, 400), P(1284, 440),
                                     P(1036, 440), P(1036, 400), P(1088, 400)]),
    # Player's Club: building with its stage on the east end; scaffold tower
    ("players-club", "building", "bldg", rect(906, 563, 1046, 624)),
    ("players-club", "stage", "stage", rect(1016, 568, 1042, 619)),
    ("players-club", "scaffold", "bldg", rect(1052, 572, 1099, 622)),
    ("players-club", "x1", "detail", line(1052, 572, 1099, 622)),
    ("players-club", "x2", "detail", line(1099, 572, 1052, 622)),
    # Mokiworld seating, Digital Gallery building holding ::444:: (north room) and Unforeseen (south room)
    ("mokiworld", "area", "bldg", rect(1205, 553, 1288, 640)),
    ("digital-gallery", "building", "bldg", [P(1292, 545), P(1478, 545), P(1478, 822), P(1232, 822),
                                              P(1232, 652), P(1292, 652)]),
    ("444", "room", "bldg", rect(1336, 550, 1472, 615)),
    ("444", "stage", "stage", rect(1440, 556, 1466, 609)),
    ("unforeseen", "room", "bldg", rect(1336, 619, 1472, 690)),
    ("unforeseen", "stage", "stage", rect(1440, 625, 1466, 684)),
    # Door IV: DJ platform in front of the building and the arch towers
    ("door-iv", "floor", "floor", rect(1012, 776, 1112, 812)),
    ("door-iv", "stage", "stage", rect(1016, 814, 1108, 836)),
    ("door-iv", "building", "bldg", rect(1042, 700, 1098, 772)),
    ("door-iv", "tower-l", "bldg", rect(1102, 728, 1140, 772)),
    ("door-iv", "bridge", "bldg", rect(1140, 742, 1190, 758)),
    ("door-iv", "tower-r", "bldg", rect(1190, 728, 1232, 768)),
    # S3QUENC3 glass cube: dance floor inside, stage at the back
    ("s3qu3nce", "floor", "floor", rect(694, 749, 785, 830)),
    ("s3qu3nce", "stage", "stage", rect(700, 754, 779, 772)),
    # Isotropic: paved floor and arched stage
    ("isotropic", "floor", "floor", rect(507, 872, 612, 968)),
    ("isotropic", "stage", "stage", arch(466, 990, 600, 1028, 500, 562, 22)),
    # Halo 88 (indoor, stage along the west wall), Fortune Row structure, III Points Radio booth
    ("halo-88", "building", "bldg", rect(663, 996, 822, 1123)),
    ("halo-88", "stage", "stage", rect(668, 1010, 696, 1110)),
    ("fortune-row", "structure", "bldg", rect(824, 991, 959, 1158)),
    ("iii-points-radio", "stage", "stage", rect(905, 876, 960, 900)),
    # VIP area west of RC95: bar tent, VIP floor, viewing platform; RC95 floor and booth
    ("vip-area", "tent", "bldg", rect(652, 1196, 848, 1252)),
    ("vip-area", "viewing", "bldg", rect(803, 1320, 836, 1360)),
    ("rc95", "floor", "floor", rect(842, 1245, 980, 1345)),
    ("rc95", "stage", "stage", rect(868, 1345, 950, 1382)),
    # Sector 3: teardrop field and arched stage
    ("sec3", "floor", "floor", stadium_top(1100, 885, 1302, 1068)),
    ("sec3", "stage", "stage", arch(1150, 1068, 1310, 1122, 1188, 1262, 16)),
    # Entrance security lanes
    ("lanes", "box", "bldg", rect(1040, 1293, 1172, 1440)),
    *[("lanes", f"lane{i}", "detail", line(1040 + 22 * i, 1330, 1040 + 22 * i, 1440)) for i in range(1, 6)],
    # Vertex: round floor and the L-shaped stage wall
    ("vertex", "floor", "floor", ellipse(1556, 960, 84, 66)),
    ("vertex", "stage", "stage", [P(1508, 970), P(1616, 970), P(1616, 904), P(1648, 904), P(1648, 1000),
                                  P(1508, 1000)]),
    # Grand Central: oval floor, stage on its west end
    ("grand-central", "floor", "floor", ellipse(1497, 1146, 118, 66)),
    ("grand-central", "stage", "stage", rect(1386, 1112, 1452, 1188)),
]

# label spot per stage (ground coordinates): inside the dance floor, or clear space beside the stage
LABEL_AT = {
    "mind-melt": (1165, 508), "sec3": (1200, 965), "grand-central": (1525, 1146), "vertex": (1548, 935),
    "isotropic": (560, 922), "rc95": (911, 1290), "s3qu3nce": (781, 696), "halo-88": (752, 1060),
    "iii-points-radio": (932, 930), "players-club": (972, 594), "door-iv": (985, 760),
    "444": (1385, 582), "unforeseen": (1385, 655),
}


def shapes():
    order = {"floor": 0, "bldg": 1, "stage": 2, "detail": 3}
    return sorted(PARTS, key=lambda p: order[p[2]])
