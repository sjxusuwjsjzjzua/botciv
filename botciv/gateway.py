"""The one place the models are called: Gemini, and Groq for the models named groq:<name>.

The Gemini key comes from GEMINI_API_KEY and is sent only as the x-goog-api-key
header, never in a URL, a log line or a file. The Groq key (GROQ_API_KEY, optional)
is sent only as a bearer header and scrubbed the same way.

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
GROQ_BASE = "https://api.groq.com/openai/v1"
KEY_RE = re.compile(r"AIza[0-9A-Za-z_\-]{20,}|gsk_[0-9A-Za-z]{20,}")


def loads_reply(text):
    """The answer's JSON object. Gemma on the API sometimes wraps it in a code fence (```json ... ```), whole or only
    at the end, though asked for JSON: about 150 replies a day each counted bad (2026-10-08). Plain JSON first; else
    the text from the first { to the last }."""
    try:
        return json.loads(text)
    except ValueError:
        a, b = text.find("{"), text.rfind("}")
        if a < 0 or b <= a:
            raise
        return json.loads(text[a:b + 1])


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
    # Groq's free tier counts tokens per minute and per day; the real per-minute figure is read from
    # its reply headers, and a per-day 429 marks the model spent
    "groq:": {"rpm": 25, "tpm": 5500, "timeout": 40},
    "gemma": {"rpm": 28, "tpm": 15000, "timeout": 150},
    "flash-lite": {"rpm": 14, "tpm": 240000, "timeout": 30},
    # a model served on this machine (Ollama, e.g. on a Kaggle GPU): no quota, only its own speed
    "ollama:": {"rpm": 100000, "tpm": 10 ** 9, "timeout": 600},
}
DEFAULT_LIMITS = {"rpm": 4, "tpm": 240000, "timeout": 90}      # larger models think before answering


def limits_for(m):
    # a service prefix decides first: "ollama:gemma4:26b" is a local model, not the API's Gemma
    for k, v in LIMITS.items():
        if k.endswith(":") and m.startswith(k):
            return v
    for k, v in LIMITS.items():
        if not k.endswith(":") and k in m:
            return v
    return DEFAULT_LIMITS


def compact(schema):
    """A reply schema in a short readable form, for models that take no response schema."""
    t = schema.get("type", "")
    if t == "OBJECT":
        return "{" + ", ".join(f'"{k}": {compact(v)}' for k, v in schema.get("properties", {}).items()) + "}"
    if t == "ARRAY":
        return "[" + compact(schema.get("items", {})) + "]"
    if schema.get("enum"):
        return "one of " + "|".join(schema["enum"])
    return {"STRING": "string", "INTEGER": "integer", "BOOLEAN": "true|false", "NUMBER": "number"}.get(t, "value")


def plain_schema(s):
    """Gemini's reply schema (types in capitals, propertyOrdering) as plain JSON Schema."""
    if isinstance(s, dict):
        return {k: (v.lower() if k == "type" and isinstance(v, str) else plain_schema(v))
                for k, v in s.items() if k != "propertyOrdering"}
    if isinstance(s, list):
        return [plain_schema(x) for x in s]
    return s


def model_size(name):
    """Billions of parameters from a model name (gemma-4-31b-it -> 31, gemma-3n-e4b-it -> 4), or 0."""
    m = re.search(r"(?:^|-)e?(\d+(?:\.\d+)?)b(?:-|$)", name)
    return float(m.group(1)) if m else 0.0


