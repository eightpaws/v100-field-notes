#!/usr/bin/env python3
"""IC-Light с нейтральным светом: смотрим, уезжает ли цвет товара без цветного ключа."""
import json
import os
import sys
import time

import cv2
import numpy as np
import torch

sys.path.insert(0, "/srv/media/projects/iclight")
import iclight_run as irl

NEUTRAL = ("neutral daylight, even white lighting, no color cast, "
           "clean light gray seamless background, product photography")
NEG = "warm light, yellow cast, blue cast, colored lighting, harsh shadows, " + irl.N_PROMPT


def main():
    files = sorted([f for f in os.listdir(irl.SRC) if f.endswith(".jpg")])[:10]
    tok, te, vae, t2i, _ = irl.build()
    print("модели подняты", flush=True)

    rows = []
    for fn in files:
        img = cv2.imread(os.path.join(irl.SRC, fn))
        h, w = img.shape[:2]
        cx, cy = w // 2, int(h * 0.55)
        pts = [(cx * irl.W // w, cy * irl.H // h),
               (max(0, cx - w // 6) * irl.W // w, cy * irl.H // h),
               (min(w - 1, cx + w // 6) * irl.W // w, cy * irl.H // h)]
        t0 = time.time()
        out = irl.relight(img, tok, te, vae, t2i, f"{NEUTRAL}, {irl.A_PROMPT}", NEG)
        secs = round(time.time() - t0, 1)
        de = irl.delta_e(irl.center_crop(img, irl.W, irl.H), out, pts)
        path = os.path.join(irl.OUT, f"{fn[:16]}_нейтральный.jpg")
        cv2.imwrite(path, cv2.cvtColor(out, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 93])
        rows.append({"file": fn[:16], "секунд": secs, "dE_среднее": round(sum(de) / 3, 1)})
        print(f"{fn[:16]:18} ΔE {rows[-1]['dE_среднее']:5} | {secs} с", flush=True)

    summary = {"пар": len(rows),
               "dE_среднее": round(sum(r["dE_среднее"] for r in rows) / len(rows), 1),
               "dE_максимум": max(r["dE_среднее"] for r in rows),
               "секунд_на_фото": round(sum(r["секунд"] for r in rows) / len(rows), 1),
               "VRAM_пик_МиБ": round(torch.cuda.max_memory_allocated() / 2 ** 20)}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    json.dump({"summary": summary, "rows": rows},
              open(os.path.join(irl.OUT, "neutral.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
