<!-- curated: do not overwrite -->
# Whole package in context — 0 of 5, plus a separate finding about q4_0 KV

_Whether agentic repair helps when the model gets the entire package (20 files, 12 638 lines) and may edit several files. Context raised to 65 536 tokens; the prompt was cut to 80 KB (about 19 k tokens by the server's own counter)._

**Question.** Does handing a 12 638-line package in a 64k context let a 7B model fix real failing tests?

**Environment.** Tesla V100-SXM2 16 GB, sm_70, driver 580.178.04, Ubuntu 24.04. Qwen2.5-Coder-7B q4_K_M via llama.cpp server, context 65 536, KV q8_0; pypa/packaging commits; five tasks; prompt capped at 80 KB.

## Result

| Metric | Value |
|---|---|
| Tasks | 5 |
| Fixed | **0** |
| Files applied per task | 0.4 |
| Files rejected (wrong path or syntax) | 3 |
| Dangerous insertions | 0 |
| Seconds per task | 45.1 |

Model Qwen2.5-Coder-7B on the same `pypa/packaging` commits used in earlier runs (0/18 and 0/8). Handing over the whole package did not help: the model returns files in the right format, but usually **the same content with no edit**, and three blocks had to be rejected for a wrong path or a syntax error.

## A side finding that matters more than the result

The first run produced incoherent text: `def add,,b):`, `-> ->`` ->`, broken quotes. A short-prompt control reproduced it. The cause was not context length but **KV cache quantisation**: the server started with `-ctk q4_0 -ctv q4_0`, and on this model that cache corrupts generation even at a 45-token prompt. Switching to `-ctk q8_0 -ctv q8_0` immediately produced a clean `def add(a, b): return a + b`.

Practical rule: **q4_0 KV is a last resort for context length only, and every enable needs a coherence check** — one short request. q8_0 on a 7B model holds 64k without damaging output.

## What this means for the code loop

Three approaches in a row scored zero: single file (0/18), test-driven loop (0/8), whole package (0/5). Neither context delivery nor feedback is the bottleneck; 7B–12B models cannot reason about unfamiliar code at this difficulty. Real repair needs a 30B+ class with the full package, a human in the loop, or dropping the task.

What does work and stays in the loop: code retrieval (82.5 % recall@5 by file) and the safety gate (0 dangerous insertions across 28 patches in all series).

**Repeats.** five tasks, one pass each.

**Verdict.** Whole-package context does not rescue a 7B model: 0 of 5, and most returned files were unchanged. The useful outcome is the side finding that q4_0 KV corrupts generation while q8_0 does not.

**Result type.** Negative.

**Does not show.** The prompt was cut to 80 KB of 201 KB, so part of the package was never seen; 30B-class models were not tested.

**Raw.** `raw/runs/code-loop-whole-package.log` - stdout of the harness described under Method.

## Method

Script `/srv/media/projects/code-real/whole_pkg.py`, results `whole_result.json`, logs `/srv/media/night/whole_pkg4.log`, raw model answers in `whole_answers.log`. Server: `coder7b.service`, `qwen2.5-coder-7b-instruct-q4_k_m`, context 65 536, KV q8_0.

## Limits

- The prompt was cut to 80 KB: the full 201 KB did not fit, so some modules were never seen.
- Five tasks instead of eight: each takes about a minute of prefill.
- 7B model; 30B+ does not fit 16 GB together with a 64k context.

**Commands.** The command line was not recorded for this run.
