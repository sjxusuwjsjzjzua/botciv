"""Append-only JSONL logs. One line per event; decisions go to their own file."""
import gzip
import json
import os


class Log:
    def __init__(self, path, mode="a"):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        opener = gzip.open if path.endswith(".gz") else open
        self.f = opener(path, mode + "t", encoding="utf-8")
        self.recent = []

    def write(self, obj):
        self.f.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n")
        if obj.get("kind") != "frame":
            self.recent.append(obj)
            if len(self.recent) > 5000:
                self.recent = self.recent[-2500:]

    def close(self):
        self.f.close()


class NullLog:
    def __init__(self):
        self.recent = []

    def write(self, obj, *_):
        if obj.get("kind") == "frame":
            return
        self.recent.append(obj)
        if len(self.recent) > 5000:
            self.recent = self.recent[-2500:]

    def close(self):
        pass


def read(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)
