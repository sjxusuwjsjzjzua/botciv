"""One look at the civ world, by rules version: what the people with minds of their own did under each
version of the rules in world2, where they think on Kaggle with an open model and, when Kaggle has no
hours left, on the free API tiers; split by model, a failure seen under both is the rules' and not one
model's. (world3, a second world on the free tiers, was retired 2026-10-02; --dirs still reads it.)

    python tools/civ_round.py                 # fetch world2, the last 3 rules versions
    python tools/civ_round.py --versions 1    # only the newest
    python tools/civ_round.py --dirs a/world b/world   # local copies instead of the branches

For each rules version (newest first): answers, seconds an answer, tokens out, refused steps (of all
planned) with the top reasons, what woke them, what they made, deaths and blows, per world and pooled,
and by model.
"""
import argparse
import collections
import glob
import gzip
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def fetch(branch, into):
    """The world folder of a branch, unpacked into a temporary folder (None if there is no such branch)."""
    if subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", f"+{branch}:refs/remotes/origin/{branch}"], capture_output=True).returncode != 0:
        return None
    data = subprocess.run(["git", "archive", f"origin/{branch}", "world"], capture_output=True).stdout
    if not data:
        return None
    tarfile.open(fileobj=io.BytesIO(data)).extractall(into, filter="data")
    return os.path.join(into, "world")


def read(f):
    out = []
    try:
        with gzip.open(f, "rt") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    break
    except (OSError, EOFError):
        pass
    return out


def pieces(d):
    """Each piece of a world's log: its minds' decisions and its events, with the rules it ran under."""
    out = []
    for fm in sorted(glob.glob(os.path.join(d, "log", "minds-*.jsonl.gz"))):
        stamp = fm.split("minds-")[1].split(".")[0]
        minds = read(fm)
        if not minds:
            continue
        rules = collections.Counter(m.get("rules", "?") for m in minds).most_common(1)[0][0]
        events = read(os.path.join(d, "log", f"events-{stamp}.jsonl.gz"))
        out.append({"stamp": stamp, "rules": rules, "minds": minds, "events": events})
    return out


def measure(ps, minds_ids):
    m = [x for p in ps for x in p["minds"]]
    ev = [e for p in ps for e in p["events"]]
    mine = lambda e: (e.get("who") or [None])[0] in minds_ids
    steps = sum(len(x.get("plan") or []) for x in m)
    ref = [e for e in ev if e["kind"] == "refused" and mine(e)]
    n = max(1, len(m))
    hours = sum(max((e["t"] for e in p["events"]), default=0) - min((e["t"] for e in p["events"]), default=0) for p in ps)
    return {
        "pieces": len(ps), "answers": len(m), "hours": hours,
        "s": round(sum(x.get("s") or 0 for x in m) / n, 1), "tout": round(sum(x.get("tout") or 0 for x in m) / n),
        "refused": len(ref), "steps": steps, "refused_pct": round(100 * len(ref) / max(1, steps), 1),
        "why": collections.Counter(e.get("why", "")[:70] for e in ref).most_common(8),
        "woke": collections.Counter((x["wake"][0][:30] if x.get("wake") else "plan done") for x in m).most_common(6),
        "made": collections.Counter(e.get("item") for e in ev if e["kind"] == "made" and mine(e)).most_common(8),
        "deaths": collections.Counter(e.get("cause", "?") for e in ev if e["kind"] == "death"),
        "attacks": sum(1 for e in ev if e["kind"] == "attack"), "thefts": sum(1 for e in ev if e["kind"] in ("steal", "take_crop")),
        "models": collections.Counter((x.get("model") or "?").split(":")[-1][:28] for x in m).most_common(5),
    }


def pool(rs):
    """The measures of several worlds together (each counted with its own people)."""
    n = sum(r["answers"] for r in rs) or 1
    c = lambda k, top: collections.Counter(dict(sum((collections.Counter(dict(r[k])) for r in rs), collections.Counter()))).most_common(top)
    steps, refused = sum(r["steps"] for r in rs), sum(r["refused"] for r in rs)
    return {"pieces": sum(r["pieces"] for r in rs), "answers": sum(r["answers"] for r in rs), "hours": sum(r["hours"] for r in rs),
            "s": round(sum(r["s"] * r["answers"] for r in rs) / n, 1), "tout": round(sum(r["tout"] * r["answers"] for r in rs) / n),
            "refused": refused, "steps": steps, "refused_pct": round(100 * refused / max(1, steps), 1),
            "why": c("why", 8), "woke": c("woke", 6), "made": c("made", 8), "deaths": collections.Counter(dict(c("deaths", 20))),
            "attacks": sum(r["attacks"] for r in rs), "thefts": sum(r["thefts"] for r in rs), "models": c("models", 6)}


def show(label, r):
    print(f"  {label}: {r['answers']} answers in {r['pieces']} pieces ({r['hours']} world hours), {r['s']} s, {r['tout']} tokens out; "
          f"refused {r['refused']} of {r['steps']} steps ({r['refused_pct']}%)")
    print(f"    refused: {'; '.join(f'{w} ({c})' for w, c in r['why'][:6])}")
    print(f"    woke by: {', '.join(f'{w} ({c})' for w, c in r['woke'])}")
    print(f"    made: {', '.join(f'{k} {c}' for k, c in r['made'])}")
    print(f"    deaths: {dict(r['deaths'])}; blows {r['attacks']}; thefts {r['thefts']}; models: {dict(r['models'])}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="*", help="world folders (default: fetch world2)")
    ap.add_argument("--versions", type=int, default=3)
    a = ap.parse_args(argv)
    from civ.run import load
    tmp = tempfile.mkdtemp()
    dirs = a.dirs or [x for x in (fetch(b, os.path.join(tmp, b)) for b in ("world2",)) if x]
    worlds = {}
    for d in dirs:
        name = os.path.basename(os.path.dirname(os.path.abspath(d))) or d
        w = load(d)
        ids = {p.id for p in w.people.values() if p.mind == "llm"} | {x["id"] for p in pieces(d) for x in p["minds"]}
        worlds[name] = {"ps": pieces(d), "ids": ids, "when": w.when(), "alive": len(w.living()),
                        "minds": sum(1 for p in w.living() if p.mind == "llm")}
    for name, W in worlds.items():
        print(f"{name}: {W['when']}, {W['alive']} living, {W['minds']} with minds of their own")
    versions = sorted({p["rules"] for W in worlds.values() for p in W["ps"]}, key=lambda v: (len(v), v), reverse=True)[:a.versions]
    for v in versions:
        print(f"\n== rules {v}")
        rs = []
        for name, W in worlds.items():
            ps = [p for p in W["ps"] if p["rules"] == v]
            if ps:
                rs.append(measure(ps, W["ids"]))
                show(name, rs[-1])
        if len(rs) > 1:
            show("both", pool(rs))

if __name__ == "__main__":
    main()
