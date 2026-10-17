"""Sketches of the five town forms of docs/towns_spec.md, to scale (1 cell = 4 m), as SVG."""
import math, os, random, json, sys
S = 4          # px per cell
N = 150        # cells shown (600 m)
COL = dict(grass="#cfe0a8", soil="#b9a06a", water="#7fb3c8", lane="#e6d3a3", laneedge="#c9b07a", green="#a9cf7f",
           plot="#e3ebc6", fence="#8a6b45", roof_thatch="#c8a25a", roof_dark="#7a5a3a", tent="#e8dcc0", stone="#9a9a92",
           store="#a5763f", pen="#d9c48f", kiln="#b0553a", grave="#8d8d86", strip1="#d7c46a", strip2="#9fbf5a",
           strip3="#b58a4f", tree="#4f7d45", tree2="#3e6b3a", text="#3a2f22", smoke="#9a948a", well="#5c7d9a", shrine="#8c6db0")

def svg(title, sub, body, bg=COL["grass"]):
    W = N * S
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W + 56}" width="{W}" height="{W + 56}" font-family="Georgia,serif">'
            f'<rect width="{W}" height="{W + 56}" fill="#f6f0e2"/><rect y="56" width="{W}" height="{W}" fill="{bg}"/>'
            f'<text x="10" y="24" font-size="20" fill="{COL["text"]}" font-weight="bold">{title}</text>'
            f'<text x="10" y="46" font-size="13" fill="{COL["text"]}">{sub}</text><g transform="translate(0,56)">{body}</g>'
            f'<g transform="translate({W - 130},{W + 40})"><rect width="100" height="5" fill="{COL["text"]}"/>'
            f'<text x="0" y="-4" font-size="11" fill="{COL["text"]}">100 m</text></g></svg>')

def R(x, y, w, h, fill, stroke=None, sw=1, rx=0, op=1):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
    return f'<rect x="{x*S:.1f}" y="{y*S:.1f}" width="{w*S:.1f}" height="{h*S:.1f}" rx="{rx}" fill="{fill}"{s} opacity="{op}"/>'
def C(x, y, r, fill, stroke=None, sw=1):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
    return f'<circle cx="{x*S:.1f}" cy="{y*S:.1f}" r="{r*S:.1f}" fill="{fill}"{s}/>'
def L(pts, w, col=COL["lane"], edge=COL["laneedge"]):
    d = "M" + " L".join(f"{x*S:.1f},{y*S:.1f}" for x, y in pts)
    return (f'<path d="{d}" fill="none" stroke="{edge}" stroke-width="{w*S+3}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w*S}" stroke-linecap="round" stroke-linejoin="round"/>')
def T(x, y, t, size=11, anchor="middle"):
    return f'<text x="{x*S:.1f}" y="{y*S:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{COL["text"]}" font-style="italic">{t}</text>'
def smoke(x, y):
    return "".join(C(x + i * 0.8, y - i * 1.6, 0.9 + i * 0.35, COL["smoke"]) for i in range(3)).replace('fill', 'opacity="0.55" fill')
def trees(rng, n, keep, box=(0, 0, N, N)):
    out = []
    for _ in range(n):
        x, y = rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3])
        if keep(x, y):
            r = rng.uniform(1.6, 2.6)
            out.append(C(x, y, r, rng.choice([COL["tree"], COL["tree2"]])))
    return "".join(out)
def strips(x0, y0, n, w, h, horiz=False):
    out = []
    for i in range(n):
        c = [COL["strip1"], COL["strip2"], COL["strip3"], COL["soil"]][i % 4]
        if horiz:
            out.append(R(x0, y0 + i * w, h, w - 0.4, c))
        else:
            out.append(R(x0 + i * w, y0, w - 0.4, h, c))
    return "".join(out)
def graves(x0, y0, cols, rows):
    out = [R(x0 - 1, y0 - 1, cols * 2.5 + 1, rows * 3.5 + 1, "#c7d3a4", COL["fence"], 1.2)]
    for i in range(cols):
        for j in range(rows):
            out.append(R(x0 + i * 2.5, y0 + j * 3.5, 1, 2, COL["grave"]))
    return "".join(out)
def house(x, y, w, h, roof, ridge=True):
    s = R(x, y, w, h, roof, "#5a4430", 1.2, 2)
    if ridge:
        if w < h:
            s += f'<line x1="{(x+w/2)*S}" y1="{(y+0.4)*S}" x2="{(x+w/2)*S}" y2="{(y+h-0.4)*S}" stroke="#5a4430" stroke-width="1.2"/>'
        else:
            s += f'<line x1="{(x+0.4)*S}" y1="{(y+h/2)*S}" x2="{(x+w-0.4)*S}" y2="{(y+h/2)*S}" stroke="#5a4430" stroke-width="1.2"/>'
    return s
