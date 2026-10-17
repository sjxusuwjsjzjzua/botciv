"""Step 0's scene (docs/world5_handoff.md §5): a river village, the land around it and a forest hamlet, written in
metres as world5 will hold them (towns_spec §3: x east, y south). Writes civ/viewer/demo/river_village.json.

The village is laid out as the target picture (docs/towns_pics/target_river_gemini.jpg) and 1_river.png: long houses
in fenced plots fanning along a curving lane round the green (well and shrine), kilns east, the burial ground west,
the stream and its plank bridge south, and strips of grain, flax and fallow beyond. This is the planner's first
fixture: the same shapes the settlement planner (towns_spec §4) will produce.

Angles: a building's `angle` is in degrees; its front (door) faces (sin a, cos a) in (x, y).
"""
import json, math, os, random

OUT = os.path.join(os.path.dirname(__file__), "..", "civ", "viewer", "demo", "river_village.json")
SEED = 5
SIZE = (6000, 3000)
C = (1300.0, 1600.0)            # the green's middle
W = 10.0                        # the river's water level (m)


def r1(v):
    return round(v, 1)


def pt(x, y):
    return [r1(x), r1(y)]


def polar(a_deg, r, c=C):
    a = math.radians(a_deg)
    return c[0] + r * math.cos(a), c[1] + r * math.sin(a)


def face(fx, fy, tx, ty):
    """The angle that turns a front at (fx, fy) to face (tx, ty)."""
    return math.degrees(math.atan2(tx - fx, ty - fy))


def noise2(rng):
    g = {}
    def at(i, j):
        if (i, j) not in g:
            g[(i, j)] = rng.random()
        return g[(i, j)]
    def n(x, y):
        i, j = math.floor(x), math.floor(y)
        u, v = x - i, y - j
        u, v = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
        return (at(i, j) * (1 - u) + at(i + 1, j) * u) * (1 - v) + (at(i, j + 1) * (1 - u) + at(i + 1, j + 1) * u) * v
    return n


def land(rng):
    n = noise2(rng)
    step = 250
    # the coarse heights reach past the scene's edge, so the land runs on into the haze
    x0, y0, nx, ny = -3000, -3000, 49, 37
    hills = [((2450, 2500), 34, 480), ((600, 350), 26, 650), ((4300, 600), 30, 700), ((3600, 2700), 22, 500),
             ((-1200, 1500), 40, 1200), ((7400, 1200), 45, 1300), ((2000, -900), 38, 1100), ((3000, 4300), 40, 1200)]
    heights = []
    for j in range(ny):
        row = []
        for i in range(nx):
            X, Y = x0 + i * step, y0 + j * step
            h = W + 2.5 + n(X / 900, Y / 900) * 7 + n(X / 300 + 50, Y / 300) * 2.5
            for (hx, hy), hh, s in hills:
                h += hh * math.exp(-((X - hx) ** 2 + (Y - hy) ** 2) / (2 * s * s))
            # the village and its fields lie on flat ground
            dv = math.hypot(X - C[0], Y - (C[1] + 80))
            if dv < 600:
                f = max(0.0, (dv - 250) / 350)
                h = (W + 2.2) * (1 - f) + h * f
            row.append(r1(h))
        heights.append(row)
    river = [(-3000, 700), (-1500, 850), (-500, 950), (0, 1000), (350, 1120), (700, 1260), (950, 1405), (1100, 1480),
             (1200, 1507), (1300, 1515), (1400, 1508), (1500, 1486), (1650, 1420), (1900, 1290), (2250, 1130), (2600, 1050), (3000, 1020),
             (3400, 1000), (3800, 1060), (4200, 1100), (4600, 1030), (5000, 950), (5500, 920), (6000, 900),
             (7000, 860), (9000, 700)]
    stream = [(2500, 1880), (2350, 1830), (2200, 1790), (2050, 1760), (1900, 1730), (1750, 1700), (1600, 1676),
              (1450, 1652), (1380, 1645), (1300, 1644), (1240, 1645), (1170, 1646), (1100, 1636), (1030, 1612),
              (960, 1570), (900, 1510), (860, 1450), (835, 1390), (822, 1330), (818, 1290)]
    forest = [[(3150, -200), (3050, 300), (3180, 700), (3080, 1000), (3250, 1350), (3120, 1700), (3300, 2100),
               (3150, 2500), (3350, 2900), (3250, 3600), (8000, 3600), (8000, -200)],
              [(-1500, -500), (-1500, 650), (-600, 760), (100, 700), (500, 820), (900, 760), (1100, 400), (900, -500)],
              [(1900, 2700), (2150, 2350), (2500, 2250), (2850, 2400), (2900, 2800), (2500, 3200), (2000, 3150)],
              [(-1500, 2300), (-200, 2150), (500, 2350), (700, 2900), (300, 3600), (-1500, 3600)]]
    clearings = [[5450, 1850, 95], [4050, 1100, 140], [5800, 2600, 220]]
    return {
        "size": list(SIZE), "seed": SEED, "water_level": W,
        "heights": {"x0": x0, "y0": y0, "step": step, "nx": nx, "ny": ny, "h": heights},
        "river": [[x, y, 46] for x, y in river],
        "stream": [[x, y, 7] for x, y in stream],
        "forest": [{"pts": [pt(*p) for p in poly], "density": 0.85} for poly in forest],
        "clearings": clearings,
        "flat": [C[0], C[1] + 40, 260],
    }


