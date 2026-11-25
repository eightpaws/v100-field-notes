<!-- curated: do not overwrite -->
# Product pipeline — what our x4 actually buys, and how many dpi reach print

_Whether the existing image pipeline is good enough for print, and whether a neural upscaler is worth swapping in. The first question is answered with numbers; the second is not, and the reason matters._

## What was measured

Six promotional images (768×1344), each with an existing 4× file (3072×5376). The 4× file was compared against a plain LANCZOS upscale of the same original to the same size.

| Image | PSNR 4× vs LANCZOS | Sharpness 4× | Sharpness LANCZOS |
|---|---|---|---|
| 8marta | 35.8 dB | 3.3 | 1.5 |
| biznes | 34.6 dB | 5.6 | 1.7 |
| dostavka | 31.5 dB | 7.6 | 1.9 |
| osen | 34.7 dB | 4.4 | 1.6 |
| svadba | 38.9 dB | 2.4 | 1.2 |
| vesna | 39.3 dB | 2.5 | 1.0 |
| **average** | **35.8 dB** | **4.31** | **1.47** |

Conclusion: the 4× output is **not plain interpolation** — it carries three times the high-frequency energy of LANCZOS and differs from it by 35.8 dB, so something beyond stretching pixels (sharpening or a light upscaler) sits inside the pipeline. That is added crispness, not recovered structure.

## How much dpi is left for print

| Format | Needed at 300 dpi | What our 4× delivers | Usable |
|---|---|---|---|
| A4 | 2480×3508 | 460 dpi | yes, with margin |
| A3 | 3508×4961 | 325 dpi | yes, just enough |
| A2 | 4961×7016 | 230 dpi | no |
| 40×60 cm | 4724×7087 | 228 dpi | no |
| 60×90 cm | 7087×10630 | 152 dpi | no |

**A3 is the ceiling of the current pipeline.** Larger prints need a second upscale step. The 768×1344 original without 4× is screen-only (A4 at 115 dpi).

## What did not work, and why

**Real-ESRGAN did not run on this card.** Installation succeeded (`basicsr` needed a shim for the removed `torchvision.transforms.functional_tensor`; one was created), weights downloaded, but the first convolution raised:

```
RuntimeError: GET was unable to find an engine to execute this computation
```

Identical in fp16 and fp32: torch 2.10 with cuDNN 9 finds no suitable engine on sm_70. This is a build incompatibility, not a code error.

**Background replacement with depth (img2img + depth) was not attempted**: no depth model is on the card, and without one a product cannot be preserved while the background changes. It needs ControlNet-depth plus a "product preserved" metric via CLIP similarity.

**No brand LoRA was trained** — hours of training plus a dataset, and judging "better" needs a human looking at results.

## Next

1. A cuDNN 8 environment or a PyTorch build for sm_70, so Real-ESRGAN and SUPIR can be compared against the current 4× on PSNR/SSIM and time.
2. For prints above A3, a second 2× step with a sharpness check instead of plain stretching.
3. ControlNet-depth (~2.5 GB) plus a product-preservation metric — the next card.

**Does not show.** one run only - repeatability was not measured; the run log was not preserved, so the numbers cannot be re-checked from this repository.

**Raw.** Not preserved for this run.

**Environment.** Tesla V100-SXM2-16GB (sm_70), driver 580, CUDA 12.9, guest VM on a home Proxmox host; engine and model as recorded in the run log.

**Commands.** The command line was not recorded for this run.

**Question.** See the card title: the premise is stated in the field notes and was not carried into this export.

**Repeats.** Not recorded: repeatability was not documented for this run - treat the numbers as a single run unless the result says otherwise.