def roundhouse(x, y, r, roof):
    return C(x, y, r, roof, "#5a4430", 1.2) + C(x, y, 0.5, "#5a4430")

# ---------- river: street village ----------
def river():
    rng = random.Random(1); b = []
    b.append(R(0, 0, N, 22, COL["water"]))
    lane_y = lambda x: 70 + 3 * math.sin(x / 23)
    pts = [(x, lane_y(x)) for x in range(4, 147, 3)]
    b.append(strips(4, 112, 12, 7, 38) + strips(100, 4 + 20, 0, 1, 1))
    b.append(T(45, 148, "strips of the south field (grain, flax, fallow)"))
    # plots
    plots = []
    for i, x in enumerate(list(range(54, 18, -9)) + list(range(84, 132, 9))):
        for side in (-1, 1):
            plots.append((x, side))
    green = (64, lane_y(70) - 8, 14, 16)
    for x, side in plots:
        y = lane_y(x + 4)
        py = y - 2 - 15 if side < 0 else y + 2
        b.append(R(x, py, 8, 15, COL["plot"], COL["fence"], 1.1))
        hy = py + 15 - 8.5 if side < 0 else py + 0.5
        b.append(house(x + 2.5, hy, 3, 8, COL["roof_thatch"]))
        yy = py + 1 if side < 0 else py + 10
        if rng.random() < 0.8: b.append(R(x + 0.7, yy, 2, 3, COL["store"], "#5a4430"))
        if rng.random() < 0.45: b.append(R(x + 3.6, yy, 4, 3.6, COL["pen"], COL["fence"]))
    b.insert(1, L(pts, 3))
    b.append(R(*green, COL["green"], "#7aa056", 1, 6))
    b.append(C(71, lane_y(70) - 4, 1.2, COL["well"]) + R(66, lane_y(70) + 3, 3, 3, COL["shrine"], "#4a3a60"))
    b.append(T(71, lane_y(70) - 10, "the green, well and shrine"))
    # back lane toward the river and a lane to the ford
    b.append(L([(71, lane_y(71) - 8), (73, 40), (78, 22)], 2))
    b.append(T(85, 30, "to the ford", 10))
    # edge: kilns downwind (east)
    for i, (x, y) in enumerate([(138, 60), (140, 78), (134, 84)]):
        b.append(R(x, y, 2, 3, COL["kiln"], "#5a2a1a") + smoke(x + 1, y))
    b.append(T(132, 96, "kilns at the east end", 10))
    b.append(graves(8, 30, 6, 4) + T(15, 47, "burial ground", 10))
    b.append(L([(2, lane_y(2)), (4, lane_y(4))], 3))
    return svg("River folk: a street village", "long houses gable-end to the lane, fenced tofts, the green in the middle, strips beyond", "".join(b))

# ---------- shore: waterfront row ----------
def shore():
    rng = random.Random(2); b = []
    b.append(R(0, 108, N, 42, COL["water"]))
    b.append(R(0, 102, N, 6, "#e7d8a8"))      # sand
    lane = [(x, 98 + 1.5 * math.sin(x / 15)) for x in range(2, 149, 3)]
    b.append(L(lane, 3))
    for i, x in enumerate(range(6, 140, 8)):
        y = 98 + 1.5 * math.sin((x + 3) / 15)
        b.append(R(x, y - 14, 7, 12, COL["plot"], None))
        b.append(house(x + 2, y - 9.5, 3, 7, COL["roof_dark"]))
        if rng.random() < 0.6: b.append(R(x + 0.5, y - 13.5, 1, 2, "#8a6b45"))   # drying rack
        if i % 3 == 0:
            b.append(R(x + 2.5, 104, 1.6, 12, "#8a6b45"))                 # jetty
            b.append(f'<ellipse cx="{(x+5.5)*S}" cy="{113*S}" rx="{2.4*S}" ry="{0.9*S}" fill="#6b4a2a"/>')
    b.append(L([(70, 97), (68, 80), (60, 60), (55, 30)], 2))
    b.append(T(64, 26, "the way inland", 10))
    b.append(R(74, 70, 12, 9, COL["green"], "#7aa056", 1, 6) + C(80, 74.5, 1.2, COL["well"]))
    b.append(T(80, 67, "the green"))
    b.append(graves(110, 50, 6, 3) + T(117, 47, "burial ground", 10))
    b.append(strips(10, 12, 8, 6, 34))
    b.append(T(34, 52, "small fields behind the row", 10))
    b.append(T(75, 130, "boats drawn up at the jetties", 11))
    return svg("Shore folk: a waterfront row", "one row of houses facing the water, jetties and drying racks, fields behind", "".join(b))

