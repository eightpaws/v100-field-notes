"""Есть ли на карте занижение: fp16 с fp16-накоплением против fp32-накопления."""
import time

import torch


def bench(dtype, reduced, n=8192, iters=8):
    torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = reduced
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


print("GPU:", torch.cuda.get_device_name(0), "драйвер:", __import__("subprocess").run(
    ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
    capture_output=True, text=True).stdout.strip())
print("fp16, накопление fp16:", bench(torch.float16, True), "TFLOPS")
print("fp16, накопление fp32:", bench(torch.float16, False), "TFLOPS")
print("bf16 (всегда fp32):", bench(torch.bfloat16, False), "TFLOPS")
