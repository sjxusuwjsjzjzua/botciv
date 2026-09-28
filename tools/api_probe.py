"""Probe the Gemini key with real agent prompts.

Reads GEMINI_API_KEY from the environment; the gateway sends it only as a
header. Prints model replies (simulation content only) and quota errors.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from botciv import config  # noqa: E402
from botciv.engine import Engine  # noqa: E402
from botciv.gateway import Gateway  # noqa: E402
from botciv.prompt import build_prompt, response_schema, available_verbs  # noqa: E402
from botciv.world import World  # noqa: E402

MODELS = sys.argv[1:] or ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemma-4-31b-it"]


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is empty: add it under Settings > Secrets and variables > Actions")
        return 1
    w = World(config.load()).generate()
    e = Engine(w)
    agents = w.living()[:2]
    for a in agents:
        a.wake = ["you have just woken at the start of spring"]
    lines = ["## Probe with real agent prompts"]
    for m in MODELS:
        gw = Gateway([m], max_calls=4, rpm=5)
        for a in agents:
            t = time.time()
            prompt = build_prompt(e, a)
            out, meta = gw.generate(prompt, response_schema(available_verbs(e, a)), temperature=1.0)
            lines.append(f"\n### `{m}` as {a.name} ({time.time() - t:.1f}s)")
            lines.append(f"meta: `{json.dumps(meta)}`")
            if out:
                lines.append("```json\n" + json.dumps(out, indent=1, ensure_ascii=False)[:2500] + "\n```")
        lines.append(f"quota learned: `{json.dumps(gw.q.get('limits', {}))}`")
    text = "\n".join(lines)
    print(text)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
