"""Whole-map ASCII view for humans."""
from .world import unkey


def render(w):
    g = [list(r) for r in w.terrain]
    for k, b in w.bushes.items():
        x, y = unkey(k)
        g[y][x] = "*" if b["b"] else "o"
    for s in w.structures.values():
        g[s.y][s.x] = {"store": "S", "shelter": "H", "wall": "#", "farm": "F", "fire": "f"}[s.kind] if s.done else "?"
    for h in w.herds:
        g[h["y"]][h["x"]] = "D"
    for a in w.living():
        g[a.y][a.x] = a.name[0]
    return "\n".join("".join(r) for r in g)
