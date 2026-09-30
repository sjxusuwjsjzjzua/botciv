"""Push tools/kaggle_trial.py to Kaggle as a private GPU notebook, wait for it, and bring back
what it measured. Runs in GitHub Actions (kaggle-trial.yml).

The Kaggle credential comes from the KAGGLE_SECRET environment variable (the repository secret
KAGGLEAPI): either the contents of a kaggle.json, or a newer API token. It is written only to
the runner's ~/.kaggle and never printed. Nothing on Kaggle can write to this repository.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if check and r.returncode:
        raise SystemExit(f"{' '.join(cmd[:3])} failed: {out[-800:]}")
    return out


def credentials(user_hint):
    secret = (os.environ.get("KAGGLE_SECRET") or "").strip()
    if not secret:
        raise SystemExit("KAGGLE_SECRET is empty: the workflow maps it from the KAGGLEAPI repository secret")
    home = os.path.expanduser("~/.kaggle")
    os.makedirs(home, exist_ok=True)
    user = user_hint.strip()
    try:
        cfg = json.loads(secret)
    except ValueError:
        cfg = None
    if isinstance(cfg, dict) and cfg.get("key"):
        path = os.path.join(home, "kaggle.json")
        with open(path, "w") as f:
            json.dump({"username": cfg.get("username", user), "key": cfg["key"]}, f)
        os.chmod(path, 0o600)
        user = user or cfg.get("username", "")
    else:
        path = os.path.join(home, "access_token")
        with open(path, "w") as f:
            f.write(secret)
        os.chmod(path, 0o600)
        os.environ["KAGGLE_API_TOKEN"] = secret
    if not user:
        m = re.search(r"username:\s*(\S+)", run(["kaggle", "config", "view"], check=False))
        user = m.group(1) if m and m.group(1).lower() != "none" else ""
    if not user:
        out = run(["kaggle", "kernels", "list", "--mine", "--csv"], check=False)
        m = re.search(r"^([\w-]+)/[\w-]+,", out, re.M)
        user = m.group(1) if m else ""
    if not user:
        raise SystemExit("could not tell the Kaggle username from the token: run again with the kaggle_user input")
    return user


def push_and_collect(a, user, slug, src_file, settings, hours):
    """Push a script as a private GPU notebook with SETTINGS replaced, wait, download its output."""
    d = os.path.join(os.getcwd(), "kaggle-kernel")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    src = open(os.path.join(HERE, src_file)).read()
    src = re.sub(r"^SETTINGS = .*$", "SETTINGS = " + json.dumps(settings), src, count=1, flags=re.M)
    with open(os.path.join(d, "main.py"), "w") as f:
        f.write(src)
    meta = {"id": f"{user}/{slug}", "title": slug, "code_file": "main.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
            "machine_shape": a.accelerator, "dataset_sources": [], "competition_sources": [],
            "kernel_sources": [], "model_sources": []}
    with open(os.path.join(d, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("pushing", meta["id"], "on", a.accelerator, flush=True)
    print(run(["kaggle", "kernels", "push", "-p", d, "--accelerator", a.accelerator,
               "-t", str(int(hours * 3600))])[-600:], flush=True)
    ref = f"{user}/{slug}"
    end = time.time() + a.wait * 60
    status = ""
    time.sleep(60)
    while time.time() < end:
        status = run(["kaggle", "kernels", "status", ref], check=False)
        print(time.strftime("%H:%M:%S"), status[-200:], flush=True)
        if re.search(r"complete|error|cancel", status, re.I):
            break
        time.sleep(60)
    os.makedirs(a.out, exist_ok=True)
    print(run(["kaggle", "kernels", "output", ref, "-p", a.out, "-o"], check=False)[-600:], flush=True)
    return status


def sweep(a):
    """How big a world one notebook serves best (tools/kaggle_sweep_kernel.py)."""
    user = credentials(a.user)
    code = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    settings = {"code": code, "model": a.models.split(",")[0].strip(), "slots": [4, 8, 12, 16, 24],
                "slot_minutes": 4, "sizes": [16, 32, 64, 96], "size_minutes": 12}
    status = push_and_collect(a, user, "botciv-sweep", "kaggle_sweep_kernel.py", settings, 2.5)
    path = os.path.join(a.out, "sweep_results.json")
    if not os.path.exists(path):
        print("no results; status:", status)
        return 1
    res = json.load(open(path))
    lines = ["## Kaggle sweep: how big a world one GPU notebook serves", "", f"status: {status[-120:]}", "",
             f"gpu `{res.get('gpu')}`, prompt {res.get('prompt_chars')} characters, best slots {res.get('best_slots')}, "
             f"{res.get('total_minutes')} minutes", "", "| slots | decisions/h | mean s | GPU mid-run | errors |",
             "|---|---|---|---|---|"]
    for r in res.get("phase_a", []):
        lines.append(f"| {r.get('slots')} | {r.get('per_hour', '-')} | {r.get('mean_s', '-')} | "
                     f"{r.get('gpu_mid', r.get('error', ''))} | {len(r.get('errors') or [])} |")
    lines += ["", "| people | decisions/h | world days/h | decisions per person-hour | stop |", "|---|---|---|---|---|"]
    for r in res.get("phase_b", []):
        lines.append(f"| {r.get('people')} | {r.get('decisions_per_hour', '-')} | {r.get('days_per_hour', '-')} | "
                     f"{r.get('decisions_per_person_hour', '-')} | {r.get('stop', '')} |")
    if res.get("error"):
        lines += ["", f"error: `{res['error']}`", "```", res.get("trace", ""), "```"]
    text = "\n".join(lines)
    print(text)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a") as f:
            f.write(text + "\n")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="")
    ap.add_argument("--models", default="gemma4:26b,gemma4:26b-a4b,gemma4:12b,gemma4")
    ap.add_argument("--minutes", type=int, default=25)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--accelerator", default="NvidiaTeslaT4")
    ap.add_argument("--wait", type=int, default=120, help="minutes to wait for the notebook")
    ap.add_argument("--out", default="kaggle-out")
    ap.add_argument("--script", default="trial", help="trial (kaggle_trial.py) or sweep (kaggle_sweep_kernel.py)")
    a = ap.parse_args()
    if a.script == "sweep":
        return sweep(a)
    user = credentials(a.user)
    slug = "botciv-trial"
    d = os.path.join(os.getcwd(), "kaggle-kernel")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    src = open(os.path.join(HERE, "kaggle_trial.py")).read()
    settings = {"models": [m.strip() for m in a.models.split(",") if m.strip()], "minutes": a.minutes,
                "parallel": a.parallel}
    src = re.sub(r"^SETTINGS = .*$", "SETTINGS = " + json.dumps(settings), src, count=1, flags=re.M)
    with open(os.path.join(d, "trial.py"), "w") as f:
        f.write(src)
    meta = {"id": f"{user}/{slug}", "title": slug, "code_file": "trial.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
            "machine_shape": a.accelerator, "dataset_sources": [], "competition_sources": [],
            "kernel_sources": [], "model_sources": []}
    with open(os.path.join(d, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("pushing", meta["id"], "on", a.accelerator, flush=True)
    print(run(["kaggle", "kernels", "push", "-p", d, "--accelerator", a.accelerator,
               "-t", str((a.minutes + 60) * 60)])[-600:], flush=True)
    ref = f"{user}/{slug}"
    end = time.time() + a.wait * 60
    status = ""
    time.sleep(60)
    while time.time() < end:
        status = run(["kaggle", "kernels", "status", ref], check=False)
        print(time.strftime("%H:%M:%S"), status[-200:], flush=True)
        if re.search(r"complete|error|cancel", status, re.I):
            break
        time.sleep(60)
    os.makedirs(a.out, exist_ok=True)
    print(run(["kaggle", "kernels", "output", ref, "-p", a.out, "-o"], check=False)[-600:], flush=True)
    path = os.path.join(a.out, "trial_results.json")
    if not os.path.exists(path):
        log = [f for f in os.listdir(a.out) if f.endswith(".log")]
        tail = open(os.path.join(a.out, log[0])).read()[-3000:] if log else "(no log)"
        print("no results; the notebook's log ends:\n" + tail)
        return 1
    res = json.load(open(path))
    lines = ["## Kaggle GPU trial", "", f"status: {status[-120:]}", ""]
    for k in ("gpu", "model", "pull_seconds", "first_answer_seconds", "prompts", "prompt_chars", "calls", "answered",
              "valid", "minutes", "per_hour", "mean_seconds", "mean_tokens_in", "mean_tokens_out", "verbs",
              "think_field", "error", "pull_failed", "errors", "total_minutes"):
        if k in res:
            lines.append(f"- **{k}**: `{json.dumps(res[k])[:400]}`")
    for s in res.get("samples", [])[:2]:
        lines.append("\n```json\n" + json.dumps({k: s.get(k) for k in ("thought", "action", "plan")}, indent=1)[:1200] + "\n```")
    text = "\n".join(lines)
    print(text)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
