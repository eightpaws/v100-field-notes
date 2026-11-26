<!-- curated: do not overwrite -->
# Olala-v1.0-mini-7A1B on the V100: unblocked, but slow

Card V100-74, priority P0. The model was blocked by the engine: upstream llama.cpp answers `unknown model architecture: 'olala'`. Unblocked by building the fork, measurement taken. The card's criterion failed: 140 tok/s expected, 42 measured.

## What the model is

A Mamba3 and sparse-expert hybrid from OVHcloud, 6.78 B parameters, about 1 B active, Q5_K_M weight 5.57 GiB, Apache-2.0.

## What it took to load it

Upstream does not know the architecture. Support lives in the `OVHai-LLM/llama.cpp` fork, branch `olala-master` (commit bd20ca9, which already merges a CUDA quantised-precision fix).

Building for sm_70 required three local patches:

1. **UI assets**: the build died in `scripts/ui-assets.cmake` — the downloaded directory did not match the expected list. Worked around by skipping the `llama-ui-assets` target, which is not needed here.
2. **`ui.h`**: `server-http.cpp` includes a header generated together with the UI. A stub declaring `llama_ui_asset` and an empty `llama_ui_get_assets()` was added, otherwise `llama-cli` does not link at all.
3. **`-lllama-ui`**: the server part linked against a library that does not exist with the UI disabled. Replaced with an empty archive by absolute path.

Then the usual flags: `-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=70`, nvcc from CUDA 12.9, g++-12, `-j 4`. Build targets must be selected: `cmake --build build --target llama-bench llama-cli`; a full build stops at the server.

## Measurement

`llama-bench`, Q5_K_M, 2 repetitions:

| Mode | pp256 | tg64 |
|---|---|---|
| GPU, `-ngl 99` | **785.3 ± 7.5 tok/s** | **43.5 ± 0.3 tok/s** |
| CPU, `-ngl 0` | 81.5 tok/s | 21.6 tok/s |

Generation through `llama-cli`: prompt 522.7 tok/s, generation **42.4 tok/s**, and the code is correct:

```python
def is_palindrome(s):
    s = ''.join(ch.lower() for ch in s if ch != ' ')
    return s == s[::-1]
```

## Why the criterion failed

The card required tg ≥ 140 tok/s and pass@1 ≥ 0.55 on MBPP. At 42.4 against 140 — three times short — quality testing is moot per the card's own condition.

Separately: the model runs in thinking mode and spent about 600 tokens on reasoning before the code. With a 220-token limit only the reasoning comes out — production needs `-n 800` or more.

The speed is suspiciously low for 1 B active parameters: DeepSeek-Coder-V2-Lite reached 183 tok/s on the same card. The likely cause is that the fork's CUDA path for Mamba3 is unoptimised on sm_70, so decode is compute-bound rather than memory-bound. That is a hypothesis, not verified.

## What it means for the contour

The model does not enter the contour: slower than the dense 12B on the same coding tasks, and it needs a separate patched engine. Keeping it in the build makes no sense; the fork can be removed.

If the model is ever needed, test it on Ada (4060 Ti), where the fork has a separate quantised-precision path — speed there may differ.

## What these numbers do not prove

- That the model itself is slow: measured on one card with a fork whose sm_70 path may be unoptimised.
- That quality is lower: the code on a simple task is correct; MBPP was not run because the speed criterion already excluded the model.
- That q8 or fp16 are faster: only Q5_K_M was tested.

## Reproduction

```
ssh the GPU guest 'cd /srv/media/ai-cache/downloads/olala7a1b && \
  /home/hermes/llama-olala/build/bin/llama-bench -m Olala-v1.0-mini-7A1B-q5_k_m.gguf \
  -p 256 -n 64 -ngl 99 -r 2'
```

Fork: `/home/hermes/llama-olala` (branch olala-master, bd20ca9, with three local patches). Build logs `/srv/media/night/olala_*.log`.

**Repeats.** Not recorded: repeatability was not documented for this run - treat the numbers as a single run unless the result says otherwise.

**Environment.** Tesla V100-SXM2-16GB (sm_70), driver 580, CUDA 12.9, guest VM on a home Proxmox host; engine and model as recorded in the run log.

**Does not show.** one run only - repeatability was not measured; the run log was not preserved, so the numbers cannot be re-checked from this repository.

**Raw.** Not preserved for this run.

**Commands.** The command line was not recorded for this run.

**Question.** See the card title: the premise is stated in the field notes and was not carried into this export.

**Verdict.** Negative against the card's own bar: the model can be made to run on the fork, but the
throughput it reaches is far below the 140 tok/s criterion, so the MoE shape bought memory headroom
rather than speed.

**Result type.** Negative - the loading problem was solved, the performance criterion was not.
