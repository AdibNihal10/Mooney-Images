"""
make_submission.py — build the ONE zip file in the exact required structure, check it, print its md5.

    python make_submission.py --name CompVP_Part1_TeamName

Required structure (from the Part 1 slides):
    Original/            100 original images
    Mooney/              100 Mooney images
    Subset/Original/     10 selected originals
    Subset/Mooney/       the same 10 as Mooneys
    Result1..4/Original/ results of system n on all originals
    Result1..4/Mooney/   results of system n on all Mooneys

By default the big raw .npy arrays are left out (they would push the zip
towards 1 GB); the per-image PNG/JSON/TXT results are included.
Use --include-npy if you really want them.
"""

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = {".png", ".jpg", ".jpeg"}


def files(folder, exts):
    return sorted(p for p in (ROOT / folder).glob("*") if p.is_file() and p.suffix.lower() in exts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="CompVP_Part1_submission", help="zip file name (without .zip)")
    ap.add_argument("--results", type=int, default=4, help="number of Result folders (4 for teams of 2-3)")
    ap.add_argument("--include-npy", action="store_true")
    a = ap.parse_args()

    result_exts = {".png", ".jpg", ".json", ".txt"} | ({".npy"} if a.include_npy else set())
    plan = {"Original": files("Original", IMG), "Mooney": files("Mooney", IMG),
            "Subset/Original": files("Subset/Original", IMG), "Subset/Mooney": files("Subset/Mooney", IMG)}
    for n in range(1, a.results + 1):
        for split in ("Original", "Mooney"):
            plan[f"Result{n}/{split}"] = files(f"Result{n}/{split}", result_exts)

    # ---- checks: counts and matching file names ----
    problems = []
    names = lambda key: {p.stem for p in plan[key]}
    for key, want in [("Original", 100), ("Mooney", 100), ("Subset/Original", 10), ("Subset/Mooney", 10)]:
        if len(plan[key]) != want:
            problems.append(f"{key}: {len(plan[key])} images (expected {want})")
    if names("Original") != names("Mooney"):
        problems.append("Original/ and Mooney/ file names don't match")
    if names("Subset/Original") != names("Subset/Mooney"):
        problems.append("Subset/Original and Subset/Mooney file names don't match")
    if not names("Subset/Original") <= names("Original"):
        problems.append("Subset contains images that are not in Original/")
    for n in range(1, a.results + 1):
        for split in ("Original", "Mooney"):
            missing = names(split) - names(f"Result{n}/{split}")
            if missing:
                problems.append(f"Result{n}/{split}: missing results for {len(missing)} images")

    for key, fs in plan.items():
        print(f"  {key:<20} {len(fs):>4} files")
    if problems:
        print("\nPROBLEMS:\n  - " + "\n  - ".join(problems))
        if input("\nCreate the zip anyway? [y/N] ").strip().lower() != "y":
            sys.exit(1)

    zpath = ROOT / f"{a.name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for key, fs in plan.items():
            for f in fs:
                z.write(f, f"{key}/{f.name}")

    md5 = hashlib.md5()
    with open(zpath, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            md5.update(block)
    print(f"\nWrote {zpath}  ({zpath.stat().st_size / 1e6:.1f} MB)")
    print(f"md5: {md5.hexdigest()}   <- keep this; if the StudOn upload fails, send this hash before the deadline")


if __name__ == "__main__":
    main()