# ---------- hill: cluster in a bank ----------
def hill():
    rng = random.Random(3); b = []
    cx, cy = 75, 72
    b.append(C(cx, cy, 52, "#cdd9a0"))
    b.append(f'<circle cx="{cx*S}" cy="{cy*S}" r="{50*S}" fill="none" stroke="#8a7a52" stroke-width="{3*S}" opacity="0.8"/>')
    b.append(f'<circle cx="{cx*S}" cy="{cy*S}" r="{53.5*S}" fill="none" stroke="#6d6040" stroke-width="{1.2*S}" stroke-dasharray="6 4"/>')
    b.append(T(cx, cy - 55, "bank and ditch", 11))
    b.append(C(cx, cy, 8, COL["pen"], COL["fence"], 2) + T(cx, cy + 1, "fold", 10))
    for r in (14, 31):
        b.append(f'<circle cx="{cx*S}" cy="{cy*S}" r="{r*S}" fill="none" stroke="{COL["laneedge"]}" stroke-width="{2*S+3}"/>'
                 f'<circle cx="{cx*S}" cy="{cy*S}" r="{r*S}" fill="none" stroke="{COL["lane"]}" stroke-width="{2*S}"/>')
    for ring, (r, n) in enumerate([(22, 10), (39, 16)]):
        for i in range(n):
            a = 2 * math.pi * (i + rng.uniform(-0.15, 0.15)) / n
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            b.append(roundhouse(x, y, 2.4 if ring == 0 else 2.6, COL["roof_thatch"]))
            if rng.random() < 0.5:
                b.append(C(cx + (r + 4.5) * math.cos(a + 0.12), cy + (r + 4.5) * math.sin(a + 0.12), 2, COL["pen"], COL["fence"]))
    for a in (0.3, 2.4, 4.2):
        b.append(L([(cx + 8 * math.cos(a), cy + 8 * math.sin(a)), (cx + 50 * math.cos(a), cy + 50 * math.sin(a))], 1.5))
    b.append(graves(118, 118, 5, 3) + T(124, 116, "cairns on the slope", 10))
    b.append(R(8, 8, 2, 3, COL["kiln"]) + smoke(9, 8))
    b.append(trees(rng, 160, lambda x, y: math.hypot(x - cx, y - cy) > 56))
    return svg("Hill clans: round houses inside a bank", "two rings of round houses round the fold, sheep pens by the doors, one way out each side", "".join(b), "#c3cf93")

# ---------- riders: tent ring ----------
def riders():
    rng = random.Random(4); b = []
    cx, cy = 75, 75
    b.append(C(cx, cy, 16, "#d8cf9a", COL["fence"], 2))
    for _ in range(26):
        a, r = rng.uniform(0, 6.28), rng.uniform(1, 14)
        b.append(f'<ellipse cx="{(cx+r*math.cos(a))*S}" cy="{(cy+r*math.sin(a))*S}" rx="{1.1*S}" ry="{0.55*S}" fill="#6b4a2a"/>')
    b.append(T(cx, cy - 18, "the horse fold"))
    for r, n in ((26, 14), (38, 20)):
        b.append(f'<circle cx="{cx*S}" cy="{cy*S}" r="{(r-4.5)*S}" fill="none" stroke="{COL["lane"]}" stroke-width="{2*S}" opacity="0.9"/>')
        for i in range(n):
            a = 2 * math.pi * i / n + (0.1 if r > 30 else 0)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            b.append(C(x, y, 1.8, COL["tent"], "#8a6b45", 1.3) + C(x, y, 0.45, "#8a6b45"))
            dx, dy = cx + (r - 2.2) * math.cos(a), cy + (r - 2.2) * math.sin(a)
            b.append(C(dx, dy, 0.45, "#5a3a20"))
    b.append(C(cx + 45, cy - 30, 2, "#d27a3a") + T(cx + 45, cy - 34, "fire", 10))
    b.append(graves(8, 120, 4, 2) + T(13, 117, "burial mounds", 10))
    b.append(L([(cx + 40, cy + 10), (149, cy + 20)], 1.5) + L([(cx - 40, cy - 8), (0, cy - 20)], 1.5))
    b.append(T(30, 30, "open steppe: no fences, no fields", 11))
    return svg("Horse riders: a ring of tents", "felt tents in rings round the horse fold, doors facing in; they can be struck and moved", "".join(b), "#d5d79c")

