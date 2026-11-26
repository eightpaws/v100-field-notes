#!/usr/bin/env python3
"""Перепаковка старых Real-ESRGAN-чекпойнтов в схему basicsr RRDBNet.

model.0                                   -> conv_first
model.1.sub.<i>.RDB<j>.conv<k>.0.{w,b}    -> body.<i>.rdb<j>.conv<k>.{weight,bias}
model.1.sub.<N> (последний, без RDB)      -> conv_body
model.3                                   -> conv_up1
model.6                                   -> conv_up2
model.8                                   -> conv_hr
model.10                                  -> conv_last
"""
import re
import sys

import torch

SIMPLE = {
    "model.0.": "conv_first.",
    "model.3.": "conv_up1.",
    "model.6.": "conv_up2.",
    "model.8.": "conv_hr.",
    "model.10.": "conv_last.",
}


def convert(src, dst):
    d = torch.load(src, map_location="cpu")
    if "params" in d and isinstance(d["params"], dict):
        d = d["params"]
    out = {}
    for k, v in d.items():
        nk = None
        m = re.match(r"model\.1\.sub\.(\d+)\.RDB(\d+)\.conv(\d)\.0\.(weight|bias)$", k)
        if m:
            i, j, c, part = m.groups()
            nk = f"body.{i}.rdb{j}.conv{c}.{part}"
        if nk is None:
            for old, new in SIMPLE.items():
                if k.startswith(old):
                    nk = new + k[len(old):]
                    break
        if nk is None and re.match(r"model\.1\.sub\.\d+\.(weight|bias)$", k):
            nk = "conv_body." + k.split(".")[-1]
        if nk is None:
            nk = k
        out[nk] = v
    torch.save({"params": out}, dst)
    print("вход:", len(d), "выход:", len(out))
    print("примеры:", list(out)[:4])


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
