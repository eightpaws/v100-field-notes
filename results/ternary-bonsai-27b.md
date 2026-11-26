<!-- curated: do not overwrite -->
# Ternary-Bonsai-2-27B on the V100: 27B in 6.8 GB at 67 tok/s

Card V100-76, priority P0. The model was blocked by format: weights are packed as `PTQ1_0`, which stock llama.cpp does not know. The PrismML fork was built, the ternary kernels do run on sm_70, and this is the best size-to-memory result measured so far.

## The model

`Ternary-Bonsai-2-27B-PTQ1_0.gguf`: 26.9 B parameters, 1.75 bits per weight, 5.93 GB on disk, Apache-2.0, from PrismML.

## What it took

Stock llama.cpp — both the older build129 and a fresh master (28148b5) — cannot read the file: it fails at load because the `PTQ1_0` type is absent upstream.

The `PrismML-Eng/llama.cpp` fork, commit f702476, built for sm_70 with three patches (the same set needed for the olala fork):

1. Skip the UI asset target: early `return()` in `tools/ui/CMakeLists.txt` when the UI is off.
2. Stub `tools/server/ui.h` declaring `llama_ui_asset` and returning an empty `llama_ui_get_assets()`.
3. Replace `-lllama-ui` in `tools/server/CMakeLists.txt` with the absolute path of an empty archive.

Build targets must be explicit: `--target llama-bench` and `--target llama-server`. `llama-cli` does not build in this fork; the server is enough.

## Measurement

`llama-bench`, idle card (0 MiB before the run), 2 repetitions:

| Test | Result |
|---|---|
| pp256 | **814.3 ± 11.9 tok/s** |
| tg64 | **67.44 ± 0.11 tok/s** |

Through the server: 6.8 GB of VRAM for the whole model, 4k context, responses at 52-58 tok/s.

The key point: `-ngl 99`, every layer on the card, 6.8 GB out of 16. Had the ternary kernels fallen back to CPU, speed would be 3-5 tok/s — here it is 67, so the kernels execute on Volta.

## Quality

**Code.** `is_palindrome` ignoring case and whitespace, 350 tokens in 6.0 s, answer correct:

```python
def is_palindrome(s):
    cleaned = ''.join(ch.lower() for ch in s if not ch.isspace())
    return cleaned == cleaned[::-1]
```

**JSON.** A valid product card, all fields present, content on point (interior style, care as a checklist), 285 tokens in 5.0 s.

**Honesty.** On a delivery price question: "Не могу точно сказать без адреса и букета. Обычно — от 300–600 ₽." It did not invent a figure, flagged the uncertainty and gave only a general range — acceptable.

Thinking mode is on by default: 400-1200 characters of reasoning before the answer, so a token budget of 800 or more is required.

## Why it matters for the contour

| Model | Parameters | VRAM | tg |
|---|---|---|---|
| Ternary-Bonsai-2-27B | 26.9 B | **6.8 GB** | **67.4** |
| Qwen3-Coder-30B MoE Q4, `-ncmoe 8` | 30 B | 13.6 GB | 36.4 |
| Nemotron-Bolt-E4B | 7.5 B | 4.7 GB | 113 |
| DeepSeek-Coder-V2-Lite | 16 B | 8.5 GB | 183 |

A 27B model fits in 6.8 GB and runs twice as fast as the 30B MoE with expert offloading, leaving 9 GB for context. On a 16 GB card that is a different regime: a large model without `-ncmoe`, without layer offload, and without the prefill penalty (814 tok/s versus 738 for the MoE).

Limitation: coding quality was not measured properly (no MBPP), only three tasks. Ternary weights at 1.75 bits usually lose on precise reasoning — that must be measured before switching the contour.

## What these numbers do not prove

- That the model works for production coding: three tasks are not a sample, MBPP is needed.
- That quality matches a 27B in Q4: different quantisation, no comparison was run.
- That 67 tok/s holds at 16k context: measured at 4k, KV grows linearly.
- That the fork is stable: one benchmark run and three server requests.

## Reproduction

```
ssh ai-gpu 'cd /srv/media/ai-cache/downloads/bonsai27b && \
  /home/hermes/llama-prism/build/bin/llama-bench \
  -m Ternary-Bonsai-2-27B-PTQ1_0.gguf -p 256 -n 64 -ngl 99 -r 2'
```

Raw output: `/srv/media/projects/raw/runs/V100-76.json`. Fork: `/home/hermes/llama-prism` (f702476, with three patches). Logs `/srv/media/night/prism_*.log`, `/srv/media/night/bonsai_*.log`.
