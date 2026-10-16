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


def turn(local, cu, cw, deg):
    """Ground-plane rotation: local (du, dw) offsets rotated by deg around (cu, cw), to picture points."""
    a = math.radians(deg)
    return [P(cu + du * math.cos(a) - dw * math.sin(a), cw + du * math.sin(a) + dw * math.cos(a)) for du, dw in local]


def rrect(cu, cw, lu, lw, deg=0):
    """Rectangle lu x lw centred on (cu, cw), rotated by deg on the ground (angles measured on the original)."""
    return turn([(-lu / 2, -lw / 2), (lu / 2, -lw / 2), (lu / 2, lw / 2), (-lu / 2, lw / 2)], cu, cw, deg)


def rarch(cu, cw, lu, lw, bump, rise, deg, n=16):
    """Arched stage roof (bump on the back side) centred on (cu, cw), rotated by deg."""
    pts = [(-lu / 2, lw / 2), (-lu / 2, -lw / 2), (-bump / 2, -lw / 2)]
    for i in range(1, n):
        a = math.pi - math.pi * i / n
        pts.append((bump / 2 * math.cos(a), -lw / 2 - rise * math.sin(a)))
    pts += [(bump / 2, -lw / 2), (lu / 2, -lw / 2), (lu / 2, lw / 2)]
    return turn(pts, cu, cw, deg)


def smooth(pts, rounds=3):
    """Chaikin corner cutting on a closed picture-space polygon."""
    for _ in range(rounds):
        out = []
        for i in range(len(pts)):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
            out += [(round(0.75 * x0 + 0.25 * x1, 1), round(0.75 * y0 + 0.25 * y1, 1)),
                    (round(0.25 * x0 + 0.75 * x1, 1), round(0.25 * y0 + 0.75 * y1, 1))]
        pts = out
    return pts


# Sector 3 field as drawn on the original (picture coordinates), smoothed
SEC3_FIELD = smooth([(858, 1122), (856, 1060), (856, 985), (862, 958), (876, 942), (898, 934), (925, 934), (952, 940),
                     (975, 956), (996, 982), (1012, 1012), (1028, 1040), (1040, 1062), (1040, 1082), (1030, 1100),
                     (990, 1112), (940, 1118)])


