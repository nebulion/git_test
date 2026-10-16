"""Map projection. All geometry is defined on the ground grid of the official map (u along the avenues,
w along the cross streets). MAP_MODE=diagram (default): straight plan at TRUE SCALE, avenues horizontal,
streets vertical. MAP_MODE=oblique: the official map's slanted view, unwarped, for checking against it.

True scale: OpenStreetMap street centrelines (tools/gps_calibrate.py) show the official map squeezes
some blocks, and the street grid jogs at NW 5th Ave (east of it the streets sit ~44 m further north).
WARP_U / W_SCALE move every point to real-world proportions (3.456 map units per metre)."""
import math
import os

MODE = os.environ.get("MAP_MODE", "diagram")
K0, S0 = 0.2586, 0.044                     # the official map's slant: picture = (u - K0*w, S0*u + w)
K, S = (0.0, 0.0) if MODE == "diagram" else (K0, S0)
STREET_ANGLE = -math.degrees(math.atan2(1, K))   # cross streets (-90 in the diagram)
AVENUE_ANGLE = math.degrees(math.atan(S))        # avenues (0 in the diagram)

UNITS_PER_M = 3.456
# map u -> true u, separately east of NW 5th Ave (w <= 840) and west of it (w >= 881); blended across the avenue
WARP_U = {
    "east": [(678, 606.1), (890, 859.5), (1047, 1051.3), (1505, 1517.0)],   # NW 24th St, 23rd St, 22nd Ln, 22nd St
    "west": [(434, 403.6), (636, 658.5), (1002, 1002.0), (1341, 1350.0)],   # NW 25th St, 24th St, 23rd St, 22nd St
}
W_AXIS, W_SCALE = 860, (1559.1 - 860) / 544                                 # NW 5th Ave centre; 5th->6th Ave is 202 m


def _interp(knots, v):
    i = 0
    while i < len(knots) - 2 and v > knots[i + 1][0]:
        i += 1
    (a0, b0), (a1, b1) = knots[i], knots[i + 1]
    return b0 + (v - a0) * (b1 - b0) / (a1 - a0)


def warp(u, w):
    # which side of NW 5th Ave: east (w <= 840) / west (w >= 881), blended across the avenue itself.
    # The Isotropic lot and NW 25th St (u < 640) belong to the west side on the official map.
    t = 1.0 if (u < 640 and w >= 700) else min(max((w - 840) / 41.0, 0.0), 1.0)
    u2 = (1 - t) * _interp(WARP_U["east"], u) + t * _interp(WARP_U["west"], u)
    return u2, W_AXIS + (w - W_AXIS) * W_SCALE


def P(u, w):
    if MODE == "diagram":
        u, w = warp(u, w)
    return (round(u - K * w, 1), round(S * u + w, 1))


def UV0(x, y):
    """A point measured on the official map (picture coordinates) -> ground grid."""
    u = (x + K0 * y) / (1 + K0 * S0)
    return u, y - S0 * u


def from_pic(x, y):
    return P(*UV0(x, y))
