"""Do two versions of the engine make the same worlds? Runs a 25-day old land (120 people) and a 25-day continent
(500 people) and prints a hash of each world's state. A speed change must leave both hashes alone (docs/speed.md).
Bot worlds are deterministic, across processes too since c87's fix (fishing's choice of water by max() over a set).

    python tools/same_world.py            # this checkout
    python tools/same_world.py /path/to/other/checkout
"""
import hashlib
import json
import os
import sys

root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, root)
from civ.engine import Engine  # noqa: E402
from civ.gen import generate  # noqa: E402
from civ.minds.bot import BotMind  # noqa: E402
from civ.realm import generate as found  # noqa: E402
from civ.world import TPD  # noqa: E402

out = []
for make in (lambda: generate({"seed": 3, "people": 120, "width": 80, "height": 80, "bands": 8}),
             lambda: found({"seed": 2, "people": 500, "width": 128, "height": 128})):
    w = make()
    e = Engine(w)
    m = BotMind(e)
    for _ in range(TPD * 25):
        e.tick(m.decide)
    h = hashlib.sha1(json.dumps(w.to_dict(), sort_keys=True, default=str).encode()).hexdigest()[:12]
    out.append(f"{h} alive {len(w.living())}")
print(" | ".join(out))