# (stage or structure id, part, style, points)
PARTS = [
    # Mind Melt (main stage): big stage, wide open floor in front
    ("mind-melt", "floor", "floor", rect(1045, 450, 1285, 560)),
    ("mind-melt", "stage", "stage", [P(1088, 348), P(1212, 348), P(1212, 400), P(1284, 400), P(1284, 440),
                                     P(1036, 440), P(1036, 400), P(1088, 400)]),
    ("mind-melt", "screen-l", "bldg", rect(1040, 372, 1082, 396)),
    ("mind-melt", "screen-r", "bldg", rect(1218, 372, 1280, 396)),
    # Player's Club: building with its stage on the east end; scaffold tower
    ("players-club", "building", "bldg", rrect(977, 593, 140, 52, 3.8)),
    ("players-club", "stage", "stage", turn([(36, -24), (66, -24), (66, 24), (36, 24)], 977, 593, 3.8)),
    ("players-club", "scaffold", "bldg", rect(1052, 572, 1099, 622)),
    ("players-club", "x1", "detail", line(1052, 572, 1099, 622)),
    ("players-club", "x2", "detail", line(1099, 572, 1052, 622)),
    # Mokiworld seating, Digital Gallery building holding ::444:: (north room) and Unforeseen (south room)
    ("digital-gallery", "building", "bldg", [P(1320, 545), P(1478, 545), P(1478, 822), P(1232, 822),
                                              P(1232, 702), P(1320, 702)]),
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
    ("halo-88", "building", "bldg", rrect(744, 1062, 160, 122, -6)),
    ("halo-88", "stage", "stage", turn([(-76, -55), (-50, -55), (-50, 55), (-76, 55)], 744, 1062, -6)),
    ("fortune-row", "structure", "bldg", rect(824, 991, 959, 1158)),
    ("iii-points-radio", "stage", "stage", rrect(936, 893, 58, 22, 25)),
    # VIP area west of RC95: bar tent, VIP floor, viewing platform; RC95 floor and booth
    ("vip-area", "tent", "bldg", rect(652, 1196, 848, 1252)),
    ("vip-area", "viewing", "bldg", rect(803, 1320, 836, 1360)),
    ("rc95", "floor", "floor", rect(842, 1245, 980, 1345)),
    ("rc95", "stage", "stage", rect(868, 1345, 950, 1382)),
    # Sector 3: teardrop field and arched stage
    ("sec3", "floor", "floor", SEC3_FIELD),
    ("sec3", "stage", "stage", rarch(1229, 1086, 150, 46, 70, 16, -22)),
    ("sec3", "speaker-l", "bldg", turn([(-90, -8), (-78, -8), (-78, 8), (-90, 8)], 1229, 1086, -22)),
    ("sec3", "speaker-r", "bldg", turn([(78, -8), (90, -8), (90, 8), (78, 8)], 1229, 1086, -22)),
    # Entrance security lanes
    ("lanes", "box", "bldg", rect(1040, 1293, 1172, 1440)),
    *[("lanes", f"lane{i}", "detail", line(1040 + 22 * i, 1330, 1040 + 22 * i, 1440)) for i in range(1, 6)],
    # Vertex: round floor and the L-shaped stage wall
    ("vertex", "floor", "floor", ellipse(1556, 960, 84, 66)),
    ("vertex", "stage", "stage", [P(1508, 970), P(1616, 970), P(1626, 904), P(1658, 904), P(1648, 1000),
                                  P(1508, 1000)]),
    # Grand Central: oval floor, stage on its west end
    ("grand-central", "floor", "floor", ellipse(1497, 1146, 118, 66)),
    ("grand-central", "stage", "stage", rrect(1440, 1157, 92, 40, 31)),
    ("grand-central", "deck", "stage", rrect(1432, 1189, 78, 22, 31)),
    ("grand-central", "screen-l", "bldg", turn([(-56, -20), (-46, -20), (-46, 28), (-56, 28)], 1440, 1165, 31)),
    ("grand-central", "screen-r", "bldg", turn([(46, -20), (56, -20), (56, 28), (46, 28)], 1440, 1165, 31)),
]

# VIP-only areas (purple on the original), measured from the hi-res map: (id, ground polygon, label spot)
ZONES = [
    ("vip-isotropic", [P(458, 846), P(505, 846), P(505, 1035), P(612, 1035), P(612, 1106), P(458, 1106)], (481, 940)),
    ("vip-players", rect(912, 408, 1082, 560), (960, 470)),
    ("vip-tables", rect(1239, 565, 1318, 697), (1278, 600)),
    ("vip-sec3", rect(1030, 1037, 1149, 1139), (1112, 1128)),
    ("vip-rc95", rect(662, 1255, 842, 1381), (700, 1300)),
    ("vip-lounge", rect(1068, 128, 1276, 396), None),
]

# label spot per stage (ground coordinates): inside the dance floor, or clear space beside the stage
LABEL_AT = {
    "mind-melt": (1165, 508), "sec3": (1200, 965), "grand-central": (1525, 1146), "vertex": (1548, 935),
    "isotropic": (560, 922), "rc95": (911, 1290), "s3qu3nce": (781, 696), "halo-88": (752, 1060),
    "iii-points-radio": (932, 930), "players-club": (972, 594), "door-iv": (985, 760),
    "444": (1385, 582), "unforeseen": (1385, 655),
}


def shapes():
    order = {"zone": -1, "floor": 0, "bldg": 1, "stage": 2, "detail": 3}
    parts = PARTS + [(zid, "zone", "zone", pts) for zid, pts, _ in ZONES]
    return sorted(parts, key=lambda p: order[p[2]])
