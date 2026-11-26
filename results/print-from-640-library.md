<!-- curated: do not overwrite -->
# Printing from the 640 px library — x4 reaches A4, not A3

_Tested on real cards from the library rather than on synthetic images: take a 640 px file, upscale x4 with Real-ESRGAN (cuDNN 8 environment), then check dpi and sharpness._

## Result on six cards

| Card | Before | After | Sharpness before | ESRGAN | LANCZOS | A4 | A3 |
|---|---|---|---|---|---|---|---|
| monstera in ceramic (1936) | 640×640 | 2560×2560 | 11.3 | 4.2 | 1.5 | 310 dpi | 219 dpi |
| monstera (1288) | 640×640 | 2560×2560 | 10.4 | 3.6 | 1.5 | 310 | 219 |
| monstera (1160) | 640×640 | 2560×2560 | 9.5 | 4.4 | 1.3 | 310 | 219 |
| fern (1286) | 640×640 | 2560×2560 | 24.8 | 7.3 | 2.3 | 310 | 219 |
| ficus (433) | 640×640 | 2560×2560 | 15.0 | 4.9 | 1.7 | 310 | 219 |
| cactus (1845) | 640×640 | 2560×2560 | 19.6 | 6.6 | 2.0 | 310 | 219 |
| **average** | | | **15.1** | **5.2** | **1.7** | **310** | **219** |

0.7 s per card, peak VRAM 2 761 MiB.

## How to read the sharpness numbers

Absolute values are not comparable across resolutions: doubling the size halves Laplacian variance. The honest comparison is at one size — and there ESRGAN is **three times sharper** than LANCZOS (5.2 versus 1.7), meaning the upscale adds texture rather than mush.

## What it means for print

- **A4 is printable**: 2560 px across 210 mm = 310 dpi, above the 300 threshold.
- **A3 is not**: 2560 px across 297 mm = 219 dpi, visibly soft.
- A3 needs a second x2 step (5120 px, 438 dpi) or generation at a higher resolution. The second ESRGAN pass was not tested — that is a separate card.

## Practical pipeline

640 px original → ESRGAN x4 → 2560 px → A4 at 310 dpi. Under a second per card on the card, so the 11 000-file library can be processed in roughly two hours into print-ready A4 files.

Script `/srv/media/projects/print-check/print_check.py`, result `result.json`, log `/srv/media/night/print_check.log`. Produced files live in `/srv/media/projects/print-check/`.


## Second step for A3

A single x4 pass gives 2560 px, while A3 needs 4961. Two variants were compared on three cards: (a) stretch 2560 to 4961 with interpolation, (b) run a second ESRGAN x4 pass to 10240 and downscale to 4961.

| Card | Single pass with stretch | Two ESRGAN passes |
|---|---|---|
| fern | 2.41 | **4.94** |
| ficus | 1.81 | **3.40** |
| cactus | 2.24 | **4.25** |
| **average** | **2.15** | **4.20** |

At the same 4961 px output sharpness doubled (+95 %), which is 424 dpi on A3 — comfortably above the 300 threshold.

One important detail: the second pass without tiling runs out of memory (asks 12.5 GiB for one layer); with `tile=256` it completes by processing roughly a hundred tiles per card. Time per card is tens of seconds versus 0.7 s for the first pass, so A3 costs about a hundred times more time than A4.

Final print scheme: 640 px original → ESRGAN x4 (0.7 s) → A4 at 310 dpi; for A3 → second tiled pass → 4961 px at 424 dpi.
