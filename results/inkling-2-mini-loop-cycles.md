<!-- curated: do not overwrite -->
# Inkling 2 Mini on the V100: the loop core's cycles do not buy quality

Card V100-144, priority P2. The question was not "is it fast" but "does quality grow with `reasoning_effort`" — that is, do three passes through the same weights in the loop core pay off. Answer: on MBPP they do not.

**Verdict.** Reasoning depth does not pay for short tasks: pass@1 stays flat at 0.475-0.525 across all three levels (spread ±0.15 at 95 %), while the high level doubles mean time per task (36.7 s vs 17.1 s). Decode speed is unchanged at 34 tok/s.


## Configuration

`Inkling-2-Mini-UD-Q3_K_XL.gguf`, 13.63 GB, 26.4 B parameters with 3.4 B active, 128 experts with 8 per token. llama.cpp master build129, `-ngl 99 -c 8192 --jinja`, three `--reasoning-effort` levels.

The model fits entirely: **15 033 MiB** of 16 144 used, leaving almost nothing for context — 8192 tokens fit, 16k on the same card would not.

## Numbers

40 MBPP tasks per level, single run, acceptance by running the tests:

| Level | pass@1 | Mean time | Mean answer | tok/s | Truncated by cap |
|---|---|---|---|---|---|
| none | 0.500 (20/40) | 17.1 s | 583 tok | 34.1 | 5 of 40 |
| medium | **0.525** (21/40) | 18.3 s | 623 tok | 34.1 | 7 of 40 |
| high | 0.475 (19/40) | 36.7 s | 1240 tok | 33.8 | 8 of 40 |

At 40 tasks and p≈0.5 the spread is about ±0.15 at 95 %, so all three rows are statistically indistinguishable. Medium beat none by one task; high trailed by one and cost twice as much.

Decode speed is identical across levels (33.8-34.1 tok/s): the loop core neither speeds up nor slows down with reasoning depth, only answer length grows.

## The trap that made the first measurement wrong

The first high run used a 1400-token cap and reported 0.375 (15/40). That would have been read as "high level is worse", but 13 of 40 answers hit exactly 1400 — the model never got to write code after its reasoning.

A rerun with a 3000 cap gave 0.475. A 10-point gap on the same level is the price of the cap, not of the model. Rule stands: for reasoning models, count truncated answers before looking at pass@1.

## What it means for the contour

For this class of task (short MBPP functions) reasoning depth is not needed: 34 tok/s and 0.5 pass@1 on none, in half the time per task. High only pays where the task needs a long chain — and on our hardware a 27B model with an external plan (Ternary-Bonsai) gives 0.55 at 67 tok/s in 6.8 GB instead of 15.

So Inkling is interesting not for MBPP quality but because 26.4 B parameters fit into 16 GB at Q3_K_XL with solid Russian text and agent-style answers. For an agentic contour it is a workable option, with one caveat: the model occupies 15 GB, so nothing else runs on the card alongside it.

## What these numbers do not prove

- That the levels are equivalent on long tasks: MBPP is short functions where reasoning is barely needed.
- That 0.475-0.525 is the model's ceiling: only levels were compared, no external models on the same 40 tasks.
- That high does not help in agentic scenarios: different task type, untested.
- That Q3_K_XL holds quality versus Q2: single quantisation.

## Reproduction

```
ssh the GPU guest
/home/hermes/venvs/cu121/bin/python mbpp_inkling.py none medium high      # 1400 cap
MAXTOK=3000 /home/hermes/venvs/cu121/bin/python mbpp_inkling.py high      # 3000 cap
```

Raw data: `/srv/media/night/v144_{none,medium,high}_40.json`, summary `v144_summary_40.json`, logs `/srv/media/night/mbpp_inkling*.log`.

**Repeats.** Not recorded: repeatability was not documented for this run - treat the numbers as a single run unless the result says otherwise.

**Environment.** Tesla V100-SXM2-16GB (sm_70), driver 580, CUDA 12.9, guest VM on a home Proxmox host; engine and model as recorded in the run log.

**Does not show.** one run only - repeatability was not measured; the run log was not preserved, so the numbers cannot be re-checked from this repository.

**Raw.** Not preserved for this run.

**Commands.** The command line was not recorded for this run.

**Question.** See the card title: the premise is stated in the field notes and was not carried into this export.
