"""
download_objects.py — fetch free 3D meshes of everyday objects from Objaverse.

Objaverse is a large open collection of 3D models. Its "LVIS" subset is
labelled with object categories, so we can ask for e.g. a teapot or a mug.
We download a few CANDIDATES per category, because model quality varies.
You then keep the best one per category (see the guide).

    pip install objaverse
    python download_objects.py                      # 20 default categories, 2 candidates each
    python download_objects.py --candidates 3       # more to choose from
    python download_objects.py --list mug           # search category names

Files are saved as  meshes_candidates/<category>__<uid>.glb
(The render script reads the category from the part before "__".)
"""

import argparse
import difflib
import shutil
from pathlib import Path

# Everyday objects with clear 3D shape: good for depth, normals and recognition.
DEFAULT_CATEGORIES = [
    "teapot", "mug", "chair", "banana", "apple", "shoe", "guitar", "teddy_bear",
    "lamp", "bottle", "hat", "airplane", "bicycle", "pumpkin", "toaster",
    "sofa", "cup", "helmet", "violin", "pear",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="meshes_candidates")
    ap.add_argument("--candidates", type=int, default=2, help="models to download per category")
    ap.add_argument("--categories", nargs="*", default=DEFAULT_CATEGORIES)
    ap.add_argument("--list", metavar="TEXT", help="only print category names containing TEXT")
    a = ap.parse_args()

    import objaverse  # imported here so --help works without the package

    print("Loading Objaverse LVIS category list (first time downloads a small file)...")
    lvis = objaverse.load_lvis_annotations()          # {category: [uid, uid, ...]}

    if a.list:
        print("\n".join(sorted(c for c in lvis if a.list.lower() in c.lower())))
        return

    wanted = {}
    for cat in a.categories:
        if cat not in lvis:
            close = difflib.get_close_matches(cat, lvis.keys(), n=3)
            print(f"  '{cat}' not found. Close matches: {close}  -> using {close[0] if close else 'none'}")
            if not close:
                continue
            cat = close[0]
        wanted[cat] = lvis[cat][:a.candidates]

    uids = [u for us in wanted.values() for u in us]
    print(f"Downloading {len(uids)} models for {len(wanted)} categories...")
    paths = objaverse.load_objects(uids=uids, download_processes=4)   # {uid: local .glb path}

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for cat, us in wanted.items():
        safe = cat.replace("(", "").replace(")", "").replace(" ", "_")
        for u in us:
            if u in paths:
                shutil.copy(paths[u], out / f"{safe}__{u}.glb")
    print(f"Done. {len(list(out.glob('*.glb')))} files in {out}/")


if __name__ == "__main__":
    main()
