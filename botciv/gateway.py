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
    """Gemini's daily quotas reset at midnight in Los Angeles (daylight time included)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    except Exception:
        return (datetime.now(timezone.utc) - timedelta(hours=7)).strftime("%Y-%m-%d")


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


def model_size(name):
    """Billions of parameters from a model name (gemma-4-31b-it -> 31, gemma-3n-e4b-it -> 4), or 0."""
    m = re.search(r"(?:^|-)e?(\d+(?:\.\d+)?)b(?:-|$)", name)
    return float(m.group(1)) if m else 0.0


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
        self.cpt = {m: 3.6 for m in self.models}     # prompt characters per token, learned from replies
        self.cool = {}          # model -> time before which it should not be called (after a 429 or 5xx)
        self.bad = {}           # model -> 400s in a row
        self.dropped = set()    # models that do not exist for this key or reject every request
        for m in self.models:
            self.q["rpm"].setdefault(m, min(rpm, limits_for(m)["rpm"]) if rpm != 10 else limits_for(m)["rpm"])
            for qid, v in self.q["limits"].get(m, {}).items():
                if "PerMinute" in qid and "Request" in qid:
                    try:
                        self.q["rpm"][m] = max(1, int(v) - 1)
                    except (TypeError, ValueError):
                        pass
                if "PerMinute" in qid and "Token" in qid:
                    try:
                        self.tpm[m] = max(2000, int(int(v) * 0.95))
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
        """Models not spent today. A spent model is tried again after 30 minutes, in case
        the day's reset came sooner than we reckoned; a 429 simply marks it spent again."""
        out = []
        for m in self.models:
            d = self.today(m)
            if not d["spent"] or time.time() - d.get("spent_at", 0) > 1800:
                out.append(m)
        return out

    def save(self):
        if self.quota_path:
            os.makedirs(os.path.dirname(self.quota_path) or ".", exist_ok=True)
            days = self.q["days"]
            for d in sorted(days)[:-30]:
                del days[d]
            with open(self.quota_path, "w") as f:
                json.dump(self.q, f, indent=1, sort_keys=True)

    def pace(self, m, est_tokens=0):
        """Block until a call to model m fits its per-minute request and token rates
        and any rest it was given after an error. Returns the token entry, so the
        estimate can be replaced by the real count."""
        while True:
            with self.lock:
                now = time.time()
                st = [t for t in self.stamps[m] if now - t < 60]
                tk = [e for e in self.tokens[m] if now - e[0] < 60]
                self.stamps[m], self.tokens[m] = st, tk
                used = sum(e[1] for e in tk)
                waits = []
                if self.cool.get(m, 0) > now:
                    waits.append(self.cool[m] - now)
                if len(st) >= self.q["rpm"][m]:
                    waits.append(60 - (now - st[0]))
                if tk and used + est_tokens > self.tpm[m]:
                    waits.append(60 - (now - tk[0][0]))
                if not waits:
                    st.append(now)
                    entry = [now, est_tokens]
                    tk.append(entry)
                    return entry
                wait = max(0.05, max(waits) + 0.05)
            time.sleep(wait)

    def list_models(self):
        """Names of every model this key can call with generateContent. Listing is free."""
        out, token = [], ""
        while True:
            url = f"{BASE}?pageSize=200" + (f"&pageToken={token}" if token else "")
            req = urllib.request.Request(url, headers={"x-goog-api-key": self.key})
            with urllib.request.urlopen(req, timeout=30) as r:
                page = json.load(r)
            out += [m["name"].split("/", 1)[1] for m in page.get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])]
            token = page.get("nextPageToken")
            if not token:
                return out

    def add_models(self, names):
        for m in names:
            if m in self.models:
                continue
            self.models.append(m)
            lim = limits_for(m)
            self.timeouts[m] = lim["timeout"]
            self.tpm[m] = lim["tpm"]
            self.cpt[m] = 3.6
            self.q["rpm"].setdefault(m, lim["rpm"])
            self.stamps[m], self.tokens[m] = [], []

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
        """Return (parsed_json, meta). Raises OutOfBudget when nothing can be called.

        Each attempt goes to the model that can take a call soonest: the preferred one
        if it is free now, otherwise whichever has room. Flash-Lite's allowance is per
        day and keeps; Gemma's is per minute and is lost when a minute passes unused,
        so no model should sit idle while another is waited on."""
        if not [m for m in self.available() if m not in self.dropped]:
            raise OutOfBudget("every model is spent for today")
        tried = {}
        last = None
        while True:
            cands = [m for m in self.available() if m not in self.dropped
                     and tried.get(m, 0) < (3 if "gemma" in m else 2)]      # Gemma has more passing server errors
            if not cands:
                return None, last or {"error": "no model answered"}
            m = self.pick(cands, prefer, prompt)
            tried[m] = tried.get(m, 0) + 1
            with self.lock:
                if self.max_calls is not None and self.calls >= self.max_calls:
                    raise OutOfBudget("this run's call budget is spent")
                self.calls += 1
            slot = self.pace(m, self.estimate(m, prompt))
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
                    n_in = u.get("promptTokenCount") or 0
                    if n_in > 100:          # the per-minute token limit counts the prompt
                        slot[1] = n_in
                        self.cpt[m] = 0.8 * self.cpt[m] + 0.2 * (len(prompt) / n_in)
                    self.bad[m] = 0
                    day["ok"] += 1
                    day["tokens_in"] += u.get("promptTokenCount", 0) or 0
                    day["tokens_out"] += (u.get("candidatesTokenCount", 0) or 0) + (u.get("thoughtsTokenCount", 0) or 0)
                return out, {"model": m, "version": payload.get("modelVersion"), "s": round(dt, 2),
                             "in": u.get("promptTokenCount"), "out": u.get("candidatesTokenCount"),
                             "think": u.get("thoughtsTokenCount")}
            with self.lock:
                day["err"] += 1
                self.errors += 1
                if code != 0:
                    slot[1] = 0             # refused or failed on arrival: those tokens were not spent
            err = payload.get("error", {})
            last = {"model": m, "code": code, "status": err.get("status"),
                    "error": scrub(err.get("message", ""), self.key)[:200]}
            if code == 429:
                per_day, retry, ids = self.quota_info(payload)
                with self.lock:
                    if ids:
                        self.q["limits"].setdefault(m, {})
                        for i in ids:
                            self.q["limits"][m][i["id"]] = i["value"]
                            if "PerMinute" in i["id"] and "Request" in i["id"]:
                                try:
                                    self.q["rpm"][m] = max(1, int(i["value"]) - 1)
                                except (TypeError, ValueError):
                                    pass
                            if "PerMinute" in i["id"] and "Token" in i["id"]:
                                try:
                                    self.tpm[m] = max(2000, int(int(i["value"]) * 0.95))
                                except (TypeError, ValueError):
                                    pass
                    if per_day:
                        day["spent"] = True
                        day["spent_after"] = day["ok"]
                        day["spent_at"] = time.time()
                        continue
                    if not any("PerMinute" in i["id"] for i in ids):
                        self.q["rpm"][m] = max(1, int(self.q["rpm"][m] * 0.8))
                    self.cool[m] = time.time() + min(60, retry if retry is not None else 10)
                continue
            with self.lock:
                if code == 404:
                    self.dropped.add(m)            # no such model for this key
                elif code == 400:
                    self.bad[m] = self.bad.get(m, 0) + 1
                    if self.bad[m] >= 3:
                        self.dropped.add(m)        # it keeps rejecting what we send
                    tried[m] = 99
                else:
                    self.cool[m] = time.time() + 3 * tried[m]     # 5xx or timeout: rest it a moment

    def estimate(self, m, prompt):
        return int(len(prompt) / self.cpt[m]) + 60

    def wait_for(self, m, est):
        """Seconds until model m could take a call of est tokens, without reserving it."""
        with self.lock:
            now = time.time()
            st = [t for t in self.stamps[m] if now - t < 60]
            tk = [e for e in self.tokens[m] if now - e[0] < 60]
            used = sum(e[1] for e in tk)
            waits = [max(0.0, self.cool.get(m, 0) - now)]
            if len(st) >= self.q["rpm"][m]:
                waits.append(60 - (now - st[0]))
            if tk and used + est > self.tpm[m]:
                waits.append(60 - (now - tk[0][0]))
            return max(waits)

    def pick(self, cands, prefer, prompt):
        waits = {m: self.wait_for(m, self.estimate(m, prompt)) for m in cands}
        if prefer in waits and waits[prefer] <= 0:
            return prefer
        return min(cands, key=lambda m: (waits[m], cands.index(m)))