def seg_dist(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy or 1)))
    return math.hypot(x - a[0] - dx * t, y - a[1] - dy * t)


def village(rng):
    lanes, plots, buildings, fields, people, animals = [], [], [], [], [], []
    cx, cy = C

    def ring(r, a0, a1, n, c=C):
        return [pt(*polar(a0 + (a1 - a0) * k / n, r, c)) for k in range(n + 1)]

    # the lane round the green, the lanes west and east, the back lane along the river, the fork to the bridge
    RING, BACK = 16, 56
    lanes.append({"pts": ring(RING, 0, 360, 36), "w": 5, "kind": "lane", "closed": True})
    west = [(cx - RING, cy), (cx - 60, cy + 1), (cx - 120, cy - 3), (cx - 170, cy - 22), (cx - 196, cy - 60), (cx - 205, cy - 92)]
    east = [(cx + RING, cy), (cx + 60, cy - 2), (cx + 100, cy + 4), (cx + 150, cy - 14), (cx + 175, cy - 60), (cx + 182, cy - 92)]
    lanes.append({"pts": [pt(*p) for p in west], "w": 5, "kind": "lane"})
    lanes.append({"pts": [pt(*p) for p in east], "w": 5, "kind": "lane"})
    back = ring(BACK, -186, 6, 30)
    lanes.append({"pts": [pt(*west[1])] + back[1:-1] + [pt(*east[1])], "w": 4, "kind": "lane"})
    bridge = (1304.0, 1644.0)
    lanes.append({"pts": [pt(cx + 2, cy + RING), pt(cx + 3, cy + 30), pt(bridge[0], bridge[1] - 9), pt(*bridge),
                          pt(bridge[0], bridge[1] + 9), pt(1306, 1680), pt(1307, 1740), pt(1308, 1800)],
                 "w": 4, "kind": "lane"})
    # the track to the hamlet: on from the field lane, south of the spring, through the forest edge
    track = [(1308, 1800), (1450, 1860), (1600, 1905), (1800, 1950), (2000, 1985), (2250, 1990), (2500, 1980),
             (2750, 1950), (3000, 1905), (3200, 1925), (3400, 1950), (3650, 1915), (3900, 1880), (4150, 1905),
             (4400, 1950), (4650, 1960), (4900, 1915), (5150, 1890), (5330, 1862), (5420, 1852)]
    lanes.append({"pts": [pt(*p) for p in track], "w": 3, "kind": "track"})

    green = {"pos": pt(cx, cy), "r": [11.5, 10.5]}
    well = (cx - 3, cy + 2.5)
    buildings.append({"kind": "well", "pos": pt(*well), "angle": 0, "size": [2.2, 2.2]})
    buildings.append({"kind": "shrine", "pos": pt(cx + 1, cy - 6.5), "angle": 0, "size": [3, 3]})

    # households: eight plots fanning along the north of the lane, two south-west of the green; each a long house
    # gable-end to the lane, its store on posts behind, a few sheep in the yard
    fan = [(-169 + k * 22.6, 10.8, RING + 3.5, BACK - 3.5, 15) for k in range(8)] + [(147, 15, RING + 3.5, 41, 12), (119, 12, RING + 3.5, 38, 11)]
    for k, (a, half, ra, rb, hl) in enumerate(fan):
        corners = [polar(a - half, ra), polar(a + half, ra), polar(a + half, rb), polar(a - half, rb)]
        # the gate: on the lane side, in the middle
        plots.append({"pts": [pt(*p) for p in corners], "fence": "wattle", "gate": 0, "household": k})
        rh = ra + 2.5 + hl / 2
        hx, hy = polar(a, rh)
        buildings.append({"kind": "long_house", "pos": pt(hx, hy), "angle": r1(face(hx, hy, cx, cy)),
                          "size": [6.6 if hl > 12 else 6, hl], "style": "river", "household": k})
        side = 1 if k % 2 else -1
        sx, sy = polar(a + side * half * 0.5, rb - 4.5)
        if rh + hl / 2 + 6 < rb and rng.random() < 0.9:
            buildings.append({"kind": "stilt_store", "pos": pt(sx, sy), "angle": r1(face(sx, sy, cx, cy) + rng.uniform(-8, 8)),
                              "size": [2.6, 2.6], "household": k})
        for _ in range(rng.choice([0, 1, 2, 2, 3])):
            ax, ay = polar(a + rng.uniform(-half, half) * 0.6, rng.uniform(rh + hl / 2 + 1.5, rb - 2))
            animals.append({"kind": "sheep", "pos": pt(ax, ay), "angle": rng.randint(0, 359)})

    # kilns at the east end, downwind, smoking
    for p in [(cx + 47, cy + 15), (cx + 56, cy + 9), (cx + 56, cy + 24)]:
        buildings.append({"kind": "kiln", "pos": pt(*p), "angle": r1(face(*p, cx + 40, cy + 10)), "size": [3.6, 4], "lit": True})
    # the burial ground, fenced, its stones in rows
    bg = [(cx - 92, cy + 7), (cx - 52, cy + 7), (cx - 52, cy + 35), (cx - 92, cy + 35)]
    plots.append({"pts": [pt(*p) for p in bg], "fence": "wattle", "gate": 0, "use": "burial"})
    for i in range(6):
        for j in range(3):
            if rng.random() < 0.85:
                x, y = cx - 87 + i * 6.4 + rng.uniform(-0.5, 0.5), cy + 13 + j * 7.5 + rng.uniform(-0.5, 0.5)
                buildings.append({"kind": "grave_stone", "pos": pt(x, y), "angle": r1(rng.uniform(-12, 12)), "size": [0.7, 0.25]})
    buildings.append({"kind": "plank_bridge", "pos": pt(*bridge), "angle": 0, "size": [3, 10]})

    # strips of the south field: two furlongs either side of the field lane, grain, flax and fallow
    crops = ["wheat", "fallow", "flax", "wheat", "stubble", "fallow", "wheat", "ley", "flax", "fallow", "wheat", "stubble", "ley"]
    k = 0
    for x0, x1 in [(1150, 1300), (1312, 1462)]:
        x = x0
        while x + 10 <= x1:
            top = 1660 + rng.uniform(-1.5, 1.5)
            bot = 1772 + rng.uniform(-4, 4)
            fields.append({"pts": [pt(x, top), pt(x + 10, top + 0.4), pt(x + 10, bot + 0.4), pt(x, bot)],
                           "crop": crops[k % len(crops)], "stage": "ripe"})
            k += 1
            x += 11.5
    # a strip being reaped: the reapers stand at the edge of the standing grain
    reap = next(f for f in fields if f["crop"] == "wheat" and f["pts"][0][0] > 1300)
    reap["reaped_to"] = 0.3        # the near (north) part is cut

    # the hamlet of the forest folk: conical huts round a fire in a clearing at the end of the track
    H = (5450.0, 1850.0)
    for k in range(4):
        hx, hy = polar(-60 + k * 72, 15, H)
        buildings.append({"kind": "conical_hut", "pos": pt(hx, hy), "angle": r1(face(hx, hy, *H)), "size": [6, 6], "style": "forest"})
    buildings.append({"kind": "fire", "pos": pt(*H), "angle": 0, "size": [2, 2], "lit": True})
    buildings.append({"kind": "drying_rack", "pos": pt(H[0] + 22, H[1] + 10), "angle": 30, "size": [3, 1.5]})

    # people at the target's tasks
    def person(pid, x, y, verb, holds=None, age=30, face_to=None, path=None, speed=1.3, detail=None):
        p = {"id": pid, "pos": pt(x, y), "verb": verb, "age": age}
        if holds: p["holds"] = holds
        if detail: p["detail"] = detail
        if face_to: p["face"] = pt(*face_to)
        if path: p["path"] = [pt(*q) for q in path]; p["speed"] = speed
        people.append(p)

    rx = reap["pts"]
    edge_y = rx[0][1] + (rx[3][1] - rx[0][1]) * reap["reaped_to"]
    for i in range(4):
        person(len(people), rx[0][0] + 1.5 + i * 2.7, edge_y - 0.9, "gather", "sickle", detail="grain", face_to=(rx[0][0] + 1.5 + i * 2.7, edge_y + 5))
    person(len(people), rx[0][0] + 6, edge_y - 6, "take", "basket", age=12, face_to=(rx[0][0] + 4, edge_y))
    # carrying sheaves home: from the strip over the bridge to the green
    home = [(rx[0][0] + 3, edge_y - 6), (1306, edge_y - 6), (1306, 1680), (bridge[0], bridge[1] + 9), bridge, (bridge[0], bridge[1] - 9), (cx + 3, cy + 30), (cx + 2, cy + 16), (cx - 9, cy + 14)]
    person(len(people), *home[0], "walk", "sheaf", path=home, speed=1.1)
    person(len(people), 1307, 1740, "walk", "sheaf", path=[(1307, 1740), (1306, 1680), (bridge[0], bridge[1] + 9), bridge, (bridge[0], bridge[1] - 9), (cx + 3, cy + 30)], speed=1.2)
    # flax: two weeding
    fl = next(f for f in fields if f["crop"] == "flax" and f["pts"][0][0] < 1300)
    person(len(people), fl["pts"][0][0] + 4, fl["pts"][0][1] + 30, "plant", age=40)
    person(len(people), fl["pts"][0][0] + 7, fl["pts"][0][1] + 44, "plant", age=19)
    # the green: two knots of talkers, children playing, one at the well
    for (x, y, n) in [(cx + 5, cy - 0.5, 3), (cx - 4, cy + 7, 2)]:
        for i in range(n):
            a = i / n * math.tau
            px, py = x + 1.3 * math.sin(a), y + 1.3 * math.cos(a)
            person(len(people), px, py, "talk", age=rng.choice([24, 33, 45, 61]), face_to=(x, y))
    for i in range(3):
        a = i / 3 * math.tau
        loop = [(cx + 1 + 4.5 * math.cos(a + t / 8 * math.tau), cy + 1.5 + 3 * math.sin(a + t / 8 * math.tau)) for t in range(9)]
        person(len(people), *loop[0], "walk", age=6 + i, path=loop, speed=2.2)
    person(len(people), well[0] + 1.8, well[1] + 0.2, "take", age=28, face_to=well)
    # spinning by a door; a child with the sheep; a potter at the kilns; a fisher at the landing; mending a fence
    hb = [b for b in buildings if b["kind"] == "long_house"]
    for b, verb, det, age in [(hb[3], "craft", "thread", 52), (hb[6], "craft", "basket", 35)]:
        a = math.radians(b["angle"])
        dx, dy = b["pos"][0] + math.sin(a) * 8.6 + math.cos(a) * 2.4, b["pos"][1] + math.cos(a) * 8.6 - math.sin(a) * 2.4
        person(len(people), dx, dy, verb, age=age, detail=det, face_to=(dx + math.sin(a), dy + math.cos(a)))
    sh = animals[2]["pos"]
    person(len(people), sh[0] + 2, sh[1] + 1.5, "tame", age=8, face_to=sh)
    person(len(people), cx + 51, cy + 20, "craft", age=38, detail="pot", face_to=(cx + 56, cy + 24))
    person(len(people), cx - 203, cy - 96, "fish", "rod", age=27, face_to=(cx - 207, cy - 115))
    pl = plots[1]["pts"]
    person(len(people), (pl[1][0] + pl[2][0]) / 2, (pl[1][1] + pl[2][1]) / 2 + 1, "build", "hammer", age=44, face_to=((pl[1][0] + pl[2][0]) / 2, (pl[1][1] + pl[2][1]) / 2))
    # on the track, walking to the hamlet; at the hamlet, three at their work
    person(len(people), *track[3], "walk", "pack", path=track[3:], speed=1.3)
    person(len(people), H[0] + 2.5, H[1] + 1.5, "rest", age=60, face_to=H)
    person(len(people), H[0] - 3, H[1] + 2, "craft", age=30, detail="arrow", face_to=H)
    person(len(people), H[0] + 30, H[1] - 25, "gather", "axe", detail="wood", age=26, face_to=(H[0] + 33, H[1] - 28))
    # the walk (?walk=1): from a door, down the lane, across the green, over the bridge, out to the strips, then the track
    door = hb[4]
    a = math.radians(door["angle"])
    dx, dy = door["pos"][0] + math.sin(a) * 8.3, door["pos"][1] + math.cos(a) * 8.3
    walk = [(dx, dy), (dx + math.sin(a) * 2, dy + math.cos(a) * 2), polar(-90, RING), (cx + 4, cy - 8), (cx + 5, cy + 8), (cx + 2, cy + RING),
            (cx + 3, cy + 30), (bridge[0], bridge[1] - 9), bridge, (bridge[0], bridge[1] + 9), (1306, 1680), (1307, 1740)] + track
    person(len(people), *walk[0], "walk", "pack", age=31, path=walk, speed=1.4)
    walker = people[-1]["id"]
    # sheep grazing the meadow west of the village, a few in the hamlet's pen
    for _ in range(14):
        animals.append({"kind": "sheep", "pos": pt(cx - 330 + rng.uniform(-40, 40), cy + 60 + rng.uniform(-30, 30)), "angle": rng.randint(0, 359)})
    # trees about the village, as in the picture: along the river bank, at the corners, by the burial ground
    trees = []
    def clear(x, y):
        if math.hypot(x - cx, y - cy) < 64: return False
        if 1140 < x < 1472 and 1650 < y < 1785: return False
        if abs(y - 1645) < 10 and 1000 < x < 1600: return False
        if cx - 98 < x < cx - 46 and cy + 2 < y < cy + 40: return False
        if cx + 36 < x < cx + 68 and cy - 4 < y < cy + 34: return False
        return True
    while len(trees) < 34:
        a, r = rng.uniform(0, math.tau), rng.uniform(70, 240)
        x, y = cx + r * math.cos(a), cy + 40 + r * math.sin(a) * 0.8
        if y < 1525 or not clear(x, y): continue
        if any(seg_dist(x, y, lane["pts"][k - 1], lane["pts"][k]) < 14 for lane in lanes for k in range(1, len(lane["pts"]))): continue
        trees.append([r1(x), r1(y), rng.choice(["broadleaf", "broadleaf", "conifer"]), round(rng.uniform(0.8, 1.25), 2)])
    return {"trees": trees, "lanes": lanes, "plots": plots, "buildings": buildings, "fields": fields, "people": people,
            "animals": animals, "green": green, "walker": walker, "centre": pt(*C)}


def build():
    rng = random.Random(SEED)
    data = {"format": "world5-demo-1", "units": "metres, x east, y south; angle: degrees, front faces (sin a, cos a)",
            "land": land(rng)}
    data.update(village(random.Random(SEED + 1)))
    return data


def main():
    data = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(OUT, os.path.getsize(OUT), "bytes;", len(data["buildings"]), "buildings,", len(data["people"]), "people,",
          len(data["fields"]), "strips")


if __name__ == "__main__":
    main()
