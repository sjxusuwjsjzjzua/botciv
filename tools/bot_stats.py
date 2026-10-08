"""What the bot farm (bots.yml) has measured, by rules version: the cheap, wide balance read.

    python tools/bot_stats.py                  # fetch the `bots` branch; the last 3 rules versions
    python tools/bot_stats.py --versions 1     # only the newest
    python tools/bot_stats.py --dir results    # a local folder of <rules>.jsonl files instead

bots.yml runs bots-only civ worlds on fresh seeds, on the code on main, without end, and appends one
line per world to results/<rules>.jsonl on the `bots` branch (tools/civ_balance.py --json). Worlds are
grouped by their land (people, size, years), since only worlds of one shape compare. For each: how many
worlds, alive (mean ± standard error), births, deaths by cause, eras reached, things built and made,
trades, teachings, thefts and attacks a world, and the most common refusals. A rules change is judged
against the version before it on the same shape, once each has a dozen worlds or so.
"""
import argparse
import collections
import glob
import json
import math
import os
import subprocess
import sys
import tempfile


def fetch(tmp):
    """The bots branch's results folder, or None before the farm has run."""
    if subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "+bots:refs/remotes/origin/bots"], capture_output=True).returncode != 0:
        return None
    out = subprocess.run(["git", "archive", "origin/bots", "results"], capture_output=True)
    if out.returncode != 0:
        return None
    subprocess.run(["tar", "-x", "-C", tmp], input=out.stdout)
    return os.path.join(tmp, "results")


def vkey(v):
    """c42 sorts after c9."""
    digits = "".join(ch for ch in v if ch.isdigit())
    return (v.rstrip("0123456789"), int(digits) if digits else 0)


def mean_se(xs):
    if not xs:
        return 0, 0
    m = sum(xs) / len(xs)
    if len(xs) < 2:
        return m, 0
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return m, math.sqrt(var / len(xs))


def summary(rows):
    alive = [r["alive"] for r in rows]
    start = [r["pop"][0] if r.get("pop") else r["people"] for r in rows]
    deaths = collections.Counter()
    refused = collections.Counter()
    counts = collections.Counter()
    for r in rows:
        deaths.update(r.get("deaths", {}))
        refused.update(r.get("refused", {}))
        counts.update(r.get("counts", {}))
    n = len(rows)
    return {"n": n, "alive": mean_se(alive), "growth": mean_se([a / max(1, s) for a, s in zip(alive, start)]),
            "births": sum(r["births"] for r in rows) / n, "deaths": {k: round(v / n, 1) for k, v in deaths.most_common()},
            "starved_share": deaths.get("starved", 0) / max(1, sum(deaths.values())),
            "era": collections.Counter(r["era"] for r in rows), "able": sum(r["able"] for r in rows) / n,
            "built": sum(r["built"] for r in rows) / n, "made": sum(r["made"] for r in rows) / n,
            "counts": {k: round(v / n, 1) for k, v in counts.items()}, "refused": refused.most_common(6),
            "codes": sorted({r.get("code", "?") for r in rows})}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="", help="a local results folder instead of the bots branch")
    ap.add_argument("--versions", type=int, default=3)
    a = ap.parse_args(argv)
    d = a.dir or fetch(tempfile.mkdtemp())
    if not d or not os.path.isdir(d):
        print("no results yet: the bots branch does not exist (bots.yml has not finished a run)")
        return 1
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in glob.glob(os.path.join(d, "*.jsonl")):
        for line in open(f):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            by[r["rules"]][(r["people"], r["size"], r["years"])].append(r)
    versions = sorted(by, key=vkey)[-a.versions:]
    for v in reversed(versions):
        print(f"== rules {v}")
        for shape in sorted(by[v]):
            s = summary(by[v][shape])
            (am, ase), (gm, _) = s["alive"], s["growth"]
            print(f"  {shape[0]} people, land {shape[1]}, {shape[2]:g} years: {s['n']} worlds; alive {am:.1f} ± {ase:.1f} "
                  f"(x{gm:.2f}); births {s['births']:.0f}; deaths a world {s['deaths']} (starved {s['starved_share']:.0%})")
            print(f"    eras {dict(sorted(s['era'].items()))}; crafts able {s['able']:.1f}; built {s['built']:.0f}, "
                  f"made {s['made']:.0f}; a world: {s['counts']}")
            print(f"    refused: {'; '.join(f'{w} ({c})' for w, c in s['refused'])}")
            print(f"    code: {', '.join(s['codes'][-4:])}")
    if len(versions) >= 2:
        new, old = versions[-1], versions[-2]
        for shape in sorted(set(by[new]) & set(by[old])):
            (nm, nse), (om, ose) = mean_se([r["alive"] for r in by[new][shape]]), mean_se([r["alive"] for r in by[old][shape]])
            z = (nm - om) / math.sqrt(nse ** 2 + ose ** 2) if nse or ose else 0
            print(f"\n{new} against {old}, {shape[0]} people, {shape[2]:g} years: alive {nm:.1f} vs {om:.1f} "
                  f"({nm - om:+.1f}, {z:+.1f} standard errors; {len(by[new][shape])} and {len(by[old][shape])} worlds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
