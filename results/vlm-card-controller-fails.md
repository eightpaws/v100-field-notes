<!-- curated: do not overwrite -->
# Card controller: Qwen2.5-VL-3B calls everything good

Card V100-142. The question was whether a VLM can replace the heuristic controller that produces 93.5 % false positives at the edges. Short answer: this VLM cannot; it does not distinguish defects at all.

## Setup

24 cards from the library, labelled by me against the criterion "product fully visible, large, no foreign objects, no artefacts": 18 good, 6 defective (cropped, too small, mushy, extra objects, artefacts).

Model Qwen2.5-VL-3B-Instruct, fp16, transformers 4.49, cu121 environment, V100.

Three runs:

1. **Contact sheet** of 12 cards in a 4×3 grid, 320 px per tile, red numbers.
2. **One card per prompt** at full resolution, answering "YES or NO, then the reason".
3. **Strict prompt**: answer exactly one word, `ok` or `brak`, on ten cards (4 good, 6 defective).

## Results

| Run | What the model said | Agreement with labels |
|---|---|---|
| contact sheet | 12 verdicts, every rejection labelled "too small" | 14 of 22 parsed (63.6 %) |
| one card per prompt | **"YES" for all 24** | 18 of 24 (75 %), only because good cards dominate |
| strict prompt | **"ok" for all 10**, including obvious defects | 4 of 10 |

Key numbers: on the contact sheet the model found **2 of 6** defects (recall 33 %) at **40 %** rejection precision (five rejections, two correct). In single-card mode it stopped rejecting entirely and echoed the task text instead of answering: "product fully visible, large, no foreign objects, no artefacts".

Timing: 1.8 s per card in single mode, 5.6 and 4.4 s per sheet of 12. VRAM peak 7 634 MiB, model load a few seconds.

## What it means

The problem is neither resolution nor pixel count — the full frame was supplied, not a thumbnail. The 3B model does not follow the one-word instruction and does not surface a defect it is not expecting. The 12-tile grid confuses it further: every rejection collapsed into "too small".

As a card controller this model is worse than the heuristic: the heuristic at least yields numbers and its false positives are visible, whereas here rejection disappears entirely and defects ship to the catalogue silently.

## What to do instead

1. **Heuristic plus thresholds**: sharpness, product coverage, margins at the edges — computed deterministically and spot-checked by eye. Edge false positives are fixed not by a model but by a product mask (the depth-based mask from card V100-102 is already available).
2. **If a VLM is required**, use 7-8B (Qwen2.5-VL-7B, InternVL2-8B) and always include 2-3 examples in the prompt: without examples the 3B showed complete failure to follow the format.
3. **Keep the labels**: 24 labelled cards, `meta.json` and the verdicts live in `/srv/media/projects/qa-vlm/`. Any future model can be compared on recall and precision against them.

## What these numbers do not prove

- That 7B will fail: only the 3B was tested.
- That the labels are ground truth: they are my own visual judgement, not an operator's; borderline cases are possible, but the six defects were checked individually and are obvious.
- That the VLM is useless everywhere: it remains usable for describing products and writing captions; the finding concerns defect acceptance only.

## Reproduction

```
ssh ai-gpu 'cd /srv/media/projects/qa-vlm && HF_HOME=/srv/media/ai-cache/hf \
  /home/hermes/venvs/cu121/bin/python qa_vlm_single.py'
```

Scripts: `qa_sheets.py`, `qa_vlm.py`, `qa_vlm_single.py`, `qa_vlm_strict.py`. Logs `/srv/media/night/qa_vlm*.log`.

**Repeats.** Not recorded: repeatability was not documented for this run - treat the numbers as a single run unless the result says otherwise.

**Environment.** Tesla V100-SXM2-16GB (sm_70), driver 580, CUDA 12.9, guest VM on a home Proxmox host; engine and model as recorded in the run log.

**Does not show.** one run only - repeatability was not measured; the run log was not preserved, so the numbers cannot be re-checked from this repository.

**Raw.** Not preserved for this run.

**Commands.** The command line was not recorded for this run.

**Question.** See the card title: the premise is stated in the field notes and was not carried into this export.
