"""Базовая линия 4060 Ti: fp16/bf16 матричное умножение и SDXL, без разблокировки."""
import time

import torch

torch.backends.cuda.matmul.allow_tf32 = True


def bench(dtype, n=8192, iters=8):
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
    tflops = 2 * n ** 3 * iters / secs / 1e12
    del a, b
    torch.cuda.empty_cache()
    return round(tflops, 1), round(secs / iters, 3)


def main():
    print("GPU:", torch.cuda.get_device_name(0))
    print("torch:", torch.__version__, "cuda:", torch.version.cuda)
    for dt, name in ((torch.float16, "fp16"), (torch.bfloat16, "bf16"), (torch.float32, "fp32")):
        tf, per = bench(dt)
        print(f"{name}: {tf} TFLOPS, {per} с на 8192^3")
    try:
        from diffusers import StableDiffusionXLPipeline
        import os
        cand = ["/d/hf-models/sdxl", "/d/models/sdxl"]
        base = next((c for c in cand if os.path.exists(c)), None)
        if base:
            pipe = StableDiffusionXLPipeline.from_pretrained(base, torch_dtype=torch.float16).to("cuda")
            pipe.set_progress_bar_config(disable=True)
            g = torch.Generator(device="cuda").manual_seed(1)
            t0 = time.time()
            pipe(prompt="a green monstera in a white pot", num_inference_steps=20,
                 height=768, width=768, generator=g)
            print("SDXL 768, 20 шагов:", round(time.time() - t0, 1), "с")
            t0 = time.time()
            pipe(prompt="a green monstera in a white pot", num_inference_steps=20,
                 height=768, width=768, generator=g)
            print("SDXL повтор:", round(time.time() - t0, 1), "с")
        else:
            print("модель SDXL локально не найдена:", cand)
    except Exception as e:
        print("SDXL не измерен:", str(e)[:120])
    print("VRAM пик МиБ:", round(torch.cuda.max_memory_allocated() / 2 ** 20))


if __name__ == "__main__":
    main()
