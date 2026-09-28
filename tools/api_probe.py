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

ARGS = [x for x in sys.argv[1:] if not x.startswith("--")]
TIMEOUT = next((int(x.split("=", 1)[1]) for x in sys.argv[1:] if x.startswith("--timeout=")), 30)
TRIES = next((int(x.split("=", 1)[1]) for x in sys.argv[1:] if x.startswith("--tries=")), 2)
LIST = "--list" in sys.argv
MODELS = ARGS or ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemma-4-31b-it"]


def list_models(key):
    """Every model this key can call with generateContent, with its token limits."""
    import urllib.request
    out, token = [], ""
    while True:
        url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200" + (f"&pageToken={token}" if token else "")
        req = urllib.request.Request(url, headers={"x-goog-api-key": key})
        with urllib.request.urlopen(req, timeout=30) as r:
            page = json.load(r)
        for m in page.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                out.append((m["name"].split("/", 1)[1], m.get("inputTokenLimit"), m.get("outputTokenLimit")))
        token = page.get("nextPageToken")
        if not token:
            return out


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is empty: the workflow maps it from the GEMINIAPI repository secret")
        return 1
    w = World(config.load()).generate()
    e = Engine(w)
    agents = w.living()[:max(2, TRIES)]
    for a in agents:
        a.wake = ["you have just woken at the start of spring"]
    lines = ["## Probe with real agent prompts"]
    models = MODELS
    if LIST:
        found = list_models(os.environ["GEMINI_API_KEY"].strip())
        lines.append("### Models this key can call\n" + "\n".join(f"- `{n}` in {i} out {o}" for n, i, o in found))
        if not ARGS:
            models = [n for n, _, _ in found if "gemma" in n]
    for m in models:
        gw = Gateway([m], max_calls=2 * TRIES + 2, rpm=5, timeout=TIMEOUT)
        for a in agents[:TRIES]:
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
