"""land_at: the land in metres (towns_spec §2.1), the Python twin of the viewer's civ/viewer/demo/land.js.

One deterministic function of a land description (coarse heights, rivers and streams as curves of a real width,
forests as polygons, clearings): the ground's height, the water under a point, wetness (reed margins) and tree cover.
Never stored; the engine and the viewer ask the same function, so the world they hold and the world they draw are one.
Both are tested on the same points (tests/test_land_at.py). Coordinates: X east, Y south, metres.

The hash and noise are integer arithmetic, written to give the same numbers in both languages.
"""
import math

M32 = 0xFFFFFFFF


def _imul(a, b):
    return ((a & M32) * (b & M32)) & M32


def hash2(i, j, seed=0):
    h = (_imul(i, 374761393) + _imul(j, 668265263) + _imul(seed, 2246822519)) & M32
    h = _imul(h ^ (h >> 13), 1274126177)
    h ^= h >> 16
    return h / 4294967296


def vnoise(x, y, seed=0):
    i, j = math.floor(x), math.floor(y)
    u, v = x - i, y - j
    u, v = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
    a, b, c, d = hash2(i, j, seed), hash2(i + 1, j, seed), hash2(i, j + 1, seed), hash2(i + 1, j + 1, seed)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return a + (b - a) * t


class Curve:
    """A polyline with a width at each point; asks "how far, how wide, how far along" quickly."""

    def __init__(self, pts, cell=200):
        self.p = [(q[0], q[1], q[2] if len(q) > 2 else 0) for q in pts]
        self.s = [0.0]
        for k in range(1, len(self.p)):
            self.s.append(self.s[-1] + math.hypot(self.p[k][0] - self.p[k - 1][0], self.p[k][1] - self.p[k - 1][1]))
        self.length = self.s[-1]
        self.max_w = max(q[2] for q in self.p)
        self.cell, self.bins = cell, {}
        pad = self.max_w + 120
        for k in range(len(self.p) - 1):
            (ax, ay, _), (bx, by, _) = self.p[k], self.p[k + 1]
            for i in range(math.floor((min(ax, bx) - pad) / cell), math.floor((max(ax, bx) + pad) / cell) + 1):
                for j in range(math.floor((min(ay, by) - pad) / cell), math.floor((max(ay, by) + pad) / cell) + 1):
                    self.bins.setdefault((i, j), []).append(k)

    def near(self, X, Y):
        """(distance, width there, distance along) to the nearest point; distance inf beyond the padding."""
        best = (math.inf, 0.0, 0.0)
        for k in self.bins.get((math.floor(X / self.cell), math.floor(Y / self.cell)), ()):
            a, b = self.p[k], self.p[k + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            t = ((X - a[0]) * dx + (Y - a[1]) * dy) / L2 if L2 > 0 else 0.0
            t = 0.0 if t < 0 else 1.0 if t > 1 else t
            d = math.hypot(X - a[0] - dx * t, Y - a[1] - dy * t)
            if d < best[0]:
                best = (d, a[2] + (b[2] - a[2]) * t, self.s[k] + (self.s[k + 1] - self.s[k]) * t)
        return best

    def at(self, s):
        s = max(0.0, min(self.length, s))
        k = 0
        while k < len(self.s) - 2 and self.s[k + 1] < s:
            k += 1
        a, b = self.p[k], self.p[k + 1]
        L = (self.s[k + 1] - self.s[k]) or 1.0
        t = (s - self.s[k]) / L
        return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t


def poly_sd(poly, X, Y):
    """Signed distance to a polygon, negative inside."""
    d, inside = math.inf, False
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i - 1]
        bx, by = poly[i]
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy)))
        d = min(d, math.hypot(X - ax - dx * t, Y - ay - dy * t))
        if (ay > Y) != (by > Y) and X < ax + (Y - ay) / (by - ay) * dx:
            inside = not inside
    return -d if inside else d


def _cr(p0, p1, p2, p3, t):
    return p1 + 0.5 * t * (p2 - p0 + t * (2 * p0 - 5 * p1 + 4 * p2 - p3 + t * (3 * (p1 - p2) + p3 - p0)))


class Ground:
    __slots__ = ("h", "water", "wet", "level", "chan")

    def __init__(self, h, water, wet, level, chan):
        self.h, self.water, self.wet, self.level, self.chan = h, water, wet, level, chan


