# Tesla V100 (sm_70) — measured results

Field notes from one **Tesla V100-SXM2 16 GB** running inside a Proxmox VM (24 vCPU, 94 GiB RAM).
Every number below was measured on the card, not copied from a project README. Negative results are
published on purpose: they are the expensive part of anyone's time.

Closed experiments: **76** — 13 positive, 9 mixed,
5 negative. Follow-ups queued: **13** — each card names the re-run that closes its caveat, and the results are published here as they land.

## Test rig

| Component | Value |
|---|---|
| GPU | Tesla V100-SXM2 16 GB, compute capability 7.0 (sm_70) |
| Driver | 580.178.04 |
| Host | Proxmox VE VM — 24 vCPU (EPYC 7282), 94 GiB RAM, Ubuntu 24.04.5, kernel 6.8.0-151 |
| Engines | Ollama 0.40.16 · llama.cpp built from source with `-DCMAKE_CUDA_ARCHITECTURES=70` |
| CUDA toolkit | driver 580.178.04 (supports up to CUDA 13.0) · builds on **12.9**, the last branch that still compiles sm_70 — CUDA 13 drops Volta entirely |
| Python / torch | 3.12.3 · 2.5.1+cu121 (video) · 2.10.0+cu128 (music) |

Every card states its rig, the commands that were run, whether the measurement was repeated, and ships the raw
numeric output in `raw/runs/`. Where a card says `single run`, it was measured once — no error bars are implied
and none are invented. Service flags changed between runs, so read the flags on the card instead of assuming
today's `systemctl show ollama` matches.

## Limitations of this dataset

Read this before quoting a number.

- **Most points are `n=1`.** Where something was repeated, the card says so and by what mechanism (for example
  `llama-bench -r 2` averages two runs internally). No card invents error bars, and a difference smaller than the
  stated spread is called noise.
- **Only some cards ship raw output.** Where the log was lost, the card says so in `Raw` and in `Does not show`
  instead of hiding it — those numbers survived in a hand-kept log, not in an archived file.
- **Engine-versus-engine comparisons are field comparisons.** Ollama against a patched llama.cpp build differs in
  more than the thing under test; those cards are labelled as such rather than presented as a controlled A/B.
- **Cards were measured hours apart and flags changed in between.** Cross-card comparisons are indicative; each
  card states the flags that affect its own result.
- **`Does not show` is part of the card.** Every card names what its numbers cannot support — the clean
  comparison it did not run, the quality check it did not do, the failure it could not explain.
- **Every caveat is queued, not parked.** Each `Follow-up` line names the re-run that closes the gap, so the
  disclaimers are work in progress rather than a permanent excuse.

