<!-- curated: do not overwrite -->
# CogVideoX on V100: 480p runs to full clip length, 720x480 runs out of memory

_Second measurement of the same card. The first one, on cuDNN 9, ended with no clip at all; this one uses the cuDNN 8 environment built in V100-141 and produces real files with frame checks._

**Question.** Can CogVideoX-5B produce a 480p clip on a 16 GB V100, how long a clip fits, and does 720x480 fit at all?

**Environment.**

| Item | Value |
|---|---|
| GPU | Tesla V100-SXM2-16GB, sm_70 (compute capability 7.0) |
| Driver / OS | 580.178.04, Ubuntu 24.04, kernel 6.8.0-151 |
| Python venv | `/home/hermes/venvs/cu121`, python 3.12 |
| PyTorch | 2.3.1+cu121, CUDA 12.1 |
| cuDNN | 8.9.2 (8902, enabled) |
| diffusers / transformers | 0.31.0 / 4.49.0 |
| Weights | `/srv/media/ai-cache/models/cogvideox-5b`, fp16, 17 GB, `local_files_only=True` |

`diffusers` had to be raised from 0.29.2 to 0.31.0 for this run: `CogVideoXPipeline` appeared in 0.30, and on 0.29.2 the script dies with `ImportError: cannot import name 'CogVideoXPipeline'`. The install was `pip install --no-deps diffusers==0.31.0` so that torch and cuDNN stayed untouched.

**Commands.**

```
bash /root/bin/v100-run.sh V100-146 -- /home/hermes/venvs/cu121/bin/python3 -u /root/v146.py
```

Inside `/root/v146.py`, one process, three configurations in sequence:

```python
pipe = CogVideoXPipeline.from_pretrained(MODEL, torch_dtype=torch.float16, local_files_only=True)
pipe.enable_model_cpu_offload()
frames = pipe(prompt=PROMPT, height=H, width=W, num_frames=N,
              num_inference_steps=20, guidance_scale=6.0,
              generator=torch.Generator("cpu").manual_seed(11)).frames[0]
export_to_video(frames, path, fps=8)
```

Prompt: `A greenhouse shelf with blooming begonias, soft daylight, camera slowly pushing in, shallow depth of field`.

**Results.**

| Configuration | Generation | Per frame | Peak VRAM (allocated) | Frames on disk |
|---|---|---|---|---|
| 480x320, 17 frames | 45.2 s | 2.7 s | 11 119 MiB | 17 |
| 480x320, 49 frames | 110.1 s | 2.2 s | 12 281 MiB | 49 |
| 720x480, 25 frames | OOM after 139.6 s | - | 13.7 GiB in use | 0 |
| model load (cold, fp16 from disk) | 122 s | - | - | - |

Frame checks on the two produced clips: 480x320x17 has sharpness median 47.3, median inter-frame motion 4.3, 0 frozen frames; 480x320x49 has sharpness 42.9, motion 3.56, 0 frozen frames.

**Result.** 480p works, and it works to the model's full clip length: 49 frames in 110 s at 12 281 MiB peak, with every frame present on disk and none frozen. 720x480 does not fit: the run died on a 1.32 GiB allocation after 139.6 s, with 13.7 GiB already in use. Longer clips are cheaper per frame than short ones (2.2 versus 2.7 s per frame), because the 122 s model load and the fixed per-clip overhead are amortised over more frames.

**Repeats.** Single run per configuration, seed 11 fixed, 20 inference steps, `guidance_scale` 6.0. No repeats: each configuration costs minutes of the card and the question here is fit, not variance.

**Verdict.** Mixed: CogVideoX-5B does run on this card and produces full-length 480p clips at about 2.2-2.7 s per frame, but 720x480 is out of reach on 16 GB, and the earlier "does not run" verdict was a property of the cuDNN 9 build rather than of the GPU.

**Result type.** Mixed.

**Does not show.** The frames were not watched: sharpness and inter-frame motion are proxies, not a judgement of whether the clip looks right. Only one prompt was used, so text adherence is unmeasured. 720x480 was tried once, with CPU offload on and 20 steps; a smaller step count, a shorter clip or a different offload setting might fit and was not tried. `CogVideoXPipeline` in diffusers 0.31 still has no `enable_vae_slicing` or `enable_vae_tiling` (checked with `hasattr`), so memory could not be traded for time. No comparison against another video model on the same prompt exists.

**Raw.** `raw/runs/V100-146.json` - per-configuration timings, VRAM peaks and frame statistics as printed by the harness. Driver script `/root/v146.py`, run log `/root/runs/V100-146/run.log`. Clips: `v146_480x320_17f.mp4` (58 016 B) and `v146_480x320_49f.mp4` (155 310 B).

## History: why this card was blocked

The first attempt (22.11.2026) ran in the venv used for the image work, with torch 2.10 and cuDNN 9:

| Path | cuDNN | Outcome | Evidence |
|---|---|---|---|
| one | 9, enabled | no engine for fp16 convolution | `GET was unable to find an engine to execute this computation` |
| two | 9, disabled | out of memory in VAE decode | `Tried to allocate 17.80 GiB`, 8.83 GiB free |

The same root cause produced three failures at once: Real-ESRGAN, SDXL inpainting (worked around by disabling cuDNN plus CPU offload) and CogVideoX. The card was therefore parked as blocked, with the fix named as a cuDNN 8 environment. V100-141 built that environment and produced the first 480x320x17 clip in 46 s; this run extends it to the model's full clip length and to the resolution that does not fit. The old log is kept as `raw/runs/video-cogvideox.log`.
