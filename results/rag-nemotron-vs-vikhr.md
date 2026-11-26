<!-- curated: do not overwrite -->
# Shop RAG assistant: Nemotron is twice as fast and three times more wrong

Whether to move the shop assistant's answerer from vikhr-nemo 12B to Nemotron-Bolt-E4B, which hit 113 tok/s on synthetic tests. Answer: no. Speed doubled, correct answers dropped 27 points.

## Setup

Same harness, same index, same 100 questions. Only the answerer server changed:

- **vikhr-nemo 12B** — llama.cpp, Q4, port 18460, 16k context.
- **Nemotron-Bolt-E4B** — llama.cpp (master 28148b5), UD-Q4_K_XL, port 18461, 8k context, `-fa on`, 4.0 GiB VRAM.

Retrieval was untouched, so recall and MRR matched exactly — a check that the comparison is fair.

## Results

| Metric | vikhr-nemo 12B | Nemotron-Bolt-E4B |
|---|---|---|
| recall@5 chunks | 83.8 % | 83.8 % |
| recall@5 pages | 88.8 % | 88.8 % |
| MRR | 0.809 | 0.809 |
| **answer correct** | **86.2 %** | **58.8 %** |
| answer incomplete | 7.5 % | 25.0 % |
| answer wrong | **6.2 %** | **16.2 %** |
| honest refusals | 100 % | 100 % |
| p50 | 1.15 s | **0.52 s** |
| p95 | 1.66 s | **0.94 s** |

Twice the speed, worse quality on both axes: fewer correct and three times more outright wrong. Refusals stay honest in both — where the context is missing, both models stay silent.

## Why

Nemotron is 7.52 B with 4.7 B active (`E4B`), vikhr-nemo is 12 B fine-tuned for Russian. On a task that requires pulling one fact out of five chunks without adding anything, size and specialisation tell: Nemotron more often paraphrases vaguely (hence 25 % incomplete) and more often fills in a detail absent from the context (hence 16.2 % wrong).

Its strength is text generation: product cards in JSON come out valid and fast at 99 tok/s, where a mistake costs less because the text is not a fact about the shop.

## Decision

- **The RAG assistant stays on vikhr-nemo 12B.** A 27-point gap in correct answers is not worth one second of latency.
- **Nemotron is used for text generation** (descriptions, cards, letters) where speed matters and fact verification does not.
- The Nemotron server on port 18461 was stopped and its VRAM released.

## What these numbers do not prove

- That Nemotron cannot be improved: prompt tuning, 16k context with `-fa`, and temperature were not explored. Some incomplete answers may be a prompt-format issue.
- That vikhr-nemo is the best choice: only one model was compared, and GLM-4.7-Flash scored 77.5 % on this harness before the prompt fix.
- That the judge is objective: the same judge as in earlier runs, and its bias applies equally to both models.

## Reproduction

```
ssh the GPU guest 'cd /srv/media/ai-cache/downloads/nemotron-bolt && \
  /home/hermes/llama-master/build/bin/llama-server \
  -m NVIDIA-Nemotron-3.5-Bolt-E4B-UD-Q4_K_XL.gguf -ngl 99 -c 8192 -fa on --port 18461'

ssh the GPU guest 'cd /srv/media/projects/shop-assistant && \
  RAG_LLM=http://127.0.0.1:18461/v1/chat/completions RAG_MODEL=nemotron ./run_eval.sh'
```

Log `/srv/media/night/rag_nemotron.log`. The vikhr-nemo baseline lives in the shop assistant card.

**Repeats.** Not recorded: repeatability was not documented for this run - treat the numbers as a single run unless the result says otherwise.

**Environment.** Tesla V100-SXM2-16GB (sm_70), driver 580, CUDA 12.9, guest VM on a home Proxmox host; engine and model as recorded in the run log.

**Does not show.** one run only - repeatability was not measured; the run log was not preserved, so the numbers cannot be re-checked from this repository; no second engine or model was measured on the same harness.

**Raw.** Not preserved for this run.

**Commands.** The command line was not recorded for this run.

**Question.** See the card title: the premise is stated in the field notes and was not carried into this export.

**Verdict.** Negative for the RAG role: Nemotron is twice as fast but three times more often wrong against the local vikhr model, so for customer-facing retrieval it loses on accuracy.

**Result type.** Negative.
