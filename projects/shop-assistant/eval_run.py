#!/usr/bin/env python3
"""Прогон проверочного набора: recall@5, MRR, верность ответов, честные отказы, задержки."""
import json
import os
import re
import statistics
import sys

from ask import ask
from retrieve import Index

BASE = "/srv/media/projects/shop-assistant"
REFUSAL = ("этого нет", "нет в описании", "не указано", "не указана", "нет данных", "не нашёл",
           "не нашел", "уточните", "напишите в службу", "обратитесь в службу", "нет информации",
           "не содержится", "в описании магазина этого нет")

JUDGE = (
    "Ты проверяющий. Тебе дают вопрос, эталонный факт и ответ консультанта. "
    "Формулировки могут отличаться, оценивай смысл, а не совпадение слов. "
    "Ставь 2, если все факты в ответе есть в эталоне и ничего не выдумано; "
    "1, если ответ верен, но неполон или добавляет верные детали из того же магазина; "
    "0 только если ответ противоречит эталону, выдумывает числа или отказывается отвечать, "
    "хотя ответ в эталоне есть. Ответь строго: ОЦЕНКА: <0|1|2>"
)


def judge(q, ref, answer):
    import urllib.request
    from ask import LLM, MODEL
    prompt = f"Вопрос: {q}\n\nЭталонный факт:\n{ref[:900]}\n\nОтвет консультанта:\n{answer}\n\n{JUDGE}"
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0, "max_tokens": 40,
               "chat_template_kwargs": {"enable_thinking": False}}
    def _post(p):
        body = json.dumps(p).encode()
        req = urllib.request.Request(LLM, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=200) as r2:
            return (json.load(r2)["choices"][0]["message"].get("content") or "")
    try:
        out = _post(payload)
    except urllib.error.HTTPError:
        payload.pop("chat_template_kwargs", None)
        out = _post(payload)
    m = re.search(r"[012]", out)
    return int(m.group(0)) if m else -1


def main():
    idx = Index()
    items = [json.loads(l) for l in open(os.path.join(BASE, "evalset.jsonl"), encoding="utf-8")]
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(items)
    items = items[:limit]

    rec5, rec5p, rr, scores, refusals, lats = [], [], [], [], [], []
    fails = []
    for n, it in enumerate(items, 1):
        hits = idx.search(it["q"], 5)
        ids = [d["id"] for d, _ in hits]
        pages5 = [d["id"].rsplit(":", 1)[0] if d["kind"] == "page" else d["id"] for d, _ in hits]
        gold_pages = [g.rsplit(":", 1)[0] if g.startswith("page:") else g for g in it["gold_ids"]]
        if it["answerable"]:
            hit = next((r for r, i in enumerate(ids) if i in it["gold_ids"]), None)
            hitp = next((r for r, i in enumerate(pages5) if i in gold_pages), None)
            rec5.append(1 if hit is not None else 0)
            rec5p.append(1 if hitp is not None else 0)
            rr.append(1.0 / (hitp + 1) if hitp is not None else 0.0)
        res = None
        for _try in range(3):
            try:
                res = ask(it["q"], idx=idx)
                break
            except Exception as _e:
                import time as _t
                _t.sleep(5)
        if res is None:
            continue
        lats.append(res["latency_s"])
        a = res["answer"].lower()
        if it["answerable"]:
            s = judge(it["q"], it["reference"], res["answer"])
            scores.append(s)
            if s < 2:
                fails.append((it["q"], res["answer"], s, ids[:2]))
        else:
            refusals.append(1 if any(r in a for r in REFUSAL) else 0)
            if not refusals[-1]:
                fails.append((it["q"], res["answer"], "не отказал", ids[:2]))
        if n % 20 == 0:
            print(f"  прошло {n}/{len(items)}", flush=True)

    def pct(x):
        return round(100.0 * sum(x) / len(x), 1) if x else 0.0

    lats.sort()
    out = {
        "вопросов": len(items),
        "recall@5_чанк": pct(rec5),
        "recall@5_страница": pct(rec5p),
        "MRR": round(sum(rr) / len(rr), 3) if rr else 0,
        "ответ_верен_2": pct([1 if s == 2 else 0 for s in scores]),
        "ответ_неполон_1": pct([1 if s == 1 else 0 for s in scores]),
        "ответ_неверен_0": pct([1 if s <= 0 else 0 for s in scores]),
        "честных_отказов": pct(refusals),
        "задержка_p50_с": round(statistics.median(lats), 2) if lats else 0,
        "задержка_p95_с": round(lats[int(len(lats) * 0.95) - 1], 2) if lats else 0,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    with open(os.path.join(BASE, "eval_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"metrics": out, "fails": fails[:40]}, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
