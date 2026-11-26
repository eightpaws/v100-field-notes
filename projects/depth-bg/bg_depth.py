#!/usr/bin/env python3
"""Смена фона с сохранением товара, второй заход: маска по глубине + ControlNet-depth.
Метрики: SSIM товара, доля изменённого фона, SSIM по контуру товара."""
import glob
import json
import os
import time

import cv2
import numpy as np
import torch

torch.backends.cudnn.enabled = False   # cuDNN 9 на sm_70 не находит движок для fp16-свёрток

from diffusers import (ControlNetModel, StableDiffusionXLControlNetInpaintPipeline)
from PIL import Image
from transformers import pipeline as hf_pipeline

MODEL = "/srv/media/apps/invokeai5/data/models/sdxl/main/stable-diffusion-xl-1.0-inpainting-0.1"
CTRL = "diffusers/controlnet-depth-sdxl-1.0-small"
DEPTH = "depth-anything/Depth-Anything-V2-Small-hf"
SRC = "/srv/media/generated/images/promo"
OUT = "/srv/media/projects/depth-bg"
os.makedirs(OUT, exist_ok=True)


def ssim_map(a, b):
    a, b = a.astype(np.float64), b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    k = (11, 11)
    ma, mb = cv2.GaussianBlur(a, k, 1.5), cv2.GaussianBlur(b, k, 1.5)
    sa = cv2.GaussianBlur(a * a, k, 1.5) - ma ** 2
    sb = cv2.GaussianBlur(b * b, k, 1.5) - mb ** 2
    sab = cv2.GaussianBlur(a * b, k, 1.5) - ma * mb
    return ((2 * ma * mb + C1) * (2 * sab + C2)) / ((ma ** 2 + mb ** 2 + C1) * (sa + sb + C2))


def fill_holes(mask):
    h, w = mask.shape
    ff = mask.copy()
    m2 = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, m2, (0, 0), 255)
    holes = cv2.bitwise_not(ff) | mask
    return holes


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.jpg")))[:3]
    ctrl = ControlNetModel.from_pretrained(CTRL, torch_dtype=torch.float16, variant="fp16",
                                           local_files_only=True)
    pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
        MODEL, controlnet=ctrl, torch_dtype=torch.float16, variant="fp16", local_files_only=True)
    pipe.enable_model_cpu_offload()
    pipe.enable_vae_slicing()
    pipe.enable_attention_slicing()
    pipe.set_progress_bar_config(disable=True)
    depth = hf_pipeline("depth-estimation", model=DEPTH, device=0)
    print("готово к работе", flush=True)

    prompt = ("clean studio background, soft neutral gradient, subtle shadow under the plant, "
              "high quality product photography")
    rows = []
    for f in files:
        img = Image.open(f).convert("RGB")
        w, h = img.size
        tw = 640
        th = max(512, (int(tw * h / w) // 8) * 8)
        img = img.resize((tw, th))
        bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        t0 = time.time()
        d = depth(img)["depth"].resize(img.size)
        d_np = np.array(d, dtype=np.float32)
        d_np = (d_np - d_np.min()) / (np.ptp(d_np) + 1e-6)
        near = (d_np > np.quantile(d_np, 0.45)).astype(np.uint8) * 255
        near = cv2.morphologyEx(near, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        product = fill_holes(near)
        product = cv2.erode(product, np.ones((5, 5), np.uint8), iterations=1)
        mask_bg = cv2.bitwise_not(product)
        if int((mask_bg > 0).sum()) < 0.05 * mask_bg.size:      # маска фона почти пустая
            h_, w_ = bgr.shape[:2]
            corners = np.array([bgr[0, 0], bgr[0, w_ - 1], bgr[h_ - 1, 0], bgr[h_ - 1, w_ - 1]], dtype=np.int16)
            bgc = np.median(corners, axis=0)
            color_bg = (np.abs(bgr.astype(np.int16) - bgc).sum(axis=2) < 42).astype(np.uint8) * 255
            mask_bg = cv2.dilate(color_bg, np.ones((7, 7), np.uint8), iterations=2)
            product = cv2.bitwise_not(mask_bg)
        t_depth = time.time() - t0

        ctrl_img = Image.merge("RGB", (d, d, d))
        t0 = time.time()
        out = pipe(prompt=prompt, image=img, mask_image=Image.fromarray(mask_bg).convert("L"),
                   control_image=ctrl_img, height=th, width=tw, strength=0.80,
                   controlnet_conditioning_scale=0.95, num_inference_steps=28,
                   guidance_scale=5.5).images[0]
        t_gen = time.time() - t0

        out_bgr = cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)
        if out_bgr.shape != bgr.shape:
            out_bgr = cv2.resize(out_bgr, (bgr.shape[1], bgr.shape[0]))
        pm = product > 0

        gray_a = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gray_b = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_a, 60, 160) > 0
        edges = cv2.dilate(edges.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & pm

        s_all = float(ssim_map(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY),
                               cv2.cvtColor(out_bgr, cv2.COLOR_BGR2GRAY))[pm].mean())
        s_edge = float(ssim_map(gray_a, gray_b)[edges].mean()) if edges.any() else 0.0
        diff = np.abs(bgr.astype(np.int16) - out_bgr.astype(np.int16)).max(axis=2)
        changed = float((diff[mask_bg > 0] > 12).mean() * 100)

        name = os.path.basename(f).replace(".jpg", "")
        out.save(os.path.join(OUT, f"{name}_depthbg.jpg"), quality=92)
        rows.append({"file": name, "ssim_product": round(s_all, 3), "ssim_edges": round(s_edge, 3),
                     "bg_changed_pct": round(changed, 1), "depth_s": round(t_depth, 1),
                     "gen_s": round(t_gen, 1)})
        print(f"{name:10} SSIM {s_all:.3f} | контур {s_edge:.3f} | фон {changed:5.1f}% | "
              f"{t_gen:.1f} с", flush=True)
        torch.cuda.empty_cache()

    if rows:
        summary = {
            "картинок": len(rows),
            "SSIM_товара": round(sum(r["ssim_product"] for r in rows) / len(rows), 3),
            "SSIM_контура": round(sum(r["ssim_edges"] for r in rows) / len(rows), 3),
            "фон_изменён": round(sum(r["bg_changed_pct"] for r in rows) / len(rows), 1),
            "секунд": round(sum(r["gen_s"] for r in rows) / len(rows), 1),
            "VRAM_пик_МиБ": round(torch.cuda.max_memory_allocated() / 2 ** 20),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        json.dump({"summary": summary, "rows": rows},
                  open(os.path.join(OUT, "result_controlnet.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
