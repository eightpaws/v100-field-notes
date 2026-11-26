<!-- curated: do not overwrite -->
# Upscaling for print: ESRGAN vs UltraSharp, SUPIR blocked by network

Card V100-06, priority P4. The question was whether a diffusion upscaler adds real texture that a GAN cannot, and whether it justifies minutes per frame. The answer came out partial: the GAN side is measured and inspected by eye, the diffusion side hit the network.

## Setup

One 640x640 frame from the library — dried flowers in kraft paper, fine texture, petals, hairs. Card protocol: 4x upscale to 2560, time and peak VRAM, colour by ΔE (5 points, back to 640 with area resampling), sharpness by Laplacian, plus a 1:1 crop for visual inspection.

## Numbers

| Method | Time | Peak VRAM | Sharpness at 2560 | ΔE mean | ΔE max |
|---|---|---|---|---|---|
| LANCZOS (base) | 0.1 s | — | — | — | — |
| Real-ESRGAN x4plus | **0.9 s** | 2 722 MiB | 5.5 | **3.9** | 6.1 |
| 4x-UltraSharp | **0.7 s** | 2 722 MiB | **15.5** | 4.9 | 7.4 |

The source measured 22.5 on the same Laplacian — the numbers are only comparable within the "at 2560" row, because upscaling changes the noise scale.

The card's colour threshold was ΔE ≤ 3. Neither GAN passed: 3.9 and 4.9. Even "safe" upscaling shifts colour, so it cannot go to print without correction.

## What the eye sees (1:1 crop, 1280 px)

**LANCZOS**: no hairs, petals blur into patches, paper texture unreadable, soft edges, halos around contrasty stems. Detail is not restored, as expected.

**Real-ESRGAN**: contours got contrastier, some petals separated, but waxy smooth regions, blotchiness and over-sharpened boundaries appeared. Individual hairs are still not recovered — the model predicts plausible texture rather than returning the real one.

**4x-UltraSharp**: three times sharper, and that is exactly why generation traces show. In the centre-right of the crop there is a shapeless blocky peach-and-white shape that does not exist in the scene, plus a scatter of white specks and "brush strokes" in the brown areas; scales turned into smears. Halos around stems are obvious.

Verdict for this card: UltraSharp in this form is unusable for product photos — the buyer would see details the product does not have. Real-ESRGAN is milder and acceptable for A4 with colour correction, but it adds no real texture.

## SUPIR: not run, the channel

The diffusion side did not reach a result. What was done:

- repo cloned, environment built: torch 2.3.1+cu121 restored after a dependency install swapped in 2.15 and broke the import (`undefined symbol: ncclCommResume`);
- sgm, pytorch_lightning, torchmetrics, k_diffusion with its dependency chain, kornia 0.7.4 installed;
- CLIP encoders not downloaded at all: the bigG text encoder was extracted from the single-file SDXL checkpoint (695 M parameters, 1.39 GB), CLIP-L taken from the diffusers directory, and `sgm` patched to load it with `strict=False`;
- SDXL base 6.94 GB and `SUPIR-v0Q.ckpt` downloaded.

1.75 GB is missing: the full checkpoint is 5 329 810 432 bytes, on disk there are 3 580 401 865 — a zip without a central directory, which torch refuses (`PytorchStreamReader failed reading zip archive`).

Channel: Cloudflare serves 25.4 MB/s while HF serves **4-5 KB/s**; four parallel streams to HF total 19 KB/s. The VPS proxy (137.22.151.13:8888) is dead — `Network is unreachable`. GitHub releases are throttled too: 26 B/s. At those numbers the remainder is a day, not minutes.

What remains once the channel opens: one command, everything else is ready.

```
ssh ai-gpu 'cd /srv/media/projects/supir && \
  /home/hermes/venvs/cu121/bin/python supir_check2.py'
```

The script runs 25 sampler steps, saves `supir_v0Q.png` and prints time, peak memory, sharpness and ΔE — the same metrics as the table above.

## What these numbers do not prove

- That SUPIR will draw real texture — no run happened.
- That 0.7-0.9 s per frame holds for other frames: tiling was off and the frame is small.
- That ΔE 3.9 is ESRGAN's limit: no colour correction was applied, measured as-is.
- That UltraSharp always produces blocky artefacts: one frame, one scene.

## Reproduction

```
python upscale_print.py     # ESRGAN x4plus + 4x-UltraSharp, /srv/media/projects/upscale-print
```

UltraSharp weights had to be repacked: the checkpoint uses the old key scheme (`model.0.*`, `model.1.sub.N.RDBj.convK.0`), while basicsr expects `conv_first.*`, `body.N.rdbj.convK.*`. `repack2.py` translates one into the other; without it the load fails with `RuntimeError: Missing key(s) in state_dict`.

Raw numbers: `/srv/media/projects/upscale-print/result.json`. Crops: `crop_esr_1280.png`, `crop_us_1280.png`, `crop_lanczos_1280.png`. Logs: `/srv/media/night/upscale_print7.log`, `/srv/media/night/supir_run17.log`.
