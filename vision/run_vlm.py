"""
Vision system 4 — Vision-language model (Qwen3-VL) describing what it sees.

Question: when we just ASK a modern multimodal model "what is this?", does it
recognise the object in the Mooney, describe it as abstract blobs, or
hallucinate something else? Unlike CLIP it gets NO list of answers.

Input : ../Original/*.png and ../Mooney/*.png
Output: ../Result4/<split>/<name>.txt   the model's raw answer
        ../Result4/metrics.csv           answer + automatic "contains the true name" check

    python run_vlm.py --limit 2
    python run_vlm.py
    python run_vlm.py --choices      # also give it the list of 20 names (multiple choice)
    python run_vlm.py --model Qwen/Qwen3-VL-4B-Instruct     # bigger, needs ~10 GB VRAM

The automatic check is strict string matching ("mug" in answer). Look over
metrics.csv by hand afterwards ("cup" for a mug is arguably right) and
mention that in the slides.
"""

import torch
from transformers import AutoModelForImageTextToText, AutoProcessor

from common import (SPLITS, MetricsWriter, base_args, category_of, list_images,
                    load_rgb, pick_device)

PROMPT = ("What object is shown in this image? Answer exactly in this format:\n"
          "OBJECT: <one or two words>\nDESCRIPTION: <one short sentence about what you see>")


def main():
    p = base_args("Qwen3-VL description of originals and Mooneys", "Result4")
    p.add_argument("--model", default="Qwen/Qwen3-VL-2B-Instruct")
    p.add_argument("--choices", action="store_true", help="give the model the list of object names")
    p.add_argument("--max-new-tokens", type=int, default=60)
    p.add_argument("--fp32", action="store_true",
                   help="full precision (use on GTX 16xx cards if answers are empty/garbage)")
    a = p.parse_args()
    root = __import__("pathlib").Path(a.root)
    device = pick_device(a.device)

    if device == "cuda" and not a.fp32:
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    else:
        dtype = torch.float32
    model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=dtype).to(device).eval()
    processor = AutoProcessor.from_pretrained(a.model)

    prompt = PROMPT
    if a.choices:
        labels = sorted({category_of(f) for f in list_images(root / "Original")})
        prompt += "\nThe object is one of: " + ", ".join(labels) + "."

    metrics = MetricsWriter(root / a.result / "metrics.csv",
                            ["file", "split", "category", "object_answer", "auto_correct", "full_answer"])
    for split in SPLITS:
        out = root / a.result / split
        out.mkdir(parents=True, exist_ok=True)
        files = list_images(root / split, a.limit)
        for i, f in enumerate(files, 1):
            messages = [{"role": "user", "content": [
                {"type": "image", "image": load_rgb(f)},
                {"type": "text", "text": prompt}]}]
            inputs = processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_dict=True, return_tensors="pt").to(device)
            with torch.no_grad():
                gen = model.generate(**inputs, max_new_tokens=a.max_new_tokens, do_sample=False)
            answer = processor.batch_decode(gen[:, inputs["input_ids"].shape[1]:],
                                            skip_special_tokens=True)[0].strip()
            (out / f"{f.stem}.txt").write_text(answer, encoding="utf-8")

            obj = answer.split("OBJECT:")[-1].split("\n")[0].strip().lower() if "OBJECT:" in answer else answer.lower()
            truth = category_of(f)
            correct = int(truth in obj or any(w in obj for w in truth.split() if len(w) > 3))
            metrics.add([f.name, split, truth, obj, correct, answer.replace("\n", " | ")])
            print(f"[{split} {i:>3}/{len(files)}] {f.name:<28} -> {obj[:30]:<30} (true: {truth})")
    metrics.save()


if __name__ == "__main__":
    main()
