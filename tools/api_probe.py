"""Probe what the Gemini key can reach: models, latency, errors, quota hints.

Reads GEMINI_API_KEY from the environment and sends it only as the
x-goog-api-key header. Prints nothing that contains the key.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://generativelanguage.googleapis.com/v1beta"
KEY = os.environ.get("GEMINI_API_KEY", "")
KEY_RE = re.compile(r"AIza[0-9A-Za-z_\-]{20,}")


def scrub(s):
    s = KEY_RE.sub("[redacted]", str(s))
    return s.replace(KEY, "[redacted]") if KEY else s


def req(method, path, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "Content-Type": "application/json", "x-goog-api-key": KEY})
    t = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.load(resp), time.time() - t
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {}
        return e.code, payload, time.time() - t
    except Exception as e:
        return 0, {"error": {"message": type(e).__name__}}, time.time() - t


def quota_details(payload):
    out = []
    for d in payload.get("error", {}).get("details", []):
        t = d.get("@type", "")
        if t.endswith("QuotaFailure"):
            for v in d.get("violations", []):
                out.append({"quotaId": v.get("quotaId"), "metric": v.get("quotaMetric"),
                            "value": v.get("quotaValue"), "dims": v.get("quotaDimensions")})
        elif t.endswith("RetryInfo"):
            out.append({"retryDelay": d.get("retryDelay")})
    return out


def call(model, text="Reply with one word: ready.", schema=False, thinking=None):
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"temperature": 1.0, "maxOutputTokens": 64}}
    if schema:
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = {
            "type": "OBJECT", "properties": {"word": {"type": "STRING"}}, "required": ["word"]}
    if thinking is not None:
        body["generationConfig"]["thinkingConfig"] = thinking
    code, payload, dt = req("POST", f"/models/{model}:generateContent", body)
    if code == 200:
        u = payload.get("usageMetadata", {})
        return {"ok": True, "s": round(dt, 1), "ver": payload.get("modelVersion"),
                "in": u.get("promptTokenCount"), "out": u.get("candidatesTokenCount"),
                "think": u.get("thoughtsTokenCount")}
    err = payload.get("error", {})
    return {"ok": False, "code": code, "s": round(dt, 1), "status": err.get("status"),
            "msg": scrub(err.get("message", ""))[:300], "quota": quota_details(payload)}


def main():
    if not KEY:
        print("GEMINI_API_KEY not set")
        return 1
    lines = []
    code, payload, _ = req("GET", "/models?pageSize=1000")
    models = []
    if code == 200:
        for m in payload.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                models.append((m["name"].split("/", 1)[1], m.get("inputTokenLimit"), m.get("thinking")))
    else:
        print("list models failed", code, scrub(payload)[:300])
    lines.append(f"## Models with generateContent ({len(models)})")
    for name, lim, th in models:
        lines.append(f"- `{name}` in={lim} thinking={th}")

    names = [m[0] for m in models]
    cands = [n for n in names if ("flash" in n or "gemma" in n)
             and not any(x in n for x in ("image", "tts", "audio", "live", "embedding", "robotics", "computer"))]
    lines.append("\n## One call per candidate (schema JSON)")
    results = {}
    for n in cands:
        r = call(n, schema=True)
        results[n] = r
        lines.append(f"- `{n}`: {json.dumps(r)}")

    ok = [n for n in cands if results[n]["ok"] and "lite" in n]
    lines.append("\n## Thinking config tests")
    for n in ok[:3]:
        for th in ({"thinkingBudget": 0}, {"thinkingLevel": "minimal"}, {"thinkingLevel": "low"}):
            lines.append(f"- `{n}` {th}: {json.dumps(call(n, thinking=th))}")

    if ok:
        target = ok[0]
        lines.append(f"\n## Burst of 40 calls on `{target}`, 8 in parallel")
        with ThreadPoolExecutor(8) as ex:
            rs = list(ex.map(lambda _: call(target), range(40)))
        good = sum(1 for r in rs if r["ok"])
        lines.append(f"- ok {good}/40")
        seen = set()
        for r in rs:
            if not r["ok"]:
                key = json.dumps(r.get("quota")) + str(r.get("code"))
                if key not in seen:
                    seen.add(key)
                    lines.append(f"- error: {json.dumps(r)}")
    out = "\n".join(lines)
    print(out)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a") as f:
            f.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
