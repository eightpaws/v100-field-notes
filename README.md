# Tesla V100 (sm_70) — measured results

Field notes from one **Tesla V100-SXM2 16 GB** running inside a Proxmox VM (24 vCPU, 94 GiB RAM).
Every number below was measured on the card, not copied from a project README. Negative results are
published on purpose: they are the expensive part of anyone's time.

Closed experiments: **33** — 14 positive, 7 mixed,
3 negative. Follow-ups queued: **13** — each card names the re-run that closes its caveat, and the results are published here as they land.

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
| [V100-14](results/V100-14.md) | 24B in 16 GB: Mistral-Small-3.1-24B AWQ | Mistral Small 24B AWQ does not fit in 16 GB via vLLM. The model is fully downloaded (3 shards, 13.4 GB, all tensors are read), 1Cat-vLLM 1.5.4 compiled for sm_70 and has separate… |
| [V100-18](results/V100-18.md) | xllama.cpp: compress KV instead of q8 | Compressed KV in xllama.cpp works, but on long context it becomes too slow. Built with xllama.cpp f9287a9 (fork of llama.cpp from April 2026 with… |
| [V100-20](results/V100-20.md) | fni8: int8 dp4a for DiT | Rejected along with V100-22: this is the same fni8 package family (int8 dp4a for DiT in ComfyUI). The author himself writes that acceleration was measured on a CMP 100-210 park with… |
| [V100-22](results/V100-22.md) | fni8 for LLM: int8 dp4a instead of tensor cores | Rejected based on the author's documentation facts. fni8 (jajmangold/fni8, ComfyUI-fni8 package) is an int8 dp4a path through CUDA kernels, and it is designed for cards with… |
| [V100-26](results/V100-26.md) | llama.cpp build flags matrix for Volta | The build flag matrix was previously verified (CUDA 12.0, llama.cpp build b7743fbfd8, model 14B Q4_K, llama-bench pp512/tg128, median of three runs). Result: none of the flags… |
| [V100-28](results/V100-28.md) | V100-LLM: ready presets for 16 GB | Rejected: the release does not include the engine. Checked GitHub API for the Abdelhayali/V100-LLM repository, tag v1.3.0 - two assets: `LocalAI-Bridge-Desktop.exe` (8 MB) and… |
| [V100-29](results/V100-29.md) | V100-29 | **Positive.** The first configuration that puts a 27B dense model fully on the card and still decodes faster than the 30B MoE with CPU offload. Stock llama.cpp cannot read the PXQN4 file — the PXA… |
| [V100-30](results/V100-30.md) | sm70-attn: FA2-D256 in llama.cpp | Rejected based on the card criterion: "do we have a model with head_dim 256 and do we need context over 64k". The answer is no and no. What was actually checked: - We don't have models… |
| [V100-41](results/V100-41.md) | V100-41 | **Mixed.** Usable only with flash attention on and 4 expert layers pushed to CPU: 24 tok/s decode. Both faster coding candidates (DeepSeek-Coder-V2-Lite at 183 tok/s, Qwen3-Coder-30B at 75 tok/s)… |
| [V100-42](results/V100-42.md) | V100-42 | **Positive.** Yes: 8 expert layers on CPU is the entry threshold, and every extra layer costs both prefill and decode roughly linearly. At 8 layers a 17.3 GB model — 1.3 GB larger than the card —… |
| [V100-43](results/V100-43.md) | V100-43 | **Positive.** Prefix caching works and is the main reason to run llama-server for agent workloads: prompt processing drops from 845 ms to 89 ms (9.5x), round trip from 1.18 s to 0.39 s. |
| [V100-45](results/V100-45.md) | V100-45 | **Positive.** Working configuration is `-ngl 99 -ncmoe 8 -c 4096`. An 8192-token context needs more VRAM (compute buffer allocation fails), so long files require either 12 CPU layers or a smaller context. |
| [V100-46](results/V100-46.md) | V100-46 | **Positive.** Tool calling works correctly with the Qwen3-Coder chat template: valid JSON arguments, no extra calls, correct final answer. At 75 tok/s decode a conversational turn costs 2–3 s. |
| [V100-47](results/V100-47.md) | V100-47 | **Positive.** Best decode measured on this card by a wide margin: 183.6 tok/s with 2250 tok/s prefill, working configuration `-ngl 99 -fa 0`. Flash attention must be off — it is 160x slower on this… |
| [V100-48](results/V100-48.md) | V100-48 | **Mixed.** FIM works and is fast enough to type ahead of a human. Latency is unstable (126 ms to 1.5 s on the same prompt) — the old build's slot handling is the suspect; a single slot with… |
| [V100-49](results/V100-49.md) | V100-49 | **Positive.** Ranking is correct with a clear margin, and the 606 MB model handles a Russian query against English code without translation. Indexing a repository is a matter of minutes on this card. |
| [V100-50](results/V100-50.md) | V100-50 | **Positive.** +21% on a 7B target. The same draft on a 14B target slows decoding by 43% — the technique has to be measured per pair, not assumed. |
| [V100-51](results/V100-51.md) | V100-51 | **Mixed.** 32k is reachable only with compressed KV plus offloaded experts: `-c 32768 -ctk q8_0 -ctv q8_0 -ncmoe 16` gives 25 tok/s. Without compression the same window needs 24+ CPU layers and… |
| [V100-52](results/V100-52.md) | V100-52 | **Positive.** The loop closes locally in 15 seconds per iteration, which makes unattended refactoring and test-fixing practical. A dense 32B on the same card would run at 3 tok/s and be unusable for this. |

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