| Idea | What | Result |
|---|---|---|
| [V100-10](results/V100-10.md) | Prefill and batching: where a V100 actually loses throughput | **Positive.** Set `num_batch=2048` explicitly on a V100 — it is ×3 over 128 and +31 % over the Ollama default, and the default is the main reason the card looks slow in off-the-shelf setups. The… |
| [V100-16](results/V100-16.md) | volta-fa patches for llama.cpp: measured, not promised | **Negative.** The promised +34–45 % is not there: +7.4 % on decode and +2.6 % on prefill, and most of that is FlashAttention itself (+8.7 % on decode), not the Volta patches. Moving off Ollama for 7 %… |
| [V100-19](results/V100-19.md) | GQA to MHA: the silent attention fallback that costs 7x | **Positive.** Check the attention path before blaming the pipeline: on sm_70 a GQA model can run 7x slower with no error message, and the same shape then OOMs at 8192 tokens. Expanding K/V to MHA… |
| [V100-27](results/V100-27.md) | volta-forever: running CUDA 13 binaries on a V100 | **Mixed.** The layer does what it says at the compatibility level: it runs code compiled without Volta, and it is worth keeping for exactly one situation — software released only for CUDA 13 with… |
| [V100-12](results/V100-12.md) | 1Cat-vLLM: a modern serving stack that still builds for sm_70 | **Mixed.** The fork runs: a real modern serving stack on Volta, roughly a quarter behind llama.cpp on 7B GGUF, with an OpenAI API and batching model that llama.cpp does not give you. Two pitfalls… |
| [V100-02](results/V100-02.md) | q8_0 KV cache: how much context a 14B model gets in 16 GB | **Mixed.** Keep `q8_0` KV with FlashAttention on, and treat 32k as the practical ceiling for a 14B model on a 16 GB card. 64k does not fit at any KV precision, so the "64k on a V100" advice is… |
| [V100-11](results/V100-11.md) | System-prompt KV cache: prefix reuse in llama-server vs Ollama | **Positive.** Enable the prefix cache in `llama-server` — it is the cheap win, and it is the only one of the two that survives a tail edit (95 ms instead of re-prefilling 1697 tokens). Ollama reuses… |
| [V100-24](results/V100-24.md) | DRY sampler and reasoning budget: a negative result | **Negative.** The DRY penalty did not reproduce here: qwen2.5-coder-14b does not loop on Russian tasks at `temperature=0`, so there is nothing for it to fix, and it costs about 3 % of decode speed.… |
| [V100-36](results/V100-36.md) | Video without the RAM ceiling: clip length and 720p | **Mixed.** RAM was never the ceiling: process RSS sat at 41.6 GB across every clip length while VRAM moved 12.7→13.0 GB. The wall is the 16 GB card. Without tricks: 12 s at 480p, or 6 s at 720p… |
| [V100-37](results/V100-37.md) | 32B dense vs 30B MoE: decode re-measured with 96 GB RAM | **Negative.** The ceiling is the 16 GB card, not system RAM: 96 GB does not let a dense 32B model run at a usable speed (3.0 tok/s at 20 layers, refuses to load above that). Among large models only… |
| [V100-39](results/V100-39.md) | TTFT and model loading with a warm page cache | **Positive.** A warm page cache changes the picture by an order of magnitude: 22.4 s cold against 3.2 s warm for llama.cpp, and 0.197 s for the repeated Ollama call with the whole prefix coming from… |
| [V100-15](results/V100-15.md) | Stack snapshot: how long sm_70 stays supportable | **Positive.** Freeze the stack and keep the wheels on disk — the failure mode here is silent, and after CUDA 13 / PyTorch 2.15 the only way back is a source build. Rule for this card: update nothing… |
| [V100-01](results/V100-01.md) | Speculative decoding in llama.cpp | Speculative decoding was tested on two targets, and the result depends on the model pair: it accelerates on 7B, but slows down almost twofold on 14B. llama.cpp master 51831d4, CUDA 12.9,… |
| [V100-03](results/V100-03.md) | imatrix Q4_K under Russian chassis | - **Environment Status (configuration, 23.11.2026 21:13).** The llama.cpp build in `~/llama-new` was killed by a VM reboot at 20:48, and was rebuilt on **CUDA 12.9**: `BUILD_OK` in **7… |
| [V100-105](results/V100-105.md) | Polyglot: eight languages on one harness | 6 languages (Python, JavaScript, PHP, Ruby, Go, Java) x 10 functions x 21 statements per language, three models, temperature 0, one run 3m 4s. Qwen2.5-Coder-7B Q8 - 6/6 languages (all… |
| [V100-106](results/V100-106.md) | Linters as acceptance: how much code passes on the first try | (25.11.2026) 40 tasks MBPP, Qwen2.5-Coder-7B-Instruct Q8_0. Tests pass 24 out of 40 (0.60). Linters: `ruff --select E,F` clean in 39 files out of 40 (one note for the whole sample),… |
| [V100-108](results/V100-108.md) | Tests that catch: mutation testing of generated tests | 10 commits with 5 planted defects each (boundary, null, race, injection, leak), Qwen2.5-Coder-7B Q8_0, 16 seconds total. Found 17 out of 50 (34%), false 0 on commit. Completely failed… |
| [V100-110](results/V100-110.md) | Red test cycle → repair on four languages | 20 tasks (5 each in Python, JavaScript, C, Perl), Qwen2.5-Coder-7B-Instruct Q8_0, `llama-server` build129, temperature 0; total set - 25s, server up in 2s. Successfully fixed 18 out of… |
| [V100-111](results/V100-111.md) | Review diff: five planted bugs, accuracy and completeness | 10 commits with 5 planted defects each (boundary, null, race, injection, leak), Qwen2.5-Coder-7B Q8_0, 16 seconds total. Found 17 out of 50 (34%), false positives 0 per commit.… |
| [V100-112](results/V100-112.md) | Refactoring with green tests | Refactoring Tasks: 10 tasks, 2-3 files each (helper code extraction, global renaming, deduplication, signature change, constant extraction, module separation, dead parameter removal,… |
| [V100-113](results/V100-113.md) | Schema, migrations, and queries against SQLite | 20 tasks on SQLite (schema, migration, 3 queries to each), Qwen2.5-Coder-7B Q8_0, two runs of 37s each. Completely correct 7 and 9 tasks out of 20 with a criterion of 15, queries correct… |
| [V100-114](results/V100-114.md) | Frontend: page with form, checking Playwright | Qwen2.5-Coder-7B-Instruct generated 10 pages of one specification in 109 seconds (9.7-12.4 seconds per page, 3.2-5.0 thousand symbols). Playwright scenario (desktop 1280, mobile 390,… |
| [V100-116](results/V100-116.md) | What a generated project still needs before delivery | **Mixed.** Deliverable, but only what was asked for: the model emitted a Dockerfile and a LICENSE exactly where the prompt named them and skipped them where it did not. The delivery checklist… |
| [V100-118](results/V100-118.md) | Conveyor spec → plan → code → tests → review against one prompt | Same 7B Q4_K_M, 10 MBPP tasks, temperature 0: one prompt 7/10 (0.70), pipeline spec-code-tests-reviews 6/10 (0.60) - difference **-10 points**. Pipeline takes **12 times longer** (6.1s… |
| [V100-13](results/V100-13.md) | AWQ/int4 vs GGUF Q4 on Volta | AWQ/int4 via vLLM 1.5.4: model loaded (14287 MiB VRAM), decode **117 tok/s** (114.2 / 116.9 after warm-up, first request 66.5), code is correct. Against GGUF Q4_K_M in llama.cpp: 132… |
| [V100-14](results/V100-14.md) | 24B in 16 GB: Mistral-Small-3.1-24B AWQ | Mistral Small 24B AWQ does not fit in 16 GB via vLLM. The model is fully downloaded (3 shards, 13.4 GB, all tensors are read), 1Cat-vLLM 1.5.4 compiled for sm_70 and has separate… |
| [V100-17](results/V100-17.md) | LMDeploy TurboMind: AWQ without forks | Partial: TurboMind works on sm_70 but loses quality in 4-bit. Speed: decode 131.2 tok/s (n=3, stdev 0.13), prefill 4266 tok/s at 751 token, VRAM 14.8 GiB, warm-up 50s. Quality: MBPP… |
| [V100-18](results/V100-18.md) | xllama.cpp: compress KV instead of q8 | Compressed KV in xllama.cpp works, but on long context it becomes too slow. Built with xllama.cpp f9287a9 (fork of llama.cpp from April 2026 with… |
| [V100-20](results/V100-20.md) | fni8: int8 dp4a for DiT | Rejected along with V100-22: this is the same fni8 package family (int8 dp4a for DiT in ComfyUI). The author himself writes that acceleration was measured on a CMP 100-210 park with… |
| [V100-21](results/V100-21.md) | Tachyon, Ninfer, Lapilli | Tachyon-v100 is being built and run on our card, but our models do not support it. Verified step by step. Build (Rust + nvcc), three pitfalls: 1. build.rs looks for the compiler strictly… |
| [V100-22](results/V100-22.md) | fni8 for LLM: int8 dp4a instead of tensor cores | Rejected based on the author's documentation facts. fni8 (jajmangold/fni8, ComfyUI-fni8 package) is an int8 dp4a path through CUDA kernels, and it is designed for cards with… |
| [V100-25](results/V100-25.md) | CUDA graphs for musical pipeline | Capture of CUDA graphs for ACE-Step 1.5 won't yield significant gain. Measurements via music studio API on xl-sft with LM 1.7B: | Duration | Steps | Seconds | |---|---|---| | 30s | 8 |… |
| [V100-26](results/V100-26.md) | llama.cpp build flags matrix for Volta | The build flag matrix was previously verified (CUDA 12.0, llama.cpp build b7743fbfd8, model 14B Q4_K, llama-bench pp512/tg128, median of three runs). Result: none of the flags… |
| [V100-28](results/V100-28.md) | V100-LLM: ready presets for 16 GB | Rejected: the release does not include the engine. Checked GitHub API for the Abdelhayali/V100-LLM repository, tag v1.3.0 - two assets: `LocalAI-Bridge-Desktop.exe` (8 MB) and… |
| [V100-29](results/V100-29.md) | V100-29 | **Positive.** The first configuration that puts a 27B dense model fully on the card and still decodes faster than the 30B MoE with CPU offload. Stock llama.cpp cannot read the PXQN4 file — the PXA… |
| [V100-30](results/V100-30.md) | sm70-attn: FA2-D256 in llama.cpp | Rejected based on the card criterion: "do we have a model with head_dim 256 and do we need context over 64k". The answer is no and no. What was actually checked: - We don't have models… |
| [V100-32](results/V100-32.md) | Prepared sm_70-weights with Hugging Face | NInfer-V100 1.7.2 unpacks and runs: three binaries of 421-424 MB (ninfer, ninfer-serve, ninfer-perplexity), no missing libraries, help opens. But it has nothing to work with. The engine… |
| [V100-40](results/V100-40.md) | V100-40 | **Negative.** The advertised 2.2x does not reproduce: prefill on the fork is about half of upstream (843–890 vs 1638–1779 tok/s) and decode is only 4% better with flash attention (73.53 vs 70.92). On… |
| [V100-41](results/V100-41.md) | V100-41 | **Mixed.** Usable only with flash attention on and 4 expert layers pushed to CPU: 24 tok/s decode. Both faster coding candidates (DeepSeek-Coder-V2-Lite at 183 tok/s, Qwen3-Coder-30B at 75 tok/s)… |
| [V100-42](results/V100-42.md) | V100-42 | **Positive.** Yes: 8 expert layers on CPU is the entry threshold, and every extra layer costs both prefill and decode roughly linearly. At 8 layers a 17.3 GB model — 1.3 GB larger than the card —… |
| [V100-43](results/V100-43.md) | V100-43 | **Positive.** Prefix caching works and is the main reason to run llama-server for agent workloads: prompt processing drops from 845 ms to 89 ms (9.5x), round trip from 1.18 s to 0.39 s. |
| [V100-44](results/V100-44.md) | NVFP4 on sm_70: 4-bit float in 16 GB | Works on sm_70. vLLM 1.5.4 (`--quantization modelopt_fp4`) boosted Ornith-1.5-9B-NVFP4 on V100: 14 133 MiB VRAM, decode **86.7-86.8 tok/s** (first request 83.0), code is correct.… |
| [V100-45](results/V100-45.md) | V100-45 | **Positive.** Working configuration is `-ngl 99 -ncmoe 8 -c 4096`. An 8192-token context needs more VRAM (compute buffer allocation fails), so long files require either 12 CPU layers or a smaller context. |
| [V100-46](results/V100-46.md) | V100-46 | **Positive.** Tool calling works correctly with the Qwen3-Coder chat template: valid JSON arguments, no extra calls, correct final answer. At 75 tok/s decode a conversational turn costs 2–3 s. |
| [V100-47](results/V100-47.md) | V100-47 | **Positive.** Best decode measured on this card by a wide margin: 183.6 tok/s with 2250 tok/s prefill, working configuration `-ngl 99 -fa 0`. Flash attention must be off — it is 160x slower on this… |
| [V100-48](results/V100-48.md) | V100-48 | **Mixed.** FIM works and is fast enough to type ahead of a human. Latency is unstable (126 ms to 1.5 s on the same prompt) — the old build's slot handling is the suspect; a single slot with… |
| [V100-49](results/V100-49.md) | V100-49 | **Positive.** Ranking is correct with a clear margin, and the 606 MB model handles a Russian query against English code without translation. Indexing a repository is a matter of minutes on this card. |
| [V100-50](results/V100-50.md) | V100-50 | **Negative.** Not reproducible. The first run on build 51831d4 showed +21% on a 7B target, but on master af5c583 with the same pair the gain is gone: base 105.5 / 111.9 / 113.0 tok/s versus 102.6 /… |
| [V100-51](results/V100-51.md) | V100-51 | **Mixed.** 32k is reachable only with compressed KV plus offloaded experts: `-c 32768 -ctk q8_0 -ctv q8_0 -ncmoe 16` gives 25 tok/s. Without compression the same window needs 24+ CPU layers and… |
| [V100-52](results/V100-52.md) | V100-52 | **Positive.** The loop closes locally in 15 seconds per iteration, which makes unattended refactoring and test-fixing practical. A dense 32B on the same card would run at 3 tok/s and be unusable for this. |
| [V100-53](results/V100-53.md) | Cache prefix: equal comparison with equal prompt length | Cache prefix is real and not an artifact of length.** Control with equal prompt length (8737 tokens in all three requests), llama-server with `--cache-reuse 256`, 7B Q4: | Request |… |
| [V100-54](results/V100-54.md) | Volt-forever: Honest native base with included cuDNN | Partial: cuDNN-on is not available on our stack. torch 2.10.0+cu128 with cuDNN 9 on convolution reports `GET was unable to find an engine to execute this computation`, cuDNN version is… |
| [V100-55](results/V100-55.md) | Llama-Bench refuses to load more than 20 layers. | There is no limit of 20 layers.** The matrix is based on Qwen3-Coder-30B (17.28 GiB), f16 KV, p128/n16: | ncmoe | prefill pp128 | decode tg16 | |---|---|---| | 24 | 179.2 | 39.2 | | 32 |… |
| [V100-56](results/V100-56.md) | 32kB Q8_0 and check Q4_0 at 64k | 32k and 64k are achievable, decoding is unaffected.** Qwen2.5-Coder-7B Q4 (4.36 GiB), FA enabled: | Context | KV | Prefill | Decode | |---|---|---|---| | 32,768 | q8_0 | **1860 tok/s** |… |
| [V100-57](results/V100-57.md) | Q8_0 KV: Confirm double decoding or attribute to noise | No double acceleration: compressed KV is slightly slower.** Qwen2.5-Coder-7B Q4 (4,36 GiB), p512/n128, r=2: | KV | FA | prefill pp512 | decode tg128 | |---|---|---|---| | f16 | off |… |
| [V100-58](results/V100-58.md) | Throughput, batching, quality | Under load, 1Cat-vLLM outperforms llama.cpp by six times.** 7B GGUF, `--max-model-len 4096`, `--gpu-memory-utilization 0.6`, different prompts for all requests (otherwise prefix cache… |
| [V100-62](results/V100-62.md) | 720p with VAE tiling: check the frames, not the exit code | **Mixed.** 720p with VAE tiling is viable — no tile seams at 1280×704 / 97 frames on 13.55 GiB. The weak point is not tiling but overall softness and blown highlights at 30 steps with the 5B model;… |
| [V100-63](results/V100-63.md) | Loading model: detach from start harness | Model loading and harness start are separated.** Measured on this card: | Engine | Model | Start to first token | |---|---|---| | llama.cpp master | 7B Q4 | 3.5-4.2 s | | llama.cpp… |
| [V100-65](results/V100-65.md) | Recheck 8k and 16k and set num\_batch to 4096 | Prefill decays smoothly, but 30B can't handle 8k at ncmoe 8.** Measurements llama-bench, n=0, r=1: | Model | pp2048 | pp8192 | pp16384 | |---|---|---|---| | DeepSeek-Coder-V2-Lite 16B,… |
| [V100-66](results/V100-66.md) | Quality over speed: MBPP on three models | Harness run of `model_eval.py`, one server ascent, 40 MBPP tasks + 8 blocks. DeepSeek-Coder-V2-Lite 16B (Q4_K_M, -fa 0, ctx 16k):** pass@1 **0.55** (22 out of 40), format 4/5, RAG 2/2,… |
| [V100-67](results/V100-67.md) | 16 GB: Q4_K_M - 128 bits, Q5_K_M - 160 bits, Q6_K - 256 bits, Q8 - 320 bits | Q5_K_M outperforms Q4_K_M in quality with a slight speed loss.** | Quant | Size | VRAM | Prefill pp128 | Decode tg32 | MBPP pass@1 | |---|---|---|---|---|---| | Q4_K_M | 4.68 GB | ~5 GB… |
| [V100-68](results/V100-68.md) | Speculation on 30B MoE: Draft 0.5B vs Qwen3-Coder | Speculation on 30B is not profitable.** With a draft of 0.5B, the model had to be raised from `-ncmoe 12` instead of 8 (draft subtracts VRAM): base in these conditions **36.0 / 32.6 /… |
| [V100-69](results/V100-69.md) | Special dec without second model | N-grams in file editing don't provide anything, draft hurts.** Prompt 200 lines of source code, model appends function based on pattern: base **71.5 / 106.3 / 106.4 tok/s**,… |
| [V100-70](results/V100-70.md) | Re-rank surface search by code | The reranker works and separates trash confidently.** bge-reranker-v2-m3 (568M, fp16) took **6.9 s** to launch on V100 and used **1092 MiB** VRAM - fits alongside working LLM, no need to… |
| [V100-71](results/V100-71.md) | The cost of 1M tokens on your own hardware is | Cost of 1M output tokens on own hardware.** Power consumption measured via `nvidia-smi power.draw`: idle **20.7-46.6 W**, under load (7B, 65% utilization) **159.0 W**, peak rated 300 W.… |
| [V100-72](results/V100-72.md) | Agent with four tools and an error on the first call | 1 of 3 scenarios.** Three tasks, four tools, the first call `get_time` was intentionally broken (server responded with `unknown argument 'location'; the only valid argument is 'city'`.… |
| [V100-73](results/V100-73.md) | Goods cards per hour: image generation throughput | On a 768 px card, it yields ~2100 images per hour, but on 1024 px it hits memory.** Tested on DreamShaperXL-Turbo (6 steps, guidance 1.5, fp16) via diffusers, local single-file… |
| [V100-74](results/V100-74.md) | Olala-v1.0-mini-7A1B: MoE with 1B active on 16 GB | Blocked by engine (24.11).** File downloaded and intact (5,990,551,040 bytes, exact size verified), but llama.cpp master from 24.11 (build 12.9, sm_70) responds with `unknown model… |
| [V100-75](results/V100-75.md) | GLM-4.7-Flash-30B-A3B IQ4_XS: fresh 30B MoE | Speed is good, model is degenerative.** Architecture of the file is `deepseek2` (like DeepSeek-Coder-V2), so FA is off. Matrix `-ncmoe` (IQ4_XS 15.56 GB, 31.22 billion): ncmoe 8 -… |
| [V100-76](results/V100-76.md) | Ternary-Bonsai-2-27B: 27B in 6 GB on ternary scales | Blocked by format (24.11).** File is valid (GGUF v3, 851 tensor, 5,946,648,928 bytes), but weights are compressed with type `PTQ1_0`, which llama.cpp does not support: the engine knows… |
| [V100-77](results/V100-77.md) | Raon-1-nano MTP: Multi-token prediction without draft | Blocked by engine (24.11).** File downloaded (2,145,934,208 bytes), but the architecture `raon1nano` is unknown to current llama.cpp. MTP head not verified - nothing to verify until the… |
| [V100-78](results/V100-78.md) | Rapid Averages: Nemotron-Bolt-E4B and SenseNova-Loop-9B | - ## Queue P1v - New Ideas Following Review (24.11.2026) | # | Idea | Stage | Resources | Status | Outcome | Ready | |---|---|---|---|---|---|---| | V100-66 | Code Quality: MBPP on Three… |
| [V100-79](results/V100-79.md) | llama.cpp v1.0.0 vs our build 51831d4 | Regression on sm_70 has occurred, but only for MoE. llama-bench, `-ngl 99 -fa 0 -r 1`, both builds on the same stand: | test | DeepSeek-V2-Lite 16B · 51831d4 | same · v1.0.0 |… |
| [V100-81](results/V100-81.md) | MOE cache experts in RAM instead of `-ncmoe` | Experts cache on sm_70 is not profitable: it doesn't fit on the card with `-ncmoe 8`, and when it fits (with `-ncmoe 12`), it loses to the current scheme. Qwen3-Coder-30B-A3B Q4_K_M,… |
| [V100-83](results/V100-83.md) | Strata-V100: third engine for verification | Run Coder IQ1_M (25.11.2026, VM 200, V100-SXM2-16GB). | Check | Result | |---|---| | Start Model | Experts 23.42 GiB in RAM (3.86 GiB/s), expert cache 4134 slots / 7.87 GiB VRAM,… |
| [V100-84](results/V100-84.md) | QWEN38-MTP flags from the recipe | The MTP flag is present in the build (`--spec-type draft-mtp` in build129), but there's nothing to test it on: the only Qwen3.8-27B on disk is a third-party quantum `pxqn-onecard` (13.57… |

## Follow-ups in progress

The cards above each name what their numbers cannot support. Those gaps are already scheduled — one
re-run per gap, on the same card, with the same engine. Nothing here is a new idea: every line either
confirms a published number or corrects it.

**Results will be published as they land** — the affected card is rewritten and this table loses the row.
Until then the caveat stands, and a table row is not a substitute for a measurement.

| Follow-up | Card it closes | What is being re-measured | Est. |
|---|---|---|---|
| V100-53 | V100-11 | repeat the prefix-cache comparison at equal prompt length | 1.5 h |
| V100-54 | V100-27 | native baseline with cuDNN enabled | 1.5 h |
| V100-55 | V100-37 | capture stderr to explain the ngl above 20 refusal | 1 h |
| V100-56 | V100-02 | measure the 32k point and try q4_0 KV at 64k | 2 h |
| V100-57 | V100-02 | repeat the q8_0 decode comparison with restarts between modes | 1.5 h |
| V100-58 | V100-12 | batching at 1/4/8 clients, aggregate throughput, answer quality | 4 h |
| V100-59 | V100-24 | repeat DRY on a model that actually loops | 2 h |
| V100-60 | V100-16 | build all eight volta-fa patches on their base commit | 5 h |
| V100-61 | V100-19 | end-to-end pipeline timing, script preserved | 2 h |
| V100-62 | V100-36 | inspect the tiled 720p frames instead of trusting the exit code | 2 h |
| V100-63 | V100-39 | separate model load time from harness start | 1 h |
| V100-64 | V100-15 | offline restore of the snapshot on a clean VM | 3 h |
| V100-65 | V100-10 | prefill at 8k and 16k, and record num_batch=4096 | 1 h |

Total queued: **13** re-runs, roughly 27.5 h of GPU time.

## How to read this

`tok/s` is generated tokens per second, `prefill` is prompt processing. Where a number depends on
conditions — cold vs warm start, KV cache type, batch size, VRAM headroom — the condition is stated in the
card, not hidden in a footnote. A card that says "not worth it" is a result, not a failure.

## Why publish the negative ones

Several cards kill popular advice: the Volta FlashAttention patches promised +34–45 % and delivered +7.4 %;
64k context does not fit a 14B model in 16 GB at any KV precision; the DRY sampler fixed nothing because this
model does not loop; a dense 32B runs at 3.0 tok/s where a 30B MoE runs at 24.5; and a CUDA 13 compatibility
layer is 11x slower than the native path it replaces. Reproducing a disappointment costs hours — reading about
it costs a minute.

Corrections are welcome: if a number does not reproduce on your card, open an issue with the command and the
output. The card will be changed, not defended.

## License

Text and results: CC BY 4.0 — reuse with attribution.
