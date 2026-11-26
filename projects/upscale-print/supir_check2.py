#!/usr/bin/env python3
"""V100-06: SUPIR v0Q на 640 px -> 2560. Время, VRAM, цвет, резкость."""
import os
import sys
import time

import cv2
import einops
import numpy as np
import torch
from omegaconf import OmegaConf
from PIL import Image

ROOT = "/srv/media/projects/supir"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from SUPIR.util import create_SUPIR_model, convert_dtype  # noqa: E402

SRC = "/srv/media/generated/images/v100_2411_1208/03_букет_сухоцветов_в_крафт.jpg"
OUT = "/srv/media/projects/upscale-print"
SDXL = f"{ROOT}/weights/sd_xl_base_1.0_0.9vae.safetensors"
CKPT_Q = f"{ROOT}/weights/SUPIR-v0Q.ckpt"

A_PROMPT = ("Cinematic, high contrast, highly detailed photo, realistic maximum detail, "
            "sharp focus, natural colors, no painting")
N_PROMPT = ("painting, illustration, drawing, cartoon, CG style, 3d render, blurry, "
            "worst quality, low quality, watermark, jpeg artifacts, over-smooth")


def sharp(bgr):
    return round(float(np.std(cv2.Laplacian(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.CV_32F))), 1)


def main():
    cfg = OmegaConf.load(f"{ROOT}/options/SUPIR_v0_tiled.yaml")
    cfg.SDXL_CKPT = SDXL
    cfg.SUPIR_CKPT_Q = CKPT_Q
    cfg_path = f"{ROOT}/options/_local_v0Q_tiled.yaml"
    OmegaConf.save(cfg, cfg_path)

    torch.cuda.reset_peak_memory_stats()
    model = create_SUPIR_model(cfg_path, SUPIR_sign="Q")
    model.eval().to("cuda")
    model.ae_dtype = convert_dtype("fp32")
    model.model.dtype = convert_dtype("fp16")
    print("модель загружена, МиБ:", round(torch.cuda.memory_allocated() / 2 ** 20), flush=True)

    pil = Image.open(SRC).convert("RGB")
    w, h = pil.size
    scale = max(1.0, 1024 / max(w, h), 2560 / max(w, h))
    new = (int(round(w * scale / 8) * 8), int(round(h * scale / 8) * 8))
    pil = pil.resize(new, Image.LANCZOS)
    arr = np.array(pil) / 255.0 * 2 - 1
    lq = torch.tensor(arr, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0).to("cuda")[:, :3]
    print("вход:", new, flush=True)

    t0 = time.time()
    with torch.no_grad():
        samples = model.batchify_sample(
            lq, [""], num_steps=25, restoration_scale=-1, s_churn=5, s_noise=1.01,
            cfg_scale=4.0, control_scale=1.0, seed=1234, num_samples=1,
            p_p=A_PROMPT, n_p=N_PROMPT, color_fix_type="Wavelet",
            use_linear_CFG=True, use_linear_control_scale=False,
            cfg_scale_start=1.0, control_scale_start=0.0)
    secs = round(time.time() - t0, 1)
    peak = round(torch.cuda.max_memory_allocated() / 2 ** 20)

    x = (einops.rearrange(samples, "b c h w -> b h w c") * 127.5 + 127.5).cpu().numpy().round().clip(0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(x[0], cv2.COLOR_RGB2BGR)
    cv2.imwrite(f"{OUT}/supir_v0Q.png", bgr)
    print(f"supir {secs} с | VRAM {peak} МиБ | {bgr.shape[1]}x{bgr.shape[0]} | резкость {sharp(bgr)}", flush=True)

    src = cv2.imread(SRC)
    back = cv2.resize(bgr, (src.shape[1], src.shape[0]), interpolation=cv2.INTER_AREA)
    la = cv2.cvtColor(src, cv2.COLOR_BGR2LAB).astype(np.float32)
    lb = cv2.cvtColor(back, cv2.COLOR_BGR2LAB).astype(np.float32)
    hh, ww = src.shape[:2]
    pts = [(int(ww * 0.5), int(hh * 0.5)), (int(ww * 0.35), int(hh * 0.45)),
           (int(ww * 0.65), int(hh * 0.55)), (int(ww * 0.5), int(hh * 0.7)), (int(ww * 0.5), int(hh * 0.3))]
    des = []
    for px, py in pts:
        pa, pb = la[py, px], lb[py, px]
        des.append(float(np.sqrt(((pa[0] - pb[0]) * 100 / 255) ** 2 + (pa[1] - pb[1]) ** 2 + (pa[2] - pb[2]) ** 2)))
    print("ΔE среднее:", round(sum(des) / len(des), 1), "максимум:", round(max(des), 1), flush=True)


if __name__ == "__main__":
    main()
