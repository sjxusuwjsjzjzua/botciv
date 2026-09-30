"""A trial on a Kaggle GPU: can an open model served there answer the world's people fast enough?

This script runs inside a Kaggle notebook (pushed by tools/kaggle_run.py). It reads the public
repository and the living world's state, builds real prompts for the living, serves an open
model with Ollama on the notebook's GPUs, asks it as many of those prompts as it can in the time
given, and writes what it measured to /kaggle/working. It holds no key and writes nowhere else:
the GitHub workflow collects the output.
"""
import collections
import json
import shutil
import os
import subprocess
import sys
import threading
import time
import urllib.request

SETTINGS = {"models": ["gemma4:26b", "gemma4:26b-a4b", "gemma4:12b", "gemma4"], "minutes": 25, "parallel": 4}
REPO = "https://github.com/sjxusuwjsjzjzua/botciv"
OUT = "/kaggle/working" if os.path.isdir("/kaggle/working") else os.getcwd()
URL = "http://127.0.0.1:11434"


def sh(cmd, timeout=3600):
    print("+", cmd, flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    tail = (r.stdout + r.stderr)[-1500:]
    print(tail, flush=True)
    return r.returncode, tail


def post(path, body, timeout=600):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def json_schema(s):
    """Gemini's schema (types in capitals, propertyOrdering) as plain JSON Schema."""
    if isinstance(s, dict):
        out = {}
        for k, v in s.items():
            if k == "propertyOrdering":
                continue
            out[k] = v.lower() if k == "type" and isinstance(v, str) else json_schema(v)
        return out
    if isinstance(s, list):
        return [json_schema(x) for x in s]
    return s


def prompts():
    sh(f"git clone -q --depth 1 {REPO} /tmp/botciv")
    sh("cd /tmp/botciv && git fetch -q --depth 1 origin world && mkdir -p /tmp/w "
       "&& git archive FETCH_HEAD world/state.json | tar -x -C /tmp/w")
    sys.path.insert(0, "/tmp/botciv")
    from botciv.engine import Engine
    from botciv.prompt import available_verbs, build_prompt, response_schema
    from botciv.world import World
    w = World.from_dict(json.load(open("/tmp/w/world/state.json")))
    e = Engine(w)
    out = []
    for a in w.living():
        verbs = available_verbs(e, a)
        out.append({"name": a.name, "prompt": build_prompt(e, a), "schema": json_schema(response_schema(verbs)),
                    "verbs": verbs})
    return out


def serve(parallel):
    sh("(apt-get -qq update || true) && apt-get -qq install -y zstd || (rm -f /etc/apt/sources.list.d/*cuda* "
       "/etc/apt/sources.list.d/*nvidia*; apt-get -qq update; apt-get -qq install -y zstd)", timeout=900)
    code, _ = sh("curl -fsSL https://ollama.com/install.sh | sh", timeout=900)
    if not shutil.which("ollama"):
        raise RuntimeError("ollama did not install (see the log above)")
    env = dict(os.environ, OLLAMA_NUM_PARALLEL=str(parallel), OLLAMA_KEEP_ALIVE="-1", OLLAMA_HOST="127.0.0.1:11434",
               OLLAMA_CONTEXT_LENGTH="8192")
    subprocess.Popen(["ollama", "serve"], env=env, stdout=open("/tmp/ollama.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            urllib.request.urlopen(URL + "/api/tags", timeout=5)
            return True
        except Exception:
            time.sleep(2)
    return False


def ask(model, p, think):
    body = {"model": model, "stream": False, "format": p["schema"],
            "options": {"temperature": 1.0, "num_ctx": 8192, "num_predict": 700},
            "messages": [{"role": "system", "content": "Reply with one JSON object and nothing else. "
                          "Leave out the fields you do not need."},
                         {"role": "user", "content": p["prompt"]}]}
    if think is not None:
        body["think"] = think
    return post("/api/chat", body)


def main():
    t0 = time.time()
    res = {"settings": SETTINGS, "started": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    res["gpu"] = sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")[1].strip()
    ps = prompts()
    res["prompts"] = len(ps)
    res["prompt_chars"] = sum(len(p["prompt"]) for p in ps) // max(1, len(ps))
    if not serve(SETTINGS["parallel"]):
        res["error"] = "the model server did not start"
        return finish(res)
    model = None
    for tag in SETTINGS["models"]:
        t = time.time()
        code, tail = sh(f"ollama pull {tag}", timeout=1800)
        if code == 0:
            model, res["pull_seconds"] = tag, round(time.time() - t)
            break
        res.setdefault("pull_failed", {})[tag] = tail[-200:]
    if not model:
        res["error"] = "no model could be pulled"
        return finish(res)
    res["model"] = model
    think = False
    try:
        t = time.time()
        ask(model, ps[0], think)
    except Exception as ex:             # a model without a thinking switch refuses the field
        res["think_field"] = str(ex)[:200]
        think = None
        ask(model, ps[0], think)
    res["first_answer_seconds"] = round(time.time() - t, 1)
    res["ps"] = sh("ollama ps")[1][-600:]

    calls, lock = [], threading.Lock()
    stop = time.time() + SETTINGS["minutes"] * 60
    nxt = [0]

    def worker():
        while time.time() < stop:
            with lock:
                p = ps[nxt[0] % len(ps)]
                nxt[0] += 1
            t = time.time()
            row = {"name": p["name"]}
            try:
                r = ask(model, p, think)
                text = r.get("message", {}).get("content", "")
                row.update(seconds=round(time.time() - t, 2), tin=r.get("prompt_eval_count"), tout=r.get("eval_count"),
                           prompt_s=round((r.get("prompt_eval_duration") or 0) / 1e9, 2),
                           gen_s=round((r.get("eval_duration") or 0) / 1e9, 2))
                try:
                    d = json.loads(text)
                    verb = str((d.get("action") or {}).get("verb", "")).lower()
                    row.update(ok=True, verb=verb, valid=verb in p["verbs"], text=text[:1500])
                except Exception:
                    row.update(ok=False, text=text[:300])
            except Exception as ex:
                row.update(ok=False, error=str(ex)[:200], seconds=round(time.time() - t, 2))
            with lock:
                calls.append(row)

    t = time.time()
    threads = [threading.Thread(target=worker) for _ in range(SETTINGS["parallel"])]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    span = time.time() - t
    good = [c for c in calls if c.get("ok")]
    res.update(calls=len(calls), answered=len(good), valid=sum(1 for c in good if c.get("valid")),
               minutes=round(span / 60, 1), per_hour=round(len(good) * 3600 / span),
               mean_seconds=round(sum(c["seconds"] for c in good) / max(1, len(good)), 1),
               mean_tokens_in=round(sum(c.get("tin") or 0 for c in good) / max(1, len(good))),
               mean_tokens_out=round(sum(c.get("tout") or 0 for c in good) / max(1, len(good))),
               verbs=dict(collections.Counter(c.get("verb") for c in good).most_common()),
               errors=[c.get("error") or c.get("text") for c in calls if not c.get("ok")][:5])
    res["samples"] = [json.loads(c["text"]) for c in good[:3] if c.get("text")]
    res["total_minutes"] = round((time.time() - t0) / 60, 1)
    json.dump(calls, open(os.path.join(OUT, "trial_calls.json"), "w"))
    finish(res)


def finish(res):
    json.dump(res, open(os.path.join(OUT, "trial_results.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "samples"}, indent=1), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:             # whatever went wrong, leave a result that says so
        import traceback
        finish({"settings": SETTINGS, "error": f"{type(ex).__name__}: {ex}", "trace": traceback.format_exc()[-1500:]})