# ---------- forest: clearing ----------
def forest():
    rng = random.Random(5); b = []
    cx, cy = 75, 75
    b.append(C(cx, cy, 46, "#bcd28f"))
    pts = []
    while len(pts) < 16:
        a, r = rng.uniform(0, 6.28), rng.uniform(13, 40)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        if all(math.hypot(x - u, y - v) > 12 for u, v in pts):
            pts.append((x, y))
    joined = [(cx, cy)]
    for x, y in sorted(pts, key=lambda q: math.hypot(q[0] - cx, q[1] - cy)):
        u, v = min(joined, key=lambda q: math.hypot(q[0] - x, q[1] - y))
        b.append(L([(u, v), (x, y)], 1, "#dcc99a", "#bfa877"))
        joined.append((x, y))
    b.append(C(cx, cy, 5, "#cfe0a8", "#9a8a5a") + C(cx, cy, 1.5, "#d27a3a") + T(cx, cy - 7, "fire-green"))
    for x, y in pts:
        b.append(roundhouse(x, y, 2.3, "#8f7a4a"))
        if rng.random() < 0.6: b.append(R(x + 3, y - 1, 1, 2, "#8a6b45"))
    b.append(graves(118, 20, 3, 3) + T(122, 17, "graves under the oaks", 10))
    b.append(trees(rng, 900, lambda x, y: math.hypot(x - cx, y - cy) > 43 or all(math.hypot(x - u, y - v) > 6 for u, v in pts + [(cx, cy)]) and math.hypot(x - cx, y - cy) > 8 and rng.random() < 0.18))
    return svg("Forest folk: huts in a clearing", "conical huts scattered among standing trees, joined by footpaths to the fire-green", "".join(b), "#9fbf7a")

# ---------- today: world4 ----------
def today():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from civ.run import load
    from civ.census import clusters
    w = load('/tmp/w4/world')
    c = max(clusters(w), key=lambda c: len(c['people']))
    xs = [h[0] for h in c['homes']]; ys = [h[1] for h in c['homes']]
    x0, y0 = min(xs) - 2, min(ys) - 2
    n = 46; px = N * S / n
    col = {'shelter': '#c8a25a', 'house': '#c8a25a', 'store': '#a5763f', 'farm': '#d7c46a', 'pen': '#d9c48f', 'cairn': '#8d8d86',
           'grave': '#8d8d86', 'kiln': '#b0553a', 'loom': '#a58ac8', 'fire': '#d27a3a', 'brewhouse': '#7a9a5a', 'oven': '#b0553a'}
    tc = {'~': COL["water"], 'T': '#5f8a50', '.': COL["grass"], ',': '#c9b47a', 'h': '#b5b08a', 'm': '#8fae8a'}
    out = []
    for yy in range(n):
        for xx in range(n):
            x, y = x0 + xx, y0 + yy
            b = w.building_at(x, y) if w.inb(x, y) else None
            f = col.get(b.kind, '#9c8a6a') if b else tc.get(w.t(x, y) if w.inb(x, y) else '.', COL["grass"])
            out.append(f'<rect x="{xx*px:.1f}" y="{yy*px:.1f}" width="{px+0.3:.1f}" height="{px+0.3:.1f}" fill="{f}"/>')
    for pid in c['people']:
        p = w.people[pid]
        if x0 <= p.x < x0 + n and y0 <= p.y < y0 + n:
            out.append(f'<circle cx="{(p.x-x0+0.5)*px:.1f}" cy="{(p.y-y0+0.5)*px:.1f}" r="2.5" fill="#222"/>')
    W = N * S
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W + 56}" width="{W}" height="{W + 56}" font-family="Georgia,serif">'
            f'<rect width="{W}" height="{W + 56}" fill="#f6f0e2"/>'
            f'<text x="10" y="24" font-size="20" fill="{COL["text"]}" font-weight="bold">world4 today: its largest settlement</text>'
            f'<text x="10" y="46" font-size="13" fill="{COL["text"]}">each square is a whole tile (about 1 km): 183 people, 1,600 buildings, 46 km across</text>'
            f'<g transform="translate(0,56)">{"".join(out)}</g></svg>')

out = sys.argv[1]
for name, f in [("0_today", today), ("1_river", river), ("2_shore", shore), ("3_hill", hill), ("4_riders", riders), ("5_forest", forest)]:
    open(f"{out}/{name}.svg", "w").write(f())
print("ok")
