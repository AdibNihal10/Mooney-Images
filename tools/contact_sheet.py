"""
contact_sheet.py — put many images into one grid picture (with file names).

Use it to (1) preview candidate meshes, (2) compare 100 Mooneys quickly when
picking the top 10, (3) make the "10 originals + 10 Mooneys" slide.

    python contact_sheet.py ../Original -o sheet_original.png --cols 10
    python contact_sheet.py ../Mooney  -o sheet_mooney.png  --cols 10 --size 160
    python contact_sheet.py ../Original ../Mooney -o pairs.png --cols 10   # row pairs: original above Mooney
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

EXTS = {".png", ".jpg", ".jpeg"}


def load(path, size):
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:                      # transparent -> black background
        a = img[:, :, 3:4].astype(np.float32) / 255
        img = (img[:, :, :3] * a).astype(np.uint8)
    return cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)


def tile(img, label, size):
    canvas = np.full((size + 18, size, 3), 40, np.uint8)
    canvas[:size] = img
    cv2.putText(canvas, label[:int(size / 6.5)], (3, size + 13), cv2.FONT_HERSHEY_SIMPLEX,
                0.35, (230, 230, 230), 1, cv2.LINE_AA)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+", help="one folder, or two folders to interleave (A above B)")
    ap.add_argument("-o", "--output", default="contact_sheet.png")
    ap.add_argument("--cols", type=int, default=10)
    ap.add_argument("--size", type=int, default=160, help="tile size in px")
    a = ap.parse_args()

    lists = [sorted(p for p in Path(f).iterdir() if p.suffix.lower() in EXTS) for f in a.folders]
    names = [p.name for p in lists[0]]
    tiles_per_folder = [[tile(load(p, a.size), p.stem, a.size) for p in ps] for ps in lists]

    blank = np.zeros_like(tiles_per_folder[0][0])
    rows = []
    for start in range(0, len(names), a.cols):
        for tiles in tiles_per_folder:           # with 2 folders: original row, then Mooney row
            chunk = tiles[start:start + a.cols]
            chunk += [blank] * (a.cols - len(chunk))
            rows.append(np.hstack(chunk))
    cv2.imwrite(a.output, np.vstack(rows))
    print(f"Wrote {a.output} ({len(names)} images)")


if __name__ == "__main__":
    main()
