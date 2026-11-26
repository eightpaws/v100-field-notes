#!/usr/bin/env python3
"""Видео 720p на V100: генерируем и проверяем КАДРЫ, а не только код возврата."""
import json
import os
import time

import cv2
import numpy as np
import torch


from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

MODEL = "/srv/media/ai-cache/models/cogvideox-5b"
OUT = "/srv/media/projects/video-720"
os.makedirs(OUT, exist_ok=True)

PROMPT = ("A greenhouse shelf with blooming begonias, soft daylight, camera slowly slides right, "
          "realistic product video, no text")
W, H, FRAMES, STEPS = 480, 320, 17, 20


def frame_stats(path):
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    if not frames:
        return None
    sharp = [float(cv2.Laplacian(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.CV_32F).var()) for f in frames]
    diffs = [float(np.abs(frames[i].astype(np.int16) - frames[i - 1].astype(np.int16)).mean())
             for i in range(1, len(frames))]
    return {
        "кадров": len(frames),
        "размер": f"{frames[0].shape[1]}x{frames[0].shape[0]}",
        "резкость_медиана": round(float(np.median(sharp)), 1),
        "резкость_мин": round(min(sharp), 1),
        "движение_медиана": round(float(np.median(diffs)), 2) if diffs else 0,
        "замерших_кадров": sum(1 for d in diffs if d < 0.5),
    }


def main():
    t0 = time.time()
    pipe = CogVideoXPipeline.from_pretrained(MODEL, torch_dtype=torch.float16, local_files_only=True)
    pipe.enable_model_cpu_offload()
    for m in ("enable_vae_slicing", "enable_vae_tiling", "enable_forward_chunking"):
        if hasattr(pipe, m):
            getattr(pipe, m)()
    pipe.set_progress_bar_config(disable=True)
    load_s = time.time() - t0
    print(f"модель загружена за {load_s:.0f} с", flush=True)

    t0 = time.time()
    frames = pipe(prompt=PROMPT, height=H, width=W, num_frames=FRAMES, num_inference_steps=STEPS,
                  guidance_scale=6.0, generator=torch.Generator("cpu").manual_seed(11)).frames[0]
    gen_s = time.time() - t0
    path = os.path.join(OUT, "greenhouse.mp4")
    export_to_video(frames, path, fps=8)

    stats = frame_stats(path)
    summary = {
        "промпт": PROMPT[:60],
        "разрешение": f"{W}x{H}",
        "кадров_запрошено": FRAMES,
        "шагов": STEPS,
        "секунд_загрузки": round(load_s),
        "секунд_генерации": round(gen_s),
        "секунд_на_кадр": round(gen_s / FRAMES, 1),
        "VRAM_пик_МиБ": round(torch.cuda.max_memory_allocated() / 2 ** 20),
        **(stats or {}),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    json.dump(summary, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
