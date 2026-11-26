#!/usr/bin/env python3
"""V100-05: IC-Light - пересвет товарного фото под сцену.

Метрики: время, VRAM, ΔE (CIE76) по трём точкам товара между оригиналом и результатом.
"""
import faulthandler
import json
import math
import os
import time

import cv2
import numpy as np
import safetensors.torch as sf
import torch
from diffusers import (AutoencoderKL, DPMSolverMultistepScheduler,
                       StableDiffusionImg2ImgPipeline, StableDiffusionPipeline,
                       UNet2DConditionModel)
from diffusers.models.attention_processor import AttnProcessor2_0
from PIL import Image
from transformers import CLIPTextModel, CLIPTokenizer

ROOT = "/srv/media/projects/iclight"
SD15 = f"{ROOT}/rv51"
WEIGHTS = f"{ROOT}/models/iclight_sd15_fc.safetensors"
SRC = "/srv/media/generated/images/v100_2411_1208"
OUT = f"{ROOT}/out"
os.environ["HF_HOME"] = "/srv/media/ai-cache/hf"

faulthandler.enable()
os.makedirs(OUT, exist_ok=True)

W, H = 512, 512
STEPS = 30

SCENES = {
    "теплый_интерьер": ("warm interior lighting, soft window light from the left, cozy living room",
                        "bright studio light, gray background, harsh shadows"),
    "холодная_студия": ("cool studio lighting from the right, product photography, neutral gray background",
                        "warm light, yellow cast, window, interior"),
    "солнечное_утро": ("morning sunlight from the left, soft shadows on a white table, airy bright scene",
                       "dark, night, artificial light, harsh contrast"),
}
A_PROMPT = "best quality, detailed product photo"
N_PROMPT = "lowres, bad quality, blurry, deformed, changed shape, altered color"

device = torch.device("cuda")


