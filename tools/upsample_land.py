"""The large land's check (world5.md §10, step 3): a saved world's land at twice the scale, against the old.

    python tools/upsample_land.py --state <dir with state.json.gz> [--out docs/towns_pics/land] [--seed N]

Prints the overlay check (the new land seen at the old scale against the old), the bodies of water before and after
(rivers unbroken), how many river blocks are more than a river; draws the old and new lands and a close look at one
stretch (PNG, with Pillow). Writes nothing to the state.
"""
import argparse
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ.upsample import K, broad_water, components, downsample, upsample  # noqa: E402

COL = {".": (150, 185, 90), ",": (120, 150, 60), "T": (40, 100, 50), "h": (160, 140, 90), "^": (130, 120, 120),
       "~": (60, 110, 190), "m": (90, 130, 110), "s": (220, 205, 150)}


def draw(terrain, path, scale, crop=None):
    from PIL import Image
    im = Image.new("RGB", (len(terrain[0]), len(terrain)))
    im.putdata([COL.get(c, (0, 0, 0)) for row in terrain for c in row])
    if crop:
        im = im.crop(crop)
    im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(path)


def check(d, u):
    t0, t1 = d["terrain"], u["terrain"]
    h, w = len(t0), len(t0[0])
    ds = downsample(t1)
    kept = sum(a == b for r0, r1 in zip(t0, ds) for a, b in zip(r0, r1)) / (w * h)
    broad = broad_water(t0)
    rivers = [(x, y) for y in range(h) for x in range(w) if t0[y][x] == "~" and (x, y) not in broad]
    full = sum(all(t1[K * y + j][K * x + i] == "~" for j in range(K) for i in range(K)) for x, y in rivers)
    c0, c1 = components(t0), components(t1)
    rows0, rows1 = d.get("region_rows"), u.get("region_rows")
    reg = (sum(rows1[Y][X] == rows0[Y // K][X // K] for Y in range(h * K) for X in range(w * K)) / (h * w * K * K)) if rows0 else None
    return {"size": [w, h, w * K, h * K], "kept": round(kept, 4), "water_bodies": [len(c0), len(c1)],
            "river_tiles": len(rivers), "river_blocks_full": full, "regions_kept": reg and round(reg, 4),
            "deposits": [len(d.get("deposits", {})), len(u["deposits"])], "places": [len(d.get("places", [])), len(u["places"])]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    with gzip.open(os.path.join(a.state, "state.json.gz"), "rt", encoding="utf-8") as f:
        d = json.load(f)
    u = upsample(d, a.seed)
    rep = check(d, u)
    print(json.dumps(rep))
    sound = rep["kept"] >= 0.95 and rep["water_bodies"][0] == rep["water_bodies"][1] and rep["river_blocks_full"] == 0
    print("SOUND" if sound else "NOT SOUND")
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        draw(d["terrain"], os.path.join(a.out, "old.png"), 4)
        draw(u["terrain"], os.path.join(a.out, "new.png"), 2)
        w = len(d["terrain"][0])
        x0, y0, s = w // 4, w // 4, max(16, w // 6)
        draw(d["terrain"], os.path.join(a.out, "old_close.png"), 8, (x0, y0, x0 + s, y0 + s))
        draw(u["terrain"], os.path.join(a.out, "new_close.png"), 4, (x0 * K, y0 * K, (x0 + s) * K, (y0 + s) * K))
    return 0 if sound else 1


if __name__ == "__main__":
    sys.exit(main())
