#!/usr/bin/env python3
"""V100-144: Inkling 2 Mini - pass@1 на полных 40 задачах MBPP для каждого reasoning_effort."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

BIN = "/home/hermes/llama-new/build129/bin/llama-server"
MODEL = "/srv/media/models/inkling/Inkling-2-Mini-UD-Q3_K_XL.gguf"
PORT = 18466
MBPP = "/srv/media/ai-cache/eval/mbpp.jsonl"
N = 40
LEVELS = sys.argv[1:] or ["none", "medium", "high"]


def wait_health(timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3) as r:
                if json.loads(r.read().decode()) == {"status": "ok"}:
                    return True
        except Exception:
            pass
        time.sleep(5)
    return False


def ask(prompt, max_tokens=int(os.environ.get("MAXTOK", "1400"))):
    body = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens, "temperature": 0.0, "stream": False,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", body,
                                 {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.loads(r.read().decode())
    secs = time.time() - t0
    ch = d["choices"][0]["message"]
    txt = ch.get("content") or ""
    usage = d.get("usage", {})
    return txt, secs, usage.get("completion_tokens", 0)


def vram():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout.strip()
    return int(out.split("\n")[0])


def load_tasks():
    tasks = []
    with open(MBPP, encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            if d.get("test_list") and (d.get("prompt") or d.get("text")):
                d["prompt"] = d.get("prompt") or d.get("text")
                tasks.append(d)
            if len(tasks) >= N:
                break
    return tasks


def run_level(level, tasks):
    subprocess.run(["bash", "-lc", "for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader); "
                                    "do sudo -n kill -9 $p 2>/dev/null; done"], check=False)
    time.sleep(3)
    log = open(f"/srv/media/night/v144_{level}_srv.log", "w")
    srv = subprocess.Popen([BIN, "-m", MODEL, "-ngl", "99", "-c", "8192", "--jinja",
                            "--reasoning-effort", level, "--port", str(PORT), "--host", "127.0.0.1"],
                           stdout=log, stderr=log)
    try:
        if not wait_health():
            print(f"{level}: сервер не поднялся")
            return None
        base = vram()
        print(f"== {level}: сервер ok, VRAM {base} МиБ", flush=True)
        rows, passed, toks, secs_all = [], 0, 0, 0.0
        for i, t in enumerate(tasks, 1):
            m = re.search(r"assert\s+(\w+)\(", " ".join(t["test_list"]))
            fname = m.group(1) if m else "solution"
            prompt = (f"Write a Python function named {fname} for this task. Answer with the code "
                      f"only, in one ```python block, no explanations.\n\n{t['prompt']}")
            try:
                txt, secs, tok = ask(prompt)
            except Exception as e:
                rows.append({"i": i, "ok": False, "err": str(e)[:80], "sec": 0, "tok": 0})
                continue
            mm = re.search(r"```(?:python)?\s*(.*?)```", txt, re.S) or re.search(r"```(?:python)?\s*(.+)\Z", txt, re.S)
            code = mm.group(1) if mm else txt
            ok = False
            if code.strip():
                r = subprocess.run([sys.executable, "-c", code + "\n\n" + "\n".join(t["test_list"])],
                                   capture_output=True, text=True, timeout=60)
                ok = r.returncode == 0
            passed += ok
            toks += tok
            secs_all += secs
            rows.append({"i": i, "ok": ok, "sec": round(secs, 1), "tok": tok})
            print(f"{level} {i:2} {'OK ' if ok else 'нет'} {secs:5.1f} с {tok:5} ток", flush=True)
        res = {"level": level, "pass@1": round(passed / len(tasks), 3), "passed": passed,
               "tasks": len(tasks), "tok_s": round(toks / secs_all, 1) if secs_all else 0,
               "vram_mib": base, "rows": rows}
        json.dump(res, open(f"/srv/media/night/v144_{level}_40.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"== {level}: pass@1 {res['pass@1']} ({passed}/{len(tasks)}), {res['tok_s']} tok/s, "
              f"VRAM {base} МиБ", flush=True)
        return res
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=30)
        except Exception:
            srv.kill()
        time.sleep(5)


def main():
    tasks = load_tasks()
    print("задач:", len(tasks), flush=True)
    out = []
    for lvl in LEVELS:
        r = run_level(lvl, tasks)
        if r:
            out.append(r)
    json.dump([{k: v for k, v in r.items() if k != "rows"} for r in out],
              open("/srv/media/night/v144_summary_40.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("готово")


if __name__ == "__main__":
    main()
