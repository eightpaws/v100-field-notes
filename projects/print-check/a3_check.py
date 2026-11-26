#!/usr/bin/env python3
"""Вторая ступень для A3: один проход x4 с дотяжкой против двух проходов x4."""
import glob
import json
import os

import cv2
import numpy as np
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

SRC = "/srv/media/projects/print-check"
OUT = "/srv/media/projects/print-check/a3"
WEIGHTS = "/srv/media/projects/upscale-bench/RealESRGAN_x4plus.pth"
TARGET = 4961  # A3 при 300 dpi по короткой стороне
os.makedirs(OUT, exist_ok=True)


def sharp(bgr):
    return round(float(np.std(cv2.Laplacian(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.CV_32F))), 2)


def main():
    src = [f for f in glob.glob(os.path.join(SRC, "*.jpg"))][:3]
    print("карточек:", len(src))
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    up = RealESRGANer(scale=4, model_path=WEIGHTS, model=model, tile=256, tile_pad=16,
                      pre_pad=0, half=True, device=torch.device("cuda"))

    rows = []
    for f in src:
        img = cv2.imread(f, cv2.IMREAD_COLOR)          # это уже 2560 после первого прохода
        # вариант А: один проход с дотяжкой до 4961
        a = cv2.resize(img, (TARGET, TARGET), interpolation=cv2.INTER_LANCZOS4)
        # вариант Б: второй проход x4, затем сжатие до 4961
        b_big, _ = up.enhance(img, outscale=4)
        b = cv2.resize(b_big, (TARGET, TARGET), interpolation=cv2.INTER_AREA)

        rows.append({
            "file": os.path.basename(f),
            "one_pass": sharp(a),
            "two_passes": sharp(b),
            "size": f"{TARGET}x{TARGET}",
        })
        print(f"{os.path.basename(f)[:26]:28} один {rows[-1]['one_pass']:7} | "
              f"два {rows[-1]['two_passes']:7}", flush=True)
        cv2.imwrite(os.path.join(OUT, "two_pass_" + os.path.basename(f)), b,
                    [cv2.IMWRITE_JPEG_QUALITY, 92])

    if rows:
        a = round(sum(r['one_pass'] for r in rows) / len(rows), 2)
        b = round(sum(r['two_passes'] for r in rows) / len(rows), 2)
        summary = {
            "cards": len(rows),
            "sharpness_one_pass": a,
            "sharpness_two_passes": b,
            "gain_percent": round(100.0 * (b - a) / a, 1) if a else 0,
            "dpi_A3": round(TARGET / (297 / 25.4)),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        json.dump({"summary": summary, "rows": rows},
                  open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
