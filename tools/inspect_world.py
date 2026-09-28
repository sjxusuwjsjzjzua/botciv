"""Summarise a world directory for review: what minds chose, what failed, what happened.

    python tools/inspect_world.py world [--thoughts 20] [--agent NAME]
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from botciv.log import read  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--thoughts", type=int, default=15)
    ap.add_argument("--agent")
    args = ap.parse_args()
    evs, minds = [], []
    for p in sorted(glob.glob(os.path.join(args.dir, "log", "events-*.jsonl.gz"))):
        evs.extend(e for e in read(p) if e["kind"] != "frame")
    for p in sorted(glob.glob(os.path.join(args.dir, "log", "minds-*.jsonl.gz"))):
        minds.extend(read(p))
    ticks = (evs[-1]["t"] - evs[0]["t"] + 1) if evs else 1
    print(f"{len(minds)} decisions over {ticks} hours ({len(minds) / max(1, ticks):.2f} per hour)")
    ok = [m for m in minds if m.get("out")]
    print(f"answered {len(ok)}, retries {sum(1 for m in minds if m.get('retry'))}, bot fallbacks {sum(1 for m in minds if m.get('bot'))}")
    lat = sorted((m["meta"].get("s") or 0) for m in ok)
    if lat:
        print(f"latency median {lat[len(lat) // 2]:.1f}s, p90 {lat[int(len(lat) * .9)]:.1f}s; "
              f"tokens in {sum(m['meta'].get('in') or 0 for m in ok) // len(ok)}, out {sum(m['meta'].get('out') or 0 for m in ok) // len(ok)} per call")
    print("models:", dict(Counter(m["meta"].get("model") for m in ok)))
    print("verbs chosen:", dict(Counter((m["out"].get("action") or {}).get("verb") for m in ok).most_common()))
    print("with plan:", sum(1 for m in ok if m["out"].get("plan")), "with speech:",
          sum(1 for m in ok if (m["out"].get("speech") or {}).get("text")), "with eat:", sum(1 for m in ok if m["out"].get("eat")))
    wakes = Counter()
    for m in minds:
        for w in m.get("wake", []):
            wakes[" ".join(x if not x[:1].isupper() else "X" for x in w.split())[:45]] += 1
    print("\nwhy asked:")
    for k, v in wakes.most_common(15):
        print(f"  {v:4d} {k}")
    print("\nevents:", dict(Counter(e["kind"] for e in evs).most_common()))
    fails = Counter(e["text"].split(" but could not: ")[-1][:70] for e in evs if e["kind"] == "fail")
    print("\nfailures:")
    for k, v in fails.most_common(20):
        print(f"  {v:4d} {k}")
    print("\nnotable:")
    for e in evs:
        if e["kind"] in ("death", "birth", "arrive", "group_found", "join", "deal", "promise_kept", "promise_broken",
                         "steal", "steal_fail", "attack", "craft", "teach", "build", "mark", "deed", "expel", "vote_result",
                         "conceive", "lost_knowledge"):
            print(f"  [{e['t']}] {e['text']}")
    print("\nsome speech:")
    says = [e for e in evs if e["kind"] in ("say", "whisper")]
    for e in says[:: max(1, len(says) // 25)][:25]:
        print(f"  [{e['t']}] {e['text'][:200]}")
    sel = [m for m in ok if not args.agent or m.get("name") == args.agent]
    print("\nsample thoughts:")
    for m in sel[:: max(1, len(sel) // args.thoughts)][: args.thoughts]:
        o = m["out"]
        print(f"  [{m['t']}] {m.get('name')} ({'; '.join(m.get('wake', []))[:60]}): {o.get('thought', '')[:220]}")
        print(f"        -> {json.dumps(o.get('action'))[:160]}")


if __name__ == "__main__":
    main()
