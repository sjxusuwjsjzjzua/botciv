"""Plane geometry in metres for the settlement planner (x east, y south): oriented rectangles, polylines, hulls.

A rect is (X, Y, w, d, angle): its centre, its width along its front, its depth, and the way its front faces in degrees
(the front faces (sin a, cos a)). Its local axes: `across` = (cos a, -sin a) along the front, `back` = (-sin a, -cos a).
"""
import math


def axes(angle):
    a = math.radians(angle)
    return (math.cos(a), -math.sin(a)), (math.sin(a), math.cos(a))      # across, forward


def corners(r):
    X, Y, w, d, ang = r
    (ax, ay), (fx, fy) = axes(ang)
    hw, hd = w / 2, d / 2
    return [(X + ax * sx * hw + fx * sy * hd, Y + ay * sx * hw + fy * sy * hd) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _project(pts, nx, ny):
    vals = [x * nx + y * ny for x, y in pts]
    return min(vals), max(vals)


def overlap(r1, r2, gap=0.0):
    """Do two rects overlap (closer than `gap` metres counts)? Separating axes."""
    if math.hypot(r1[0] - r2[0], r1[1] - r2[1]) > (math.hypot(r1[2], r1[3]) + math.hypot(r2[2], r2[3])) / 2 + gap:
        return False
    c1, c2 = corners(r1), corners(r2)
    for r in (r1, r2):
        for n in axes(r[4]):
            a0, a1 = _project(c1, *n)
            b0, b1 = _project(c2, *n)
            if a1 + gap <= b0 or b1 + gap <= a0:
                return False
    return True


def inside(r, X, Y):
    (ax, ay), (fx, fy) = axes(r[4])
    dx, dy = X - r[0], Y - r[1]
    return abs(dx * ax + dy * ay) <= r[2] / 2 and abs(dx * fx + dy * fy) <= r[3] / 2


def to_world(r, u, v):
    """A point given in a rect's own frame (u along the front to the right, v forward from the centre)."""
    (ax, ay), (fx, fy) = axes(r[4])
    return r[0] + ax * u + fx * v, r[1] + ay * u + fy * v


def segment_rects(pts, w):
    """A polyline of width w as rects, one a segment (for overlap tests)."""
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1e-6:
            continue
        ang = math.degrees(math.atan2(-(y1 - y0), (x1 - x0)))     # across axis along the segment
        out.append(((x0 + x1) / 2, (y0 + y1) / 2, L + w, w, ang))
    return out


def length(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def at(pts, s):
    """The point and unit direction at distance s along a polyline (clamped)."""
    s = max(0.0, s)
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if s <= L or b is pts[-1]:
            t = min(1.0, s / L) if L else 0.0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ((b[0] - a[0]) / (L or 1), (b[1] - a[1]) / (L or 1))
        s -= L
    return tuple(pts[-1]), (1.0, 0.0)


def facing(dx, dy):
    """The angle whose front faces the direction (dx, dy)."""
    return math.degrees(math.atan2(dx, dy))


def hull(points):
    """Convex hull, counter-clockwise (monotone chain)."""
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in points))
    if len(pts) < 3:
        return [list(p) for p in pts]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return [list(p) for p in lower[:-1] + upper[:-1]]


def grow(poly, m):
    """A convex polygon pushed out by m metres from its centroid (a soft margin)."""
    if not poly:
        return poly
    cx, cy = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
    out = []
    for x, y in poly:
        d = math.hypot(x - cx, y - cy) or 1
        out.append([round(x + (x - cx) / d * m, 1), round(y + (y - cy) / d * m, 1)])
    return out
