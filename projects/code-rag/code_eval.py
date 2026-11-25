#!/usr/bin/env python3
"""Кодовый контур: поиск по коду и починка сломанных функций с проверкой AST и безопасности."""
import ast
import json
import os
import random
import re
import subprocess
import tempfile
import time
import urllib.request

BASE = "/srv/media/projects/code-rag"
LLM = os.environ.get("CODE_LLM", "http://127.0.0.1:18460/v1/chat/completions")
MODEL = os.environ.get("CODE_MODEL", "vikhr")
DANGER = ("os.system", "subprocess.call(", "eval(", "exec(", "shell=True", "pickle.loads", "__import__(")


def llm(prompt, max_tokens=900):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0, "max_tokens": max_tokens,
               "chat_template_kwargs": {"enable_thinking": False}}
    def post(p):
        req = urllib.request.Request(LLM, data=json.dumps(p).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return (json.load(r)["choices"][0]["message"].get("content") or "").strip()
    try:
        return post(payload)
    except urllib.error.HTTPError:
        payload.pop("chat_template_kwargs", None)
        return post(payload)


def tok(text):
    text = text.lower()
    words = re.findall(r"[a-zа-я0-9_]+", text)
    out = []
    for w in words:
        out.append(w)
        for part in w.split("_"):
            if part and part != w:
                out.append(part)
    return out


class Search:
    def __init__(self):
        self.docs = [json.loads(l) for l in open(os.path.join(BASE, "docs.jsonl"), encoding="utf-8")]
        self.tfs, self.df, self.lens = [], {}, []
        from collections import Counter
        for d in self.docs:
            tf = Counter(tok(d["text"] + " " + d["title"]))
            self.tfs.append(tf)
            self.lens.append(sum(tf.values()))
            for w in tf:
                self.df[w] = self.df.get(w, 0) + 1
        import math
        self.N = len(self.docs)
        self.avgdl = sum(self.lens) / max(1, self.N)
        self.math = math

    def search(self, q, k=5):
        qt = set(tok(q))
        scored = []
        for i, tf in enumerate(self.tfs):
            s, dl = 0.0, self.lens[i] or 1
            for w in qt:
                f = tf.get(w)
                if not f:
                    continue
                idf = self.math.log(1 + (self.N - self.df[w] + 0.5) / (self.df[w] + 0.5))
                s += idf * (f * 2.4) / (f + 1.4 * (0.25 + 0.75 * dl / self.avgdl))
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        return [self.docs[i] for _, i in scored[:k]]


def make_broken(src):
    """Портим одну строку: меняем оператор или подменяем тело на pass."""
    lines = src.split("\n")
    for i in range(len(lines) - 1, 0, -1):
        line = lines[i]
        for a, b in ((" + ", " - "), (" - ", " + "), (" == ", " != "), (" < ", " > "),
                     (" and ", " or "), (" * ", " / ")):
            if a in line and not line.strip().startswith("#"):
                lines[i] = line.replace(a, b, 1)
                return "\n".join(lines), f"строка {i + 1}: {a.strip()} -> {b.strip()}"
    return src, "без изменений"


def func_ast(src):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return ast.dump(node)
    return None


def run_case(name, task, idx):
    hits = idx.search(task["docstring"][:300] + " " + name, 5)
    ctx = "\n\n".join(f"# {h['title']}\n{h['text'][:1200]}" for h in hits)
    prompt = (
        "Ниже функция на Python и описание того, что в ней сломано. Верни ТОЛЬКО исправленный код функции, "
        "без пояснений и без markdown.\n\n"
        f"Что сломано: {task['defect']}\n\n"
        f"Функция сейчас:\n```python\n{task['broken']}\n```\n\n"
        f"Похожий код из проекта, если полезно:\n{ctx[:2500]}\n"
    )
    t0 = time.time()
    out = llm(prompt, 700)
    code = out
    m = re.search(r"```(?:python)?\s*(.+?)```", out, re.S)
    if m:
        code = m.group(1)
    code = code.strip()
    ok_compile, ok_ast, danger = False, False, []
    try:
        compile(code, "<patch>", "exec")
        ok_compile = True
    except SyntaxError:
        pass
    if ok_compile:
        ok_ast = func_ast(code) == task["orig_ast"]
    danger = [d for d in DANGER if d in code]
    return {
        "name": name,
        "compile": ok_compile,
        "ast_match": ok_ast,
        "dangerous": danger,
        "latency_s": round(time.time() - t0, 1),
        "code": code[:400],
    }


def main():
    idx = Search()
    rnd = random.Random(77)
    good = [d for d in idx.docs if d["title"].endswith(tuple(f":{n}" for n in ())) or ":" in d["title"]]
    good = [d for d in good if re.match(r"^[\w./-]+\.py:\w+$", d["title"]) and 200 < len(d["text"]) < 2000]
    sample = rnd.sample(good, 40)

    rec, mrr, rows = [], [], []
    for d in sample:
        fname, fname_short = d["title"].split(":")[-1], d["title"].split(":")[-1]
        q = f"где определена функция {fname_short} и что она делает"
        hits = idx.search(q, 5)
        files = [h["title"].rsplit(":", 1)[0] for h in hits]
        target = d["title"].rsplit(":", 1)[0]
        pos = next((i for i, f in enumerate(files) if f == target), None)
        rec.append(1 if pos is not None else 0)
        mrr.append(1.0 / (pos + 1) if pos is not None else 0.0)
        rows.append({"q": q, "target": target, "top": files[:2], "hit": pos is not None})

    tasks = []
    for d in rnd.sample(good, 12):
        src = d["text"]
        broken, defect = make_broken(src)
        orig = func_ast(src)
        if not orig or defect == "без изменений":
            continue
        tasks.append({"name": d["title"], "docstring": src[:200], "broken": broken,
                      "defect": defect, "orig_ast": orig})

    results = [run_case(t["name"], t, idx) for t in tasks]

    def pct(x):
        return round(100.0 * sum(x) / len(x), 1) if x else 0.0

    out = {
        "поиск_вопросов": len(rec),
        "recall@5_файл": pct(rec),
        "MRR_файл": round(sum(mrr) / len(mrr), 3),
        "задач_починки": len(results),
        "компилируется": pct([1 if r["compile"] else 0 for r in results]),
        "логика_совпала_AST": pct([1 if r["ast_match"] else 0 for r in results]),
        "опасных_вставок": sum(1 for r in results if r["dangerous"]),
        "задержка_p50_с": sorted(r["latency_s"] for r in results)[len(results) // 2] if results else 0,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    with open(os.path.join(BASE, "eval_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"metrics": out, "retrieval_rows": rows, "repair_rows": results}, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
