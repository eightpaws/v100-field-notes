"""Возможности карты: fp16, bf16, fp8 - что реально считает тензорными ядрами."""
import json
import subprocess
import time

import torch


def matmul(dtype, n=8192, iters=8):
    a = torch.randn(n, n, device="cuda", dtype=dtype)
    b = torch.randn(n, n, device="cuda", dtype=dtype)
    for _ in range(3):
        a @ b
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(iters):
        a @ b
    torch.cuda.synchronize()
    secs = time.time() - t0
    del a, b
    torch.cuda.empty_cache()
    return round(2 * n ** 3 * iters / secs / 1e12, 1)


def main():
    name = torch.cuda.get_device_name(0)
    cc = torch.cuda.get_device_capability(0)
    drv = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    res = {"карта": name, "cc": f"sm_{cc[0]}{cc[1]}", "драйвер": drv,
           "torch": torch.__version__, "cuda": torch.version.cuda}

    for label, dt in (("fp16", torch.float16), ("bf16", torch.bfloat16)):
        try:
            res[label] = matmul(dt)
        except Exception as e:
            res[label] = f"ошибка: {str(e)[:60]}"

    for label, dt in (("fp8_e4m3", torch.float8_e4m3fn), ("fp8_e5m2", torch.float8_e5m2)):
        try:
            res[label] = matmul(dt, n=4096, iters=4)
        except Exception as e:
            res[label] = f"ошибка: {str(e)[:60]}"

    # поддерживается ли bf16 аппаратно: сравним с fp16
    try:
        res["bf16_к_fp16"] = round(res["bf16"] / res["fp16"], 2) if isinstance(res["bf16"], float) else None
    except Exception:
        res["bf16_к_fp16"] = None

    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
