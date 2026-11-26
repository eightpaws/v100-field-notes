<!-- curated: do not overwrite -->
# What the 4060 Ti can do that the V100 cannot

Card V100-95, priority P1: are there tasks better routed to the PC not for speed but for capability. Answer: yes, and the bf16 gap is larger than the V100's fp16 advantage.

## Capabilities (identical code, torch, 8192³)

| Precision | V100 (sm_70) | 4060 Ti (sm_89) | Note |
|---|---|---|---|
| fp16 | **97.8 TFLOPS** | 42.1 | V100 is 2.3× faster |
| bf16 | 10.8 (**11 %** of fp16) | **43.7** (104 % of fp16) | on V100 this is software emulation |
| fp8 e4m3 | none (`_scaled_mm` needs sm_80+) | **78.5 TFLOPS** | V100 has no hardware fp8 at all |
| fp8 e5m2 | none | none (matmul unsupported on Ada too) | — |

Plus what earlier cards established: FlashAttention 2 requires sm_80 or newer (V100-88), Marlin INT4 runs on Ada while sm_70 needs a workaround (V100-87).

## Task-level measurement: a training step

Linear layer 4096×4096, batch 8×1024 tokens, forward+backward+SGD, 5 steps after warmup.

| Card | fp16 | bf16 |
|---|---|---|
| V100 | 6.7 ms (122.7 TFLOPS) | **50.1 ms** (16.5 TFLOPS) |
| 4060 Ti | 16.2 ms (50.9 TFLOPS) | **15.5 ms** (53.2 TFLOPS) |

In fp16 the V100 is 2.4× faster. In bf16 the **PC is 3.2× faster** (15.5 vs 50.1 ms), and on the PC bf16 costs nothing against fp16 (15.5 vs 16.2 ms).

This is the task where the PC wins at equal quality: bf16 and fp16 carry the same representation precision, but the V100 computes bf16 by emulation.

## Routing rule

| Task | Where | Why |
|---|---|---|
| bf16 fine-tuning, LoRA, any bf16 pipeline | **4060 Ti** | 3.2× faster on the task, fp8 in reserve |
| fp8 inference | **4060 Ti** | no such path on V100 |
| Models with FlashAttention 2 | **4060 Ti** | sm_70 unsupported |
| Heavy fp16 inference, long context, large models | **V100** | 97.8 TFLOPS and 900 GB/s vs 288 |
| Images, video, upscaling | **V100** | proven: cuDNN 8 and 15.7 GB for models |
| Code and RAG | **V100** | proven on real tasks |

## What these numbers do not prove

- That bf16 on V100 is always 9× slower: it depends on tensor shape; this is one 8192³ slice and one training step.
- That fp8 on the PC speeds up a real model: measured raw matmul, without activation quantisation or overheads.
- That Marlin INT4 is faster on the PC: vLLM was not brought up under Windows and no Marlin figures were taken on Ada.
- Memory bandwidth and decode throughput were not measured: 288 GB/s on the 4060 Ti vs 900 GB/s on the V100 — a separate test.

## Reproduction

```
# on the PC
/d/venvs/image/Scripts/python.exe caps_bench.py
/d/venvs/image/Scripts/python.exe caps_fp8.py
/d/venvs/image/Scripts/python.exe train_step_bench.py

# on the V100
ssh ai-gpu 'cd /srv/media/projects && /home/hermes/venvs/cu121/bin/python caps_bench.py'
```

Scripts `caps_bench.py`, `caps_fp8.py`, `train_step_bench.py` live in the PC home directory and in `/srv/media/projects/` on ai-gpu.
