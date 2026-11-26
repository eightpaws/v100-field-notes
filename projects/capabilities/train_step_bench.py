"""Задачный уровень: шаг обучения (forward+backward) в fp16 и bf16 - где карта выигрывает."""
import json

import torch

D_MODEL = 4096
BATCH, SEQ = 8, 1024
ITERS = 5


def step_bench(dtype):
    lin = torch.nn.Linear(D_MODEL, D_MODEL, bias=False).to("cuda", dtype=dtype)
    x = torch.randn(BATCH, SEQ, D_MODEL, device="cuda", dtype=dtype, requires_grad=False)
    target = torch.randn(BATCH, SEQ, D_MODEL, device="cuda", dtype=dtype)
    opt = torch.optim.SGD(lin.parameters(), lr=0.0)
    loss_fn = torch.nn.MSELoss()

    for _ in range(2):
        opt.zero_grad(set_to_none=True)
        loss_fn(lin(x), target).backward()
        opt.step()
    torch.cuda.synchronize()
    import time
    t0 = time.time()
    for _ in range(ITERS):
        opt.zero_grad(set_to_none=True)
        loss_fn(lin(x), target).backward()
        opt.step()
    torch.cuda.synchronize()
    secs = (time.time() - t0) / ITERS
    # три матричных умножения на слой (fwd, dW, dx), каждое 2*B*S*D*D флоп
    flops = 3 * 2 * BATCH * SEQ * D_MODEL * D_MODEL
    del lin, x, target
    torch.cuda.empty_cache()
    return round(secs * 1000, 1), round(flops / secs / 1e12, 2)


res = {"карта": torch.cuda.get_device_name(0),
       "cc": "sm_%d%d" % torch.cuda.get_device_capability(0)}
for label, dt in (("fp16", torch.float16), ("bf16", torch.bfloat16)):
    try:
        ms, tf = step_bench(dt)
        res[label] = {"мс_на_шаг": ms, "TFLOPS": tf}
    except Exception as e:
        res[label] = {"ошибка": str(e)[:70]}

print(json.dumps(res, ensure_ascii=False, indent=1))
