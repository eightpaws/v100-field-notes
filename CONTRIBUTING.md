# Contributing

Two kinds of contributions are useful here: a measurement that contradicts a card, and a fix to the tooling. Both are welcome, and both have a shape that makes them easy to act on.

## A number that does not reproduce

Open a **Measurement correction** issue. Without these fields the report cannot be checked, and it will be closed with a request for them:

| Field | Why it is needed |
|---|---|
| Card ID (`V100-16`) | so the card can be corrected, not the whole repository |
| Your GPU and compute capability | sm_70 results do not transfer to sm_75 or sm_80 |
| Driver, engine and version (`llama.cpp` commit, Ollama tag) | the flags on the card are version-specific |
| The exact command you ran | a reconstruction cannot be compared with a transcript |
| Your output, raw | a summary hides the difference that matters |
| What you expected and what you got | so the card can be changed in the right place |

If your number is close but not equal, say by how much before anyone argues about causes. Single runs disagree by a few percent routinely; the card says `single run` where it measured once, so treat that band as noise rather than as a contradiction.

## A new measurement

A card is accepted when it answers a question that changes a decision. Before writing one, check `results/` for the same question: duplicates get merged, not published twice.

Every card carries these blocks, in this order:

1. `**Question.**` — what is being tested and what a pass looks like, as a number.
2. `**Environment.**` — GPU, compute capability, driver, engine and version, OS and kernel, the flags that matter, paths to weights.
3. `**Results.**` — a table of metric, value, unit.
4. `**Repeats.**` — `n` and spread, or an explicit `single run`.
5. `**Verdict.**` — one sentence: what a reader should do with this number.
6. `**Result type.**` — `Positive`, `Mixed` or `Negative`.
7. `**Does not show.**` — the clean comparison that was not made.
8. `**Raw.**` — path to the raw output, or an explicit statement that the log was lost.

Negative results are published on purpose. They cost the most time to discover and save the most time to read.

## Code changes

- Run the consistency gate before opening a pull request: `python3 tools/check_index.py`. It fails when a card exists on disk but is missing from `raw/index.json`, when the README table disagrees with the index, or when a raw JSON file does not parse.
- Cards are English-only. Russian text lives outside this repository, in a private wiki.
- No em dashes in `results/`: the repository uses a plain hyphen so copy-paste cannot turn a minus into a dash.
- One card per file: `results/V100-NN.md`, with the number taken from the file name, never re-derived from the integer.
- A hand-written card starts with `<!-- curated: do not overwrite -->` so the generator leaves it alone.

## License

By contributing text, tables or measurement data you agree to license them under CC BY 4.0. By contributing code (`tools/`, `projects/`, snippets) you agree to license it under the MIT license. See `LICENSE` and `LICENSE-CODE`.
