# Tesla V100 (sm_70) — measured results

Field notes from one **Tesla V100-SXM2 16 GB** running inside a Proxmox VM (24 vCPU, 96 GB RAM, driver 580).
Every number below was measured on the card, not copied from a project README. Negative results are
published on purpose: they are the expensive part of anyone's time.

Closed experiments: **9**.

## Test rig

| Component | Value |
|---|---|
| GPU | Tesla V100-SXM2 16 GB, compute capability 7.0 (sm_70) |
| Driver | 580.178.04 |
| Host | Proxmox VE VM — 24 vCPU (EPYC 7282), 94 GiB RAM, Ubuntu 24.04.5, kernel 6.8.0-151 |
| Python / torch | 3.12.3 · 2.5.1+cu121 (video venv) · 2.10.0+cu128 (music venv) |
| Ollama | KV cache q8_0, `NUM_PARALLEL=4`, `KEEP_ALIVE=30m`, `MAX_LOADED_MODELS=1` |

Every card states its rig, the commands that were run, whether the measurement was repeated, and ships the
raw numeric output in `raw/runs/`. Where a card says `single run`, it was measured once — no error bars are
implied and none are invented.

| Idea | What | Result |
|---|---|---|
| [V100-10](results/V100-10.md) | Prefill and batching: where V100 actually loses | prefill 1776 tok/s at `num_batch=2048` against 587 at 128 and 1351 at default 512 - ×3 to 128 and +31 % to 512, on 1k, 8k and 16k the best is exactly 2048. On 16 440 toke |
| [V100-16](results/V100-16.md) | Volta-fa patches for llama.cpp | Built llama.cpp with 4 of 8 patches (the rest did not apply - base-commit in the patches was not specified). Compared to Ollama: decode 70.65 against 65.8 tok/s (+7.4%),  |
| [V100-19](results/V100-19.md) | GQA→MHA: quiet fallback attention in ComfyUI | Confirmed: GQA silently falls back to the math path on sm_70: 4.63 TF/s compared to 33.15 for MHA (×7.2), on 8192 math tokens it consumes 8 GB and crashes due to OOM. Exp |
| [V100-02](results/V100-02.md) | KV cache q8_0 → context 32–64k | q8_0 KV does not hurt retrieval quality (needle 3/3 on 6496 tokens, as with fp16) and at 16k provides twice the generation speed - 44 against 21 tok/s, plus 2 GB of free  |
| [V100-11](results/V100-11.md) | System prompt KV cache | The prefix cache works in both llama.cpp and Ollama, but llama.cpp wins on tail editing. 2k prefix: cold 1047 ms, repeat 663 ms, tail edit 95 ms (recomputed 34 tokens). 6 |
| [V100-24](results/V100-24.md) | DRY-sampler and budget of reasoning | The DRY penalty did not reproduce on our model: on five regular tasks and two specifically designed to cycle (120 varieties of roses by numbers, 80 lines of log) the shar |
| [V100-36](results/V100-36.md) | Video without RAM ceiling: clip length and 720p | RAM was not the limit: process RSS of 41.6 GB at all lengths, VRAM 12.7-13.0 GB. 480p (20 steps): 97/145/193 frames ok - 176/283/416 sec; 241 and 321 - OOM. 720p without  |
| [V100-37](results/V100-37.md) | 32B dense and 30B MoE: re-measuring decode at 96 GB | The ceiling is at 16 GB of VRAM even with 96 GB RAM. Dense 32B Q4 (18.5 GB) model with 20 layers on GPU: prefill 253, decode 3.0 tok/s; at 40 and 99 layers llama-bench fa |
| [V100-39](results/V100-39.md) | TTFT and model loading with warm cache | A warm page cache changes the picture dramatically. llama.cpp: cold start 22.4 s, warm repeat 3.2 s - 7 times faster. Ollama 14B: after offloading the model, 18.2 s and p |

## How to read this

`tok/s` is generated tokens per second, `prefill` is prompt processing. Where a number depends on
conditions — cold vs warm start, KV cache type, batch size, VRAM headroom — the condition is stated in the
card, not hidden in a footnote. A card that says "not worth it" is a result, not a failure.

## Why publish the negative ones

Three of these cards kill popular advice: FlashAttention patches promised +34–45 % and delivered +7.4 %;
64k context does not fit a 14B model in 16 GB at any KV precision; a dense 32B model runs at 3 tok/s where a
30B MoE runs at 24.5 tok/s. Reproducing a disappointment costs hours — reading about it costs a minute.

## License

Text and results: CC BY 4.0 — reuse with attribution.
