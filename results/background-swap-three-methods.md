<!-- curated: do not overwrite -->
# Background replacement: three methods, the deterministic one won

Card V100-102, hypothesis from a video: img2img with depth control swaps the background while preserving the product. Three methods were tested on five product cards from the library, all using the same depth mask (Depth-Anything-V2-Small).

## Method 1: img2img + ControlNet depth

RealVisXL V5 base, ControlNet depth SDXL small, denoise strength 0.45-0.75, 704 px.

| Strength | SSIM | background brightness | background spread | time |
|---|---|---|---|---|
| 0.45 | 0.861 | 146.3 | 20.5 | 2.5 s |
| 0.60 | 0.828 | 145.0 | 19.8 | 2.5 s |
| 0.75 | 0.798 | 143.4 | 18.3 | 2.9 s |

The background stays grey at every strength: ControlNet preserves the geometry of the whole scene, including the wall. Across five cards: mean SSIM 0.825, 2.1 s per card, 8 693 MiB peak.

**Verdict: the background does not change this way.** Light and small details can shift, the environment cannot.

## Method 2: inpainting with a background mask

The mask covers everything except the product, and the product is copied back from the original bit-exact. SDXL-inpainting, strength 0.95-0.99.

- the product covers 24-37 % of the frame, the rest is redrawn;
- mask edges are invisible, no halos;
- but background colour ignores the prompt: "pure white seamless background, #FFFFFF" yields a grey background at 142 ±33, with softboxes appearing at the edges;
- 4.1 s per card, 7 823 MiB peak.

**Verdict: the product is preserved perfectly, a white background is not guaranteed.** Diffusion pulls towards the "studio" imagery it was trained on.

## Method 3: deterministic white background

Same mask, no diffusion: the product is cut out with a 2 px soft edge and composited onto a #FFFFFF canvas.

- background exactly **255.0 ± 0.2** on all five cards;
- the product is never repainted;
- fractions of a second, almost no VRAM (only the depth model, on CPU).

**Key detail:** the depth mask cannot be used as-is. Holes remain inside the product where depth dips, and they cut leaf fragments with straight edges. Fixed by filling external contours: `findContours(RETR_EXTERNAL)` plus `drawContours(..., -1)` for contours larger than 0.2 % of the frame, then a 25 px close. After that no fragments are lost.

## Recommendation for the shop

- **White background for the catalogue** — method 3. Flat white, untouched product, seconds per card, no surprises.
- **Interior background** — method 2, but colour cannot be steered by prompt, it needs trial and eyes.
- **Change light and texture without changing the scene** — method 1 at strength 0.45.

## What these numbers do not prove

- The depth mask fails on transparent and thin subjects (glass, dried flowers); the sample contained none.
- Five cards is little for the whole catalogue, but the three methods gave consistently different results, and the difference is explained by how the methods work.
- The deterministic variant adds no shadows: a premium card needs a shadow drawn separately.

## Reproduction

```
ssh ai-gpu 'cd /srv/media/projects/depth-bg && HF_HOME=/srv/media/ai-cache/hf \
  /home/hermes/venvs/cu121/bin/python bg_white.py'
```

Scripts: `bg_controlnet.py`, `bg_sweep.py`, `bg_mask.py`, `bg_prompts.py`, `bg_white.py`. Logs `/srv/media/night/bg_{cn,sweep,mask,prompts,white}.log`, output in `/srv/media/projects/depth-bg/{cn,mask,white,prompts}/`.
