"""
common.py — shared helpers for the 4 vision-system scripts.

Every run_*.py script follows the same pattern:

    for split in ["Original", "Mooney"]:
        for each image in ../<split>/:
            run the model  ->  save output to ../Result<N>/<split>/<same name>
    write ../Result<N>/metrics.csv (one row per image and split)

Keeping the same file names everywhere means Original/obj03_mug_L2.png,
Mooney/obj03_mug_L2.png and Result1/Mooney/obj03_mug_L2.png all belong
together, which makes comparing them trivial.
"""

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent      # the compvp_part1 folder
SPLITS = ["Original", "Mooney"]


def base_args(description, result_name):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--root", default=str(ROOT), help="project folder containing Original/ and Mooney/")
    p.add_argument("--result", default=result_name, help="output folder name, e.g. Result1")
    p.add_argument("--limit", type=int, default=0, help="only the first N images (smoke test)")
    p.add_argument("--device", default=None, help="cuda / cpu (default: cuda if available)")
    return p


def pick_device(requested=None):
    import torch
    if requested:
        return requested
    if torch.cuda.is_available():
        print(f"Using GPU: {torch.cuda.get_device_name(0)}")
        return "cuda"
    print("WARNING: no CUDA GPU visible to PyTorch -> using CPU (slow). See GUIDE.md, Step 3.0.")
    return "cpu"


def list_images(folder, limit=0):
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    return files[:limit] if limit else files


def load_rgb(path):
    """Load as RGB PIL image. Transparent backgrounds (our renders) become black;
    grayscale Mooneys become 3-channel, so every model gets the same input type."""
    img = Image.open(path)
    if img.mode in ("RGBA", "LA"):
        black = Image.new("RGBA", img.size, (0, 0, 0, 255))
        img = Image.alpha_composite(black, img.convert("RGBA"))
    return img.convert("RGB")


def category_of(path):
    """obj03_teddy_bear_L2.png -> 'teddy bear'"""
    stem = Path(path).stem
    return " ".join(stem.split("_")[1:-1])


def foreground_mask(root, stem):
    """Object pixels = where the ground-truth depth is > 0 (from the renderer)."""
    gt = Path(root) / "GT" / "depth" / f"{stem}.npy"
    return (np.load(gt) > 0) if gt.exists() else None


def load_gt(root, kind, stem):
    f = Path(root) / "GT" / kind / f"{stem}.npy"
    return np.load(f) if f.exists() else None


class MetricsWriter:
    def __init__(self, path, header):
        self.path, self.header, self.rows = Path(path), header, []

    def add(self, row):
        self.rows.append(row)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(self.header)
            w.writerows(self.rows)
        print(f"Metrics -> {self.path}")


# ----------------------------- metrics ------------------------------------
def spearman(a, b):
    """Rank correlation: 1 = same ordering of near/far, 0 = unrelated."""
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    return float(np.corrcoef(ra, rb)[0, 1])


def depth_metrics(pred_disparity, gt_depth, mask):
    """Compare a RELATIVE depth prediction to ground truth on object pixels.

    Monocular models output relative inverse depth (disparity) with unknown
    scale and shift, so we (1) fit scale+shift to GT disparity by least
    squares, then (2) report AbsRel in depth space and the Spearman
    rank correlation (which needs no fitting at all).
    """
    m = mask & (gt_depth > 0)
    if m.sum() < 50:
        return float("nan"), float("nan")
    p, g = pred_disparity[m].astype(np.float64), 1.0 / gt_depth[m].astype(np.float64)
    A = np.stack([p, np.ones_like(p)], 1)
    s, t = np.linalg.lstsq(A, g, rcond=None)[0]
    aligned = np.clip(s * p + t, 1e-6, None)
    absrel = float(np.mean(np.abs(1.0 / aligned - gt_depth[m]) / gt_depth[m]))
    return absrel, spearman(p, g)


def angular_error_deg(pred, gt, mask):
    """Mean angle (degrees) between predicted and GT normals on object pixels."""
    m = mask & (np.linalg.norm(gt, axis=-1) > 0.5)
    if m.sum() < 50:
        return float("nan")
    a = pred[m] / (np.linalg.norm(pred[m], axis=-1, keepdims=True) + 1e-8)
    b = gt[m] / (np.linalg.norm(gt[m], axis=-1, keepdims=True) + 1e-8)
    return float(np.degrees(np.arccos(np.clip((a * b).sum(-1), -1, 1))).mean())
