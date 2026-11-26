<!-- curated: do not overwrite -->
# V100-06 - Upscaling for print: ESRGAN vs UltraSharp, SUPIR blocked by the channel

_Measured on a Tesla V100-SXM2 16 GB (sm_70) in a VM: driver 580.178.04, CUDA 12.9, 24 vCPU, 94 GiB RAM._

**Question.** Does a diffusion upscaler add real texture that a GAN cannot, and does that justify minutes
per frame? One 640x640 frame from the library was upscaled 4x to 2560 with two GAN models and inspected at
1:1; the diffusion path (SUPIR v0Q) was the second half of the test.

**Environment.** V100-SXM2-16GB (sm_70), driver 580.178.04. Two Python environments: `venvs/cu121`
(torch 2.3.1+cu121) for the upscalers, and the SUPIR workspace with `sgm`, `pytorch_lightning`,
`torchmetrics`, `k_diffusion`, `kornia 0.7.4`. Source frame: dried flowers in kraft paper - fine texture,
petals, hairs. Protocol: 4x upscale, time and peak VRAM, colour by delta-E (5 points, back to 640 with area
resampling), sharpness by Laplacian, plus a 1280 px 1:1 crop for visual inspection.

**Commands.**
```
python upscale_print.py            # Real-ESRGAN x4plus + 4x-UltraSharp, run dir /srv/media/projects/upscale-print
python supir_check2.py             # SUPIR v0Q, 25 steps, run dir /srv/media/projects/supir (not reached)
```

**Repeats.** single frame, single pass per method - the card asked for inspection, not for variance.

**Result.**

| Method | Time | Peak VRAM | Sharpness at 2560 | delta-E mean | delta-E max |
|---|---|---|---|---|---|
| LANCZOS (base) | 0,1 s | - | - | - | - |
| Real-ESRGAN x4plus | 0,9 s | 2 722 MiB | 5,5 | 3,9 | 6,1 |
| 4x-UltraSharp | 0,7 s | 2 722 MiB | 15,5 | 4,9 | 7,4 |

The source measured 22,5 on the same Laplacian; the sharpness values are comparable only within the "at
2560" column, because upscaling changes the noise scale. The card's colour threshold was delta-E <= 3 and
neither GAN passed (3,9 and 4,9), so even the mild upscaler cannot go to print without colour correction.

What the 1:1 crop shows: LANCZOS keeps no hairs and smears petals into patches. Real-ESRGAN gains contrast
and separates some petals, but leaves waxy regions, blotchiness and over-sharpened edges, and still does not
recover individual hairs - it predicts plausible texture rather than returning the real one. 4x-UltraSharp
is three times sharper, and that is exactly where generation traces appear: a blocky peach-and-white shape
that does not exist in the scene, white specks, brush strokes in the brown areas, scales turned into smears.

SUPIR did not run: 1,75 GB of the checkpoint is missing (5 329 810 432 bytes expected, 3 580 401 865 on disk

- a zip without a central directory, which torch refuses), and the channel could not deliver it. Hugging
Face served 4-5 KB/s with four parallel streams totalling 19 KB/s, the local proxy answered
`Network is unreachable`, and GitHub releases were throttled to 26 B/s, while Cloudflare on the same machine
gave 25,4 MB/s.

**Verdict.** Mixed. The GAN half is measured and inspected: Real-ESRGAN at 0,9 s per frame is acceptable for
A4 after colour correction but adds no real texture, while 4x-UltraSharp in this form is unusable for product
photos - the buyer would see details the product does not have. The diffusion half produced no number at all,
so the original question ("is a diffusion upscaler worth minutes per frame") is still open.

**Result type.** Mixed.

**Does not show.** Nothing about SUPIR: no image, no timing, no sharpness, no delta-E. Nothing about whether
0,7-0,9 s per frame holds for other frames, since tiling was off and the frame is small. Nothing about
delta-E 3,9 being the limit of ESRGAN - no colour correction was applied, it is measured as-is. And one
frame in one scene does not establish that UltraSharp always produces blocky artefacts.

**Raw.** `/srv/media/projects/upscale-print/result.json` (numbers), crops `crop_esr_1280.png`,
`crop_us_1280.png`, `crop_lanczos_1280.png`, logs `/srv/media/night/upscale_print7.log` and
`/srv/media/night/supir_run17.log`. The UltraSharp checkpoint had to be repacked first - it uses the old key
scheme (`model.0.*`, `model.1.sub.N.RDBj.convK.0`) while basicsr expects `conv_first.*`,
`body.N.rdbj.convK.*` - `repack2.py` translates one into the other.
