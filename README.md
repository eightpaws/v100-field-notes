# Tesla V100 (sm_70) — measured results

Field notes from one **Tesla V100-SXM2 16 GB** running inside a Proxmox VM (24 vCPU, 94 GiB RAM).
Every number below was measured on the card, not copied from a project README. Negative results are
published on purpose: they are the expensive part of anyone's time.

Closed experiments: **161** — 25 positive, 33 mixed,
26 negative. Follow-ups queued: **26** — each card names the re-run that closes its caveat, and the results are published here as they land.

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
| [4060ti-capabilities-vs-v100](results/4060ti-capabilities-vs-v100.md) | 4060ti-capabilities-vs-v100 | The split is clean and measured: the 4060 Ti is the card that can train QLoRA at 398 tok/s (3B) and run bf16 paths, while the V100 is the card that serves inference with 900 GB/s and… |
| [V100-01](results/V100-01.md) | Speculative decoding in llama.cpp | Speculative decoding was tested on two targets, and the result depends on the model pair: it accelerates on 7B, but slows down almost twofold on 14B. llama.cpp master 51831d4, CUDA 12.9,… |
| [V100-03](results/V100-03.md) | Importance matrix for Q4_K on a Russian corpus | **Mixed.** Held-out perplexity is consistently 0.57-0.64 % lower with the matrix (mean −0.61 %, Δ −0.107), and the direction holds on all three slices. The file sizes are identical to within 192… |
| [V100-04](results/V100-04.md) | VLM as a card reject controller | Qwen2.5-VL-3B-Instruct (fp16, `device_map=cuda`) on 24 generated cards 640x640 produced **24 out of 24 "good"**, **1.8 sec per image** (45.4 sec per batch), peak VRAM **7,634 MiB**.… |
| [V100-05](results/V100-05.md) | IC-Light relighting: the product colour moves by 24-37 dE | **Negative.** | Metric | Value | Unit | |---|---|---| | pairs with a coloured scene | 30 | pairs | | dE mean, coloured scenes | 37.5 | dE76 | | dE max, coloured scenes | 65.9 | dE76 | | dE mean,… |
| [V100-06](results/V100-06.md) | SUPIR vs Real-ESRGAN in print | Real part measured, diffusion stuck in channel. - Real measurement at 640x640 frame, upscale x4 to 2560: Real-ESRGAN x4plus - 0.9 s, peak 2722 MiB, sharpness 5.5, ΔE 3.9 (max 6.1).… |
| [V100-07](results/V100-07.md) | Chatterbox Multilingual on a V100: expressiveness for free, 40-second ceiling | **Mixed.** Mixed: Chatterbox Multilingual speaks Russian intelligibly (WER 2-11 % on a 92-word paragraph, 0 % on a short phrase), carries emotion through `exaggeration`, and clones the reference… |
| [V100-08](results/V100-08.md) | Text-to-SFX on a V100: Stable Audio Open vs the open alternative | **Mixed.** Mixed: text-to-SFX on this card is real and cheap (one second of audio per 0.93 s, 2.9 GB VRAM, so a whole video's ambience layer costs seconds), but AudioLDM2 tops out at **16 kHz… |
| [V100-09](results/V100-09.md) | 360° Product: Photogrammetry or Splines | **Mixed.** | Configuration | Gaussians | ms/iteration | iterations/s | VRAM peak, MiB | |---|---|---|---|---| | 480x640, kernels built in this run | 200 000 | 7.0 | 143 | 98 | | 480x640, kernels… |
| [V100-100](results/V100-100.md) | Style presets and immutable prompt part | **Positive.** Three presets (catalog_white, warm_interior, flatlay_social) x 5 seeds, one position (bouquet of peonies in craft cone), 832x1216, RealVisXL V5 fp16, cuDNN off, CPU-offload: 15/15… |
| [V100-101](results/V100-101.md) | LoRA under the product and brand | **Mixed.** LoRA on 24 frames of a single product (640 px, rank 8, lr 1e-4): 800 steps in 16.1 min, 2400 steps in 48.9 min, peak VRAM 7.8 GiB. Similarity to reference frame (CLIP ViT-L/14, cosine):… |
| [V100-102](results/V100-102.md) | Image-to-image and depth: Save product, change background | Confirmed partially. Diffusion (SDXL + ControlNet depth 1.0-small, strength 0.45, 25 steps) preserves the product but does not remove the background to white: background brightness is… |
| [V100-103](results/V100-103.md) | Batch savings: Batch vs individual loads | **Positive.** Group of four runs on one model: batch 23.9 s vs. variance 39.1 s, savings 38.8%. Warm switching: 7B 1.5 s, 16B 2.5 s, 30B 3.5 s, i.e., 10 times less than the 40-60 s figure from the… |
| [V100-104](results/V100-104.md) | GPU Unlock: Thawing cores 4060 Ti, +24% on 4060 | Translation:** "Measurement 'before' exists, unlock was not installed. - Baseline on 4060 Ti, driver 617.14 untouched: fp16 38.7 TFLOPS, fp16 with fp32 accumulation 40.1, bf16 40.3, fp32… |
| [V100-105](results/V100-105.md) | Polyglot: eight languages on one harness | 6 languages (Python, JavaScript, PHP, Ruby, Go, Java) x 10 functions x 21 statements per language, three models, temperature 0, one run 3m 4s. Qwen2.5-Coder-7B Q8 - 6/6 languages (all… |
| [V100-106](results/V100-106.md) | Linters as acceptance: how much code passes on the first try | (25.11.2026) 40 tasks MBPP, Qwen2.5-Coder-7B-Instruct Q8_0. Tests pass 24 out of 40 (0.60). Linters: `ruff --select E,F` clean in 39 files out of 40 (one note for the whole sample),… |
| [V100-107](results/V100-107.md) | Safety: semgrep, bandit, gosec on generated code | The "secure by default" prompt barely helps: 8 bandit findings in normal mode versus 7 in secure mode (MEDIUM 3 against 2, HIGH none in either), clean files 6 out of 10 versus 7. Only… |
| [V100-108](results/V100-108.md) | Tests that catch: mutation testing of generated tests | **Mixed.** Three branches, Qwen2.5-Coder-7B Q8, temp 0.2. (A) The model writes both code and tests according to the spec: red suite on its own code (3 out of 6 tests fail), with two real errors in… |
| [V100-109](results/V100-109.md) | Medium-sized project from scratch: FastAPI, Postgres, authorization, tests, Docker | The project has been assembled but does not launch. Qwen2.5-Coder-7B Q8 produced 11 files and 634 lines according to plan (main, models, schemas, auth, notes, tests, README, Dockerfile,… |
| [V100-110](results/V100-110.md) | Red test cycle → repair on four languages | 20 tasks (5 each in Python, JavaScript, C, Perl), Qwen2.5-Coder-7B-Instruct Q8_0, `llama-server` build129, temperature 0; total set - 25s, server up in 2s. Successfully fixed 18 out of… |
| [V100-111](results/V100-111.md) | Review diff: five planted bugs, accuracy and completeness | 10 commits with 5 planted defects each (boundary, null, race, injection, leak), Qwen2.5-Coder-7B Q8_0, 16 seconds total. Found 17 out of 50 (34%), false positives 0 per commit.… |
| [V100-112](results/V100-112.md) | Refactoring with green tests | Refactoring Tasks: 10 tasks, 2-3 files each (helper code extraction, global renaming, deduplication, signature change, constant extraction, module separation, dead parameter removal,… |
| [V100-113](results/V100-113.md) | Schema, migrations, and queries against SQLite | 20 tasks on SQLite (schema, migration, 3 queries to each), Qwen2.5-Coder-7B Q8_0, two runs of 37s each. Completely correct 7 and 9 tasks out of 20 with a criterion of 15, queries correct… |
| [V100-114](results/V100-114.md) | Frontend: page with form, checking Playwright | Qwen2.5-Coder-7B-Instruct generated 10 pages of one specification in 109 seconds (9.7-12.4 seconds per page, 3.2-5.0 thousand symbols). Playwright scenario (desktop 1280, mobile 390,… |
| [V100-115](results/V100-115.md) | CI and Docker: how many repositories are being built | 5 projects from previous cards (V100-109 FastAPI-notes, V100-114 static page, V100-116: api-client, CLI-ETL, FastAPI+JWT). First pass without edits: **0 out of 5**. Reproducible reasons:… |
| [V100-116](results/V100-116.md) | What a generated project still needs before delivery | **Mixed.** Deliverable, but only what was asked for: the model emitted a Dockerfile and a LICENSE exactly where the prompt named them and skipped them where it did not. The delivery checklist… |
| [V100-117](results/V100-117.md) | Cost of a typical order: machine hours and price for six types of work | **Mixed.** The machine is not the cost. Six orders cost seven kopecks of electricity and under three minutes of GPU time; two of six needed the full two repair rounds and still failed, which is… |
| [V100-118](results/V100-118.md) | Conveyor spec → plan → code → tests → review against one prompt | Same 7B Q4_K_M, 10 MBPP tasks, temperature 0: one prompt 7/10 (0.70), pipeline spec-code-tests-reviews 6/10 (0.60) - difference **-10 points**. Pipeline takes **12 times longer** (6.1s… |
| [V100-119](results/V100-119.md) | Someone else's repository: where to change | **Positive.** The edit point is found: | Metric | Result | |---|---| | Right file | 9 of 10 | | Right function | 9 of 10 | | Strict pair (file and function) | **8 of 10** | The criterion (7 of 10) is… |
| [V100-120](results/V100-120.md) | Russian text in generated code | 8 out of 10 tasks accepted without revision according to the task criteria: names in Latin 10/10, Russian text in place 10/10, long hyphens 0, typos 0, syntax valid 10/10. Terms in Latin… |
| [V100-121](results/V100-121.md) | Consistency of style with existing code | 20 runs (10 tasks x 2 models), temp 0, baseline Harness passed ruff/mypy/pytest 10/10. Qwen2.5-Coder-7B Q8: ruff clean 4/10, mypy 9/10, tests 8/10, median deviation from baseline 19.5%… |
| [V100-122](results/V100-122.md) | Output stability: five repeats of one task | **Negative.** Negative: 0 of 5 runs green at temperature 0 and 0 of 5 at 0.2, so the shipping bar is not met. Repeatability is not quality — temperature 0 reproduces the same defect with byte-exact… |
| [V100-123](results/V100-123.md) | Quant ladder for a 30B MoE code model: Q4, Q5, Q6, Q8 | **Negative.** Negative for Q6 and Q8: no quality gain over Q5_K_M, only more time, RAM and disk. Q5_K_M is the recommended quant for a 30B-A3B code model on one 16 GB Volta card. |
| [V100-124](results/V100-124.md) | Third-party API integration: retries, timeouts, idempotency | **Negative.** Negative: 3 of 10 scenarios in both runs. The retry skeleton is sound, but one shadowed name kills every request the client makes — exactly the class of defect that a test suite finds… |
| [V100-125](results/V100-125.md) | WordPress and WooCommerce: plugin edit with tests | **Mixed.** All three models passed both suites on the first attempt, with no retries and no manual fixes: Qwen2.5-Coder-14B Q4_K_M scored 10/10 and 6/6 in 7 and 8 seconds at a 9565 MiB VRAM peak;… |
| [V100-126](results/V100-126.md) | Generated code productivity | Ten tasks on 100,000 records, n=3, median. Correct in 9/10 cases, all nine within 3x of the standard: median ratio 0.95, worst 1.02, so model code indistinguishable from the standard in… |
| [V100-127](results/V100-127.md) | Multi-file edits that keep the public API intact | **Negative.** No. 7 of 10 edits pass both gates; the stated criterion was 8 of 10. | Task | Files written | Generation | API gate | Tests | Pass | |---|---|---|---|---|---| | t01 rounding module | 4 |… |
| [V100-128](results/V100-128.md) | Writing tests for someone else's code: coverage and defect detection | **Negative.** No. All three suites are red on the correct code: 14 of 18 tests fail. Counting only the tests that are green on the pristine module, coverage is 22.2-22.8 % against a 60 % target, and 1… |
| [V100-129](results/V100-129.md) | Censored 27B on one card | Dense 27B IQ3_S (10.95 GiB) fit entirely: decode 37.26 tok/s (tg64, n=3), prefill 837.69 on pp512 and 800.49 on pp8192, server with `-c 16384` launched in 9s with 12,977 MiB VRAM, peak… |
| [V100-13](results/V100-13.md) | AWQ/int4 vs GGUF Q4 on Volta | AWQ/int4 via vLLM 1.5.4: model loaded (14287 MiB VRAM), decode **117 tok/s** (114.2 / 116.9 after warm-up, first request 66.5), code is correct. Against GGUF Q4_K_M in llama.cpp: 132… |
| [V100-130](results/V100-130.md) | Uncensored Flash-Next Q2_0 under Strata | **Mixed.** The server came up in **90 s** and held **15 661 MiB** of VRAM with the expert cache at 88-90 % hit during the code test. Speed: **45.1 tok/s** during MBPP (1.66 s per task), 38.0 tok/s… |
| [V100-131](results/V100-131.md) | Failure metric: 20 prompts, uncensored vs censored | Translation:** 27B abliterated IQ3_S (model 2 of 3): class A 7/7 direct response, class B 9/9 direct (zero failures), class C 4/4 refusal. 11.5s for 400 tokens (~35 tok/s), VRAM 12,443… |
| [V100-132](results/V100-132.md) | Captcha: Local VLM vs Service | 26.11.2026, V100 16 GB, Qwen2.5-VL-7B-Instruct Q4_K_M + mmproj-F16, 200 synthetic CAPTCHAs: distorted text 88/100 (88%), arithmetic 50/50 (100%), "how many figures" grid 15/50 (30%);… |
| [V100-139](results/V100-139.md) | Coded contour: entire package in context | The entire `pypa/packaging` package (20 files, 12,638 lines) in the context of 65,536 tokens, prompt truncated to 80KB (around 19 thousand tokens). Five tasks, fixed 0. Model returns… |
| [V100-14](results/V100-14.md) | 24B in 16 GB: Mistral-Small-3.1-24B AWQ | Mistral Small 24B AWQ does not fit in 16 GB via vLLM. The model is fully downloaded (3 shards, 13.4 GB, all tensors are read), 1Cat-vLLM 1.5.4 compiled for sm_70 and has separate… |
| [V100-140](results/V100-140.md) | Q4_0 KV disrupts generation | On Qwen2.5-Coder-7B server with `-ctk q4_0 -ctv q4_0`, it produced incoherent text even for a 45 token prompt: `def add,,b):`, with fragments of quotes and arrows. After switching to… |
| [V100-141](results/V100-141.md) | cuDNN 8 environment for graphics and video models | **Positive.** Positive: cuDNN 8 restores the missing convolution path on sm_70, and all three pipelines run with cuDNN enabled. It removes the engine failure, not the memory ceiling - 720p video still… |
| [V100-142](results/V100-142.md) | VLM card controller: blind to framing | **Mixed.** | Metric | Value | Unit | |---|---|---| | accuracy (80 frames) | 0.85 | fraction | | recall over defects | 0.70 (28/40) | fraction | | false rejects on clean cards | 0/40 | frames | |… |
| [V100-143](results/V100-143.md) | Raw archive: nine of thirteen missing logs recovered | **Mixed.** Nine of the thirteen cards now have archived raw output: V100-29, 40, 43, 45, 46, 47, 48, 50, 51. The files were on the rig all along under suffixed names (`v100_29_pxa.log`,… |
| [V100-144](results/V100-144.md) | Inkling 2 Mini: looped MoE, depth without weight growth | **Mixed.** Mixed — the knob moves the token budget, not the speed: decode sits at 33 tok/s on all three levels, while `high` spends 51% more tokens per answer and is not better than `medium` (7/12… |
| [V100-145](results/V100-145.md) | Gemini 4 26B-A4B in 4 bits: 16-GB sweet spot on Volta | Fits entirely and fastest among those measured on this map: prefill 2696.3 ± 94.7 tok/s on pp256, decode 124.09 ± 0.53 tok/s on tg64, peak VRAM 15331 MiB at 8k context, server ready in… |
| [V100-146](results/V100-146.md) | CogVideoX-5B: does not launch on this stack | CogVideoX-5B does not run on this build: with cuDNN enabled, it's `GET was unable to find an engine` on fp16-convolutions, and with disabled, the VAE decoder requests 17.8 GiB while only… |
| [V100-147](results/V100-147.md) | Cache prefix: equal prompt lengths | With a prompt length of 4096 tokens, prefix cache provides an **8.25x** speedup: without cache, 1179.8 ± 2.0 ms (full prefill of 4096 tokens, 3472 tok/s), repeating the same prefix 143.0… |
| [V100-148](results/V100-148.md) | PXA: Second checkpoint and quality 27B | Second checkpoint PXQN yielded the same quality: MBPP pass@1 **0.625 (25/40)** compared to **0.60 (24/40)** at V100-29 checkpoint, indicating a difference of one task - noise from a… |
| [V100-149](results/V100-149.md) | llama-server throughput with ten concurrent clients | **Mixed.** | Configuration | TTFT median | TTFT max | Burst throughput | Decode per client | VRAM | |---|---|---|---|---|---| | 1 client, `-np 1`, 4096 | 491 ± 6 ms | 510 ms | 111 tok/s | 111 tok/s… |
| [V100-150](results/V100-150.md) | 27B PXQN: 8k context and two clients on one 16 GB card | **Mixed.** Mixed. The 8k context per slot fits and a second client does not steal throughput: with `-c 8192 --np 1` each of two clients decodes at 161.4 tok/s, which is 2.3x the single-client… |
| [V100-151](results/V100-151.md) | PXQN vs standard Q4_K_M on a single 27B | The default Q4_K_M of the same Qwen3.8-27B model fully loads onto the card using the stock llama.cpp and achieves a MBPP pass@1 score of **0.650 (26/40)** compared to 0.600-0.625… |
| [V100-152](results/V100-152.md) | 200 tasks instead of 40: does the difference between checkpoints hold? | On 200 tasks of MBPP, the difference between checkpoints is insignificant: **0.470 (94/200)** for the baseline and **0.495 (99/200)** for Swift-1.5, meaning five tasks out of two hundred… |
| [V100-153](results/V100-153.md) | Reasoning budget on 27B: what thinking buys | **Negative.** MBPP pass@1 is **0.600 (24/40)** in all three modes, so reasoning bought no task at either budget. The cost is 5.88 s per task at budget 512 (3.8x the 1.55 s of no reasoning) and 11.72 s… |
| [V100-17](results/V100-17.md) | LMDeploy TurboMind: AWQ without forks | Partial: TurboMind works on sm_70 but loses quality in 4-bit. Speed: decode 131.2 tok/s (n=3, stdev 0.13), prefill 4266 tok/s at 751 token, VRAM 14.8 GiB, warm-up 50s. Quality: MBPP… |
| [V100-18](results/V100-18.md) | xllama.cpp: compress KV instead of q8 | Compressed KV in xllama.cpp works, but on long context it becomes too slow. Built with xllama.cpp f9287a9 (fork of llama.cpp from April 2026 with… |
| [V100-20](results/V100-20.md) | fni8: int8 dp4a for DiT | Rejected along with V100-22: this is the same fni8 package family (int8 dp4a for DiT in ComfyUI). The author himself writes that acceleration was measured on a CMP 100-210 park with… |
| [V100-21](results/V100-21.md) | Tachyon, Ninfer, Lapilli | Tachyon-v100 is being built and run on our card, but our models do not support it. Verified step by step. Build (Rust + nvcc), three pitfalls: 1. build.rs looks for the compiler strictly… |
| [V100-22](results/V100-22.md) | fni8 for LLM: int8 dp4a instead of tensor cores | Rejected based on the author's documentation facts. fni8 (jajmangold/fni8, ComfyUI-fni8 package) is an int8 dp4a path through CUDA kernels, and it is designed for cards with… |
| [V100-25](results/V100-25.md) | CUDA graphs for musical pipeline | Capture of CUDA graphs for ACE-Step 1.5 won't yield significant gain. Measurements via music studio API on xl-sft with LM 1.7B: | Duration | Steps | Seconds | |---|---|---| | 30s | 8 |… |
| [V100-26](results/V100-26.md) | llama.cpp build flags matrix for Volta | The build flag matrix was previously verified (CUDA 12.0, llama.cpp build b7743fbfd8, model 14B Q4_K, llama-bench pp512/tg128, median of three runs). Result: none of the flags… |
| [V100-28](results/V100-28.md) | V100-LLM: ready presets for 16 GB | Rejected: the release does not include the engine. Checked GitHub API for the Abdelhayali/V100-LLM repository, tag v1.3.0 - two assets: `LocalAI-Bridge-Desktop.exe` (8 MB) and… |
| [V100-29](results/V100-29.md) | PXA 4.0 engine: a 27B model on a 16 GB card | **Positive.** The first configuration that puts a 27B dense model fully on the card and still decodes faster than the 30B MoE with CPU offload. Stock llama.cpp cannot read the PXQN4 file — the PXA… |
| [V100-30](results/V100-30.md) | sm70-attn: FA2-D256 in llama.cpp | Rejected based on the card criterion: "do we have a model with head_dim 256 and do we need context over 64k". The answer is no and no. What was actually checked: - We don't have models… |
| [V100-31](results/V100-31.md) | One model across V100 and 4060 Ti: the link kills it | **Negative.** Heterogeneous tensor parallelism over 1 Gbit is latency-bound at roughly 11 tok/s for a 27B dense model, and even the bandwidth-only ceiling (45 tok/s) leaves no margin over the 24.5… |
| [V100-32](results/V100-32.md) | Prepared sm_70-weights with Hugging Face | NInfer-V100 1.7.2 unpacks and runs: three binaries of 421-424 MB (ninfer, ninfer-serve, ninfer-perplexity), no missing libraries, help opens. But it has nothing to work with. The engine… |
| [V100-38](results/V100-38.md) | ACE-Step 4B and work alongside SDXL | Test 25.11:** `music-studio` service starts, stops `imgd` (no coexistence in fact, despite the description claiming "coexists with SDXL"), loads weights and crashes on loading 5Hz LM:… |
| [V100-40](results/V100-40.md) | ik_llama.cpp vs upstream llama.cpp on V100 | **Negative.** The advertised 2.2x does not reproduce: prefill on the fork is about half of upstream (843–890 vs 1638–1779 tok/s) and decode is only 4% better with flash attention (73.53 vs 70.92). On… |
| [V100-41](results/V100-41.md) | GPT-OSS-20B MXFP4 on a 16 GB Volta card | **Mixed.** Usable only with flash attention on and 4 expert layers pushed to CPU: 24 tok/s decode. Both faster coding candidates (DeepSeek-Coder-V2-Lite at 183 tok/s, Qwen3-Coder-30B at 75 tok/s)… |
| [V100-42](results/V100-42.md) | MoE experts in system RAM: -ncmoe on V100 16 GB | **Positive.** Yes: 8 expert layers on CPU is the entry threshold, and every extra layer costs both prefill and decode roughly linearly. At 8 layers a 17.3 GB model — 1.3 GB larger than the card —… |
| [V100-43](results/V100-43.md) | llama-server as the working server: prefix cache and batching | **Positive.** Prefix caching works and is the main reason to run llama-server for agent workloads: prompt processing drops from 845 ms to 89 ms (9.5x), round trip from 1.18 s to 0.39 s. |
| [V100-44](results/V100-44.md) | NVFP4 on sm_70: 4-bit float in 16 GB | Works on sm_70. vLLM 1.5.4 (`--quantization modelopt_fp4`) boosted Ornith-1.5-9B-NVFP4 on V100: 14 133 MiB VRAM, decode **86.7-86.8 tok/s** (first request 83.0), code is correct.… |
| [V100-45](results/V100-45.md) | Qwen3-Coder-30B-A3B as a coding writer on 16 GB | **Positive.** Working configuration is `-ngl 99 -ncmoe 8 -c 4096`. An 8192-token context needs more VRAM (compute buffer allocation fails), so long files require either 12 CPU layers or a smaller context. |
| [V100-46](results/V100-46.md) | Tool calling on a local V100 model | **Positive.** Tool calling works correctly with the Qwen3-Coder chat template: valid JSON arguments, no extra calls, correct final answer. At 75 tok/s decode a conversational turn costs 2–3 s. |
| [V100-47](results/V100-47.md) | DeepSeek-Coder-V2-Lite 16B MoE: the fastest decode on V100 | **Positive.** Best decode measured on this card by a wide margin: 183.6 tok/s with 2250 tok/s prefill, working configuration `-ngl 99 -fa 0`. Flash attention must be off — it is 160x slower on this… |
| [V100-48](results/V100-48.md) | FIM autocomplete in the editor via llama-server /infill | **Mixed.** FIM works and is fast enough to type ahead of a human. Latency is unstable (126 ms to 1.5 s on the same prompt) — the old build's slot handling is the suspect; a single slot with… |
| [V100-49](results/V100-49.md) | Embeddings for code search with bge-m3 on V100 | **Positive.** Ranking is correct with a clear margin, and the 606 MB model handles a Russian query against English code without translation. Indexing a repository is a matter of minutes on this card. |
| [V100-50](results/V100-50.md) | Speculative decoding for code generation | **Negative.** Not reproducible. The first run on build 51831d4 showed +21% on a 7B target, but on master af5c583 with the same pair the gain is gone: base 105.5 / 111.9 / 113.0 tok/s versus 102.6 /… |
| [V100-51](results/V100-51.md) | 32k context for a 30B MoE on 16 GB | **Mixed.** 32k is reachable only with compressed KV plus offloaded experts: `-c 32768 -ctk q8_0 -ctv q8_0 -ncmoe 16` gives 25 tok/s. Without compression the same window needs 24+ CPU layers and… |
| [V100-52](results/V100-52.md) | Local edit → test → fix loop | **Positive.** The loop closes locally in 15 seconds per iteration, which makes unattended refactoring and test-fixing practical. A dense 32B on the same card would run at 3 tok/s and be unusable for this. |
| [V100-53](results/V100-53.md) | Cache prefix: equal comparison at equal prompt length | **Positive.** | Window, tokens | No cache | Repeat (cache) | Tail edit | Gain | |---|---|---|---|---| | 2053 | 575.0 ± 1.6 ms | 77.4 ± 1.0 ms | 80.0 ± 2.3 ms | 7.4x | | 6142 | 1916.2 ± 3.4 ms | 208.5… |
| [V100-54](results/V100-54.md) | Volt-forever: Honest native base with included cuDNN | Partial: cuDNN-on is not available on our stack. torch 2.10.0+cu128 with cuDNN 9 on convolution reports `GET was unable to find an engine to execute this computation`, cuDNN version is… |
| [V100-55](results/V100-55.md) | Llama-Bench refuses to load more than 20 layers. | There is no limit of 20 layers.** The matrix is based on Qwen3-Coder-30B (17.28 GiB), f16 KV, p128/n16: | ncmoe | prefill pp128 | decode tg16 | |---|---|---| | 24 | 179.2 | 39.2 | | 32 |… |
| [V100-56](results/V100-56.md) | 32k with q8_0 KV and 64k with q4_0 KV on a 7B model | **Positive.** Both settings work: 32k with q8_0 and 64k with q4_0 KV fit on one 16 GB card, and decode stays at 126 tok/s at either context length. Compressed KV is what makes 64k possible at all; the… |
| [V100-57](results/V100-57.md) | Q8_0 KV: Confirm double decoding or attribute to noise | No double acceleration: compressed KV is slightly slower.** Qwen2.5-Coder-7B Q4 (4,36 GiB), p512/n128, r=2: | KV | FA | prefill pp512 | decode tg128 | |---|---|---|---| | f16 | off |… |
| [V100-58](results/V100-58.md) | Throughput, batching, quality | Under load, 1Cat-vLLM outperforms llama.cpp by six times.** 7B GGUF, `--max-model-len 4096`, `--gpu-memory-utilization 0.6`, different prompts for all requests (otherwise prefix cache… |
| [V100-60](results/V100-60.md) | Gather all eight patches on their base commit. | No: all eight patches apply on 79e2e74 (HEAD 70782b2), but the claimed +34-45% does not reproduce - decode tg64 67.8 tok/s against 70.93 for the upstream build b1b770d (-4.4%), prefill… |
| [V100-61](results/V100-61.md) | GQA to MHA expansion: nothing in the pipeline can carry it | Unstated is the honest label here: the check had no carrier, which is not the same as "the effect does not exist". The kernel-level 7.2x from V100-19 stands and is untouched by this card. |
| [V100-62](results/V100-62.md) | 720p with VAE tiling: check the frames, not the exit code | **Mixed.** 720p with VAE tiling is viable — no tile seams at 1280×704 / 97 frames on 13.55 GiB. The weak point is not tiling but overall softness and blown highlights at 30 steps with the 5B model;… |
| [V100-63](results/V100-63.md) | Model loading is not the same number as harness start | **Mixed.** Any load-time number from this rig has to name the engine. For llama.cpp, 3.5-4.2 s for a 7B model is real. For vLLM on Volta the correct figure is about two minutes, paid once per… |
| [V100-64](results/V100-64.md) | Snapshot of stack: offline installation on clean VM | No: snapshot does not raise the stack without a network. In cache, there are 12 wheels for 2.3 GB, covering 8 lines out of 302 in full freeze (2.6%) and 15 out of 45 in… |
| [V100-65](results/V100-65.md) | Batch size does not change prefill at 8k or 16k | **Negative.** On this card, in llama.cpp, `n_batch` between 512 and 4096 changes nothing measurable at 8k or 16k: prefill sits at 2649 tok/s at 8k and 1898 tok/s at 16k across the whole range, and… |
| [V100-66](results/V100-66.md) | Quality over speed: MBPP pass@1 on 16 GB models | **Mixed.** Reasoning mode costs 6x the time and 37 points of pass@1 unless it is disabled; with thinking off the 30B MoE reaches 0.60 on 40 tasks but 0.50 on 200, level with the 16B dense model at… |
| [V100-67](results/V100-67.md) | 16 GB: Q4_K_M - 128 bits, Q5_K_M - 160 bits, Q6_K - 256 bits, Q8 - 320 bits | Q5_K_M outperforms Q4_K_M in quality with a slight speed loss.** | Quant | Size | VRAM | Prefill pp128 | Decode tg32 | MBPP pass@1 | |---|---|---|---|---|---| | Q4_K_M | 4.68 GB | ~5 GB… |
| [V100-68](results/V100-68.md) | Speculation on 30B MoE: Draft 0.5B vs Qwen3-Coder | Speculation on 30B is not profitable.** With a draft of 0.5B, the model had to be raised from `-ncmoe 12` instead of 8 (draft subtracts VRAM): base in these conditions **36.0 / 32.6 /… |
| [V100-69](results/V100-69.md) | Special dec without second model | N-grams in file editing don't provide anything, draft hurts.** Prompt 200 lines of source code, model appends function based on pattern: base **71.5 / 106.3 / 106.4 tok/s**,… |
| [V100-70](results/V100-70.md) | Re-rank surface search by code | The reranker works and separates trash confidently.** bge-reranker-v2-m3 (568M, fp16) took **6.9 s** to launch on V100 and used **1092 MiB** VRAM - fits alongside working LLM, no need to… |
| [V100-71](results/V100-71.md) | The cost of 1M tokens on your own hardware is | Cost of 1M output tokens on own hardware.** Power consumption measured via `nvidia-smi power.draw`: idle **20.7-46.6 W**, under load (7B, 65% utilization) **159.0 W**, peak rated 300 W.… |
| [V100-72](results/V100-72.md) | Agent with four tools and an error on the first call | 1 of 3 scenarios.** Three tasks, four tools, the first call `get_time` was intentionally broken (server responded with `unknown argument 'location'; the only valid argument is 'city'`.… |
| [V100-73](results/V100-73.md) | Goods cards per hour: image generation throughput | On a 768 px card, it yields ~2100 images per hour, but on 1024 px it hits memory.** Tested on DreamShaperXL-Turbo (6 steps, guidance 1.5, fp16) via diffusers, local single-file… |
| [V100-74](results/V100-74.md) | Olala-v1.0-mini-7A1B: MoE with 1B active on 16 GB | Blocked by engine (24.11).** File downloaded and intact (5,990,551,040 bytes, exact size verified), but llama.cpp master from 24.11 (build 12.9, sm_70) responds with `unknown model… |
| [V100-75](results/V100-75.md) | GLM-4.7-Flash-30B-A3B IQ4_XS: fresh 30B MoE | Speed is good, model is degenerative.** Architecture of the file is `deepseek2` (like DeepSeek-Coder-V2), so FA is off. Matrix `-ncmoe` (IQ4_XS 15.56 GB, 31.22 billion): ncmoe 8 -… |
| [V100-76](results/V100-76.md) | Ternary-Bonsai-2-27B: a 27B model in 5.95 GB, engine decides | On the PrismML runtime the ternary path works: prefill **815.88 +/- 11.60 tok/s** at pp256, decode **67.13 +/- 0.08 tok/s** at tg64, server at **7 041 MiB**, and **MBPP pass@1 0.55… |
| [V100-77](results/V100-77.md) | Raon-1-nano MTP: multi-token prediction without a draft model | **Negative.** The MTP head is dead weight in this engine: it loads but is never executed, no speculative counters appear in server responses, and decode never improves. Two clean-card series: 93.28 vs… |
| [V100-78](results/V100-78.md) | Rapid Averages: Nemotron-Bolt-E4B and SenseNova-Loop-9B | - ## Queue P1v - New Ideas Following Review (24.11.2026) | # | Idea | Stage | Resources | Status | Outcome | Ready | |---|---|---|---|---|---|---| | V100-66 | Code Quality: MBPP on Three… |
| [V100-79](results/V100-79.md) | llama.cpp v1.0.0 vs our build 51831d4 | Regression on sm_70 has occurred, but only for MoE. llama-bench, `-ngl 99 -fa 0 -r 1`, both builds on the same stand: | test | DeepSeek-V2-Lite 16B · 51831d4 | same · v1.0.0 |… |
| [V100-80](results/V100-80.md) | Inkling-2-Mini 26B/3.4B Q3 on sm_70: NaN check | **Positive.** Usable: a 26B MoE at 13.6 GB answers correctly on a 16 GB Volta card at about 29 tok/s, provided the client allows a long thinking budget and reads `reasoning_content` as part of the stream. |
| [V100-81](results/V100-81.md) | MOE cache experts in RAM instead of `-ncmoe` | Experts cache on sm_70 is not profitable: it doesn't fit on the card with `-ncmoe 8`, and when it fits (with `-ncmoe 12`), it loses to the current scheme. Qwen3-Coder-30B-A3B Q4_K_M,… |
| [V100-82](results/V100-82.md) | 262K context on a single 16 GB card | **Positive.** Yes for a small model: 262k fits on 16 GB with quantised KV. The ceiling is set by model size, not by the card: 0.5–1B reaches 262k, a dense 7B is realistic at 64k, and a 30B MoE at 8–16k. |
| [V100-83](results/V100-83.md) | Strata-V100: third engine for verification | Run Coder IQ1_M (25.11.2026, VM 200, V100-SXM2-16GB). | Check | Result | |---|---| | Start Model | Experts 23.42 GiB in RAM (3.86 GiB/s), expert cache 4134 slots / 7.87 GiB VRAM,… |
| [V100-84](results/V100-84.md) | QWEN38-MTP flags from the recipe | The MTP flag is present in the build (`--spec-type draft-mtp` in build129), but there's nothing to test it on: the only Qwen3.8-27B on disk is a third-party quantum `pxqn-onecard` (13.57… |
| [V100-85](results/V100-85.md) | Xing4.0-29B-A4B in IQ2_M | **Negative.** Negative. The 2-bit quant does what it promises on memory - a 29B MoE resident in 16 GB at 71 tok/s decode - but code quality lands at 0.425, below the card's 0.55 bar and below even a… |
| [V100-86](results/V100-86.md) | v100-llm-kit: prebuilt SM70 binaries vs our own build | **Mixed.** Mixed: prefill 16 % faster with the shipped sm_70 binaries, decode identical. Worth taking for long prompts (document analysis, repository context); not a reason to migrate a… |
| [V100-87](results/V100-87.md) | Marlin_v100: INT4-cores Marlin on sm_70 | Workspace assembled: BUILD_RC=0 in 3368 s (56 min), `_C.abi3.so` 509 MB and `_moe_C.abi3.so` 447 MB, loading on sm_70, `torch.ops._C.marlin_gemm` in place. Dense class matrix: 12/12… |
| [V100-89](results/V100-89.md) | colibri: a three-tier expert engine, slower than llama.cpp here | The engine builds and runs on Volta: the server holds **8 529 MiB**, resident weights load in 5.2 s, and decode lands at **16.2 and 16.6 tok/s** on the two warm runs (mean over three… |
| [V100-90](results/V100-90.md) | FlashQLA-SM70: Gated DeltaNet | The V100 core executes and is accurate with a maximum deviation from the reference cycle of 0.0 on the form 1x512x2hx4kvxd128, time 0.5 ms compared to 575 ms for the Python cycle (1099x… |
| [V100-91](results/V100-91.md) | Recheck sm70-attn with head_dim 256 | **Positive.** Prefill, tokens per second: | Context | Fork `sm70-attn` 5e11845 | Our build dbaf582 | Delta | |---|---|---|---| | 8k | **1279.4** | 1178.9 | +8.5 % | | 16k | **1224.6** | 1100.9 | +11.2… |
| [V100-92](results/V100-92.md) | Fused dequant of quantized KV | A/B on one model (27B IQ3_S, 10.95 GiB, fits entirely) and the same flags (`-p 8192 -n 8 -ctk q8_0 -ctv q8_0 -r 1`): base build129 gives **799.82** TOPS prefilling, PR #31802 (HEAD… |
| [V100-93](results/V100-93.md) | Two-machine pipeline: V100 writes, 4060 Ti reviews | **Negative.** 20 tasks per mode, the same task set: | Metric | (a) both stages on the V100 | (b) writer + separate reviewer | |---|---|---| | Total | **26.52 s** (1.33 s/task) | **108.47 s** (5.42… |
| [V100-94](results/V100-94.md) | Images on 4060 Ti, code on V100 | **Mixed.** Mixed: the 4060 Ti reaches 1885 images per hour on the turbo preset and 519 at 30 steps, but it is slower than the V100 in all three modes, so moving the factory would not speed… |
| [V100-95](results/V100-95.md) | What a 4060 Ti can do that a V100 cannot | **Mixed.** Mixed: the desktop card pre-fills faster at mid context and equals the V100 at 8.5k tokens, but decodes 1.9x slower, so no tested task finishes sooner on it. Inference stays on the V100;… |
| [V100-97](results/V100-97.md) | Batch half-and-half: 20 tasks for both cards | Criterion 1.5x passed only on 14B: distributing 12 tasks on V100 and 8 on PC yields 1.53x compared to one V100 (20.46 → 13.38 s, n=3), on 7B it's 1.43x (10.62 → 7.43 s, n=2). Quality… |
| [V100-98](results/V100-98.md) | Llama.cpp RPC: one model on two cards | 27.11.2026, llama.cpp b12811 (00d5c142c, ready binaries ubuntu-cuda-12.8), Qwen3-30B-A3B Q4_K_M 17.28 GB (does not fit in 16 GB of one card). Split V100 + 4060 Ti via `--rpc` (`-dev… |
| [V100-99](results/V100-99.md) | Prompt-expander: LLM writes prompt for photographer | The hypothesis was partially confirmed, and the solution depends on the prompt length. 20 product positions via vikhr-nemo-12b: valid JSON 20/20, all three keys 20/20, English without… |
| [background-swap-three-methods](results/background-swap-three-methods.md) | background-swap-three-methods | **Positive.** Positive for the catalogue path: the deterministic white background wins on untouchable product pixels and cost, while img2img and inpainting stay for interior scenes where a prompt… |
| [code-loop-agentic](results/code-loop-agentic.md) | code-loop-agentic | **Negative.** Feedback is not the bottleneck: 0 of 8 with four iterations each, every patch syntactically valid and every one wrong, because the fixes need coordinated changes across files that the… |
| [code-loop-real-fixes](results/code-loop-real-fixes.md) | code-loop-real-fixes | **Negative.** Single-shot repair of real bugs with 12B models does not work: 0 of 18, though every patch was valid and safe. What does work in the same harness is retrieval (82.5 % recall@5 by file)… |
| [code-loop-whole-package](results/code-loop-whole-package.md) | code-loop-whole-package | **Negative.** Whole-package context does not rescue a 7B model: 0 of 5, and most returned files were unchanged. The useful outcome is the side finding that q4_0 KV corrupts generation while q8_0 does not. |
| [cudnn8-unblocks-graphics](results/cudnn8-unblocks-graphics.md) | cudnn8-unblocks-graphics | **Positive.** Switching to cuDNN 8 is the fix for fp16 convolutions on sm_70: all three tasks run, 480p video included; 720p still runs out of memory, so on this card the limit is memory, not the build. |
| [gpu-unlock-baseline](results/gpu-unlock-baseline.md) | gpu-unlock-baseline | Baseline only: the stock card was measured and the unlock was deliberately not installed, so this note answers "what we have now", not "what the unlock gives". No pass/fail is claimed. |
| [iclight-color-drift](results/iclight-color-drift.md) | iclight-color-drift | **Mixed.** Unsuitable for the catalogue: ΔE 24-37 against a threshold of 5-10. |
| [image-quality-checker](results/image-quality-checker.md) | image-quality-checker | **Negative.** The library is not printable: 0.1 % reaches A4 and 99.8 % is under 768 px, so upscaling is mandatory; the clipping flag is unusable, with 93.5 % false positives on flower close-ups. |
| [inkling-2-mini-loop-cycles](results/inkling-2-mini-loop-cycles.md) | inkling-2-mini-loop-cycles | Reasoning depth does not pay for short tasks: pass@1 stays flat at 0.475-0.525 across all three levels (spread ±0.15 at 95 %), while the high level doubles mean time per task (36.7 s vs… |
| [lora-monstera-no-benefit](results/lora-monstera-no-benefit.md) | lora-monstera-no-benefit | **Negative.** Training ran to completion on 30 monstera images and changed nothing visible in the product shots, so this LoRA is not worth keeping; the same budget is better spent on reference images… |
| [nemotron-bolt-e4b-fast-honest](results/nemotron-bolt-e4b-fast-honest.md) | nemotron-bolt-e4b-fast-honest | **Positive.** Positive with a caveat: the model reaches 113 tok/s and answers honestly on the tested questions, so it qualifies as the fast working model; SenseNova is blocked outright by the engine. |
| [olala-mini-unblocked-slow](results/olala-mini-unblocked-slow.md) | olala-mini-unblocked-slow | **Negative.** Negative against the card's own bar: the model can be made to run on the fork, but the throughput it reaches is far below the 140 tok/s criterion, so the MoE shape bought memory headroom… |
| [print-from-640-library](results/print-from-640-library.md) | print-from-640-library | **Mixed.** A4 at 310 dpi is print-ready after one x4 pass at 0.7 s per card; A3 is not (219 dpi) and needs a second tiled ESRGAN pass, which doubles sharpness on the same output size but costs… |
| [product-background-swap](results/product-background-swap.md) | product-background-swap | **Mixed.** Backgrounds can be replaced, the product cannot: product SSIM reaches 0.851 with depth conditioning while contour SSIM stays at 0.701, and the eye confirms redrawn petals and centres.… |
| [rag-nemotron-vs-vikhr](results/rag-nemotron-vs-vikhr.md) | rag-nemotron-vs-vikhr | **Negative.** Negative for the RAG role: Nemotron is twice as fast but three times more often wrong against the local vikhr model, so for customer-facing retrieval it loses on accuracy. |
| [shop-assistant-similar-products](results/shop-assistant-similar-products.md) | shop-assistant-similar-products | **Mixed.** Retrieval is fine and first choice is not: the right variant is in the top five 90 % of the time but first only 15 %, so the assistant must list the varieties instead of picking one,… |
| [ternary-bonsai-27b](results/ternary-bonsai-27b.md) | ternary-bonsai-27b | Mixed: the ternary 27B does run here and holds 6.8 GB, but the throughput it reaches decides whether the trade is worth it for the shop - see the measurement above. |
| [upscale-for-print](results/upscale-for-print.md) | Upscaling for print: ESRGAN vs UltraSharp, SUPIR blocked by the channel | **Mixed.** | Method | Time | Peak VRAM | Sharpness at 2560 | delta-E mean | delta-E max | |---|---|---|---|---|---| | LANCZOS (base) | 0,1 s | - | - | - | - | | Real-ESRGAN x4plus | 0,9 s | 2 722… |
| [video-cogvideox-blocked](results/video-cogvideox-blocked.md) | video-cogvideox-blocked | **Negative.** With cuDNN 9 video is blocked for a build reason, not a model limit: fp16 convolutions find no engine on sm_70, and without cuDNN the VAE asks 17.8 GiB. The fix is a cuDNN 8 environment,… |
| [vlm-card-controller-fails](results/vlm-card-controller-fails.md) | vlm-card-controller-fails | **Negative.** Negative: the 3B VLM accepted every card it was shown, good and bad alike, so as a controller it carries no signal - a human or a mechanical check still has to do the deciding. |

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
| V100-29b | V100-29 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-40b | V100-40 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-41b | V100-41 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-42b | V100-42 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-43b | V100-43 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-45b | V100-45 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-46b | V100-46 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-47b | V100-47 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-48b | V100-48 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-49b | V100-49 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-50b | V100-50 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-51b | V100-51 | re-measure and archive the raw output; the original run was not archived | 1 h |
| V100-52b | V100-52 | re-measure and archive the raw output; the original run was not archived | 1 h |

Total queued: **26** re-runs, roughly 40.5 h of GPU time.

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

## Related repositories

| Repository | What it adds |
|---|---|
| [onprem-llm-closed-loop](https://github.com/eightpaws/onprem-llm-closed-loop) | the same 16 GB card in an air-gapped stand: isolation verified by a script, not by a promise |
| [it-infra-audit-kit](https://github.com/eightpaws/it-infra-audit-kit) | read-only audit of Active Directory, Proxmox and backups, with risk levels |
| [eightpaws](https://github.com/eightpaws) | profile: what else is published and where |

This repository is the measurement layer: every number sits in a card with its command and its raw output.

## License

- Text, tables and measurement data: **CC BY 4.0** (`LICENSE`) — reuse with attribution.
- Code in `tools/`, `projects/` and snippets inside cards: **MIT** (`LICENSE-CODE`).

## Contributing

A number that does not reproduce is a useful report. Open a [measurement correction](https://github.com/eightpaws/v100-field-notes/issues/new?template=measurement_correction.yml) with your command and raw output; the card will be changed, not defended. What a card must contain is described in [CONTRIBUTING.md](CONTRIBUTING.md).
