#!/usr/bin/env python3
"""Детерминированный белый фон: маска по глубине, заливка #FFFFFF, без диффузии."""
import glob
import json
import os

import cv2
import numpy as np
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

DEPTH_MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
SRC = sorted(glob.glob("/srv/media/generated/images/v100_2411_1208/*.jpg"))[:5]
OUT = "/srv/media/projects/depth-bg/white"
os.environ["HF_HOME"] = "/srv/media/ai-cache/hf"
os.makedirs(OUT, exist_ok=True)


def main():
    proc = AutoImageProcessor.from_pretrained(DEPTH_MODEL)
    dep = AutoModelForDepthEstimation.from_pretrained(DEPTH_MODEL).to("cpu").float()

    rows = []
    for path in SRC:
        img = cv2.imread(path)
        h, w = img.shape[:2]
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        inputs = dict(proc(images=pil, return_tensors="pt"))
        import torch
        with torch.no_grad():
            d = dep(**inputs).predicted_depth
        d = torch.nn.functional.interpolate(d.unsqueeze(1), size=(h, w), mode="bicubic",
                                            align_corners=False)[0, 0].numpy()
        d_norm = (d - d.min()) / (np.ptp(d) + 1e-6)
        product = (d_norm > 0.42).astype(np.uint8) * 255
        product = cv2.morphologyEx(product, cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8))
        product = cv2.morphologyEx(product, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
        # заливаем внутренние дыры: берём только внешние контуры
        cnts, _ = cv2.findContours(product, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filled = np.zeros_like(product)
        for c in cnts:
            if cv2.contourArea(c) > 0.002 * product.size:
                cv2.drawContours(filled, [c], -1, 255, -1)
        filled = cv2.morphologyEx(filled, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        product = filled
        # сглаженная маска: мягкий край 2 px
        alpha = cv2.GaussianBlur(product, (5, 5), 1.2).astype(np.float32) / 255.0
        alpha3 = cv2.merge([alpha, alpha, alpha])

        canvas = np.full_like(img, 255)
        final = (img * alpha3 + canvas * (1 - alpha3)).astype(np.uint8)
        name = os.path.basename(path)[:18] + "_white.jpg"
        cv2.imwrite(os.path.join(OUT, name), final, [cv2.IMWRITE_JPEG_QUALITY, 95])

        g = cv2.cvtColor(final, cv2.COLOR_BGR2GRAY)
        bg = g[alpha < 0.05]
        rows.append({"file": os.path.basename(path)[:18],
                     "товар_процент": round(100.0 * float(alpha.mean()), 1),
                     "фон_яркость": round(float(bg.mean()), 1),
                     "фон_разброс": round(float(bg.std()), 1)})
        print(f"{rows[-1]['file']:20} товар {rows[-1]['товар_процент']:5}% | "
              f"фон {rows[-1]['фон_яркость']} ±{rows[-1]['фон_разброс']}", flush=True)

    json.dump(rows, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
