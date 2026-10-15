"""Found a live world from a bots-only land of peoples (grand.md Phase 8): its years so far become the old times, and
minds of their own take the seats where choices move many (civ/realm.seat_minds).

    python tools/found_world.py --src gw/world --dst w4/world --seat 48 [--usage w2/world/kaggle_usage.json]

The land is copied as it stands (state and the season-by-season history); its hour-by-hour logs stay behind. The
Kaggle hours already spent (kaggle_usage.json of the world it takes over from) come along, so the week's budget holds.
Run by found-world.yml, which pushes the result to the new world's branch.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ.realm import seat_minds  # noqa: E402
from civ.run import load, save  # noqa: E402


def found(src, dst, seat, usage=None, name=None):
    w = load(src)
    if w is None:
        raise SystemExit(f"no land at {src}")
    if not w.peoples:
        raise SystemExit("not a land of peoples: nothing to seat")
    for p in w.living():
        if p.mind == "llm":
            p.mind, p.intent = "bot", None
    w.cfg["ai"] = seat
    if name:
        w.cfg["name"] = name
    seat_minds(w, w.rng, seat)
    os.makedirs(dst, exist_ok=True)
    save(w, dst)
    for f in ("history.jsonl",):
        if os.path.exists(os.path.join(src, f)):
            shutil.copy(os.path.join(src, f), os.path.join(dst, f))
    if usage and os.path.exists(usage):
        shutil.copy(usage, os.path.join(dst, "kaggle_usage.json"))
    minds = [p for p in w.living() if p.mind == "llm"]
    lines = [f"# {name or 'A new world'}: founded in year {w.year() + 1} of its land", "",
             f"{len(w.living())} alive, {len(w.people)} have lived; {len(minds)} with minds of their own, in these seats:", ""]
    for p in minds:
        lead = [g.name for g in w.groups.values() if g.leader == p.id and g.dissolved is None]
        lines.append(f"- {p.name} of the {p.people} people, {int(p.age(w.tick))}" + (f", leads {', '.join(lead)}" if lead else "")
                     + (f", {p.vocation}" if p.vocation else ""))
    with open(os.path.join(dst, "last_run.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    return w, minds


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--seat", type=int, default=48)
    ap.add_argument("--usage", default="")
    ap.add_argument("--name", default="The grand world")
    a = ap.parse_args(argv)
    w, minds = found(a.src, a.dst, a.seat, a.usage, a.name)
    print(f"founded at tick {w.tick}: {len(w.living())} alive, {len(minds)} minds seated")


if __name__ == "__main__":
    main()
