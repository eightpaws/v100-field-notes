#!/usr/bin/env python3
"""Контролёр качества карточек: разрешение, резкость, обрезка товара, пригодность к печати."""
import glob
import json
import os
from collections import Counter

import cv2
import numpy as np

ROOT = "/srv/media/generated/images"
OUT = "/srv/media/projects/image-qa"
os.makedirs(OUT, exist_ok=True)
A4_300 = 2480  # короткая сторона A4 при 300 dpi


def analyse(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    small = cv2.resize(gray, (512, int(512 * h / w)))
    sharp = float(cv2.Laplacian(small, cv2.CV_32F).var())

    corners = np.array([img[0, 0], img[0, w - 1], img[h - 1, 0], img[h - 1, w - 1]], dtype=np.int16)
    bgc = np.median(corners, axis=0)
    diff = np.abs(img.astype(np.int16) - bgc).sum(axis=2)
    subject = (diff > 60).astype(np.uint8)
    cover = float(subject.mean() * 100)

    edges = [subject[0, :].mean(), subject[h - 1, :].mean(),
             subject[:, 0].mean(), subject[:, w - 1].mean()]
    clipped = max(edges) > 0.30

    return {
        "file": os.path.relpath(path, ROOT),
        "w": w, "h": h,
        "short_side": min(w, h),
        "sharpness": round(sharp, 1),
        "subject_pct": round(cover, 1),
        "clipped": bool(clipped),
        "print_a4_ok": min(w, h) >= A4_300,
    }


def main():
    files = glob.glob(os.path.join(ROOT, "**", "*.jpg"), recursive=True)
    files += glob.glob(os.path.join(ROOT, "**", "*.png"), recursive=True)
    print("файлов:", len(files))
    rows = []
    for i, f in enumerate(files):
        r = analyse(f)
        if r:
            rows.append(r)
        if (i + 1) % 200 == 0:
            print(f"  обработано {i + 1}", flush=True)

    if not rows:
        print("нечего анализировать")
        return

    sharp_vals = np.array([r["sharpness"] for r in rows])
    thr_soft = float(np.quantile(sharp_vals, 0.10))
    thr_sharp = float(np.quantile(sharp_vals, 0.90))

    for r in rows:
        flags = []
        if r["short_side"] < 768:
            flags.append("мелко")
        if r["sharpness"] < thr_soft:
            flags.append("мягко")
        if r["clipped"]:
            flags.append("товар обрезан")
        if not r["print_a4_ok"]:
            flags.append("не для A4")
        r["flags"] = flags

    total = len(rows)
    def pct(n):
        return round(100.0 * n / total, 1)

    summary = {
        "картинок": total,
        "годных_к_печати_A4": pct(sum(1 for r in rows if r["print_a4_ok"])),
        "мелких": pct(sum(1 for r in rows if r["short_side"] < 768)),
        "мягких": pct(sum(1 for r in rows if r["sharpness"] < thr_soft)),
        "с_обрезанным_товаром": pct(sum(1 for r in rows if r["clipped"])),
        "порог_резкости_10проц": round(thr_soft, 1),
        "медиана_резкости": round(float(np.median(sharp_vals)), 1),
        "хоть_один_флаг": pct(sum(1 for r in rows if r["flags"])),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))

    bad = [r for r in rows if r["flags"]]
    print("\nпримеры брака:")
    for r in bad[:8]:
        print(f"  {r['file'][:52]:54} {r['short_side']}px резкость {r['sharpness']:6} "
              f"покрытие {r['subject_pct']:5}% {', '.join(r['flags'])}")

    json.dump({"summary": summary, "rows": rows[:2000]},
              open(os.path.join(OUT, "quality.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
