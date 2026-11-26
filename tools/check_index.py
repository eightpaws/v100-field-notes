#!/usr/bin/env python3
"""Cross-checks cards, index and README, and catches what the eye does not.

Checks:
  1. every card in results/ (not only V100-*.md — hand-written cards carry slug
     names) is published in raw/index.json, or carries an explicit
     `<!-- unpublished: reason -->` marker on its first line;
  2. every index record points at a card that exists, and ids are unique;
  3. the README count and the number of table rows match the index;
  4. every json in raw/runs parses;
  5. every `raw/runs/<file>` reference in a card points at a file that exists.

Exit code 1 on any mismatch. Silent drift is how V100-60, V100-80 and V100-82 were
lost: the cards were on disk, the index did not know about them. The same hole
reopened with slug-named cards in November 2026: nine cards sat in git, invisible
to the index and to the README table, while this script reported "consistent".
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "raw" / "index.json"
RESULTS = ROOT / "results"
README = ROOT / "README.md"
errors = []

if not INDEX.exists():
    print("::error::raw/index.json is missing")
    sys.exit(1)

index = json.loads(INDEX.read_text(encoding="utf-8"))
records = index if isinstance(index, list) else index.get("runs", [])
ids = [str(r.get("id")) for r in records]
index_ids = set(ids)

cards = {p.stem for p in RESULTS.glob("*.md") if p.name != "README.md"}
declared = {p.stem for p in RESULTS.glob("*.md")
            if p.name != "README.md"
            and p.read_text(encoding="utf-8").startswith("<!-- unpublished:")}

missing_in_index = sorted(cards - index_ids - declared)
missing_cards = sorted(index_ids - cards)
dupes = sorted({i for i in ids if ids.count(i) > 1})

if missing_in_index:
    errors.append("cards on disk but neither published nor marked unpublished: "
                  + ", ".join(missing_in_index)
                  + " (add it to raw/index.json and the README table, or start the card with"
                  " '<!-- unpublished: reason -->')")
if missing_cards:
    errors.append("index records without a card file: " + ", ".join(missing_cards))
if dupes:
    errors.append("duplicate index ids: " + ", ".join(dupes))

readme = README.read_text(encoding="utf-8")
m = re.search(r"Closed experiments:\s*\*\*(\d+)\*\*", readme)
rows = re.findall(r"\|\s*\[([A-Za-z0-9._\-]+)\]\(results/", readme)
if not m:
    errors.append("README has no 'Closed experiments: N' line")
elif int(m.group(1)) != len(records):
    errors.append(f"README says {m.group(1)} experiments, the index has {len(records)}")
if len(rows) != len(records):
    errors.append(f"README table has {len(rows)} rows, the index has {len(records)} records")
if sorted(rows) != sorted(ids):
    only_rows = sorted(set(rows) - index_ids)
    only_index = sorted(index_ids - set(rows))
    errors.append("README table and index disagree"
                  + (f"; only in README: {', '.join(only_rows)}" if only_rows else "")
                  + (f"; only in index: {', '.join(only_index)}" if only_index else ""))

runs = list((ROOT / "raw" / "runs").glob("*.json"))
bad = []
for f in runs:
    try:
        json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        bad.append(f"{f.name}: {e.msg}")
if bad:
    errors.append("unparsable raw files: " + "; ".join(bad))

# Ссылка на несуществующий файл замеров читается как обещание данных, которых нет.
runs_dir = ROOT / "raw" / "runs"
have_runs = {p.name for p in runs_dir.iterdir() if p.is_file()}
dangling = []
for p in RESULTS.glob("*.md"):
    if p.name == "README.md":
        continue
    for ref in re.findall(r"raw/runs/([A-Za-z0-9._\-]+)", p.read_text(encoding="utf-8")):
        if ref not in have_runs:
            dangling.append(f"{p.stem} -> {ref}")
if dangling:
    errors.append("cards point at raw files that do not exist: " + ", ".join(sorted(set(dangling))))

print(f"cards: {len(cards)}, index records: {len(records)}, raw files: {len(runs)}, "
      f"declared unpublished: {len(declared & cards)}")
if errors:
    for e in errors:
        print("::error::" + e)
    sys.exit(1)
print("consistent")
