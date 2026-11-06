"""
Vision system 3 — Zero-shot object recognition with CLIP.

Question: can a model trained on 400M internet image-text pairs still tell
WHICH object it sees once the image is a Mooney? This is the closest modern
analogue to the paper's "invariance" models (VGG-Face).

How it works: CLIP compares the image with the sentences
"a photo of a teapot.", "a photo of a mug.", ... (one per category of our
20 objects) and returns a probability for each. Chance level = 1/20 = 5%.

Input : ../Original/*.png and ../Mooney/*.png
Output: ../Result3/<split>/<name>.json   top-5 labels with probabilities
        ../Result3/metrics.csv           correct top-1 / top-3, prob. of true class

    python run_clip.py --limit 2
    python run_clip.py
    python run_clip.py --template "a black and white image of a {}."   # try other prompts
"""

import json

from transformers import pipeline

from common import (SPLITS, MetricsWriter, base_args, category_of, list_images,
                    load_rgb, pick_device)


def main():
    p = base_args("CLIP zero-shot recognition on originals and Mooneys", "Result3")
    p.add_argument("--model", default="openai/clip-vit-large-patch14")
    p.add_argument("--template", default="a photo of a {}.")
    a = p.parse_args()
    root = __import__("pathlib").Path(a.root)
    device = pick_device(a.device)

    labels = sorted({category_of(f) for f in list_images(root / "Original")})
    print(f"{len(labels)} candidate labels: {labels}")
    clf = pipeline("zero-shot-image-classification", model=a.model, device=device)

    metrics = MetricsWriter(root / a.result / "metrics.csv",
                            ["file", "split", "category", "top1", "top1_correct", "top3_correct", "p_true"])
    for split in SPLITS:
        out = root / a.result / split
        out.mkdir(parents=True, exist_ok=True)
        files = list_images(root / split, a.limit)
        for i, f in enumerate(files, 1):
            preds = clf(load_rgb(f), candidate_labels=labels, hypothesis_template=a.template)
            truth = category_of(f)
            ranked = [r["label"] for r in preds]
            p_true = next(r["score"] for r in preds if r["label"] == truth)
            with open(out / f"{f.stem}.json", "w") as fh:
                json.dump({"true": truth, "top5": preds[:5]}, fh, indent=2)
            metrics.add([f.name, split, truth, ranked[0], int(ranked[0] == truth),
                         int(truth in ranked[:3]), round(p_true, 4)])
            print(f"[{split} {i:>3}/{len(files)}] {f.name:<28} -> {ranked[0]:<12} (true: {truth}, p={p_true:.2f})")
    metrics.save()


if __name__ == "__main__":
    main()
