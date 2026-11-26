<!-- curated: do not overwrite -->
# LoRA on monstera: training succeeded, no visible benefit

Card V100-101 — "LoRA for product and brand". Trained on 30 monstera images from the library, RealVisXL V5 base, 800 steps, 512 resolution. Training took 18 minutes at 8.6 GiB VRAM.

## What worked mechanically

- Base converted from a single checkpoint into a shard-free diffusers folder: `base-sdxl2`, 6.2 GB.
- Dataset: 30 images plus `metadata.jsonl` with captions and the `flrmonstera` trigger.
- Loss at step 800 was 0.045; checkpoints saved at 400 and 800.
- LoRA file: `sd-model-finetuned-lora/pytorch_lora_weights.safetensors`.
- Generation at 768×768, 25 steps: 5.0-5.2 s, 8.6 GiB peak.

## Three-way check

| Variant | SSIM to base |
|---|---|
| no LoRA (control) | 1.000 |
| LoRA without trigger | 0.741 |
| LoRA with trigger | 0.731 |
| LoRA with trigger vs LoRA without trigger | 0.888 |

Reading: the LoRA does change the image (0.74 to base), but the **trigger word changes almost nothing** (0.888 between the two LoRA variants). A properly trained LoRA has the trigger switch a character or style wholesale.

## Eyes-on review

- The RealVisXL base already draws a monstera in a white pot on a neutral background: glossy leaves, fenestrations, soft light from the left, wooden table.
- With the LoRA the image changes, but towards "a different monstera" rather than "our brand".
- Defects are the same either way: extra bridges between leaf segments and overly thin leaf tips.

## Verdict

A LoRA over 30 heterogeneous photos gives no brand result: too little data and no single style to learn. The model learns "monstera in general", which the base already knows.

To make a useful LoRA the dataset must be homogeneous on the exact trait needed: same background, same pot type, same lighting scheme, 100-150 frames, then 1500-2500 steps. It must also be evaluated differently: not SSIM between variants but similarity to the dataset (CLIP or a manual checklist of traits: background colour, pot shape, light angle).

For the current print and catalogue work the right tool is the base model plus a prompt: 5 seconds per image, adequate quality, nothing to train.

## Environment notes (for future training)

A separate version set is required, otherwise everything breaks:

- torch 2.3.1+cu121 with torchvision 0.18.1+cu121. Any dependency can replace torch with a build lacking cuDNN 8, which makes `torchvision::nms` vanish and takes transformers and peft down with it.
- diffusers 0.29.2, because 0.31 requires torch ≥ 2.4.
- accelerate 1.x rejects `--report_to none`; tensorboard is needed.
- bitsandbytes 0.50 requires torch ≥ 2.4 and had to be removed.
- The training base must be saved shard-free with `variant="fp16"`, otherwise the script cannot find the weights.

Scripts: `lora_prep.py`, `train_lora_029.py`, `lora_control2.py` in `/srv/media/projects/lora/`, logs `/srv/media/night/lora_*.log`.

**Repeats.** Not recorded: repeatability was not documented for this run - treat the numbers as a single run unless the result says otherwise.

**Environment.** Tesla V100-SXM2-16GB (sm_70), driver 580, CUDA 12.9, guest VM on a home Proxmox host; engine and model as recorded in the run log.

**Does not show.** one run only - repeatability was not measured; the run log was not preserved, so the numbers cannot be re-checked from this repository.

**Raw.** Not preserved for this run.

**Commands.** The command line was not recorded for this run.

**Question.** See the card title: the premise is stated in the field notes and was not carried into this export.

**Result type.** Negative - the LoRA trained without error and produced no visible change on the
product shots, so the criterion (a measurable likeness gain on 30 monstera images) was not met.

**Verdict.** Training ran to completion on 30 monstera images and changed nothing visible in the
product shots, so this LoRA is not worth keeping; the same budget is better spent on reference
images per SKU than on a brand-wide adapter.
