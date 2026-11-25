#!/usr/bin/env python3
"""Поиск по корпусу магазина: BM25 (+dense, если есть векторы). Без внешних зависимостей."""
import json
import math
import os
import re
import urllib.request
from collections import Counter

import numpy as np

BASE = "/srv/media/projects/shop-assistant"
OLLAMA = "http://127.0.0.1:11434/api/embed"
EMB_MODEL = "bge-m3"


def tok(text):
    text = text.lower().replace("ё", "е")
    words = re.findall(r"[a-zа-я0-9]+", text)
    out = []
    for w in words:
        out.append(w)
        if len(w) > 6:
            out.append(w[:6])
    return out


class Index:
    def __init__(self):
        self.docs = [json.loads(l) for l in open(os.path.join(BASE, "docs.jsonl"), encoding="utf-8")]
        self.tfs, self.df = [], Counter()
        self.lens = []
        for d in self.docs:
            tf = Counter(tok(d["text"] + " " + d.get("title", "")))
            self.tfs.append(tf)
            self.lens.append(sum(tf.values()))
            for w in tf:
                self.df[w] += 1
        self.N = len(self.docs)
        self.avgdl = sum(self.lens) / max(1, self.N)
        self.vecs = None
        vp = os.path.join(BASE, "vectors.npy")
        if os.path.exists(vp):
            try:
                self.vecs = np.load(vp)
            except Exception:
                self.vecs = None

    def bm25(self, query, k=50, k1=1.4, b=0.75):
        qt = set(tok(query))
        scored = []
        for i, tf in enumerate(self.tfs):
            s = 0.0
            dl = self.lens[i] or 1
            for w in qt:
                f = tf.get(w)
                if not f:
                    continue
                idf = math.log(1 + (self.N - self.df[w] + 0.5) / (self.df[w] + 0.5))
                s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / self.avgdl))
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        return scored[:k]

    def dense(self, query, k=50):
        if self.vecs is None:
            return []
        try:
            req = urllib.request.Request(
                OLLAMA,
                data=json.dumps({"model": EMB_MODEL, "input": [query]}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                qv = np.array(json.load(r)["embeddings"][0], dtype=np.float32)
        except Exception:
            return []
        qv /= np.linalg.norm(qv) + 1e-9
        sims = self.vecs @ qv
        idx = np.argsort(-sims)[:k]
        return [(float(sims[i]), int(i)) for i in idx]

    def search(self, query, k=5):
        bm = self.bm25(query, 50)
        dn = self.dense(query, 50)
        fused = {}
        for rank, (_, i) in enumerate(bm):
            fused[i] = fused.get(i, 0) + 1.0 / (60 + rank)
        for rank, (_, i) in enumerate(dn):
            fused[i] = fused.get(i, 0) + 1.0 / (60 + rank)
        if not fused:
            return []
        order = sorted(fused.items(), key=lambda kv: -kv[1])[:k]
        return [(self.docs[i], score) for i, score in order]


_INDEX = None


def get_index():
    global _INDEX
    if _INDEX is None:
        _INDEX = Index()
    return _INDEX


if __name__ == "__main__":
    import sys
    idx = Index()
    print("документов:", idx.N, "| dense:", "да" if idx.vecs is not None else "нет")
    q = " ".join(sys.argv[1:]) or "доставка почтой сроки"
    for d, s in idx.search(q, 5):
        print(f"{s:.4f} [{d['kind']}] {d['title'][:60]}")
