#!/usr/bin/env python3
"""Агентный цикл починки: применил - прогнал тесты - прочитал ошибку - поправил, до 4 шагов."""
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request

BASE = "/srv/media/projects/code-real"
REPO = os.path.join(BASE, "packaging")
WORK = os.path.join(BASE, "loop")
PY = "/home/hermes/venvs/vllm/bin/python"
LLM = os.environ.get("CODE_LLM", "http://127.0.0.1:18470/v1/chat/completions")
MODEL = os.environ.get("CODE_MODEL", "deepseek-coder")
MAX_TASKS = 8
MAX_STEPS = 4
DANGER = ("subprocess", "os.system", "eval(", "exec(", "shutil.rmtree", "shell=True")


def sh(cmd, cwd, timeout=300):
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)


def ensure_server():
    """Проверяет, что сервер модели жив, и поднимает его при падении."""
    import socket
    host, port = "127.0.0.1", 18470
    for _ in range(3):
        try:
            with socket.create_connection((host, port), timeout=3):
                return True
        except OSError:
            subprocess.run("sudo -n systemctl restart coderllm", shell=True, capture_output=True)
            time.sleep(12)
    return False


def llm(messages, max_tokens=1800):
    payload = {"model": MODEL, "messages": messages, "temperature": 0,
               "max_tokens": max_tokens, "chat_template_kwargs": {"enable_thinking": False}}
    def post(p):
        req = urllib.request.Request(LLM, data=json.dumps(p).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            return (json.load(r)["choices"][0]["message"].get("content") or "").strip()
    try:
        return post(payload)
    except urllib.error.HTTPError:
        payload.pop("chat_template_kwargs", None)
        return post(payload)


def clean_code(text):
    m = re.search(r"```(?:python)?\s*(.+?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def candidates():
    out = sh("git log --format='%H|%s' -n 400 --name-only", REPO).stdout
    cur, rows = None, []
    for line in out.split("\n"):
        if "|" in line and len(line.split("|")[0]) == 40:
            if cur:
                rows.append(cur)
            h, s = line.split("|", 1)
            cur = {"sha": h, "s": s, "f": []}
        elif line.strip() and cur:
            cur["f"].append(line.strip())
    if cur:
        rows.append(cur)
    picked = []
    for r in rows:
        src = [f for f in r["f"] if f.startswith("src/") and f.endswith(".py")]
        tst = [f for f in r["f"] if f.startswith("tests/") and f.endswith(".py")]
        if len(src) == 1 and tst:
            picked.append({**r, "src": src[0], "tests": tst})
    return picked


def main():
    os.makedirs(WORK, exist_ok=True)
    results = []
    for i, c in enumerate(candidates()):
        if len(results) >= MAX_TASKS:
            break
        ensure_server()
        d = os.path.join(WORK, f"l{i}")
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(REPO, d)
        if sh(f"git checkout {c['sha']} -- {' '.join(c['tests'])}", d).returncode:
            shutil.rmtree(d, ignore_errors=True)
            continue
        if sh(f"git checkout {c['sha']}^ -- {c['src']}", d).returncode:
            shutil.rmtree(d, ignore_errors=True)
            continue
        before = sh(f"PYTHONPATH=src {PY} -m pytest {' '.join(c['tests'])} -q", d)
        blob = before.stdout + before.stderr
        if before.returncode == 0 or "FAILED tests/" not in blob:
            shutil.rmtree(d, ignore_errors=True)
            continue
        if "ImportError" in blob or "ERROR collecting" in blob or "error during collection" in blob:
            shutil.rmtree(d, ignore_errors=True)
            continue

        path = os.path.join(d, c["src"])
        code = open(path, encoding="utf-8").read()
        messages = [{"role": "user", "content": (
            "Исправь ошибку в коде так, чтобы тест проходил. Верни только содержимое файла целиком.\n\n"
            f"Вывод pytest:\n{blob[-2500:]}\n\nФайл {c['src']}:\n{code[:9000]}")}]
        t0 = time.time()
        fixed, steps, danger = False, 0, []
        for step in range(1, MAX_STEPS + 1):
            steps = step
            try:
                ans = llm(messages, 1800)
            except Exception as e:
                ensure_server()
                messages.append({"role": "user", "content": f"ошибка модели: {e}"})
                continue
            patch = clean_code(ans)
            danger += [w for w in DANGER if w in patch]
            try:
                compile(patch, "<p>", "exec")
            except SyntaxError as e:
                messages.append({"role": "assistant", "content": ans[:1500]})
                messages.append({"role": "user", "content": f"Не компилируется: {e}. Верни исправленный файл целиком."})
                continue
            open(path, "w", encoding="utf-8").write(patch)
            after = sh(f"PYTHONPATH=src {PY} -m pytest {' '.join(c['tests'])} -q", d)
            if after.returncode == 0:
                fixed = True
                break
            out = (after.stdout + after.stderr)[-1800:]
            messages.append({"role": "assistant", "content": ans[:1200]})
            messages.append({"role": "user", "content":
                             f"Тест всё ещё падает. Вот вывод:\n{out}\n\nИсправь и верни файл целиком."})
        results.append({"sha": c["sha"][:8], "subject": c["s"][:60], "fixed": fixed,
                        "steps": steps, "dangerous": len(set(danger)), "sec": round(time.time() - t0, 1)})
        print(f"{results[-1]['sha']} {'починено' if fixed else 'нет':9} шагов {steps} {c['s'][:50]}", flush=True)
        shutil.rmtree(d, ignore_errors=True)

    fixed = sum(1 for r in results if r["fixed"])
    summary = {
        "задач": len(results), "починено": fixed,
        "процент": round(100.0 * fixed / len(results), 1) if results else 0,
        "среднее_шагов": round(sum(r["steps"] for r in results) / max(1, len(results)), 1),
        "опасных_вставок": sum(r["dangerous"] for r in results),
        "среднее_секунд": round(sum(r["sec"] for r in results) / max(1, len(results)), 1),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    json.dump({"summary": summary, "rows": results},
              open(os.path.join(BASE, "loop_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
