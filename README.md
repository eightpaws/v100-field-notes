# Tesla V100 (sm_70) — measured results

Field notes from a single Tesla V100-SXM2 16 GB running inside a Proxmox VM (24 vCPU, 96 GB RAM, driver 580).
Everything below was measured on the card, not copied from a README. Negative results are published on purpose:
they are the expensive part.

Closed experiments: **9** of 42.

| Idea | What | Result |
|---|---|---|
| [V100-02](results/V100-02.md) | KV-кэш q8_0 → контекст 32–64k | q8_0 KV поиск не портит (иголка 3/3 на 6496 токенах, как и fp16) и на 16k даёт вдвое быстрее генерацию - 44 против 21 tok/s, плюс 2 ГБ свободной VRAM  |
| [V100-10](results/V100-10.md) | Prefill и батчинг: где V100 теряет на самом деле | prefill 1776 tok/s при `num_batch=2048` против 587 при 128 и 1351 при дефолтных 512 - ×3 к 128 и +31 % к 512, на 1k, 8k и 16k лучший именно 2048. На 1 |
| [V100-16](results/V100-16.md) | Патчи volta-fa к llama.cpp | собрали llama.cpp с 4 из 8 патчей (остальные не легли - base-commit в патчах не указан). Против Ollama: decode 70,65 против 65,8 tok/s (+7,4 %), prefi |
| [V100-19](results/V100-19.md) | GQA→MHA: тихий фолбэк внимания в ComfyUI | подтверждено - GQA на sm_70 тихо уходит в math-путь: 4,63 TF/s против 33,15 у MHA (×7,2), на 8192 токенах math съедает 8 ГБ и падает в OOM. Расширение |
| [V100-36](results/V100-36.md) | Видео без RAM-потолка: длина клипа и 720p | RAM не был потолком: RSS процесса 41,6 ГБ на всех длинах, VRAM 12,7-13,0 ГБ. 480p (20 шагов): 97/145/193 кадра ок - 176/283/416 с; 241 и 321 - OOM. 72 |
| [V100-11](results/V100-11.md) | Кэш KV системного промпта | Кэш префикса работает и в llama.cpp, и в Ollama, но llama.cpp выигрывает на правке хвоста. 2k префикс: холодно 1047 мс, повтор 663 мс, правка хвоста 9 |
| [V100-24](results/V100-24.md) | DRY-сэмплер и бюджет рассуждений | DRY-штраф не подтвердился на нашей модели: на пяти обычных задачах и на двух специально зацикливающих (120 сортов роз по номерам, 80 строк лога) доля  |
| [V100-37](results/V100-37.md) | 32B dense и 30B MoE: пере-замер декода при 96 ГБ | Потолок и при 96 ГБ RAM остаётся в 16 ГБ карты. Плотная 32B Q4 (18,5 ГБ) при 20 слоях на GPU: prefill 253, decode 3,0 tok/s; при 40 и 99 слоях llama-b |
| [V100-39](results/V100-39.md) | TTFT и загрузка моделей при тёплом кэше | Тёплый кэш страниц меняет картину в разы. llama.cpp: холодный запуск 22,4 с, тёплый повтор 3,2 с - в 7 раз быстрее. Ollama 14B: после выгрузки модели  |

Units: `tok/s` = generated tokens per second, `prefill` = prompt processing, `VRAM` from `nvidia-smi`.
Full cards (hypothesis, method, risks, raw numbers) are in `results/`.

## Method

Each card lists what was run, on which model and context, and how it was measured. Where a number depends on
conditions (cold vs warm start, KV type, batch size), the condition is written next to it — a bare number here
means the configuration is stated in the card.

## License

Results and text: CC BY 4.0 — reuse with attribution.
