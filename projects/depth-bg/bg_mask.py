#!/usr/bin/env python3
"""Маска только на фоне: товар остаётся байт-в-байт, перерисовывается лишь окружение."""
import json
import os
import time

import cv2
import numpy as np
import torch
from diffusers import AutoPipelineForInpainting
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

INPAINT = "/srv/media/apps/invokeai5/data/models/sdxl/main/stable-diffusion-xl-1.0-inpainting-0.1"
DEPTH_MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
SRC = ["/srv/media/generated/images/v100_2411_1208/00_монстера_в_белом_керамич.jpg",
       "/srv/media/generated/images/v100_2411_1208/01_фикус_в_плетёной_корзине.jpg",
       "/srv/media/generated/images/v100_2411_1208/02_суккулент_в_бетонном_каш.jpg",
       "/srv/media/generated/images/v100_2411_1208/03_букет_сухоцветов_в_крафт.jpg",
       "/srv/media/generated/images/v100_2411_1208/04_орхидея_фаленопсис_в_сте.jpg"]
OUT = "/srv/media/projects/depth-bg/mask"
PROMPT = "clean white studio background, seamless paper backdrop, soft even light, product photography"
NEG = "plants, pot, floor, objects, text, watermark, shadow"
os.environ["HF_HOME"] = "/srv/media/ai-cache/hf"
os.makedirs(OUT, exist_ok=True)


def main():
    proc = AutoImageProcessor.from_pretrained(DEPTH_MODEL)
    dep = AutoModelForDepthEstimation.from_pretrained(DEPTH_MODEL).to("cpu").float()
    pipe = AutoPipelineForInpainting.from_pretrained(
        INPAINT, torch_dtype=torch.float16, variant="fp16").to("cuda")
    pipe.set_progress_bar_config(disable=True)

    rows = []
    for path in SRC:
        img = cv2.imread(path)
        h, w = img.shape[:2]
        scale = 768.0 / min(h, w)
        nw, nh = int(round(w * scale / 8) * 8), int(round(h * scale / 8) * 8)
        small = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
        pil = Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))

        inputs = dict(proc(images=pil, return_tensors="pt"))
        with torch.no_grad():
            d = dep(**inputs).predicted_depth
        d = torch.nn.functional.interpolate(d.unsqueeze(1), size=(nh, nw), mode="bicubic",
                                            align_corners=False)[0, 0].numpy()
        d_norm = (d - d.min()) / (np.ptp(d) + 1e-6)
        product = (d_norm > 0.42).astype(np.uint8) * 255
        product = cv2.morphologyEx(product, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        product = cv2.erode(product, np.ones((3, 3), np.uint8))
        bg_mask = cv2.bitwise_not(product)
        bg_mask = cv2.erode(bg_mask, np.ones((3, 3), np.uint8))

        mask_pil = Image.fromarray(bg_mask)
        g = torch.Generator(device="cuda").manual_seed(5)
        t0 = time.time()
        res = pipe(prompt=PROMPT, negative_prompt=NEG, image=pil, mask_image=mask_pil,
                   strength=0.95, num_inference_steps=25, guidance_scale=6.0,
                   height=nh, width=nw, generator=g).images[0]
        secs = time.time() - t0
        out = cv2.cvtColor(np.array(res), cv2.COLOR_RGB2BGR)

        # возвращаем товар байт-в-байт из оригинала
        m3 = cv2.cvtColor(product, cv2.COLOR_GRAY2BGR) / 255.0
        final = (out * (1 - m3) + small * m3).astype(np.uint8)
        name = os.path.basename(path)[:18] + "_mask.jpg"
        cv2.imwrite(os.path.join(OUT, name), final, [cv2.IMWRITE_JPEG_QUALITY, 93])

        gs, gf = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), cv2.cvtColor(final, cv2.COLOR_BGR2GRAY)
        pm = product > 0
        bg_px = gf[~pm]
        # средняя абсолютная разница фона
        diff_bg = float(np.abs(gf.astype(int) - gs.astype(int))[~pm].mean())
        rows.append({"file": os.path.basename(path)[:18],
                     "SSIM_товар": round(float(ssim(gs, gf)), 3),
                     "товар_процент": round(100.0 * pm.mean(), 1),
                     "фон_яркость": round(float(bg_px.mean()), 1),
                     "фон_разброс": round(float(bg_px.std()), 1),
                     "фон_изменён_ед": round(diff_bg, 1),
                     "секунд": round(secs, 1)})
        print(f"{rows[-1]['file']:20} товар {rows[-1]['товар_процент']:5}% | "
              f"фон {rows[-1]['фон_яркость']:5} ±{rows[-1]['фон_разброс']:4} | "
              f"изменено {rows[-1]['фон_изменён_ед']:5} | {rows[-1]['секунд']} с", flush=True)

    if rows:
        summary = {"картинок": len(rows),
                   "фон_яркость": round(sum(r["фон_яркость"] for r in rows) / len(rows), 1),
                   "фон_разброс": round(sum(r["фон_разброс"] for r in rows) / len(rows), 1),
                   "секунд": round(sum(r["секунд"] for r in rows) / len(rows), 1),
                   "VRAM_пик_МиБ": round(torch.cuda.max_memory_allocated() / 2 ** 20)}
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        json.dump({"summary": summary, "rows": rows},
                  open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
