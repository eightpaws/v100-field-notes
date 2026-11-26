#!/usr/bin/env python3
"""Готовим базу для LoRA: конвертируем одиночный чекпойнт SDXL в diffusers-каталог
и собираем датасет из монстер (30 картинок + подписи)."""
import glob
import os
import random
import shutil

import torch
from diffusers import StableDiffusionXLPipeline

SRC_CKPT = "/srv/media/apps/invokeai5/data/models/sdxl/main/RealVisXL_V5.0_fp16.safetensors"
BASE = "/srv/media/projects/lora/base-sdxl"
DATA = "/srv/media/projects/lora/data"
IMG_ROOT = "/srv/media/generated/images"
TRIGGER = "flrmonstera"

os.makedirs(DATA, exist_ok=True)

if not os.path.exists(os.path.join(BASE, "model_index.json")):
    print("конвертирую чекпойнт в diffusers, это пара минут", flush=True)
    pipe = StableDiffusionXLPipeline.from_single_file(SRC_CKPT, torch_dtype=torch.float32)
    pipe.save_pretrained(BASE, safe_serialization=True)
    del pipe
    print("готово:", BASE, flush=True)
else:
    print("база уже сконвертирована")

files = glob.glob(os.path.join(IMG_ROOT, "**", "*монстера*.jpg"), recursive=True)
random.Random(21).shuffle(files)
files = files[:30]

for i, f in enumerate(files):
    dst = os.path.join(DATA, f"monstera_{i:02d}.jpg")
    shutil.copy2(f, dst)
    with open(os.path.join(DATA, f"monstera_{i:02d}.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"{TRIGGER}, monstera plant in a ceramic pot, product photo, soft studio light, "
                 f"plain background, detailed leaves, high quality")

print("картинок в датасете:", len(glob.glob(os.path.join(DATA, "*.jpg"))))
