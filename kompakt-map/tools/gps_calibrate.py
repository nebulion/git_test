"""GPS calibration for the true-scale diagram map (see tools/proj.py).

Street centrelines from OpenStreetMap (source/osm/streets.json) give real positions, measured
separately east and west of NW 5th Ave because the grid jogs there. The diagram is drawn at true scale,
so GPS -> map is linear: u from metres north, w from metres east, anchored at NW 23rd St (west side)
and NW 5th Ave. Writes app/assets/gps.json and prints how well the map's streets line up.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("MAP_MODE", "diagram")
from proj import UNITS_PER_M, warp  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
osm = json.load(open(os.path.join(ROOT, "source", "osm", "streets.json")))
LAT0, LON0 = 25.799, -80.203
KX = 111320 * math.cos(math.radians(LAT0))
KY = 110574


def pts(name, xmin, xmax, ymin=-400, ymax=400):
    out = []
    for e in osm["elements"]:
        if e["tags"].get("name") != name:
            continue
        for p in e["geometry"]:
            x, y = (p["lon"] - LON0) * KX, (p["lat"] - LAT0) * KY
            if xmin <= x <= xmax and ymin <= y <= ymax:
                out.append((x, y))
    return np.array(out)


def street_y(name, side):
    p = pts(name, *((-260, -12) if side == "west" else (12, 420)))
    return float(np.median(p[:, 1])) if len(p) else None


AVE5 = float(np.median(pts("Northwest 5th Avenue", -60, 40, -200, 120)[:, 0]))
AVE6 = float(np.median(pts("Northwest 6th Avenue", -260, -150, -200, 120)[:, 0]))
Y23W = street_y("Northwest 23rd Street", "west")
print(f"NW 5th Ave x={AVE5:.1f} m, NW 6th Ave x={AVE6:.1f} m ({AVE5 - AVE6:.0f} m apart)")

# GPS -> map (linear, two knots per axis keeps the app's piecewise code unchanged)
north_to_u = [[Y23W - 300, 1002 + 300 * UNITS_PER_M], [Y23W + 300, 1002 - 300 * UNITS_PER_M]]
east_to_w = [[AVE5 - 300, 860 + 300 * UNITS_PER_M], [AVE5 + 300, 860 - 300 * UNITS_PER_M]]
doc = {"lat0": LAT0, "lon0": LON0, "kx": KX, "ky": KY,
       "north_to_u": [[round(a, 2), round(b, 1)] for a, b in north_to_u],
       "east_to_w": [[round(a, 2), round(b, 1)] for a, b in east_to_w]}
json.dump(doc, open(os.path.join(ROOT, "app", "assets", "gps.json"), "w"), indent=1)


def gps_u(y):
    return 1002 - (y - Y23W) * UNITS_PER_M


# check: map street centrelines (after the true-scale warp) vs where GPS puts the real streets
checks = [("west", "Northwest 25th Street", 434), ("west", "Northwest 24th Street", 636), ("west", "Northwest 23rd Street", 1002),
          ("west", "Northwest 22nd Street", 1341), ("east", "Northwest 24th Street", 678), ("east", "Northwest 23rd Street", 890),
          ("east", "Northwest 22nd Lane", 1047), ("east", "Northwest 22nd Street", 1505)]
for side, name, u_map in checks:
    y = street_y(name, side)
    if y is None:
        print(f"{side:4s} {name:24s}  (not in OSM near the venue)")
        continue
    u_warped = warp(u_map, 1000 if side == "west" else 700)[0]
    print(f"{side:4s} {name:24s} real {y:7.1f} m  map {u_warped:7.1f}  gps {gps_u(y):7.1f}  "
          f"error {abs(u_warped - gps_u(y)) / UNITS_PER_M:4.1f} m")
w6 = warp(1000, 1404)[1]
print(f"NW 6th Ave: map {w6:.1f}  gps {860 + (AVE5 - AVE6) * UNITS_PER_M:.1f}")
mana = json.load(open(os.path.join(ROOT, "source", "osm", "mana.json")))[0]
mx, my = (float(mana["lon"]) - LON0) * KX, (float(mana["lat"]) - LAT0) * KY
print("Mana Wynwood centre -> u, w =", round(gps_u(my)), round(860 - (mx - AVE5) * UNITS_PER_M))
