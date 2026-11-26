#!/usr/bin/env python3
"""Весь пакет в контекст (64k) и правка нескольких файлов сразу.
Приёмка - прогон теста из коммита."""
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request

BASE = "/srv/media/projects/code-real"
REPO = os.path.join(BASE, "packaging")
WORK = os.path.join(BASE, "whole")
PY = "/home/hermes/venvs/vllm/bin/python"
LLM = os.environ.get("CODE_LLM", "http://127.0.0.1:18480/v1/chat/completions")
MODEL = os.environ.get("CODE_MODEL", "qwen2.5-coder-7b")
MAX_TASKS = int(os.environ.get("MAX_TASKS", "6"))
LAST_USAGE = {}
DANGER = ("os.system", "eval(", "exec(", "shell=True", "shutil.rmtree", "subprocess.call(")


def sh(cmd, cwd, timeout=300):
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)


def llm(prompt, max_tokens=2500):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0, "max_tokens": max_tokens,
               "chat_template_kwargs": {"enable_thinking": False}}
    def post(p):
        req = urllib.request.Request(LLM, data=json.dumps(p).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1800) as r:
            d = json.load(r)
            global LAST_USAGE
            LAST_USAGE = d.get("usage", {})
            return (d["choices"][0]["message"].get("content") or "").strip()
    try:
        return post(payload)
    except urllib.error.HTTPError:
        payload.pop("chat_template_kwargs", None)
        return post(payload)


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
        if src and tst:
            picked.append({**r, "src": src, "tests": tst})
    return picked


def parse_files(answer):
    """Достаёт блоки вида === FILE: путь ... === из ответа модели."""
    out = {}
    cur = None
    buf = []
    for line in answer.split("\n"):
        m = re.match(r"^\s*===+\s*FILE:\s*(\S+)", line)
        if m:
            if cur:
                out[cur] = "\n".join(buf)
            cur = m.group(1).strip()
            buf = []
            continue
        if cur is not None:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf)
    return {k: re.sub(r"^```\w*|```$", "", v.strip(), flags=re.M).strip() + "\n" for k, v in out.items()}


def main():
    os.makedirs(WORK, exist_ok=True)
    results = []
    for i, c in enumerate(candidates()):
        if len(results) >= MAX_TASKS:
            break
        d = os.path.join(WORK, f"w{i}")
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(REPO, d)
        if sh(f"git checkout {c['sha']} -- {' '.join(c['tests'])}", d).returncode:
            shutil.rmtree(d, ignore_errors=True)
            continue
        if sh(f"git checkout {c['sha']}^ -- {' '.join(c['src'])}", d).returncode:
            shutil.rmtree(d, ignore_errors=True)
            continue
        before = sh(f"PYTHONPATH=src {PY} -m pytest {' '.join(c['tests'])} -q", d)
        blob = before.stdout + before.stderr
        if before.returncode == 0 or "FAILED tests/" not in blob:
            shutil.rmtree(d, ignore_errors=True)
            continue
        if "ImportError" in blob or "error during collection" in blob:
            shutil.rmtree(d, ignore_errors=True)
            continue

        pkg = ""
        for root, _dirs, files in os.walk(os.path.join(d, "src", "packaging")):
            for fn in sorted(files):
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, d)
                pkg += f"\n=== FILE: {rel}\n" + open(p, encoding="utf-8").read()
        prompt = (
            "Ниже весь пакет проекта и падающий тест. Исправь ошибку.\n"
            "Можно менять несколько файлов. Верни ТОЛЬКО изменённые файлы, каждый в формате:\n"
            "=== FILE: путь/от/корня/репозитория\n<полное содержимое файла>\n"
            "Без пояснений.\n\n"
            f"Вывод pytest:\n{blob[-2000:]}\n\nПакет:{pkg[:80000]}\n"
        )
        t0 = time.time()
        try:
            answer = llm(prompt, 3000)
        except Exception as e:
            results.append({"sha": c["sha"][:8], "s": c["s"][:50], "error": str(e)[:80]})
            shutil.rmtree(d, ignore_errors=True)
            continue
        files = parse_files(answer)
        if not files:
            only = [f for f in c["src"] if f.endswith(".py")]
            if len(only) == 1:
                body = re.sub(r"^```\w*|```$", "", answer.strip(), flags=re.M).strip()
                if body:
                    files = {only[0]: body + chr(10)}
        applied, danger, bad = [], 0, []
        for rel, content in files.items():
            rel = rel.lstrip("/")
            target = os.path.join(d, rel)
            if not os.path.abspath(target).startswith(os.path.abspath(d)) or not rel.endswith(".py"):
                bad.append(rel)
                continue
            danger += sum(1 for w in DANGER if w in content)
            try:
                compile(content, "<p>", "exec")
            except SyntaxError:
                bad.append(rel)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            open(target, "w", encoding="utf-8").write(content)
            applied.append(rel)
        after = sh(f"PYTHONPATH=src {PY} -m pytest {' '.join(c['tests'])} -q", d)
        results.append({
            "sha": c["sha"][:8], "s": c["s"][:60], "fixed": after.returncode == 0,
            "files_applied": applied, "bad_files": bad, "dangerous": danger,
            "sec": round(time.time() - t0, 1), "prompt_tokens": LAST_USAGE.get("prompt_tokens"),
        })
        with open("/srv/media/night/whole_answers.log", "a", encoding="utf-8") as fh:
            fh.write(chr(10) + "===== " + c["sha"][:8] + " =====" + chr(10) + answer[:4000] + chr(10))
        print(f"{results[-1]['sha']} {'ПОЧИНЕНО' if results[-1]['fixed'] else 'нет':9} "
              f"файлов {len(applied)} {c['s'][:44]}", flush=True)
        shutil.rmtree(d, ignore_errors=True)

    fixed = sum(1 for r in results if r.get("fixed"))
    summary = {
        "задач": len(results), "починено": fixed,
        "процент": round(100.0 * fixed / len(results), 1) if results else 0,
        "среднее_файлов": round(sum(len(r.get("files_applied", [])) for r in results) / max(1, len(results)), 1),
        "отклонённых_файлов": sum(len(r.get("bad_files", [])) for r in results),
        "опасных_вставок": sum(r.get("dangerous", 0) for r in results),
        "секунд": round(sum(r.get("sec", 0) for r in results) / max(1, len(results)), 1),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    json.dump({"summary": summary, "rows": results},
              open(os.path.join(BASE, "whole_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
