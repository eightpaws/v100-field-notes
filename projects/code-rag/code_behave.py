#!/usr/bin/env python3
"""Проверка починки поведением: оригинал против исправленного на одних аргументах."""
import ast
import itertools
import itertools as it
import json
import os
import random
import re
import textwrap

BASE = "/srv/media/projects/code-rag"
SAMPLES = {
    "int": [0, 1, 2, 5, -3, 10],
    "str": ["", "a", "abc", "тест"],
    "list": [[], [1, 2, 3], ["a", "b"], list(range(5))],
    "dict": [{}, {"a": 1}],
    "bool": [True, False],
}


def func_name(src):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    return None


def sig_types(src):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.args.vararg or node.args.kwarg:
                return None
            types = []
            for a in node.args.args:
                if a.arg in ("self", "cls"):
                    return None
                ann = ast.unparse(a.annotation) if a.annotation else ""
                types.append(ann if ann in SAMPLES else "int")
            return types
    return None


def load(src, name):
    ns = {}
    try:
        exec(compile(textwrap.dedent(src), "<m>", "exec"), ns)
    except Exception:
        return None
    return ns.get(name)


def behave(orig_src, new_src):
    name = func_name(orig_src)
    types = sig_types(orig_src)
    if not name or not types or len(types) > 3:
        return None
    fo, fn = load(orig_src, name), load(new_src, name)
    if not fo or not fn:
        return (0, 0)
    pools = [SAMPLES[t] for t in types]
    same = total = 0
    for combo in it.islice(itertools.product(*pools), 24):
        total += 1
        try:
            a = fo(*combo)
        except Exception:
            continue
        try:
            b = fn(*combo)
        except Exception:
            continue
        same += 1 if repr(a) == repr(b) else 0
    return same, total


def main():
    data = json.load(open(os.path.join(BASE, "eval_result.json"), encoding="utf-8"))
    rows = data["repair_rows"]
    print("проверяю поведением:", len(rows), "починок")
    checked = same_total = calls_total = 0
    for r in rows:
        res = behave_orig = None
        src_orig = None
        # оригинал берём из корпуса по имени блока
        for line in open(os.path.join(BASE, "docs.jsonl"), encoding="utf-8"):
            d = json.loads(line)
            if d["title"] == r["name"]:
                src_orig = d["text"]
                break
        if not src_orig:
            print(f"  {r['name']}: оригинал не найден")
            continue
        out = behave(src_orig, r["code"])
        if out is None:
            print(f"  {r['name']}: проверка не применима")
            continue
        checked += 1
        same, total = out
        same_total += same
        calls_total += total
        print(f"  {r['name']}: совпало {same}/{total} вызовов")
    pct = round(100.0 * same_total / calls_total, 1) if calls_total else 0
    data["metrics"]["поведение_совпало_процент_вызовов"] = pct
    data["metrics"]["проверено_поведением"] = checked
    json.dump(data, open(os.path.join(BASE, "eval_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"итого: {checked} функций, совпадение поведения {pct}% вызовов")


if __name__ == "__main__":
    main()
