#!/usr/bin/env python3
"""Апскейл под печать: LANCZOS против Real-ESRGAN, честная метрика на своих картинках.
Схема: берём оригинал 1024, уменьшаем до 512, апскейлим обратно до 1024, сравниваем с оригиналом."""
import glob
import json
import os
import time

import cv2
import numpy as np
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

SRC = "/srv/media/generated/images/promo"
OUT = "/srv/media/projects/upscale-bench"
os.makedirs(OUT, exist_ok=True)


def psnr(a, b):
    mse = np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2)
    return 99.0 if mse == 0 else float(10 * np.log10(255.0 ** 2 / mse))


def ssim(a, b):
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    k = (11, 11)
    mu_a = cv2.GaussianBlur(a, k, 1.5)
    mu_b = cv2.GaussianBlur(b, k, 1.5)
    sa = cv2.GaussianBlur(a * a, k, 1.5) - mu_a ** 2
    sb = cv2.GaussianBlur(b * b, k, 1.5) - mu_b ** 2
    sab = cv2.GaussianBlur(a * b, k, 1.5) - mu_a * mu_b
    s = ((2 * mu_a * mu_b + C1) * (2 * sab + C2)) / ((mu_a ** 2 + mu_b ** 2 + C1) * (sa + sb + C2))
    return float(np.mean(s))


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.jpg")))[:8]
    print("картинок:", len(files))
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    w = os.path.join(OUT, "RealESRGAN_x4plus.pth")
    if not os.path.exists(w):
        import urllib.request
        url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
        print("качаю веса...")
        urllib.request.urlretrieve(url, w)
    up = RealESRGANer(scale=4, model_path=w, model=model, tile=0, tile_pad=10,
                      pre_pad=0, half=False, device=torch.device("cuda"))

    rows = []
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, wd = img.shape[:2]
        half = cv2.resize(img, (wd // 2, h // 2), interpolation=cv2.INTER_AREA)

        t0 = time.time()
        lan = cv2.resize(half, (wd, h), interpolation=cv2.INTER_LANCZOS4)
        t_lan = time.time() - t0

        t0 = time.time()
        esr, _ = up.enhance(half, outscale=2)
        esr = cv2.resize(esr, (wd, h)) if esr.shape[:2] != (h, wd) else esr
        t_esr = time.time() - t0

        rows.append({
            "file": os.path.basename(f),
            "lanczos": {"psnr": round(psnr(img, lan), 2), "ssim": round(ssim(img, lan), 4), "sec": round(t_lan, 2)},
            "realesrgan": {"psnr": round(psnr(img, esr), 2), "ssim": round(ssim(img, esr), 4), "sec": round(t_esr, 2)},
        })
        print(f"{os.path.basename(f)[:22]:24} lanczos {rows[-1]['lanczos']['psnr']:5} дБ / {rows[-1]['lanczos']['ssim']:.3f}"
              f" | esrgan {rows[-1]['realesrgan']['psnr']:5} дБ / {rows[-1]['realesrgan']['ssim']:.3f}"
              f" | {rows[-1]['realesrgan']['sec']} с")

    def avg(k, m):
        vals = [r[k][m] for r in rows]
        return round(sum(vals) / len(vals), 3) if vals else 0

    summary = {
        "картинок": len(rows),
        "lanczos_psnr": avg("lanczos", "psnr"), "lanczos_ssim": avg("lanczos", "ssim"),
        "esrgan_psnr": avg("realesrgan", "psnr"), "esrgan_ssim": avg("realesrgan", "ssim"),
        "esrgan_секунд": avg("realesrgan", "sec"),
        "vrgb_пик_МиБ": round(torch.cuda.max_memory_allocated() / 2 ** 20),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    json.dump({"summary": summary, "rows": rows}, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
