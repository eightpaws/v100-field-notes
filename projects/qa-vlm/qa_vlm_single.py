#!/usr/bin/env python3
"""Тот же VLM, но по одной карточке в полном разрешении."""
import json
import os
import re
import time

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

MODEL = "Qwen/Qwen2.5-VL-3B-Instruct"
OUT = "/srv/media/projects/qa-vlm"
SRC = "/srv/media/generated/images/v100_2411_1208"
os.environ["HF_HOME"] = "/srv/media/ai-cache/hf"

PROMPT = ("Оцени эту карточку товара для интернет-магазина. Ответь строго двумя частями: "
          "сначала слово ДА или НЕТ, затем через точку с запятой причину, если НЕТ "
          "(обрезан товар, мелко, мыло, лишние предметы, артефакты), иначе слово ок. "
          "Критерий: товар виден целиком, крупно, без посторонних предметов, без артефактов.")


def main():
    meta = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL, torch_dtype=torch.float16, device_map="cuda")
    proc = AutoProcessor.from_pretrained(MODEL)

    rows = []
    t_all = time.time()
    for item in meta:
        path = os.path.join(SRC, item["file"])
        img = Image.open(path).convert("RGB")
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PROMPT}]}]
        text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = proc(text=[text], images=[img], return_tensors="pt").to("cuda")
        t0 = time.time()
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=60, do_sample=False)
        secs = round(time.time() - t0, 1)
        ans = proc.batch_decode(out[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0].strip()
        m = re.match(r"\W*(ДА|НЕТ)\b\W*(.*)", ans.upper())
        verdict = bool(m and m.group(1) == "ДА")
        reason = (m.group(2) if m else ans)[:60]
        rows.append({"n": item["n"], "file": item["file"], "px": item["px"],
                     "резкость": item["резкость"], "ответ": verdict,
                     "причина": reason, "секунд": secs})
        print(f"{item['n']:2} {'ДА ' if verdict else 'НЕТ'} {reason:45} {secs} с", flush=True)

    summary = {"карточек": len(rows),
               "секунд_всего": round(time.time() - t_all, 1),
               "секунд_на_карточку": round(sum(r["секунд"] for r in rows) / len(rows), 1),
               "годных": sum(1 for r in rows if r["ответ"]),
               "VRAM_пик_МиБ": round(torch.cuda.max_memory_allocated() / 2 ** 20)}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    json.dump({"summary": summary, "rows": rows},
              open(os.path.join(OUT, "vlm_single.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
