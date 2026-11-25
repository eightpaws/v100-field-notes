#!/usr/bin/env python3
"""Индекс для ассистента магазина: чанки корпуса + эмбеддинги bge-m3 через ollama."""
import json
import os
import sys
import urllib.request

import numpy as np

BASE = "/srv/media/projects/shop-assistant"
OLLAMA = "http://127.0.0.1:11434/api/embed"
MODEL = "bge-m3"
CHUNK = 900
OVERLAP = 150


def embed(texts):
    out = []
    for i in range(0, len(texts), 16):
        batch = texts[i:i + 16]
        req = urllib.request.Request(
            OLLAMA,
            data=json.dumps({"model": MODEL, "input": batch}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            out.extend(json.load(r)["embeddings"])
    return np.array(out, dtype=np.float32)


def chunks_of(text, size=CHUNK, overlap=OVERLAP):
    text = " ".join(text.split())
    if len(text) <= size:
        return [text] if text else []
    res, i = [], 0
    while i < len(text):
        res.append(text[i:i + size])
        i += size - overlap
    return res


def main():
    corpus = json.load(open(os.path.join(BASE, "corpus.json"), encoding="utf-8"))
    docs = []
    for p in corpus["products"]:
        price = f"{p['price']:.0f} {p['currency']}" if p.get("price") is not None else "не указана"
        body = (
            f"Товар: {p['name']}\n"
            f"Категории: {p.get('categories') or 'не указаны'}\n"
            f"Артикул: {p.get('sku') or 'нет'}\n"
            f"Цена: {price}\n"
            f"В наличии: {'да' if p.get('in_stock') else 'нет'}\n"
            f"Описание: {(p.get('short') or '')} {(p.get('full') or '')[:700]}"
        )
        docs.append({
            "id": f"product:{p['id']}",
            "kind": "product",
            "title": p["name"],
            "url": p.get("url", ""),
            "text": body.strip(),
            "price": p.get("price"),
            "in_stock": p.get("in_stock"),
        })

    seen_pages = set()
    for pg in corpus["pages"]:
        text = pg.get("text") or ""
        if len(text) < 200:
            continue
        key = (pg.get("slug") or "") + str(len(text))
        if key in seen_pages:
            continue
        seen_pages.add(key)
        for n, piece in enumerate(chunks_of(text)):
            docs.append({
                "id": f"page:{pg.get('slug')}:{n}",
                "kind": "page",
                "title": pg.get("title", ""),
                "url": f"https://shop/{pg.get('slug')}/",
                "text": f"{pg.get('title', '')}\n{piece}",
            })

    print("чанков:", len(docs))
    try:
        vecs = embed([d["text"] for d in docs])
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        np.save(os.path.join(BASE, "vectors.npy"), vecs)
        print("векторов:", vecs.shape)
    except Exception as e:
        print("эмбеддинги не готовы, только BM25:", e)
    with open(os.path.join(BASE, "docs.jsonl"), "w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    print("товарных:", sum(1 for d in docs if d["kind"] == "product"),
          "| страничных:", sum(1 for d in docs if d["kind"] == "page"))


if __name__ == "__main__":
    main()
