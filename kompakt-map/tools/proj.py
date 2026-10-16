"""Map projection. All geometry is defined on the ground grid (u along the avenues, w along the
cross streets). MAP_MODE=diagram (default): straight plan, avenues horizontal, streets vertical.
MAP_MODE=oblique: the official map's slanted view, used to check geometry against the original."""
import math
import os

MODE = os.environ.get("MAP_MODE", "diagram")
K0, S0 = 0.2586, 0.044                     # the official map's slant: picture = (u - K0*w, S0*u + w)
K, S = (0.0, 0.0) if MODE == "diagram" else (K0, S0)
STREET_ANGLE = -math.degrees(math.atan2(1, K))   # cross streets (-90 in the diagram)
AVENUE_ANGLE = math.degrees(math.atan(S))        # avenues (0 in the diagram)


def P(u, w):
    return (round(u - K * w, 1), round(S * u + w, 1))


def UV0(x, y):
    """A point measured on the official map (picture coordinates) -> ground grid."""
    u = (x + K0 * y) / (1 + K0 * S0)
    return u, y - S0 * u


def from_pic(x, y):
    return P(*UV0(x, y))
