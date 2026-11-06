"""
Vision system 1 — Monocular depth estimation with Depth Anything V2.

Question: does the model still recover the 3D shape (near vs far) from a
Mooney image, or only from the original render?

Input : ../Original/*.png and ../Mooney/*.png
Output: ../Result1/<split>/<name>.png   coloured depth map (bright = near)
        ../Result1/<split>/<name>.npy   raw prediction (relative inverse depth)
        ../Result1/metrics.csv          AbsRel + Spearman vs. ground-truth depth

    python run_depth.py --limit 2          # smoke test
    python run_depth.py                    # all 200 images
    python run_depth.py --model depth-anything/Depth-Anything-V2-Base-hf   # bigger model
"""

import cv2
import numpy as np
import torch
from transformers import pipeline

from common import (SPLITS, MetricsWriter, base_args, category_of, depth_metrics,
                    foreground_mask, list_images, load_gt, load_rgb, pick_device)


def main():
    p = base_args("Depth Anything V2 on originals and Mooneys", "Result1")
    p.add_argument("--model", default="depth-anything/Depth-Anything-V2-Small-hf")
    a = p.parse_args()
    root = __import__("pathlib").Path(a.root)
    device = pick_device(a.device)

    depth = pipeline("depth-estimation", model=a.model, device=device)
    metrics = MetricsWriter(root / a.result / "metrics.csv",
                            ["file", "split", "category", "absrel", "spearman"])

    for split in SPLITS:
        out = root / a.result / split
        out.mkdir(parents=True, exist_ok=True)
        files = list_images(root / split, a.limit)
        for i, f in enumerate(files, 1):
            img = load_rgb(f)
            with torch.no_grad():
                pred = depth(img)["predicted_depth"].squeeze().float().cpu().numpy()
            pred = cv2.resize(pred, img.size, interpolation=cv2.INTER_LINEAR)
            np.save(out / f"{f.stem}.npy", pred.astype(np.float32))

            vis = (pred - pred.min()) / (pred.max() - pred.min() + 1e-8)
            cv2.imwrite(str(out / f"{f.stem}.png"),
                        cv2.applyColorMap((vis * 255).astype(np.uint8), cv2.COLORMAP_INFERNO))

            mask, gt = foreground_mask(root, f.stem), load_gt(root, "depth", f.stem)
            absrel, rho = depth_metrics(pred, gt, mask) if gt is not None else (np.nan, np.nan)
            metrics.add([f.name, split, category_of(f), round(absrel, 4), round(rho, 4)])
            print(f"[{split} {i:>3}/{len(files)}] {f.name:<28} AbsRel={absrel:.3f}  Spearman={rho:.3f}")
    metrics.save()


if __name__ == "__main__":
    main()
