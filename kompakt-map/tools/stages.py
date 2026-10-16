"""Stage drawings for the B/W map, recreated from the official map's artwork.

Each stage is a set of flat parts in reference coordinates (see build_map.py), drawn in one of
these styles:
  floor   dance floor / stage field: dashed outline
  roof    stage roof or dark structure: solid black
  side    side wall / open structure: hatched
  screen  LED screen or pale panel: white with outline
  struct  building or platform: white with outline
Parts come from two sources: outlines traced from the hi-res stitch by tools/trace_stages.py
(TRACED: stage/part names taken from source/map/stage_parts.json) and outlines read by hand
off gridded close-ups (tools/stage_crops.py) where the artwork is a 3D render the tracer can't
separate. Stage labels are a separate layer (build_map.STAGES) and don't depend on these shapes.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TRACED = {("grand-central", "stage"), ("grand-central", "deck"), ("grand-central", "screen-r"),
          ("iii-points-radio", "box"), ("rc95", "booth")}

# (stage, part, style, shape); shape is a point list or ("ellipse", cx, cy, rx, ry)
HAND = [
    # Mind Melt: big black stage with two side screens, light beams and a mirror ball
    ("mind-melt", "body", "roof", [(975, 434), (987.5, 399), (1045, 391), (1117.5, 419), (1110, 457.5), (1180, 475),
                                   (1180, 497.5), (1030, 512.5), (927.5, 501), (927.5, 460), (975, 457.5)]),
    ("mind-melt", "screen-l", "screen", [(936, 409), (976, 412.5), (975, 457.5), (937.5, 454)]),
    ("mind-melt", "screen-r", "screen", [(1121, 420), (1166, 422.5), (1176, 476), (1125, 472.5)]),
    ("mind-melt", "logo", "screen", [(1022.5, 430), (1047.5, 430), (1035, 450)]),
    ("mind-melt", "ball", "screen", ("ellipse", 1003, 522, 9, 9)),
    # Sector 3: teardrop field with the arched stage roof at its foot
    ("sec3", "floor", "floor", [(858, 1122), (856, 1060), (856, 985), (862, 958), (876, 942), (898, 934), (925, 934),
                                (952, 940), (975, 956), (996, 982), (1012, 1012), (1028, 1040), (1040, 1062),
                                (1040, 1082), (1030, 1100)]),
    ("sec3", "roof", "roof", [(875, 1122.5), (907.5, 1110), (920, 1100), (965, 1100), (977.5, 1107.5), (1015, 1100),
                              (1031, 1137.5), (900, 1180), (877.5, 1150)]),
    # Grand Central: oval floor, stage (traced) and left screen
    ("grand-central", "floor", "floor", ("ellipse", 1192, 1194, 103, 66)),
    ("grand-central", "screen-l", "screen", [(1102.5, 1172.5), (1114, 1177.5), (1115, 1230), (1104, 1225)]),
    # Vertex: round floor and the L-shaped wall
    ("vertex", "floor", "floor", ("ellipse", 1318.5, 1020, 76, 65)),
    ("vertex", "front", "side", [(1252, 1066.5), (1382.5, 1072.5), (1379, 1100), (1250, 1093)]),
    ("vertex", "side", "side", [(1392.5, 979), (1402, 1000), (1392, 1097), (1379, 1100), (1382.5, 1072.5)]),
    ("vertex", "top", "roof", [(1375, 975), (1392.5, 979), (1382.5, 1072.5), (1252, 1066.5), (1253, 1051), (1365, 1056)]),
    # Isotropic: paved floor and the arched purple roof
    ("isotropic", "floor", "floor", [(281, 896), (376, 898), (358, 1045), (250, 1040)]),
    ("isotropic", "roof", "roof", [(204, 1021), (246, 1014), (252.5, 1002.5), (267.5, 995), (292.5, 993.5), (310, 1001),
                                   (315, 1012.5), (342.5, 1021), (335, 1051), (205, 1049)]),
    # Halo 88 building and the Fortune Row structure in front of it
    ("halo-88", "top", "struct", [(400, 1047), (562, 1032), (545, 1160), (375, 1150)]),
    ("halo-88", "front", "struct", [(375, 1150), (530, 1160), (527, 1212), (372, 1195)]),
    ("fortune-row", "building", "side", [(565, 1027.5), (677.5, 1035), (660, 1200), (537.5, 1180)]),
    # RC95: pink stage field and the booth (traced) with its screen
    ("rc95", "floor", "floor", [(518, 1282), (650, 1288), (632, 1388), (512, 1380)]),
    ("rc95", "screen", "screen", [(545, 1397.5), (572.5, 1398.5), (572.5, 1407), (545, 1406)]),
    # Door IV platform, the building behind it and the arch gateway
    ("door-iv", "platform", "struct", [(805, 860), (897.5, 862.5), (891, 882.5), (804, 882.5)]),
    ("door-iv", "building", "side", [(867.5, 722), (924, 738), (932.5, 822), (857.5, 810), (855, 772)]),
    ("door-iv", "tower-l", "struct", [(925, 722), (960, 717), (962.5, 822), (927.5, 820)]),
    ("door-iv", "bridge", "side", [(960, 745), (1015, 745), (1015, 768), (960, 768)]),
    ("door-iv", "tower-r", "struct", [(1012.5, 717), (1052.5, 722), (1045, 822), (1015, 820)]),
    # Player's Club building
    ("players-club", "building", "struct", [(760, 602.5), (892.5, 617.5), (887.5, 670), (762.5, 655)]),
    # ::444:: room with the Unforeseen triangle in front
    ("444", "room", "struct", [(1188, 604), (1292, 604), (1300, 752), (1196, 752)]),
    ("unforeseen", "triangle", "struct", [(1247, 662), (1279, 737), (1215, 737)]),
    # S3QUENC3 glass cube with the dance floor inside
    ("s3qu3nce", "glass", "floor", [(500, 780), (575, 785), (570, 865), (500, 860)]),
    ("s3qu3nce", "floor", "roof", [(502.5, 782.5), (554, 785), (550, 820), (502.5, 817.5)]),
]

# Other structures (not stages): (name, part, style, shape)
OTHER = [
    # security lanes at the main entrance: fenced box with gate triangles
    ("lanes", "box", "struct", [(705, 1342), (822, 1344), (800, 1492), (683, 1488)]),
    *[("lanes", f"fence{i}", "line", [(717 + 10 * i, 1374), (727 + 10 * i, 1338)]) for i in range(8)],
    *[("lanes", f"gate{r}{c}", "tri", [(712 + 30 * c - 4 * r, 1440 + 18 * r), (728 + 30 * c - 4 * r, 1426 + 18 * r),
                                        (744 + 30 * c - 4 * r, 1440 + 18 * r)]) for r in range(3) for c in range(3)],
    # VIP area west of RC95: bar tent, purple VIP floor, viewing platform
    ("vip-area", "tent", "struct", [(340, 1228), (532, 1232), (526, 1290), (332, 1285)]),
    ("vip-area", "floor", "floor", [(332, 1292), (510, 1296), (500, 1420), (318, 1415)]),
    ("vip-area", "viewing", "struct", [(462, 1355), (526, 1357), (522, 1398), (457, 1396)]),
    # Player's Club scaffold tower
    ("players-club", "scaffold", "struct", [(886, 568), (935, 563), (940, 665), (889, 668)]),
    ("players-club", "scaffold-x1", "line", [(886, 568), (940, 665)]),
    ("players-club", "scaffold-x2", "line", [(935, 563), (889, 668)]),
    ("players-club", "scaffold-mid", "line", [(888, 616), (938, 612)]),
    # Digital Gallery building (the ::444:: room is part of it) and the skate space
    ("digital-gallery", "building", "struct", [(1100, 614), (1188, 606), (1196, 752), (1204, 770), (1196, 880),
                                                (1046, 878), (1040, 820), (1062, 702)]),
    # Mokiworld seating floor
    ("mokiworld", "floor", "floor", [(1062, 606), (1137, 612), (1126, 700), (1050, 694)]),
    # small DJ booth at the NW corner of the Sector 3 block
    ("sec3-booth", "box", "struct", [(818, 913), (849, 917), (845, 941), (814, 937)]),
    # shuttle bus
    ("bus", "body", "struct", [(1125, 1069), (1156, 1078), (1146, 1128), (1112, 1122)]),
    ("bus", "window", "line", [(1115, 1108), (1148, 1114)]),
]

ORDER = {"floor": 0, "struct": 1, "side": 2, "roof": 2, "screen": 3, "line": 4, "tri": 4}


def area(pts):
    return abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2


def shapes():
    """All stage parts as (stage, part, style, shape), floors first."""
    out = list(HAND) + list(OTHER)
    traced = json.load(open(os.path.join(ROOT, "source", "map", "stage_parts.json")))
    best = {}
    for t in traced:
        key = (t["stage"], t["part"])
        if key in TRACED and (key not in best or area(t["pts"]) > area(best[key]["pts"])):
            best[key] = t
    for (stage, part), t in best.items():
        out.append((stage, part, t["style"], [tuple(p) for p in t["pts"]]))
    return sorted(out, key=lambda s: ORDER[s[2]])
