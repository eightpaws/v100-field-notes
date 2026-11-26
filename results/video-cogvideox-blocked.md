<!-- curated: do not overwrite -->
# CogVideoX on V100 — blocked by the build, not by the model

_Testing video generation on the card: CogVideoX-5B is already on disk (17 GB). The goal was an actual clip plus frame checks, not just an exit code. No clip was produced, for the same reason on both paths._

**Question.** Can CogVideoX-5B produce a 480p and a 720p clip on a 16 GB V100 with cuDNN 9?

**Environment.** Tesla V100-SXM2 16 GB, sm_70, driver 580.178.04, Ubuntu 24.04. venvs/video with torch 2.10 and cuDNN 9; model cogvideox-5b from local disk; 480x320x17 frames, 20 steps, and 720x480x25.

## What happened

**Path one, cuDNN enabled (fp16):**
```
RuntimeError: GET was unable to find an engine to execute this computation
```
The same error that broke Real-ESRGAN and SDXL inpainting: cuDNN 9 in this PyTorch build finds no working engine for fp16 convolutions on sm_70.

**Path two, cuDNN disabled (the workaround):**
```
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 17.80 GiB.
GPU 0 has a total capacity of 15.77 GiB of which 8.83 GiB is free
```
Without cuDNN the convolution falls back to im2col and needs far more memory: VAE decoding at 480×320×17 frames asks for 17.8 GiB. At 720×480×25 it asked 10 GiB one layer earlier.

There is no VAE tiling in `CogVideoXPipeline`: `enable_vae_slicing` and `enable_vae_tiling` simply do not exist on the pipeline (checked with `hasattr`).

## What it means

Video on this V100 is unavailable, and the limit is the build rather than the model: cuDNN 9 with PyTorch 2.10 cannot run fp16 convolutions on sm_70, and without cuDNN memory runs out. The same root cause produced three failures in this session: Real-ESRGAN, SDXL inpainting (worked around by disabling cuDNN plus CPU offload) and CogVideoX.

Practical options:
1. Build a cuDNN 8 environment — all three likely start working.
2. Keep video on the 4060 Ti: cuDNN 9 is fine on Ada, but that machine needs its own torch venv.
3. Generate frames with SDXL and interpolate, skipping video models entirely.

## What remains unmeasured

The card asked for 720p with tiling and frame checks. There are no frames, so frame metrics (sharpness, motion, frozen frames) were not collected — the script computes them, but no file was produced. Once a working build exists, the run is a single command.

**Repeats.** single run per configuration; no successful clip to repeat.

**Verdict.** With cuDNN 9 video is blocked for a build reason, not a model limit: fp16 convolutions find no engine on sm_70, and without cuDNN the VAE asks 17.8 GiB. The fix is a cuDNN 8 environment, measured in V100-141, not a smaller clip.

**Result type.** Negative.

**Does not show.** No clip was produced, so frame metrics were never collected; 720p with tiling remains unmeasured.

**Raw.** `raw/runs/video-cogvideox.log` - stdout of the harness described under Method.

## Method

Script `/srv/media/projects/video-720/video720.py` (frame sharpness, inter-frame motion, writes mp4), logs `/srv/media/night/video720.log`, `video480.log`, `video480b.log`. Model `/srv/media/ai-cache/models/cogvideox-5b`, local, no downloads.

**Commands.** The command line was not recorded for this run.