def build():
    tok = CLIPTokenizer.from_pretrained(SD15, subfolder="tokenizer")
    te = CLIPTextModel.from_pretrained(SD15, subfolder="text_encoder")
    vae = AutoencoderKL.from_pretrained(SD15, subfolder="vae")
    unet = UNet2DConditionModel.from_pretrained(SD15, subfolder="unet")

    with torch.no_grad():
        new_conv_in = torch.nn.Conv2d(8, unet.conv_in.out_channels, unet.conv_in.kernel_size,
                                      unet.conv_in.stride, unet.conv_in.padding)
        new_conv_in.weight.zero_()
        new_conv_in.weight[:, :4, :, :].copy_(unet.conv_in.weight)
        new_conv_in.bias = unet.conv_in.bias
        unet.conv_in = new_conv_in

    orig_forward = unet.forward

    def hooked(sample, timestep, encoder_hidden_states, **kwargs):
        c = kwargs["cross_attention_kwargs"]["concat_conds"].to(sample)
        c = torch.cat([c] * (sample.shape[0] // c.shape[0]), dim=0)
        kwargs["cross_attention_kwargs"] = {}
        return orig_forward(torch.cat([sample, c], dim=1), timestep, encoder_hidden_states, **kwargs)

    unet.forward = hooked

    sd_offset = sf.load_file(WEIGHTS)
    sd_origin = unet.state_dict()
    unet.load_state_dict({k: sd_origin[k] + sd_offset[k] for k in sd_origin}, strict=True)
    del sd_offset, sd_origin

    te = te.to(device=device, dtype=torch.float16)
    vae = vae.to(device=device, dtype=torch.bfloat16)
    unet = unet.to(device=device, dtype=torch.float16)
    unet.set_attn_processor(AttnProcessor2_0())
    vae.set_attn_processor(AttnProcessor2_0())

    sched = DPMSolverMultistepScheduler(num_train_timesteps=1000, beta_start=0.00085,
                                        beta_end=0.012, algorithm_type="sde-dpmsolver++",
                                        use_karras_sigmas=True, steps_offset=1)
    kwargs = dict(vae=vae, text_encoder=te, tokenizer=tok, unet=unet, scheduler=sched,
                  safety_checker=None, requires_safety_checker=False,
                  feature_extractor=None, image_encoder=None)
    return tok, te, vae, StableDiffusionPipeline(**kwargs), StableDiffusionImg2ImgPipeline(**kwargs)


def encode(tok, te, txt):
    ids = tok(txt, truncation=False, add_special_tokens=False)["input_ids"]
    chunks = [[tok.bos_token_id] + ids[i:i + tok.model_max_length - 2] + [tok.eos_token_id]
              for i in range(0, len(ids), tok.model_max_length - 2)]
    chunks = [c[:tok.model_max_length] if len(c) >= tok.model_max_length
              else c + [tok.eos_token_id] * (tok.model_max_length - len(c)) for c in chunks]
    t = torch.tensor(chunks, device=device, dtype=torch.int64)
    return te(t).last_hidden_state


def pair(tok, te, pos, neg):
    c, uc = encode(tok, te, pos), encode(tok, te, neg)
    n = max(len(c), len(uc))
    c = torch.cat([c] * math.ceil(n / len(c)), dim=0)[:n]
    uc = torch.cat([uc] * math.ceil(n / len(uc)), dim=0)[:n]
    return torch.cat([p[None] for p in c], dim=1), torch.cat([p[None] for p in uc], dim=1)


def to_t(arr):
    return (torch.from_numpy(np.stack([arr])).float() / 127.0 - 1.0).movedim(-1, 1)


def to_np(x):
    y = x.movedim(0, -1) * 127.5 + 127.5
    return y.detach().float().cpu().numpy().clip(0, 255).astype(np.uint8)


def center_crop(arr, w, h):
    im = Image.fromarray(arr)
    ow, oh = im.size
    s = max(w / ow, h / oh)
    im = im.resize((int(round(ow * s)), int(round(oh * s))), Image.LANCZOS)
    rw, rh = im.size
    return np.array(im.crop(((rw - w) / 2, (rh - h) / 2, (rw + w) / 2, (rh + h) / 2)))


def resize(arr, w, h):
    return np.array(Image.fromarray(arr).resize((w, h), Image.LANCZOS))


def relight(img, tok, te, vae, t2i, prompt, neg, seed=3):
    fg = center_crop(img, W, H)
    cc = to_t(fg).to(device=vae.device, dtype=vae.dtype)
    cc = vae.encode(cc).latent_dist.mode() * vae.config.scaling_factor
    conds, unconds = pair(tok, te, prompt, neg)
    g = torch.Generator(device=device).manual_seed(seed)
    lat = t2i(prompt_embeds=conds, negative_prompt_embeds=unconds, width=W, height=H,
              num_inference_steps=STEPS, generator=g, output_type="latent",
              guidance_scale=2.0, cross_attention_kwargs={"concat_conds": cc}).images
    return to_np(vae.decode(lat.to(vae.dtype) / vae.config.scaling_factor).sample[0])


def delta_e(a, b, pts):
    lab_a = cv2.cvtColor(a, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab_b = cv2.cvtColor(b, cv2.COLOR_BGR2LAB).astype(np.float32)
    # cv2 LAB: L 0-255, a/b 0-255 со сдвигом 128; переводим к стандартным единицам
    out = []
    for (x, y) in pts:
        pa, pb = lab_a[y, x], lab_b[y, x]
        la, aa, ba = pa[0] * 100 / 255, pa[1] - 128, pa[2] - 128
        lb, ab, bb = pb[0] * 100 / 255, pb[1] - 128, pb[2] - 128
        out.append(round(float(np.sqrt((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2)), 1))
    return out


def main():
    files = sorted([f for f in os.listdir(SRC) if f.endswith(".jpg")])[:10]
    print("фото:", len(files), flush=True)
    tok, te, vae, t2i, _ = build()
    print("модели подняты", flush=True)

    rows = []
    for fn in files:
        img = cv2.imread(os.path.join(SRC, fn))
        h, w = img.shape[:2]
        cx, cy = w // 2, int(h * 0.55)
        pts = [(cx, cy), (max(0, cx - w // 6), cy), (min(w - 1, cx + w // 6), cy)]
        for name, (prompt, neg) in SCENES.items():
            t0 = time.time()
            out = relight(img, tok, te, vae, t2i, f"{prompt}, {A_PROMPT}", f"{neg}, {N_PROMPT}")
            secs = round(time.time() - t0, 1)
            de = delta_e(center_crop(img, W, H), out, [(x * W // w, y * H // h) for x, y in pts])
            path = os.path.join(OUT, f"{fn[:16]}_{name}.jpg")
            cv2.imwrite(path, cv2.cvtColor(out, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 93])
            rows.append({"file": fn[:16], "сцена": name, "секунд": secs,
                         "dE_центр": de[0], "dE_слева": de[1], "dE_справа": de[2],
                         "dE_среднее": round(sum(de) / 3, 1)})
            print(f"{fn[:16]:18} {name:16} ΔE {rows[-1]['dE_среднее']:5} | {secs} с", flush=True)

    if rows:
        summary = {"пар": len(rows),
                   "dE_среднее": round(sum(r["dE_среднее"] for r in rows) / len(rows), 1),
                   "dE_максимум": max(r["dE_среднее"] for r in rows),
                   "секунд_на_фото": round(sum(r["секунд"] for r in rows) / len(rows), 1),
                   "VRAM_пик_МиБ": round(torch.cuda.max_memory_allocated() / 2 ** 20)}
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        json.dump({"summary": summary, "rows": rows},
                  open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
