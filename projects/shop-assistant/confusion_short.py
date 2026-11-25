#!/usr/bin/env python3
"""Устойчивость к похожим товарам: находит ли ассистент именно тот сорт, который спросили."""
import json
import os
import random
import re

BASE = "/srv/media/projects/shop-assistant"
docs = [json.loads(l) for l in open(os.path.join(BASE, "docs.jsonl"), encoding="utf-8")]
products = [d for d in docs if d["kind"] == "product"]


def group_key(name):
    """Первый смысловой блок имени: род/сорт до запятой и уточнений."""
    base = name.split(",")[0].strip().lower()
    base = re.sub(r"\s+(стартер|взрослое|детка|укорененный|укоренённый)\b.*$", "", base)
    return base


groups = {}
for p in products:
    groups.setdefault(group_key(p["title"]), []).append(p)

multi = {k: v for k, v in groups.items() if len(v) >= 3}
print("групп похожих товаров:", len(multi), "| крупнейшая:", max(len(v) for v in multi.values()))

import importlib
retrieve = importlib.import_module("retrieve")
idx = retrieve.Index()

rnd = random.Random(5)
cases = []
for key, items in multi.items():
    pick = rnd.choice(items)
    parts = [x.strip() for x in pick["title"].split(",") if x.strip()]
    short = parts[1] if len(parts) > 1 else parts[0]
    cases.append({"q": f"есть ли {short}?", "gold": pick["id"], "group": key,
                  "n_in_group": len(items)})
rnd.shuffle(cases)
cases = cases[:40]

top1 = top5 = 0
confused = []
for c in cases:
    hits = idx.search(c["q"], 5)
    ids = [d["id"] for d, _ in hits]
    if ids and ids[0] == c["gold"]:
        top1 += 1
    if c["gold"] in ids:
        top5 += 1
    else:
        titles = [d["title"] for d, _ in hits[:2]]
        confused.append({"q": c["q"], "gold_title": next(d["title"] for d in products if d["id"] == c["gold"]),
                         "got": titles})

res = {
    "вопросов": len(cases),
    "top1_процент": round(100.0 * top1 / len(cases), 1),
    "top5_процент": round(100.0 * top5 / len(cases), 1),
    "промахов": len(confused),
}
print(json.dumps(res, ensure_ascii=False, indent=1))
for c in confused[:6]:
    print("  промах:", c["q"][:50], "| ждали:", c["gold_title"][:34], "| выдали:", c["got"][:1])
json.dump({"summary": res, "misses": confused},
          open(os.path.join(BASE, "confusion_short_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
