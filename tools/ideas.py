"""What the people want that the world does not offer yet: the backlog for new versions.

    python tools/ideas.py --dir .world/world            # or a checkout of the `world` branch
    python tools/ideas.py --dir wb/world --out ideas.md

Reads the world's logs and ranks three signals:
- ideas: the optional `idea` people give when they want to do, make or have
  something no one knows how to do yet (rules w8 on);
- deeds: free-form `do` actions, which have no effect of their own, so a deed
  done often is something people act out because the world cannot do it;
- failures: choices the engine refused, grouped by reason; an unknown verb is a
  thing someone tried that does not exist.

Ideas are grouped by the words they share, so "a raft to cross the water" and
"build a boat" land near each other. The grouping is rough on purpose: read the
examples, decide what to build, and when an idea becomes real, let the person
who first imagined it (if alive) work it out first.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from botciv.log import read  # noqa: E402

STOP = set("""a an the and or but to of for in on at by with from into onto over under i me my we our us you your
it its this that these those is are was were be been being have has had do does did can could would should will
shall may might must so if then than as not no yes some any all more most other others such very just also only
want wish need make made making build built get give take use using used like thing things something someone one
way ways help let lets able know how what which who whom whose where when why here there them they their he she
his her him""".split())


def words(text):
    return [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2 and w not in STOP]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="world")
    ap.add_argument("--out", default=None)
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args(argv)

    ideas, deeds, fails = [], [], Counter()
    names = {}
    for p in sorted(glob.glob(os.path.join(args.dir, "log", "events-*.jsonl.gz"))):
        for ev in read(p):
            k = ev.get("kind")
            if k == "idea":
                ideas.append(ev)
            elif k == "deed":
                deeds.append(ev)
            elif k == "fail":
                reason = ev["text"].split("could not: ", 1)[-1]
                fails[re.sub(r"\d+", "N", reason)] += 1
    try:
        with open(os.path.join(args.dir, "state.json")) as f:
            names = {int(k): v["name"] for k, v in json.load(f)["agents"].items()}
    except (OSError, ValueError, KeyError):
        pass

    L = [f"# What the people want ({len(ideas)} ideas, {len(deeds)} deeds, {sum(fails.values())} refused choices)", ""]
    from botciv.realized import REALIZED
    L.append("## Made real so far (botciv/realized.py)")
    L.extend(f"- {r['version']}: {r['what']}" for r in REALIZED)
    L.append("")
    # group ideas by their most telling shared word
    df = Counter(w for ev in ideas for w in set(words(ev.get("words") or ev["text"])))
    groups = defaultdict(list)
    for ev in ideas:
        ws = [w for w in words(ev.get("words") or ev["text"]) if df[w] > 1]
        key = max(ws, key=lambda w: (df[w], w)) if ws else "(alone)"
        groups[key].append(ev)
    L.append("## Ideas, grouped by a shared word")
    for key, evs in sorted(groups.items(), key=lambda kv: (kv[0] == "(alone)", -len(kv[1]))):
        people = sorted({names.get(ev.get("a"), str(ev.get("a"))) for ev in evs})
        first = min(evs, key=lambda ev: ev["t"])
        L.append(f"\n### {key} — {len(evs)} ideas from {len(people)} {'person' if len(people) == 1 else 'people'} (first: {names.get(first.get('a'), '?')}, hour {first['t']})")
        seen = set()
        for ev in evs[:8]:
            text = (ev.get("words") or ev["text"]).strip()
            if text.lower() in seen:
                continue
            seen.add(text.lower())
            L.append(f"- {names.get(ev.get('a'), '?')}: “{text}”")
    L.append("\n## Deeds acted out most (they change nothing by themselves)")
    dw = Counter(w for ev in deeds for w in set(words(ev.get("words") or ev["text"])))
    for w, n in dw.most_common(args.top):
        ex = next((ev.get("words") or ev["text"]) for ev in deeds if w in words(ev.get("words") or ev["text"]))
        L.append(f"- {w} ({n}): “{ex[:160]}”")
    L.append("\n## Choices the world refused, by reason")
    for reason, n in fails.most_common(args.top):
        L.append(f"- {n} × {reason}")
    text = "\n".join(L) + "\n"
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
