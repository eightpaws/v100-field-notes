#!/usr/bin/env python3
"""Смена фона с сохранением товара: локальная SDXL-inpainting.
Метрики: SSIM внутри маски товара (сохранность) и доля изменившихся пикселей фона."""
import glob
import json
import os
import time

import cv2
import numpy as np
import torch
torch.backends.cudnn.enabled = False   # cuDNN 9 на sm_70 не находит движок для fp16-свёрток
from diffusers import StableDiffusionXLInpaintPipeline
from PIL import Image

MODEL = "/srv/media/apps/invokeai5/data/models/sdxl/main/stable-diffusion-xl-1.0-inpainting-0.1"
SRC = "/srv/media/generated/images/promo"
OUT = "/srv/media/projects/depth-bg"
os.makedirs(OUT, exist_ok=True)


def ssim(a, b, mask=None):
    a, b = a.astype(np.float64), b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    k = (11, 11)
    ma, mb = cv2.GaussianBlur(a, k, 1.5), cv2.GaussianBlur(b, k, 1.5)
    sa = cv2.GaussianBlur(a * a, k, 1.5) - ma ** 2
    sb = cv2.GaussianBlur(b * b, k, 1.5) - mb ** 2
    sab = cv2.GaussianBlur(a * b, k, 1.5) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * sab + C2)) / ((ma ** 2 + mb ** 2 + C1) * (sa + sb + C2))
    return float(s[mask].mean()) if mask is not None else float(s.mean())


def background_mask(bgr, tol=14):
    """Фон = области, связанные с краями и близкие по цвету к углам."""
    h, w = bgr.shape[:2]
    corners = np.array([bgr[0, 0], bgr[0, w - 1], bgr[h - 1, 0], bgr[h - 1, w - 1]], dtype=np.int16)
    bg_color = np.median(corners, axis=0)
    diff = np.abs(bgr.astype(np.int16) - bg_color.astype(np.int16)).sum(axis=2)
    close = (diff < tol * 3).astype(np.uint8) * 255
    n, labels, stats, _ = cv2.connectedComponentsWithStats(close, 8)
    keep = np.zeros_like(close)
    for i in range(1, n):
        x, y, ww, hh, area = stats[i]
        if x <= 1 or y <= 1 or x + ww >= w - 1 or y + hh >= h - 1:
            keep[labels == i] = 255
    keep = cv2.dilate(keep, np.ones((7, 7), np.uint8), iterations=2)
    return keep, diff


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.jpg")))[:3]
    print("картинок:", len(files), flush=True)
    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        MODEL, torch_dtype=torch.float16, variant="fp16", local_files_only=True)
    pipe.enable_model_cpu_offload()
    pipe.set_progress_bar_config(disable=True)
    pipe.enable_vae_slicing()
    pipe.enable_attention_slicing()
    pipe.enable_vae_tiling()
    print("модель загружена", flush=True)

    prompt = ("clean studio background, soft neutral surface, subtle shadow under the plant, "
              "high quality product photography")
    rows = []
    for f in files:
        img = Image.open(f).convert("RGB")
        w, h = img.size
        tw = 512
        th = max(512, (int(tw * h / w) // 8) * 8)
        img = img.resize((tw, th))
        bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        mask_bg, _ = background_mask(bgr)
        mask_pil = Image.fromarray(mask_bg).convert("L")

        t0 = time.time()
        out = pipe(prompt=prompt, image=img, mask_image=mask_pil, height=img.size[1],
                   width=img.size[0], strength=0.95, num_inference_steps=28,
                   guidance_scale=5.5).images[0]
        t_gen = time.time() - t0

        out_bgr = cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)
        if out_bgr.shape != bgr.shape:
            out_bgr = cv2.resize(out_bgr, (bgr.shape[1], bgr.shape[0]))
        product = mask_bg == 0
        inside = ssim(bgr, out_bgr, product)
        diff = np.abs(bgr.astype(np.int16) - out_bgr.astype(np.int16)).max(axis=2)
        changed = float((diff[mask_bg > 0] > 12).mean() * 100)

        name = os.path.basename(f).replace(".jpg", "")
        out.save(os.path.join(OUT, f"{name}_newbg.jpg"), quality=92)
        rows.append({"file": name, "ssim_product": round(inside, 3),
                     "bg_changed_pct": round(changed, 1), "gen_s": round(t_gen, 1)})
        print(f"{name:10} SSIM товара {inside:.3f} | фон изменён {changed:5.1f}% | {t_gen:.1f} с", flush=True)
        torch.cuda.empty_cache()

    if rows:
        summary = {
            "картинок": len(rows),
            "SSIM_товара": round(sum(r["ssim_product"] for r in rows) / len(rows), 3),
            "фон_изменён_процент": round(sum(r["bg_changed_pct"] for r in rows) / len(rows), 1),
            "секунд": round(sum(r["gen_s"] for r in rows) / len(rows), 1),
            "VRAM_пик_МиБ": round(torch.cuda.max_memory_allocated() / 2 ** 20),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        json.dump({"summary": summary, "rows": rows},
                  open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
