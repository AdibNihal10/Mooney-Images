"""
mooney_tool.py — turn normal images into Mooney images (CLI + importable core).

HOW A MOONEY IMAGE IS MADE (same recipe as Egger et al., "Inverse Rendering
Best Explains Face Perception Under Extreme Illuminations"):

    1. Convert the image to grayscale.
    2. Blur it with a Gaussian filter   -> removes fine texture, keeps big
                                           light/shadow regions.
    3. Threshold it to pure black/white -> every pixel becomes 0 or 255.

Instead of hand-picking a threshold per image, we fix the PERCENTAGE OF WHITE
PIXELS (the paper used 16%) and find the threshold that produces exactly that
percentage with a binary search. That makes all Mooneys comparable even when
images have different brightness.

Two knobs control everything:
    --sigma : blur strength (Gaussian standard deviation, in pixels)
    --white : percentage of pixels that end up white

USAGE
    # one image
    python mooney_tool.py input.png -o out/ --sigma 3 --white 16

    # a whole folder (batch mode), PNG/JPG inside
    python mooney_tool.py Original/ -o Mooney/ --sigma 3 --white 16

    # count the white % only inside the object (uses the PNG alpha channel)
    python mooney_tool.py Original/ -o Mooney/ --use-alpha

    # exact paper setting: 7x7 kernel, sigma 35, 16% white
    python mooney_tool.py Original/ -o Mooney/ --ksize 7 --sigma 35 --white 16

A log file (mooney_log.csv) with the parameters, chosen threshold and the
actual white percentage of every image is written next to the outputs.
"""

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


# --------------------------------------------------------------------------
# 1) Loading: grayscale + (optional) object mask from the alpha channel
# --------------------------------------------------------------------------
def load_gray_and_mask(path):
    """Read an image and return (grayscale float image, mask or None).

    If the PNG has an alpha channel (our 3D renders do), the object is
    composited onto a BLACK background and the alpha is returned as a mask
    so we can optionally count white pixels only on the object.
    """
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    return to_gray_and_mask(img)


def to_gray_and_mask(img):
    """Same as above but for an image already in memory (BGR / BGRA / gray)."""
    mask = None
    if img.ndim == 2:                       # already grayscale
        gray = img.astype(np.float32)
    elif img.shape[2] == 4:                 # BGRA -> composite on black
        alpha = img[:, :, 3].astype(np.float32) / 255.0
        bgr = img[:, :, :3].astype(np.float32) * alpha[..., None]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        mask = alpha > 0.5
    else:                                   # BGR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if gray.max() > 255:                    # 16-bit images
        gray = gray / 257.0
    return gray, mask


# --------------------------------------------------------------------------
# 2) Blur
# --------------------------------------------------------------------------
def gaussian_blur(gray, sigma, ksize=None):
    """Gaussian blur. ksize=None lets OpenCV pick a kernel that fits sigma
    (about 6*sigma wide). Pass ksize (odd int) to force a kernel size,
    e.g. ksize=7 to reproduce the paper's 7x7 filter."""
    if sigma <= 0:
        return gray.copy()
    k = (0, 0) if ksize is None else (int(ksize) | 1, int(ksize) | 1)  # force odd
    return cv2.GaussianBlur(gray, k, sigmaX=sigma, sigmaY=sigma)


# --------------------------------------------------------------------------
# 3) Threshold chosen by binary search on the white-pixel percentage
# --------------------------------------------------------------------------
def find_threshold(blurred, white_pct, mask=None, iterations=40):
    """Binary search for threshold t so that ~white_pct % of pixels > t.

    Pixels brighter than t become white. A higher t -> fewer white pixels.
    We search t in [min, max] of the image and halve the interval each step.
    """
    values = blurred[mask] if mask is not None else blurred.ravel()
    target = white_pct / 100.0
    lo, hi = float(values.min()), float(values.max())
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        frac_white = np.mean(values > mid)
        if frac_white > target:   # too much white -> raise threshold
            lo = mid
        else:                     # too little white -> lower threshold
            hi = mid
    return (lo + hi) / 2.0


def make_mooney(gray, sigma=3.0, white_pct=16.0, mask=None, ksize=None):
    """Full pipeline on a grayscale float image.

    Returns (mooney uint8 image, blurred image, threshold, actual white %).
    If a mask is given, the white % is measured on the object only and
    everything outside the object is forced to black.
    """
    blurred = gaussian_blur(gray, sigma, ksize)
    t = find_threshold(blurred, white_pct, mask)
    mooney = (blurred > t).astype(np.uint8) * 255
    if mask is not None:
        mooney[~mask] = 0
        actual = 100.0 * np.mean(mooney[mask] > 0)
    else:
        actual = 100.0 * np.mean(mooney > 0)
    return mooney, blurred, t, actual


# --------------------------------------------------------------------------
# Batch processing
# --------------------------------------------------------------------------
def list_images(path):
    path = Path(path)
    if path.is_file():
        return [path]
    return sorted(p for p in path.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)


def process(input_path, output_dir, sigma=3.0, white_pct=16.0,
            use_alpha=False, ksize=None, verbose=True):
    """Convert one image or every image in a folder. Output files keep the
    input file name (as .png) so originals and Mooneys line up 1:1."""
    files = list_images(input_path)
    if not files:
        raise SystemExit(f"No images found in {input_path}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for i, f in enumerate(files, 1):
        gray, mask = load_gray_and_mask(f)
        mooney, _, t, actual = make_mooney(
            gray, sigma, white_pct, mask if use_alpha else None, ksize)
        out_file = out / (f.stem + ".png")
        cv2.imwrite(str(out_file), mooney)
        rows.append([f.name, out_file.name, sigma, ksize or "auto",
                     white_pct, use_alpha, round(t, 3), round(actual, 2)])
        if verbose:
            print(f"[{i:>3}/{len(files)}] {f.name:<30} threshold={t:6.1f}  white={actual:5.1f}%")

    with open(out / "mooney_log.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["input", "output", "sigma", "ksize", "target_white_pct",
                    "use_alpha", "threshold", "actual_white_pct"])
        w.writerows(rows)
    if verbose:
        print(f"Done: {len(files)} Mooney image(s) written to {out}/")
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description="Generate Mooney images (blur + white-%% threshold).")
    p.add_argument("input", help="image file or folder of images")
    p.add_argument("-o", "--output", default="Mooney", help="output folder (default: Mooney)")
    p.add_argument("--sigma", type=float, default=3.0, help="Gaussian blur sigma in pixels (default 3)")
    p.add_argument("--white", type=float, default=16.0, help="percentage of white pixels (default 16)")
    p.add_argument("--ksize", type=int, default=None, help="force odd kernel size, e.g. 7 (default: auto)")
    p.add_argument("--use-alpha", action="store_true",
                   help="measure white %% on the object only (needs PNG with alpha)")
    a = p.parse_args(argv)
    if not 0 < a.white < 100:
        sys.exit("--white must be between 0 and 100")
    process(a.input, a.output, a.sigma, a.white, a.use_alpha, a.ksize)


if __name__ == "__main__":
    main()
