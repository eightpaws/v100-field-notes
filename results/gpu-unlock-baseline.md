<!-- curated: do not overwrite -->
# GPU Unlock: baseline measured, unlock not installed

Card V100-104, hypothesis from a video: the GPU Unlock project removes the tensor-core cap on GeForce cards, and inference gets 24 % faster. The primary source was checked and a baseline was measured on our 4060 Ti.

## What the primary source says (not the video)

The project is `Zagitta/gpu-unlock`. It works **on Linux only**: a kernel module plus the `gpu_unlock.targets=all` kernel command line parameter. No driver patch and no vBIOS flash, so driver 617.14 stays untouched and a driver update does not undo it.

Card status per the README:

| Generation | Our cards | Status |
|---|---|---|
| Ampere (RTX 30) | — | stable, 100+ reports |
| Ada (RTX 40) | **4060 Ti 16 GB** | experimental |
| Turing (RTX 20) | — | experimental |
| Volta | **V100** | not supported |

For Windows the author points to a third-party port and warns to be "very careful" with installers.

Expected gains per the project: SDXL and other fp16 models +30-55 %, LLM prefill +25-55 %, fine-tuning +25-50 %, FlashAttention +50-60 %. Quantized GGUF in llama.cpp and ollama gain 0-15 %, token decode does not speed up at all, INT8/INT4/FP8 are unchanged. Outputs are bit-identical; only speed changes.

## Our measurement (no unlock)

Windows 11, RTX 4060 Ti 16 GB, driver 617.14, torch 2.11.0+cu128, 8192×8192 matmul, 8 iterations after warmup.

| Precision | TFLOPS | Time per matmul |
|---|---|---|
| fp16, fp16 accumulate | 38.8 | 0.028 s |
| fp16, fp32 accumulate | 40.1 | 0.027 s |
| bf16 (always fp32) | 40.3 | 0.027 s |
| fp32 without tensor cores | 19.6 | 0.056 s |

Key observation: bf16 gives 40.3 TFLOPS, exactly twice fp32 (19.6). In the project's published data an RTX 4070 Ti shows 81 TFLOPS before unlock against 40 TFLOPS fp32 — the same two-to-one ratio. After unlock it shows 150 TFLOPS, four times fp32.

So our card matches the "capped" profile: half of what is possible. If the unlock works, the reference is about 80 TFLOPS bf16 rather than 40.

Separately: fp16 with fp16 accumulation and with fp32 accumulation both land at 39-40 TFLOPS, confirming the limiter sits on the fp32-accumulate path rather than in our torch build.

## Why it was not installed

1. No official Windows support, only a third-party port with the author's own warning.
2. The 4060 Ti is "experimental": few reports, no documented rollback.
3. The card is production hardware: images, dictation, local models run on it. A brick or a blue screen stops the whole studio.

## Plan if we decide to go ahead

Safety here is better than it sounds: neither vBIOS nor driver is modified, everything lives in the kernel boot parameters.

1. Separate Linux install on a spare disk (or a persistent live image); Windows is not touched at all.
2. `git clone`, `make install`, add `gpu_unlock.targets=all` to the kernel command line.
3. Re-run the same benchmark: expect 40 → 75-85 TFLOPS bf16.
4. Measure SDXL: 20 steps at 768 px, compare with the Windows baseline.
5. Thirty minutes under load, watch temperatures and artefacts.
6. If the gain is under 15 % or artefacts appear, remove the boot parameter and everything reverts.

The comparison baseline is already captured by this run; scripts `pc_baseline.py` and `pc_cap.py` live in the home directory.

## What these numbers do not prove

- That our card is genuinely capped: the "twice fp32" ratio matches the published data, but there is no direct comparison against a professional card on the same die.
- That the SDXL gain will be 30-55 %: SDXL was not run locally (no model on disk), the figure comes from project reports.
- That the third-party Windows port is safe: untested, deliberately not installed.

## Verdict

Baseline captured, unlock not installed: there is no official path on Windows, and the risk to production hardware is not justified. If it is ever enabled, do it on a separate Linux install where the rollback is deleting one boot parameter.
