"""How big a world one Kaggle GPU notebook serves best. Runs inside a private Kaggle notebook
(pushed by tools/kaggle_run.py --script tools/kaggle_sweep_kernel.py).

A: how many decisions an hour the model gives with 4, 8, 12... answers at once (Ollama's
   parallel slots), on real prompts from a fresh world;
B: fresh worlds of several sizes advanced for real at the best slot count, recording once a
   minute the world's hour and the decisions made, so the first hours (everyone wakes at once)
   can be left out.

Writes /kaggle/working/sweep_results.json. Holds no key and writes nowhere else.
"""
import json
import shutil
import math
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib.request

SETTINGS = {"code": "main", "model": "gemma4:26b", "slots": [4, 8, 12, 16, 24], "slot_minutes": 4,
            "sizes": [16, 32, 64, 96], "size_minutes": 12}
REPO = "https://github.com/sjxusuwjsjzjzua/botciv"
OUT = "/kaggle/working" if os.path.isdir("/kaggle/working") else os.getcwd()
URL = "http://127.0.0.1:11434"
res = {"settings": SETTINGS, "started": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
server = [None]


def sh(cmd, timeout=3600):
    print("+", cmd, flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    tail = (r.stdout + r.stderr)[-1500:]
    print(tail, flush=True)
    return r.returncode, tail


def save():
    json.dump(res, open(os.path.join(OUT, "sweep_results.json"), "w"), indent=1)


def serve(slots):
    """(Re)start the model server with this many answers at once."""
    if server[0] is not None:
        server[0].terminate()
        try:
            server[0].wait(30)
        except Exception:
            server[0].kill()
        time.sleep(3)
    env = dict(os.environ, OLLAMA_NUM_PARALLEL=str(slots), OLLAMA_KEEP_ALIVE="-1", OLLAMA_HOST="127.0.0.1:11434",
               OLLAMA_CONTEXT_LENGTH="8192", OLLAMA_MAX_QUEUE="2048")
    server[0] = subprocess.Popen(["ollama", "serve"], env=env, stdout=open(f"/tmp/ollama-{slots}.log", "w"),
                                 stderr=subprocess.STDOUT)
    for _ in range(90):
        try:
            urllib.request.urlopen(URL + "/api/tags", timeout=5)
            return True
        except Exception:
            time.sleep(2)
    return False


def world_cfg(n):
    """A land sized for n people, as the default land (14) and configs/large.toml (100) are:
    about 41 tiles, 3.1 bushes and 0.2 herds a person."""
    side = max(24, int(round(math.sqrt(41 * n))))
    return {"world": {"width": side, "height": side, "agents": n, "max_population": int(n * 1.7),
                      "bushes": int(n * 3.1), "herds": max(3, round(n * 0.2)), "arrival_below": int(n * 1.3)},
            "resources": {"wolf_packs": max(1, round(n / 16))}}


def phase_a(model):
    from botciv import config
    from botciv.engine import Engine
    from botciv.gateway import plain_schema
    from botciv.prompt import available_verbs, build_prompt, response_schema
    from botciv.world import World
    w = World(config.load(None, world_cfg(48))).generate()
    e = Engine(w)
    ps = [{"prompt": build_prompt(e, a), "schema": plain_schema(response_schema(available_verbs(e, a)))}
          for a in w.living()]
    res["prompt_chars"] = sum(len(p["prompt"]) for p in ps) // len(ps)
    out = []
    for slots in SETTINGS["slots"]:
        row = {"slots": slots}
        if not serve(slots):
            row["error"] = "server did not start"
            out.append(row)
            continue
        body = lambda p: {"model": model, "stream": False, "format": p["schema"], "think": False,
                          "options": {"temperature": 1.0, "num_ctx": 8192, "num_predict": 700},
                          "messages": [{"role": "system", "content": "Reply with one JSON object and nothing else. "
                                        "Leave out the fields you do not need."},
                                       {"role": "user", "content": p["prompt"]}]}

        def ask(p):
            req = urllib.request.Request(URL + "/api/chat", data=json.dumps(body(p)).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.load(r)
        t = time.time()
        try:
            ask(ps[0])                                   # load the model
        except Exception as ex:
            row["error"] = f"first call: {type(ex).__name__} {ex}"[:200]
            out.append(row)
            continue
        row["load_seconds"] = round(time.time() - t, 1)
        row["ps"] = sh("ollama ps")[1][-300:]
        row["vram"] = sh("nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader")[1].strip()
        calls, lock, nxt = [], threading.Lock(), [0]
        stop = time.time() + SETTINGS["slot_minutes"] * 60

        def worker():
            while time.time() < stop:
                with lock:
                    p = ps[nxt[0] % len(ps)]
                    nxt[0] += 1
                t0 = time.time()
                try:
                    r = ask(p)
                    json.loads(r["message"]["content"])
                    c = {"ok": True, "s": time.time() - t0, "in": r.get("prompt_eval_count"), "out": r.get("eval_count")}
                except Exception as ex:
                    c = {"ok": False, "s": time.time() - t0, "err": str(ex)[:120]}
                with lock:
                    calls.append(c)
        t = time.time()
        th = [threading.Thread(target=worker) for _ in range(slots + 2)]
        [x.start() for x in th]
        mid = None
        time.sleep(SETTINGS["slot_minutes"] * 30)
        mid = sh("nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader")[1].strip()
        [x.join() for x in th]
        span = time.time() - t
        good = [c for c in calls if c["ok"]]
        row.update(calls=len(calls), ok=len(good), per_hour=round(len(good) * 3600 / span),
                   mean_s=round(sum(c["s"] for c in good) / max(1, len(good)), 1),
                   tokens_in=round(sum(c["in"] or 0 for c in good) / max(1, len(good))),
                   tokens_out=round(sum(c["out"] or 0 for c in good) / max(1, len(good))),
                   gpu_mid=mid, errors=[c.get("err") for c in calls if not c["ok"]][:3])
        out.append(row)
        res["phase_a"] = out
        save()
        print(json.dumps(row), flush=True)
    return out


def phase_b(model, slots):
    from botciv import config
    from botciv.engine import Engine
    from botciv.gateway import Gateway
    from botciv.minds.gemini import GeminiMind
    from botciv.run import assign_models
    from botciv.world import World
    out = []
    for n in SETTINGS["sizes"]:
        w = World(config.load(None, world_cfg(n))).generate()
        e = Engine(w)
        gw = Gateway(["ollama:" + model])
        assign_models(w, ["ollama:" + model])
        mind = GeminiMind(e, gw, None, parallel=slots + 2)
        t0 = time.time()
        end = t0 + SETTINGS["size_minutes"] * 60
        mind.deadline = end
        series, last = [], 0
        row = {"people": n, "side": w.cfg["world"]["width"]}
        try:
            while time.time() < end:
                e.tick(mind.decide)
                if time.time() - last >= 30:
                    last = time.time()
                    series.append([round(last - t0), w.tick, mind.model_decisions, len(w.living()), len(mind.pending)])
        except Exception as ex:                      # the time limit ends it while waiting for answers
            row["stop"] = f"{type(ex).__name__}: {ex}"[:120]
        mind.close()
        series.append([round(time.time() - t0), w.tick, mind.model_decisions, len(w.living()), 0])
        row["series"] = series
        # steady state: leave out the first quarter (everyone decides at the start)
        cut = next((s for s in series if s[0] >= SETTINGS["size_minutes"] * 15), series[0])
        fin = series[-1]
        mins = (fin[0] - cut[0]) / 60
        if mins > 0:
            row.update(decisions_per_hour=round((fin[2] - cut[2]) * 60 / mins),
                       world_hours_per_hour=round((fin[1] - cut[1]) * 60 / mins, 1),
                       days_per_hour=round((fin[1] - cut[1]) * 60 / mins / w.tpd(), 2),
                       decisions_per_person_hour=round((fin[2] - cut[2]) / max(1, fin[1] - cut[1]) / n, 3))
        row["bots"] = mind.bot_decisions
        out.append(row)
        res["phase_b"] = out
        save()
        print(json.dumps({k: v for k, v in row.items() if k != "series"}), flush=True)
    return out


def main():
    res["gpu"] = sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")[1].strip()
    sh(f"git clone -q --single-branch --branch main {REPO} /tmp/botciv && cd /tmp/botciv && git checkout -q {SETTINGS['code']}")
    sys.path.insert(0, "/tmp/botciv")
    os.chdir("/tmp/botciv")
    sh("(apt-get -qq update || true) && apt-get -qq install -y zstd || (rm -f /etc/apt/sources.list.d/*cuda* "
       "/etc/apt/sources.list.d/*nvidia*; apt-get -qq update; apt-get -qq install -y zstd)", timeout=900)
    sh("curl -fsSL https://ollama.com/install.sh | sh", timeout=900)
    if not shutil.which("ollama"):
        raise RuntimeError("ollama did not install (see the log above)")
    if not serve(4):
        res["error"] = "the model server did not start"
        return
    code, tail = sh(f"ollama pull {SETTINGS['model']}", timeout=1800)
    if code:
        res["error"] = "pull failed: " + tail[-200:]
        return
    a = phase_a(SETTINGS["model"])
    good = [r for r in a if r.get("per_hour")]
    if not good:
        res["error"] = "no slot count answered"
        return
    top = max(r["per_hour"] for r in good)
    best = min(r["slots"] for r in good if r["per_hour"] >= 0.95 * top)     # the fewest slots within 5% of the best
    res["best_slots"] = best
    serve(best)
    phase_b(SETTINGS["model"], best)


if __name__ == "__main__":
    T0 = time.time()
    try:
        main()
    except Exception as ex:
        res["error"] = f"{type(ex).__name__}: {ex}"
        res["trace"] = traceback.format_exc()[-1500:]
    finally:
        res["total_minutes"] = round((time.time() - T0) / 60, 1)
        save()
        print(json.dumps({k: v for k, v in res.items() if k != "phase_b"}, indent=1)[:4000], flush=True)
