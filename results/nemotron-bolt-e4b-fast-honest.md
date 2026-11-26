<!-- curated: do not overwrite -->
# Nemotron-Bolt-E4B on the V100: 113 tok/s and honest answers

Card V100-78. Two models checked for fast shop copy. One qualified, the other stays unavailable to the engine.

## SenseNova-Loop-9B: blocked for good

The file is intact (5.82 GB, Q4_K_M), but neither build 129 nor a fresh llama.cpp master (28148b5) knows the `sensenova_loop` architecture: master supports only `sensenova_u1`. So this is not a matter of updating the build — upstream carries a different model variant. Keeping the file makes no sense.

## Nemotron-Bolt-E4B: qualified

`NVIDIA-Nemotron-3.5-Bolt-E4B-UD-Q4_K_XL.gguf` from unsloth: 4.70 GiB on disk, 7.52 B parameters, and the GGUF architecture is named `gemma4` — which explains why new builds load it while the older 129 does not.

`llama-bench`, 2 repetitions:

| Test | Result |
|---|---|
| pp256 | 4 281 ± 1 200 tok/s |
| tg64 | **113.1 ± 0.4 tok/s** |

In real generation through `llama-cli`: 98.8-100.3 tok/s, prefill 269-449 tok/s.

## Quality checks

**JSON format 5/5.** Prompt: a product card with fields name, description, care, price_rub. The answer is fully valid:

```json
{
  "name": "Монстера в белом керамическом горшке (60 см)",
  "description": "Элегантная и эффектная монстера, идеально подходящая для современного интерьера. Высота растения 60 см, представлена в стильном белом керамическом горшке, который подчеркивает природную красоту растения.",
  "care": "Требует яркого, но рассеянного света. Поливать умеренно, когда верхний слой почвы просохнет. Предпочитает высокую влажность. Регулярно удалять сухие листья.",
  "price_rub": 3800
}
```

**Honesty passed.** Asked about the delivery price of a bouquet to Kazan tomorrow morning, the model did not invent a figure: "Уточните в конкретном цветочном магазине или службе доставки. Цены зависят от букета и магазина."

**Volume and language** are fine: the description is to the point, Russian is clean, the price came out as a placeholder of 3800 (the model itself noted in its reasoning that the price is nominal).

## What it means for the contour

Nemotron-Bolt-E4B works as the shop copy model: 113 tok/s on the benchmark, about 100 in chat, valid JSON, honest refusals, 4.7 GiB of memory. That is faster than the vikhr-nemo 12B currently answering in the RAG assistant, with far more headroom.

Limitation: the model runs in thinking mode and spends 200-400 tokens before answering. JSON needs `-n 1400`, otherwise the answer is cut mid-object.

## Build

Fresh llama.cpp master: commit 28148b5, `-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=70`, nvcc CUDA 12.9, g++-12; targets `llama-bench llama-cli llama-server` build with no patches (unlike the olala fork, which needed three). Binaries in `/home/hermes/llama-master/build/bin/`.

Important: cmake is not on PATH over non-interactive ssh; use `/home/hermes/venvs/tools/lib/python3.12/site-packages/cmake/data/bin`.

## What these numbers do not prove

- That the model is better than vikhr-nemo in quality: comparison covers speed and two checks only; the full harness (RAG, injections, format across 20 tasks) was not run.
- That 113 tok/s holds at long context: measured at pp256, throughput drops at 16k.
- That the model never confabulates: one honesty question was tested, not a suite.

## Reproduction

```
ssh ai-gpu 'cd /srv/media/ai-cache/downloads/nemotron-bolt && \
  /home/hermes/llama-master/build/bin/llama-bench \
  -m NVIDIA-Nemotron-3.5-Bolt-E4B-UD-Q4_K_XL.gguf -p 256 -n 64 -ngl 99 -r 2'
```
