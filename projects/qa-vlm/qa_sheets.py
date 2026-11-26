#!/usr/bin/env python3
"""Собирает контактные листы: 24 карточки по 12 на лист, с номерами."""
import glob
import json
import os
import random

import cv2
import numpy as np

SRC = "/srv/media/generated/images/v100_2411_1208"
OUT = "/srv/media/projects/qa-vlm"
os.makedirs(OUT, exist_ok=True)

files = sorted(glob.glob(os.path.join(SRC, "*.jpg")))
random.Random(7).shuffle(files)
files = files[:24]

TILE = 320
COLS, ROWS = 4, 3
meta = []
for sheet in range(2):
    part = files[sheet * 12:(sheet + 1) * 12]
    canvas = np.full((ROWS * TILE, COLS * TILE, 3), 255, np.uint8)
    for i, f in enumerate(part):
        img = cv2.imread(f)
        if img is None:
            continue
        h, w = img.shape[:2]
        s = TILE / max(h, w)
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        r, c = divmod(i, COLS)
        y0, x0 = r * TILE, c * TILE
        canvas[y0:y0 + img.shape[0], x0:x0 + img.shape[1]] = img
        cv2.rectangle(canvas, (x0, y0), (x0 + TILE - 1, y0 + TILE - 1), (0, 0, 0), 2)
        cv2.putText(canvas, str(i + 1 + sheet * 12), (x0 + 8, y0 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        meta.append({"n": i + 1 + sheet * 12, "file": os.path.basename(f),
                     "px": f"{w}x{h}",
                     "sharpness": round(float(np.std(cv2.Laplacian(gray, cv2.CV_32F))), 1)})
    path = os.path.join(OUT, f"sheet{sheet + 1}.jpg")
    cv2.imwrite(path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("лист:", path)

json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("карточек:", len(meta))
