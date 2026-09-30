"""The living world advanced on a Kaggle GPU for an hour or so.

This script runs inside a private Kaggle notebook (pushed by tools/kaggle_world.py). While the
model server starts and the model is fetched, the GitHub workflow takes the world's lock and waits
for the Actions runner to finish its piece. When the world branch's LOCK says go (for this run),
the notebook takes that commit of the world, advances it with the people's minds served here by
Ollama, and leaves the advanced world in /kaggle/working/world.tar.gz. It holds no key and writes
nowhere else: the workflow brings the world back and pushes it.
"""
import json
import os
import subprocess
import sys
import time
import traceback
import urllib.request

SETTINGS = {"code": "main", "run": "", "minutes": 55, "parallel": 4, "model": "gemma4:26b", "wait": 45,
            "branch": "world", "sha": "", "config": ""}
REPO = "https://github.com/sjxusuwjsjzjzua/botciv"
OUT = "/kaggle/working" if os.path.isdir("/kaggle/working") else os.getcwd()
URL = "http://127.0.0.1:11434"
res = {"settings": SETTINGS, "started": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}


def sh(cmd, timeout=3600):
    print("+", cmd, flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    tail = (r.stdout + r.stderr)[-1500:]
    print(tail, flush=True)
    return r.returncode, tail


def serve(parallel):
    sh("apt-get -qq update && apt-get -qq install -y zstd", timeout=600)     # the installer unpacks with zstd
    sh("curl -fsSL https://ollama.com/install.sh | sh", timeout=900)
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


def wait_for_go():
    """The world commit to advance: the first on the world branch whose LOCK gives this run the go."""
    end = time.time() + SETTINGS["wait"] * 60
    while time.time() < end:
        code, _ = sh("cd /tmp/botciv && git fetch -q --depth 1 origin world", timeout=300)
        if code == 0:
            r = subprocess.run("cd /tmp/botciv && git show FETCH_HEAD:world/LOCK", shell=True,
                               capture_output=True, text=True)
            try:
                lock = json.loads(r.stdout)
            except ValueError:
                lock = {}
            if lock.get("run") == SETTINGS["run"] and lock.get("go"):
                return subprocess.run("cd /tmp/botciv && git rev-parse FETCH_HEAD", shell=True,
                                      capture_output=True, text=True).stdout.strip()
        time.sleep(30)
    return None


def main():
    t0 = time.time()
    res["gpu"] = sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")[1].strip()
    sh(f"git clone -q --single-branch --branch main {REPO} /tmp/botciv && cd /tmp/botciv && git checkout -q {SETTINGS['code']}")
    if not serve(SETTINGS["parallel"]):
        res["error"] = "the model server did not start"
        return
    t = time.time()
    code, tail = sh(f"ollama pull {SETTINGS['model']}", timeout=1800)
    if code:
        res["error"] = "the model could not be pulled: " + tail[-200:]
        return
    res["pull_seconds"] = round(time.time() - t)
    res["ready_minutes"] = round((time.time() - t0) / 60, 1)
    extra = []
    sh("mkdir -p /tmp/run/world")
    if SETTINGS.get("branch", "world") == "world":
        # the living world: the Actions runner hands it over through world/LOCK
        t = time.time()
        sha = wait_for_go()
        res["waited_for_go_minutes"] = round((time.time() - t) / 60, 1)
        if not sha:
            res["error"] = "the world was never handed over"
            return
    else:
        # a world only this notebook advances: the commit to go on from, or a new world
        sha = SETTINGS.get("sha", "")
        if sha:
            sh(f"cd /tmp/botciv && git fetch -q origin {SETTINGS['branch']}")
        else:
            extra = ["--new"] + (["--config", SETTINGS["config"]] if SETTINGS.get("config") else [])
    res["world_from"] = sha or "new"
    if sha:
        sh(f"cd /tmp/botciv && git archive {sha} world | tar -x -C /tmp/run")
    sys.path.insert(0, "/tmp/botciv")
    os.chdir("/tmp/botciv")
    from botciv import run as runner
    try:
        state = json.load(open("/tmp/run/world/state.json"))
    except OSError:
        state = {}
    res["tick_from"] = state.get("tick", 0)
    t = time.time()
    try:
        runner.main(["--dir", "/tmp/run/world", "--minutes", str(SETTINGS["minutes"]), "--max-calls", "1000000",
                     "--models", "ollama:" + SETTINGS["model"], "--parallel", str(SETTINGS["parallel"])] + extra)
    finally:
        res["run_minutes"] = round((time.time() - t) / 60, 1)
        state = json.load(open("/tmp/run/world/state.json"))
        res["tick_to"] = state.get("tick")
        res["ticks_per_day"] = state.get("cfg", {}).get("world", {}).get("ticks_per_day", 12)
        res["population"] = sum(1 for a in state.get("agents", {}).values() if a.get("alive"))
        sh("rm -rf /tmp/run/world/prompts && tar -czf " + os.path.join(OUT, "world.tar.gz") + " -C /tmp/run world")
        try:
            res["last_run"] = open("/tmp/run/world/last_run.md").read()[:3000]
        except OSError:
            pass


def finish():
    res["total_minutes"] = round((time.time() - T0) / 60, 1)
    json.dump(res, open(os.path.join(OUT, "world_results.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "last_run"}, indent=1), flush=True)


if __name__ == "__main__":
    T0 = time.time()
    try:
        main()
    except Exception as ex:             # whatever went wrong, leave a result that says so
        res["error"] = f"{type(ex).__name__}: {ex}"
        res["trace"] = traceback.format_exc()[-1500:]
    finally:
        sh("tail -c 1500 /tmp/ollama.log")
        finish()
