<!-- curated: do not overwrite -->
# Card quality checker without a VLM — 11 663 images, 0.1 % printable

_Automatic quality control over our own image library using measurable signals instead of a vision model: resolution, sharpness, subject coverage, edge clipping, A4 print readiness._

**Question.** How much of the image library is printable as is, and which heuristic flags can be trusted?

**Environment.** Tesla V100-SXM2 16 GB, sm_70, driver 580.178.04, Ubuntu 24.04. 11 663 files under the generated-images library; Laplacian variance on a 512 px copy; coverage from corner colour with a threshold of 60 summed channels; A4 needs a 2480 px short side.

## What the full run showed

Processed **11 663** files from `/srv/media/generated/images`.

| Metric | Value |
|---|---|
| Print-ready for A4 (short side ≥ 2480) | **0.1 %** |
| Shorter than 768 px | 99.8 % |
| Soft (below the 10th percentile of sharpness) | 10.0 % |
| Median sharpness (Laplacian variance) | 202.5 |
| Files with at least one flag | 100 % |

By short side the library is almost entirely **640 px** — the factory default. Fine for screens, useless for print: 640 px on A4 is 65 dpi.

## Where the metric lies, and I admit it

The "product clipped" flag fired on 93.5 % of files. These are false positives: the images are close-ups of flowers that fill the frame by design and therefore touch the edges. A "more than 30 % of pixels on the border" rule does not fit this genre. Real clipping — a cut bud or petal — cannot be told apart from a dense composition at the border.

The "too small" flag is formal as well: it separates the factory's 640 px files from the handful of 1024 and 768 test files.

## What it means for the shop

1. **Printing from the library is impossible** — an x4 upscale is required (2560 on the short side = 250 dpi on A4, just enough) plus a second x2 step for A3 and larger.
2. **Sharpness is fine** — median 202; the tenth below 100 are the ones worth regenerating.
3. **Clipping must be checked differently**: on a product mask rather than frame edges. That needs segmentation or a VLM, and the card has neither.

## What is left of card V100-04

The visual defect controller — a VLM that looks at a card and says "bud is cut, background is dirty, wrong variety" — was not built: there is no vision model on the card and downloading 2–3 GB is expensive on this link right now. The heuristic checker works and produces the numbers above.

To finish it properly: download Qwen2.5-VL-3B (~2.5 GB) or InternVL2-2B, run it over 200 manually labelled images, and measure accuracy. Without labels any VLM judgement is an opinion, not a metric.

**Repeats.** single pass over the whole library.

**Verdict.** The library is not printable: 0.1 % reaches A4 and 99.8 % is under 768 px, so upscaling is mandatory; the clipping flag is unusable, with 93.5 % false positives on flower close-ups.

**Result type.** Negative.

**Does not show.** No vision model was run and no labelled set exists, so what a VLM would catch is unmeasured; the sharpness thresholds are not validated against human judgement.

**Raw.** `raw/runs/image-quality-checker.log` - stdout of the harness described under Method.

## Method

Script `/srv/media/projects/image-qa/image_qa.py`, result `quality.json` (first 2000 rows in detail, summary over all 11 663), log `/srv/media/night/image_qa.log`. Sharpness is Laplacian variance on a 512 px copy; coverage is the share of pixels differing from the corner colour by more than 60 summed over channels.
