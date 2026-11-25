#!/usr/bin/env python3
"""Что на самом деле даёт наш x4: интерполяцию или новые детали.
Сравниваем готовый promo_x4 с обычным LANCZOS-увеличением того же оригинала."""
import glob
import json
import os

import cv2
import numpy as np

ROOT = "/srv/media/generated/images"
OUT = "/srv/media/projects/upscale-bench"
os.makedirs(OUT, exist_ok=True)


def psnr(a, b):
    mse = np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2)
    return 99.0 if mse == 0 else float(10 * np.log10(255.0 ** 2 / mse))


rows = []
for f in sorted(glob.glob(os.path.join(ROOT, "promo", "*.jpg")))[:8]:
    x4 = os.path.join(ROOT, "promo_x4", os.path.basename(f).replace(".jpg", "_x4.jpg"))
    if not os.path.exists(x4):
        continue
    src = cv2.imread(f, cv2.IMREAD_COLOR)
    got = cv2.imread(x4, cv2.IMREAD_COLOR)
    if src is None or got is None:
        continue
    h, w = got.shape[:2]
    lan = cv2.resize(src, (w, h), interpolation=cv2.INTER_LANCZOS4)
    cub = cv2.resize(src, (w, h), interpolation=cv2.INTER_CUBIC)
    hf_src = float(np.std(cv2.Laplacian(cv2.cvtColor(got, cv2.COLOR_BGR2GRAY), cv2.CV_32F)))
    hf_lan = float(np.std(cv2.Laplacian(cv2.cvtColor(lan, cv2.COLOR_BGR2GRAY), cv2.CV_32F)))
    rows.append({
        "file": os.path.basename(f),
        "size": f"{w}x{h}",
        "psnr_x4_vs_lanczos": round(psnr(got, lan), 2),
        "psnr_x4_vs_cubic": round(psnr(got, cub), 2),
        "sharpness_x4": round(hf_src, 2),
        "sharpness_lanczos": round(hf_lan, 2),
    })
    print(f"{rows[-1]['file'][:20]:22} {rows[-1]['size']:10} PSNR x4/LANCZOS {rows[-1]['psnr_x4_vs_lanczos']:6} дБ"
          f" | резкость x4 {rows[-1]['sharpness_x4']:.1f} против {rows[-1]['sharpness_lanczos']:.1f}")

if rows:
    avg = lambda k: round(sum(r[k] for r in rows) / len(rows), 2)
    summary = {
        "картинок": len(rows),
        "средний_PSNR_x4_против_LANCZOS": avg("psnr_x4_vs_lanczos"),
        "средний_PSNR_x4_против_CUBIC": avg("psnr_x4_vs_cubic"),
        "резкость_x4": avg("sharpness_x4"),
        "резкость_LANCZOS": avg("sharpness_lanczos"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    json.dump({"summary": summary, "rows": rows}, open(os.path.join(OUT, "x4_check.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
