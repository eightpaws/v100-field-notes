<!-- curated: do not overwrite -->
# Background replacement with the product kept — SSIM 0.833, but details drift

_Whether product photos can get a new background without a reshoot. Local SDXL inpainting (`stable-diffusion-xl-1.0-inpainting-0.1`, already on disk in InvokeAI); the background mask was built from corner colour and edge connectivity, the product left outside the mask._

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
