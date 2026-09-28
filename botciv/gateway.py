"""The one place Gemini is called.

The key comes from GEMINI_API_KEY and is sent only as the x-goog-api-key
header, never in a URL, a log line or a file.

Quotas are unknown, so the gateway learns them: it counts calls per model per
day (Pacific time, when Gemini's daily quotas reset), backs off on per-minute
429s, and marks a model spent for the day on a per-day 429. What it learns is
saved to a JSON file so the next run starts from it.
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
KEY_RE = re.compile(r"AIza[0-9A-Za-z_\-]{20,}")


class OutOfBudget(Exception):
    pass


def pacific_day():
    # Pacific time without tz data: UTC-8 (close enough to UTC-7 in summer for a day key)
    return (datetime.now(timezone.utc) - timedelta(hours=8)).strftime("%Y-%m-%d")


def scrub(s, key=""):
    s = KEY_RE.sub("[redacted]", str(s))
    return s.replace(key, "[redacted]") if key else s


# What each model family allows on the free tier (AI Studio, 2026-09-27), kept
# a little under the limits. Gemma is slow and token-limited: a long timeout.
LIMITS = {
    "gemma": {"rpm": 28, "tpm": 15000, "timeout": 150},
    "flash-lite": {"rpm": 14, "tpm": 240000, "timeout": 30},
}
DEFAULT_LIMITS = {"rpm": 4, "tpm": 240000, "timeout": 30}


def limits_for(m):
    for k, v in LIMITS.items():
        if k in m:
            return v
    return DEFAULT_LIMITS


class Gateway:
    def __init__(self, models, quota_path=None, max_calls=None, timeout=30, rpm=10, thinking=None):
        self.key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not self.key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.models = list(models)
        self.timeout = timeout
        self.max_calls = max_calls
        self.thinking = thinking or {}
        self.lock = threading.Lock()
        self.quota_path = quota_path
        self.q = {}
        if quota_path and os.path.exists(quota_path):
            with open(quota_path) as f:
                self.q = json.load(f)
        self.q.setdefault("days", {})
        self.q.setdefault("rpm", {})
        self.q.setdefault("limits", {})
        self.timeouts = {m: limits_for(m)["timeout"] if timeout == 30 else timeout for m in self.models}
        self.tpm = {m: limits_for(m)["tpm"] for m in self.models}
        for m in self.models:
            self.q["rpm"].setdefault(m, min(rpm, limits_for(m)["rpm"]) if rpm != 10 else limits_for(m)["rpm"])
            for qid, v in self.q["limits"].get(m, {}).items():
                if "PerMinute" in qid and "Request" in qid:
                    try:
                        self.q["rpm"][m] = max(1, int(v) - 1)
                    except (TypeError, ValueError):
                        pass
        self.stamps = {m: [] for m in self.models}
        self.tokens = {m: [] for m in self.models}   # (time, tokens) in the last minute
        self.calls = 0
        self.errors = 0

    # ---------- bookkeeping ----------
    @property
    def day(self):
        return pacific_day()        # recomputed, so a long run crosses midnight correctly

    def today(self, m):
        return self.q["days"].setdefault(self.day, {}).setdefault(
            m, {"ok": 0, "err": 0, "spent": False, "tokens_in": 0, "tokens_out": 0})

    def available(self):
        return [m for m in self.models if not self.today(m)["spent"]]

    def save(self):
        if self.quota_path:
            os.makedirs(os.path.dirname(self.quota_path) or ".", exist_ok=True)
            days = self.q["days"]
            for d in sorted(days)[:-30]:
                del days[d]
            with open(self.quota_path, "w") as f:
                json.dump(self.q, f, indent=1, sort_keys=True)

    def pace(self, m, est_tokens=0):
        """Block until a call to model m fits its per-minute request and token rates."""
        while True:
            with self.lock:
                now = time.time()
                st = [t for t in self.stamps[m] if now - t < 60]
                tk = [(t, n) for t, n in self.tokens[m] if now - t < 60]
                self.stamps[m], self.tokens[m] = st, tk
                used = sum(n for _, n in tk)
                if len(st) < self.q["rpm"][m] and (not tk or used + est_tokens <= self.tpm[m]):
                    st.append(now)
                    tk.append((now, est_tokens))
                    return
                waits = []
                if len(st) >= self.q["rpm"][m]:
                    waits.append(60 - (now - st[0]))
                if tk and used + est_tokens > self.tpm[m]:
                    waits.append(60 - (now - tk[0][0]))
                wait = max(0.05, min(waits) + 0.05)
            time.sleep(wait)

    # ---------- calling ----------
    def post(self, m, body):
        req = urllib.request.Request(f"{BASE}/{m}:generateContent", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": self.key})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeouts.get(m, self.timeout)) as r:
                return r.status, json.load(r), time.time() - t0
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode())
            except Exception:
                payload = {}
            return e.code, payload, time.time() - t0
        except Exception as e:
            return 0, {"error": {"message": type(e).__name__}}, time.time() - t0

    def quota_info(self, payload):
        per_day, retry, ids = False, None, []
        for d in payload.get("error", {}).get("details", []):
            t = d.get("@type", "")
            if t.endswith("QuotaFailure"):
                for v in d.get("violations", []):
                    qid = v.get("quotaId", "")
                    ids.append({"id": qid, "value": v.get("quotaValue")})
                    if "PerDay" in qid:
                        per_day = True
            elif t.endswith("RetryInfo"):
                rd = d.get("retryDelay", "")
                try:
                    retry = float(str(rd).rstrip("s"))
                except ValueError:
                    pass
        return per_day, retry, ids

    def generate(self, prompt, schema, prefer=None, temperature=1.0):
        """Return (parsed_json, meta). Raises OutOfBudget when nothing can be called."""
        order = self.available()
        if prefer in order:
            order.remove(prefer)
            order.insert(0, prefer)
        if not order:
            raise OutOfBudget("every model is spent for today")
        last = None
        for m in order:
            for attempt in (0, 1):
                with self.lock:
                    if self.max_calls is not None and self.calls >= self.max_calls:
                        raise OutOfBudget("this run's call budget is spent")
                    self.calls += 1
                self.pace(m, len(prompt) // 3 + 400)
                body = {"contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json",
                                             "responseSchema": schema, "maxOutputTokens": 2048}}
                if self.thinking.get(m):
                    body["generationConfig"]["thinkingConfig"] = self.thinking[m]
                code, payload, dt = self.post(m, body)
                day = self.today(m)
                if code == 200:
                    try:
                        text = "".join(p.get("text", "") for p in payload["candidates"][0]["content"]["parts"]
                                       if not p.get("thought"))
                        out = json.loads(text)
                    except Exception as e:
                        with self.lock:
                            day["err"] += 1
                        last = {"model": m, "code": 200, "error": f"bad reply: {type(e).__name__}"}
                        continue
                    u = payload.get("usageMetadata", {})
                    with self.lock:
                        day["ok"] += 1
                        day["tokens_in"] += u.get("promptTokenCount", 0) or 0
                        day["tokens_out"] += (u.get("candidatesTokenCount", 0) or 0) + (u.get("thoughtsTokenCount", 0) or 0)
                    return out, {"model": m, "version": payload.get("modelVersion"), "s": round(dt, 2),
                                 "in": u.get("promptTokenCount"), "out": u.get("candidatesTokenCount"),
                                 "think": u.get("thoughtsTokenCount")}
                with self.lock:
                    day["err"] += 1
                    self.errors += 1
                err = payload.get("error", {})
                last = {"model": m, "code": code, "status": err.get("status"),
                        "error": scrub(err.get("message", ""), self.key)[:200]}
                if code == 429:
                    per_day, retry, ids = self.quota_info(payload)
                    if ids:
                        with self.lock:
                            self.q["limits"].setdefault(m, {})
                            for i in ids:
                                self.q["limits"][m][i["id"]] = i["value"]
                                if "PerMinute" in i["id"] and "Request" in i["id"]:
                                    try:
                                        self.q["rpm"][m] = max(1, int(i["value"]) - 1)
                                    except (TypeError, ValueError):
                                        pass
                    if per_day:
                        with self.lock:
                            day["spent"] = True
                            day["spent_after"] = day["ok"]
                        break
                    if not any("PerMinute" in i["id"] for i in ids):
                        with self.lock:
                            self.q["rpm"][m] = max(1, int(self.q["rpm"][m] * 0.8))
                    time.sleep(min(60, retry or 10))
                    continue
                if code == 400:
                    break          # this model rejects the request; try the next
                time.sleep(2)      # 5xx or timeout: one retry
        return None, last or {"error": "no model answered"}
