<!-- curated: do not overwrite -->
# A cuDNN 8 environment unblocked three tasks

_Three failures in a row — Real-ESRGAN, SDXL inpainting and CogVideoX — shared one cause: cuDNN 9 in the PyTorch 2.10 build cannot find an engine for fp16 convolutions on sm_70. A separate environment `venvs/cu121` was built: torch 2.3.1+cu121, cuDNN **8.9.2**, numpy 1.26, diffusers 0.31, transformers 4.46. All three tasks now run._

**Question.** Does a separate cuDNN 8 environment unblock Real-ESRGAN, SDXL inpainting and CogVideoX-480p on sm_70?

**Environment.** Tesla V100-SXM2 16 GB, sm_70, driver 580.178.04, Ubuntu 24.04. Environment venvs/cu121: torch 2.3.1+cu121, cuDNN 8.9.2 (8902), numpy 1.26, diffusers 0.31, transformers 4.46. Six promo images, three background-swap images, one 480x320x17 clip.

## 1. Real-ESRGAN (was: `GET was unable to find an engine`)

Six promo images, scheme "original 768 → downscale to 384 → back to 768", compared against the original:

| Metric | LANCZOS | Real-ESRGAN | Original |
|---|---|---|---|
| PSNR | **39.4 dB** | 33.5 dB | — |
| SSIM | **0.980** | 0.942 | — |
| Sharpness (Laplacian std) | 6.4 | **18.3** | 12.0 |
| Seconds per image | 0.01 | 0.78 | — |

This explains why neural upscaling "loses" on PSNR: it adds detail that was never in the original, so it deviates pixel-wise, but it restores sharpness **above the source** (18.3 versus 12.0), while LANCZOS halves it (6.4). For print that matters: LANCZOS gives smooth mush, ESRGAN gives texture. Peak VRAM 2 445 MiB.

## 2. SDXL inpainting (was: OOM or the same engine error)

Same background-replacement test, without the `cudnn.enabled=False` crutch:

| Image | Product SSIM | Background changed | Time |
|---|---|---|---|
| 8marta | 0.763 | 66.5 % | 40.1 s (first run) |
| biznes | 0.914 | 73.7 % | 7.8 s |
| dostavka | 0.836 | 90.4 % | 7.5 s |
| **average** | **0.838** | **76.9 %** | **7.8 s** |

Numbers match the earlier pass (0.833): disabling cuDNN had never been necessary.

## 3. CogVideoX-5B (was: would not start at all)

**480×320, 17 frames, 20 steps:**

| Metric | Value |
|---|---|
| Generation | 46 s |
| Per frame | 2.7 s |
| Peak VRAM | 11 119 MiB |
| Frames written | 17 |
| Frame sharpness, median | 272.2 |
| Inter-frame motion | 10.8 |
| Frozen frames | **0** |

The clip was written and the frames are alive: motion in every transition, even sharpness (minimum 231 of 272). First working video result on this card.

**720×480, 25 frames: OOM.** 1.32 GiB short on a VAE normalisation layer. So 720p is out of reach on 16 GB even with cuDNN 8 — it needs 24 GB, per-frame assembly, or VAE tiling that the pipeline does not provide.

## What changes

- Graphics on the V100 is no longer a dead end: ESRGAN, SDXL and video all run in `venvs/cu121`.
- The older `venvs/video` (torch 2.10, cuDNN 9) is kept for ACE-Step, which has its own requirements.
- Rule going forward: for any fp16 convolution on sm_70 use the cu121 environment; on `GET was unable to find an engine`, do not disable cuDNN — switch environments.

**Repeats.** single run per task; six images for the upscale, three for the swap.

**Verdict.** Switching to cuDNN 8 is the fix for fp16 convolutions on sm_70: all three tasks run, 480p video included; 720p still runs out of memory, so on this card the limit is memory, not the build.

**Result type.** Positive.

**Does not show.** Video is judged by frame sharpness and motion, not by eye; 720p with tiling, and fp16 models other than these three, were not tried.

**Raw.** `raw/runs/cudnn8-unblocks.log` - stdout of the harness described under Method.

## Method

Scripts `upscale_bench.py`, `bg_inpaint.py`, `video720.py`; logs `/srv/media/night/esrgan_cu121c.log`, `bg_cu121.log`, `video_cu121.log`, `video720_cu121.log`. Environment `/home/hermes/venvs/cu121` (torch 2.3.1+cu121, cuDNN 8902). A `torchvision.transforms.functional_tensor` shim was created because basicsr requires it on newer torchvision.

**Commands.** The command line was not recorded for this run.
