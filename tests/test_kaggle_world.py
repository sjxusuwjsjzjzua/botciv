"""The world advanced on a Kaggle GPU (2026-09-30): the gateway speaks to a model served by Ollama
without any key, and the Actions world run waits on a lock taken elsewhere, keeps a piece that
finished while the lock was taken, and takes the world the lock holder brings back."""
import http.server
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

from botciv import gateway as G
from tools import advance


class Ollama(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Ollama.seen.append((self.path, body, dict(self.headers)))
        out = json.dumps({"model": body["model"], "message": {"role": "assistant", "content": '{"thought": "rest"}'},
                          "prompt_eval_count": 321, "eval_count": 12}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class OllamaGateway(unittest.TestCase):
    def test_plain_schema(self):
        s = {"type": "OBJECT", "propertyOrdering": ["a"], "properties": {
            "a": {"type": "ARRAY", "items": {"type": "STRING", "enum": ["X"]}}}, "required": ["a"]}
        self.assertEqual(G.plain_schema(s), {"type": "object", "properties": {
            "a": {"type": "array", "items": {"type": "string", "enum": ["X"]}}}, "required": ["a"]})

    def test_asks_the_local_server_without_a_key(self):
        srv = http.server.HTTPServer(("127.0.0.1", 0), Ollama)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        env = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY", "GROQ_API_KEY")}
        env["OLLAMA_URL"] = f"http://127.0.0.1:{srv.server_port}"
        try:
            with mock.patch.dict(os.environ, env, clear=True):
                gw = G.Gateway(["ollama:gemma4:26b"])
                out, meta = gw.generate("Who are you?", {"type": "OBJECT", "properties": {"thought": {"type": "STRING"}}})
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual(out, {"thought": "rest"})
        self.assertEqual((meta["model"], meta["in"], meta["out"]), ("ollama:gemma4:26b", 321, 12))
        path, body, headers = Ollama.seen[-1]
        self.assertEqual(path, "/api/chat")
        self.assertEqual(body["model"], "gemma4:26b")
        self.assertEqual(body["format"]["type"], "object")
        self.assertFalse(any(k.lower() in ("x-goog-api-key", "authorization") for k in headers))

    def test_the_api_still_needs_its_key(self):
        env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeError):
                G.Gateway(["ollama:gemma4:26b", "gemini-2.5-flash-lite"])


class NotebookScripts(unittest.TestCase):
    def test_settings_fill_and_compile(self):
        from tools.kaggle_run import fill_settings
        here = os.path.join(os.path.dirname(__file__), "..", "tools")
        for name in ("kaggle_trial.py", "kaggle_world_kernel.py", "kaggle_sweep_kernel.py"):
            src = open(os.path.join(here, name)).read()
            out = fill_settings(src, {"code": "abc", "sizes": [1, 2], "minutes": 3})
            compile(out, name, "exec")
            self.assertIn('SETTINGS = {"code": "abc", "sizes": [1, 2], "minutes": 3}', out)


def sh(cwd, *cmd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


class Handover(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.origin = os.path.join(t, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "world", self.origin], check=True)
        self.a, self.b = os.path.join(t, "a"), os.path.join(t, "b")
        seed = os.path.join(t, "seed")
        os.makedirs(os.path.join(seed, "world"))
        sh(seed, "git", "init", "-q", "-b", "world")
        self.who(seed)
        self.write(seed, "state.json", "0")
        sh(seed, "git", "add", "-A")
        sh(seed, "git", "commit", "-qm", "start")
        sh(seed, "git", "push", "-q", self.origin, "world")
        for d in (self.a, self.b):
            subprocess.run(["git", "clone", "-q", "-b", "world", self.origin, d], check=True)
            self.who(d)

    def tearDown(self):
        self.tmp.cleanup()

    def who(self, d):
        sh(d, "git", "config", "user.name", "t")
        sh(d, "git", "config", "user.email", "t@example.com")
        sh(d, "git", "config", "commit.gpgsign", "false")

    def write(self, d, name, text):
        with open(os.path.join(d, "world", name), "w") as f:
            f.write(text)

    def commit_push(self, d, msg):
        sh(d, "git", "add", "-A")
        sh(d, "git", "commit", "-qm", msg)
        sh(d, "git", "push", "-q", "origin", "HEAD:world")

    def test_a_piece_finished_under_a_new_lock_is_kept(self):
        self.write(self.b, "LOCK", json.dumps({"by": "kaggle", "until": time.time() + 600}))
        self.commit_push(self.b, "lock")
        self.write(self.a, "state.json", "1")             # the Actions run's piece
        self.assertTrue(advance.commit_and_push(self.a))
        sh(self.b, "git", "pull", "-q", "origin", "world")
        with open(os.path.join(self.b, "world", "state.json")) as f:
            self.assertEqual(f.read(), "1")
        self.assertTrue(advance.locked(os.path.join(self.a, "world")))

    def test_a_real_fork_is_refused(self):
        self.write(self.b, "state.json", "2")
        self.commit_push(self.b, "someone else advanced it")
        self.write(self.a, "state.json", "1")
        with mock.patch.object(advance.time, "sleep"):
            self.assertFalse(advance.commit_and_push(self.a))

    def test_the_waiting_run_takes_the_lock_and_then_the_world(self):
        self.write(self.b, "LOCK", json.dumps({"by": "kaggle", "until": time.time() + 600}))
        self.commit_push(self.b, "lock")
        advance.take_lock_news(self.a)
        self.assertTrue(advance.locked(os.path.join(self.a, "world")))
        os.remove(os.path.join(self.b, "world", "LOCK"))
        self.write(self.b, "state.json", "9")
        self.commit_push(self.b, "the world, advanced elsewhere")
        advance.take_lock_news(self.a)
        self.assertFalse(advance.locked(os.path.join(self.a, "world")))
        with open(os.path.join(self.a, "world", "state.json")) as f:
            self.assertEqual(f.read(), "9")
        self.assertFalse(advance.someone_else_pushed(self.a))

    def test_a_waiting_run_says_it_has_stopped(self):
        self.write(self.b, "LOCK", json.dumps({"by": "kaggle", "run": "r1", "until": time.time() + 600}))
        self.commit_push(self.b, "lock")
        advance.take_lock_news(self.a)
        self.assertTrue(advance.acknowledge_lock(self.a))
        self.assertFalse(advance.acknowledge_lock(self.a))        # once is enough
        sh(self.b, "git", "pull", "-q", "origin", "world")
        with open(os.path.join(self.b, "world", "LOCK")) as f:
            self.assertTrue(json.load(f)["ack"])

    def test_an_unlocked_run_does_not_pull_others_work(self):
        self.write(self.b, "state.json", "2")
        self.commit_push(self.b, "someone else advanced it")
        advance.take_lock_news(self.a)
        self.assertTrue(advance.someone_else_pushed(self.a))


if __name__ == "__main__":
    unittest.main()


class SecondWorld(unittest.TestCase):
    def test_budget_spreads_the_week(self):
        from tools import kaggle_world2 as K2
        now = 10 * 86400
        self.assertEqual(K2.room([], now, 3.8, 27), 3.8 * 60 - K2.SETUP)
        self.assertLess(K2.room([[now - 3600, 200]], now, 3.8, 27), 30)          # today's hours are spent
        self.assertGreater(K2.room([[now - 90000, 228]], now, 3.8, 27), 200)     # yesterday's are not today's
        week = [[now - d * 86400 - 3600, 228] for d in range(1, 7)] + [[now - 90000, 228]]
        self.assertLess(K2.room(week, now, 3.8, 27), 30)                         # but the week's add up

    def test_begin_then_go_on(self):
        from tools import kaggle_world2 as K2
        import tarfile
        with tempfile.TemporaryDirectory() as t:
            origin = os.path.join(t, "o.git")
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
            wt = os.path.join(t, "wb")
            subprocess.run(["git", "init", "-q", "-b", "world2", wt], check=True)
            for k, v in (("user.name", "t"), ("user.email", "t@e"), ("commit.gpgsign", "false")):
                sh(wt, "git", "config", k, v)
            sh(wt, "git", "remote", "add", "origin", origin)
            out = os.path.join(t, "out")
            seen = []

            clock = [time.time()]

            def fake(a, user, slug, script, settings, hours, tick=[0]):
                seen.append(settings)
                clock[0] += (settings["minutes"] + 10) * 60
                tick[0] += 50
                d = os.path.join(t, "nb", "world")
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, "state.json"), "w") as f:
                    json.dump({"tick": tick[0]}, f)
                with open(os.path.join(d, "last_run.md"), "w") as f:
                    f.write(f"## botciv: tick {tick[0]}\n")
                os.makedirs(out, exist_ok=True)
                with open(os.path.join(out, "world_results.json"), "w") as f:
                    json.dump({"tick_from": tick[0] - 50, "tick_to": tick[0]}, f)
                with tarfile.open(os.path.join(out, "world.tar.gz"), "w:gz") as tf:
                    tf.add(d, arcname="world")
                return "complete"
            with mock.patch.object(K2, "push_and_collect", fake), mock.patch.object(K2, "credentials", lambda u: "me"), \
                    mock.patch.object(K2.time, "time", lambda: clock[0]):
                self.assertEqual(K2.main(["--worktree", wt, "--out", out, "--minutes", "225"]), 0)
                self.assertEqual(seen[0]["sha"], "")
                self.assertEqual(seen[0]["config"], "configs/world2.toml")
                self.assertEqual(seen[0]["branch"], "world2")
                # the next piece goes on from the pushed head, and today's hours are spent
                self.assertEqual(K2.main(["--worktree", wt, "--out", out, "--minutes", "225"]), 0)
                self.assertEqual(len(seen), 1)
                with open(os.path.join(wt, "world", "kaggle_usage.json")) as f:
                    runs = json.load(f)["runs"]
                runs[0][0] -= 2 * 86400
                with open(os.path.join(wt, "world", "kaggle_usage.json"), "w") as f:
                    json.dump({"runs": runs}, f)
                sh(wt, "git", "commit", "-qam", "a day later")
                sh(wt, "git", "push", "-q", "origin", "HEAD:world2")
                self.assertEqual(K2.main(["--worktree", wt, "--out", out, "--minutes", "225"]), 0)
                self.assertEqual(len(seen), 2)
                self.assertTrue(seen[1]["sha"])
                self.assertEqual(seen[1]["config"], "")
            log = sh(wt, "git", "log", "--format=%s", "origin/world2")
            self.assertIn("botciv: tick 100 (on a Kaggle GPU)", log)
