#!/usr/bin/env python3
"""Сверяет карточки, индекс и README. Ловит то, что глазами не видно.

Три проверки:
  1. у каждой карточки results/V100-*.md есть запись в raw/index.json;
  2. каждая запись индекса указывает на существующую карточку;
  3. число экспериментов в README совпадает с числом записей индекса;
  4. все json в raw/runs разбираются.

Код возврата 1, если расхождение: именно так терялись карточки V100-60, V100-80, V100-82.
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
    print("нет raw/index.json")
    sys.exit(1)

index = json.loads(INDEX.read_text(encoding="utf-8"))
records = index if isinstance(index, list) else index.get("runs", [])
index_ids = {str(r.get("id")) for r in records}

cards = {p.stem for p in RESULTS.glob("V100-*.md")}

missing_in_index = sorted(cards - index_ids)
missing_cards = sorted(index_ids - cards)

if missing_in_index:
    errors.append(f"карточки без записи в индексе: {', '.join(missing_in_index)}")
if missing_cards:
    errors.append(f"записи индекса без карточки: {', '.join(missing_cards)}")

readme = README.read_text(encoding="utf-8")
m = re.search(r"Closed experiments:\s*\*\*(\d+)\*\*", readme)
if not m:
    errors.append("в README нет строки «Closed experiments: N»")
elif int(m.group(1)) != len(records):
    errors.append(f"README говорит {m.group(1)} экспериментов, в индексе {len(records)}")

runs = list((ROOT / "raw" / "runs").glob("*.json"))
bad = []
for f in runs:
    try:
        json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        bad.append(f"{f.name}: {e.msg}")
if bad:
    errors.append("не разбираются: " + "; ".join(bad))

print(f"карточек: {len(cards)}, записей в индексе: {len(records)}, файлов замеров: {len(runs)}")
if errors:
    for e in errors:
        print("::error::" + e)
    sys.exit(1)
print("согласовано")
