#!/usr/bin/env python3
"""V100-06: ESRGAN против 4x-UltraSharp - время, память, цвет (ΔE), резкость."""
import json
import os
import time

import cv2
import numpy as np
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

SRC = "/srv/media/generated/images/v100_2411_1208/03_букет_сухоцветов_в_крафт.jpg"
W4 = "/srv/media/projects/upscale-print/weights/4x-UltraSharp_basicsr.pth"
WESR = "/srv/media/projects/upscale-bench/RealESRGAN_x4plus.pth"
OUT = "/srv/media/projects/upscale-print"
os.makedirs(OUT, exist_ok=True)


def sharp(bgr):
    return round(float(np.std(cv2.Laplacian(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.CV_32F))), 1)


def delta_e(a, b, pts):
    la = cv2.cvtColor(a, cv2.COLOR_BGR2LAB).astype(np.float32)
    lb = cv2.cvtColor(b, cv2.COLOR_BGR2LAB).astype(np.float32)
    out = []
    for x, y in pts:
        pa, pb = la[y, x], lb[y, x]
        out.append(round(float(np.sqrt(((pa[0] - pb[0]) * 100 / 255) ** 2 +
                                       (pa[1] - pb[1]) ** 2 + (pa[2] - pb[2]) ** 2)), 1))
    return out


def run(name, weights, img):
    arch = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    up = RealESRGANer(scale=4, model_path=weights, model=arch, tile=0, tile_pad=10,
                      pre_pad=0, half=True, device=torch.device("cuda"))
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    out, _ = up.enhance(img, outscale=4)
    secs = round(time.time() - t0, 1)
    peak = round(torch.cuda.max_memory_allocated() / 2 ** 20)
    path = os.path.join(OUT, f"{name}.jpg")
    cv2.imwrite(path, out, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return out, {"метод": name, "секунд": secs, "VRAM_пик_МиБ": peak, "размер": f"{out.shape[1]}x{out.shape[0]}",
                 "резкость": sharp(out)}


def main():
    img = cv2.imread(SRC)
    print("исходник:", img.shape, "резкость", sharp(img), flush=True)
    h, w = img.shape[:2]
    pts_in = [(int(w * 0.5), int(h * 0.5)), (int(w * 0.35), int(h * 0.45)),
              (int(w * 0.65), int(h * 0.55)), (int(w * 0.5), int(h * 0.7)), (int(w * 0.5), int(h * 0.3))]
    rows = []
    for name, weights in (("esrgan_x4plus", WESR), ("4x_ultrasharp", W4)):
        out, meta = run(name, weights, img)
        back = cv2.resize(out, (w, h), interpolation=cv2.INTER_AREA)
        de = delta_e(img, back, pts_in)
        meta["dE_среднее"] = round(sum(de) / len(de), 1)
        meta["dE_максимум"] = max(de)
        meta["резкость_исходника"] = sharp(img)
        rows.append(meta)
        print(f"{name:16} {meta['секунд']:5} с | VRAM {meta['VRAM_пик_МиБ']:5} МиБ | "
              f"резкость {meta['резкость']:6} | ΔE {meta['dE_среднее']}", flush=True)

    json.dump(rows, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
