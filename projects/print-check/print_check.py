#!/usr/bin/env python3
"""Print check on the 640 px library: ESRGAN x4 against LANCZOS, dpi and sharpness."""
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
    print("cards at 640 px:", len(files))

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
        a4_short_mm, a4_long_mm = 210, 297
        rows.append({
            "file": os.path.basename(f),
            "before": f"{w}x{h}",
            "after": f"{W4}x{H4}",
            "sharpness_before": sharp(img),
            "sharpness_lanczos": sharp(lan),
            "sharpness_esrgan": sharp(esr),
            "dpi_a4": dpi(min(W4, H4), a4_short_mm),
            "dpi_a3": dpi(min(W4, H4), a4_long_mm),
            "seconds": round(t_esr, 1),
        })
        out_path = os.path.join(OUT, os.path.basename(f))
        cv2.imwrite(out_path, esr, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"{os.path.basename(f)[:26]:28} {rows[-1]['before']} -> {rows[-1]['after']} "
              f"sharpness {rows[-1]['sharpness_before']} -> {rows[-1]['sharpness_esrgan']} "
              f"(lanczos {rows[-1]['sharpness_lanczos']}) | A4 {rows[-1]['dpi_a4']} dpi, "
              f"A3 {rows[-1]['dpi_a3']} dpi | {rows[-1]['seconds']} s", flush=True)

    if rows:
        summary = {
            "cards": len(rows),
            "sharpness_before": round(sum(r["sharpness_before"] for r in rows) / len(rows), 1),
            "sharpness_lanczos": round(sum(r["sharpness_lanczos"] for r in rows) / len(rows), 1),
            "sharpness_esrgan": round(sum(r["sharpness_esrgan"] for r in rows) / len(rows), 1),
            "dpi_a4": round(sum(r["dpi_a4"] for r in rows) / len(rows)),
            "dpi_a3": round(sum(r["dpi_a3"] for r in rows) / len(rows)),
            "seconds": round(sum(r["seconds"] for r in rows) / len(rows), 1),
            "vram_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20),
        }
        print(json.dumps(summary, indent=1))
        json.dump({"summary": summary, "rows": rows,
                   "note": "source file names were transliterated to keep the repository ASCII-only"},
                  open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
