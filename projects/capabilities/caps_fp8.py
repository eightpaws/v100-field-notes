"""FP8 отдельно: тензоры создаём в fp16 и приводим, умножение через _scaled_mm."""
import json
import subprocess

import torch


def try_fp8(n=4096, iters=4):
    out = {}
    a16 = torch.randn(n, n, device="cuda", dtype=torch.float16)
    b16 = torch.randn(n, n, device="cuda", dtype=torch.float16)
    for name, dt in (("e4m3", torch.float8_e4m3fn), ("e5m2", torch.float8_e5m2)):
        try:
            a = a16.to(dt)
            b = b16.to(dt)
            sa = torch.tensor([1.0], device="cuda")
            sb = torch.tensor([1.0], device="cuda")
            for _ in range(2):
                torch._scaled_mm(a, b.t(), scale_a=sa, scale_b=sb, out_dtype=torch.float16)
            torch.cuda.synchronize()
            import time
            t0 = time.time()
            for _ in range(iters):
                torch._scaled_mm(a, b.t(), scale_a=sa, scale_b=sb, out_dtype=torch.float16)
            torch.cuda.synchronize()
            secs = time.time() - t0
            out[name] = round(2 * n ** 3 * iters / secs / 1e12, 1)
        except Exception as e:
            out[name] = f"нет: {str(e)[:70]}"
    return out


res = {
    "карта": torch.cuda.get_device_name(0),
    "cc": "sm_%d%d" % torch.cuda.get_device_capability(0),
    "torch": torch.__version__,
    "fp8": try_fp8(),
}
print(json.dumps(res, ensure_ascii=False, indent=1))
