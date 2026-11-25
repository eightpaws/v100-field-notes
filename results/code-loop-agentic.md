<!-- curated: do not overwrite -->
# Agentic repair loop — running the tests at every step still leaves 12B at zero

_Follow-up to the real-fix experiment. This time the model does not patch blind: the loop is apply → run pytest → read the output → fix again, up to four steps per task. Same `pypa/packaging` task set, same acceptance criterion — the test's exit code._

## Result

| Metric | Value |
|---|---|
| Tasks | 8 |
| Fixed | **0** |
| Mean steps per task | 4.0 (hit the ceiling) |
| Dangerous insertions | 0 |
| Seconds per task | 66.8 |

Model: DeepSeek-Coder-V2-Lite. Same commits as the single-pass run, which also scored 0 of 8. Feedback changed nothing.

## What it means

The loop itself works: the model reads the failure text, patches, fails again, patches again — four times. Every patch is syntactically valid, contains no forbidden constructs, and every one misses.

The failure pattern explains it: these fixes require coordinated changes across the parser, the requirement model and the validators, while the model holds one file. Four iterations on one file do not become a cross-file change; that requires handing it the whole package and allowing several files per step.

**Practical consequence for the loop we are building:** 12B-class local models are not yet suitable for repairing real bugs, even with tests in the loop. They are suitable for narrow tasks — implement a function to satisfy a test, fix a single line from a traceback, explain a failure. Tasks of that size are solvable (see the gate: zero dangerous insertions, valid syntax throughout).

## Cost and method

Script `/srv/media/projects/code-real/agent_loop.py`, results `loop_result.json`, log `/srv/media/night/agent_loop2.log`. The model server is restarted automatically when it dies: llama.cpp with this checkpoint survives only a few dozen requests, so the loop probes the port and restarts the unit.

## Limits

- Eight tasks, one repository, one language.
- One file per step, at most four steps: multi-file fixes are out of reach by construction.
- The model is 16B-MoE with 2.4B active, not 30B+; larger does not fit 16 GB with KV.
- Not tested: feeding the whole package into context, allowing multi-file edits, or an external linter as feedback.
