<!-- curated: do not overwrite -->
# Code loop — retrieval works, auto-repair benchmark does not

_Goal: the agent finds the right code in its own repositories, applies a patch, and a machine verifies the result. The first half worked. The second did not, and the numbers say so._

## What was built

Code corpus of **1703 blocks** (functions and classes) from **267 Python files** in `/srv/media/projects/shop-assistant` and `/home/hermes`. `site-packages`, `.venv`, llama.cpp build trees and third-party trees were excluded — otherwise the sample contained sympy tests and lldb providers.

Code: `/srv/media/projects/code-rag` (`code_corpus.py`, `code_eval.py`, `code_behave.py`).

## Code retrieval — 40 questions

Questions of the form "where is the function `name` defined and what does it do"; ground truth is the file that defines it.

| Metric | Value |
|---|---|
| recall@5 by file | 82.5 % |
| MRR | 0.667 |

For comparison, the same BM25 pipeline scored 88.8 % on the shop corpus. Code is harder: function names repeat and the vocabulary is poorer.

## Function repair — and why the metric is invalid

Design: take a function, break one operation (`+` to `-`, `==` to `!=`), hand the model the broken version, check whether it restored the logic.

Results on 9 tasks:

| Metric | Value |
|---|---|
| Patch compiles | 100 % |
| AST matches the original | 22.2 % |
| Dangerous insertions (`eval`, `exec`, `shell=True`, `os.system`) | **0** |
| Latency | 2.9 s |
| Behavioural agreement on identical arguments | **0 %** |

The behavioural number is meaningless, and the reason matters: the sample contained test helpers, converters and debugger providers that cannot be called on synthetic arguments. Eight of nine tasks either cannot be invoked without setup or raise on every supplied argument, so the comparison degenerates.

AST agreement is also pessimistic: the model rewrites code in its own words, so a functionally identical function has a different parse tree. Both metrics measure shape, not correctness.

## Conclusion

**Retrieval over own repositories is done and measured. Automatic verification of repair is not.** Mutating random functions is not a substitute for a task set with real tests: it needs functions with coverage, or real defects from the issue log with reproductions.

To make the second half honest:
1. build 20 tasks from real commits: before/after from git history plus the test that failed before and passes after;
2. acceptance = running those tests, not comparing ASTs;
3. the safety gate (`eval`, `exec`, `shell=True`, `os.system`) must run on every model output, not only during measurement — it already holds: zero insertions across nine patches.

## Limits

- One language, own repositories, 267 files. Foreign codebases untested.
- Nine repair tasks is far too few for any claim about repair ability.
- The model was vikhr-nemo 12B, not a code-specialised one. Code models on the card (Qwen3-Coder-30B, DeepSeek-Coder-V2-Lite) were not compared.

**Does not show.** one run only - repeatability was not measured; the run log was not preserved, so the numbers cannot be re-checked from this repository; no second engine or model was measured on the same harness.

**Raw.** Not preserved for this run.

**Environment.** Tesla V100-SXM2-16GB (sm_70), driver 580, CUDA 12.9, guest VM on a home Proxmox host; engine and model as recorded in the run log.

**Commands.** The command line was not recorded for this run.

**Question.** See the card title: the premise is stated in the field notes and was not carried into this export.

**Repeats.** Not recorded: repeatability was not documented for this run - treat the numbers as a single run unless the result says otherwise.
