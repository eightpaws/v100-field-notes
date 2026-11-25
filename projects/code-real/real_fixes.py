#!/usr/bin/env python3
"""V100-137: задачи из реальных правок. Тест из коммита, исходник до правки, приёмка - pytest."""
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request

BASE = "/srv/media/projects/code-real"
REPO = os.path.join(BASE, "packaging")
WORK = os.path.join(BASE, "tasks")
PY = "/home/hermes/venvs/vllm/bin/python"
LLM = os.environ.get("CODE_LLM", "http://127.0.0.1:18460/v1/chat/completions")
MODEL = os.environ.get("CODE_MODEL", "vikhr")
MAX_TASKS = 10


def sh(cmd, cwd, timeout=180):
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)


def llm(prompt, max_tokens=1600):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0, "max_tokens": max_tokens,
               "chat_template_kwargs": {"enable_thinking": False}}

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


def candidates():
    out = sh("git log --format='%H|%s' -n 400 --name-only", REPO).stdout
    entries, cur = [], None
    for line in out.split("\n"):
        if "|" in line and len(line.split("|")[0]) == 40:
            if cur:
                entries.append(cur)
            h, s = line.split("|", 1)
            cur = {"sha": h, "subject": s, "files": []}
        elif line.strip() and cur:
            cur["files"].append(line.strip())
    if cur:
        entries.append(cur)
    picked = []
    for e in entries:
        e["tests_existed"] = False
        src = [f for f in e["files"] if f.startswith("src/") and f.endswith(".py")]
        tst = [f for f in e["files"] if f.startswith("tests/") and f.endswith(".py")]
        if len(src) == 1 and tst:
            picked.append({**e, "src": src, "tests": tst})
    return picked


def main():
    os.makedirs(WORK, exist_ok=True)
    cands = candidates()
    print("коммитов с правкой кода и тестов:", len(cands))
    results = []
    for i, c in enumerate(cands):
        if len(results) >= MAX_TASKS:
            break
        d = os.path.join(WORK, f"t{i}")
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(REPO, d)
        r1 = sh(f"git checkout {c['sha']} -- {chr(32).join(c['tests'])}", d)
        r2 = sh(f"git checkout {c['sha']}^ -- {chr(32).join(c['src'])}", d)
        if r1.returncode or r2.returncode:
            shutil.rmtree(d, ignore_errors=True)
            continue
        before = sh(f"PYTHONPATH=src {PY} -m pytest {' '.join(c['tests'])} -q", d, 300)
        blob = before.stdout + before.stderr
        if before.returncode == 0:
            shutil.rmtree(d, ignore_errors=True)
            continue
        if "FAILED tests/" not in blob:
            shutil.rmtree(d, ignore_errors=True)
            continue
        if ("ImportError" in blob or "ERROR collecting" in blob or "error during collection" in blob
                or "ModuleNotFoundError" in blob or "SyntaxError" in blob):
            shutil.rmtree(d, ignore_errors=True)
            continue
        tail = "\n".join(before.stdout.split("\n")[-14:])
        src_text = ""
        for f in c["src"]:
            p = os.path.join(d, f)
            if os.path.exists(p):
                src_text += f"\n# файл {f}\n" + open(p, encoding="utf-8").read()[:6000]
        prompt = (
            "Ниже исходный код проекта и тест, который падает. Найди причину и исправь код.\n"
            "Верни ТОЛЬКО содержимое исправленного файла целиком, без пояснений и без markdown.\n\n"
            f"Вывод pytest:\n{tail}\n\nКод:\n{src_text[:9000]}\n"
        )
        t0 = time.time()
        try:
            answer = llm(prompt, 1800)
        except Exception as e:
            shutil.rmtree(d, ignore_errors=True)
            results.append({"sha": c["sha"][:8], "subject": c["subject"][:60], "error": str(e)[:80]})
            continue
        code = answer
        m = re.search(r"```(?:python)?\s*(.+?)```", answer, re.S)
        if m:
            code = m.group(1)
        try:
            compile(code, "<patch>", "exec")
            syntax_ok = True
        except SyntaxError:
            syntax_ok = False
        target = os.path.join(d, c["src"][0])
        danger = [w for w in ("subprocess", "os.system", "eval(", "exec(", "shutil.rmtree") if w in code]
        open(target, "w", encoding="utf-8").write(code)
        after = sh(f"PYTHONPATH=src {PY} -m pytest {' '.join(c['tests'])} -q", d, 300)
        _after_tail = " | ".join(after.stdout.splitlines()[-6:])[-300:]
        results.append({
            "sha": c["sha"][:8],
            "subject": c["subject"][:70],
            "fixed": after.returncode == 0,
            "dangerous": danger,
            "syntax_ok": syntax_ok,
            "sec": round(time.time() - t0, 1),
            "fail_tail": tail[-300:],
            "after_tail": _after_tail,
        })
        print(f"{results[-1]['sha']} {'починено' if results[-1]['fixed'] else 'не починено':12} {c['subject'][:56]}", flush=True)
        shutil.rmtree(d, ignore_errors=True)

    rate = round(100.0 * sum(1 for r in results if r.get("fixed")) / len(results), 1) if results else 0
    summary = {
        "задач": len(results),
        "починено": sum(1 for r in results if r.get("fixed")),
        "процент": rate,
        "опасных_вставок": sum(1 for r in results if r.get("dangerous")),
        "синтаксис_валиден": sum(1 for r in results if r.get("syntax_ok")),
        "среднее_секунд": round(sum(r.get("sec", 0) for r in results) / max(1, len(results)), 1),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    json.dump({"summary": summary, "rows": results}, open(os.path.join(BASE, "result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