class Land:
    """The land of a description (the shape demo/river_village.json's `land` holds)."""

    def __init__(self, L):
        self.L = L
        self.W = L["water_level"]
        self.hg = L["heights"]
        self.river = Curve(L["river"])
        self.stream = Curve(L["stream"])
        self.forests = []
        for f in L["forest"]:
            xs, ys = [p[0] for p in f["pts"]], [p[1] for p in f["pts"]]
            self.forests.append((f["pts"], f["density"], (min(xs) - 400, min(ys) - 400, max(xs) + 400, max(ys) + 400)))
        self.clearings = L.get("clearings", [])
        self.flat = L.get("flat")

    def coarse(self, X, Y):
        H = self.hg
        fx, fy = (X - H["x0"]) / H["step"], (Y - H["y0"]) / H["step"]
        i, j = math.floor(fx), math.floor(fy)
        u, v = fx - i, fy - j
        hh, nx, ny = H["h"], H["nx"], H["ny"]

        def g(a, b):
            return hh[max(0, min(ny - 1, b))][max(0, min(nx - 1, a))]

        def row(jj):
            return _cr(g(i - 1, jj), g(i, jj), g(i + 1, jj), g(i + 2, jj), u)
        return _cr(row(j - 1), row(j), row(j + 1), row(j + 2), v)

    def natural(self, X, Y):
        h = self.coarse(X, Y)
        amp = 1.0
        if self.flat:
            fx, fy, fr = self.flat
            amp = 0.25 + 0.75 * smoothstep(fr * 0.6, fr * 1.4, math.hypot(X - fx, Y - fy))
        h += amp * ((vnoise(X / 170, Y / 170, 11) - 0.5) * 3.2 + (vnoise(X / 55, Y / 55, 12) - 0.5) * 1.1
                    + (vnoise(X / 19, Y / 19, 13) - 0.5) * 0.3)
        return max(h, self.W + 1.3)

    def stream_level(self, s):
        return self.W + 0.1 + 0.45 * smoothstep(0, 320, self.stream.length - s)

    def ground(self, X, Y):
        h = self.natural(X, Y)
        water, wet, level, chan = 0.0, 0.0, self.W, math.inf
        d, w, s = self.river.near(X, Y)
        if d < math.inf:
            hw, edge = w / 2, self.W + 0.35
            hc = edge - (edge - (self.W - 2.6)) * (1 - (d / hw) ** 2) if d < hw else mix(edge, h, smoothstep(hw, hw + 45, d))
            h = min(h, hc)
            chan = d - hw
            wet = max(wet, 1 - smoothstep(hw + 2, hw + 22, d))
            if d < hw:
                water, level = self.W - h, self.W
        d, w, s = self.stream.near(X, Y)
        if d < math.inf:
            hw, lv = w / 2, self.stream_level(s)
            edge = lv + 0.25
            hc = edge - (edge - (lv - 0.9)) * (1 - (d / hw) ** 2) if d < hw else mix(edge, h, smoothstep(hw, hw + 14, d))
            h = min(h, hc)
            chan = min(chan, d - hw)
            wet = max(wet, 1 - smoothstep(hw + 1, hw + 7, d))
            if d < hw:
                water, level = max(water, lv - h), lv
        return Ground(h, water, wet, level, chan)

    def height(self, X, Y):
        return self.ground(X, Y).h

    def tree_cover(self, X, Y, chan=math.inf):
        cover = 0.0
        for pts, density, (x0, y0, x1, y1) in self.forests:
            if X < x0 or X > x1 or Y < y0 or Y > y1:
                continue
            sd = poly_sd(pts, X, Y) + (vnoise(X / 140, Y / 140, 21) - 0.5) * 170 + (vnoise(X / 40, Y / 40, 22) - 0.5) * 40
            cover = max(cover, density * (1 - smoothstep(-90, 70, sd)))
        for cx, cy, cr in self.clearings:
            cover *= smoothstep(cr * 0.75, cr * 1.35, math.hypot(X - cx, Y - cy))
        if self.flat:
            fx, fy, fr = self.flat
            cover *= smoothstep(fr * 0.9, fr * 1.6, math.hypot(X - fx, Y - fy))
        return cover * smoothstep(3, 25, chan)

    def at(self, X, Y):
        """Everything at a point: {h, water, wet, level, chan, tree}."""
        g = self.ground(X, Y)
        return {"h": g.h, "water": g.water, "wet": g.wet, "level": g.level, "chan": g.chan,
                "tree": self.tree_cover(X, Y, g.chan)}
