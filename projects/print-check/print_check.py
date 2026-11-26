#!/usr/bin/env python3
"""Печать из библиотеки: 640 px карточки, ESRGAN x4 против LANCZOS, dpi и резкость."""
import glob
import json
import os
import random
import time

import cv2
import numpy as np
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

SRC = "/srv/media/generated/images"
OUT = "/srv/media/projects/print-check"
WEIGHTS = "/srv/media/projects/upscale-bench/RealESRGAN_x4plus.pth"
os.makedirs(OUT, exist_ok=True)


def dpi(px, mm):
    return round(px / (mm / 25.4))


def sharp(bgr):
    return round(float(np.std(cv2.Laplacian(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.CV_32F))), 1)


def main():
    files = [f for f in glob.glob(os.path.join(SRC, "**", "*.jpg"), recursive=True)
             if cv2.imread(f) is not None and min(cv2.imread(f).shape[:2]) <= 700]
    random.Random(3).shuffle(files)
    files = files[:6]
    print("карточек 640 px:", len(files))

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    up = RealESRGANer(scale=4, model_path=WEIGHTS, model=model, tile=0, tile_pad=10,
                      pre_pad=0, half=True, device=torch.device("cuda"))

    rows = []
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        h, w = img.shape[:2]
        t0 = time.time()
        esr, _ = up.enhance(img, outscale=4)
        t_esr = time.time() - t0
        lan = cv2.resize(img, (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4)

        H4, W4 = esr.shape[:2]
        short_mm_a4, long_mm_a4 = 210, 297
        rows.append({
            "file": os.path.basename(f),
            "было": f"{w}x{h}",
            "стало": f"{W4}x{H4}",
            "резкость_было": sharp(img),
            "резкость_lanczos": sharp(lan),
            "резкость_esrgan": sharp(esr),
            "dpi_A4": dpi(min(W4, H4), short_mm_a4),
            "dpi_A3": dpi(min(W4, H4), 297),
            "секунд": round(t_esr, 1),
        })
        out_path = os.path.join(OUT, os.path.basename(f))
        cv2.imwrite(out_path, esr, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"{os.path.basename(f)[:26]:28} {rows[-1]['было']} -> {rows[-1]['стало']} "
              f"резкость {rows[-1]['резкость_было']} -> {rows[-1]['резкость_esrgan']} "
              f"(lanczos {rows[-1]['резкость_lanczos']}) | A4 {rows[-1]['dpi_A4']} dpi, "
              f"A3 {rows[-1]['dpi_A3']} dpi | {rows[-1]['секунд']} с", flush=True)

    if rows:
        summary = {
            "карточек": len(rows),
            "резкость_было": round(sum(r["резкость_было"] for r in rows) / len(rows), 1),
            "резкость_lanczos": round(sum(r["резкость_lanczos"] for r in rows) / len(rows), 1),
            "резкость_esrgan": round(sum(r["резкость_esrgan"] for r in rows) / len(rows), 1),
            "dpi_A4": round(sum(r["dpi_A4"] for r in rows) / len(rows)),
            "dpi_A3": round(sum(r["dpi_A3"] for r in rows) / len(rows)),
            "секунд": round(sum(r["секунд"] for r in rows) / len(rows), 1),
            "VRAM_пик_МиБ": round(torch.cuda.max_memory_allocated() / 2 ** 20),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        json.dump({"summary": summary, "rows": rows},
                  open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
