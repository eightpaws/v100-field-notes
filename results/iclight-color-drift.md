<!-- curated: do not overwrite -->
# IC-Light: light changes, product colour does not survive

Card V100-05. The question was whether an existing catalogue photo can be relit into a chosen scene while preserving the product: shape and hue. Shape holds, hue does not.

## Setup

The official IC-Light code (`lllyasviel/IC-Light`), model `iclight_sd15_fc`, Realistic Vision 5.1 base (SD1.5), 512 px, 30 steps, guidance 2.0, cu121 environment on a V100.

10 product cards from the library, three scenes: warm interior, cool studio, morning sun. Plus a separate run with neutral light: "even daylight, no colour cast, light grey seamless background".

Metric — ΔE (CIE76) at three points of the product: centre and two points to the sides.

## Results

| Scene | Mean ΔE | Max ΔE | Time per photo |
|---|---|---|---|
| warm interior | 40.3 | 65.9 | 1.9 s |
| cool studio | 32.4 | 58.7 | 1.9 s |
| morning sun | 33.6 | 61.2 | 1.9 s |
| **three scenes together** | **37.5** | **65.9** | **1.9 s** |
| neutral light | 24.1 | 41.5 | 2.0 s |

VRAM peak 7 132 MiB, model load about a minute.

The threshold for a printed product card is ΔE up to 5, for web up to 10. Even under neutral light we get 24.1, a shift any eye sees.

## Eyes-on review

Warm interior: the monstera is plausible, the wall beige-amber, light from the left, shadows to the right. But the leaves drift olive, the white pot turns golden-cream on the lit side, and surfaces look smooth and "plastic". Useless for a catalogue: the buyer cannot tell the real hue.

Neutral light shifts less (ΔE 24.1) but stays unstable: 8.4 on one bottle, 35.0 on the monstera. Behaviour varies card by card.

## Why

IC-Light does not transport illumination onto the original pixels — it repaints the frame, feeding the source as a condition into the UNet. Colour and texture therefore depend on the prompt and on what the model "remembers" about such a product. Shape holds well: pot, leaf count and composition match the original, with no seam artefacts.

## Verdict

Unsuitable for the catalogue: ΔE 24-37 against a threshold of 5-10. Fine for blog and social imagery: fast (2 s), light on memory (7 GiB), product shape preserved.

If different lighting is needed in a catalogue, the path is different: shoot the product in that light, or change only the background with the deterministic mask (method 3 in card V100-102), where the product stays bit-exact.

## What these numbers do not prove

- That ΔE cannot be lowered: guidance 2.0 and 30 steps were used in `fc` mode. The `fbc` mode with a product mask, where repainting is confined to the background, was not tried, and guidance was not tuned.
- That other bases are better or worse: only Realistic Vision 5.1 was tested.
- That ΔE at three points describes the whole product: it is a spot probe, not a difference map over the whole mask.

## Reproduction

```
ssh the GPU guest 'cd /srv/media/projects/iclight && HF_HOME=/srv/media/ai-cache/hf \
  /home/hermes/venvs/cu121/bin/python iclight_run.py'
```

Scripts: `iclight_run.py` (three scenes), `iclight_neutral.py` (neutral light). Logs `/srv/media/night/iclight*.log`, results in `out/result.json` and `out/neutral.json`.

**Repeats.** Not recorded: repeatability was not documented for this run - treat the numbers as a single run unless the result says otherwise.

**Environment.** Tesla V100-SXM2-16GB (sm_70), driver 580, CUDA 12.9, guest VM on a home Proxmox host; engine and model as recorded in the run log.

**Does not show.** one run only - repeatability was not measured; the run log was not preserved, so the numbers cannot be re-checked from this repository.

**Raw.** Not preserved for this run.

**Commands.** The command line was not recorded for this run.

**Question.** See the card title: the premise is stated in the field notes and was not carried into this export.

**Verdict.** Unsuitable for the catalogue: ΔE 24-37 against a threshold of 5-10.

**Result type.** Mixed.
