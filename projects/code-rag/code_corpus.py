#!/usr/bin/env python3
"""Корпус кода для ассистента: свои репозитории, разбитые на функции и блоки."""
import hashlib
import json
import os
import re
import sys

OUT = "/srv/media/projects/code-rag"
ROOTS = [
    ("/srv/media/projects/shop-assistant", "py"),
    ("/home/hermes", "py"),
]
SKIP_DIRS = {".git", "__pycache__", "venvs", ".venv", "site-packages", "node_modules", "build", "build129", "build_v100", "cuda-12.9", "acestep15", "llama-new", "llama.cpp", "venvs"}
MAX_FILES = 120


def blocks_of(path, text):
    """Делим файл на функции и классы с сохранением имени."""
    out = []
    lines = text.split("\n")
    cur, name = [], None
    for i, line in enumerate(lines, 1):
        m = re.match(r"^(def|class|async def)\s+(\w+)", line)
        if m:
            if cur and name:
                out.append((name, "\n".join(cur)))
            name = m.group(2)
            cur = [line]
        elif name:
            cur.append(line)
    if cur and name:
        out.append((name, "\n".join(cur)))
    if not out:
        out.append((os.path.basename(path), text))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    docs = []
    for root, _ext in ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if len(docs) > 4000:
                break
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    text = open(path, encoding="utf-8").read()
                except Exception:
                    continue
                if len(text) > 400_000:
                    continue
                rel = path.replace(root, "").lstrip("/")
                for name, body in blocks_of(path, text):
                    if len(body) < 80:
                        continue
                    docs.append({
                        "id": hashlib.sha1(f"{path}:{name}:{len(body)}".encode()).hexdigest()[:12],
                        "kind": "code",
                        "title": f"{rel}:{name}",
                        "url": path,
                        "text": body[:2600],
                    })
                    if len(docs) >= 4000:
                        break
    with open(os.path.join(OUT, "docs.jsonl"), "w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    files = len({d["url"] for d in docs})
    print("блоков кода:", len(docs), "| файлов:", files)


if __name__ == "__main__":
    main()
