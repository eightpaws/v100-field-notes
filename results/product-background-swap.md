<!-- curated: do not overwrite -->
# Background replacement with the product kept — SSIM 0.833, but details drift

_Whether product photos can get a new background without a reshoot. Local SDXL inpainting (`stable-diffusion-xl-1.0-inpainting-0.1`, already on disk in InvokeAI); the background mask was built from corner colour and edge connectivity, the product left outside the mask._

**Question.** Can SDXL inpainting replace a product background while keeping the exact plant?

**Environment.** Tesla V100-SXM2 16 GB, sm_70, driver 580.178.04, Ubuntu 24.04. SDXL inpainting 1.0, fp16-only weights, 512 px width with CPU offload. Pass 1: colour mask, strength 0.95. Pass 2: depth mask from Depth-Anything-V2-Small with ControlNet-depth, strength 0.80, conditioning scale 0.95. Three promo images.

## Results on three promo images

| Image | Product SSIM | Background changed | Time |
|---|---|---|---|
| 8marta | 0.770 | 63.2 % | 11.4 s |
| biznes | 0.904 | 66.8 % | 7.3 s |
| dostavka | 0.825 | 93.2 % | 7.0 s |
| **average** | **0.833** | **74.4 %** | **8.6 s** |

Peak VRAM 5 296 MiB at 512 px width with CPU offload.

## What that means in practice

The numbers look fine: background replaced across three quarters of the frame, product geometry held (SSIM 0.83). The eye says otherwise. Comparing the original and the result of "biznes": the bouquet is recognisable and the composition is unchanged, but **the flowers are redrawn** — different orchid centres, added golden buds, petals merged together. The model did not preserve the product; it painted a similar bouquet.

Fine for an advertising banner, not for a product card: the customer would get a variety that never ships.

## Why

The mask was built from colour and edge connectivity, so gaps between flowers fell inside the mask and the model painted its own content there. Strength 0.95 forces redrawing even outside the mask because edges are feathered.

What would actually preserve the product:
1. Background-only mask with no gaps — depth-based fill (Depth-Anything-V2-Small is already downloaded) or manual outlining.
2. Strength down to 0.7–0.8 plus ControlNet-depth instead of free regeneration.
3. Preservation measured on contours and petal colour patches, not whole-product SSIM — SSIM 0.9 hides redrawn details.

## How it was run

Script `/srv/media/projects/depth-bg/bg_inpaint.py`, output `result.json`, log `/srv/media/night/bg_inpaint6.log`. Two obstacles had to be worked around:

- **`GET was unable to find an engine`** on fp16 convolutions: cuDNN 9 in this PyTorch build finds no engine on sm_70. Fixed with `torch.backends.cudnn.enabled = False`, which raises VRAM use and forces `enable_model_cpu_offload()` plus 512 px width.
- **Local weights are fp16-only**: the files are `model.fp16.safetensors` and `diffusion_pytorch_model.fp16.safetensors`, so the pipeline must be loaded with `variant="fp16"`, otherwise diffusers looks for `model.safetensors` and fails.

## Limits

- Three images, one background prompt.
- SSIM is computed inside a crude product mask, so the figure is optimistic relative to what the eye sees.
- ControlNet-depth is downloaded but was not used in this series: the first question was whether the card can inpaint at all.

## Second pass - depth mask plus ControlNet-depth

The first result (SSIM 0.833) used a colour mask and free regeneration. The second pass builds the background mask from a depth map (Depth-Anything-V2-Small) and generates through SDXL ControlNet-inpaint with depth conditioning, strength 0.80, conditioning scale 0.95.

| Image | Product SSIM | Edge SSIM | Background changed | Time |
|---|---|---|---|---|
| 8marta | 0.800 | 0.557 | 47.4 % | 10.7 s |
| biznes | 0.952 | 0.884 | 83.2 % | 7.2 s |
| dostavka | 0.800 | 0.663 | 79.0 % | 6.7 s |
| **average** | **0.851** | **0.701** | **69.9 %** | **8.2 s** |

Peak VRAM 5 766 MiB.

**What it bought:** product SSIM rose from 0.833 to 0.851, a small gain. The edge metric is the honest one and shows the core problem: product contours still move (0.70), and badly on the hardest image (0.56). Best case is biznes at 0.952 / 0.884.

**Verdict:** ControlNet-depth helps but does not solve preservation of a specific plant. Product cards need a manual cutout composited over a generated background, or the admission that neural background replacement is for advertising material only.

Script `/srv/media/projects/depth-bg/bg_depth.py`, results `result_controlnet.json`, log `/srv/media/night/bg_depth3.log`.

**Repeats.** three images per pass, two passes, single run each.

**Verdict.** Backgrounds can be replaced, the product cannot: product SSIM reaches 0.851 with depth conditioning while contour SSIM stays at 0.701, and the eye confirms redrawn petals and centres. Product cards need a manual cutout over a generated background.

**Result type.** Mixed.

**Does not show.** Three images and one background prompt; the strength sweep and manual masks were not tried; SSIM inside a crude product mask is optimistic.

**Raw.** `raw/runs/product-background-swap.log` - stdout of the harness described under Method.
