#!/usr/bin/env python3
"""Набор проверочных вопросов: 40 по товарам, 40 по правилам (через модель), 20 без ответа."""
import json
import os
import random
import re
import urllib.request

BASE = "/srv/media/projects/shop-assistant"
LLM = "http://127.0.0.1:18450/v1/chat/completions"

TEMPLATES = [
    ("Сколько стоит {name}?", "price"),
    ("{name} есть в наличии?", "stock"),
    ("Какой артикул у товара {name}?", "sku"),
    ("Расскажи про {name}", "desc"),
]

UNANSWERABLE = [
    "Есть ли у вас доставка в Казахстан дронами?",
    "Какой у магазина ИНН и ОГРН?",
    "Дадите ли скидку 70 процентов при покупке двух растений?",
    "Можно ли оплатить заказ биткоинами?",
    "Вы продаёте семена томатов?",
    "Кто генеральный директор компании?",
    "Есть ли у вас магазин в Санкт-Петербурге, куда можно прийти лично?",
    "Сколько сотрудников работает в компании?",
    "Можно ли вернуть растение через три года после покупки?",
    "Вы доставляете в Австралию?",
    "Продаёте ли вы удобрения для кактусов?",
    "Какой у вас годовой оборот?",
    "Есть ли рассрочка на 24 месяца без банка?",
    "Можно ли забрать заказ ночью?",
    "У вас есть вакансия курьера с личным автомобилем?",
    "Продаёте ли вы искусственные цветы из пластика?",
    "Можно ли получить сертификат на редкий сорт орхидеи?",
    "Сколько стоит подписка на ежемесячную доставку букета?",
    "Вы работаете по договору с юридическими лицами по безналу с отсрочкой 90 дней?",
    "Есть ли у вас мобильное приложение для iOS?",
]


def llm(msgs, max_tokens=300):
    body = json.dumps({
        "messages": msgs, "temperature": 0, "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    req = urllib.request.Request(LLM, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return (json.load(r)["choices"][0]["message"].get("content") or "").strip()


def main():
    docs = [json.loads(l) for l in open(os.path.join(BASE, "docs.jsonl"), encoding="utf-8")]
    products = [d for d in docs if d["kind"] == "product"]
    pages = [d for d in docs if d["kind"] == "page"]
    rnd = random.Random(20261124)

    items = []
    for n, p in enumerate(rnd.sample(products, 40)):
        tmpl, kind = TEMPLATES[n % len(TEMPLATES)]
        items.append({
            "q": tmpl.format(name=p["title"]),
            "kind": "product_" + kind,
            "gold_ids": [p["id"]],
            "reference": p["text"][:600],
            "answerable": True,
        })

    picked = rnd.sample(pages, 40)
    for p in picked:
        prompt = (
            "Ниже фрагмент страницы интернет-магазина. Придумай ОДИН короткий вопрос покупателя, "
            "ответ на который прямо есть в этом фрагменте. Затем выпиши короткий ответ (до 30 слов), "
            "используя только факты из фрагмента. Формат строго:\nВОПРОС: ...\nОТВЕТ: ...\n\n"
            f"Фрагмент:\n{p['text'][:1200]}"
        )
        try:
            out = llm([{"role": "user", "content": prompt}], 220)
        except Exception:
            continue
        mq = re.search(r"ВОПРОС:\s*(.+)", out)
        ma = re.search(r"ОТВЕТ:\s*(.+)", out, re.S)
        if not (mq and ma):
            continue
        q = mq.group(1).strip()
        a = " ".join(ma.group(1).split())[:300]
        if len(q) < 8 or len(a) < 5:
            continue
        items.append({
            "q": q, "kind": "page", "gold_ids": [p["id"]],
            "reference": f"{a}\n\nФрагмент: {p['text'][:700]}", "answerable": True,
        })

    for q in UNANSWERABLE:
        items.append({"q": q, "kind": "unanswerable", "gold_ids": [], "reference": "", "answerable": False})

    path = os.path.join(BASE, "evalset.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    page_n = sum(1 for i in items if i["kind"] == "page")
    print("вопросов:", len(items), "| товарных:", sum(1 for i in items if i['kind'].startswith('product')),
          "| страничных:", page_n, "| без ответа:", sum(1 for i in items if not i['answerable']))


if __name__ == "__main__":
    main()