class Gateway:
    def __init__(self, models, quota_path=None, max_calls=None, timeout=30, rpm=10, thinking=None):
        self.key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not self.key and not all(m.startswith("ollama:") for m in models):
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.groq_key = os.environ.get("GROQ_API_KEY", "").strip()
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
        self.fails = {}         # model -> failures in a row; each one doubles its rest, a success clears it
        self.stopped = False    # set when the run is ending: waits give up instead of sleeping on
        self.bad = {}           # model -> 400s in a row
        self.lat = {}           # model -> seconds an answer takes, learned; the faster of two free models is asked
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
            if self.stopped:
                raise OutOfBudget("the run is ending")
            time.sleep(min(wait, 1.0))      # in short naps, so a stop is noticed

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
    def post_groq(self, m, body):
        req = urllib.request.Request(f"{GROQ_BASE}/chat/completions", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "botciv/1",
                                              "Authorization": "Bearer " + self.groq_key})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeouts.get(m, self.timeout)) as r:
                payload = json.load(r)
                payload["_headers"] = {k.lower(): v for k, v in r.headers.items()}
                return r.status, payload, time.time() - t0
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode())
            except Exception:
                payload = {}
            payload["_headers"] = {k.lower(): v for k, v in e.headers.items()}
            return e.code, payload, time.time() - t0
        except Exception as e:
            return 0, {"error": {"message": type(e).__name__}}, time.time() - t0

    def list_groq(self):
        """Names of the models the Groq key can call. Listing is free."""
        req = urllib.request.Request(f"{GROQ_BASE}/models", headers={"Authorization": "Bearer " + self.groq_key,
                                                                    "User-Agent": "botciv/1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return [x["id"] for x in json.load(r).get("data", [])]

    def clean(self, s):
        s = scrub(s, self.key)
        return s.replace(self.groq_key, "[redacted]") if self.groq_key else s

    def body_for(self, m, prompt, schema, temperature):
        if m.startswith("ollama:"):
            return {"model": m[7:], "stream": False, "format": plain_schema(schema), "think": False,
                    "options": {"temperature": temperature, "num_ctx": 8192, "num_predict": 700},
                    "messages": [{"role": "system", "content": "Reply with one JSON object and nothing else. "
                                  "Leave out the fields you do not need."},
                                 {"role": "user", "content": prompt}]}
        if m.startswith("groq:"):
            body = {"model": m[5:], "temperature": min(1.0, temperature), "max_tokens": 700,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": "Reply with one JSON object and nothing else, shaped like "
                                  + compact(schema) + ". Leave out the fields you do not need."},
                                 {"role": "user", "content": prompt}]}
            if "gpt-oss" in m or "qwen3" in m:
                # reasoning models: as little thinking as each allows, so the reply is quick and fits max_tokens
                body["reasoning_effort"] = "low" if "gpt-oss" in m else "none"
            return body
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature, "responseMimeType": "application/json",
                                     "responseSchema": schema, "maxOutputTokens": 8192}}
        if self.thinking.get(m):
            body["generationConfig"]["thinkingConfig"] = self.thinking[m]
        return body

    def extract(self, m, payload):
        """(reply text, usage in Gemini's field names, model version) from either service's reply."""
        if m.startswith("ollama:"):
            return (payload.get("message", {}).get("content", ""),
                    {"promptTokenCount": payload.get("prompt_eval_count"), "candidatesTokenCount": payload.get("eval_count")},
                    payload.get("model"))
        if m.startswith("groq:"):
            u = payload.get("usage", {})
            try:
                h = int(payload["_headers"]["x-ratelimit-limit-tokens"])
                self.tpm[m] = max(2000, int(h * 0.9))
            except (KeyError, TypeError, ValueError):
                pass
            return (payload["choices"][0]["message"]["content"],
                    {"promptTokenCount": u.get("prompt_tokens"), "candidatesTokenCount": u.get("completion_tokens")},
                    payload.get("model"))
        text = "".join(p.get("text", "") for p in payload["candidates"][0]["content"]["parts"] if not p.get("thought"))
        return text, payload.get("usageMetadata", {}), payload.get("modelVersion")

    def post(self, m, body):
        if m.startswith("groq:"):
            return self.post_groq(m, body)
        if m.startswith("ollama:"):
            url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/chat"
            req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json"})
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=self.timeouts.get(m, 600)) as r:
                    return r.status, json.load(r), time.time() - t0
            except urllib.error.HTTPError as e:
                return e.code, {"error": {"message": e.read().decode(errors="replace")[:200]}}, time.time() - t0
            except Exception as e:
                return 0, {"error": {"message": type(e).__name__}}, time.time() - t0
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
        if "_headers" in payload:                       # Groq: the message says which limit and for how long
            msg = payload.get("error", {}).get("message", "")
            per_day = "per day" in msg
            g = re.search(r"try again in ((?:[\d.]+(?:ms|h|m|s))+)", msg)
            if g:
                unit = {"h": 3600, "m": 60, "s": 1, "ms": 0.001}
                retry = sum(float(n) * unit[u] for n, u in re.findall(r"([\d.]+)(ms|h|m|s)", g.group(1)))
            elif payload["_headers"].get("retry-after"):
                try:
                    retry = float(payload["_headers"]["retry-after"])
                except ValueError:
                    pass
            return per_day, retry, ids
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
        so no model should sit idle while another is waited on. When none can take a
        call within MAX_WAIT seconds it raises OutOfBudget rather than sleep."""
        if not [m for m in self.available() if m not in self.dropped]:
            raise OutOfBudget("every model is spent for today")
        tried = {}
        last = None
        while True:
            cands = [m for m in self.available() if m not in self.dropped
                     and tried.get(m, 0) < (4 if "gemma" in m else 2)]      # Gemma has more passing server errors
            if not cands:
                return None, last or {"error": "no model answered"}
            m = self.pick(cands, prefer, prompt)
            if self.wait_for(m, self.estimate(m, prompt)) > self.MAX_WAIT:
                # every model is resting or full for a while: say so instead of sleeping, so the
                # run can end its piece, save the world and look again later
                raise OutOfBudget("every model is spent or resting for now")
            tried[m] = tried.get(m, 0) + 1
            with self.lock:
                if self.max_calls is not None and self.calls >= self.max_calls:
                    raise OutOfBudget("this run's call budget is spent")
                self.calls += 1
            slot = self.pace(m, self.estimate(m, prompt))
            body = self.body_for(m, prompt, schema, temperature)
            code, payload, dt = self.post(m, body)
            day = self.today(m)
            if code == 200:
                try:
                    text, u, version = self.extract(m, payload)
                    out = loads_reply(text)
                    if not isinstance(out, dict):
                        raise ValueError("not an object")
                except Exception as e:
                    with self.lock:
                        day["err"] += 1
                        self.failed(m, day, "bad reply")
                    last = {"model": m, "code": 200, "error": f"bad reply: {type(e).__name__}"}
                    continue
                with self.lock:
                    n_in = u.get("promptTokenCount") or 0
                    if n_in > 100:          # the per-minute token limit counts the prompt
                        slot[1] = n_in
                        self.cpt[m] = 0.8 * self.cpt[m] + 0.2 * (len(prompt) / n_in)
                    self.bad[m] = 0
                    self.fails[m] = 0
                    self.lat[m] = dt if m not in self.lat else 0.7 * self.lat[m] + 0.3 * dt
                    day["ok"] += 1
                    day["tokens_in"] += u.get("promptTokenCount", 0) or 0
                    day["tokens_out"] += (u.get("candidatesTokenCount", 0) or 0) + (u.get("thoughtsTokenCount", 0) or 0)
                return out, {"model": m, "version": version, "s": round(dt, 2),
                             "in": u.get("promptTokenCount"), "out": u.get("candidatesTokenCount"),
                             "think": u.get("thoughtsTokenCount")}
            with self.lock:
                day["err"] += 1
                self.errors += 1
                if code == 429:
                    slot[1] = 0             # refused: those tokens were not counted against the minute
                # a server error still counts its prompt against the minute (Gemma's 429s came mostly from the
                # model with the most 500s), so it stays in the tally
                self.failed(m, day, str(code or "timeout"), rest=code != 429, quick=dt < 5)   # a 429 carries its own wait
            err = payload.get("error", {})
            last = {"model": m, "code": code, "status": err.get("status"),
                    "error": self.clean(err.get("message", ""))[:200]}
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
                    if any(str(i["value"]) == "0" for i in ids):
                        per_day = True             # the free tier gives this model nothing
                    if per_day:
                        day["spent"] = True
                        day["spent_after"] = day["ok"]
                        day["spent_at"] = time.time()
                        continue
                    if not any("PerMinute" in i["id"] for i in ids) and not m.startswith("groq:"):
                        self.q["rpm"][m] = max(1, int(self.q["rpm"][m] * 0.8))
                    self.cool[m] = max(self.cool.get(m, 0), time.time() + min(60, retry if retry is not None else 10))
                continue
            with self.lock:
                if code == 404 or (code in (401, 403) and m.startswith("groq:")):
                    self.dropped.add(m)            # no such model for this key, or the key is refused
                elif code == 400:
                    self.bad[m] = self.bad.get(m, 0) + 1
                    if self.bad[m] >= 3:
                        self.dropped.add(m)        # it keeps rejecting what we send
                    tried[m] = 99
                # 5xx ("high demand"), timeouts: failed() has rested it, longer each time in a row

    MAX_WAIT = 90           # seconds a call may wait for room before the gateway gives up

    def stop(self):
        self.stopped = True

    def failed(self, m, day, code, rest=True, quick=False):
        """Count a failure (the caller holds the lock) and rest the model. A quick internal
        error (a 500 back within seconds) is a passing fault: gemma-4-31b gave one on about half
        its calls on 2026-09-29, at random, so it rests only 2 s. "High demand" (503) doubles from
        2 s up to a minute; timeouts and anything else double up to 10 minutes, so a model the
        service is struggling with stops taking calls that others could answer."""
        codes = day.setdefault("codes", {})
        codes[code] = codes.get(code, 0) + 1
        if not rest:
            return
        self.fails[m] = self.fails.get(m, 0) + 1
        if code == "500" and quick:
            wait = 2
        elif code == "503":
            wait = min(60, 2 ** min(self.fails[m], 6))
        else:
            wait = min(600, 2 ** min(self.fails[m], 10))
        self.cool[m] = max(self.cool.get(m, 0), time.time() + wait)

    def estimate(self, m, prompt):
        return int(len(prompt) / self.cpt[m]) + (900 if m.startswith("groq:") else 60)    # Groq: the reply schema and room to answer

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
        return min(cands, key=lambda m: (round(waits[m], 1), self.lat.get(m, 3 if "flash-lite" in m else 20),
                                         cands.index(m)))
