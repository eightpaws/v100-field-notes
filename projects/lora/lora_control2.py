#!/usr/bin/env python3
"""Контроль: без LoRA, с LoRA без триггера, с LoRA и триггером. LoRA грузится один раз."""
import json
import os
import time

import cv2
import torch
from diffusers import StableDiffusionXLPipeline
from skimage.metrics import structural_similarity as ssim

BASE = "/srv/media/projects/lora/base-sdxl2"
LORA = "/srv/media/projects/lora/sd-model-finetuned-lora"
OUT = "/srv/media/projects/lora/eval3"
PROMPT = "monstera plant in a white ceramic pot, product photo, soft studio light, plain background"
TRIGGER = "flrmonstera"
NEG = "blurry, watermark, text"
SEED = 777

os.makedirs(OUT, exist_ok=True)


def main():
    pipe = StableDiffusionXLPipeline.from_pretrained(
        BASE, torch_dtype=torch.float16, variant="fp16").to("cuda")
    pipe.set_progress_bar_config(disable=True)
    pipe.load_lora_weights(LORA, weight_name="pytorch_lora_weights.safetensors")

    cases = [
        ("1_bez_lora", PROMPT, False),
        ("2_lora_bez_trigera", PROMPT, True),
        ("3_lora_s_trigerom", f"{TRIGGER}, {PROMPT}", True),
    ]
    res = {}
    for name, prompt, use_lora in cases:
        if use_lora:
            pipe.enable_lora()
        else:
            pipe.disable_lora()
        g = torch.Generator(device="cuda").manual_seed(SEED)
        t0 = time.time()
        img = pipe(prompt=prompt, negative_prompt=NEG, num_inference_steps=25,
                   guidance_scale=5.0, height=768, width=768, generator=g).images[0]
        p = os.path.join(OUT, f"{name}.png")
        img.save(p)
        res[name] = {"секунд": round(time.time() - t0, 1), "файл": p}
        print(f"{name:22} {res[name]['секунд']:5} с", flush=True)

    def gray(n):
        return cv2.cvtColor(cv2.imread(res[n]["файл"]), cv2.COLOR_BGR2GRAY)

    base = gray("1_bez_lora")
    for n in ("2_lora_bez_trigera", "3_lora_s_trigerom"):
        res[n]["ssim_k_baze"] = round(float(ssim(base, gray(n))), 3)
        print(f"{n:22} SSIM k baze {res[n]['ssim_k_baze']}", flush=True)

    res["VRAM_pik_MiB"] = round(torch.cuda.max_memory_allocated() / 2 ** 20)
    json.dump(res, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
