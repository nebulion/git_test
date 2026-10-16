"""Calibrate map ground-grid coordinates (u, w) against real GPS using OSM street centerlines.

Each street (E-W, constant latitude) and avenue (N-S, constant longitude) centreline is measured
from source/osm/streets.json near the venue; their intersections are paired with the same
intersections on the map grid, and an affine lat/lon -> (u, w) transform is fitted by least squares.
Writes app/assets/gps.json. Usage: python3 tools/gps_calibrate.py
"""
import json
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
osm = json.load(open(os.path.join(ROOT, "source", "osm", "streets.json")))
LAT0, LON0 = 25.799, -80.203                  # local origin
KX = 111320 * math.cos(math.radians(LAT0))     # m per degree lon
KY = 110574                                    # m per degree lat


def xy(lat, lon):
    return ((lon - LON0) * KX, (lat - LAT0) * KY)


def coords(name):
    pts = [xy(p["lat"], p["lon"]) for e in osm["elements"] if e["tags"].get("name") == name for p in e["geometry"]]
    return np.array(pts)


def street_y(name):      # E-W street: north offset (m) near the venue
    p = coords(name)
    p = p[(p[:, 0] > -400) & (p[:, 0] < 300)]
    return float(np.median(p[:, 1]))


def avenue_x(name):      # N-S avenue: east offset (m) near the venue
    p = coords(name)
    p = p[(p[:, 1] > -300) & (p[:, 1] < 400)]
    return float(np.median(p[:, 0]))


# map grid centrelines (ground units) of the same streets, south of NW 5th Ave where the map is a plain grid
MAP_STREETS = {"Northwest 24th Street": 636, "Northwest 23rd Street": 1002, "Northwest 22nd Street": 1341}
MAP_AVENUES = {"Northwest 5th Avenue": 860, "Northwest 6th Avenue": 1404}

# The official map is not to scale (24th->23rd St is 103 m, 23rd->22nd is 151 m, but both are drawn
# about the same), so instead of one affine fit each axis is mapped piecewise-linearly between the
# streets it crosses: north metres -> u (along the avenues), east metres -> w (along the streets).
U_KNOTS = sorted([(street_y("Northwest 25th Street"), 434)] + [(street_y(n), u) for n, u in MAP_STREETS.items()])
W_KNOTS = sorted([(avenue_x(n), w) for n, w in MAP_AVENUES.items()])
print("north m -> u:", [(round(a, 1), b) for a, b in U_KNOTS])
print("east m  -> w:", [(round(a, 1), b) for a, b in W_KNOTS])


def interp(knots, v):
    for (a0, b0), (a1, b1) in zip(knots, knots[1:]):
        if v <= a1 or (a1, b1) == knots[-1]:
            if v < knots[0][0]:
                (a0, b0), (a1, b1) = knots[0], knots[1]
            return b0 + (v - a0) * (b1 - b0) / (a1 - a0)


doc = {"lat0": LAT0, "lon0": LON0, "kx": KX, "ky": KY,
       "north_to_u": [[round(a, 2), b] for a, b in U_KNOTS],
       "east_to_w": [[round(a, 2), b] for a, b in W_KNOTS]}
json.dump(doc, open(os.path.join(ROOT, "app", "assets", "gps.json"), "w"), indent=1)
mana = json.load(open(os.path.join(ROOT, "source", "osm", "mana.json")))[0]
mx, my = xy(float(mana["lat"]), float(mana["lon"]))
print("Mana Wynwood centre -> u, w =", round(interp(U_KNOTS, my)), round(interp(W_KNOTS, mx)))
