<!-- curated: do not overwrite -->
# Code loop on real fixes — 0 of 18, and why that is the useful result

_Not synthetic tasks: real commits in `pypa/packaging` that changed both code and tests. For each, the test from the commit was kept, the source was reverted to the pre-commit state, the test was confirmed failing, the model got the file plus the pytest output, and the test was run again._

## Results

| Model | Tasks | Fixed | Valid syntax | Dangerous insertions | Seconds per task |
|---|---|---|---|---|---|
| vikhr-nemo 12B | 10 | **0** | 8 of 10 | 0 | 18.5 |
| DeepSeek-Coder-V2-Lite | 8 | **0** | 8 of 8 | 0 | 17 |

Both models emit syntactically valid Python, never insert `eval`, `exec`, `os.system` or `shell=True`, and touch nothing outside the file — the safety gate holds. Neither passes the real tests.

## Why zero, and not "almost"

The cause is the task shape, not model competence. Three things showed up in failure analysis:

1. **Real fixes almost always span more than one file.** In `packaging`, a fix pulls in the parser, the requirement model and validators; the prompt contained one file, so the model patched the symptom instead of the cause.
2. **The test from the commit often exercises new behaviour.** A large share of failures are `ImportError`/`AttributeError` on new functions — that is "write missing functionality to satisfy a test", not "find the bug".
3. **One pass is not enough.** The model never sees the result of its own patch: there is no apply-run-read-fix loop. That is the structural difference from an agentic setup.

## What this settles

A negative result closes a question: **single-shot repair of real bugs with 12B-class models does not work**, regardless of language or whether the model is code-specialised. A code loop needs either an agentic cycle that runs tests at every step, a much larger model, or both.

What already works in this same harness: code retrieval (82.5 % recall@5 by file) and the safety gate (0 dangerous insertions across 18 patches). Both can serve as the base of an agentic loop unchanged.

## Method

Repository `pypa/packaging`, 400 commits of history, 146 commits touching one source file plus tests. The task set is deterministic — fixed commit hashes, no seed. Acceptance is the pytest exit code on the commit's own test, never an AST comparison.

Script: `/srv/media/projects/code-real/real_fixes.py`; results `result.json`; logs `/srv/media/night/real_fixes*.log`.

## Limits

- One repository, one language, 18 tasks. Firm conclusions need 50+ tasks across at least two repositories.
- Models received only the single changed file; multi-file fixes are lost by construction.
- Not tested: 30B+ models (Qwen3-Coder-30B does not fit in 16 GB with KV), an agentic loop, or feeding the whole repository into context.
- The ControlNet-depth download for the neighbouring card crawled (129 MB of 2.5 GB in an hour), so the product work slipped.
