"""
Vision system 2 — Surface normal estimation with Marigold (diffusion-based).

Question: the paper's best model of human perception was the one that
reconstructs SHAPE. Surface normals are shape: does a modern network still
recover them when the image is reduced to black/white blobs?

Input : ../Original/*.png and ../Mooney/*.png
Output: ../Result2/<split>/<name>.png   normal map (RGB = xyz direction)
        ../Result2/<split>/<name>.npy   raw normals, camera space
        ../Result2/metrics.csv          mean angular error (deg) vs. GT normals

    python run_normals.py --limit 2
    python run_normals.py
    python run_normals.py --steps 4 --ensemble 3     # slower, slightly better

Axis conventions differ between programs (is +y up or down?). We pick the
sign convention that best fits the ORIGINAL renders and then apply the same
one to the Mooneys, so the comparison stays fair.
"""

import itertools

import numpy as np
import torch
from diffusers import MarigoldNormalsPipeline

from common import (SPLITS, MetricsWriter, angular_error_deg, base_args, category_of,
                    foreground_mask, list_images, load_gt, load_rgb, pick_device)


def main():
    p = base_args("Marigold normals on originals and Mooneys", "Result2")
    p.add_argument("--model", default="prs-eth/marigold-normals-v1-1")
    p.add_argument("--steps", type=int, default=None, help="denoising steps (default: model's own)")
    p.add_argument("--ensemble", type=int, default=1, help="average N predictions")
    p.add_argument("--fp32", action="store_true",
                   help="full precision on GPU (use on GTX 16xx cards if outputs are black/NaN)")
    a = p.parse_args()
    root = __import__("pathlib").Path(a.root)
    device = pick_device(a.device)
    dtype = torch.float16 if device == "cuda" and not a.fp32 else torch.float32

    pipe = MarigoldNormalsPipeline.from_pretrained(
        a.model, variant="fp16" if dtype == torch.float16 else None, torch_dtype=dtype).to(device)

    # 1) run the model and save everything
    done = {s: [] for s in SPLITS}
    for split in SPLITS:
        out = root / a.result / split
        out.mkdir(parents=True, exist_ok=True)
        files = list_images(root / split, a.limit)
        for i, f in enumerate(files, 1):
            res = pipe(load_rgb(f), num_inference_steps=a.steps, ensemble_size=a.ensemble,
                       generator=torch.Generator(device=device).manual_seed(0))
            pred = np.asarray(res.prediction[0], dtype=np.float32)       # H x W x 3 in [-1, 1]
            np.save(out / f"{f.stem}.npy", pred)
            pipe.image_processor.visualize_normals(res.prediction)[0].save(out / f"{f.stem}.png")
            done[split].append(f)
            print(f"[{split} {i:>3}/{len(files)}] {f.name}")

    # 2) choose axis signs on the originals, then score both splits
    def err(f, split, sign):
        gt, mask = load_gt(root, "normal", f.stem), foreground_mask(root, f.stem)
        if gt is None:
            return np.nan
        pred = np.load(root / a.result / split / f"{f.stem}.npy") * sign
        return angular_error_deg(pred, gt, mask)

    signs = [np.array(s, np.float32) for s in itertools.product([1, -1], repeat=3)]
    best = min(signs, key=lambda s: np.nanmean([err(f, "Original", s) for f in done["Original"]] or [np.nan]))
    print(f"Axis sign convention chosen on originals: {best.tolist()}")

    metrics = MetricsWriter(root / a.result / "metrics.csv",
                            ["file", "split", "category", "mean_angular_error_deg", "axis_signs"])
    for split in SPLITS:
        for f in done[split]:
            metrics.add([f.name, split, category_of(f), round(err(f, split, best), 2), str(best.tolist())])
    metrics.save()


if __name__ == "__main__":
    main()
